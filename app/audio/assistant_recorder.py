"""Background Assistant launcher and recoverable chunked audio storage."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path

from app.audio.recorder import (
    RecorderError,
    StopResult,
    _process_command,
    _process_exists,
    _tail,
    _wait_until_stopped,
)
from app.config import Settings
from app.platform_support import (
    AudioBackend,
    detached_process_options,
    ffmpeg_audio_input,
    signal_process_group,
)


class AssistantRecorder:
    """Launches one Python worker; that worker owns the only ffmpeg capture."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.chunks = ChunkAudioStore(settings)

    def start(
        self,
        audio_path: Path,
        device: str,
        log_path: Path,
        *,
        system_device: str | None = None,
    ) -> int:
        if system_device is not None:
            raise RecorderError(
                "La captura de audio del sistema está disponible solo en record mode."
            )
        session_id = audio_path.stem
        self.chunks.prepare(session_id)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        command = [
            sys.executable,
            "-m",
            "app.assistant.worker",
            "--session-id",
            session_id,
            "--device",
            device,
        ]
        try:
            with log_path.open("ab") as log_file:
                process = subprocess.Popen(
                    command,
                    stdin=subprocess.DEVNULL,
                    stdout=log_file,
                    stderr=log_file,
                    **detached_process_options(),
                )
        except OSError as error:
            raise RecorderError(f"No se pudo iniciar Assistant: {error}") from error

        time.sleep(0.5)
        exit_code = process.poll()
        if exit_code is not None:
            detail = _tail(log_path)
            raise RecorderError(
                f"Assistant terminó al iniciar (código {exit_code}). {detail}".strip()
            )
        return process.pid

    def is_active(self, pid: int | None, audio_path: Path) -> bool:
        if not pid or not _process_exists(pid):
            return False
        command = _process_command(pid)
        return "app.assistant.worker" in command and audio_path.stem in command

    def stop(self, pid: int, audio_path: Path, *, timeout: float = 75.0) -> StopResult:
        if not self.is_active(pid, audio_path):
            return StopResult(stopped=False)
        try:
            signal_process_group(pid)
        except ProcessLookupError:
            return StopResult(stopped=True)
        except PermissionError as error:
            raise RecorderError(
                "El sistema operativo rechazó la señal de cierre para Assistant."
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
                "El sistema operativo rechazó la finalización de Assistant."
            ) from error
        return StopResult(stopped=_wait_until_stopped(pid, 3.0), forced=True)

    def recover_audio(self, audio_path: Path) -> bool:
        self.chunks.stop_orphan_capture(audio_path.stem)
        return self.chunks.finalize(audio_path.stem, audio_path)


