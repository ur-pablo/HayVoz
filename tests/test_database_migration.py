import sqlite3

from app.storage.database import Database


def test_old_database_gains_new_session_columns(tmp_path) -> None:
    path = tmp_path / "database.sqlite"
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE sessions (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                started_at TEXT,
                ended_at TEXT,
                mode TEXT NOT NULL,
                status TEXT NOT NULL,
                audio_path TEXT NOT NULL,
                recording_pid INTEGER,
                local_only INTEGER NOT NULL DEFAULT 0,
                error_message TEXT
            )
            """
        )

    Database(path).initialize()

    with sqlite3.connect(path) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(sessions)")}
    assert {
        "guide_path",
        "system_audio_path",
        "system_audio_device",
        "assistant_chunk_seconds",
        "assistant_analysis_interval_seconds",
        "assistant_last_segments",
    } <= columns


def test_legacy_assistant_data_is_copied_transactionally(tmp_path) -> None:
    path = tmp_path / "database.sqlite"
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE sessions (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                started_at TEXT,
                ended_at TEXT,
                mode TEXT NOT NULL,
                status TEXT NOT NULL,
                audio_path TEXT NOT NULL,
                copilot_chunk_seconds INTEGER,
                copilot_analysis_interval_seconds INTEGER,
                copilot_last_segments INTEGER,
                recording_pid INTEGER,
                local_only INTEGER NOT NULL DEFAULT 0,
                error_message TEXT
            );
            CREATE TABLE copilot_updates (
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
                model TEXT NOT NULL
            );
            """
        )
        connection.execute(
            """
            INSERT INTO sessions (
                id, title, created_at, mode, status, audio_path,
                copilot_chunk_seconds, copilot_analysis_interval_seconds,
                copilot_last_segments
            ) VALUES ('session-1', 'Legacy', '2026-01-01T00:00:00+00:00',
                      'copilot', 'completed', '/tmp/audio.flac', 15, 60, 20)
            """
        )
        connection.execute(
            """
            INSERT INTO copilot_updates VALUES (
                'update-1', 'session-1', 'summary', '[]', '[]', 'question',
                'reason', 1, 1.0, '2026-01-01T00:01:00+00:00', 'model'
            )
            """
        )

    Database(path).initialize()

    with sqlite3.connect(path) as connection:
        session = connection.execute(
            """
            SELECT mode, assistant_chunk_seconds,
                   assistant_analysis_interval_seconds, assistant_last_segments
            FROM sessions WHERE id = 'session-1'
            """
        ).fetchone()
        update = connection.execute(
            "SELECT suggested_question FROM assistant_updates WHERE id = 'update-1'"
        ).fetchone()
    assert session == ("assistant", 15, 60, 20)
    assert update == ("question",)
