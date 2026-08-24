"""Automatic local import and transcription for completed browser captures."""

from __future__ import annotations

import os
from pathlib import Path

from app.browser.inbox import (
    MIME_EXTENSIONS,
    BrowserMessageError,
    _atomic_json,
    _read_json,
)
from app.config import Settings
from app.local_config import secure_file
from app.sessions.importer import AudioImportError, AudioImportService
from app.storage.database import Database
from app.storage.repository import SessionNotFoundError, SessionRepository
from app.storage.transcript_repository import TranscriptRepository
from app.transcription.json_store import TranscriptJsonStore
from app.transcription.models import Speaker, WhisperModelName
from app.transcription.service import TranscriptionService, TranscriptionServiceError
from app.transcription.transcriber import FasterWhisperTranscriber


class BrowserProcessor:
    def __init__(
        self,
        settings: Settings,
        database: Database,
        sessions: SessionRepository,
    ) -> None:
        self.settings = settings
        self.sessions = sessions
        self.importer = AudioImportService(settings, sessions)
        try:
            model = WhisperModelName(settings.whisper_model)
        except ValueError:
            model = WhisperModelName.SMALL
        self.transcription = TranscriptionService(
            sessions,
            TranscriptRepository(database),
            TranscriptJsonStore(settings),
            FasterWhisperTranscriber(
                settings,
                model,
            ),
        )

    def process_pending(self, *, limit: int = 1) -> int:
        processed = 0
        for root in self.settings.browser_inbox_roots():
            if not root.is_dir():
                continue
            for directory in sorted(root.iterdir()):
                if processed >= limit:
                    return processed
                if not directory.is_dir() or directory.is_symlink():
                    continue
                if not (
                    (directory / "request.json").is_file()
                    or (directory / "processing.json").is_file()
                ):
                    continue
                if self._claim_and_process(directory):
                    processed += 1
        return processed

    def _claim_and_process(self, directory: Path) -> bool:
        lock_path = directory / ".processing.lock"
        try:
            descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            return False
        os.close(descriptor)
        secure_file(lock_path)
        try:
            request_path = directory / "request.json"
            processing_path = directory / "processing.json"
            if request_path.exists():
                os.replace(request_path, processing_path)
                secure_file(processing_path)
            self._process(directory, processing_path)
            return True
        finally:
            lock_path.unlink(missing_ok=True)

    def _process(self, directory: Path, processing_path: Path) -> None:
        result_path = directory / "result.json"
        try:
            metadata = _read_json(directory / "metadata.json")
            request = _read_json(processing_path)
            title = metadata.get("title")
            mime_type = metadata.get("mime_type")
            chunk_count = request.get("chunk_count")
            if not isinstance(title, str) or mime_type not in MIME_EXTENSIONS:
                raise AudioImportError("Los metadatos de captura no son válidos.")
            if not isinstance(chunk_count, int) or chunk_count < 1:
                raise AudioImportError("La captura no tiene chunks válidos.")

            previous = _read_json(result_path) if result_path.is_file() else {}
            session_id = previous.get("session_id")
            if isinstance(session_id, str):
                try:
                    self.sessions.get(session_id)
                except SessionNotFoundError:
                    session_id = None
            else:
                session_id = None

            source = directory / f"source{MIME_EXTENSIONS[mime_type]}"
            if session_id is None:
                self._assemble(directory, source, chunk_count)
                session = self.importer.import_audio(source, title=title)
                session_id = session.id
                _atomic_json(
                    result_path,
                    {"ok": True, "status": "transcribing", "session_id": session_id},
                )

            run = self.transcription.transcribe(
                session_id,
                language=self.settings.whisper_language,
                speaker=Speaker.INTERVIEWER,
            )
            _atomic_json(
                result_path,
                {
                    "ok": True,
                    "status": "completed",
                    "session_id": session_id,
                    "segment_count": run.segment_count,
                },
            )
            processing_path.unlink(missing_ok=True)
            source.unlink(missing_ok=True)
            for chunk in directory.glob("chunk-*.bin"):
                chunk.unlink(missing_ok=True)
        except (
            AudioImportError,
            BrowserMessageError,
            TranscriptionServiceError,
            OSError,
            ValueError,
        ) as error:
            _atomic_json(
                result_path,
                {"ok": False, "status": "failed", "error": _safe_error(error)},
            )
            processing_path.unlink(missing_ok=True)
        except Exception as error:
            _atomic_json(
                result_path,
                {"ok": False, "status": "failed", "error": _safe_error(error)},
            )
            processing_path.unlink(missing_ok=True)

    @staticmethod
    def _assemble(directory: Path, source: Path, chunk_count: int) -> None:
        temporary = source.with_suffix(f"{source.suffix}.tmp")
        try:
            with temporary.open("wb") as output:
                for sequence in range(chunk_count):
                    chunk = directory / f"chunk-{sequence:08d}.bin"
                    if not chunk.is_file():
                        raise AudioImportError("Faltan chunks de la captura.")
                    output.write(chunk.read_bytes())
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, source)
            secure_file(source)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise


def _safe_error(error: Exception) -> str:
    message = str(error)
    if "no está instalado" in message:
        return message
    if isinstance(error, AudioImportError):
        return message
    return "No se pudo completar la transcripción local. Revisa los logs locales."
