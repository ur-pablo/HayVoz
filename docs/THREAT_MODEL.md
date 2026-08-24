# Threat Model

## Protected assets

Credentials, audio, transcripts, guides, analyses, session metadata, local paths,
logs, and model/provider choices.

## Trust boundaries

1. Local user and filesystem.
2. FFmpeg and local model runtime.
3. Explicit model-download source.
4. User-configured AI provider after consent.
5. Git/GitHub source distribution, which must never include runtime assets.
6. Browser and operating-system capture picker after an explicit user gesture.

## Threats and controls

| Threat | Control | Residual risk |
| --- | --- | --- |
| Accidental Git publication | ignore rules and secret scans | manual force-add remains possible |
| Secret leakage in logs | redaction and content-free structured fields | unknown third-party exception text |
| Prompt injection from transcript | instructions mark content untrusted; structured schema | provider model can still fail |
| Silent external processing | explicit consent and local-only persistence | user may authorize provider processing |
| Remote exploitation | no listener, no inbound IPC, user-scoped agent | local account compromise |
| Background credential exposure | recovery agent discards AI credentials | local config remains a trust boundary |
| Cross-user file access | owner-only permissions where supported | platform/backup ACL configuration |
| Corrupt/interrupted capture | transactional state and conservative recovery | final audio block may be incomplete |
| Dependency compromise | lockfile and isolated environment | upstream/package-index compromise |
| Extension reads browsing data | no host/page permissions, scripts, URL access, storage, or background worker | browser/runtime compromise |
| Unintended tab capture | native picker, visible browser indicator, explicit stop, track release | user can select the wrong source |
| Extension exfiltration | no network permission or network client; static policy tests | browser itself remains a trust boundary |

## Security invariants

- No telemetry dependency or endpoint.
- No credentials in command arguments, SQLite, logs, docs, or Git.
- No AI request without an allowed session/action.
- No audio in AI requests.
- No service installation without an explicit command.
- No extension capture without a user gesture and native source selection.
