#!/usr/bin/env bash
# build.sh — Build lotusd from a workspace.
#
# SERIES=v2 (default): build from workspace/
# SERIES=v1:           build from workspace-v1/
#
# Usage: ./scripts/build.sh [cmake-args...]
#   e.g. ./scripts/build.sh -DBUILD_BITCOIN_QT=OFF

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DAEMON_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SERIES="${SERIES:-v2}"

if [[ "$SERIES" == "v1" ]]; then
    WORKSPACE="$DAEMON_DIR/workspace-v1"
    LABEL="V1 (mainnet)"
elif [[ "$SERIES" == "doged" ]]; then
    WORKSPACE="$DAEMON_DIR/workspace-doged"
    LABEL="doged (Tobias/Dogecoin ABC)"
else
    WORKSPACE="$DAEMON_DIR/workspace"
    LABEL="V2 (new chain)"
fi

BUILD_DIR="$WORKSPACE/build"

if [[ ! -d "$WORKSPACE" ]]; then
    echo "Workspace not found. Run: make setup SERIES=$SERIES"
    exit 1
fi

mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

CMAKE_ARGS=(
    -GNinja
    -DBUILD_BITCOIN_QT=OFF
    -DBUILD_BITCOIN_ZMQ=OFF
    -DENABLE_UPNP=OFF
    -DENABLE_NATPMP=OFF
    ${@+"$@"}
)

echo "Configuring $LABEL with cmake..."
cmake .. "${CMAKE_ARGS[@]}"

echo "Building..."
ninja -j"$(nproc 2>/dev/null || sysctl -n hw.logicalcpu)" lotusd lotus-cli

echo ""
echo "Build complete ($LABEL). Binaries:"
ls -lh "$BUILD_DIR/src/lotusd" "$BUILD_DIR/src/lotus-cli" 2>/dev/null || true
