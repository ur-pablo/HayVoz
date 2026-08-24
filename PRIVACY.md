# Privacy Policy for HayVoz

HayVoz has zero first-party tracking. The project does not operate an analytics,
telemetry, advertising, crash-reporting, update-check, or remote-log service.

## Local data

Recordings, transcripts, guides, analyses, models, logs, and the SQLite database
stay in the user's configured data directory. Credentials stay in process
environment or an owner-readable private configuration file.

## Network use

HayVoz initiates network traffic only when the user explicitly downloads a model
or authorizes AI text processing. AI requests contain text context, never audio,
and request non-storage when supported. A configured third-party provider still
receives request metadata and content under its own terms; HayVoz cannot promise
zero processing by that provider after the user opts in.

## No automatic publication

HayVoz never publishes user data to Git, GitHub, a web endpoint, or another user.
Repository ignore rules exclude runtime data and common credential material.

## Browser companion

The Chrome/Safari companion declares only local `nativeMessaging`: it has no page,
host, history, storage, or network permission and cannot read meeting pages.
Capture starts only after a user gesture and native browser selection, and the
extension records only shared audio tracks. On stop it transfers bounded chunks
to the same-device bridge; HayVoz automatically strips embedded source metadata,
normalizes the audio, and transcribes with the local model. No listening port or
remote endpoint is involved.

Chrome allowlists a stable extension identity. Safari uses the containing native
extension and a private App Group. Only processing state, session ID, segment
count, or a sanitized error returns to the extension; transcript content and
paths do not. A failed bridge/model operation downloads or preserves local audio
for recovery instead of publishing it.

The browser and operating system still mediate screen/tab capture and may display
their own UI or apply their own policies. HayVoz cannot remove that trust
boundary.

## User control

Users choose the data directory, may operate fully local-only, can uninstall the
browser bridge, service, or program without deleting data, and can delete or back
up their local files directly. The experimental MCP server returns data only in
response to explicit read requests and does not publish, synchronize, or mutate
local data.
