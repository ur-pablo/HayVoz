from __future__ import annotations

from app.config import Settings
from app.sessions.models import SessionMode, SessionStatus
from app.sessions.service import SessionService, SessionServiceError
from app.storage.repository import SessionRepository
from tests.fakes import FakeRecorder


def test_create_and_stop_session(
    settings: Settings, repository: SessionRepository
) -> None:
    recorder = FakeRecorder()
    service = SessionService(settings, repository, recorder)

    started = service.start(title="Entrevista", local_only=True)
    assert started.status is SessionStatus.RECORDING
    assert started.recording_pid == 42000
    assert started.local_only is True
    assert started.audio_path.exists()

    stopped = service.stop()
    assert stopped.status is SessionStatus.COMPLETED
    assert stopped.ended_at is not None
    assert stopped.recording_pid is None


def test_dual_source_paths_are_persisted_and_required(
    settings: Settings, repository: SessionRepository
) -> None:
    recorder = FakeRecorder()
    service = SessionService(settings, repository, recorder)

    started = service.start(
        title="Dos fuentes",
        device="0",
        system_device="1",
        local_only=True,
    )

    assert started.system_audio_device == "1"
    assert started.system_audio_path == settings.recordings_dir / (
        f"{started.id}.system.flac"
    )
    assert started.system_audio_path.read_bytes() == b"fLaC-system-test"
    persisted = repository.get(started.id)
    assert persisted.system_audio_path == started.system_audio_path
    assert service.stop().status is SessionStatus.COMPLETED


def test_dual_source_missing_one_file_is_interrupted(
    settings: Settings, repository: SessionRepository
) -> None:
    recorder = FakeRecorder()
    service = SessionService(settings, repository, recorder)
    started = service.start(title="Incompleta", device="0", system_device="1")
    assert started.system_audio_path is not None
    started.system_audio_path.unlink()

    stopped = service.stop()

    assert stopped.status is SessionStatus.INTERRUPTED
    assert "ambas fuentes" in (stopped.error_message or "")


def test_dual_source_rejects_same_device_and_assistant(
    settings: Settings, repository: SessionRepository
) -> None:
    service = SessionService(settings, repository, FakeRecorder(), FakeRecorder())

    for mode, message in (
        (SessionMode.RECORD, "fuentes diferentes"),
        (SessionMode.ASSISTANT, "solo en record mode"),
    ):
        try:
            service.start(
                title="Inválida",
                mode=mode,
                device="0",
                system_device="0" if mode is SessionMode.RECORD else "1",
                local_only=True,
            )
        except SessionServiceError as error:
            assert message in str(error)
        else:
            raise AssertionError("se esperaba SessionServiceError")


def test_session_persists_across_repository_instances(
    settings: Settings, repository: SessionRepository
) -> None:
    recorder = FakeRecorder()
    service = SessionService(settings, repository, recorder)
    started = service.start(title="Persistente")

    from app.storage.database import Database

    fresh_repository = SessionRepository(Database(settings.database_path))
    loaded = fresh_repository.get(started.id)
    assert loaded.id == started.id
    assert loaded.title == "Persistente"
    assert loaded.status is SessionStatus.RECORDING


def test_start_failure_is_persisted(
    settings: Settings, repository: SessionRepository
) -> None:
    service = SessionService(
        settings,
        repository,
        FakeRecorder(fail_on_start=True),
    )
    try:
        service.start(title="Fallará")
    except SessionServiceError as error:
        assert "fallo simulado" in str(error)
    else:
        raise AssertionError("se esperaba SessionServiceError")

    sessions = repository.list()
    assert len(sessions) == 1
    assert sessions[0].status is SessionStatus.FAILED
    assert sessions[0].error_message == "fallo simulado"


def test_recover_stopped_recorder_without_losing_audio(
    settings: Settings, repository: SessionRepository
) -> None:
    recorder = FakeRecorder()
    service = SessionService(settings, repository, recorder)
    started = service.start(title="Recuperable")
    recorder.active.clear()

    assert service.recover_orphans() == 1
    recovered = repository.get(started.id)
    assert recovered.status is SessionStatus.INTERRUPTED
    assert recovered.audio_path.read_bytes() == b"fLaC-test"


def test_assistant_configuration_and_guide_are_persisted(
    settings: Settings,
    repository: SessionRepository,
    tmp_path,
) -> None:
    guide = tmp_path / "guide.md"
    guide.write_text("# Guía\n\n- ¿Qué problema tienes?\n", encoding="utf-8")
    assistant_recorder = FakeRecorder()
    service = SessionService(
        settings,
        repository,
        FakeRecorder(),
        assistant_recorder,
    )

    session = service.start(
        title="Assistant",
        mode=SessionMode.ASSISTANT,
        guide=guide,
        allow_external=True,
        assistant_chunk_seconds=10,
        assistant_analysis_interval_seconds=40,
        assistant_last_segments=12,
    )

    assert session.guide_path == settings.guides_dir / f"{session.id}.md"
    assert session.guide_path.read_text(encoding="utf-8").startswith("# Guía")
    assert session.assistant_chunk_seconds == 10
    assert session.assistant_analysis_interval_seconds == 40
    assert session.assistant_last_segments == 12
    assert service.stop().status is SessionStatus.COMPLETED
