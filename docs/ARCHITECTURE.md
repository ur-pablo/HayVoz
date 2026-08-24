# Architecture

HayVoz is a modular Python monolith with a local Core and optional integration
boundaries:

1. `app/ui`: Typer CLI and rendering.
2. `app/sessions`: session lifecycle and recovery.
3. `app/audio`: FFmpeg capture and chunk finalization.
4. `app/transcription`: local faster-whisper processing.
5. `app/core`: fact-only `SessionContextService` for external consumers.
6. `app/analysis` and `app/assistant`: optional external intelligence workflows.
7. `app/llm`: provider-neutral contracts and the optional OpenAI adapter.
8. `app/storage`: SQLite repositories and migrations.
9. `app/config.py` and `app/local_config.py`: private configuration boundary.
10. `app/platform_support.py` and `app/system_service.py`: OS-specific adapters.
11. `app/browser`: bounded native inbox, browser registration, and automatic
    local import/transcription processor.
12. `app/integrations`: optional OpenAI and experimental MCP boundaries.
13. `extensions/web` and `extensions/safari`: shared capture UI plus platform
    native messaging adapters.

The CLI constructs a runtime and injects repositories/services. Audio, local
transcription, storage, session lifecycle, guides, and `SessionContextService` do
not require an LLM or the OpenAI SDK. External intelligence is reachable only
through an explicit optional integration and consent checks. The optional system
agent performs local orphan recovery and exposes no socket.

The supported local data flow is:

```text
Audio -> faster-whisper -> SQLite -> SessionContextService
                                      |              |
                                      v              v
                             optional OpenAI     experimental MCP
```

`SessionContextService` is the only supported read boundary for external
consumers. It returns facts, not summaries, decisions, pain points, or other
generative inferences.

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
