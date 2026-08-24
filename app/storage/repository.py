"""Session persistence with no recording or UI concerns."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from app.sessions.models import ACTIVE_STATUSES, Session, SessionMode, SessionStatus
from app.storage.database import Database


class ActiveSessionError(RuntimeError):
    pass


class SessionNotFoundError(RuntimeError):
    pass


class SessionRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def create_starting(
        self,
        *,
        session_id: str,
        title: str,
        mode: SessionMode,
        audio_path: Path,
        system_audio_path: Path | None,
        system_audio_device: str | None,
        local_only: bool,
        guide_path: Path | None = None,
        assistant_chunk_seconds: int | None = None,
        assistant_analysis_interval_seconds: int | None = None,
        assistant_last_segments: int | None = None,
    ) -> Session:
        now = datetime.now(UTC)
        try:
            with self.database.transaction(immediate=True) as connection:
                connection.execute(
                    """
                    INSERT INTO sessions (
                        id, title, created_at, started_at, mode, status,
                        audio_path, system_audio_path, system_audio_device, local_only,
                        guide_path, assistant_chunk_seconds,
                        assistant_analysis_interval_seconds, assistant_last_segments
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session_id,
                        title,
                        now.isoformat(),
                        now.isoformat(),
                        mode.value,
                        SessionStatus.STARTING.value,
                        str(audio_path),
                        str(system_audio_path) if system_audio_path else None,
                        system_audio_device,
                        int(local_only),
                        str(guide_path) if guide_path else None,
                        assistant_chunk_seconds,
                        assistant_analysis_interval_seconds,
                        assistant_last_segments,
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise ActiveSessionError("Ya existe una sesión activa.") from error
        return self.get(session_id)

    def create_completed_import(
        self,
        *,
        session_id: str,
        title: str,
        audio_path: Path,
    ) -> Session:
        """Persist an already finalized local recording as a completed session."""
        now = datetime.now(UTC).isoformat()
        with self.database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO sessions (
                    id, title, created_at, started_at, ended_at, mode, status,
                    audio_path, local_only
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    title,
                    now,
                    now,
                    now,
                    SessionMode.RECORD.value,
                    SessionStatus.COMPLETED.value,
                    str(audio_path),
                    1,
                ),
            )
        return self.get(session_id)

    def mark_recording(self, session_id: str, pid: int) -> Session:
        with self.database.transaction() as connection:
            cursor = connection.execute(
                "UPDATE sessions SET status = ?, recording_pid = ? WHERE id = ?",
                (SessionStatus.RECORDING.value, pid, session_id),
            )
            if cursor.rowcount != 1:
                raise SessionNotFoundError(session_id)
        return self.get(session_id)

    def set_status(self, session_id: str, status: SessionStatus) -> Session:
        with self.database.transaction() as connection:
            cursor = connection.execute(
                "UPDATE sessions SET status = ? WHERE id = ?",
                (status.value, session_id),
            )
            if cursor.rowcount != 1:
                raise SessionNotFoundError(session_id)
        return self.get(session_id)

    def finish(
        self,
        session_id: str,
        status: SessionStatus,
        *,
        error_message: str | None = None,
    ) -> Session:
        ended_at = datetime.now(UTC).isoformat()
        with self.database.transaction() as connection:
            cursor = connection.execute(
                """
                UPDATE sessions
                SET status = ?, ended_at = ?, recording_pid = NULL, error_message = ?
                WHERE id = ?
                """,
                (status.value, ended_at, error_message, session_id),
            )
            if cursor.rowcount != 1:
                raise SessionNotFoundError(session_id)
        return self.get(session_id)

    def get(self, session_id: str) -> Session:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM sessions WHERE id = ?", (session_id,)
            ).fetchone()
        if row is None:
            raise SessionNotFoundError(session_id)
        return _to_session(row)

    def get_active(self) -> Session | None:
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM sessions
                WHERE status IN (?, ?, ?)
                ORDER BY created_at DESC LIMIT 1
                """,
                tuple(status.value for status in ACTIVE_STATUSES),
            ).fetchone()
        return _to_session(row) if row else None

    def list_active(self) -> list[Session]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM sessions
                WHERE status IN (?, ?, ?)
                ORDER BY created_at
                """,
                tuple(status.value for status in ACTIVE_STATUSES),
            ).fetchall()
        return [_to_session(row) for row in rows]

    def list(self, *, limit: int = 100) -> list[Session]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM sessions ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [_to_session(row) for row in rows]


def _to_session(row: sqlite3.Row) -> Session:
    return Session(
        id=row["id"],
        title=row["title"],
        created_at=datetime.fromisoformat(row["created_at"]),
        started_at=(
            datetime.fromisoformat(row["started_at"]) if row["started_at"] else None
        ),
        ended_at=datetime.fromisoformat(row["ended_at"]) if row["ended_at"] else None,
        mode=SessionMode(row["mode"]),
        status=SessionStatus(row["status"]),
        audio_path=Path(row["audio_path"]),
        system_audio_path=(
            Path(row["system_audio_path"]) if row["system_audio_path"] else None
        ),
        system_audio_device=row["system_audio_device"],
        guide_path=Path(row["guide_path"]) if row["guide_path"] else None,
        assistant_chunk_seconds=row["assistant_chunk_seconds"],
        assistant_analysis_interval_seconds=row["assistant_analysis_interval_seconds"],
        assistant_last_segments=row["assistant_last_segments"],
        recording_pid=row["recording_pid"],
        local_only=bool(row["local_only"]),
        error_message=row["error_message"],
    )
