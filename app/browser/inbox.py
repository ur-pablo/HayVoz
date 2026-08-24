"""Validated, owner-only inbox for browser native-messaging requests."""

from __future__ import annotations

import base64
import binascii
import json
import os
import tempfile
import uuid
from pathlib import Path
from typing import Any

from app.local_config import secure_directory, secure_file

HOST_NAME = "com.urpablo.hayvoz"
CHROME_EXTENSION_ID = "fgnjijejmeghpcclbbegoapmlimghlcb"
MAX_CHUNK_BYTES = 384 * 1024
MAX_CHUNK_COUNT = 16_384
MAX_TITLE_LENGTH = 120
MIME_EXTENSIONS = {
    "audio/webm": ".webm",
    "audio/webm;codecs=opus": ".webm",
    "audio/mp4": ".m4a",
}


class BrowserMessageError(RuntimeError):
    pass


class BrowserInbox:
    def __init__(self, root: Path) -> None:
        self.root = root.expanduser().resolve()
        secure_directory(self.root)

    def handle(self, message: object) -> dict[str, object]:
        if not isinstance(message, dict):
            raise BrowserMessageError("El mensaje nativo debe ser un objeto JSON.")
        message_type = message.get("type")
        if message_type == "ping":
            return {"ok": True, "status": "ready"}
        capture_id = _capture_id(message.get("capture_id"))
        if message_type == "start":
            return self._start(capture_id, message)
        if message_type == "chunk":
            return self._chunk(capture_id, message)
        if message_type == "finish":
            return self._finish(capture_id, message)
        if message_type == "status":
            return self._status(capture_id)
        raise BrowserMessageError("Tipo de mensaje nativo no permitido.")

    def _start(
        self,
        capture_id: str,
        message: dict[str, Any],
    ) -> dict[str, object]:
        title = message.get("title")
        mime_type = message.get("mime_type")
        if not isinstance(title, str) or not title.strip():
            raise BrowserMessageError("El título de captura es obligatorio.")
        title = title.strip()
        if len(title) > MAX_TITLE_LENGTH:
            raise BrowserMessageError("El título de captura es demasiado largo.")
        if mime_type not in MIME_EXTENSIONS:
            raise BrowserMessageError("Formato de audio del navegador no permitido.")

        directory = self.capture_dir(capture_id)
        secure_directory(directory)
        metadata_path = directory / "metadata.json"
        metadata = {
            "schema_version": 1,
            "capture_id": capture_id,
            "title": title,
            "mime_type": mime_type,
        }
        if metadata_path.exists():
            existing = _read_json(metadata_path)
            if existing != metadata:
                raise BrowserMessageError("La captura ya existe con otros datos.")
        else:
            _atomic_json(metadata_path, metadata)
        return {"ok": True, "status": "receiving"}

    def _chunk(
        self,
        capture_id: str,
        message: dict[str, Any],
    ) -> dict[str, object]:
        directory = self.capture_dir(capture_id)
        if not (directory / "metadata.json").is_file():
            raise BrowserMessageError("La captura no fue iniciada.")
        sequence = message.get("sequence")
        encoded = message.get("data")
        if not isinstance(sequence, int) or not 0 <= sequence < MAX_CHUNK_COUNT:
            raise BrowserMessageError("Secuencia de audio inválida.")
        if not isinstance(encoded, str):
            raise BrowserMessageError("Chunk de audio inválido.")
        try:
            content = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError) as error:
            raise BrowserMessageError("Chunk de audio inválido.") from error
        if not content or len(content) > MAX_CHUNK_BYTES:
            raise BrowserMessageError("Tamaño de chunk de audio no permitido.")

        path = directory / f"chunk-{sequence:08d}.bin"
        if path.exists():
            if path.read_bytes() != content:
                raise BrowserMessageError("El chunk repetido no coincide.")
        else:
            _atomic_bytes(path, content)
        return {"ok": True, "status": "receiving", "sequence": sequence}

    def _finish(
        self,
        capture_id: str,
        message: dict[str, Any],
    ) -> dict[str, object]:
        directory = self.capture_dir(capture_id)
        if not (directory / "metadata.json").is_file():
            raise BrowserMessageError("La captura no fue iniciada.")
        chunk_count = message.get("chunk_count")
        if not isinstance(chunk_count, int) or not 0 < chunk_count <= MAX_CHUNK_COUNT:
            raise BrowserMessageError("Cantidad de chunks inválida.")
        expected = {
            directory / f"chunk-{sequence:08d}.bin" for sequence in range(chunk_count)
        }
        present = set(directory.glob("chunk-*.bin"))
        if present != expected:
            raise BrowserMessageError("Faltan chunks de audio antes de finalizar.")
        _atomic_json(
            directory / "request.json",
            {"schema_version": 1, "chunk_count": chunk_count},
        )
        return {"ok": True, "status": "queued"}

    def _status(self, capture_id: str) -> dict[str, object]:
        directory = self.capture_dir(capture_id)
        result_path = directory / "result.json"
        if result_path.is_file():
            result = _read_json(result_path)
            return {
                key: result[key]
                for key in ("ok", "status", "session_id", "segment_count", "error")
                if key in result
            }
        if (directory / "processing.json").is_file():
            return {"ok": True, "status": "processing"}
        if (directory / "request.json").is_file():
            return {"ok": True, "status": "queued"}
        if (directory / "metadata.json").is_file():
            return {"ok": True, "status": "receiving"}
        return {"ok": False, "status": "unknown"}

    def capture_dir(self, capture_id: str) -> Path:
        return self.root / _capture_id(capture_id)


def _capture_id(value: object) -> str:
    if not isinstance(value, str):
        raise BrowserMessageError("Identificador de captura inválido.")
    try:
        parsed = uuid.UUID(value)
    except ValueError as error:
        raise BrowserMessageError("Identificador de captura inválido.") from error
    if str(parsed) != value.lower():
        raise BrowserMessageError("Identificador de captura inválido.")
    return str(parsed)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise BrowserMessageError("Estado local de captura inválido.") from error
    if not isinstance(value, dict):
        raise BrowserMessageError("Estado local de captura inválido.")
    return value


def _atomic_json(path: Path, value: dict[str, object]) -> None:
    _atomic_bytes(
        path,
        (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
    )


def _atomic_bytes(path: Path, content: bytes) -> None:
    secure_directory(path.parent)
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
        secure_file(path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
