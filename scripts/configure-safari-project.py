#!/usr/bin/env python3
"""Inject HayVoz's native handler and App Group into a generated Safari project."""

from __future__ import annotations

import plistlib
import shutil
import sys
from pathlib import Path

APP_GROUP = "group.com.urpablo.hayvoz"


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: configure-safari-project.py PROJECT_DIR")
    project = Path(sys.argv[1]).expanduser().resolve()
    repository = Path(__file__).resolve().parents[1]
    handlers = list(project.rglob("SafariWebExtensionHandler.swift"))
    if not handlers:
        raise SystemExit(
            "No se encontró SafariWebExtensionHandler.swift en el proyecto generado."
        )
    template = repository / "extensions" / "safari" / "SafariWebExtensionHandler.swift"
    for handler in handlers:
        shutil.copyfile(template, handler)

    entitlements = list(project.rglob("*.entitlements"))
    if not entitlements:
        raise SystemExit("No se encontraron entitlements para configurar el App Group.")
    for path in entitlements:
        with path.open("rb") as source:
            payload = plistlib.load(source)
        groups = payload.setdefault("com.apple.security.application-groups", [])
        if APP_GROUP not in groups:
            groups.append(APP_GROUP)
        with path.open("wb") as destination:
            plistlib.dump(payload, destination, sort_keys=True)
    print(
        f"Safari configurado: {len(handlers)} handler(s), "
        f"{len(entitlements)} entitlement(s)."
    )


if __name__ == "__main__":
    main()
