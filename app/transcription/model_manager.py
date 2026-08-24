"""Explicit, allow-listed Whisper model downloads."""

from __future__ import annotations

import os
import shutil
import tempfile
from collections.abc import Callable
from pathlib import Path

from app.config import Settings
from app.transcription.models import WhisperModelName


class ModelManagerError(RuntimeError):
    pass


DownloadFunction = Callable[..., str]


class WhisperModelManager:
    def __init__(
        self,
        settings: Settings,
        *,
        downloader: DownloadFunction | None = None,
    ) -> None:
        self.settings = settings
        self._downloader = downloader

    def path_for(self, model: WhisperModelName | str) -> Path:
        name = _validate_model(model)
        return self.settings.whisper_model_path(name.value)

    def is_installed(self, model: WhisperModelName | str) -> bool:
        return _model_is_ready(self.path_for(model))

    def download(self, model: WhisperModelName | str) -> tuple[Path, bool]:
        """Download to a temporary directory, then publish with one rename."""
        name = _validate_model(model)
        target = self.path_for(name)
        if _model_is_ready(target):
            return target, False

        self.settings.models_dir.mkdir(parents=True, exist_ok=True)
        _cleanup_incomplete_downloads(target, self.settings.models_dir)
        temporary = Path(
            tempfile.mkdtemp(
                prefix=f".{target.name}-",
                dir=self.settings.models_dir,
            )
        )
        try:
            downloader = self._downloader or _official_downloader()
            downloader(name.value, output_dir=str(temporary), local_files_only=False)
            if not _model_is_ready(temporary):
                raise ModelManagerError("La descarga terminó sin un modelo válido.")
            if target.exists():
                _remove_owned_model_directory(target, self.settings.models_dir)
            os.replace(temporary, target)
        except ModelManagerError:
            shutil.rmtree(temporary, ignore_errors=True)
            raise
        except Exception as error:
            shutil.rmtree(temporary, ignore_errors=True)
            raise ModelManagerError(
                f"No se pudo descargar Whisper {name.value}: {error}"
            ) from error
        return target, True


def _official_downloader() -> DownloadFunction:
    try:
        from faster_whisper.utils import download_model
    except ImportError as error:
        raise ModelManagerError(
            "faster-whisper no está instalado. Ejecuta 'uv sync --extra dev'."
        ) from error
    return download_model


def _validate_model(model: WhisperModelName | str) -> WhisperModelName:
    try:
        return model if isinstance(model, WhisperModelName) else WhisperModelName(model)
    except ValueError as error:
        allowed = ", ".join(item.value for item in WhisperModelName)
        raise ModelManagerError(f"Modelo no permitido. Usa: {allowed}.") from error


def _model_is_ready(path: Path) -> bool:
    return (
        path.is_dir()
        and (path / "model.bin").is_file()
        and (path / "config.json").is_file()
    )


def _remove_owned_model_directory(target: Path, models_dir: Path) -> None:
    resolved_target = target.resolve()
    resolved_models = models_dir.resolve()
    if resolved_target.parent != resolved_models or not target.name.startswith(
        "faster-whisper-"
    ):
        raise ModelManagerError(
            "Se rechazó limpiar una ruta de modelo no administrada."
        )
    shutil.rmtree(target)


def _cleanup_incomplete_downloads(target: Path, models_dir: Path) -> None:
    for candidate in models_dir.glob(f".{target.name}-*"):
        if candidate.is_dir():
            _remove_owned_temporary_directory(candidate, models_dir, target.name)


def _remove_owned_temporary_directory(
    target: Path, models_dir: Path, model_directory_name: str
) -> None:
    if target.resolve().parent != models_dir.resolve() or not target.name.startswith(
        f".{model_directory_name}-"
    ):
        raise ModelManagerError(
            "Se rechazó limpiar una descarga temporal no administrada."
        )
    shutil.rmtree(target)
