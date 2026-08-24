# ADR 0007: Branch and release versioning

- Status: Accepted
- Date: 2026-08-24

## Context

The package and browser extension exposed the same version through manually
maintained fields. Development had no enforceable repository convention for
isolating changes before they reached `main`.

## Decision

Use short-lived topic branches and pull requests for all development. Keep
`main` releasable and identify releases with signed `vX.Y.Z` tags.

`app/__init__.py` is the canonical stable semantic version. Hatch reads that
value for Python builds, while `scripts/version.py` synchronizes and validates
the browser manifest. CI rejects inconsistent versions. A tag-triggered workflow
validates that the tag and source version match before publishing artifacts.

## Consequences

- Each change has an isolated review and CI boundary.
- Python and browser artifacts cannot silently drift in version.
- Releases remain deliberate; ordinary branch pushes publish nothing.
- Stable `X.Y.Z` is supported now. Prerelease identifiers require a later
  decision that maps Python and browser version formats explicitly.
