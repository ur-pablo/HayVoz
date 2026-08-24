# ADR 0001: Retain Python

- Status: Accepted
- Date: 2026-08-24

## Decision

Retain Python for the domain, CLI, storage, transcription orchestration, and AI
provider boundary. Isolate OS-specific capture/process/service behavior.

## Consequences

The project avoids a high-risk rewrite and keeps its tested logic. Windows/Linux
still require hardware validation. Narrow native helpers remain possible if
measured platform limitations justify them.
