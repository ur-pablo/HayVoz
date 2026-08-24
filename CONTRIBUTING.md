# Contributing to HayVoz

Thank you for helping improve a privacy-sensitive project.

## Development setup

```bash
git clone https://github.com/ur-pablo/HayVoz.git
cd HayVoz
uv sync --extra dev
uv run pytest
```

Do not use real recordings, transcripts, credentials, customer names, or private
guides in tests, issues, commits, fixtures, screenshots, or logs.

## Workflow

1. Open an issue for behavior, privacy-boundary, schema, or architecture changes.
2. Add or update an ADR when a durable architectural decision changes.
3. Add tests before or with implementation.
4. Run `uv run pytest`, `uv run ruff check app tests`,
   `uv run ruff format --check app tests`, and
   `uv run python -m compileall -q app tests`.
5. Run `sh -n install.sh`, a secret scan, and `git diff --check` before
   submitting.
6. Keep commits focused and explain migrations and privacy effects.

## Design rules

- Network access must be explicit and documented.
- Never add telemetry or a listening network service.
- Stable internal values are language-neutral; translated UI is a presentation
  layer.
- Provider secrets stay in environment/private config and never in persistence.
- New platforms require unit tests plus an explicit validation status.
- Data migrations are transactional and preserve recoverable user data.

## Licensing

Contributions are accepted under GPLv3 or later, matching the repository license.
By submitting a contribution, you confirm you have the right to license it on
those terms.
