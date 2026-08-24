# Spec 0001: Extension-icon control and live transcription

- Status: Proposed
- Document version: 0.1.0
- Date: 2026-08-24
- Target release: To be decided after feasibility spikes
- Related baseline: [`SPEC.md`](../../SPEC.md), section 9.1
- Related decisions: [ADR 0005](../adr/0005-permission-free-browser-capture.md),
  [ADR 0006](../adr/0006-automatic-local-browser-transcription.md)

## 1. Outcome

HayVoz will use the extension icon popup as the only visible control surface for
browser capture. A user can start, pause, resume, and stop there, reopen the popup
without losing the active state, see provisional transcription while recording,
and save one final transcript after stopping. HayVoz will not retain a recording
or create a domain session for this flow.

The popup is the control plane, not the recording runtime. Recording and native
processing must survive the popup closing.

### 1.1 Current baseline

- [`popup.html`](../../extensions/web/popup.html) is currently a link that opens
  the visible `capture.html` extension page.
- [`capture.js`](../../extensions/web/capture.js) owns `MediaStream` and
  `MediaRecorder`, accumulates the complete recording in memory, and uploads it
  only after Stop.
- [`BrowserProcessor`](../../app/browser/processor.py) assembles the chunks,
  imports a canonical audio file, creates a completed `Session`, and then invokes
  batch transcription.
- [`TranscriptSegment`](../../app/transcription/models.py) requires a
  `session_id`; the [SQLite schema](../../app/storage/database.py) enforces the
  same relationship with a foreign key.
- On success, the current flow removes inbox chunks but retains canonical audio,
  the session, transcript JSON, and database rows. On failure, it retains or
  downloads audio for recovery.

## 2. Why the literal proposal needs adjustment

The product direction is sound, but three literal interpretations are not safe
implementation requirements:

1. **Run everything inside the popup.** Extension popups are ephemeral. Losing
   focus may destroy their document and stop a `MediaRecorder`. A durable runtime
   must own capture while the popup renders and sends commands.
2. **Never create audio.** Transcription requires audio samples. “Transcript
   only” therefore means that audio is temporary processing material, never a
   durable product artifact. A strict zero-audio-at-rest mode would require a
   separate RAM-only design and would have weaker crash recovery.
3. **Pause means no active capture.** `MediaRecorder.pause()` can stop producing
   chunks while the browser still owns an active shared source and shows its
   capture indicator. Only **Stop** releases every media track. The popup must
   explain this difference rather than imply that Pause revokes capture.

These constraints are not merely project assumptions:

- Chrome's [capture guidance](https://developer.chrome.com/docs/extensions/how-to/web-platform/screen-capture)
  states that popup-owned recording stops when the popup closes and documents an
  offscreen runtime for background recording.
- Chrome's [Offscreen API](https://developer.chrome.com/docs/extensions/reference/api/offscreen)
  requires an additional `offscreen` permission and supports only runtime
  messaging from the hidden document.
- The web platform's [`getDisplayMedia`](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getDisplayMedia)
  requires transient user activation and fresh user permission for each capture.
- Apple's [Safari WebExtension guidance](https://developer.apple.com/documentation/safariservices/optimizing-your-web-extension-for-safari)
  says Safari may unload nonpersistent background pages when the user is not
  directly interacting with the extension.

## 3. Strengths and weaknesses

### Strengths

- One obvious place to control recording reduces navigation and makes Stop easier
  to find.
- Reopening the icon can show authoritative state instead of depending on an
  extension tab that the user may close or lose.
- Transcript-only retention is easier to explain and reduces sensitive data,
  storage use, and accidental audio reuse.
- A streaming path can expose errors earlier and shorten the delay between Stop
  and the final transcript.
- The existing no-page-access and no-network boundaries can remain intact.

### Weaknesses and costs

- The popup cannot itself be the reliable recorder; Chrome and Safari require
  different background/runtime strategies.
