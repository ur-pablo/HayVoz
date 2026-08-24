# Product specifications

Product specifications are versioned design contracts for behavior that spans
multiple implementation layers. They complement `SPEC.md`, which defines the
current product baseline, and ADRs, which record architecture decisions after
they are accepted.

## Lifecycle

1. Create a numbered file as `NNNN-short-name.md` on a short-lived branch.
2. Start with status `Proposed` and a document version of `0.1.0`.
3. Update the version while the proposal is under review:
   - patch: clarification without a behavioral change;
   - minor: new or changed requirement;
   - major: incompatible change to the proposed contract.
4. Record material edits in the specification's change log.
5. After acceptance, change behavior through a new specification that explicitly
   supersedes the accepted one. Do not silently rewrite accepted history.
6. Implement the accepted specification in separate, reviewable pull requests.

Specifications and their index are tracked in Git. Private meeting content,
recordings, transcripts, credentials, and local validation data never belong in
a specification.

## Index

| Spec | Version | Status | Summary |
| --- | --- | --- | --- |
| [0001](0001-extension-icon-live-transcription.md) | 0.1.0 | Proposed | Extension-icon controls, transcript-only retention, and a path to live transcription |
| [0002](0002-extension-automatic-updates.md) | 0.1.0 | Proposed | Signed browser-extension updates without repeated manual loading |
| [0003](0003-automatic-realtime-transcription.md) | 0.1.0 | Proposed | Implementation steps for automatic local transcription and live popup rendering |
