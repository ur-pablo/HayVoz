## Summary

Describe the user-visible outcome and why the change is needed.

## Validation

- [ ] `uv run python scripts/version.py check`
- [ ] `uv run ruff check app tests`
- [ ] `uv run ruff format --check app tests`
- [ ] `uv run pytest`
- [ ] Relevant platform/manual checks completed or limitations documented

## Privacy and compatibility

- [ ] No credentials, recordings, transcripts, private paths, or user data added
- [ ] Network, permissions, storage, migration, and uninstall effects documented
- [ ] `CHANGELOG.md` updated when the change is user-visible
