"""Small, explicit operating-system boundary for audio and process launch."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
from enum import StrEnum


class AudioBackend(StrEnum):
    AVFOUNDATION = "avfoundation"
    DSHOW = "dshow"
    PULSE = "pulse"
    ALSA = "alsa"


def default_audio_backend() -> AudioBackend:
    if sys.platform == "darwin":
        return AudioBackend.AVFOUNDATION
    if os.name == "nt":
        return AudioBackend.DSHOW
    return AudioBackend.PULSE


def resolve_audio_backend(value: str | None) -> AudioBackend:
    try:
        return AudioBackend(value.strip().lower()) if value else default_audio_backend()
    except ValueError as error:
        supported = ", ".join(item.value for item in AudioBackend)
        raise ValueError(
            f"HAYVOZ_AUDIO_BACKEND debe ser uno de: {supported}."
        ) from error


def ffmpeg_audio_input(device: str, backend: AudioBackend) -> list[str]:
    if backend is AudioBackend.AVFOUNDATION:
        source = f":{device}"
    elif backend is AudioBackend.DSHOW:
        source = f"audio={device}"
    else:
        source = device
    return ["-f", backend.value, "-i", source]


def detached_process_options() -> dict[str, object]:
    if os.name == "nt":
        return {
            "creationflags": getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
        }
    return {"start_new_session": True, "close_fds": True}


def signal_process_group(pid: int, *, force: bool = False) -> None:
    if os.name == "nt":
        selected = signal.SIGTERM if force else signal.CTRL_BREAK_EVENT
        os.kill(pid, selected)
        return
    os.killpg(pid, signal.SIGTERM if force else signal.SIGINT)
