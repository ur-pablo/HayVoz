from __future__ import annotations

import base64
import json
from types import SimpleNamespace
from uuid import uuid4

from app.browser.inbox import BrowserInbox
from app.browser.processor import BrowserProcessor
from app.transcription.service import TranscriptionServiceError


class FakeImporter:
    def import_audio(self, source, *, title):
        assert source.read_bytes() == b"browser-audio"
        assert title == "Captura automática"
        return SimpleNamespace(id="session-from-browser")


class FakeTranscription:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail

    def transcribe(self, session_id, *, language, speaker):
        assert session_id == "session-from-browser"
        if self.fail:
            raise TranscriptionServiceError("modelo no está instalado")
        return SimpleNamespace(segment_count=3)


class FakeSessions:
    def get(self, session_id):
        return SimpleNamespace(id=session_id)


def _queued_capture(settings) -> tuple[BrowserInbox, str]:
    inbox = BrowserInbox(settings.browser_inbox_dir)
    capture_id = str(uuid4())
    inbox.handle(
        {
            "type": "start",
            "capture_id": capture_id,
            "title": "Captura automática",
            "mime_type": "audio/webm",
        }
    )
    inbox.handle(
        {
            "type": "chunk",
            "capture_id": capture_id,
            "sequence": 0,
            "data": base64.b64encode(b"browser-audio").decode(),
        }
    )
    inbox.handle({"type": "finish", "capture_id": capture_id, "chunk_count": 1})
    return inbox, capture_id


def _processor(settings, *, fail: bool = False) -> BrowserProcessor:
    processor = BrowserProcessor.__new__(BrowserProcessor)
    processor.settings = settings
    processor.sessions = FakeSessions()
    processor.importer = FakeImporter()
    processor.transcription = FakeTranscription(fail=fail)
    return processor


def test_browser_processor_imports_transcribes_and_cleans_raw_capture(settings) -> None:
    inbox, capture_id = _queued_capture(settings)
    directory = inbox.capture_dir(capture_id)

    assert _processor(settings).process_pending() == 1
    assert inbox.handle({"type": "status", "capture_id": capture_id}) == {
        "ok": True,
        "status": "completed",
        "session_id": "session-from-browser",
        "segment_count": 3,
    }
    assert not list(directory.glob("chunk-*.bin"))
    assert not (directory / "processing.json").exists()


def test_browser_processor_reports_failure_and_preserves_raw_audio(settings) -> None:
    inbox, capture_id = _queued_capture(settings)
    directory = inbox.capture_dir(capture_id)

    assert _processor(settings, fail=True).process_pending() == 1
    result = json.loads((directory / "result.json").read_text())
    assert result == {
        "ok": False,
        "status": "failed",
        "error": "modelo no está instalado",
    }
    assert (directory / "chunk-00000000.bin").is_file()
