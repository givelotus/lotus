#!/usr/bin/env bash
# run.sh — Launch lotusd with adequate file descriptor limits.
#
# SERIES=v2 (default): run from workspace-v2/
# SERIES=v1:           run from workspace-v1/
#
# Usage: ./scripts/run.sh [lotusd-args...]
#   e.g. ./scripts/run.sh -regtest -datadir=/tmp/lotus-regtest -daemon

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DAEMON_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SERIES="${SERIES:-v2}"

if [[ "$SERIES" == "v1" ]]; then
    LOTUSD="$DAEMON_DIR/workspace-v1/build/src/lotusd"
elif [[ "$SERIES" == "doged" ]]; then
    LOTUSD="$DAEMON_DIR/workspace-doged/build/src/doged"
else
    LOTUSD="$DAEMON_DIR/workspace-v2/build/src/lotusd"
fi

if [[ ! -x "$LOTUSD" ]]; then
    echo "lotusd not found. Run: make build SERIES=$SERIES"
    exit 1
fi

ulimit -n 65536
exec "$LOTUSD" ${@+"$@"}
