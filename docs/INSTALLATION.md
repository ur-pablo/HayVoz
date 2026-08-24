# Installation

## macOS and Linux

Run `./install.sh`. It installs HayVoz into an isolated `uv` tool environment,
creates private config/data directories, and runs diagnostics. It never requests
an AI key on the command line. `uv` installation requires confirmation unless
`--yes` is supplied; system packages remain an explicit user responsibility.

Useful options:

```bash
./install.sh --with-model small
./install.sh --with-service
./install.sh --with-model small --with-browser
./install.sh --yes --with-model small --with-browser
```

The service and browser bridge are not installed by default, and model download
occurs only with `--with-model` because it is a large, explicit network operation.
`--with-browser` registers the Chrome native host and installs the local processor;
the extension itself is still loaded by the user in Chrome or packaged in Xcode.

Manual development setup:

```bash
uv sync --extra dev
uv run hayvoz doctor --skip-mic-check
```

The optional Chrome/Safari capture companion is installed separately from the
CLI because browser installation and signing require an explicit user action.
See [BROWSER_EXTENSION.md](BROWSER_EXTENSION.md).

## Uninstall

```bash
./uninstall.sh
./uninstall.sh --keep-tool  # keep the CLI, remove integrations
```

The script first removes browser registrations and the per-user service. It then
removes the isolated `uv` tool unless `--keep-tool` is present. It always preserves
private configuration, models, recordings, transcripts, and SQLite data.

## Windows

Windows support is experimental. Install Python 3.11+, FFmpeg with DirectShow,
and `uv`, then run:

```powershell
uv sync --extra dev
uv run hayvoz doctor --skip-mic-check
```

Native PowerShell/MSIX packaging is a later phase. A shell installer running in
WSL does not install native Windows capture or the scheduled task.

## Packaging direction

Python's packaging guide recommends isolated environments for CLI applications.
HayVoz uses a console-script entry point and plans signed native artifacts after
hardware validation: <https://packaging.python.org/en/latest/guides/creating-command-line-tools/>.
