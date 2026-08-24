from pathlib import Path

import pytest

from app.config import Settings
from app.transcription.model_manager import ModelManagerError, WhisperModelManager


def test_model_download_is_explicit_atomic_and_idempotent(settings: Settings) -> None:
    calls: list[str] = []

    def fake_download(model: str, *, output_dir: str, local_files_only: bool) -> str:
        assert local_files_only is False
        calls.append(model)
        destination = Path(output_dir)
        (destination / "model.bin").write_bytes(b"model")
        (destination / "config.json").write_text("{}", encoding="utf-8")
        return output_dir

    manager = WhisperModelManager(settings, downloader=fake_download)
    stale = settings.models_dir / ".faster-whisper-small-interrupted"
    stale.mkdir()
    (stale / "partial.bin").write_bytes(b"partial")
    path, downloaded = manager.download("small")
    assert downloaded is True
    assert path == settings.models_dir / "faster-whisper-small"
    assert manager.is_installed("small") is True
    assert stale.exists() is False

    same_path, downloaded_again = manager.download("small")
    assert same_path == path
    assert downloaded_again is False
    assert calls == ["small"]


def test_large_model_is_rejected(settings: Settings) -> None:
    manager = WhisperModelManager(settings)
    with pytest.raises(ModelManagerError, match="Modelo no permitido"):
        manager.download("large")