- Chrome will probably require additional narrow extension permissions such as
  `offscreen` and possibly `tabCapture`. This weakens the current
  `nativeMessaging`-only manifest, even though it does not grant DOM, URL,
  history, cookie, or host access.
- Safari Manifest V3 workers can be unloaded. Icon-only capture parity must not be
  promised until a real Safari spike proves a durable media owner.
- Deleting audio on every outcome removes today's recovery fallback. If
  transcription fails, the meeting audio and transcript may both be lost.
- Live transcription adds ordering, backpressure, deduplication, provisional-text
  replacement, crash cleanup, and significantly more cross-browser testing.
- Removing browser sessions conflicts with the current schema: transcript rows
  have a mandatory foreign key to `sessions`, and transcription consumes a
  persisted session audio path. This is a storage migration, not a popup-only UI
  change.

## 4. Product contract

Normative terms **MUST**, **SHOULD**, and **MAY** define implementation
requirements.

### 4.1 Visible experience

- The extension popup MUST be the only HayVoz browser UI opened by this flow. It
  MUST NOT open `capture.html`, a new tab, or a separate visible window.
- The browser's native source picker and browser capture indicator are permitted
  operating-system/browser UI and remain mandatory security controls.
- In `idle`, the popup MUST show title input, processor readiness, and Start.
- In `starting`, it MUST show that the native picker is pending and offer Cancel
  when the browser supports cancellation.
- In `recording`, it MUST show elapsed time, Pause, and Stop.
- In `paused`, it MUST state that source sharing remains active and show Resume
  and Stop.
- In `finalizing`, controls that would create a second capture MUST be disabled.
- In `completed`, it MUST show the saved transcript and a copy/export action. It
  MUST NOT show a session ID.
- Closing and reopening the popup MUST reconstruct state from the runtime. The
  popup DOM MUST NOT be the source of truth.
- The extension badge SHOULD distinguish recording, paused, and finalizing states
  so the user has a signal while the popup is closed.

### 4.2 State machine

Allowed transitions are:

```text
idle -> starting -> recording <-> paused -> finalizing -> completed -> idle
                  |          |             |
                  +----------+-------------+-> failed -> idle
                  +----------+-------------+-> cancelled -> idle
```

- Exactly one browser capture MAY be active per browser profile.
- Every command MUST be idempotent and include a monotonic command sequence.
- Stop MUST end every source track before final transcript persistence begins.
- Browser-level source termination MUST behave like Stop.
- A stale popup MUST query current state before enabling a command.

### 4.3 Transcript-only retention

- The durable result MUST be one transcript document with a stable
  `transcript_id`, title, creation time, detected language when available, and
  ordered final segments.
- A `transcript_id` identifies the saved document; it MUST NOT imply or require a
  row in the current `sessions` table.
- The browser flow MUST NOT create a domain `Session`, a canonical FLAC/M4A/WebM
  recording, or an audio download fallback.
- Raw or normalized audio MAY exist only as bounded, owner-only temporary
  processing material. It MUST NOT be presented as saved user content.
- After successful atomic transcript persistence, all audio chunks, assembled
  audio, native inbox data, and runtime capture metadata MUST be deleted.
- Cancel and failure MUST also schedule all temporary audio for deletion. Startup
  recovery MUST remove abandoned browser-capture material using a documented
  short time-to-live.
- Logs MUST contain state and sanitized identifiers only, never audio or
  transcript text.
- The project MUST document that file deletion on SSDs is best-effort cleanup,
  not a guarantee of forensic secure erasure.

The proposed canonical document is:

```json
{
  "schema_version": 2,
  "transcript_id": "uuid",
  "title": "Reunión desde navegador",
  "created_at": "RFC-3339 timestamp",
  "language": "es",
  "segments": [
    {
      "speaker": "unknown",
      "start": 0.0,
      "end": 2.4,
      "text": "Texto final",
      "confidence": 0.91
    }
  ]
}
```

