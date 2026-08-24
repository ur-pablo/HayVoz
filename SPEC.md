# HayVoz Evolution Specification

- Status: Accepted for implementation
- Target release: 0.8.0
- Date: 2026-08-24
- License: GNU GPL v3.0 or later

## 1. Purpose

HayVoz is a local-first meeting capture, transcription, storage, and session
context layer. It records and transcribes locally and remains fully useful when
no generative integration is installed. Optional external intelligence consumes
fact-only session context after an explicit user decision.

This specification defines the local Core, the optional OpenAI integration, the
experimental read-only MCP boundary, an optional operating-system user service,
a zero-first-party-tracking policy, and public distribution under GPLv3.

## 2. Interpretation of confidentiality and GPLv3

The source code is public and redistributable under GPLv3. “Confidential” means
that recordings, transcripts, guides, analyses, credentials, identifiers, logs,
and local configuration belong to the user and are private by default. User data
must never be committed, bundled, uploaded, or exposed by a background service.

GPLv3 does not make user data public. It governs distribution of the program and
modified program source, not the private files processed by a user.

## 3. Goals

1. Keep capture, transcription, sessions, storage, guides, and context useful
   without an LLM or API key.
2. Keep stable, language-neutral internal identifiers and persistence values.
3. Expose fact-only session context through one stable Core service.
4. Keep every optional AI request opt-in, text-only, stateless, and non-persistent
   at the provider API when the provider supports that control.
5. Provide an optional per-user operating-system service with no listening port.
6. Make application data live outside the source checkout by default.
7. Establish documentation, contribution, security, privacy, licensing, release,
   and architecture records suitable for a public repository.
8. Retain Python while separating platform-specific audio and service behavior.
9. Publish a validated `main` branch to `ur-pablo/HayVoz`.
10. Provide an explicit Chrome/Safari audio capture path that automatically
    saves, imports, and transcribes through an allowlisted local native bridge.
11. Keep session-specific project context in an ignored local file.
12. Provide an uninstall path that removes executables and integrations while
    preserving private user data.

Session tooling reads the local context at the start and updates it before handoff.
Tracked agent instructions define this lifecycle while prohibiting credentials,
meeting content, participant identities, customer data, and private data paths in
the context file.

## 4. Non-goals for 0.8.0

- Translating every message, help string, or document.
- Claiming hardware-validated parity on macOS, Windows, and Linux.
- Providing a GUI, tray icon, signed native package, or app-store distribution.
- Running a local HTTP server, opening a port, or exposing IPC to other users.
- Silently installing an operating-system service.
- Sending crash reports, analytics, update checks, usage metrics, or device IDs.
- Requiring an AI SDK, API key, or external network for Core operation.
- Supporting arbitrary AI SDKs or provider frameworks in-process.
- Encrypting recordings at rest in 0.8.0. Permissions and isolation are enforced;
  application-level encryption is scheduled as a later phase.
- Reading meeting pages, URLs, participants, cookies, history, or browser storage.
- Automatic meeting detection, capture start, or publication. Import and local
  transcription are automatic only after the user explicitly records and stops.
- Chrome Web Store or Safari App Store distribution in this phase.

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
later full-message translation, but this release localizes only the feature term and
exposes aliases that route to the same implementation.

### 5.3 Compatibility migration

Existing sessions using the previous mode value are migrated transactionally to
`assistant`. Existing incremental suggestions and batching configuration are
copied into the new schema. The old public command and mode are not advertised.

## 6. Configuration and optional integration credentials

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

### 6.3 Optional OpenAI integration environment contract

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
- sending reviewed text to the optional OpenAI integration after explicit consent;
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

The installed component is a per-user background recovery and browser-processing
agent. It periodically recovers orphaned recorder processes and consumes completed
captures from owner-only inbox directories. It does not start recording, contact
an AI provider, expose a network port, or accept remote commands.

Adapters:

- macOS: user LaunchAgent in `~/Library/LaunchAgents`;
- Linux: systemd user service in `~/.config/systemd/user`;
- Windows: Task Scheduler task running at user logon.

Installation and uninstallation are explicit. Generated service definitions must
use absolute executable/config paths and must never embed credentials.

## 9. Cross-platform strategy and language decision

Python remains the implementation language for 0.8.0. The application logic,
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

### 9.1 Browser companion

The browser boundary uses a shared Manifest V3 WebExtension in Chrome and Safari.
It declares only `nativeMessaging`: no page/host/history/storage permission,
content script, background worker, or network client. An extension-owned page
calls the standard display-capture API only after a user gesture, and the native
picker remains the authority for choosing a meeting tab and audio.

Only shared audio tracks enter `MediaRecorder`; video is never encoded or saved.
When capture stops, the extension sends bounded chunks to the local native host.
Chrome accepts messages only from the stable, allowlisted extension identity.
Safari writes through its sandboxed native extension into a named App Group.
Neither bridge opens a port or receives network traffic.

The user service assembles the chunks, normalizes audio to private mono 16 kHz
FLAC, creates a completed session, runs configured local Whisper transcription,
and stores the transcript without a manual import/transcribe step. Successful
processing removes raw inbox chunks; failure preserves a local audio fallback.
Only status, session ID, segment count, or a sanitized error returns to the
extension—never transcript content, credentials, URLs, participants, or paths.

Chrome uses the unpacked extension during development. Safari uses Apple's Xcode
WebExtension packaging flow plus an App Group. Neither path is described as
store-ready or hardware-validated until its manual checks are completed.

