"""Atomic transcript.json persistence with validated public fields."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from pydantic import TypeAdapter

from app.config import Settings
from app.transcription.models import SegmentContent, TranscriptSegment

SEGMENT_LIST = TypeAdapter(list[SegmentContent])


class TranscriptJsonStore:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def path_for(self, session_id: str) -> Path:
        return self.settings.transcripts_dir / f"{session_id}.json"

    def write(self, session_id: str, segments: list[TranscriptSegment]) -> Path:
        payload = [segment.content().model_dump(mode="json") for segment in segments]
        encoded = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode(
            "utf-8"
        )
        path = self.path_for(session_id)
        _atomic_write(path, encoded)
        return path

    def read(self, session_id: str) -> list[SegmentContent]:
        data = json.loads(self.path_for(session_id).read_text(encoding="utf-8"))
        return SEGMENT_LIST.validate_python(data)

    def snapshot(self, session_id: str) -> bytes | None:
        path = self.path_for(session_id)
        return path.read_bytes() if path.exists() else None

    def restore(self, session_id: str, previous: bytes | None) -> None:
        path = self.path_for(session_id)
        if previous is None:
            path.unlink(missing_ok=True)
        else:
            _atomic_write(path, previous)


def _atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}-",
        suffix=".tmp",
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as file:
            file.write(content)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
