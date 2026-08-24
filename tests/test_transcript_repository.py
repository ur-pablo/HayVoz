from app.config import Settings
from app.sessions.service import SessionService
from app.storage.database import Database
from app.storage.repository import SessionRepository
from app.storage.transcript_repository import TranscriptRepository
from app.transcription.models import TranscriptSegment
from tests.fakes import FakeRecorder


def test_replace_segments_is_transactional_and_ordered(
    settings: Settings, repository: SessionRepository
) -> None:
    session_service = SessionService(settings, repository, FakeRecorder())
    session = session_service.start(title="Transcripción")
    session_service.stop()
    transcripts = TranscriptRepository(Database(settings.database_path))

    first = TranscriptSegment(
        session_id=session.id,
        speaker="interviewer",
        start=0,
        end=1,
        text="Primero",
    )
    second = TranscriptSegment(
        session_id=session.id,
        speaker="interviewer",
        start=1,
        end=2,
        text="Segundo",
    )
    transcripts.replace_for_session(session.id, [first, second])
    assert [item.text for item in transcripts.list_for_session(session.id)] == [
        "Primero",
        "Segundo",
    ]

    replacement = TranscriptSegment(
        session_id=session.id,
        speaker="interviewer",
        start=0,
        end=3,
        text="Reemplazo",
    )
    transcripts.replace_for_session(session.id, [replacement])
    assert [item.text for item in transcripts.list_for_session(session.id)] == [
        "Reemplazo"
    ]
