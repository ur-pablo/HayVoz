# Release Process

1. Move relevant entries from `Unreleased` in `CHANGELOG.md` to a dated semantic
   version section.
2. Run the locked test, lint, formatting, compile, CLI-help, shell-syntax,
   Markdown-link, privacy, and secret checks described in `CONTRIBUTING.md`.
3. Confirm the Windows/Linux claims still say experimental unless hardware
   validation evidence exists.
4. Confirm Chrome/Safari claims still say experimental unless real meeting-tab
   capture, stop, download, import, and transcription have been manually checked.
5. Build wheel and source distribution with `uv build`; inspect both archives to
   ensure no private data, config, caches, models, logs, or generated graphs are
   present.
6. Sign the Git tag and future native artifacts. Publish only from a clean
   checkout of the reviewed commit.
7. Verify checksums, license inclusion, repository metadata, and installation in
   a new user profile before announcing the release.

The project does not perform silent update checks. Release discovery remains an
explicit user action until a privacy-preserving signed updater is designed and
accepted in a future ADR.