### 4.4 Live transcription

- Audio chunks MUST leave the recording runtime incrementally; the extension
  MUST NOT accumulate the entire meeting in a JavaScript array.
- The native processor MUST apply bounded queues and backpressure. It MUST fail
  visibly rather than grow memory or disk without a limit.
- Live results MUST distinguish `provisional` from `final` segments and carry a
  monotonically increasing revision.
- A newer revision MAY replace provisional text. Final segments MUST be append
  only unless the protocol explicitly issues a correction for a segment ID.
- The popup MUST render the most recent transcript snapshot when reopened.
- Provisional text MUST remain ephemeral. Stop triggers final decoding and one
  atomic write of the final transcript document.
- No transcript or audio is sent over a network. Native messaging and the Safari
  App Group remain same-device boundaries.

## 5. Proposed architecture

```text
extension popup <-> runtime controller <-> media runtime
       ^                    |                    |
       |                    v                    v
       +---------- live snapshot <-> native incremental transcriber
                                      |
                                      +-> atomic transcript store
```

Responsibilities:

- **Popup:** render current state and transcript snapshot; issue commands only.
- **Runtime controller:** own the state machine, sequence commands, restore state,
  set the badge, and relay native status.
- **Media runtime:** own `MediaStream` and `MediaRecorder`, emit bounded chunks,
  and release tracks on Stop.
- **Native incremental transcriber:** accept ordered chunks, decode rolling audio
  windows, publish revisions, finalize the tail, and clean temporary audio.
- **Transcript store:** persist transcript documents without a browser session.

Chrome's candidate design is an MV3 service worker plus an offscreen document.
The feasibility spike MUST compare `getDisplayMedia` with the `DISPLAY_MEDIA`
offscreen reason against `tabCapture` plus `USER_MEDIA`; it MUST record required
permissions, minimum Chrome version, whether the native picker remains available,
and whether audio playback to the user is preserved.

Safari requires an independent feasibility spike. A nonpersistent service worker
MUST NOT be assumed to own long-lived media. The spike must prove either a
durable extension/native owner controlled by the popup or report icon-only Safari
capture as unsupported. A hidden runtime is allowed; a second visible HayVoz page
is not.

## 6. Protocol direction

The current `start/chunk/finish/status` request-response protocol uploads the
whole blob only after Stop. It will evolve, behind a new schema version, toward:

- `capture.begin`
- `capture.append`
- `capture.pause`
- `capture.resume`
- `capture.finalize`
- `capture.cancel`
- `capture.status`
- `transcript.snapshot`

Messages MUST carry `capture_id`, schema version, command/chunk sequence, and a
bounded payload. Append and command retries MUST be idempotent. Snapshot replies
MUST omit local paths and domain session identifiers.

Chrome SHOULD use a long-lived `runtime.connectNative()` port during active
capture if reliability tests show it is superior to one native process per
message. Safari MAY keep request-response messaging if the App Group protocol
provides equivalent ordering and status behavior.

## 7. Delivery plan

### Phase 0 — Feasibility and evidence

1. Build a minimal Chrome spike that starts from the icon, survives popup close,
   pauses/resumes, stops, and preserves audible tab playback.
2. Record the exact Chrome APIs, permissions, minimum version, picker behavior,
   and shutdown behavior.
3. Build the equivalent Safari spike with a current Xcode/Safari toolchain.
4. Benchmark local incremental Whisper on explicit reference hardware and choose
   chunk/window/overlap limits from evidence.
5. Decide whether temporary owner-only disk chunks are acceptable. If not,
   specify a RAM-only mode and its maximum meeting duration before implementation.

Exit gate: accept, revise, or reject the cross-browser runtime design. Do not
change the production manifest based only on automated mocks.

### Phase 1 — Popup as control surface

1. Replace the link-only popup with the idle/starting/recording/paused/finalizing
   UI.
