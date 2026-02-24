#!/usr/bin/env bash
# setup.sh — Create or reset a daemon build workspace.
#
# SERIES=v2 (default): clone bitcoin-abc at latest, apply V2 patch series
# SERIES=v1:           clone bitcoin-abc at latest, apply V1 patch series
# SERIES=doged:        clone bitcoin-abc at latest, apply doged patch series
# SERIES=bchn:         clone bitcoin-cash-node at pinned tag, apply patches 29-31
#
# Usage: ./scripts/setup.sh [--reset]
#   --reset  wipe existing workspace and start fresh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DAEMON_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SERIES="${SERIES:-v2}"

# ─── helper: clone-and-checkout ──────────────────────────────────────────────
clone_and_checkout() {
    local workspace="$1" remote="$2" ref="$3" branch="$4" label="$5"
    if [[ "${RESET:-}" == "--reset" || "${1:-}" == "--reset" ]]; then
        echo "Resetting $label workspace..."
        rm -rf "$workspace"
    fi
    if [[ ! -d "$workspace" ]]; then
        echo "Cloning $remote into $(basename "$workspace")/..."
        git clone "$remote" "$workspace"
    fi
    echo "Checking out $ref..."
    cd "$workspace"
    git fetch origin
    git checkout -B "$branch" "$ref"
    echo ""
    echo "$label workspace ready at: $workspace"
}

# ─── helper: apply-patch-series ──────────────────────────────────────────────
apply_patch_series() {
    local series_file="$1" patches_dir="$2"
    echo "Applying patch series..."
    while IFS= read -r line; do
        [[ "$line" =~ ^#.*$ || -z "$line" ]] && continue
        local patch="$patches_dir/$line"
        [[ ! -f "$patch" ]] && echo "ERROR: patch not found: $patch" && exit 1
        echo "  applying $line..."
        git apply --whitespace=nowarn "$patch"
        git add -A
        git commit -m "Apply patch: $line" --no-verify 2>/dev/null || true
    done < "$series_file"
}

# ─── V1: bitcoin-abc base + Lotus mainnet patch series ───────────────────────
if [[ "$SERIES" == "v1" ]]; then
    WORKSPACE="$DAEMON_DIR/workspace-v1"
    VERSION_FILE="$DAEMON_DIR/bitcoin-abc-version"
    SERIES_FILE="$DAEMON_DIR/patches/v1/series"
    PATCHES_DIR="$DAEMON_DIR/patches/v1"
    REMOTE="git@github.com:Bitcoin-ABC/bitcoin-abc.git"
    REF=$(grep -v '^#' "$VERSION_FILE" | grep -v '^$' | head -1)
    echo "bitcoin-abc ref: $REF"
    clone_and_checkout "$WORKSPACE" "$REMOTE" "$REF" "lotus-v1-work" "V1 (Lotus mainnet)"
    apply_patch_series "$SERIES_FILE" "$PATCHES_DIR"
    echo ""
    echo "V1 workspace ready at: $WORKSPACE"
    echo "Build with: make build SERIES=v1"
    exit 0
fi

# ─── doged: bitcoin-abc base + doged patch series ────────────────────────────
if [[ "$SERIES" == "doged" ]]; then
    WORKSPACE="$DAEMON_DIR/workspace-doged"
    VERSION_FILE="$DAEMON_DIR/bitcoin-abc-version"
    SERIES_FILE="$DAEMON_DIR/patches/doged/series"
    PATCHES_DIR="$DAEMON_DIR/patches/doged"
    REMOTE="git@github.com:Bitcoin-ABC/bitcoin-abc.git"
    REF=$(grep -v '^#' "$VERSION_FILE" | grep -v '^$' | head -1)
    echo "bitcoin-abc ref (doged base): $REF"
    clone_and_checkout "$WORKSPACE" "$REMOTE" "$REF" "doged-work" "doged"
    apply_patch_series "$SERIES_FILE" "$PATCHES_DIR"
    echo ""
    echo "doged workspace ready at: $WORKSPACE"
    echo "Build with: make build SERIES=doged"
    exit 0
fi

# ─── bchn: Bitcoin Cash Node upstream PR candidates ──────────────────────────
if [[ "$SERIES" == "bchn" ]]; then
    WORKSPACE="$DAEMON_DIR/workspace-bchn"
    VERSION_FILE="$DAEMON_DIR/bchn-version"
    SERIES_FILE="$DAEMON_DIR/patches/bchn/series"
    PATCHES_DIR="$DAEMON_DIR/patches/bchn"
    REMOTE="https://gitlab.com/bitcoin-cash-node/bitcoin-cash-node.git"
    REF=$(grep -v '^#' "$VERSION_FILE" | grep -v '^$' | head -1)
    echo "bitcoin-cash-node ref: $REF"
    clone_and_checkout "$WORKSPACE" "$REMOTE" "$REF" "bchn-work" "BCHN"
    apply_patch_series "$SERIES_FILE" "$PATCHES_DIR"
    echo ""
    echo "BCHN workspace ready at: $WORKSPACE"
    echo "Build with: make build SERIES=bchn"
    echo ""
    echo "NOTE: Patches 29-31 were written against eCash v0.24.11 and may need context"
    echo "  adjustments to apply cleanly against BCHN. If git apply fails, port manually:"
    echo "  cd workspace-bchn && <apply hunks by hand>"
    echo "  make mkpatch SERIES=bchn NAME=<patch-name>"
    exit 0
fi

# ─── V2: bitcoin-abc base + Lotus patch series (new chain) ───────────────────
WORKSPACE="$DAEMON_DIR/workspace"
VERSION_FILE="$DAEMON_DIR/bitcoin-abc-version"
SERIES_FILE="$DAEMON_DIR/patches/v2/series"
PATCHES_DIR="$DAEMON_DIR/patches/v2"
REMOTE="git@github.com:Bitcoin-ABC/bitcoin-abc.git"

REF=$(grep -v '^#' "$VERSION_FILE" | grep -v '^$' | head -1)
echo "bitcoin-abc ref: $REF"

clone_and_checkout "$WORKSPACE" "$REMOTE" "$REF" "lotus-work" "V2 (Lotus new chain)"
apply_patch_series "$SERIES_FILE" "$PATCHES_DIR"

echo ""
echo "V2 workspace ready at: $WORKSPACE"
echo "Build with: make build"
