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

# Resolve only the registered source submodule; never fall back to workspace-*.
SERIES="$(python3 "$SCRIPT_DIR/daemon_sources.py" canonical "$SERIES")"
python3 "$SCRIPT_DIR/daemon_sources.py" require-ready "$SERIES"
WORKSPACE="$(python3 "$SCRIPT_DIR/daemon_sources.py" path "$SERIES")"
case "$SERIES" in
    v1|v2) LABEL="Lotus $SERIES"; TARGETS=(lotusd lotus-cli) ;;
    ecash|bchn|bitcoin) LABEL="$SERIES"; TARGETS=(bitcoind bitcoin-cli) ;;
    doged) LABEL="Dogecoin on ABC"; TARGETS=(doged doge-cli) ;;
esac

BUILD_DIR="$DAEMON_DIR/.build/$SERIES"

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

if [[ "$SERIES" == "v1" || "$SERIES" == "v2" || "$SERIES" == "doged" || "$SERIES" == "doged-reference" ]]; then
    CMAKE_ARGS+=(-DBUILD_CHRONIK=ON)
    if [[ "$SERIES" == v2 || "$SERIES" == doged ]]; then
        CMAKE_ARGS+=(-DCHRONIK_IMPLEMENTATION=native)
    fi
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
cmake -S "$WORKSPACE" -B "$BUILD_DIR" "${CMAKE_ARGS[@]}"

echo "Building..."
ninja -j"$(nproc 2>/dev/null || sysctl -n hw.logicalcpu)" "${TARGETS[@]}"

echo ""
echo "Build complete ($LABEL). Binaries:"
for target in "${TARGETS[@]}"; do
    if [[ "$SERIES" == bitcoin ]]; then ls -lh "$BUILD_DIR/bin/$target"; else ls -lh "$BUILD_DIR/src/$target"; fi
done
