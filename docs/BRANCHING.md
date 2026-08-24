# Branching and Versioning

HayVoz uses short-lived branches, pull requests, semantic versions, and signed
release tags. Development does not happen directly on `main`.

## Branch workflow

1. Synchronize local `main` with `origin/main`.
2. Create one focused branch using a descriptive prefix:
   `feat/`, `fix/`, `chore/`, `docs/`, `refactor/`, `test/`, or `release/`.
3. Commit and push only that branch.
4. Open a pull request into `main`, complete the privacy checklist, and wait for
   every required check.
5. Merge through GitHub. Delete the branch after the merge.

Examples: `feat/live-speaker-labels`, `fix/browser-retry`, and
`release/0.9.0`. Force-pushing shared branches and direct pushes to `main` are
not part of the project workflow.

## Version source

HayVoz follows stable [Semantic Versioning](https://semver.org/):

- `MAJOR` for incompatible behavior or storage/protocol changes;
- `MINOR` for backward-compatible functionality;
- `PATCH` for backward-compatible corrections.

`app/__init__.py` is the canonical version source. Hatch reads it when building
the Python package. The Chrome/Safari manifest must carry the same version.
Check or update every synchronized field with:

```bash
uv run python scripts/version.py current
uv run python scripts/version.py check
uv run python scripts/version.py set 0.9.0
uv lock
```

The updater accepts stable `X.Y.Z` versions. A future prerelease scheme requires
an explicit design because browser manifests and Python packages encode
prereleases differently.

## Releases

A release is prepared on `release/X.Y.Z`. That branch updates the version,
lockfile, changelog, and validation evidence in one pull request. After merge,
the maintainer creates and pushes a signed `vX.Y.Z` tag on the reviewed commit.
The release workflow rejects a tag that differs from the canonical version,
re-runs validation, builds the wheel and source archive, creates SHA-256
checksums, and publishes the GitHub release artifacts.
