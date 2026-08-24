"""Small sqlite3 wrapper with explicit durability settings."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from app.local_config import secure_directory, secure_file

LEGACY_MODE = "copilot"
LEGACY_UPDATES_TABLE = "copilot_updates"
LEGACY_COLUMNS = {
    "assistant_chunk_seconds": "copilot_chunk_seconds",
    "assistant_analysis_interval_seconds": "copilot_analysis_interval_seconds",
    "assistant_last_segments": "copilot_last_segments",
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    created_at TEXT NOT NULL,
    started_at TEXT,
    ended_at TEXT,
    mode TEXT NOT NULL,
    status TEXT NOT NULL,
    audio_path TEXT NOT NULL,
    system_audio_path TEXT,
    system_audio_device TEXT,
    guide_path TEXT,
    assistant_chunk_seconds INTEGER,
    assistant_analysis_interval_seconds INTEGER,
    assistant_last_segments INTEGER,
    recording_pid INTEGER,
    local_only INTEGER NOT NULL DEFAULT 0,
    error_message TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS one_active_session
ON sessions ((1))
WHERE status IN ('starting', 'recording', 'stopping');

CREATE INDEX IF NOT EXISTS sessions_created_at
ON sessions (created_at DESC);

CREATE TABLE IF NOT EXISTS transcript_segments (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    position INTEGER NOT NULL,
    speaker TEXT NOT NULL,
    start REAL NOT NULL,
    end REAL NOT NULL,
    text TEXT NOT NULL,
    confidence REAL,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    UNIQUE (session_id, position)
);

CREATE INDEX IF NOT EXISTS transcript_segments_session_start
ON transcript_segments (session_id, start, position);

CREATE TABLE IF NOT EXISTS analyses (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    type TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL,
    model TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    UNIQUE (session_id, type)
);

CREATE INDEX IF NOT EXISTS analyses_session_created_at
ON analyses (session_id, created_at);

CREATE TABLE IF NOT EXISTS assistant_updates (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    rolling_summary TEXT NOT NULL,
    asked_questions TEXT NOT NULL,
    pending_questions TEXT NOT NULL,
    suggested_question TEXT NOT NULL,
    rationale TEXT NOT NULL,
    segment_count INTEGER NOT NULL,
    through_end REAL NOT NULL,
    created_at TEXT NOT NULL,
    model TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS assistant_updates_session_created_at
ON assistant_updates (session_id, created_at DESC);
"""


SESSION_MIGRATIONS = {
    "system_audio_path": "TEXT",
    "system_audio_device": "TEXT",
    "guide_path": "TEXT",
    "assistant_chunk_seconds": "INTEGER",
    "assistant_analysis_interval_seconds": "INTEGER",
    "assistant_last_segments": "INTEGER",
}


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path

    def connect(self) -> sqlite3.Connection:
        secure_directory(self.path.parent)
        connection = sqlite3.connect(self.path, timeout=5.0)
        secure_file(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = NORMAL")
        return connection

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(SCHEMA)
            existing = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(sessions)").fetchall()
            }
            for name, declaration in SESSION_MIGRATIONS.items():
                if name not in existing:
                    connection.execute(
                        f"ALTER TABLE sessions ADD COLUMN {name} {declaration}"
                    )
            updated = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(sessions)").fetchall()
            }
            for current, legacy in LEGACY_COLUMNS.items():
                if legacy in updated:
                    connection.execute(
                        f"UPDATE sessions SET {current} = COALESCE({current}, {legacy})"
                    )
            connection.execute(
                "UPDATE sessions SET mode = ? WHERE mode = ?",
                ("assistant", LEGACY_MODE),
            )
            tables = {
                row["name"]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
            }
            if LEGACY_UPDATES_TABLE in tables:
                connection.execute(
                    f"""
                    INSERT OR IGNORE INTO assistant_updates
                    SELECT * FROM {LEGACY_UPDATES_TABLE}
                    """
                )

    @contextmanager
    def transaction(self, *, immediate: bool = False) -> Iterator[sqlite3.Connection]:
        connection = self.connect()
        try:
            connection.execute("BEGIN IMMEDIATE" if immediate else "BEGIN")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
