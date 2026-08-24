from __future__ import annotations

import plistlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_safari_project_configurator_injects_handler_and_app_group(tmp_path) -> None:
    handler = tmp_path / "Extension" / "SafariWebExtensionHandler.swift"
    handler.parent.mkdir(parents=True)
    handler.write_text("placeholder", encoding="utf-8")
    entitlements = tmp_path / "Extension" / "HayVoz.entitlements"
    entitlements.write_bytes(plistlib.dumps({"com.apple.security.app-sandbox": True}))

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "configure-safari-project.py"),
            str(tmp_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "NSExtensionRequestHandling" in handler.read_text(encoding="utf-8")
    payload = plistlib.loads(entitlements.read_bytes())
    assert payload["com.apple.security.application-groups"] == [
        "group.com.urpablo.hayvoz"
    ]
