from app.analysis.models import Analysis, AnalysisType
from app.sessions.service import SessionService
from app.storage.analysis_repository import AnalysisRepository
from app.storage.database import Database
from app.storage.repository import SessionRepository
from tests.fakes import FakeRecorder


def test_replace_analyses_is_transactional_and_idempotent(
    settings,
    repository: SessionRepository,
) -> None:
    sessions = SessionService(settings, repository, FakeRecorder())
    session = sessions.start(title="Análisis")
    sessions.stop()
    analyses = AnalysisRepository(Database(settings.database_path))

    analyses.replace_for_session(
        session.id,
        [
            Analysis(
                session_id=session.id,
                type=AnalysisType.SUMMARY,
                content="Primero",
                model="test-model",
            )
        ],
    )
    analyses.replace_for_session(
        session.id,
        [
            Analysis(
                session_id=session.id,
                type=AnalysisType.FINAL_REPORT,
                content="# Reemplazo",
                model="test-model-2",
            )
        ],
    )

    persisted = analyses.list_for_session(session.id)
    assert [(item.type, item.content) for item in persisted] == [
        (AnalysisType.FINAL_REPORT, "# Reemplazo")
    ]
