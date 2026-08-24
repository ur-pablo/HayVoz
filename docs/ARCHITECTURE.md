# Architecture

HayVoz is a modular Python monolith with explicit boundaries:

1. `app/ui`: Typer CLI and rendering.
2. `app/sessions`: session lifecycle and recovery.
3. `app/audio`: FFmpeg capture and chunk finalization.
4. `app/transcription`: local faster-whisper processing.
5. `app/analysis` and `app/assistant`: reviewed and incremental reasoning.
6. `app/llm`: provider-neutral contracts and configured adapter factory.
7. `app/storage`: SQLite repositories and migrations.
8. `app/config.py` and `app/local_config.py`: private configuration boundary.
9. `app/platform_support.py` and `app/system_service.py`: OS-specific adapters.
10. `app/browser`: bounded native inbox, browser registration, and automatic
    local import/transcription processor.
11. `extensions/web` and `extensions/safari`: shared capture UI plus platform
    native messaging adapters.

The CLI constructs a runtime and injects repositories/services. Audio and text
processing do not depend on the UI. External AI calls are reachable only through
an explicit provider boundary and consent checks. The optional system agent
performs local orphan recovery and exposes no socket.

The browser companion reaches the application only through native messaging—no
HTTP server or listening socket. Chrome invokes the installed `hayvoz-native`
stdio host from a fixed allowlisted extension ID. Safari invokes its containing
native extension, which writes into a named App Group. Both produce the same
owner-only inbox protocol. The user service claims completed captures, delegates
normalization to `AudioImportService`, delegates offline work to
`TranscriptionService`, and returns only an allowlisted status summary.

Successful processing removes the raw inbox representation after the canonical
FLAC and transcript are persisted. Failed processing retains recovery material.
The existing `import-audio` command remains available for arbitrary user-selected
files but is no longer required by the extension workflow.

See [SPEC.md](../SPEC.md) and the [ADR index](adr/README.md).
