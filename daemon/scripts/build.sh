#!/usr/bin/env bash
# build.sh — Build lotusd from the workspace.
# Runs cmake + ninja (or make) inside workspace/build/
#
# Usage: ./scripts/build.sh [cmake-args...]
#   e.g. ./scripts/build.sh -DBUILD_BITCOIN_QT=OFF

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DAEMON_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
WORKSPACE="$DAEMON_DIR/workspace"
BUILD_DIR="$WORKSPACE/build"

if [[ ! -d "$WORKSPACE" ]]; then
    echo "Workspace not found. Run: make setup"
    exit 1
fi

mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

# Default cmake args — override Bitcoin Qt, enable static builds if desired
CMAKE_ARGS=(
    -GNinja
    -DBUILD_BITCOIN_QT=OFF
    -DBUILD_BITCOIN_ZMQ=OFF
    -DENABLE_UPNP=OFF
    -DENABLE_NATPMP=OFF
    "${@}"
)

echo "Configuring with cmake..."
cmake .. "${CMAKE_ARGS[@]}"

echo "Building..."
ninja -j"$(nproc 2>/dev/null || sysctl -n hw.logicalcpu)" bitcoind bitcoin-cli

echo ""
echo "Build complete. Binaries:"
ls -lh "$BUILD_DIR/src/bitcoind" "$BUILD_DIR/src/bitcoin-cli" 2>/dev/null || true
