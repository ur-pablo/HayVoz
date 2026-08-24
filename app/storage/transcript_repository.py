"""Transactional persistence for transcript segments."""

from __future__ import annotations

import sqlite3

from app.storage.database import Database
from app.transcription.models import Speaker, TranscriptSegment


class TranscriptRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def replace_for_session(
        self, session_id: str, segments: list[TranscriptSegment]
    ) -> None:
        if any(segment.session_id != session_id for segment in segments):
            raise ValueError("Todos los segmentos deben pertenecer a la sesión.")
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                "DELETE FROM transcript_segments WHERE session_id = ?", (session_id,)
            )
            connection.executemany(
                """
                INSERT INTO transcript_segments (
                    id, session_id, position, speaker, start, end, text, confidence
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        segment.id,
                        session_id,
                        position,
                        segment.speaker.value,
                        segment.start,
                        segment.end,
                        segment.text,
                        segment.confidence,
                    )
                    for position, segment in enumerate(segments)
                ],
            )

    def list_for_session(self, session_id: str) -> list[TranscriptSegment]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT id, session_id, speaker, start, end, text, confidence
                FROM transcript_segments
                WHERE session_id = ?
                ORDER BY position
                """,
                (session_id,),
            ).fetchall()
        return [_to_segment(row) for row in rows]

    def append_for_session(
        self,
        session_id: str,
        segments: list[TranscriptSegment],
    ) -> None:
        if any(segment.session_id != session_id for segment in segments):
            raise ValueError("Todos los segmentos deben pertenecer a la sesión.")
        if not segments:
            return
        with self.database.transaction(immediate=True) as connection:
            row = connection.execute(
                """
                SELECT COALESCE(MAX(position), -1) AS last_position
                FROM transcript_segments WHERE session_id = ?
                """,
                (session_id,),
            ).fetchone()
            first_position = int(row["last_position"]) + 1
            connection.executemany(
                """
                INSERT INTO transcript_segments (
                    id, session_id, position, speaker, start, end, text, confidence
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        segment.id,
                        session_id,
                        first_position + offset,
                        segment.speaker.value,
                        segment.start,
                        segment.end,
                        segment.text,
                        segment.confidence,
                    )
                    for offset, segment in enumerate(segments)
                ],
            )

    def list_recent_for_session(
        self,
        session_id: str,
        *,
        limit: int,
    ) -> list[TranscriptSegment]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT id, session_id, speaker, start, end, text, confidence
                FROM (
                    SELECT id, session_id, position, speaker, start, end, text,
                           confidence
                    FROM transcript_segments
                    WHERE session_id = ?
                    ORDER BY position DESC
                    LIMIT ?
                )
                ORDER BY position
                """,
                (session_id, limit),
            ).fetchall()
        return [_to_segment(row) for row in rows]


def _to_segment(row: sqlite3.Row) -> TranscriptSegment:
    return TranscriptSegment(
        id=row["id"],
        session_id=row["session_id"],
        speaker=Speaker(row["speaker"]),
        start=row["start"],
        end=row["end"],
        text=row["text"],
        confidence=row["confidence"],
    )
