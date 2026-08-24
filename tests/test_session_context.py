from __future__ import annotations

import pytest

from app.core.session_context import SessionContextError, SessionContextService
from app.sessions.service import SessionService
from app.storage.transcript_repository import TranscriptRepository
from app.transcription.models import Speaker, TranscriptSegment
from tests.fakes import FakeRecorder


def _context(settings, repository) -> SessionContextService:
    return SessionContextService(
        settings,
        repository,
        TranscriptRepository(repository.database),
    )


def test_session_context_reads_fact_only_session_guide_and_recent_segments(
    settings, repository, tmp_path
) -> None:
    guide = tmp_path / "guide.md"
    guide.write_text("# Discovery\n\n- Ask why\n", encoding="utf-8")
    recorder = FakeRecorder()
    lifecycle = SessionService(settings, repository, recorder)
    session = lifecycle.start(
        title="Discovery interview",
        guide=guide,
        local_only=True,
    )
    lifecycle.stop()
    transcripts = TranscriptRepository(repository.database)
    transcripts.append_for_session(
        session.id,
        [
            TranscriptSegment(
                session_id=session.id,
                speaker=Speaker.INTERVIEWER,
                start=120.3,
                end=125.6,
                text="¿Cómo lo haces hoy?",
            ),
            TranscriptSegment(
                session_id=session.id,
                speaker=Speaker.INTERVIEWEE,
                start=126.1,
                end=145.2,
                text="Pregunto por Teams.",
            ),
        ],
    )

    context = _context(settings, repository)
    value = context.get_session_context(session.id, recent_segments=1)

    assert value["session"]["title"] == "Discovery interview"
    assert value["session"]["status"] == "completed"
    assert value["guide"] == {
        "title": session.id,
        "content": "# Discovery\n\n- Ask why\n",
    }
    assert [item["text"] for item in value["recent_segments"]] == [
        "Pregunto por Teams."
    ]
    assert "audio_path" not in value["session"]


def test_session_context_rejects_unknown_session(settings, repository) -> None:
    context = _context(settings, repository)

    with pytest.raises(SessionContextError, match="No existe"):
        context.get_session("missing")


def test_session_context_returns_empty_transcript(settings, repository) -> None:
    lifecycle = SessionService(settings, repository, FakeRecorder())
    session = lifecycle.start(title="Sin transcript", local_only=True)
    lifecycle.stop()

    assert _context(settings, repository).get_transcript(session.id) == []


def test_session_context_rejects_guide_path_outside_private_directory(
    settings, repository, tmp_path
) -> None:
    session = SessionService(settings, repository, FakeRecorder()).start(
        title="Path safety", local_only=True
    )
    SessionService(settings, repository, FakeRecorder()).stop()
    with repository.database.transaction() as connection:
        connection.execute(
            "UPDATE sessions SET guide_path = ? WHERE id = ?",
            (str(tmp_path / "outside.md"), session.id),
        )

    with pytest.raises(SessionContextError, match="fuera"):
        _context(settings, repository).get_interview_guide(session.id)
