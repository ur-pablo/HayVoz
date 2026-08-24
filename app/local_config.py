"""Private per-user configuration and data locations."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

CONFIG_KEY = re.compile(r"^[A-Z][A-Z0-9_]*$")


def default_config_dir() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "HayVoz"
    if os.name == "nt":
        root = os.getenv("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(root) / "HayVoz"
    root = os.getenv("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(root) / "hayvoz"


def default_data_dir() -> Path:
    if sys.platform == "darwin":
        return default_config_dir() / "data"
    if os.name == "nt":
        root = os.getenv("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(root) / "HayVoz" / "data"
    root = os.getenv("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(root) / "hayvoz"


def configured_path() -> Path:
    override = os.getenv("HAYVOZ_CONFIG_FILE", "").strip()
    return (
        Path(override).expanduser() if override else default_config_dir() / "config.env"
    )


def load_local_config(path: Path | None = None) -> dict[str, str]:
    selected = (path or configured_path()).expanduser()
    if not selected.exists():
        return {}
    values: dict[str, str] = {}
    for number, raw_line in enumerate(
        selected.read_text(encoding="utf-8").splitlines(), start=1
    ):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            raise ValueError(f"Configuración inválida en {selected}:{number}.")
        key, raw_value = line.split("=", 1)
        key = key.strip()
        if not CONFIG_KEY.fullmatch(key):
            raise ValueError(f"Clave inválida en {selected}:{number}.")
        value = raw_value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        values[key] = value
    return values


def setting(values: dict[str, str], name: str, *fallback_names: str) -> str:
    for key in (name, *fallback_names):
        if key in os.environ:
            return os.environ[key].strip()
    for key in (name, *fallback_names):
        if key in values:
            return values[key].strip()
    return ""


def secure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        path.chmod(0o700)


def secure_file(path: Path) -> None:
    if path.exists() and os.name != "nt":
        path.chmod(0o600)
