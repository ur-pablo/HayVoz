"""Import user-selected audio into the private HayVoz session store."""

from __future__ import annotations

import os
import subprocess
import uuid
from collections.abc import Callable, Sequence
from pathlib import Path

from app.config import Settings
from app.local_config import secure_file
from app.sessions.models import Session
from app.storage.repository import SessionRepository


class AudioImportError(RuntimeError):
    pass


Runner = Callable[..., subprocess.CompletedProcess[str]]


class AudioImportService:
    def __init__(
        self,
        settings: Settings,
        repository: SessionRepository,
        runner: Runner = subprocess.run,
    ) -> None:
        self.settings = settings
        self.repository = repository
        self.runner = runner

    def import_audio(self, source: Path, *, title: str) -> Session:
        selected = source.expanduser().resolve()
        normalized_title = title.strip()
        if not normalized_title:
            raise AudioImportError("El título no puede estar vacío.")
        if not selected.is_file():
            raise AudioImportError("El archivo de audio seleccionado no existe.")
        if selected.stat().st_size == 0:
            raise AudioImportError("El archivo de audio seleccionado está vacío.")

        session_id = str(uuid.uuid4())
        destination = self.settings.recordings_dir / f"{session_id}.flac"
        temporary = destination.with_suffix(".tmp.flac")
        command: Sequence[str] = (
            self.settings.ffmpeg,
            "-nostdin",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(selected),
            "-vn",
            "-map_metadata",
            "-1",
            "-map_chapters",
            "-1",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "flac",
            "-compression_level",
            "5",
            "-y",
            str(temporary),
        )
        try:
            result = self.runner(
                command,
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError as error:
            raise AudioImportError(
                "No se pudo ejecutar FFmpeg para importar el audio."
            ) from error

        if result.returncode != 0 or not temporary.is_file():
            temporary.unlink(missing_ok=True)
            raise AudioImportError(
                "FFmpeg no pudo convertir el audio seleccionado a FLAC."
            )
        if temporary.stat().st_size == 0:
            temporary.unlink(missing_ok=True)
            raise AudioImportError("FFmpeg produjo un archivo de audio vacío.")

        try:
            os.replace(temporary, destination)
        except OSError as error:
            temporary.unlink(missing_ok=True)
            raise AudioImportError(
                "No se pudo guardar el audio en el directorio privado."
            ) from error
        secure_file(destination)
        try:
            return self.repository.create_completed_import(
                session_id=session_id,
                title=normalized_title,
                audio_path=destination,
            )
        except Exception:
            destination.unlink(missing_ok=True)
            raise
