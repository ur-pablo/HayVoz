from __future__ import annotations

import re
from types import SimpleNamespace

from typer.testing import CliRunner

from app.analysis.models import Analysis, AnalysisType
from app.config import Settings
from app.sessions.service import SessionService
from app.storage.analysis_repository import AnalysisRepository
from app.storage.database import Database
from app.storage.repository import SessionRepository
from app.storage.transcript_repository import TranscriptRepository
from app.transcription.models import TranscriptSegment
from app.ui import cli
from app.ui.cli import app
from tests.fakes import FakeRecorder

runner = CliRunner()
ANSI_ESCAPE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


def test_cli_version_reports_package_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert result.stdout.strip() == cli.__version__


def test_cli_help_lists_phase_one_commands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for command in (
        "doctor",
        "devices",
        "model",
        "start",
        "stop",
        "sessions",
        "import-audio",
        "transcribe",
        "transcript",
        "analyze",
        "assistant",
        "report",
        "browser",
        "uninstall",
    ):
        assert command in result.stdout


def test_sessions_is_empty_with_isolated_data(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HAYVOZ_DATA_DIR", str(tmp_path / "data"))
    result = runner.invoke(app, ["sessions"])
    assert result.exit_code == 0
    assert "No hay sesiones" in result.stdout


def test_assistant_requires_explicit_privacy_choice(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HAYVOZ_DATA_DIR", str(tmp_path / "data"))
    result = runner.invoke(
        app,
        ["start", "--title", "Fuera de alcance", "--mode", "assistant"],
    )
    assert result.exit_code == 1
    assert "--confirm-send o --local-only" in result.stdout


def test_start_help_documents_optional_system_device() -> None:
    result = runner.invoke(app, ["start", "--help"], terminal_width=160)
    output = ANSI_ESCAPE.sub("", result.stdout)
    assert result.exit_code == 0
    assert "--system-device" in output
    assert "Entrada virtual" in output


def test_uninstall_removes_integrations_but_does_not_delete_data(monkeypatch) -> None:
    calls: list[str] = []
    browser = SimpleNamespace(uninstall=lambda: calls.append("browser"))
    service = SimpleNamespace(uninstall=lambda: calls.append("service"))
    monkeypatch.setattr(cli, "_browser_integration", lambda: browser)
    monkeypatch.setattr(cli, "_system_service", lambda: service)

    result = runner.invoke(app, ["uninstall"])

    assert result.exit_code == 0
    assert calls == ["browser", "service"]
    assert "se conservaron" in result.stdout


def test_analyze_previews_without_network_and_local_only_blocks_send(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("HAYVOZ_DATA_DIR", str(tmp_path / "data"))
    settings = Settings.from_env()
    settings.ensure_directories()
    database = Database(settings.database_path)
    database.initialize()
    sessions = SessionRepository(database)
    lifecycle = SessionService(settings, sessions, FakeRecorder())
    session = lifecycle.start(title="Privada", local_only=True)
    lifecycle.stop()
    TranscriptRepository(database).replace_for_session(
        session.id,
        [
            TranscriptSegment(
                session_id=session.id,
                speaker="interviewee",
                start=0,
                end=1,
                text="Texto revisable",
            )
        ],
    )

    preview = runner.invoke(app, ["analyze", session.id])
    assert preview.exit_code == 0
    assert "Texto revisable" in preview.stdout
    assert "No se envió nada" in preview.stdout

    confirmed = runner.invoke(app, ["analyze", session.id, "--confirm-send"])
    assert confirmed.exit_code == 1
    assert "--local-only" in confirmed.stdout


def test_report_reads_persisted_result_without_openai(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HAYVOZ_DATA_DIR", str(tmp_path / "data"))
    settings = Settings.from_env()
    settings.ensure_directories()
    database = Database(settings.database_path)
    database.initialize()
    sessions = SessionRepository(database)
    lifecycle = SessionService(settings, sessions, FakeRecorder())
    session = lifecycle.start(title="Informe")
    lifecycle.stop()
    AnalysisRepository(database).replace_for_session(
        session.id,
        [
            Analysis(
                session_id=session.id,
                type=AnalysisType.FINAL_REPORT,
                content="# Resultado offline",
                model="test-model",
            )
        ],
    )

    result = runner.invoke(app, ["report", session.id])
    assert result.exit_code == 0
    assert "Resultado offline" in result.stdout
    assert "test-model" in result.stdout
