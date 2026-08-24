"""Transactional session lifecycle independent of the CLI."""

from __future__ import annotations

import logging
from pathlib import Path
from uuid import uuid4

from app.audio.recorder import Recorder, RecorderError, system_audio_path_for
from app.config import Settings
from app.sessions.guide import InterviewGuideError, InterviewGuideStore
from app.sessions.models import Session, SessionMode, SessionStatus
from app.storage.repository import SessionRepository

logger = logging.getLogger(__name__)


class SessionServiceError(RuntimeError):
    pass


class SessionService:
    def __init__(
        self,
        settings: Settings,
        repository: SessionRepository,
        recorder: Recorder,
        assistant_recorder: Recorder | None = None,
    ) -> None:
        self.settings = settings
        self.repository = repository
        self.recorder = recorder
        self.assistant_recorder = assistant_recorder or recorder
        self.guide_store = InterviewGuideStore(settings)

    def start(
        self,
        *,
        title: str,
        mode: SessionMode = SessionMode.RECORD,
        device: str | None = None,
        system_device: str | None = None,
        local_only: bool = False,
        guide: Path | None = None,
        allow_external: bool = False,
        assistant_chunk_seconds: int | None = None,
        assistant_analysis_interval_seconds: int | None = None,
        assistant_last_segments: int | None = None,
    ) -> Session:
        if not title.strip():
            raise SessionServiceError("El título no puede estar vacío.")
        if mode is SessionMode.ASSISTANT and not local_only and not allow_external:
            raise SessionServiceError(
                "Assistant requiere --confirm-send o --local-only para evitar envíos "
                "accidentales."
            )
        if local_only and allow_external:
            raise SessionServiceError(
                "--local-only y --confirm-send son mutuamente excluyentes."
            )
        selected_device = (device or self.settings.default_audio_device).strip()
        if not selected_device:
            raise SessionServiceError("--device no puede estar vacío.")
        selected_system_device = (
            system_device.strip() or None if system_device is not None else None
        )
        if selected_system_device and mode is SessionMode.ASSISTANT:
            raise SessionServiceError(
                "--system-device está disponible solo en record mode."
            )
        if selected_system_device == selected_device:
            raise SessionServiceError(
                "--device y --system-device deben ser fuentes diferentes."
            )

        chunk_seconds: int | None = None
        analysis_interval: int | None = None
        last_segments: int | None = None
        if mode is SessionMode.ASSISTANT:
            chunk_seconds = (
                assistant_chunk_seconds
                if assistant_chunk_seconds is not None
                else self.settings.assistant_chunk_seconds
            )
            analysis_interval = (
                assistant_analysis_interval_seconds
                if assistant_analysis_interval_seconds is not None
                else self.settings.assistant_analysis_interval_seconds
            )
            last_segments = (
                assistant_last_segments
                if assistant_last_segments is not None
                else self.settings.assistant_last_segments
            )
            if not 10 <= chunk_seconds <= 20:
                raise SessionServiceError(
                    "Los chunks deben durar entre 10 y 20 segundos."
                )
            if analysis_interval < chunk_seconds:
                raise SessionServiceError(
                    "El intervalo de análisis no puede ser menor que el chunk."
                )
            if last_segments < 1:
                raise SessionServiceError("El rolling context requiere segmentos.")

        self.recover_orphans()
        session_id = str(uuid4())
        audio_path = self.settings.recordings_dir / f"{session_id}.flac"
        system_audio_path = (
            system_audio_path_for(audio_path) if selected_system_device else None
        )
        try:
            guide_path = self.guide_store.copy_for_session(session_id, guide)
        except InterviewGuideError as error:
            raise SessionServiceError(str(error)) from error
        self.repository.create_starting(
            session_id=session_id,
            title=title.strip(),
            mode=mode,
            audio_path=audio_path,
            system_audio_path=system_audio_path,
            system_audio_device=selected_system_device,
            local_only=local_only,
            guide_path=guide_path,
            assistant_chunk_seconds=chunk_seconds,
            assistant_analysis_interval_seconds=analysis_interval,
            assistant_last_segments=last_segments,
        )
        log_path = self.settings.logs_dir / f"recorder-{session_id}.log"
        recorder = self._recorder_for(mode)
        try:
            pid = recorder.start(
                audio_path,
                selected_device,
                log_path,
                system_device=selected_system_device,
            )
        except RecorderError as error:
            self.repository.finish(
                session_id,
                SessionStatus.FAILED,
                error_message=str(error),
            )
            logger.error(
                "recorder_start_failed",
                extra={"event": "recorder_start_failed", "session_id": session_id},
            )
            raise SessionServiceError(str(error)) from error

        try:
            result = self.repository.mark_recording(session_id, pid)
        except Exception:
            recorder.stop(pid, audio_path)
            self.repository.finish(
                session_id,
                SessionStatus.FAILED,
                error_message="No se pudo persistir el PID del grabador.",
            )
            raise
        logger.info(
            "recording_started",
            extra={"event": "recording_started", "session_id": session_id},
        )
        return result

    def stop(self) -> Session:
        active = self.repository.get_active()
        if active is None:
            self.recover_orphans()
            raise SessionServiceError("No hay una sesión activa.")
        if active.recording_pid is None:
            return self.repository.finish(
                active.id,
                SessionStatus.FAILED,
                error_message="La sesión activa no tenía PID de grabación.",
            )

        self.repository.set_status(active.id, SessionStatus.STOPPING)
        recorder = self._recorder_for(active.mode)
        try:
            result = recorder.stop(
                active.recording_pid,
                active.audio_path,
                timeout=75.0 if active.mode is SessionMode.ASSISTANT else 10.0,
            )
        except RecorderError as error:
            complete_audio, any_audio = self._audio_health(active, recorder)
            self.repository.finish(
                active.id,
                SessionStatus.INTERRUPTED if any_audio else SessionStatus.FAILED,
                error_message=str(error),
            )
            raise SessionServiceError(str(error)) from error
        complete_audio, any_audio = self._audio_health(active, recorder)
        if result.stopped and complete_audio:
            status = SessionStatus.COMPLETED
            error_message = None
        elif any_audio:
            status = SessionStatus.INTERRUPTED
            error_message = (
                "No se produjeron correctamente ambas fuentes de audio."
                if active.system_audio_path and not complete_audio
                else "No se pudo confirmar el cierre limpio de ffmpeg."
            )
        else:
            status = SessionStatus.FAILED
            error_message = "La grabación terminó sin producir audio."
        finished = self.repository.finish(
            active.id,
            status,
            error_message=error_message,
        )
        logger.info(
            "recording_stopped",
            extra={
                "event": "recording_stopped",
                "session_id": active.id,
                "status": status.value,
            },
        )
        return finished

    def list_sessions(self, *, limit: int = 100) -> list[Session]:
        self.recover_orphans()
        return self.repository.list(limit=limit)

    def recover_orphans(self) -> int:
        recovered = 0
        for session in self.repository.list_active():
            recorder = self._recorder_for(session.mode)
            if recorder.is_active(session.recording_pid, session.audio_path):
                continue
            complete_audio, any_audio = self._audio_health(session, recorder)
            status = SessionStatus.INTERRUPTED if any_audio else SessionStatus.FAILED
            message = (
                "Se recuperó audio después de detectar un grabador detenido."
                if any_audio
                else "El grabador se detuvo antes de producir audio."
            )
            if any_audio and not complete_audio:
                message = "Se recuperó solo una de las dos fuentes de audio."
            self.repository.finish(session.id, status, error_message=message)
            recovered += 1
            logger.warning(
                "orphan_session_recovered",
                extra={
                    "event": "orphan_session_recovered",
                    "session_id": session.id,
                    "status": status.value,
                },
            )
        return recovered

    def _recorder_for(self, mode: SessionMode) -> Recorder:
        return (
            self.assistant_recorder if mode is SessionMode.ASSISTANT else self.recorder
        )

    @staticmethod
    def _has_audio(recorder: Recorder, audio_path: Path) -> bool:
        recover = getattr(recorder, "recover_audio", None)
        if callable(recover):
            try:
                return bool(recover(audio_path))
            except RecorderError:
                return False
        return audio_path.exists() and audio_path.stat().st_size > 0

    @classmethod
    def _audio_health(cls, session: Session, recorder: Recorder) -> tuple[bool, bool]:
        primary = cls._has_audio(recorder, session.audio_path)
        if session.system_audio_path is None:
            return primary, primary
        secondary = (
            session.system_audio_path.exists()
            and session.system_audio_path.stat().st_size > 0
        )
        return primary and secondary, primary or secondary
