"""Offline transcription orchestration independent of recording."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from app.sessions.models import ACTIVE_STATUSES
from app.storage.repository import SessionNotFoundError, SessionRepository
from app.storage.transcript_repository import TranscriptRepository
from app.transcription.json_store import TranscriptJsonStore
from app.transcription.models import Speaker, TranscriptionOutput, TranscriptSegment
from app.transcription.transcriber import Transcriber, TranscriberError

logger = logging.getLogger(__name__)


class TranscriptionServiceError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class TranscriptionRun:
    session_id: str
    transcript_path: Path
    segment_count: int
    language: str | None
    language_probability: float | None
    model: str


class TranscriptionService:
    def __init__(
        self,
        sessions: SessionRepository,
        transcripts: TranscriptRepository,
        json_store: TranscriptJsonStore,
        transcriber: Transcriber,
    ) -> None:
        self.sessions = sessions
        self.transcripts = transcripts
        self.json_store = json_store
        self.transcriber = transcriber

    def transcribe(
        self,
        session_id: str,
        *,
        language: str | None,
        speaker: Speaker,
    ) -> TranscriptionRun:
        try:
            session = self.sessions.get(session_id)
        except SessionNotFoundError as error:
            raise TranscriptionServiceError(
                f"No existe la sesión {session_id}."
            ) from error
        if session.status in ACTIVE_STATUSES:
            raise TranscriptionServiceError(
                "Detén la grabación antes de iniciar la transcripción."
            )
        if not _valid_audio(session.audio_path):
            raise TranscriptionServiceError(
                "La sesión no tiene un archivo de audio válido."
            )
        if session.system_audio_path is not None and not _valid_audio(
            session.system_audio_path
        ):
            raise TranscriptionServiceError(
                "La sesión no tiene un archivo de audio del sistema válido."
            )

        try:
            primary = self.transcriber.transcribe(
                session.audio_path,
                language=language,
                speaker=(
                    Speaker.INTERVIEWER
                    if session.system_audio_path is not None
                    else speaker
                ),
            )
            outputs = [primary]
            if session.system_audio_path is not None:
                outputs.append(
                    self.transcriber.transcribe(
                        session.system_audio_path,
                        language=language,
                        speaker=Speaker.INTERVIEWEE,
                    )
                )
        except TranscriberError as error:
            logger.error(
                "transcription_failed",
                extra={"event": "transcription_failed", "session_id": session_id},
            )
            raise TranscriptionServiceError(str(error)) from error

        segments = [
            TranscriptSegment(
                session_id=session_id,
                **segment.model_dump(),
            )
            for output in outputs
            for segment in output.segments
        ]
        segments.sort(
            key=lambda item: (
                item.start,
                item.end,
                0 if item.speaker == Speaker.INTERVIEWER else 1,
            )
        )
        previous_json = self.json_store.snapshot(session_id)
        try:
            transcript_path = self.json_store.write(session_id, segments)
            self.transcripts.replace_for_session(session_id, segments)
        except Exception as error:
            self.json_store.restore(session_id, previous_json)
            logger.error(
                "transcript_persistence_failed",
                extra={
                    "event": "transcript_persistence_failed",
                    "session_id": session_id,
                },
            )
            raise TranscriptionServiceError(
                "No se pudo persistir la transcripción; se restauró el JSON anterior."
            ) from error

        logger.info(
            "transcription_completed",
            extra={"event": "transcription_completed", "session_id": session_id},
        )
        return TranscriptionRun(
            session_id=session_id,
            transcript_path=transcript_path,
            segment_count=len(segments),
            language=_combined_language(outputs),
            language_probability=_combined_probability(outputs),
            model=self.transcriber.model_name.value,
        )

    def get_segments(self, session_id: str) -> list[TranscriptSegment]:
        try:
            self.sessions.get(session_id)
        except SessionNotFoundError as error:
            raise TranscriptionServiceError(
                f"No existe la sesión {session_id}."
            ) from error
        segments = self.transcripts.list_for_session(session_id)
        if segments and not self._json_matches(session_id, segments):
            self.json_store.write(session_id, segments)
            logger.warning(
                "transcript_json_recovered",
                extra={"event": "transcript_json_recovered", "session_id": session_id},
            )
        return segments

    def _json_matches(self, session_id: str, segments: list[TranscriptSegment]) -> bool:
        try:
            public_segments = self.json_store.read(session_id)
        except (OSError, ValueError):
            return False
        return public_segments == [segment.content() for segment in segments]


def _valid_audio(path: Path) -> bool:
    return path.is_file() and path.stat().st_size > 0


def _combined_language(outputs: list[TranscriptionOutput]) -> str | None:
    languages = list(dict.fromkeys(item.language for item in outputs if item.language))
    return " / ".join(languages) if languages else None


def _combined_probability(outputs: list[TranscriptionOutput]) -> float | None:
    languages = {item.language for item in outputs if item.language}
    if len(languages) > 1:
        return None
    probabilities = [
        item.language_probability
        for item in outputs
        if item.language_probability is not None
    ]
    return min(probabilities) if len(probabilities) == len(outputs) else None
