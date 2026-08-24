"""Read-only dependency and environment diagnostics."""

from __future__ import annotations

import importlib.util
import shutil
import sqlite3
import sys
from dataclasses import dataclass
from enum import StrEnum

from app.audio.devices import AudioDevice, list_audio_devices, probe_microphone
from app.config import Settings
from app.transcription.model_manager import ModelManagerError, WhisperModelManager


class CheckLevel(StrEnum):
    OK = "ok"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class DoctorCheck:
    name: str
    level: CheckLevel
    detail: str
    suggestion: str = ""


def run_doctor(settings: Settings, *, probe_mic: bool = True) -> list[DoctorCheck]:
    checks: list[DoctorCheck] = []
    python_ok = sys.version_info >= (3, 11)
    checks.append(
        DoctorCheck(
            "Python",
            CheckLevel.OK if python_ok else CheckLevel.ERROR,
            sys.version.split()[0],
            "Instala Python 3.11 o superior." if not python_ok else "",
        )
    )

    ffmpeg_path = shutil.which(settings.ffmpeg)
    checks.append(
        DoctorCheck(
            "ffmpeg",
            CheckLevel.OK if ffmpeg_path else CheckLevel.ERROR,
            ffmpeg_path or "no encontrado",
            "Instálalo manualmente (por ejemplo, brew install ffmpeg)."
            if not ffmpeg_path
            else "",
        )
    )

    devices = []
    if ffmpeg_path:
        try:
            devices = list_audio_devices(
                settings.ffmpeg, backend=settings.audio_backend
            )
            checks.append(
                DoctorCheck(
                    "Dispositivos de audio",
                    CheckLevel.OK if devices else CheckLevel.ERROR,
                    f"{len(devices)} detectado(s)",
                    f"Revisa permisos y la entrada {settings.audio_backend}."
                    if not devices
                    else "",
                )
            )
        except RuntimeError as error:
            checks.append(
                DoctorCheck(
                    "Dispositivos de audio",
                    CheckLevel.ERROR,
                    str(error),
                    f"Revisa la configuración del backend {settings.audio_backend}.",
                )
            )
    else:
        checks.append(
            DoctorCheck(
                "Dispositivos de audio",
                CheckLevel.ERROR,
                "no comprobados sin ffmpeg",
            )
        )

    loopbacks = _system_audio_devices(devices)
    is_avfoundation = settings.audio_backend == "avfoundation"
    checks.append(
        DoctorCheck(
            "Audio de sistema",
            CheckLevel.OK if loopbacks else CheckLevel.WARNING,
            (
                ", ".join(f"{item.index}: {item.name}" for item in loopbacks)
                if loopbacks
                else (
                    "BlackHole no detectado; captura dual opcional no disponible"
                    if is_avfoundation
                    else (
                        "entrada loopback no detectada; captura dual opcional no "
                        "disponible"
                    )
                )
            ),
            (
                (
                    "Consulta docs/MACOS_SYSTEM_AUDIO.md; la instalación y el "
                    "ruteo son manuales."
                    if is_avfoundation
                    else (
                        "Configura una fuente monitor/loopback compatible con tu "
                        "sistema."
                    )
                )
                if not loopbacks
                else ""
            ),
        )
    )

    if ffmpeg_path and devices and probe_mic:
        configured = next(
            (
                device
                for device in devices
                if device.index == settings.default_audio_device
            ),
            devices[0],
        )
        ok, detail = probe_microphone(
            settings.ffmpeg,
            configured.index,
            backend=settings.audio_backend,
        )
        checks.append(
            DoctorCheck(
                "Acceso al micrófono",
                CheckLevel.OK if ok else CheckLevel.ERROR,
                detail,
                "Habilita el micrófono para Terminal en Ajustes > "
                "Privacidad y seguridad."
                if not ok
                else "",
            )
        )
    else:
        checks.append(
            DoctorCheck(
                "Acceso al micrófono",
                CheckLevel.WARNING,
                "prueba omitida" if not probe_mic else "no comprobable",
            )
        )

    whisper_installed = importlib.util.find_spec("faster_whisper") is not None
    checks.append(
        DoctorCheck(
            "faster-whisper",
            CheckLevel.OK if whisper_installed else CheckLevel.ERROR,
            "instalado" if whisper_installed else "ausente",
            "Ejecuta uv sync --extra dev." if not whisper_installed else "",
        )
    )
    manager = WhisperModelManager(settings)
    try:
        model_ready = manager.is_installed(settings.whisper_model)
        model_detail = (
            f"{settings.whisper_model}: instalado"
            if model_ready
            else f"{settings.whisper_model}: no descargado"
        )
        model_suggestion = (
            f"Ejecuta hayvoz model download --model {settings.whisper_model}."
            if not model_ready
            else ""
        )
    except ModelManagerError as error:
        model_ready = False
        model_detail = str(error)
        model_suggestion = "Configura tiny, base, small o medium."
    checks.append(
        DoctorCheck(
            "Modelo Whisper",
            CheckLevel.OK if model_ready else CheckLevel.WARNING,
            model_detail,
            model_suggestion,
        )
    )

    free_bytes = shutil.disk_usage(settings.data_dir).free
    free_gib = free_bytes / (1024**3)
    disk_level = (
        CheckLevel.OK
        if free_gib >= 2
        else (CheckLevel.WARNING if free_gib >= 0.5 else CheckLevel.ERROR)
    )
    checks.append(
        DoctorCheck(
            "Espacio disponible",
            disk_level,
            f"{free_gib:.1f} GiB en {settings.data_dir}",
            "Libera al menos 2 GiB antes de una entrevista larga."
            if disk_level is not CheckLevel.OK
            else "",
        )
    )

    try:
        with sqlite3.connect(settings.database_path) as connection:
            version = connection.execute("SELECT sqlite_version()").fetchone()[0]
        checks.append(DoctorCheck("SQLite", CheckLevel.OK, version))
    except sqlite3.Error as error:
        checks.append(DoctorCheck("SQLite", CheckLevel.ERROR, str(error)))

    for dependency in (
        "typer",
        "rich",
        "pydantic",
        "ctranslate2",
        "onnxruntime",
        "openai",
    ):
        installed = importlib.util.find_spec(dependency) is not None
        checks.append(
            DoctorCheck(
                f"Dependencia {dependency}",
                CheckLevel.OK if installed else CheckLevel.ERROR,
                "instalada" if installed else "ausente",
                "Ejecuta uv sync --extra dev." if not installed else "",
            )
        )

    api_key = bool(settings.ai_api_key)
    model = settings.ai_model
    checks.append(
        DoctorCheck(
            "Proveedor de IA",
            CheckLevel.OK if api_key and model else CheckLevel.WARNING,
            "configurado"
            if api_key and model
            else "opcional; configuración incompleta",
            "Define HAYVOZ_AI_API_KEY y HAYVOZ_AI_MODEL antes de usar analyze."
            if not (api_key and model)
            else "",
        )
    )
    checks.append(
        DoctorCheck(
            "Assistant batching",
            CheckLevel.OK,
            (
                f"chunks={settings.assistant_chunk_seconds}s, "
                f"IA>={settings.assistant_analysis_interval_seconds}s, "
                f"contexto={settings.assistant_last_segments} segmentos"
            ),
        )
    )
    return checks


def _blackhole_devices(devices: list[AudioDevice]) -> list[AudioDevice]:
    return [device for device in devices if "blackhole" in device.name.casefold()]


def _system_audio_devices(devices: list[AudioDevice]) -> list[AudioDevice]:
    markers = ("blackhole", "loopback", "monitor of", "stereo mix", "what u hear")
    return [
        device
        for device in devices
        if any(marker in device.name.casefold() for marker in markers)
    ]
