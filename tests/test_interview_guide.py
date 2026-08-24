from pathlib import Path

import pytest

from app.sessions.guide import InterviewGuideError, InterviewGuideStore


def test_guide_is_copied_for_recovery(settings, tmp_path: Path) -> None:
    source = tmp_path / "interview.md"
    source.write_text("# Guía\n\n- ¿Cómo trabajan hoy?\n", encoding="utf-8")
    store = InterviewGuideStore(settings)

    copied = store.copy_for_session("session-1", source)

    assert copied == settings.guides_dir / "session-1.md"
    assert copied is not None
    assert store.read(copied) == source.read_text(encoding="utf-8")
    source.unlink()
    assert "¿Cómo trabajan hoy?" in (store.read(copied) or "")


def test_empty_guide_is_rejected(settings, tmp_path: Path) -> None:
    source = tmp_path / "empty.md"
    source.write_text("   \n", encoding="utf-8")

    with pytest.raises(InterviewGuideError, match="vacía"):
        InterviewGuideStore(settings).copy_for_session("session-1", source)
