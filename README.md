# HayVoz

Privacy-first meeting recorder and multilingual interview assistant. HayVoz
records locally, transcribes locally with `faster-whisper`, and contacts a
configured AI provider only after explicit consent.

> Status: macOS is hardware-validated. Windows and Linux platform adapters are
> experimental until hardware validation and release packaging are completed.
> Chrome and Safari capture is also experimental until manual browser/hardware
> validation is completed.

## Principles

- Zero first-party tracking: no telemetry, analytics, crash upload, advertising,
  fingerprinting, remote logging, or silent update checks.
- Local by default: audio, transcripts, guides, analyses, logs, and credentials
  remain in private per-user directories.
- Explicit network use: only model download and consented AI text processing.
- Audio is never sent to the AI provider by HayVoz.
- No listening port, web server, or remotely accessible control surface.
- GPLv3-or-later source code; private user data is not part of the licensed
  repository.

The complete scope and roadmap are in [SPEC.md](SPEC.md). Privacy boundaries are
documented in [PRIVACY.md](PRIVACY.md) and [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md).

## Requirements

- Python 3.11 or newer.
- `ffmpeg` with the relevant input backend:
  - macOS: AVFoundation;
  - Windows: DirectShow;
  - Linux: PulseAudio or ALSA.
- Approximately 1.5 GiB of free RAM for the default `small` Whisper model.
- BlackHole or another explicitly configured loopback only when macOS system
  audio capture is needed.
- AI provider credentials only for optional external analysis/suggestions.

## Install

Development checkout:

```bash
uv sync --extra dev
uv run hayvoz doctor --skip-mic-check
```

Automated macOS/Linux installation:

```bash
./install.sh
# Optional explicit additions:
./install.sh --with-model small --with-service
./install.sh --with-model small --with-browser
```

The installer does not install the background user service or browser bridge
unless the corresponding option is supplied. See
[docs/INSTALLATION.md](docs/INSTALLATION.md) for platform details and the Windows
status.

## Private configuration

HayVoz reads process environment first, then a private `config.env`:

- macOS: `~/Library/Application Support/HayVoz/config.env`
- Windows: `%APPDATA%\HayVoz\config.env`
- Linux: `${XDG_CONFIG_HOME:-~/.config}/hayvoz/config.env`

Copy `.env.example` to that location and restrict it to the current user. Real
credentials must never be placed in the checkout.

Core settings:

```text
HAYVOZ_LANGUAGE=es
HAYVOZ_DATA_DIR=
HAYVOZ_FFMPEG=ffmpeg
HAYVOZ_AUDIO_BACKEND=avfoundation
HAYVOZ_AUDIO_DEVICE=0

HAYVOZ_AI_PROVIDER=openai
HAYVOZ_AI_API_KEY=
HAYVOZ_AI_MODEL=
HAYVOZ_AI_BASE_URL=
HAYVOZ_AI_TIMEOUT_SECONDS=60

WHISPER_MODEL=small
WHISPER_LANGUAGE=
WHISPER_CPU_THREADS=4
WHISPER_BEAM_SIZE=1
WHISPER_VAD=true

ASSISTANT_CHUNK_SECONDS=15
ASSISTANT_ANALYSIS_INTERVAL_SECONDS=60
ASSISTANT_LAST_SEGMENTS=20
```

Standard `OPENAI_API_KEY`, `OPENAI_MODEL`, and `OPENAI_BASE_URL` variables are
accepted as compatibility inputs. The `HAYVOZ_AI_*` contract takes precedence.
See [docs/CONFIGURATION.md](docs/CONFIGURATION.md).

## Usage

Inspect the environment and audio devices:

```bash
uv run hayvoz doctor
uv run hayvoz devices
```

Record locally:

```bash
uv run hayvoz start \
  --title "Discovery interview" \
  --mode record \
  --device 0 \
  --local-only

uv run hayvoz stop
uv run hayvoz sessions
```

Transcribe offline:

```bash
uv run hayvoz model download --model small
uv run hayvoz transcribe SESSION_ID --language es
uv run hayvoz transcript SESSION_ID
```

Capture a meeting tab with the optional Chrome/Safari companion and let HayVoz
save and transcribe it automatically:

```bash
uv run hayvoz model download --model small
uv run hayvoz browser install
```

