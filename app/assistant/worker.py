"""Detached sequential worker used only while Assistant mode is active."""

from __future__ import annotations

import argparse
import logging
import signal
import threading
from pathlib import Path

from app.assistant.service import AssistantService, AssistantServiceError
from app.audio.assistant_recorder import ChunkAudioStore, ChunkedFFmpegCapture
from app.audio.recorder import RecorderError
from app.config import Settings
from app.llm.provider import LLMProvider, LLMProviderError
from app.logging_config import configure_logging
from app.sessions.guide import InterviewGuideStore
from app.sessions.models import SessionMode
from app.storage.assistant_repository import AssistantRepository
from app.storage.database import Database
from app.storage.repository import SessionNotFoundError, SessionRepository
from app.storage.transcript_repository import TranscriptRepository
from app.transcription.json_store import TranscriptJsonStore
from app.transcription.models import WhisperModelName
from app.transcription.transcriber import FasterWhisperTranscriber

logger = logging.getLogger(__name__)


def run_worker(session_id: str, device: str) -> int:
    settings = Settings.from_env()
    settings.ensure_directories()
    configure_logging(settings.logs_dir)
    database = Database(settings.database_path)
    database.initialize()
    sessions = SessionRepository(database)
    try:
        session = sessions.get(session_id)
    except SessionNotFoundError:
        logger.error(
            "assistant_session_missing",
            extra={"event": "assistant_session_missing", "session_id": session_id},
        )
        return 1
    if (
        session.mode is not SessionMode.ASSISTANT
        or session.assistant_chunk_seconds is None
    ):
        logger.error(
            "assistant_session_invalid",
            extra={"event": "assistant_session_invalid", "session_id": session_id},
        )
        return 1

    try:
        model = WhisperModelName(settings.whisper_model)
    except ValueError:
        model = WhisperModelName.SMALL
    provider = _provider(settings, local_only=session.local_only, session_id=session_id)
    service = AssistantService(
        sessions,
        TranscriptRepository(database),
        AssistantRepository(database),
        TranscriptJsonStore(settings),
        InterviewGuideStore(settings),
        FasterWhisperTranscriber(settings, model),
        provider,
        language=settings.whisper_language,
    )
    chunk_store = ChunkAudioStore(settings)
    capture = ChunkedFFmpegCapture(settings, chunk_store)
    stop_event = threading.Event()

    def request_stop(_signal_number: int, _frame: object) -> None:
        stop_event.set()

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)
    capture_log = settings.logs_dir / f"assistant-ffmpeg-{session_id}.log"
    try:
        process = capture.start(
            session_id,
            device=device,
            chunk_seconds=session.assistant_chunk_seconds,
            log_path=capture_log,
        )
    except RecorderError:
        logger.error(
            "assistant_capture_failed",
            extra={"event": "assistant_capture_failed", "session_id": session_id},
        )
        return 1

    processed: set[int] = set()
    try:
        while process.poll() is None and not stop_event.is_set():
            _process_ready_chunks(
                service, chunk_store, session_id, processed, active=True
            )
            stop_event.wait(1.0)
    finally:
        capture.stop(process)
        _process_ready_chunks(service, chunk_store, session_id, processed, active=False)
        chunk_store.pid_path(session_id).unlink(missing_ok=True)
        try:
            chunk_store.finalize(session_id, session.audio_path)
        except RecorderError:
            logger.exception(
                "assistant_audio_finalize_failed",
                extra={
                    "event": "assistant_audio_finalize_failed",
                    "session_id": session_id,
                },
            )
            return 1
    return 0


def _provider(
    settings: Settings,
    *,
    local_only: bool,
    session_id: str,
) -> LLMProvider | None:
    if local_only:
        return None
    try:
        from app.integrations.openai import create_provider

        return create_provider(settings)
    except LLMProviderError:
        logger.warning(
            "assistant_ai_provider_disabled",
            extra={
                "event": "assistant_ai_provider_disabled",
                "session_id": session_id,
                "status": "configuration_incomplete",
            },
        )
        return None


def _process_ready_chunks(
    service: AssistantService,
    store: ChunkAudioStore,
    session_id: str,
    processed: set[int],
    *,
    active: bool,
) -> None:
    for chunk in store.completed_chunks(session_id, capture_active=active):
        index = _chunk_index(chunk)
        if index in processed:
            continue
        try:
            service.process_chunk(session_id, chunk, chunk_index=index)
        except AssistantServiceError:
            logger.exception(
                "assistant_chunk_failed",
                extra={"event": "assistant_chunk_failed", "session_id": session_id},
            )
        processed.add(index)
        try:
            service.maybe_suggest(session_id)
        except AssistantServiceError:
            logger.exception(
                "assistant_suggestion_failed",
                extra={
                    "event": "assistant_suggestion_failed",
                    "session_id": session_id,
                },
            )


def _chunk_index(path: Path) -> int:
    try:
        return int(path.stem)
    except ValueError as error:
        raise AssistantServiceError(f"Nombre de chunk inválido: {path.name}") from error


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--device", required=True)
    arguments = parser.parse_args()
    raise SystemExit(run_worker(arguments.session_id, arguments.device))


if __name__ == "__main__":
    main()
