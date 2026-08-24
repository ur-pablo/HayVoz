"""SQLite persistence for incremental Assistant suggestions."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime

from app.assistant.models import AssistantUpdate
from app.storage.database import Database


class AssistantRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def add(self, update: AssistantUpdate) -> None:
        with self.database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO assistant_updates (
                    id, session_id, rolling_summary, asked_questions,
                    pending_questions, suggested_question, rationale,
                    segment_count, through_end, created_at, model
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    update.id,
                    update.session_id,
                    update.rolling_summary,
                    json.dumps(update.asked_questions, ensure_ascii=False),
                    json.dumps(update.pending_questions, ensure_ascii=False),
                    update.suggested_question,
                    update.rationale,
                    update.segment_count,
                    update.through_end,
                    update.created_at.isoformat(),
                    update.model,
                ),
            )

    def latest(self, session_id: str) -> AssistantUpdate | None:
        updates = self.list_for_session(session_id, limit=1)
        return updates[0] if updates else None

    def list_for_session(
        self, session_id: str, *, limit: int = 20
    ) -> list[AssistantUpdate]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM assistant_updates
                WHERE session_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (session_id, limit),
            ).fetchall()
        return [_to_update(row) for row in rows]


def _to_update(row: sqlite3.Row) -> AssistantUpdate:
    return AssistantUpdate(
        id=row["id"],
        session_id=row["session_id"],
        rolling_summary=row["rolling_summary"],
        asked_questions=json.loads(row["asked_questions"]),
        pending_questions=json.loads(row["pending_questions"]),
        suggested_question=row["suggested_question"],
        rationale=row["rationale"],
        segment_count=row["segment_count"],
        through_end=row["through_end"],
        created_at=datetime.fromisoformat(row["created_at"]),
        model=row["model"],
    )
