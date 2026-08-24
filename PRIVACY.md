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

The Chrome/Safari companion declares no page, host, history, storage, or network
permissions. It cannot read meeting pages. Capture starts only after a user
gesture and native browser selection, and the extension records only shared
audio tracks. It downloads locally; HayVoz imports only the file the user names
and strips embedded source metadata during conversion.

The browser and operating system still mediate screen/tab capture and may display
their own UI or apply their own policies. HayVoz cannot remove that trust
boundary.

## User control

Users choose the data directory, may operate fully local-only, can uninstall the
background user service without deleting data, and can delete or back up their
local files directly.