The shared Manifest V3 extension requests only local `nativeMessaging`: no page,
host, history, storage, or network permission. The user selects the tab through
the browser's native capture prompt. On stop, the local user service imports the
audio, runs Whisper, and persists the transcript. If the bridge or model is not
available, the extension downloads the audio as a local fallback. Installation,
Safari packaging, privacy boundaries, and validation status are in
[docs/BROWSER_EXTENSION.md](docs/BROWSER_EXTENSION.md).

Run the interview Assistant locally:

```bash
uv run hayvoz start \
  --title "Private interview" \
  --mode asistente \
  --device 0 \
  --guide ./interview-guide.md \
  --local-only

uv run hayvoz asistente SESSION_ID --watch
```

The stable alias is `assistant`. Initial localized aliases include `asistente`,
`assistente`, and `assistent`. Internal persistence always uses `assistant`, so
changing language does not break sessions or automation. This release provides
the i18n capability and localized feature term; it does not translate the whole
interface. See [docs/I18N.md](docs/I18N.md).

To allow periodic text suggestions, replace `--local-only` with
`--confirm-send`. Without valid AI credentials, recording and local
transcription continue but external suggestions remain disabled.

Review an analysis before sending anything:

```bash
uv run hayvoz analyze SESSION_ID
uv run hayvoz analyze SESSION_ID --confirm-send
uv run hayvoz report SESSION_ID
```

## Optional operating-system extension

HayVoz can run a per-user recovery agent:

```bash
hayvoz system install
hayvoz system status
hayvoz system uninstall
```

The agent checks local orphaned-session state and processes completed extension
captures. It never starts recording, calls an AI provider, opens a port, or
exposes remote commands. Platform details are in
[docs/SYSTEM_EXTENSION.md](docs/SYSTEM_EXTENSION.md).

## Uninstall

From a source checkout:

```bash
./uninstall.sh
# Or remove integrations but retain the installed CLI:
./uninstall.sh --keep-tool
```

`hayvoz uninstall` removes the browser bridge and per-user service when the CLI
must be managed separately. Both paths preserve configuration, models, sessions,
recordings, transcripts, and the database. HayVoz never guesses that private data
should be deleted.

## Storage and recovery

Default data locations:

- macOS: `~/Library/Application Support/HayVoz/data`
- Windows: `%LOCALAPPDATA%\HayVoz\data`
- Linux: `${XDG_DATA_HOME:-~/.local/share}/hayvoz`

The directory contains SQLite state, recordings, transcript JSON, copied guides,
models, and content-free structured logs. Directories use owner-only permissions
where supported. SQLite is canonical; interrupted recordings and partial
transcription are recovered conservatively and never uploaded.

## Platform scope

Python remains appropriate because the domain, persistence, provider, and
transcription layers are portable. The platform-specific boundaries are FFmpeg
device discovery, audio input syntax, process signaling, permissions, and user
service registration. See [docs/PORTABILITY.md](docs/PORTABILITY.md) and
[docs/adr/0001-retain-python.md](docs/adr/0001-retain-python.md).

## Development

```bash
uv sync --extra dev
uv run hayvoz --version
uv run python scripts/version.py check
uv run pytest
uv run python -m compileall -q app tests
```

All development uses short-lived branches and pull requests; direct development
on `main` is not part of the workflow. See
[docs/BRANCHING.md](docs/BRANCHING.md) for branch naming, semantic version
updates, and signed release tags.

Contribution and security reporting guidance:

- [CONTRIBUTING.md](CONTRIBUTING.md)
- [SECURITY.md](SECURITY.md)
- [SUPPORT.md](SUPPORT.md)
- [CHANGELOG.md](CHANGELOG.md)
- [docs/BRANCHING.md](docs/BRANCHING.md)
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/RELEASE.md](docs/RELEASE.md)
- [docs/adr/README.md](docs/adr/README.md)

## Support the project

If HayVoz is useful to you, you can support its independent development at
[Buy Me a Coffee](https://www.buymeacoffee.com/ur.pablo). Contributions remain
optional and do not change the GPLv3 license or privacy guarantees.

## License

Copyright (C) 2026 Pablo Ulloa Ramos and contributors.

HayVoz is free software licensed under the
[GNU General Public License version 3 or later](LICENSE). It is distributed
without warranty, as permitted by the license.
