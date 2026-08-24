"""Install and remove the user-scoped Chrome native-messaging bridge."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from app.browser.inbox import CHROME_EXTENSION_ID, HOST_NAME
from app.local_config import default_config_dir, secure_directory, secure_file


class BrowserIntegrationError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class BrowserIntegrationStatus:
    installed: bool
    manifests: tuple[Path, ...]


class BrowserIntegrationManager:
    def __init__(self, native_executable: Path, config_path: Path) -> None:
        self.native_executable = native_executable.expanduser().resolve()
        self.config_path = config_path.expanduser().resolve()

    def install(self) -> tuple[Path, ...]:
        if not self.native_executable.is_file():
            raise BrowserIntegrationError(
                "No se encontró el ejecutable hayvoz-native junto a hayvoz."
            )
        payload = {
            "name": HOST_NAME,
            "description": "HayVoz private local transcription bridge",
            "path": str(self.native_executable),
            "type": "stdio",
            "allowed_origins": [f"chrome-extension://{CHROME_EXTENSION_ID}/"],
        }
        paths = self._manifest_paths()
        for path in paths:
            secure_directory(path.parent)
            path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            secure_file(path)
        bootstrap = self._bootstrap_path()
        secure_directory(bootstrap.parent)
        bootstrap.write_text(
            json.dumps({"config_file": str(self.config_path)}, indent=2) + "\n",
            encoding="utf-8",
        )
        secure_file(bootstrap)
        if os.name == "nt":
            self._register_windows(paths[0])
        return paths

    def uninstall(self) -> None:
        if os.name == "nt":
            subprocess.run(
                [
                    "reg",
                    "delete",
                    rf"HKCU\Software\Google\Chrome\NativeMessagingHosts\{HOST_NAME}",
                    "/f",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
        for path in self._manifest_paths():
            path.unlink(missing_ok=True)
        self._bootstrap_path().unlink(missing_ok=True)

    def status(self) -> BrowserIntegrationStatus:
        paths = tuple(path for path in self._manifest_paths() if path.is_file())
        return BrowserIntegrationStatus(installed=bool(paths), manifests=paths)

    def _manifest_paths(self) -> tuple[Path, ...]:
        filename = f"{HOST_NAME}.json"
        if sys.platform == "darwin":
            application_support = Path.home() / "Library" / "Application Support"
            return (
                application_support
                / "Google"
                / "Chrome"
                / "NativeMessagingHosts"
                / filename,
                application_support / "Chromium" / "NativeMessagingHosts" / filename,
            )
        if os.name == "nt":
            return (default_config_dir() / "native-messaging" / filename,)
        config_home = Path(os.getenv("XDG_CONFIG_HOME") or Path.home() / ".config")
        return (
            config_home / "google-chrome" / "NativeMessagingHosts" / filename,
            config_home / "chromium" / "NativeMessagingHosts" / filename,
        )

    @staticmethod
    def _bootstrap_path() -> Path:
        return default_config_dir() / "native-host.json"

    @staticmethod
    def _register_windows(manifest: Path) -> None:
        result = subprocess.run(
            [
                "reg",
                "add",
                rf"HKCU\Software\Google\Chrome\NativeMessagingHosts\{HOST_NAME}",
                "/ve",
                "/d",
                str(manifest),
                "/f",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise BrowserIntegrationError(result.stderr.strip() or "reg.exe falló")
