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
2. Create a short-lived `feat/`, `fix/`, `chore/`, `docs/`, `refactor/`,
   `test/`, or `release/` branch. Do not develop or push directly on `main`.
3. Add or update an ADR when a durable architectural decision changes.
4. Add tests before or with implementation.
5. Run `uv run python scripts/version.py check`, `uv run pytest`,
   `uv run ruff check app tests`,
   `uv run ruff format --check app tests`, and
   `uv run python -m compileall -q app tests`.
   On macOS, also run `swift build` to compile the Safari native handler.
6. Run `sh -n install.sh uninstall.sh scripts/package-safari-extension.sh`, a
   secret scan, and `git diff --check` before
   submitting.
7. Push the topic branch and open a pull request into `main`. Merge only after
   required checks pass, then delete the branch.
8. Keep commits focused and explain migrations and privacy effects.

See [docs/BRANCHING.md](docs/BRANCHING.md) for branch naming, version updates,
and the release-tag workflow.

## Design rules

- Network access must be explicit and documented.
- Never add telemetry or a listening network service.
- Stable internal values are language-neutral; translated UI is a presentation
  layer.
- Provider secrets stay in environment/private config and never in persistence.
- New platforms require unit tests plus an explicit validation status.
- Data migrations are transactional and preserve recoverable user data.
- Browser code may declare only `nativeMessaging`; it must retain no page/host,
  history, storage, content-script, or network capability and must pass
  `tests/test_browser_extension.py` plus the browser inbox/processor tests.
- Native bridge changes must preserve canonical capture IDs, bounded messages,
  the Chrome origin allowlist, Safari App Group isolation, and sanitized replies.
- Uninstall behavior must preserve private user data unless a separate, explicit
  destructive data-removal feature is designed and approved.

## Licensing

Contributions are accepted under GPLv3 or later, matching the repository license.
By submitting a contribution, you confirm you have the right to license it on
those terms.
