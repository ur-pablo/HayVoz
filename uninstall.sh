#!/bin/sh
# Remove HayVoz executables and integrations while preserving all private data.
set -eu

KEEP_TOOL=0

usage() {
    printf '%s\n' \
        "Usage: ./uninstall.sh [--keep-tool]" \
        "" \
        "  --keep-tool  Remove services/browser bridges but keep the CLI installed." \
        "  --help       Show this help." \
        "" \
        "Private configuration, models, recordings and transcripts are always preserved."
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --keep-tool) KEEP_TOOL=1 ;;
        --help|-h) usage; exit 0 ;;
        *) printf '%s\n' "Unknown option: $1" >&2; usage >&2; exit 2 ;;
    esac
    shift
done

if command -v hayvoz >/dev/null 2>&1; then
    HAYVOZ_COMMAND=$(command -v hayvoz)
elif command -v uv >/dev/null 2>&1; then
    HAYVOZ_BIN_DIR=$(uv tool dir --bin)
    HAYVOZ_COMMAND="$HAYVOZ_BIN_DIR/hayvoz"
else
    HAYVOZ_COMMAND=""
fi

if [ -n "$HAYVOZ_COMMAND" ] && [ -x "$HAYVOZ_COMMAND" ]; then
    "$HAYVOZ_COMMAND" uninstall
else
    printf '%s\n' "HayVoz CLI was not found; no registered integrations were changed." >&2
fi

if [ "$KEEP_TOOL" -eq 0 ]; then
    if command -v uv >/dev/null 2>&1; then
        uv tool uninstall hayvoz || true
    else
        printf '%s\n' "uv was not found; remove the HayVoz executable manually." >&2
    fi
fi

printf '%s\n' \
    "HayVoz uninstalled." \
    "Private configuration, models, recordings and transcripts were preserved."
