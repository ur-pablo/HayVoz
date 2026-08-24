"""Platform-aware FFmpeg audio-device discovery."""

from __future__ import annotations

import re
import subprocess
from collections.abc import Callable
from dataclasses import dataclass

from app.platform_support import AudioBackend, ffmpeg_audio_input, resolve_audio_backend

ANSI_ESCAPE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
DEVICE_LINE = re.compile(r"\[(?P<index>\d+)\]\s+(?P<name>.+)$")


@dataclass(frozen=True, slots=True)
class AudioDevice:
    index: str
    name: str


def parse_avfoundation_devices(output: str) -> list[AudioDevice]:
    """Extract only audio devices from ffmpeg's AVFoundation diagnostics."""
    devices: list[AudioDevice] = []
    in_audio_section = False
    for raw_line in ANSI_ESCAPE.sub("", output).splitlines():
        if "AVFoundation audio devices:" in raw_line:
            in_audio_section = True
            continue
        if not in_audio_section:
            continue
        match = DEVICE_LINE.search(raw_line)
        if match:
            devices.append(
                AudioDevice(
                    index=match.group("index"),
                    name=match.group("name").strip(),
                )
            )
    return devices


def parse_dshow_devices(output: str) -> list[AudioDevice]:
    devices: list[AudioDevice] = []
    seen: set[str] = set()
    for line in ANSI_ESCAPE.sub("", output).splitlines():
        match = re.search(r'"(?P<name>.+)"\s+\(audio\)', line)
        if match and match.group("name") not in seen:
            name = match.group("name")
            seen.add(name)
            devices.append(AudioDevice(index=name, name=name))
    return devices


def parse_pulse_devices(output: str) -> list[AudioDevice]:
    devices: list[AudioDevice] = []
    for line in output.splitlines():
        fields = line.split()
        if len(fields) >= 2 and fields[0].isdigit():
            devices.append(AudioDevice(index=fields[1], name=fields[1]))
    return devices


def parse_alsa_devices(output: str) -> list[AudioDevice]:
    devices: list[AudioDevice] = []
    for line in output.splitlines():
        match = re.search(
            r"card (?P<card>\d+): (?P<name>.+?), device (?P<device>\d+):", line
        )
        if match:
            index = f"hw:{match.group('card')},{match.group('device')}"
            devices.append(AudioDevice(index=index, name=match.group("name").strip()))
    return devices


def list_audio_devices(
    ffmpeg: str,
    *,
    backend: str | AudioBackend | None = None,
    timeout: float = 8.0,
) -> list[AudioDevice]:
    selected = (
        backend if isinstance(backend, AudioBackend) else resolve_audio_backend(backend)
    )
    if selected is AudioBackend.PULSE:
        return _list_command(
            ["pactl", "list", "sources", "short"], parse_pulse_devices, timeout
        )
    if selected is AudioBackend.ALSA:
        return _list_command(["arecord", "-l"], parse_alsa_devices, timeout)
    command = [
        ffmpeg,
        "-hide_banner",
        "-f",
        selected.value,
        "-list_devices",
        "true",
        "-i",
    ]
    command.append("" if selected is AudioBackend.AVFOUNDATION else "dummy")
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as error:
        raise RuntimeError(f"No se encontró ffmpeg: {ffmpeg}") from error
    except subprocess.TimeoutExpired as error:
        raise RuntimeError("ffmpeg no respondió al enumerar dispositivos") from error
    output = result.stderr + "\n" + result.stdout
    return (
        parse_avfoundation_devices(output)
        if selected is AudioBackend.AVFOUNDATION
        else parse_dshow_devices(output)
    )


def _list_command(
    command: list[str],
    parser: Callable[[str], list[AudioDevice]],
    timeout: float,
) -> list[AudioDevice]:
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as error:
        raise RuntimeError(f"No se encontró {command[0]}.") from error
    except subprocess.TimeoutExpired as error:
        raise RuntimeError(f"{command[0]} no respondió.") from error
    return parser(result.stdout + "\n" + result.stderr)


def probe_microphone(
    ffmpeg: str,
    device: str,
    *,
    backend: str | AudioBackend | None = None,
    timeout: float = 8.0,
) -> tuple[bool, str]:
    """Attempt a short, discarded capture to verify permission and access."""
    try:
        selected = (
            backend
            if isinstance(backend, AudioBackend)
            else resolve_audio_backend(backend)
        )
        command = [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
        ]
        command.extend(ffmpeg_audio_input(device, selected))
        command.extend(
            [
                "-t",
                "0.25",
                "-vn",
                "-f",
                "null",
                "-",
            ]
        )
        result = subprocess.run(
            command,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError:
        return False, "ffmpeg no está instalado"
    except subprocess.TimeoutExpired:
        return False, "la prueba del micrófono excedió el tiempo límite"
    if result.returncode == 0:
        return True, "captura breve completada"
    detail = (result.stderr or result.stdout).strip().splitlines()
    return False, detail[-1] if detail else f"{selected.value} rechazó la captura"
