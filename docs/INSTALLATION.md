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
./install.sh --yes --with-model small --with-service
```

The service is not installed by default, and model download occurs only with
`--with-model` because it is a large, explicit network operation.

Manual development setup:

```bash
uv sync --extra dev
uv run hayvoz doctor --skip-mic-check
```

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
