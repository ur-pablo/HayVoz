"""Resource-conscious microphone recording through one ffmpeg process."""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from app.config import Settings
from app.platform_support import (
    AudioBackend,
    detached_process_options,
    ffmpeg_audio_input,
    signal_process_group,
)


class RecorderError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class StopResult:
    stopped: bool
    forced: bool = False


class Recorder(Protocol):
    def start(
        self,
        audio_path: Path,
        device: str,
        log_path: Path,
        *,
        system_device: str | None = None,
    ) -> int: ...

    def is_active(self, pid: int | None, audio_path: Path) -> bool: ...

    def stop(
        self, pid: int, audio_path: Path, *, timeout: float = 10.0
    ) -> StopResult: ...


class FFmpegRecorder:
    """Launch and control a detached ffmpeg/AVFoundation recorder."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def available(self) -> bool:
        return shutil.which(self.settings.ffmpeg) is not None

    def start(
        self,
        audio_path: Path,
        device: str,
        log_path: Path,
        *,
        system_device: str | None = None,
    ) -> int:
        audio_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        command = self.build_command(audio_path, device, system_device=system_device)
        try:
            with log_path.open("ab") as log_file:
                process = subprocess.Popen(
                    command,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=log_file,
                    **detached_process_options(),
                )
        except FileNotFoundError as error:
            raise RecorderError(
                "No se encontró ffmpeg. Ejecuta 'hayvoz doctor'."
            ) from error
        except OSError as error:
            raise RecorderError(f"No se pudo iniciar ffmpeg: {error}") from error

        time.sleep(0.35)
        exit_code = process.poll()
        if exit_code is not None:
            detail = _tail(log_path)
            raise RecorderError(
                f"ffmpeg terminó al iniciar (código {exit_code}). {detail}".strip()
            )
        return process.pid

    def build_command(
        self,
        audio_path: Path,
        device: str,
        *,
        system_device: str | None = None,
    ) -> list[str]:
        """Build one-process capture for one or two independent inputs."""
        command = [
            self.settings.ffmpeg,
            "-nostdin",
            "-hide_banner",
            "-loglevel",
            "warning",
            "-y",
            "-thread_queue_size",
            "128",
        ]
        backend = AudioBackend(self.settings.audio_backend)
        command.extend(ffmpeg_audio_input(device, backend))
        if system_device is not None:
            command.extend(
                [
                    "-thread_queue_size",
                    "128",
                ]
            )
            command.extend(ffmpeg_audio_input(system_device, backend))
        command.extend(_flac_output("0:a:0", audio_path))
        if system_device is not None:
            command.extend(_flac_output("1:a:0", system_audio_path_for(audio_path)))
        return command

    def is_active(self, pid: int | None, audio_path: Path) -> bool:
        if not pid or not _process_exists(pid):
            return False
        command = _process_command(pid)
        if not command:
            return False
        executable = Path(self.settings.ffmpeg).name
        return executable in command and str(audio_path) in command

    def stop(self, pid: int, audio_path: Path, *, timeout: float = 10.0) -> StopResult:
        if not self.is_active(pid, audio_path):
            return StopResult(stopped=False)
        try:
            signal_process_group(pid)
        except ProcessLookupError:
            return StopResult(stopped=True)
        except PermissionError as error:
            raise RecorderError(
                "El sistema operativo rechazó la señal de cierre para ffmpeg."
            ) from error
        if _wait_until_stopped(pid, timeout):
            return StopResult(stopped=True)

        if not self.is_active(pid, audio_path):
            return StopResult(stopped=True)
        try:
            signal_process_group(pid, force=True)
        except ProcessLookupError:
            return StopResult(stopped=True)
        except PermissionError as error:
            raise RecorderError(
                "El sistema operativo rechazó la finalización de ffmpeg."
            ) from error
        return StopResult(stopped=_wait_until_stopped(pid, 2.0), forced=True)


def _process_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except (ProcessLookupError, PermissionError):
        return False
    return True


def _process_command(pid: int) -> str:
    if os.name == "nt":
        command = [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            f"(Get-CimInstance Win32_Process -Filter 'ProcessId = {pid}').CommandLine",
        ]
    else:
        command = ["ps", "-ww", "-p", str(pid), "-o", "command="]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return ""
    value = result.stdout.strip() if result.returncode == 0 else ""
    return "" if value.casefold() in {"", "null"} else value


def _wait_until_stopped(pid: int, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not _process_exists(pid):
            return True
        time.sleep(0.1)
    return not _process_exists(pid)


def _tail(path: Path, limit: int = 600) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")[-limit:].strip()
    except OSError:
        return ""


def system_audio_path_for(audio_path: Path) -> Path:
    return audio_path.with_name(f"{audio_path.stem}.system{audio_path.suffix}")


def _flac_output(source: str, path: Path) -> list[str]:
    return [
        "-map",
        source,
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-c:a",
        "flac",
        "-compression_level",
        "5",
        str(path),
    ]
