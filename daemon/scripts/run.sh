#!/usr/bin/env bash
# run.sh — Launch lotusd with adequate file descriptor limits.
# Passes all arguments through to lotusd.
#
# Usage: ./scripts/run.sh [lotusd-args...]
#   e.g. ./scripts/run.sh -regtest -datadir=/tmp/lotus-regtest -daemon

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DAEMON_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LOTUSD="$DAEMON_DIR/workspace/build/src/lotusd"

if [[ ! -x "$LOTUSD" ]]; then
    echo "lotusd not found. Run: make build"
    exit 1
fi

ulimit -n 65536
exec "$LOTUSD" ${@+"$@"}
