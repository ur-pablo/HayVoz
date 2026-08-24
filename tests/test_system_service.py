from __future__ import annotations

from types import SimpleNamespace

import app.system_service as system_service
from app.system_service import SystemServiceManager, _windows_task_command


def test_linux_service_quotes_private_config_path(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(system_service.sys, "platform", "linux")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg config"))
    calls: list[list[str]] = []

    def fake_run(command, **_kwargs):
        calls.append(command)
        return SimpleNamespace(returncode=0, stderr="")

    monkeypatch.setattr(system_service.subprocess, "run", fake_run)
    manager = SystemServiceManager(
        tmp_path / "bin" / "hayvoz",
        tmp_path / "private config" / "config.env",
    )

    path = manager.install()
    unit = path.read_text(encoding="utf-8")

    assert 'Environment="HAYVOZ_CONFIG_FILE=' in unit
    assert 'private config/config.env"' in unit
    assert "NoNewPrivileges=true" in unit
    assert "PrivateTmp=true" in unit
    assert ["systemctl", "--user", "enable", "--now", "hayvoz.service"] in calls


def test_windows_task_uses_an_argument_instead_of_shell_environment(tmp_path) -> None:
    command = _windows_task_command(
        tmp_path / "Hay Voz" / "hayvoz.exe",
        tmp_path / "Private Config" / "config.env",
    )

    assert "cmd /d" not in command
    assert "set HAYVOZ" not in command
    assert "system run --config" in command
    assert '"' in command