class ChunkAudioStore:
    def __init__(
        self,
        settings: Settings,
        *,
        runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    ) -> None:
        self.settings = settings
        self.runner = runner

    def directory(self, session_id: str) -> Path:
        return self.settings.recordings_dir / ".chunks" / session_id

    def prepare(self, session_id: str) -> Path:
        directory = self.directory(session_id)
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    def pattern(self, session_id: str) -> Path:
        return self.directory(session_id) / "%06d.flac"

    def pid_path(self, session_id: str) -> Path:
        return self.directory(session_id) / "ffmpeg.pid"

    def chunks_for(self, session_id: str) -> list[Path]:
        return sorted(
            path
            for path in self.directory(session_id).glob(
                "[0-9][0-9][0-9][0-9][0-9][0-9].flac"
            )
            if path.is_file() and path.stat().st_size > 0
        )

    def completed_chunks(self, session_id: str, *, capture_active: bool) -> list[Path]:
        chunks = self.chunks_for(session_id)
        return chunks[:-1] if capture_active and chunks else chunks

    def finalize(self, session_id: str, audio_path: Path) -> bool:
        if audio_path.exists() and audio_path.stat().st_size > 0:
            self._cleanup(session_id)
            return True
        chunks = self.chunks_for(session_id)
        if not chunks:
            return False

        temporary = audio_path.with_name(f".{audio_path.name}.tmp.flac")
        temporary.unlink(missing_ok=True)
        if len(chunks) == 1:
            temporary.write_bytes(chunks[0].read_bytes())
        else:
            concat_path = self.directory(session_id) / "concat.txt"
            concat_path.write_text(
                "".join(
                    f"file '{_concat_escape(path.resolve())}'\n" for path in chunks
                ),
                encoding="utf-8",
            )
            command = [
                self.settings.ffmpeg,
                "-nostdin",
                "-hide_banner",
                "-loglevel",
                "error",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_path),
                "-c:a",
                "flac",
                "-compression_level",
                "5",
                "-y",
                str(temporary),
            ]
            result = self.runner(
                command,
                capture_output=True,
                text=True,
                check=False,
                timeout=120,
            )
            if result.returncode != 0:
                temporary.unlink(missing_ok=True)
                raise RecorderError(
                    f"No se pudieron unir los chunks: {result.stderr[-400:].strip()}"
                )
        os.replace(temporary, audio_path)
        self._cleanup(session_id)
        return audio_path.exists() and audio_path.stat().st_size > 0

    def stop_orphan_capture(self, session_id: str) -> None:
        pid_path = self.pid_path(session_id)
        try:
            pid = int(pid_path.read_text(encoding="ascii").strip())
        except (OSError, ValueError):
            return
        command = _process_command(pid)
        if not command or str(self.directory(session_id)) not in command:
            return
        try:
            signal_process_group(pid)
        except (ProcessLookupError, PermissionError):
            return
        _wait_until_stopped(pid, 5.0)

    def _cleanup(self, session_id: str) -> None:
        directory = self.directory(session_id)
        for path in self.chunks_for(session_id):
            path.unlink(missing_ok=True)
        for name in ("concat.txt", "ffmpeg.pid"):
            (directory / name).unlink(missing_ok=True)
        try:
            directory.rmdir()
            directory.parent.rmdir()
        except OSError:
            pass


class ChunkedFFmpegCapture:
    def __init__(self, settings: Settings, store: ChunkAudioStore) -> None:
        self.settings = settings
        self.store = store

    def start(
        self,
        session_id: str,
        *,
        device: str,
        chunk_seconds: int,
        log_path: Path,
    ) -> subprocess.Popen[bytes]:
        self.store.prepare(session_id)
        command = [
            self.settings.ffmpeg,
            "-nostdin",
            "-hide_banner",
            "-loglevel",
            "warning",
        ]
        command.extend(
            ffmpeg_audio_input(device, AudioBackend(self.settings.audio_backend))
        )
        command.extend(
            [
                "-vn",
                "-ac",
                "1",
                "-ar",
                "16000",
                "-c:a",
                "flac",
                "-compression_level",
                "5",
                "-f",
                "segment",
                "-segment_time",
                str(chunk_seconds),
                "-reset_timestamps",
                "1",
                "-y",
                str(self.store.pattern(session_id)),
            ]
        )
        try:
            log_file = log_path.open("ab")
            process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=log_file,
                **detached_process_options(),
            )
            log_file.close()
        except OSError as error:
            raise RecorderError(
                f"No se pudo iniciar ffmpeg por chunks: {error}"
            ) from error
        self.store.pid_path(session_id).write_text(str(process.pid), encoding="ascii")
        time.sleep(0.35)
        if process.poll() is not None:
            raise RecorderError(
                f"ffmpeg por chunks terminó al iniciar. {_tail(log_path)}".strip()
            )
        return process

    @staticmethod
    def stop(process: subprocess.Popen[bytes], *, timeout: float = 10.0) -> None:
        if process.poll() is not None:
            return
        try:
            signal_process_group(process.pid)
        except ProcessLookupError:
            return
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            signal_process_group(process.pid, force=True)
            try:
                process.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2.0)


def _concat_escape(path: Path) -> str:
    return str(path).replace("'", "'\\''")
