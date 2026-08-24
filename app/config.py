"""Environment-backed application configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from app.i18n import normalize_language, system_language
from app.local_config import (
    configured_path,
    default_data_dir,
    load_local_config,
    secure_directory,
    secure_file,
    setting,
)
from app.platform_support import resolve_audio_backend


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime paths and external executable configuration."""

    project_root: Path
    config_path: Path
    language: str
    data_dir: Path
    database_path: Path
    recordings_dir: Path
    transcripts_dir: Path
    guides_dir: Path
    models_dir: Path
    logs_dir: Path
    ffmpeg: str
    audio_backend: str
    default_audio_device: str
    whisper_model: str
    whisper_language: str | None
    whisper_cpu_threads: int
    whisper_beam_size: int
    whisper_vad: bool
    ai_provider: str
    ai_api_key: str | None = field(repr=False)
    ai_model: str | None
    ai_base_url: str | None
    ai_timeout_seconds: float
    assistant_chunk_seconds: int
    assistant_analysis_interval_seconds: int
    assistant_last_segments: int

    @classmethod
    def from_env(cls, *, load_ai_credentials: bool = True) -> Settings:
        project_root = Path(__file__).resolve().parents[1]
        config_path = configured_path()
        local = load_local_config(config_path)
        configured_data_dir = setting(local, "HAYVOZ_DATA_DIR")
        data_dir = (
            Path(configured_data_dir).expanduser().resolve()
            if configured_data_dir
            else default_data_dir().expanduser().resolve()
        )
        chunk_seconds = _bounded_int(
            "ASSISTANT_CHUNK_SECONDS",
            values=local,
            default=15,
            minimum=10,
            maximum=20,
        )
        analysis_interval = _positive_int(
            "ASSISTANT_ANALYSIS_INTERVAL_SECONDS", values=local, default=60
        )
        if analysis_interval < chunk_seconds:
            raise ValueError(
                "ASSISTANT_ANALYSIS_INTERVAL_SECONDS no puede ser menor que "
                "ASSISTANT_CHUNK_SECONDS."
            )
        return cls(
            project_root=project_root,
            config_path=config_path,
            language=normalize_language(
                setting(local, "HAYVOZ_LANGUAGE") or system_language()
            ),
            data_dir=data_dir,
            database_path=data_dir / "database.sqlite",
            recordings_dir=data_dir / "recordings",
            transcripts_dir=data_dir / "transcripts",
            guides_dir=data_dir / "guides",
            models_dir=data_dir / "models",
            logs_dir=data_dir / "logs",
            ffmpeg=setting(local, "HAYVOZ_FFMPEG") or "ffmpeg",
            audio_backend=resolve_audio_backend(
                setting(local, "HAYVOZ_AUDIO_BACKEND") or None
            ).value,
            default_audio_device=setting(local, "HAYVOZ_AUDIO_DEVICE") or "0",
            whisper_model=setting(local, "WHISPER_MODEL") or "small",
            whisper_language=setting(local, "WHISPER_LANGUAGE") or None,
            whisper_cpu_threads=_positive_int(
                "WHISPER_CPU_THREADS", values=local, default=4
            ),
            whisper_beam_size=_positive_int(
                "WHISPER_BEAM_SIZE", values=local, default=1
            ),
            whisper_vad=_boolean("WHISPER_VAD", values=local, default=True),
            ai_provider=(setting(local, "HAYVOZ_AI_PROVIDER") or "openai").lower(),
            ai_api_key=(
                setting(local, "HAYVOZ_AI_API_KEY", "OPENAI_API_KEY") or None
                if load_ai_credentials
                else None
            ),
            ai_model=setting(local, "HAYVOZ_AI_MODEL", "OPENAI_MODEL") or None,
            ai_base_url=setting(local, "HAYVOZ_AI_BASE_URL", "OPENAI_BASE_URL") or None,
            ai_timeout_seconds=_positive_float(
                "HAYVOZ_AI_TIMEOUT_SECONDS",
                values=local,
                default=60.0,
                fallback_names=("OPENAI_TIMEOUT_SECONDS",),
            ),
            assistant_chunk_seconds=chunk_seconds,
            assistant_analysis_interval_seconds=analysis_interval,
            assistant_last_segments=_positive_int(
                "ASSISTANT_LAST_SEGMENTS", values=local, default=20
            ),
        )

    def ensure_directories(self) -> None:
        for directory in (
            self.data_dir,
            self.recordings_dir,
            self.transcripts_dir,
            self.guides_dir,
            self.models_dir,
            self.logs_dir,
        ):
            secure_directory(directory)
        secure_file(self.config_path)

    def whisper_model_path(self, model: str | None = None) -> Path:
        return self.models_dir / f"faster-whisper-{model or self.whisper_model}"


def _positive_int(name: str, *, values: dict[str, str], default: int) -> int:
    raw = setting(values, name) or str(default)
    try:
        value = int(raw)
    except ValueError as error:
        raise ValueError(f"{name} debe ser un número entero positivo.") from error
    if value < 1:
        raise ValueError(f"{name} debe ser mayor que cero.")
    return value


def _bounded_int(
    name: str,
    *,
    values: dict[str, str],
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    value = _positive_int(name, values=values, default=default)
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} debe estar entre {minimum} y {maximum}.")
    return value


def _boolean(name: str, *, values: dict[str, str], default: bool) -> bool:
    raw = (setting(values, name) or str(default)).lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} debe ser true o false.")


def _positive_float(
    name: str,
    *,
    values: dict[str, str],
    default: float,
    fallback_names: tuple[str, ...] = (),
) -> float:
    raw = setting(values, name, *fallback_names) or str(default)
    try:
        value = float(raw)
    except ValueError as error:
        raise ValueError(f"{name} debe ser un número positivo.") from error
    if value <= 0:
        raise ValueError(f"{name} debe ser mayor que cero.")
    return value
