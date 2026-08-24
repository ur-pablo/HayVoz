#!/usr/bin/env python3
"""Validate or update HayVoz's synchronized semantic version fields."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_FILE = ROOT / "app" / "__init__.py"
MANIFEST_FILE = ROOT / "extensions" / "web" / "manifest.json"
VERSION_PATTERN = re.compile(
    r'^__version__ = "(?P<version>\d+\.\d+\.\d+)"$', re.MULTILINE
)
SEMVER_PATTERN = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


class VersionError(RuntimeError):
    """Raised when version metadata is invalid or inconsistent."""


def package_version() -> str:
    content = PACKAGE_FILE.read_text(encoding="utf-8")
    match = VERSION_PATTERN.search(content)
    if match is None:
        raise VersionError(f"No version found in {PACKAGE_FILE.relative_to(ROOT)}")
    return match.group("version")


def manifest_version() -> str:
    manifest = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    version = manifest.get("version")
    if not isinstance(version, str):
        raise VersionError("Browser manifest version is missing")
    return version


def validate(expected: str | None = None) -> str:
    version = package_version()
    if SEMVER_PATTERN.fullmatch(version) is None:
        raise VersionError(f"Invalid stable semantic version: {version}")
    if manifest_version() != version:
        raise VersionError(
            f"Version mismatch: package={version}, browser={manifest_version()}"
        )
    if expected is not None and version != expected:
        raise VersionError(f"Expected {expected}, found {version}")
    return version


def set_version(version: str) -> None:
    if SEMVER_PATTERN.fullmatch(version) is None:
        raise VersionError("Version must use stable X.Y.Z semantic versioning")
    package = PACKAGE_FILE.read_text(encoding="utf-8")
    manifest = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    if not isinstance(manifest.get("version"), str):
        raise VersionError("Browser manifest version is missing")
    updated, replacements = VERSION_PATTERN.subn(
        f'__version__ = "{version}"', package, count=1
    )
    if replacements != 1:
        raise VersionError("Package version could not be updated safely")

    manifest["version"] = version
    _atomic_write(PACKAGE_FILE, updated)
    _atomic_write(
        MANIFEST_FILE,
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
    )


def _atomic_write(path: Path, content: str) -> None:
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("current", help="print the canonical version")
    check = subcommands.add_parser("check", help="validate all version fields")
    check.add_argument("--expect", help="require this exact version")
    update = subcommands.add_parser("set", help="set all version fields")
    update.add_argument("version", help="stable semantic version in X.Y.Z form")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.command == "current":
            print(package_version())
        elif args.command == "check":
            print(validate(args.expect))
        else:
            set_version(args.version)
            print(validate(args.version))
    except VersionError as error:
        print(f"version error: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