## 10. ChatGPT integration status

HayVoz distinguishes the local protocol implementation from actual availability
in a ChatGPT product or plan:

| Capability | Status |
| --- | --- |
| Local Core: capture, transcription, storage, and context | Supported |
| OpenAI API integration | Optional / supported |
| Local `hayvoz mcp` server over stdio | Experimental |
| Direct ChatGPT connection to a local stdio server | Not supported directly |
| ChatGPT through a supported remote MCP endpoint or Secure MCP Tunnel | To be validated |

The current MCP command is a development boundary. It does not prove that a
ChatGPT plan can consume it. OpenAI's current API documentation describes remote
MCP servers using a `server_url`; private servers may use Secure MCP Tunnel. HayVoz
does not install a tunnel, open an HTTP port, publish data, or synchronize local
sessions automatically as part of this release.

## 11. Installer and distribution

`install.sh` targets macOS and Linux shells. It:

1. validates supported OS and required commands;
2. installs `uv` only with explicit confirmation if missing;
3. installs the application in an isolated environment;
4. creates the private configuration and data directories;
5. sets restrictive permissions;
6. optionally registers the browser bridge and per-user processing service;
7. optionally installs the per-user recovery service;
8. runs `hayvoz doctor`.

`uninstall.sh` removes the registered browser bridge, user service, and—unless
`--keep-tool` is supplied—the isolated CLI installation. It never deletes private
configuration, models, recordings, transcripts, or SQLite state. Deleting private
data remains a separate, deliberate user action.

Windows installation is documented separately and is prepared for a future
native PowerShell/MSIX installer. A shell script executed through WSL or Git Bash
must not be presented as native Windows service installation.

## 12. Documentation deliverables

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
- `docs/BROWSER_EXTENSION.md`
- `docs/THREAT_MODEL.md`
- `docs/adr/README.md` and numbered ADRs

## 13. Acceptance criteria

1. Capture, transcription, sessions, storage, guides, `transcript`, and
   `context` work without OpenAI credentials or SDK installation.
2. No Core module imports `openai`, `OpenAIProvider`, or an integration factory.
3. `SessionContextService` is the only read boundary used by external
   integrations and exposes facts without generative inference.
4. OpenAI remains functional through the optional `hayvoz[openai]` extra and
   its absence never makes `doctor` fail.
5. `hayvoz mcp` is a local stdio server with only read operations and no arbitrary
   filesystem, shell, session mutation, or recording controls.
6. The MCP server being functional is reported separately from ChatGPT
   connectivity, which remains unsupported directly for local stdio.
7. `assistant` and the configured localized alias reach the same command.
8. Changing locale does not change persisted values.
9. AI credentials load from environment/private config and never enter logs or
   SQLite.
10. External AI calls still require explicit consent and use non-storage controls.
11. Default data and config paths are outside the checkout.
12. The system service is optional, user-scoped, port-free, and removable.
13. macOS tests and smoke checks pass; Windows/Linux command generation is tested.
14. Secret and privacy scans find no committed credentials or user artifacts.
15. The repository contains GPLv3 licensing and the listed documentation.
16. `CONTEXT.md` exists locally, is ignored by Git, and contains no secrets or
    meeting data.
17. The extension manifest has only `nativeMessaging`, no page/host permissions,
    and its source has no network client or page injection.
18. A browser-format audio fixture imports transactionally as a completed,
    private `local_only` session; failed conversion leaves no session or partial
    output.
19. Stopping an extension capture queues automatic local import/transcription and
    returns a persisted session result without manual CLI commands.
20. Browser messages use bounded chunks, canonical UUID paths, an allowlisted
    Chrome origin or Safari App Group, and owner-only local files.
21. Uninstall removes program integrations but preserves all private user data.

## 14. Delivery phases

### Phase 0 — Specification and governance

This document, ADR structure, privacy boundaries, acceptance criteria.

### Phase 1 — Local Core and context boundary

Keep local capture, storage, transcription, guides, and session state independent
of generative intelligence. Add `SessionContextService`, `hayvoz context`, and
read-only integration contracts.

### Phase 2 — Optional OpenAI integration

Keep the existing OpenAI API integration functional behind an optional package
extra and explicit consent. Core tests and imports must not require its SDK.

### Phase 3 — Platform and system integration

Add FFmpeg platform adapters and optional macOS/Linux/Windows user services.

### Phase 4 — Public project readiness

Add GPLv3, security/privacy/contribution/release documentation, installer,
repository metadata, CI scaffolding, and publish `main`.

### Phase 5 — Native packaging and validation

Hardware validation on Windows/Linux, signed macOS app, Windows MSIX, Linux
packages, Chrome/Safari manual capture validation, browser-store packaging,
auto-generated completions, and reproducible release artifacts.

### Phase 6 — Encrypted local vault

Optional encryption at rest, OS keychain integration, retention policies,
selective export, secure deletion semantics, and backup guidance.

### Phase 7 — Full localization

Message catalogs, translated help and documentation, contributor translation
workflow, locale QA, and right-to-left validation.

### Phase 8 — Integration and audio evolution

Validate a supported remote/tunneled MCP deployment if a real consumer requires
it. Any future audio evolution remains separate from generative integrations.

## 15. Repository description

Local-first meeting recorder, transcription, and session context layer with
optional OpenAI and experimental MCP integrations.