2. Introduce a runtime state contract and badge states.
3. Move recording ownership out of the popup for the validated browser target.
4. Add reconnect and stale-command behavior.
5. Keep batch transcription temporarily so the UI/runtime change can be tested
   independently.

### Phase 2 — Transcript-only browser persistence

1. Introduce a transcript aggregate/repository independent of `Session`.
2. Add transcript document schema version 2 and atomic persistence.
3. Route browser transcription without `AudioImportService` or a canonical
   recording.
4. Remove the browser audio-download fallback.
5. Add success, failure, cancellation, crash, and TTL cleanup tests.
6. Define migration/compatibility behavior for existing session-backed browser
   transcripts; do not delete existing user data automatically.

### Phase 3 — Streaming transport and incremental decoding

1. Send each `MediaRecorder` timeslice while capture is active.
2. Add ordered, idempotent append plus bounded backpressure.
3. Add rolling native decoding with overlap and segment/revision reconciliation.
4. Expose live snapshots to the runtime controller.
5. Finalize the trailing window on Stop and atomically save the transcript.

### Phase 4 — Live popup presentation

1. Render provisional and final segments with accessible status announcements.
2. Restore the latest snapshot whenever the popup opens.
3. Show delayed/offline/failed native processing without implying data was saved.
4. Add copy and explicit transcript export without adding audio export.
5. Measure time-to-first-text, revision frequency, memory, temporary disk use,
   CPU, and finalization time on supported platforms.

### Phase 5 — Hardening and release

1. Run real meetings in Chrome and Safari, including long captures, popup churn,
   tab navigation, source termination, sleep/wake, native-process restart, and
   model failure.
2. Re-run privacy, permissions, no-network, native-message validation, packaging,
   uninstall, and update tests.
3. Update the threat model, browser documentation, root specification, and an ADR
   that supersedes the affected parts of ADR 0006.
4. Declare browser/version support only for combinations with recorded manual
   evidence.

## 8. Acceptance criteria

1. No HayVoz capture page, tab, or window opens; the native picker is the only
   additional visible surface.
2. Capture continues after the popup closes, and reopening the icon shows the
   correct state and elapsed time.
3. Pause emits no new audio chunks; the UI states that sharing remains active.
4. Stop releases all media tracks and cannot be undone.
5. Live provisional text appears, survives popup reopen, and is visibly
   distinguishable from final text.
6. A successful Stop leaves exactly the intended transcript artifact and allowed
   transcript index data: no browser `Session`, canonical recording, inbox chunk,
   assembled audio, or fallback download.
7. Failure and cancellation do not create a completed transcript and clean all
   temporary audio according to the defined lifecycle.
8. Existing session-backed transcripts remain readable after migration.
9. The extension retains no host permissions, content scripts, page inspection,
   network client, analytics, or telemetry.
10. Automated protocol/storage tests and real-browser manual tests pass for every
    browser/version combination declared supported.
11. Performance evidence reports time-to-first-text and resource use; the product
    does not publish a universal latency claim unsupported by hardware tests.

## 9. Explicit non-goals

- Reading meeting DOM, URL, participants, captions, cookies, or history.
- Detecting meetings or starting capture automatically.
- Retaining or exporting audio from the browser flow.
- Speaker diarization in the first live-transcription release.
- Network transcription or remote control.
- Claiming Safari parity before the native-browser spike succeeds.

## 10. Open decisions

1. Is bounded owner-only temporary audio on disk acceptable, or is RAM-only
   processing required despite its memory and crash-recovery costs?
2. Should the final transcript be JSON only, or should an explicit user export
   also support plain text/Markdown?
3. What short TTL applies to abandoned temporary captures?
4. Which Chrome and Safari versions become the minimum supported versions after
   the spikes?
5. Should existing browser session-backed transcripts appear in the new
   transcript list through a compatibility view?

## 11. Change log

- 0.1.0 (2026-08-24): Initial proposal.
