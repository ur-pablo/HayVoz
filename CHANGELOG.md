# Changelog

All notable changes follow [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and semantic versioning.

## [Unreleased]

### Added

- Canonical semantic version source, synchronized package/browser version
  checker and updater, and `hayvoz --version`.
- Topic-branch and pull-request workflow with a privacy-aware PR template.
- Tag-triggered release validation, distribution builds, checksums, and GitHub
  release publication.

### Changed

- Development now occurs on short-lived branches; `main` is reserved for
  reviewed merges.

## [0.8.0] - 2026-08-24

### Added

- Automatic browser capture ingestion and offline transcription through a local
  native-messaging bridge; manual import/transcribe commands are no longer needed.
- Owner-only, bounded browser inbox protocol with allowlisted Chrome identity and
  a Safari App Group native handler.
- `hayvoz browser install|status|uninstall`, top-level `hayvoz uninstall`, and a
  safe `uninstall.sh` that preserves all private user data.
- Safari project postprocessor for the native handler and App Group entitlement.
- A minimal Swift Package and macOS CI compilation for the Safari native handler.

### Changed

- The per-user service now processes completed browser captures in addition to
  recovering interrupted local sessions.
- Successful browser processing removes raw inbox chunks; failures preserve a
  local audio fallback for recovery.
- Raised the project version to 0.8.0.

### Security

- The extension declares only `nativeMessaging`; it still has no page/host,
  history, storage, content-script, background-worker, or network capability.
- Native messages use canonical UUID paths, 384 KiB chunks, sanitized status
  responses, a fixed Chrome origin allowlist, and owner-only local files.

## [0.7.0] - 2026-08-24

### Added

- Initially permission-free Manifest V3 capture companion shared by Chrome and
  Safari; superseded in 0.8.0 by the local native-messaging bridge.
- Explicit `hayvoz import-audio` workflow for browser downloads and other local
  audio files.
- Safari Xcode project packaging script and browser extension documentation.
- GitHub and README support links for Buy Me a Coffee.
- Git-ignored `CONTEXT.md` convention for session-local project context.
- Agent handoff instructions that keep the local context synchronized at session
  boundaries without committing it.

### Changed

- Browser-imported audio is normalized to private mono 16 kHz FLAC and persisted
  as a completed `local_only` session.
- Raised the project version to 0.7.0.

### Security

- The browser manifest declares no permissions or hosts and includes no content
  scripts, background worker, storage, or network client.
- Automated tests enforce the extension permission and no-network boundary.

## [0.6.0] - 2026-08-24

### Added

- Multilingual Assistant terminology and localized CLI aliases.
- Private per-user configuration and data locations.
- Environment-configured OpenAI/OpenAI-compatible provider credentials.
- Optional macOS LaunchAgent, Linux systemd user service, and Windows scheduled
  task adapters.
- AVFoundation, DirectShow, PulseAudio, and ALSA capture backends.
- Zero-first-party-tracking policy, threat model, security documentation, and
  secret-redacted logs.
- Automated macOS/Linux installer.
- GPLv3-or-later project license and public contribution documentation.

### Changed

- Renamed the incremental interview feature and its domain/storage components to
  Assistant.
- Moved default user data outside the source checkout.
- Raised the project version to 0.6.0.

### Security

- Configuration, data directories, SQLite, logs, and service definitions use
  owner-only permissions where supported.
- Provider secrets are excluded from representations, logs, persistence, and
  subprocess arguments.

## [0.5.0] - 2026-08-24

- Local recording, offline transcription, reviewed AI analysis, incremental
  interview assistance, and dual-source macOS recording MVP.
