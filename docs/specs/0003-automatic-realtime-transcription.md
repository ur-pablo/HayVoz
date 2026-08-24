# Spec 0003: Automatic local real-time transcription

- Status: Proposed
- Document version: 0.1.0
- Date: 2026-08-24
- Target release: To be decided after feasibility spikes
- Related baseline: [`SPEC.md`](../../SPEC.md), section 9.1
- Related spec: [0001](0001-extension-icon-live-transcription.md)
- Related decision: [ADR 0006](../adr/0006-automatic-local-browser-transcription.md)

## 1. Outcome

After the user starts capture from the browser's native picker, HayVoz MUST
automatically send bounded audio chunks to the same-device native processor,
transcribe them locally, and show the latest transcript in the extension popup
while capture continues. The user MUST NOT need to run `import-audio`,
`transcribe`, download audio, or reload a capture page.

The popup is a view and command surface. A durable runtime owns capture and
processing so closing and reopening the popup does not stop the workflow.

## 2. Steps to implement

### Phase 0 — Prove feasibility

1. Build a Chrome spike using the least-privileged viable capture runtime.
2. Verify that capture survives popup close, pause/resume, browser source stop,
   sleep/wake, and native-process restart.
3. Repeat the runtime test for Safari with the signed WebExtension/App Group
   packaging path; record unsupported cases instead of assuming parity.
4. Benchmark local Whisper with bounded chunk size, rolling window, overlap,
   time-to-first-text, CPU, memory, and temporary disk use.
5. Choose the temporary-audio policy and document its TTL and crash cleanup.

### Phase 1 — Make the flow automatic

1. Replace the link-only popup with `idle`, `starting`, `recording`, `paused`,
   `finalizing`, `completed`, `failed`, and `cancelled` states.
2. Move `MediaStream` and `MediaRecorder` ownership to the validated durable
   media runtime.
3. Introduce `capture.begin`, `capture.append`, `capture.pause`,
   `capture.resume`, `capture.finalize`, `capture.cancel`, and `capture.status`.
4. Add monotonic command/chunk sequence numbers, idempotent retries, bounded
   queues, and visible backpressure failure.
5. Keep all messages same-device through native messaging/App Group; add no HTTP
   server, page permission, host permission, or network client.

### Phase 2 — Add incremental transcription

1. Decode each accepted chunk in a native rolling window; never accumulate the
   entire meeting in a JavaScript array.
2. Publish `transcript.snapshot` messages containing ordered segments, a capture
   ID, and a monotonically increasing revision.
3. Mark segments as `provisional` or `final`; permit replacement only for
   provisional segments, unless an explicit correction references a segment ID.
4. On Stop, decode the tail, reconcile the final revision, atomically persist one
   transcript document, and delete temporary audio according to its policy.
5. On cancel, failure, crash recovery, or TTL expiry, remove temporary audio and
   avoid creating a completed transcript.

### Phase 3 — Render safely in the popup

1. Reopen the popup by querying authoritative runtime state, not by trusting old
   DOM state.
2. Render final text append-only and provisional text with a distinct visual and
   accessible status announcement.
3. Show processor readiness, delay, queue pressure, model errors, and finalizing
   state without implying that unsaved text is durable.
4. Add copy/export for the transcript only; do not add an audio download to this
   flow.
5. Set an extension badge for recording, paused, and finalizing states.

### Phase 4 — Validate and release

1. Add protocol, ordering, retry, storage, cleanup, migration, and popup-reopen
   tests.
2. Run real Chrome and Safari meetings on every declared platform/version,
   including long captures and interrupted captures.
3. Measure time-to-first-text and finalization latency on reference hardware;
   publish no universal latency promise without evidence.
4. Update the root spec, browser documentation, threat model, release notes, and
   ADRs before enabling the feature by default.

## 3. Acceptance criteria

- No manual import, transcribe command, capture-page navigation, or audio download
  is required for a successful browser capture.
- The popup shows live provisional text and final text while the same capture is
  active, and restores the latest snapshot after reopening.
- Stop releases every media track and persists exactly one final transcript.
- Temporary audio and abandoned chunks are bounded, owner-only, and cleaned up;
  no audio or transcript is sent over a network.
- Existing session-backed transcripts remain readable after any storage migration.
- The feature is enabled only for browser/version combinations supported by real
  manual evidence.

## 4. Explicit non-goals

- Reading meeting DOM, captions, URLs, participants, cookies, or history.
- Automatic meeting detection or automatic capture without a user gesture.
- Speaker diarization in the first release.
- Remote transcription, telemetry, or silent update checks.

## 5. Open decisions

1. RAM-only versus bounded owner-only temporary audio on disk.
2. Final export formats beyond the canonical JSON document.
3. TTL and recovery behavior for abandoned captures.
4. Minimum supported Chrome/Safari versions after the feasibility spikes.

## 6. Change log

- 0.1.0 (2026-08-24): Initial proposal.
