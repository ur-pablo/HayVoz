from __future__ import annotations

import base64
import json
from uuid import uuid4

import pytest

from app.browser.inbox import (
    MAX_CHUNK_BYTES,
    MAX_CHUNK_COUNT,
    BrowserInbox,
    BrowserMessageError,
)


def test_browser_inbox_receives_capture_and_reports_status(tmp_path) -> None:
    inbox = BrowserInbox(tmp_path / "inbox")
    capture_id = str(uuid4())

    assert inbox.handle({"type": "ping"}) == {"ok": True, "status": "ready"}
    assert (
        inbox.handle(
            {
                "type": "start",
                "capture_id": capture_id,
                "title": "Reunión privada",
                "mime_type": "audio/webm;codecs=opus",
            }
        )["status"]
        == "receiving"
    )
    assert (
        inbox.handle(
            {
                "type": "chunk",
                "capture_id": capture_id,
                "sequence": 0,
                "data": base64.b64encode(b"audio-local").decode("ascii"),
            }
        )["sequence"]
        == 0
    )
    assert (
        inbox.handle({"type": "finish", "capture_id": capture_id, "chunk_count": 1})[
            "status"
        ]
        == "queued"
    )
    assert inbox.handle({"type": "status", "capture_id": capture_id}) == {
        "ok": True,
        "status": "queued",
    }

    directory = inbox.capture_dir(capture_id)
    assert (directory / "chunk-00000000.bin").read_bytes() == b"audio-local"
    assert json.loads((directory / "request.json").read_text())["chunk_count"] == 1


def test_browser_inbox_rejects_invalid_capture_and_chunk(tmp_path) -> None:
    inbox = BrowserInbox(tmp_path / "inbox")

    with pytest.raises(BrowserMessageError, match="Identificador"):
        inbox.handle({"type": "status", "capture_id": "../../private"})

    capture_id = str(uuid4())
    inbox.handle(
        {
            "type": "start",
            "capture_id": capture_id,
            "title": "Prueba",
            "mime_type": "audio/webm",
        }
    )
    too_large = base64.b64encode(b"x" * (MAX_CHUNK_BYTES + 1)).decode()
    for encoded in ("not-base64", too_large):
        with pytest.raises(BrowserMessageError):
            inbox.handle(
                {
                    "type": "chunk",
                    "capture_id": capture_id,
                    "sequence": 0,
                    "data": encoded,
                }
            )

    with pytest.raises(BrowserMessageError, match="Secuencia"):
        inbox.handle(
            {
                "type": "chunk",
                "capture_id": capture_id,
                "sequence": MAX_CHUNK_COUNT,
                "data": base64.b64encode(b"audio").decode(),
            }
        )


def test_browser_inbox_repeated_chunk_must_match(tmp_path) -> None:
    inbox = BrowserInbox(tmp_path / "inbox")
    capture_id = str(uuid4())
    inbox.handle(
        {
            "type": "start",
            "capture_id": capture_id,
            "title": "Idempotencia",
            "mime_type": "audio/mp4",
        }
    )
    message = {
        "type": "chunk",
        "capture_id": capture_id,
        "sequence": 0,
        "data": base64.b64encode(b"first").decode(),
    }
    inbox.handle(message)
    inbox.handle(message)
    message["data"] = base64.b64encode(b"different").decode()
    with pytest.raises(BrowserMessageError, match="no coincide"):
        inbox.handle(message)
