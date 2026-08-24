# HayVoz session context

At the start of a coding session, read the repository files and the local
`CONTEXT.md` when it exists. Treat repository source and tracked documentation as
canonical; the context file is a concise handoff, not a replacement for them.

Before ending a session, update `CONTEXT.md` with the current branch/commit,
decisions, validation evidence, incomplete work, and next safe action. Keep it
ignored by Git. Never place credentials, recordings, transcripts, participant
names, customer information, absolute private data paths, or other user content
in that file.

If `CONTEXT.md` is missing, create it locally with only non-sensitive project
state. Confirm `git check-ignore CONTEXT.md` before relying on it as private.
