import json

import pytest

from app.config import Settings
from app.sessions.service import SessionService
from app.storage.database import Database
from app.storage.repository import SessionRepository
from app.storage.transcript_repository import TranscriptRepository
from app.transcription.json_store import TranscriptJsonStore
from app.transcription.models import Speaker
from app.transcription.service import TranscriptionService, TranscriptionServiceError
from tests.fakes import FakeRecorder, FakeTranscriber


def _completed_session(settings: Settings, repository: SessionRepository) -> str:
    sessions = SessionService(settings, repository, FakeRecorder())
    session = sessions.start(title="Audio listo")
    sessions.stop()
    return session.id


def _service(
    settings: Settings,
    sessions: SessionRepository,
    transcriber: FakeTranscriber,
) -> TranscriptionService:
    database = Database(settings.database_path)
    return TranscriptionService(
        sessions,
        TranscriptRepository(database),
        TranscriptJsonStore(settings),
        transcriber,
    )


def test_transcription_persists_public_json_and_segments(
    settings: Settings, repository: SessionRepository
) -> None:
    session_id = _completed_session(settings, repository)
    service = _service(settings, repository, FakeTranscriber())

    run = service.transcribe(
        session_id,
        language="es",
        speaker=Speaker.INTERVIEWER,
    )

    assert run.segment_count == 1
    assert run.language == "es"
    persisted = service.get_segments(session_id)
    assert persisted[0].text == "Texto de prueba"
    public_json = json.loads(run.transcript_path.read_text(encoding="utf-8"))
    assert public_json == [
        {
            "speaker": "interviewer",
            "start": 0.5,
            "end": 2.25,
            "text": "Texto de prueba",
            "confidence": 0.91,
        }
    ]


def test_whisper_failure_preserves_previous_transcript(
    settings: Settings, repository: SessionRepository
) -> None:
    session_id = _completed_session(settings, repository)
    original = _service(settings, repository, FakeTranscriber(text="Anterior"))
    run = original.transcribe(
        session_id,
        language="es",
        speaker=Speaker.INTERVIEWER,
    )
    previous_json = run.transcript_path.read_bytes()

    failing = _service(settings, repository, FakeTranscriber(fail=True))
    with pytest.raises(TranscriptionServiceError, match="fallo Whisper simulado"):
        failing.transcribe(
            session_id,
            language="es",
            speaker=Speaker.INTERVIEWER,
        )

    assert run.transcript_path.read_bytes() == previous_json
    assert [item.text for item in original.get_segments(session_id)] == ["Anterior"]


def test_dual_source_transcription_is_sequential_and_assigns_speakers(
    settings: Settings, repository: SessionRepository
) -> None:
    lifecycle = SessionService(settings, repository, FakeRecorder())
    session = lifecycle.start(
        title="Dos voces", device="0", system_device="1", local_only=True
    )
    lifecycle.stop()
    transcriber = FakeTranscriber()
    service = _service(settings, repository, transcriber)

    run = service.transcribe(
        session.id,
        language="es",
        speaker=Speaker.UNKNOWN,
    )

    assert transcriber.calls == [session.audio_path, session.system_audio_path]
    assert run.segment_count == 2
    assert [item.speaker for item in service.get_segments(session.id)] == [
        Speaker.INTERVIEWER,
        Speaker.INTERVIEWEE,
    ]


def test_second_source_failure_preserves_previous_transcript(
    settings: Settings, repository: SessionRepository
) -> None:
    lifecycle = SessionService(settings, repository, FakeRecorder())
    session = lifecycle.start(title="Atómica", device="0", system_device="1")
    lifecycle.stop()
    original = _service(settings, repository, FakeTranscriber(text="Anterior"))
    run = original.transcribe(
        session.id,
        language="es",
        speaker=Speaker.UNKNOWN,
    )
    previous_json = run.transcript_path.read_bytes()

    failing = _service(settings, repository, FakeTranscriber(fail_on_call=2))
    with pytest.raises(TranscriptionServiceError, match="fallo Whisper simulado"):
        failing.transcribe(
            session.id,
            language="es",
            speaker=Speaker.UNKNOWN,
        )

    assert run.transcript_path.read_bytes() == previous_json
    assert [item.text for item in original.get_segments(session.id)] == [
        "Anterior",
        "Anterior",
    ]


def test_missing_json_is_recovered_from_sqlite(
    settings: Settings, repository: SessionRepository
) -> None:
    session_id = _completed_session(settings, repository)
    service = _service(settings, repository, FakeTranscriber(text="Recuperable"))
    run = service.transcribe(
        session_id,
        language="es",
        speaker=Speaker.INTERVIEWER,
    )
    run.transcript_path.unlink()

    assert [item.text for item in service.get_segments(session_id)] == ["Recuperable"]
    assert run.transcript_path.exists()


def test_active_session_cannot_be_transcribed(
    settings: Settings, repository: SessionRepository
) -> None:
    session = SessionService(settings, repository, FakeRecorder()).start(
        title="Todavía grabando"
    )
    service = _service(settings, repository, FakeTranscriber())

    with pytest.raises(TranscriptionServiceError, match="Detén la grabación"):
        service.transcribe(
            session.id,
            language=None,
            speaker=Speaker.INTERVIEWER,
        )
