"""Transactional persistence for generated analyses."""

from __future__ import annotations

import sqlite3
from datetime import datetime

from app.analysis.models import Analysis, AnalysisType
from app.storage.database import Database


class AnalysisRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def replace_for_session(
        self,
        session_id: str,
        analyses: list[Analysis],
    ) -> None:
        if any(analysis.session_id != session_id for analysis in analyses):
            raise ValueError("Todos los análisis deben pertenecer a la sesión.")
        if len({analysis.type for analysis in analyses}) != len(analyses):
            raise ValueError("No puede repetirse un tipo de análisis.")
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                "DELETE FROM analyses WHERE session_id = ?", (session_id,)
            )
            connection.executemany(
                """
                INSERT INTO analyses (
                    id, session_id, type, content, created_at, model
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        analysis.id,
                        session_id,
                        analysis.type.value,
                        analysis.content,
                        analysis.created_at.isoformat(),
                        analysis.model,
                    )
                    for analysis in analyses
                ],
            )

    def list_for_session(self, session_id: str) -> list[Analysis]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT id, session_id, type, content, created_at, model
                FROM analyses
                WHERE session_id = ?
                ORDER BY created_at, type
                """,
                (session_id,),
            ).fetchall()
        return [_to_analysis(row) for row in rows]

    def get_for_type(
        self,
        session_id: str,
        analysis_type: AnalysisType,
    ) -> Analysis | None:
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT id, session_id, type, content, created_at, model
                FROM analyses
                WHERE session_id = ? AND type = ?
                """,
                (session_id, analysis_type.value),
            ).fetchone()
        return _to_analysis(row) if row else None


def _to_analysis(row: sqlite3.Row) -> Analysis:
    return Analysis(
        id=row["id"],
        session_id=row["session_id"],
        type=AnalysisType(row["type"]),
        content=row["content"],
        created_at=datetime.fromisoformat(row["created_at"]),
        model=row["model"],
    )
