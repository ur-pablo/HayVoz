# ADR 0005: Permission-free browser capture companion

- Status: Accepted
- Date: 2026-08-24

## Context

Meeting audio in Chrome and Safari can be selected by the user through the
browser's display-capture prompt. A conventional extension could request host,
tab, storage, or content-script permissions, but those capabilities expand the
amount of browsing data exposed to HayVoz and are unnecessary for explicit
capture.

## Decision

Maintain one Manifest V3 WebExtension source with no declared permissions, host
permissions, injected content scripts, background worker, storage API, or
network client. An extension-owned page invokes `getDisplayMedia` only from a
user gesture. It records only the returned audio tracks with `MediaRecorder`,
downloads the result locally, and releases every capture track on stop.

The Python application imports a user-selected audio file explicitly, converts
it to the canonical local FLAC format, and creates a completed `local_only`
session. Safari uses Apple's WebExtension-to-Xcode packaging path rather than a
separate implementation.

## Consequences

- HayVoz cannot discover meetings, read page metadata, auto-start capture, or
  bypass the native sharing prompt.
- Chrome and Safari share auditable HTML, CSS, and JavaScript.
- Safari still requires Xcode packaging/signing and browser capture remains a
  manually validated integration.
- The extension downloads a minimal optional receipt, but the application does
  not ingest it automatically.
