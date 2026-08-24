# HayVoz Evolution Specification

- Status: Accepted for implementation
- Target release: 0.6.0
- Date: 2026-08-24
- License: GNU GPL v3.0 or later

## 1. Purpose

HayVoz is a privacy-first meeting recorder and interview assistant. It records
locally, transcribes locally by default, and performs external AI processing
only after an explicit user decision.

This specification defines the evolution from the legacy incremental-interview
feature to a multilingual Assistant capability, introduces provider credentials through
environment-backed private configuration, adds an optional operating-system
user service, establishes a zero-first-party-tracking policy, and prepares the
project for public distribution under GPLv3.

## 2. Interpretation of confidentiality and GPLv3

The source code is public and redistributable under GPLv3. “Confidential” means
that recordings, transcripts, guides, analyses, credentials, identifiers, logs,
and local configuration belong to the user and are private by default. User data
must never be committed, bundled, uploaded, or exposed by a background service.

GPLv3 does not make user data public. It governs distribution of the program and
modified program source, not the private files processed by a user.

## 3. Goals

1. Replace the legacy feature name with Assistant across public and internal APIs.
2. Localize the word “Assistant” according to the configured or detected locale
   without translating the entire application in this release.
3. Keep stable, language-neutral internal identifiers and persistence values.
4. Load AI provider credentials from process environment or a private local
   configuration file, with process environment taking precedence.
5. Keep every AI request opt-in, text-only, stateless, and non-persistent at the
   provider API when the provider supports that control.
6. Provide an optional per-user operating-system service with no listening port.
7. Make application data live outside the source checkout by default.
8. Establish documentation, contribution, security, privacy, licensing, release,
   and architecture records suitable for a public repository.
9. Retain Python while separating platform-specific audio and service behavior.
10. Publish a validated `main` branch to `ur-pablo/HayVoz`.

## 4. Non-goals for 0.6.0

- Translating every message, help string, or document.
- Claiming hardware-validated parity on macOS, Windows, and Linux.
- Providing a GUI, tray icon, signed native package, or app-store distribution.
- Running a local HTTP server, opening a port, or exposing IPC to other users.
- Silently installing an operating-system service.
- Sending crash reports, analytics, update checks, usage metrics, or device IDs.
- Supporting arbitrary AI SDKs in-process. The first adapter remains
  OpenAI/OpenAI-compatible behind a provider boundary.
- Encrypting recordings at rest in 0.6.0. Permissions and isolation are enforced;
  application-level encryption is scheduled as a later phase.

## 5. Terminology and multilingual capability

### 5.1 Stable internal vocabulary

- Persisted mode: `assistant`
- Python domain name: `Assistant`
- Stable English CLI alias: `assistant`
- Locale setting: `HAYVOZ_LANGUAGE`

Internal identifiers are never translated. This avoids database and automation
breakage when the user changes language.

### 5.2 Localized public term

The first catalog provides the Assistant term for a small initial locale set:

| Locale | Term | CLI alias |
| --- | --- | --- |
| `es` | Asistente | `asistente` |
| `en` | Assistant | `assistant` |
| `pt` | Assistente | `assistente` |
| `fr` | Assistant | `assistant` |
| `de` | Assistent | `assistent` |
| `it` | Assistente | `assistente` |

Locale selection order:

1. `HAYVOZ_LANGUAGE`
2. private config file
3. operating-system locale
4. `en`

Unknown locales fall back to English. The catalog and resolver are designed for
later full-message translation, but 0.6.0 localizes only the feature term and
exposes aliases that route to the same implementation.

### 5.3 Compatibility migration

Existing sessions using the previous mode value are migrated transactionally to
`assistant`. Existing incremental suggestions and batching configuration are
copied into the new schema. The old public command and mode are not advertised.

## 6. Configuration and AI credentials

### 6.1 Configuration precedence

1. Process environment
2. User-local `config.env`
3. safe built-in defaults

The optional `HAYVOZ_CONFIG_FILE` selects an explicit config file. Otherwise:

- macOS: `~/Library/Application Support/HayVoz/config.env`
- Windows: `%APPDATA%\HayVoz\config.env`
- Linux: `${XDG_CONFIG_HOME:-~/.config}/hayvoz/config.env`

The file must be readable only by its owner where the platform supports POSIX
permissions. It is never searched inside Git history and is ignored if placed in
the checkout.

### 6.2 Data directories

- macOS: `~/Library/Application Support/HayVoz/data`
- Windows: `%LOCALAPPDATA%\HayVoz\data`
- Linux: `${XDG_DATA_HOME:-~/.local/share}/hayvoz`

`HAYVOZ_DATA_DIR` overrides the default. Existing local development data may be
kept by placing that explicit path in the private config file.

### 6.3 AI environment contract

- `HAYVOZ_AI_PROVIDER` (`openai` initially)
- `HAYVOZ_AI_API_KEY`
- `HAYVOZ_AI_MODEL`
- `HAYVOZ_AI_BASE_URL` (optional OpenAI-compatible endpoint)
- `HAYVOZ_AI_TIMEOUT_SECONDS`

Standard provider variables such as `OPENAI_API_KEY`, `OPENAI_MODEL`, and
`OPENAI_BASE_URL` are accepted as lower-priority compatibility inputs. Secrets
must not appear in `repr`, logs, exceptions, subprocess arguments, database
records, documentation examples, or Git.

## 7. Privacy and zero tracking

“Zero tracking” means HayVoz itself has no telemetry, analytics, advertising,
fingerprinting, crash reporting, remote logging, silent update checks, or unique
installation identifier.

Network access is limited to explicit user actions:

- downloading a selected local transcription model;
- sending reviewed text to the configured AI provider after explicit consent;
- periodic Assistant suggestions only for a session started with explicit
  external-processing consent.

Audio is never sent to an AI provider by HayVoz. Provider requests omit the local
session ID and use provider non-storage controls where supported. Third-party
providers may still process metadata under their own terms; documentation must
state this boundary instead of claiming that an opted-in external request is
private from the provider.

Local controls:

- config files: owner-only permissions;
- data directories: owner-only permissions where supported;
- database and generated text: private local files;
- logs: structured, local, content-free, and secret-redacted;
- repository ignore rules: credentials, user data, models, logs, caches, and
  generated graphs are excluded;
- service: user scope only, no root requirement, no inbound socket.

## 8. Operating-system extension

HayVoz exposes an optional `system` command group:

- `hayvoz system install`
- `hayvoz system uninstall`
- `hayvoz system status`
- `hayvoz system run`

The installed component is a per-user background recovery agent. It periodically
checks local session state and recovers orphaned recorder processes. It does not
record automatically, contact a provider, expose a network port, or accept remote
commands.

Adapters:

- macOS: user LaunchAgent in `~/Library/LaunchAgents`;
- Linux: systemd user service in `~/.config/systemd/user`;
- Windows: Task Scheduler task running at user logon.

Installation and uninstallation are explicit. Generated service definitions must
use absolute executable/config paths and must never embed credentials.

## 9. Cross-platform strategy and language decision

Python remains the implementation language for 0.6.0. The application logic,
SQLite, Typer CLI, provider boundary, and faster-whisper integration are portable.
The current limitations come from platform-specific capture and process control,
not from Python itself.

The platform boundary will select:

- macOS: FFmpeg AVFoundation;
- Windows: FFmpeg DirectShow;
- Linux: FFmpeg PulseAudio by default, with ALSA as an explicit alternative.

macOS remains the hardware-validated platform. Windows and Linux receive command
construction, device discovery, service adapters, unit tests, and clear
experimental status until hardware CI/manual validation exists.

A language rewrite is reconsidered only if profiling demonstrates that Python
causes a material resource, packaging, security, or native-integration problem
that cannot be solved by isolation or a small native helper. Rust or Swift/Kotlin
helpers may later cover narrow platform integrations without rewriting the
domain layer.

## 10. Installer and distribution

`install.sh` targets macOS and Linux shells. It:

1. validates supported OS and required commands;
2. installs `uv` only with explicit confirmation if missing;
3. installs the application in an isolated environment;
4. creates the private configuration and data directories;
5. sets restrictive permissions;
6. optionally installs the per-user system service;
7. runs `hayvoz doctor`.

Windows installation is documented separately and is prepared for a future
native PowerShell/MSIX installer. A shell script executed through WSL or Git Bash
must not be presented as native Windows service installation.

## 11. Documentation deliverables

- `README.md`
- `CHANGELOG.md`
- `CONTRIBUTING.md`
- `SECURITY.md`
- `SUPPORT.md`
- `PRIVACY.md`
- `LICENSE`
- `docs/ARCHITECTURE.md`
- `docs/CONFIGURATION.md`
- `docs/INSTALLATION.md`
- `docs/I18N.md`
- `docs/PORTABILITY.md`
- `docs/RELEASE.md`
- `docs/SYSTEM_EXTENSION.md`
- `docs/THREAT_MODEL.md`
- `docs/adr/README.md` and numbered ADRs

## 12. Acceptance criteria

1. No active public feature, symbol, command, setting, file, table, or test uses
   the previous feature name except an isolated compatibility migration.
2. `assistant` and the configured localized alias reach the same command.
3. Changing locale does not change persisted values.
4. AI credentials load from environment/private config and never enter logs or
   SQLite.
5. External AI calls still require explicit consent and use non-storage controls.
6. Default data and config paths are outside the checkout.
7. The system service is optional, user-scoped, port-free, and removable.
8. macOS tests and smoke checks pass; Windows/Linux command generation is tested.
9. Secret and privacy scans find no committed credentials or user artifacts.
10. The repository contains GPLv3 licensing and the listed documentation.
11. `main` is pushed to the requested GitHub remote with a concise description.

## 13. Delivery phases

### Phase 0 — Specification and governance

This document, ADR structure, privacy boundaries, acceptance criteria.

### Phase 1 — Assistant and i18n capability

Rename domain, storage, worker, recorder, CLI, tests, and docs. Add stable internal
identifiers, localized term resolver, aliases, and transactional legacy migration.

### Phase 2 — Private configuration and AI provider credentials

Move defaults outside the checkout, add secure config loading, environment-based
provider factory, permission enforcement, and secret-redaction tests.

### Phase 3 — Platform and system integration

Add FFmpeg platform adapters and optional macOS/Linux/Windows user services.

### Phase 4 — Public project readiness

Add GPLv3, security/privacy/contribution/release documentation, installer,
repository metadata, CI scaffolding, and publish `main`.

### Phase 5 — Native packaging and validation

Hardware validation on Windows/Linux, signed macOS app, Windows MSIX, Linux
packages, auto-generated completions, and reproducible release artifacts.

### Phase 6 — Encrypted local vault

Optional encryption at rest, OS keychain integration, retention policies,
selective export, secure deletion semantics, and backup guidance.

### Phase 7 — Full localization

Message catalogs, translated help and documentation, contributor translation
workflow, locale QA, and right-to-left validation.

### Phase 8 — Extensible AI and audio backends

Provider plugins, local LLM adapters, native audio helpers where justified,
policy-enforced data minimization, and sandboxed extension manifests.

## 14. Repository description

Privacy-first, multilingual meeting recorder and interview assistant with local
transcription, explicit AI consent, and zero first-party tracking.
