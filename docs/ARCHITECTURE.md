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
10. `extensions/web`: permission-free Chrome/Safari capture companion.

The CLI constructs a runtime and injects repositories/services. Audio and text
processing do not depend on the UI. External AI calls are reachable only through
an explicit provider boundary and consent checks. The optional system agent
performs local orphan recovery and exposes no socket.

The browser companion is intentionally disconnected from application internals.
It downloads audio locally after explicit native browser selection. The
`import-audio` command validates and normalizes that user-selected file to FLAC,
then persists a completed `local_only` session. No extension bridge, local web
server, native messaging port, or automatic metadata ingestion exists.

See [SPEC.md](../SPEC.md) and the [ADR index](adr/README.md).
