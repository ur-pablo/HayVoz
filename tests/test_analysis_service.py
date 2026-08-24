import pytest

from app.analysis.models import Analysis, AnalysisType
from app.analysis.service import AnalysisService, AnalysisServiceError
from app.core.session_context import SessionContextService
from app.sessions.service import SessionService
from app.storage.analysis_repository import AnalysisRepository
from app.storage.database import Database
from app.storage.transcript_repository import TranscriptRepository
from app.transcription.models import TranscriptSegment
from tests.fakes import FakeLLMProvider, FakeRecorder


def _service_with_transcript(settings, repository, *, local_only=False, provider=None):
    sessions = SessionService(settings, repository, FakeRecorder())
    session = sessions.start(title="Entrevista", local_only=local_only)
    sessions.stop()
    database = Database(settings.database_path)
    transcripts = TranscriptRepository(database)
    transcripts.replace_for_session(
        session.id,
        [
            TranscriptSegment(
                session_id=session.id,
                speaker="interviewee",
                start=1,
                end=3,
                text="No tenemos un catálogo central.",
            )
        ],
    )
    analyses = AnalysisRepository(database)
    return (
        session,
        AnalysisService(
            SessionContextService(settings, repository, transcripts),
            analyses,
            provider,
        ),
        analyses,
    )


def test_preview_builds_context_without_calling_provider(settings, repository) -> None:
    provider = FakeLLMProvider()
    session, service, _ = _service_with_transcript(
        settings, repository, provider=provider
    )

    preview = service.preview(session.id)

    assert preview.request.title == "Entrevista"
    assert preview.request.turns[0].speaker == "interviewee"
    assert preview.character_count == len("No tenemos un catálogo central.")
    assert provider.requests == []


def test_analysis_requires_confirmation_and_persists_all_types(
    settings, repository
) -> None:
    provider = FakeLLMProvider()
    session, service, analyses = _service_with_transcript(
        settings, repository, provider=provider
    )

    with pytest.raises(AnalysisServiceError, match="confirmación explícita"):
        service.analyze(session.id)
    assert provider.requests == []

    result = service.analyze(session.id, allow_external=True)
    assert len(result) == 8
    assert len(provider.requests) == 1
    assert {item.type for item in analyses.list_for_session(session.id)} == set(
        AnalysisType
    )


def test_local_only_never_calls_provider(settings, repository) -> None:
    provider = FakeLLMProvider()
    session, service, _ = _service_with_transcript(
        settings,
        repository,
        local_only=True,
        provider=provider,
    )

    with pytest.raises(AnalysisServiceError, match="--local-only"):
        service.analyze(session.id, allow_external=True)
    assert provider.requests == []


def test_provider_failure_preserves_previous_analysis(settings, repository) -> None:
    good_provider = FakeLLMProvider()
    session, _service, analyses = _service_with_transcript(
        settings, repository, provider=good_provider
    )
    analyses.replace_for_session(
        session.id,
        [
            Analysis(
                session_id=session.id,
                type=AnalysisType.SUMMARY,
                content="Anterior",
                model="old-model",
            )
        ],
    )
    failing = AnalysisService(
        SessionContextService(
            settings,
            repository,
            TranscriptRepository(Database(settings.database_path)),
        ),
        analyses,
        FakeLLMProvider(fail=True),
    )

    with pytest.raises(AnalysisServiceError, match="fallo OpenAI simulado"):
        failing.analyze(session.id, allow_external=True)

    persisted = analyses.list_for_session(session.id)
    assert len(persisted) == 1
    assert persisted[0].content == "Anterior"
