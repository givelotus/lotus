#!/usr/bin/env bash
# build.sh — Build lotusd from a workspace.
#
# SERIES=v1 (default):           build from workspace-v1/
#
# Usage: ./scripts/build.sh [cmake-args...]
#   e.g. ./scripts/build.sh -DBUILD_BITCOIN_QT=OFF
# FEATURES=chronik,nng-off selects independent build options; no policy patches
# are applied by this script. Explicit trailing CMake arguments take precedence.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DAEMON_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SERIES="${SERIES:-v1}"

case "$SERIES" in
    v1) WORKSPACE="$DAEMON_DIR/workspace-v1"; LABEL="V1 (mainnet)"; TARGETS=(lotusd lotus-cli) ;;
    ecash) WORKSPACE="$DAEMON_DIR/workspace-ecash"; LABEL="eCash candidates"; TARGETS=(bitcoind bitcoin-cli) ;;
    doged) WORKSPACE="$DAEMON_DIR/workspace-doged-abc"; LABEL="Dogecoin on Bitcoin ABC"; TARGETS=(doged doge-cli) ;;
    doged-reference) WORKSPACE="$DAEMON_DIR/workspace-doged-reference"; LABEL="historical doged reference"; TARGETS=(doged doge-cli) ;;
    bitcoin) WORKSPACE="$DAEMON_DIR/workspace-bitcoin"; LABEL="Bitcoin Core BTC"; TARGETS=(bitcoind bitcoin-cli) ;;
    bchn) WORKSPACE="$DAEMON_DIR/workspace-bchn"; LABEL="BCHN candidates"; TARGETS=(bitcoind bitcoin-cli) ;;
    *) echo "Unsupported series: $SERIES (choose v1, ecash, doged, doged-reference, bchn, or bitcoin)" >&2; exit 1 ;;
esac

BUILD_DIR="$WORKSPACE/build"

if [[ ! -d "$WORKSPACE" ]]; then
    echo "Workspace not found. Run: make setup SERIES=$SERIES"
    exit 1
fi

mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

CMAKE_ARGS=(-GNinja)
if [[ "$SERIES" == bitcoin ]]; then
    CMAKE_ARGS+=(-DBUILD_GUI=OFF -DENABLE_IPC=OFF -DWITH_ZMQ=OFF -DBUILD_BENCH=OFF)
elif [[ "$SERIES" == bchn ]]; then
    CMAKE_ARGS+=(-DBUILD_BITCOIN_QT=OFF -DBUILD_BITCOIN_ZMQ=OFF
                 -DENABLE_UPNP=OFF -DENABLE_NATPMP=OFF -DENABLE_MAN=OFF)
else
    # Current ABC and Doged use these names; UPnP/NAT-PMP were removed upstream.
    CMAKE_ARGS+=(-DBUILD_QT=OFF -DBUILD_ZMQ=OFF)
fi

if [[ "$SERIES" == "v1" || "$SERIES" == "doged" || "$SERIES" == "doged-reference" ]]; then
    CMAKE_ARGS+=(-DBUILD_CHRONIK=ON)
fi

if [[ -n "${FEATURES:-}" ]]; then
    PLAN=$(python3 "$SCRIPT_DIR/feature-plan.py" --target "$SERIES" --features "$FEATURES")
    FLAGS=$(python3 -c 'import json,sys; plan=json.load(sys.stdin); assert not plan["patches"], "Build options cannot apply patches"; print("\n".join(plan["cmake_args"]))' <<< "$PLAN")
    while IFS= read -r flag; do
        [[ -z "$flag" ]] || CMAKE_ARGS+=("$flag")
    done <<< "$FLAGS"
fi

CMAKE_ARGS+=("$@")

echo "Configuring $LABEL with cmake..."
cmake .. "${CMAKE_ARGS[@]}"

echo "Building..."
ninja -j"$(nproc 2>/dev/null || sysctl -n hw.logicalcpu)" "${TARGETS[@]}"

echo ""
echo "Build complete ($LABEL). Binaries:"
for target in "${TARGETS[@]}"; do
    if [[ "$SERIES" == bitcoin ]]; then ls -lh "$BUILD_DIR/bin/$target"; else ls -lh "$BUILD_DIR/src/$target"; fi
done
