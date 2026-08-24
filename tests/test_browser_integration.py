from __future__ import annotations

import json
from types import SimpleNamespace

from app.browser import integration
from app.browser.inbox import CHROME_EXTENSION_ID, HOST_NAME
from app.browser.integration import BrowserIntegrationManager


def test_browser_integration_installs_and_removes_owner_scoped_files(
    tmp_path, monkeypatch
) -> None:
    native = tmp_path / "bin" / "hayvoz-native"
    native.parent.mkdir()
    native.write_text("native")
    config = tmp_path / "private" / "config.env"
    manifest = tmp_path / "chrome" / f"{HOST_NAME}.json"
    bootstrap = tmp_path / "config" / "native-host.json"
    manager = BrowserIntegrationManager(native, config)
    monkeypatch.setattr(manager, "_manifest_paths", lambda: (manifest,))
    monkeypatch.setattr(manager, "_bootstrap_path", lambda: bootstrap)
    monkeypatch.setattr(manager, "_register_windows", lambda _path: None)
    monkeypatch.setattr(
        integration.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="", stderr=""),
    )

    assert manager.install() == (manifest,)
    payload = json.loads(manifest.read_text())
    assert payload == {
        "name": HOST_NAME,
        "description": "HayVoz private local transcription bridge",
        "path": str(native.resolve()),
        "type": "stdio",
        "allowed_origins": [f"chrome-extension://{CHROME_EXTENSION_ID}/"],
    }
    assert json.loads(bootstrap.read_text()) == {"config_file": str(config.resolve())}
    assert manager.status().installed is True

    manager.uninstall()
    assert not manifest.exists()
    assert not bootstrap.exists()
    assert manager.status().installed is False
