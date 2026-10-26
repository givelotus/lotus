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

SERIES="$(python3 "$SCRIPT_DIR/daemon_sources.py" canonical "$SERIES")"
python3 "$SCRIPT_DIR/daemon_sources.py" require-ready "$SERIES"
case "$SERIES" in
    v1|v2) LOTUSD="$DAEMON_DIR/.build/$SERIES/src/lotusd" ;;
    ecash|bchn) LOTUSD="$DAEMON_DIR/.build/$SERIES/src/bitcoind" ;;
    doged) LOTUSD="$DAEMON_DIR/.build/$SERIES/src/doged" ;;
    bitcoin) LOTUSD="$DAEMON_DIR/.build/$SERIES/bin/bitcoind" ;;
esac

if [[ ! -x "$LOTUSD" ]]; then
    echo "lotusd not found. Run: make build SERIES=$SERIES"
    exit 1
fi

ulimit -n 65536
exec "$LOTUSD" ${@+"$@"}
