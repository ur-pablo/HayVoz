# Release Process

1. Start from an up-to-date `main` and create `release/X.Y.Z`. Never prepare a
   release directly on `main`.
2. Run `uv run python scripts/version.py set X.Y.Z`, then `uv lock`.
3. Move relevant entries from `Unreleased` in `CHANGELOG.md` to a dated semantic
   version section.
4. Run the locked version check, tests, lint, formatting, compile, CLI-help, shell-syntax,
   Markdown-link, privacy, and secret checks described in `CONTRIBUTING.md`.
5. Confirm the Windows/Linux claims still say experimental unless hardware
   validation evidence exists.
6. Confirm Chrome/Safari claims still say experimental unless real meeting-tab
   capture, stop, native transfer, automatic import, and transcription have been
   manually checked. Also exercise the local-download fallback.
7. Build wheel and source distribution with `uv build`; inspect both archives to
   ensure no private data, config, caches, models, logs, or generated graphs are
   present.
8. Push the release branch, merge its pull request only after required checks,
   and create a signed `vX.Y.Z` tag on that exact `main` commit.
9. Push the tag. The release workflow verifies the tag/version match, reruns
   validation, builds distributions, writes SHA-256 checksums, and publishes the
   GitHub release.
10. Verify checksums, license inclusion, repository metadata, and installation in
   a new user profile before announcing the release.

The project does not perform silent update checks. Release discovery remains an
explicit user action until a privacy-preserving signed updater is designed and
accepted in a future ADR.
