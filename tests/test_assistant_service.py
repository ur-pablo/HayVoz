from pathlib import Path

from app.assistant.service import AssistantService
from app.sessions.guide import InterviewGuideStore
from app.sessions.models import SessionMode
from app.sessions.service import SessionService
from app.storage.assistant_repository import AssistantRepository
from app.storage.database import Database
from app.storage.repository import SessionRepository
from app.storage.transcript_repository import TranscriptRepository
from app.transcription.json_store import TranscriptJsonStore
from tests.fakes import FakeLLMProvider, FakeRecorder, FakeTranscriber


def test_assistant_uses_guide_rolling_context_and_debounce(
    settings,
    repository: SessionRepository,
    tmp_path: Path,
) -> None:
    guide = tmp_path / "guide.md"
    guide.write_text(
        "# Objetivo\n\n- ¿Cómo trabajan hoy?\n- ¿Qué cambiarían?\n",
        encoding="utf-8",
    )
    recorder = FakeRecorder()
    lifecycle = SessionService(settings, repository, FakeRecorder(), recorder)
    session = lifecycle.start(
        title="Discovery",
        mode=SessionMode.ASSISTANT,
        guide=guide,
        allow_external=True,
        assistant_chunk_seconds=15,
        assistant_analysis_interval_seconds=30,
        assistant_last_segments=1,
    )
    database = Database(settings.database_path)
    provider = FakeLLMProvider()
    service = AssistantService(
        repository,
        TranscriptRepository(database),
        AssistantRepository(database),
        TranscriptJsonStore(settings),
        InterviewGuideStore(settings),
        FakeTranscriber(),
        provider,
        language="es",
    )
    chunk = tmp_path / "000000.flac"
    chunk.write_bytes(b"fLaC")

    service.process_chunk(session.id, chunk, chunk_index=0)
    assert service.maybe_suggest(session.id) is None
    service.process_chunk(session.id, chunk, chunk_index=2)
    first = service.maybe_suggest(session.id)

    assert first is not None
    assert first.suggested_question == "¿Qué impacto tiene ese problema?"
    assert len(provider.assistant_requests) == 1
    request = provider.assistant_requests[0]
    assert "¿Cómo trabajan hoy?" in (request.interview_guide or "")
    assert len(request.recent_turns) == 1
    assert request.recent_turns[0].start == 30.5

    service.process_chunk(session.id, chunk, chunk_index=4)
    second = service.maybe_suggest(session.id)
    assert second is not None
    assert provider.assistant_requests[1].accumulated_summary == "Resumen acumulado."
    assert provider.assistant_requests[1].previous_suggestions == [
        "¿Qué impacto tiene ese problema?"
    ]
    assert TranscriptJsonStore(settings).path_for(session.id).exists()


def test_local_only_assistant_transcribes_without_llm(
    settings, repository, tmp_path
) -> None:
    recorder = FakeRecorder()
    lifecycle = SessionService(settings, repository, FakeRecorder(), recorder)
    session = lifecycle.start(
        title="Privada",
        mode=SessionMode.ASSISTANT,
        local_only=True,
    )
    database = Database(settings.database_path)
    provider = FakeLLMProvider()
    service = AssistantService(
        repository,
        TranscriptRepository(database),
        AssistantRepository(database),
        TranscriptJsonStore(settings),
        InterviewGuideStore(settings),
        FakeTranscriber(),
        provider,
    )
    chunk = tmp_path / "000000.flac"
    chunk.write_bytes(b"fLaC")

    persisted = service.process_chunk(session.id, chunk, chunk_index=0)

    assert len(persisted) == 1
    assert service.maybe_suggest(session.id) is None
    assert provider.assistant_requests == []
