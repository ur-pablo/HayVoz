#!/bin/sh
# Install HayVoz from a trusted source checkout on macOS or Linux.
set -eu

WITH_SERVICE=0
WITH_BROWSER=0
WITH_MODEL=""
ASSUME_YES=0
RUN_DOCTOR=1

usage() {
    printf '%s\n' \
        "Usage: ./install.sh [--yes] [--with-service] [--with-browser] [--with-model MODEL] [--no-doctor]" \
        "" \
        "  --yes               Accept installation of missing uv automatically." \
        "  --with-service      Install the optional per-user recovery service." \
        "  --with-browser      Register the browser bridge and processing service." \
        "  --with-model MODEL  Download tiny, base, small or medium explicitly." \
        "  --no-doctor         Skip the final local diagnostic." \
        "  --help              Show this help."
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --yes)
            ASSUME_YES=1
            ;;
        --with-service)
            WITH_SERVICE=1
            ;;
        --with-browser)
            WITH_BROWSER=1
            ;;
        --with-model)
            [ "$#" -ge 2 ] || { printf '%s\n' "--with-model requires a value." >&2; exit 2; }
            WITH_MODEL=$2
            shift
            case "$WITH_MODEL" in
                tiny|base|small|medium) ;;
                *) printf '%s\n' "Model must be tiny, base, small or medium." >&2; exit 2 ;;
            esac
            ;;
        --no-doctor)
            RUN_DOCTOR=0
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            printf '%s\n' "Unknown option: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
    shift
done

case "$(uname -s)" in
    Darwin) PLATFORM=macos ;;
    Linux) PLATFORM=linux ;;
    *)
        printf '%s\n' "This installer supports macOS and Linux. See docs/INSTALLATION.md for Windows." >&2
        exit 1
        ;;
esac

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
[ -f "$SCRIPT_DIR/pyproject.toml" ] || {
    printf '%s\n' "Run this installer from a complete HayVoz source checkout." >&2
    exit 1
}

confirm() {
    if [ "$ASSUME_YES" -eq 1 ]; then
        return 0
    fi
    printf '%s [y/N] ' "$1"
    read -r answer
    case "$answer" in y|Y|yes|YES) return 0 ;; *) return 1 ;; esac
}

if command -v uv >/dev/null 2>&1; then
    UV_COMMAND=$(command -v uv)
else
    command -v curl >/dev/null 2>&1 || {
        printf '%s\n' "curl is required to install uv." >&2
        exit 1
    }
    confirm "uv is missing. Download and run the official Astral installer?" || {
        printf '%s\n' "Installation cancelled; install uv and retry." >&2
        exit 1
    }
    UV_INSTALLER=$(mktemp "${TMPDIR:-/tmp}/hayvoz-uv.XXXXXX")
    trap 'rm -f "$UV_INSTALLER"' EXIT HUP INT TERM
    curl -LsSf https://astral.sh/uv/install.sh -o "$UV_INSTALLER"
    sh "$UV_INSTALLER"
    rm -f "$UV_INSTALLER"
    trap - EXIT HUP INT TERM
    if [ -x "$HOME/.local/bin/uv" ]; then
        UV_COMMAND="$HOME/.local/bin/uv"
    elif [ -x "$HOME/.cargo/bin/uv" ]; then
        UV_COMMAND="$HOME/.cargo/bin/uv"
    else
        printf '%s\n' "uv was installed but its executable was not found." >&2
        exit 1
    fi
fi

if ! command -v ffmpeg >/dev/null 2>&1; then
    printf '%s\n' "Warning: ffmpeg is not installed. HayVoz will install, but recording will not work yet." >&2
    if [ "$PLATFORM" = macos ]; then
        printf '%s\n' "Install it with: brew install ffmpeg"
    else
        printf '%s\n' "Install your distribution's ffmpeg, PulseAudio/PipeWire compatibility, or ALSA tools."
    fi
fi

printf '%s\n' "Installing HayVoz in an isolated uv tool environment..."
"$UV_COMMAND" tool install --force "$SCRIPT_DIR"
HAYVOZ_BIN_DIR=$("$UV_COMMAND" tool dir --bin)
HAYVOZ_COMMAND="$HAYVOZ_BIN_DIR/hayvoz"
[ -x "$HAYVOZ_COMMAND" ] || {
    printf '%s\n' "HayVoz executable was not created at $HAYVOZ_COMMAND." >&2
    exit 1
}

if [ "$PLATFORM" = macos ]; then
    CONFIG_DIR="$HOME/Library/Application Support/HayVoz"
    DATA_DIR="$CONFIG_DIR/data"
else
    CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/hayvoz"
    DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/hayvoz"
fi
CONFIG_FILE="$CONFIG_DIR/config.env"
mkdir -p "$CONFIG_DIR" "$DATA_DIR"
chmod 700 "$CONFIG_DIR" "$DATA_DIR"
if [ ! -e "$CONFIG_FILE" ]; then
    {
        printf '%s\n' "# Private HayVoz configuration. Never commit this file."
        printf '%s\n' "HAYVOZ_LANGUAGE="
        printf '%s\n' "WHISPER_MODEL=small"
    } > "$CONFIG_FILE"
fi
chmod 600 "$CONFIG_FILE"

if [ -n "$WITH_MODEL" ]; then
    "$HAYVOZ_COMMAND" model download --model "$WITH_MODEL"
fi
if [ "$WITH_SERVICE" -eq 1 ] && [ "$WITH_BROWSER" -eq 0 ]; then
    HAYVOZ_CONFIG_FILE="$CONFIG_FILE" "$HAYVOZ_COMMAND" system install
fi
if [ "$WITH_BROWSER" -eq 1 ]; then
    HAYVOZ_CONFIG_FILE="$CONFIG_FILE" "$HAYVOZ_COMMAND" browser install
fi
if [ "$RUN_DOCTOR" -eq 1 ]; then
    HAYVOZ_CONFIG_FILE="$CONFIG_FILE" "$HAYVOZ_COMMAND" doctor --skip-mic-check || true
fi

printf '%s\n' \
    "HayVoz installed: $HAYVOZ_COMMAND" \
    "Private configuration: $CONFIG_FILE" \
    "Private data: $DATA_DIR" \
    "Uninstall safely with: $SCRIPT_DIR/uninstall.sh" \
    "Run '$HAYVOZ_COMMAND devices' after ffmpeg and audio permissions are ready."
