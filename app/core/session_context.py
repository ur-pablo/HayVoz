"""Stable, fact-only context contract for local and external consumers."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from app.config import Settings
from app.sessions.guide import InterviewGuideError, InterviewGuideStore
from app.sessions.models import Session
from app.storage.repository import SessionNotFoundError, SessionRepository
from app.storage.transcript_repository import TranscriptRepository


class SessionContextError(RuntimeError):
    """Raised when a local session context cannot be read safely."""


class SessionContextService:
    """Expose persisted HayVoz facts without exposing storage implementation."""

    def __init__(
        self,
        settings: Settings,
        sessions: SessionRepository,
        transcripts: TranscriptRepository,
        guides: InterviewGuideStore | None = None,
    ) -> None:
        self.settings = settings
        self.sessions = sessions
        self.transcripts = transcripts
        self.guides = guides or InterviewGuideStore(settings)

    def list_sessions(self, *, limit: int = 100) -> list[dict[str, Any]]:
        if limit < 1 or limit > 1000:
            raise SessionContextError("limit debe estar entre 1 y 1000.")
        return [
            self._session_view(session) for session in self.sessions.list(limit=limit)
        ]

    def get_session(self, session_id: str) -> dict[str, Any]:
        return self._session_view(self._get_session(session_id))

    def get_transcript(self, session_id: str) -> list[dict[str, Any]]:
        self._get_session(session_id)
        return [
            self._segment_view(segment)
            for segment in self.transcripts.list_for_session(session_id)
        ]

    def get_recent_segments(
        self, session_id: str, *, limit: int = 20
    ) -> list[dict[str, Any]]:
        if limit < 1 or limit > 1000:
            raise SessionContextError("limit debe estar entre 1 y 1000.")
        self._get_session(session_id)
        return [
            self._segment_view(segment)
            for segment in self.transcripts.list_recent_for_session(
                session_id, limit=limit
            )
        ]

    def get_interview_guide(self, session_id: str) -> dict[str, str] | None:
        session = self._get_session(session_id)
        if session.guide_path is None:
            return None
        guide_path = self._safe_guide_path(session.guide_path)
        try:
            content = self.guides.read(guide_path)
        except InterviewGuideError as error:
            raise SessionContextError(str(error)) from error
        if content is None:
            return None
        return {"title": guide_path.stem, "content": content}

    def get_session_context(
        self, session_id: str, *, recent_segments: int = 20
    ) -> dict[str, Any]:
        return {
            "session": self.get_session(session_id),
            "guide": self.get_interview_guide(session_id),
            "recent_segments": self.get_recent_segments(
                session_id, limit=recent_segments
            ),
        }

    def _get_session(self, session_id: str) -> Session:
        if not session_id.strip():
            raise SessionContextError("session_id no puede estar vacío.")
        try:
            return self.sessions.get(session_id)
        except SessionNotFoundError as error:
            raise SessionContextError(f"No existe la sesión {session_id}.") from error

    def _safe_guide_path(self, path: Path) -> Path:
        root = self.settings.guides_dir.expanduser().resolve()
        candidate = path.expanduser().resolve()
        try:
            candidate.relative_to(root)
        except ValueError as error:
            raise SessionContextError(
                "La guía de la sesión está fuera del directorio privado de guías."
            ) from error
        return candidate

    @staticmethod
    def _session_view(session: Session) -> dict[str, Any]:
        return {
            "id": session.id,
            "title": session.title,
            "created_at": _isoformat(session.created_at),
            "started_at": _isoformat(session.started_at),
            "ended_at": _isoformat(session.ended_at),
            "mode": session.mode.value,
            "status": session.status.value,
            "local_only": session.local_only,
            "has_guide": session.guide_path is not None,
        }

    @staticmethod
    def _segment_view(segment: Any) -> dict[str, Any]:
        return {
            "id": segment.id,
            "speaker": segment.speaker.value,
            "start": segment.start,
            "end": segment.end,
            "text": segment.text,
            "confidence": segment.confidence,
        }


def _isoformat(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None
