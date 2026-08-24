"""Durable local copies of optional Markdown interview guides."""

from __future__ import annotations

import os
from pathlib import Path

from app.config import Settings

MAX_GUIDE_BYTES = 256 * 1024


class InterviewGuideError(RuntimeError):
    pass


class InterviewGuideStore:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def copy_for_session(self, session_id: str, source: Path | None) -> Path | None:
        if source is None:
            return None
        resolved = source.expanduser().resolve()
        if not resolved.is_file():
            raise InterviewGuideError(f"No existe la guía Markdown: {source}")
        try:
            size = resolved.stat().st_size
            content = resolved.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            raise InterviewGuideError("No se pudo leer la guía como UTF-8.") from error
        if size > MAX_GUIDE_BYTES:
            raise InterviewGuideError("La guía supera el límite local de 256 KiB.")
        if not content.strip():
            raise InterviewGuideError("La guía está vacía.")

        destination = self.settings.guides_dir / f"{session_id}.md"
        temporary = destination.with_suffix(".md.tmp")
        try:
            temporary.write_text(content, encoding="utf-8")
            os.replace(temporary, destination)
        except OSError as error:
            temporary.unlink(missing_ok=True)
            raise InterviewGuideError("No se pudo persistir la guía local.") from error
        return destination

    def read(self, path: Path | None) -> str | None:
        if path is None:
            return None
        try:
            return path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            raise InterviewGuideError(
                "No se pudo leer la copia local de la guía."
            ) from error
