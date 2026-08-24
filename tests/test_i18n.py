from typer.testing import CliRunner

from app.i18n import assistant_aliases, assistant_term, normalize_language
from app.sessions.models import SessionMode
from app.ui.cli import _parse_session_mode, app


def test_assistant_term_and_internal_mode_are_language_independent() -> None:
    assert assistant_term("es_CL") == "Asistente"
    assert assistant_term("de-DE") == "Assistent"
    assert assistant_term("zz") == "Assistant"
    assert normalize_language("pt_BR") == "pt"
    assert _parse_session_mode("assistente") is SessionMode.ASSISTANT
    assert _parse_session_mode("asistente") is SessionMode.ASSISTANT
    assert _parse_session_mode("assistant") is SessionMode.ASSISTANT


def test_localized_aliases_are_registered(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HAYVOZ_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("HAYVOZ_LANGUAGE", "es")
    result = CliRunner().invoke(app, ["asistente", "missing-session"])
    assert result.exit_code == 1
    assert "No se pudo leer Asistente" in result.stdout
    assert {"assistant", "asistente", "assistente", "assistent"} <= set(
        assistant_aliases()
    )
