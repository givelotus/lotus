#!/usr/bin/env bash
# setup.sh — Create or reset a daemon build workspace.
#
# SERIES=v2 (default): clone eCash at pinned commit, apply V2 patch series
# SERIES=v1:           clone LotusiaStewardship/lotusd at pinned tag/commit
# SERIES=doged:        clone doged-io/doged at pinned commit
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

# ─── V1: LotusiaStewardship/lotusd (mainnet-compatible) ──────────────────────
if [[ "$SERIES" == "v1" ]]; then
    WORKSPACE="$DAEMON_DIR/workspace-v1"
    VERSION_FILE="$DAEMON_DIR/lotusd-version"
    REMOTE="https://github.com/LotusiaStewardship/lotusd.git"
    REF=$(grep -v '^#' "$VERSION_FILE" | grep -v '^$' | head -1)
    echo "LotusiaStewardship/lotusd ref: $REF"
    clone_and_checkout "$WORKSPACE" "$REMOTE" "$REF" "lotusd-work" "V1 (mainnet)"
    echo "Build with: make build SERIES=v1"
    exit 0
fi

# ─── doged: Tobias's Dogecoin ABC implementation ─────────────────────────────
if [[ "$SERIES" == "doged" ]]; then
    WORKSPACE="$DAEMON_DIR/workspace-doged"
    VERSION_FILE="$DAEMON_DIR/doged-version"
    REMOTE="https://github.com/doged-io/doged.git"
    REF=$(grep -v '^#' "$VERSION_FILE" | grep -v '^$' | head -1)
    echo "doged-io/doged ref: $REF"
    clone_and_checkout "$WORKSPACE" "$REMOTE" "$REF" "doged-work" "doged"
    echo "Build with: make build SERIES=doged"
    echo ""
    echo "NOTE: eCash fork point unknown. After cloning, run:"
    echo "  cd workspace-doged && git log --oneline | head -20"
    echo "  to find where this diverged from Bitcoin ABC."
    exit 0
fi

# ─── V2: eCash base + Lotus patch series (new chain) ─────────────────────────
WORKSPACE="$DAEMON_DIR/workspace"
ECASH_VERSION_FILE="$DAEMON_DIR/ecash-version"
SERIES_FILE="$DAEMON_DIR/patches/series"
PATCHES_DIR="$DAEMON_DIR/patches"
ECASH_REMOTE="git@github.com:Bitcoin-ABC/bitcoin-abc.git"

ECASH_COMMIT=$(grep -v '^#' "$ECASH_VERSION_FILE" | grep -v '^$' | head -1)
echo "eCash base commit: $ECASH_COMMIT"

if [[ "${1:-}" == "--reset" ]]; then
    echo "Resetting V2 workspace..."
    rm -rf "$WORKSPACE"
fi

if [[ ! -d "$WORKSPACE" ]]; then
    echo "Cloning eCash into workspace/..."
    git clone "$ECASH_REMOTE" "$WORKSPACE"
fi

echo "Checking out pinned commit $ECASH_COMMIT..."
cd "$WORKSPACE"
git fetch origin
git checkout -B lotus-work "$ECASH_COMMIT"

echo "Applying patch series..."
while IFS= read -r line; do
    [[ "$line" =~ ^#.*$ || -z "$line" ]] && continue
    PATCH="$PATCHES_DIR/$line"
    if [[ ! -f "$PATCH" ]]; then
        echo "ERROR: patch not found: $PATCH"
        exit 1
    fi
    echo "  applying $line..."
    git apply --whitespace=nowarn "$PATCH"
    git add -A
    git commit -m "Apply patch: $line" --no-verify 2>/dev/null || true
done < "$SERIES_FILE"

echo ""
echo "V2 workspace ready at: $WORKSPACE"
echo "Build with: make build"
