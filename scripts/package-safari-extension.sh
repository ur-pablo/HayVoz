#!/bin/sh
set -eu

if [ "$(uname -s)" != "Darwin" ]; then
  echo "El empaquetado de Safari requiere macOS y Xcode." >&2
  exit 1
fi

if ! xcrun --find safari-web-extension-packager >/dev/null 2>&1; then
  echo "No se encontró safari-web-extension-packager. Instala una versión actual de Xcode." >&2
  exit 1
fi

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
SOURCE_DIR="$PROJECT_ROOT/extensions/web"
OUTPUT_DIR="$PROJECT_ROOT/build/safari"

mkdir -p "$OUTPUT_DIR"
xcrun safari-web-extension-packager "$SOURCE_DIR" \
  --project-location "$OUTPUT_DIR" \
  --app-name "HayVoz" \
  --bundle-identifier "com.urpablo.hayvoz.browser" \
  --swift \
  --copy-resources \
  --no-open

python3 "$PROJECT_ROOT/scripts/configure-safari-project.py" "$OUTPUT_DIR"

echo "Proyecto Safari generado en: $OUTPUT_DIR"
