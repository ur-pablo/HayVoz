"""Chrome native-messaging stdio host for the private browser inbox."""

from __future__ import annotations

import json
import os
import struct
import sys

from app.browser.inbox import BrowserInbox, BrowserMessageError
from app.config import Settings
from app.local_config import default_config_dir

MAX_MESSAGE_BYTES = 2 * 1024 * 1024


def main() -> None:
    try:
        _load_bootstrap_config()
        settings = Settings.from_env(load_ai_credentials=False)
        settings.ensure_directories()
        message = _read_message()
        response = BrowserInbox(settings.browser_inbox_dir).handle(message)
    except BrowserMessageError as error:
        response = {"ok": False, "status": "error", "error": str(error)}
    except Exception:
        response = {
            "ok": False,
            "status": "error",
            "error": "El puente local no pudo procesar el mensaje.",
        }
    _write_message(response)


def _load_bootstrap_config() -> None:
    if os.getenv("HAYVOZ_CONFIG_FILE"):
        return
    bootstrap = default_config_dir() / "native-host.json"
    if not bootstrap.is_file():
        return
    try:
        value = json.loads(bootstrap.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    config_file = value.get("config_file") if isinstance(value, dict) else None
    if isinstance(config_file, str) and config_file:
        os.environ["HAYVOZ_CONFIG_FILE"] = config_file


def _read_message() -> object:
    header = _read_exact(4)
    if len(header) != 4:
        raise BrowserMessageError("Mensaje nativo incompleto.")
    length = struct.unpack("=I", header)[0]
    if not 0 < length <= MAX_MESSAGE_BYTES:
        raise BrowserMessageError("Tamaño de mensaje nativo no permitido.")
    encoded = _read_exact(length)
    if len(encoded) != length:
        raise BrowserMessageError("Mensaje nativo incompleto.")
    try:
        return json.loads(encoded.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise BrowserMessageError("Mensaje nativo inválido.") from error


def _read_exact(length: int) -> bytes:
    chunks: list[bytes] = []
    remaining = length
    while remaining:
        chunk = sys.stdin.buffer.read(remaining)
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def _write_message(message: dict[str, object]) -> None:
    encoded = json.dumps(message, ensure_ascii=False).encode("utf-8")
    sys.stdout.buffer.write(struct.pack("=I", len(encoded)))
    sys.stdout.buffer.write(encoded)
    sys.stdout.buffer.flush()


if __name__ == "__main__":
    main()
