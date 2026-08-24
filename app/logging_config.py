"""Small JSON-lines logging setup that avoids conversational content."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from app.local_config import secure_file
from app.privacy import redact_text


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": redact_text(record.getMessage()),
        }
        for key in (
            "event",
            "session_id",
            "status",
            "provider",
            "model",
            "purpose",
            "segment_count",
            "character_count",
        ):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = redact_text(self.formatException(record.exc_info))
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(logs_dir: Path, *, debug: bool = False) -> None:
    logs_dir.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    if any(getattr(handler, "_hayvoz_handler", False) for handler in root.handlers):
        return

    handler = logging.FileHandler(logs_dir / "app.jsonl", encoding="utf-8")
    secure_file(logs_dir / "app.jsonl")
    handler.setFormatter(JsonFormatter())
    handler._hayvoz_handler = True  # type: ignore[attr-defined]
    root.addHandler(handler)
    root.setLevel(logging.DEBUG if debug else logging.INFO)
