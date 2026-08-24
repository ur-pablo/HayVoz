from __future__ import annotations

import json
import re
from pathlib import Path

from app import __version__
from scripts import version

ROOT = Path(__file__).resolve().parents[1]


def test_version_is_stable_semver_and_shared_with_browser() -> None:
    manifest = json.loads(
        (ROOT / "extensions" / "web" / "manifest.json").read_text(encoding="utf-8")
    )

    assert re.fullmatch(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)", __version__)
    assert manifest["version"] == __version__


def test_pyproject_uses_package_version_as_canonical_source() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert 'dynamic = ["version"]' in pyproject
    assert 'path = "app/__init__.py"' in pyproject
    assert re.search(r'^version\s*=\s*"', pyproject, re.MULTILINE) is None


def test_version_script_updates_package_and_browser_together(
    tmp_path, monkeypatch
) -> None:
    package = tmp_path / "__init__.py"
    manifest = tmp_path / "manifest.json"
    package.write_text('__version__ = "0.8.0"\n', encoding="utf-8")
    manifest.write_text('{"version": "0.8.0"}\n', encoding="utf-8")
    monkeypatch.setattr(version, "PACKAGE_FILE", package)
    monkeypatch.setattr(version, "MANIFEST_FILE", manifest)

    version.set_version("1.2.3")

    assert version.validate("1.2.3") == "1.2.3"
    assert '__version__ = "1.2.3"' in package.read_text(encoding="utf-8")
    assert json.loads(manifest.read_text(encoding="utf-8"))["version"] == "1.2.3"
