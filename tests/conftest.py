from __future__ import annotations

from pathlib import Path

import pytest

from app.config import Settings
from app.storage.database import Database
from app.storage.repository import SessionRepository


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    data_dir = tmp_path / "data"
    result = Settings(
        project_root=tmp_path,
        config_path=tmp_path / "config.env",
        language="es",
        data_dir=data_dir,
        database_path=data_dir / "database.sqlite",
        recordings_dir=data_dir / "recordings",
        transcripts_dir=data_dir / "transcripts",
        guides_dir=data_dir / "guides",
        models_dir=data_dir / "models",
        logs_dir=data_dir / "logs",
        ffmpeg="ffmpeg",
        audio_backend="avfoundation",
        default_audio_device="0",
        whisper_model="small",
        whisper_language=None,
        whisper_cpu_threads=2,
        whisper_beam_size=1,
        whisper_vad=True,
        ai_provider="openai",
        ai_api_key=None,
        ai_model=None,
        ai_base_url=None,
        ai_timeout_seconds=10.0,
        assistant_chunk_seconds=15,
        assistant_analysis_interval_seconds=60,
        assistant_last_segments=20,
    )
    result.ensure_directories()
    return result


@pytest.fixture
def repository(settings: Settings) -> SessionRepository:
    database = Database(settings.database_path)
    database.initialize()
    return SessionRepository(database)
