# ADR 0006: Automatic local browser transcription bridge

- Status: Accepted
- Date: 2026-08-24
- Supersedes: ADR 0005's permission-free/manual-import transport decision

## Context

ADR 0005 minimized browser privileges by downloading each capture and requiring
the user to run `import-audio` and `transcribe`. That preserved a narrow boundary
but made every meeting a multi-step manual workflow. Automatic persistence needs
a same-device transport without granting page access or opening a local network
service.

Chrome and Safari both support WebExtension native messaging, with different
native-host packaging. Chrome launches a registered stdio executable and can
restrict it to explicit extension origins. Safari routes messages into the native
extension of the containing app; sandboxed components share files through an App
Group.

## Decision

Declare only `nativeMessaging` in the shared extension. Keep page/host/history/
storage permissions, content scripts, background workers, and network clients
absent. Capture still starts only from an extension-page user gesture and the
browser's native source picker.

Split audio into 384 KiB messages and validate canonical UUID capture IDs, MIME
types, titles, sequence ranges, base64, repeated chunks, and completion counts.
Chrome registers `hayvoz-native` for one stable extension ID. Safari uses a native
message handler and `group.com.urpablo.hayvoz`. Both write owner-only files into
the same logical inbox schema; neither opens a port.

The existing per-user service processes completed requests automatically through
`AudioImportService` and local `TranscriptionService`. It removes raw chunks only
after canonical audio and transcript persistence succeeds. The extension receives
only status, local session ID, segment count, or a sanitized error. On failure,
local raw audio is retained/downloaded as a recovery fallback.

Installation and uninstall remain explicit. Uninstall removes browser/service
integration and program binaries but preserves user data.

## Consequences

- A stopped browser capture becomes a persisted local transcript without manual
  CLI import/transcription commands.
- The extension gains one narrow local capability, so native-host identity,
  framing, input validation, file permissions, and status minimization become
  security-critical and are covered by tests.
- Chrome and Safari share capture/protocol code but require distinct native
  packaging and real-browser validation.
- HayVoz still cannot discover meetings, inspect meeting pages, auto-start
  capture, bypass the native picker, or publish transcripts.
- A compromised local account, browser, signed containing app, or explicitly
  allowlisted extension remains a residual trust boundary.
