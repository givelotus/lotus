#!/usr/bin/env bash
# run.sh — Launch lotusd with adequate file descriptor limits.
#
# SERIES=v1 (default):           run from workspace-v1/
#
# Usage: ./scripts/run.sh [lotusd-args...]
#   e.g. ./scripts/run.sh -regtest -datadir=/tmp/lotus-regtest -daemon

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DAEMON_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SERIES="${SERIES:-v1}"

case "$SERIES" in
    v1) LOTUSD="$DAEMON_DIR/workspace-v1/build/src/lotusd" ;;
    ecash) LOTUSD="$DAEMON_DIR/workspace-ecash/build/src/bitcoind" ;;
    doged) LOTUSD="$DAEMON_DIR/workspace-doged/build/src/doged" ;;
    bchn) LOTUSD="$DAEMON_DIR/workspace-bchn/build/src/bitcoind" ;;
    *) echo "Unsupported series: $SERIES (choose v1, ecash, doged, or bchn)" >&2; exit 1 ;;
esac

if [[ ! -x "$LOTUSD" ]]; then
    echo "lotusd not found. Run: make build SERIES=$SERIES"
    exit 1
fi

ulimit -n 65536
exec "$LOTUSD" ${@+"$@"}
