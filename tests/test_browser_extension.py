from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXTENSION = ROOT / "extensions" / "web"


def test_manifest_has_no_page_or_network_permissions() -> None:
    manifest = json.loads((EXTENSION / "manifest.json").read_text(encoding="utf-8"))

    assert manifest["manifest_version"] == 3
    assert manifest["action"]["default_popup"] == "popup.html"
    assert manifest["permissions"] == ["nativeMessaging"]
    assert "host_permissions" not in manifest
    assert "content_scripts" not in manifest
    assert "background" not in manifest


def test_manifest_has_stable_allowlisted_chrome_identity() -> None:
    manifest = json.loads((EXTENSION / "manifest.json").read_text(encoding="utf-8"))
    digest = hashlib.sha256(base64.b64decode(manifest["key"])).hexdigest()[:32]
    extension_id = "".join(chr(ord("a") + int(value, 16)) for value in digest)

    assert extension_id == "fgnjijejmeghpcclbbegoapmlimghlcb"


def test_extension_is_self_contained_and_has_no_network_client() -> None:
    manifest = json.loads((EXTENSION / "manifest.json").read_text(encoding="utf-8"))
    assert (EXTENSION / manifest["action"]["default_popup"]).is_file()
    for name in ("popup.html", "capture.html", "capture.js", "styles.css"):
        assert (EXTENSION / name).is_file()

    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in EXTENSION.iterdir()
        if path.suffix in {".html", ".js", ".css", ".json"}
    )
    for forbidden in (
        "fetch(",
        "XMLHttpRequest",
        "WebSocket",
        "sendBeacon",
        "http://",
        "https://",
    ):
        assert forbidden not in source


def test_capture_uses_explicit_display_selection_and_audio_only_recording() -> None:
    source = (EXTENSION / "capture.js").read_text(encoding="utf-8")

    assert "getDisplayMedia" in source
    assert "getAudioTracks" in source
    assert "new MediaStream(audioTracks)" in source
    assert "new MediaRecorder(audioStream" in source
    assert "getVideoTracks" in source
    assert "sendNativeMessage" in source
    assert "UPLOAD_CHUNK_BYTES = 384 * 1024" in source
    assert "Transcripción guardada automáticamente" in source


def test_safari_bridge_uses_native_messaging_and_private_app_group() -> None:
    source = (ROOT / "extensions/safari/SafariWebExtensionHandler.swift").read_text(
        encoding="utf-8"
    )

    assert "NSExtensionRequestHandling" in source
    assert "beginRequest(with" in source
    assert "group.com.urpablo.hayvoz" in source
    assert "browser-inbox" in source
