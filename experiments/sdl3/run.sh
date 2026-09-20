#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
export ZUIKI_SDL3_ROOT="${ZUIKI_SDL3_ROOT:-$SCRIPT_DIR/../../build/sdl3-experiment}"
if [[ ! -x "$ZUIKI_SDL3_ROOT/env/bin/python" ]]; then
    echo 'Run bash experiments/sdl3/build.sh first.' >&2
    exit 1
fi
exec "$ZUIKI_SDL3_ROOT/env/bin/python" -u "$SCRIPT_DIR/launch.py" "$@"
