# Spec 0002: Automatic browser-extension updates

- Status: Proposed
- Document version: 0.1.0
- Date: 2026-08-24
- Target release: To be decided after distribution spikes
- Related baseline: [`SPEC.md`](../../SPEC.md), section 9.1
- Related documents: [`BROWSER_EXTENSION.md`](../BROWSER_EXTENSION.md),
  [`RELEASE.md`](../RELEASE.md), [ADR 0007](../adr/0007-branch-and-release-versioning.md)

## 1. Outcome

Users who install the released HayVoz browser extension through its supported
browser distribution channel MUST receive new extension versions without
repeating **Load unpacked** or manually replacing extension files. The browser's
own signed update mechanism is the source of truth; HayVoz MUST NOT download or
execute an unsigned extension bundle or run a silent updater of its own.

Development installations remain explicit and local. This spec does not promise
automatic updates for an unpacked extension loaded in developer mode.

## 2. Distribution contract

- Chrome releases MUST be published through the Chrome Web Store, or another
  browser-supported signed enterprise channel documented before release.
- Safari releases MUST be shipped in the signed containing app and distributed
  through Apple's supported update channel. The Safari extension bundle MUST be
  rebuilt from the same versioned source and native bridge contract.
- The extension manifest version MUST equal the canonical Python package version
  and MUST pass `uv run python scripts/version.py check`.
- Every release MUST have a signed Git tag, reproducible source association, and
  release notes describing extension, native-host, schema, and migration impact.
- The native host and extension MUST declare compatible protocol versions. An
  extension update MUST NOT strand an older installed native host without a
  visible recovery message.

## 3. Update behavior

- The browser MAY check and apply updates according to its normal policy. HayVoz
  MUST NOT add telemetry, unique installation identifiers, remote update checks,
  or a background network client.
- An update MUST preserve capture safety: an active capture MUST either finish
  before replacement or be cancelled with temporary material cleaned up and a
  clear user-visible error.
- On startup and native-message connection, the extension MUST validate the
  protocol version and show `Actualizar HayVoz` when the native bridge is too old
  or too new.
- An incompatible update MUST fail closed: it MUST NOT send chunks to an
  unrecognized protocol or silently fall back to a network service.
- Failed browser-managed updates MUST be recoverable through the browser's
  previous-version/repair mechanism where available. HayVoz MUST document the
  exact supported recovery action for each channel.

## 4. Release and validation steps

1. Create `release/X.Y.Z`, update the canonical version, lockfile, changelog,
   manifest, and native protocol compatibility metadata.
2. Build the Chrome and Safari artifacts from the same commit; do not patch a
   generated artifact by hand.
3. Run automated version, manifest, protocol, privacy, packaging, and no-network
   checks.
4. Install version `X.Y.(Z-1)` in clean Chrome and Safari profiles, publish or
   stage `X.Y.Z` through the intended channel, and verify browser-managed update.
5. During an update test, verify popup state, native messaging, capture cleanup,
   transcript persistence, permissions, extension identity, and rollback/repair.
6. Publish only after the update test passes for each browser/version combination
   declared supported.
7. Update `docs/BROWSER_EXTENSION.md` and `docs/RELEASE.md` with the actual
   channel, minimum versions, review status, and evidence.

## 5. Acceptance criteria

1. A store-installed extension updates without **Load unpacked** or manual file
   replacement.
2. The extension and native host reject incompatible protocol versions safely.
3. No HayVoz-owned update check, telemetry, analytics, or network client is
   introduced.
4. The extension ID/signing identity remains stable across compatible releases.
5. An update cannot lose a completed transcript or leave unbounded temporary
   audio behind.
6. Development documentation clearly distinguishes unpacked builds from
   updateable signed distributions.

## 6. Explicit non-goals

- Automatically updating the HayVoz CLI, native host, models, or operating-system
  services.
- Circumventing browser or App Store review and signing requirements.
- Claiming automatic updates for locally loaded unpacked extensions.

## 7. Open decisions

1. Which Chrome distribution channel will be used: public Web Store or managed
   enterprise distribution?
2. Which Safari containing-app distribution and update channel will be supported?
3. What minimum extension/native protocol compatibility window is required?
4. How will an active capture be drained or surfaced when a browser update is
   pending?

## 8. Change log

- 0.1.0 (2026-08-24): Initial proposal.
