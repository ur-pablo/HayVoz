"""Optional per-user background integration with no network listener."""

from __future__ import annotations

import os
import plistlib
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from app.local_config import secure_directory, secure_file

SERVICE_ID = "org.hayvoz.assistant"


class SystemServiceError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ServiceStatus:
    installed: bool
    detail: str


class SystemServiceManager:
    def __init__(self, executable: Path, config_path: Path) -> None:
        self.executable = executable.resolve()
        self.config_path = config_path.expanduser().resolve()

    def install(self) -> Path:
        if sys.platform == "darwin":
            return self._install_macos()
        if os.name == "nt":
            return self._install_windows()
        return self._install_linux()

    def uninstall(self) -> None:
        if sys.platform == "darwin":
            path = self._macos_path()
            subprocess.run(
                ["launchctl", "bootout", f"gui/{os.getuid()}", str(path)],
                check=False,
                capture_output=True,
                text=True,
            )
            path.unlink(missing_ok=True)
            return
        if os.name == "nt":
            subprocess.run(
                ["schtasks", "/Delete", "/TN", "HayVoz Assistant", "/F"],
                check=False,
                capture_output=True,
                text=True,
            )
            return
        path = self._linux_path()
        subprocess.run(
            ["systemctl", "--user", "disable", "--now", "hayvoz.service"],
            check=False,
            capture_output=True,
            text=True,
        )
        path.unlink(missing_ok=True)
        subprocess.run(
            ["systemctl", "--user", "daemon-reload"],
            check=False,
            capture_output=True,
            text=True,
        )

    def status(self) -> ServiceStatus:
        if sys.platform == "darwin":
            installed = self._macos_path().exists()
        elif os.name == "nt":
            result = subprocess.run(
                ["schtasks", "/Query", "/TN", "HayVoz Assistant"],
                check=False,
                capture_output=True,
                text=True,
            )
            installed = result.returncode == 0
        else:
            installed = self._linux_path().exists()
        return ServiceStatus(
            installed=installed,
            detail="instalado para el usuario actual" if installed else "no instalado",
        )

    def _install_macos(self) -> Path:
        path = self._macos_path()
        secure_directory(path.parent)
        subprocess.run(
            ["launchctl", "bootout", f"gui/{os.getuid()}", str(path)],
            check=False,
            capture_output=True,
            text=True,
        )
        payload = {
            "Label": SERVICE_ID,
            "ProgramArguments": [str(self.executable), "system", "run"],
            "EnvironmentVariables": {
                "HAYVOZ_CONFIG_FILE": str(self.config_path),
            },
            "RunAtLoad": True,
            "KeepAlive": False,
            "ProcessType": "Background",
        }
        path.write_bytes(plistlib.dumps(payload, sort_keys=True))
        secure_file(path)
        result = subprocess.run(
            ["launchctl", "bootstrap", f"gui/{os.getuid()}", str(path)],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise SystemServiceError(result.stderr.strip() or "launchctl falló")
        return path

    def _install_linux(self) -> Path:
        path = self._linux_path()
        secure_directory(path.parent)
        executable = shlex.quote(str(self.executable))
        config = _systemd_environment_value(str(self.config_path))
        path.write_text(
            "\n".join(
                [
                    "[Unit]",
                    "Description=HayVoz private user assistant",
                    "After=default.target",
                    "",
                    "[Service]",
                    "Type=simple",
                    f'Environment="HAYVOZ_CONFIG_FILE={config}"',
                    f"ExecStart={executable} system run",
                    "Restart=on-failure",
                    "NoNewPrivileges=true",
                    "PrivateTmp=true",
                    "",
                    "[Install]",
                    "WantedBy=default.target",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        secure_file(path)
        for command in (
            ["systemctl", "--user", "daemon-reload"],
            ["systemctl", "--user", "enable", "--now", "hayvoz.service"],
        ):
            result = subprocess.run(
                command, check=False, capture_output=True, text=True
            )
            if result.returncode != 0:
                raise SystemServiceError(result.stderr.strip() or "systemctl falló")
        return path

    def _install_windows(self) -> Path:
        command = _windows_task_command(self.executable, self.config_path)
        result = subprocess.run(
            [
                "schtasks",
                "/Create",
                "/TN",
                "HayVoz Assistant",
                "/SC",
                "ONLOGON",
                "/TR",
                command,
                "/RL",
                "LIMITED",
                "/F",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise SystemServiceError(result.stderr.strip() or "schtasks falló")
        return self.config_path

    @staticmethod
    def _macos_path() -> Path:
        return Path.home() / "Library" / "LaunchAgents" / f"{SERVICE_ID}.plist"

    @staticmethod
    def _linux_path() -> Path:
        root = Path(os.getenv("XDG_CONFIG_HOME") or Path.home() / ".config")
        return root / "systemd" / "user" / "hayvoz.service"


def _systemd_environment_value(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("%", "%%")


def _windows_task_command(executable: Path, config_path: Path) -> str:
    return subprocess.list2cmdline(
        [str(executable), "system", "run", "--config", str(config_path)]
    )
