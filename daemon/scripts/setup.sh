#!/usr/bin/env bash
# setup.sh — Create or replay a daemon build workspace.
#
# SERIES=v1 (default):           clone bitcoin-abc at bitcoin-abc-v1-version, apply V1 patch series (153 patches)
# SERIES=doged:        clone doged-io/doged directly at doged-version tag/branch
# SERIES=bchn:         clone bitcoin-cash-node at pinned tag, apply patches 29-31
#
# Usage: ./scripts/setup.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DAEMON_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SERIES="${SERIES:-v1}"

if [[ $# -gt 0 || -n "${RESET:-}" ]]; then
    echo "Setup no longer deletes workspaces. Preserve or move the old workspace, then rerun without --reset/RESET." >&2
    exit 1
fi

# ─── helper: clone-and-checkout ──────────────────────────────────────────────
clone_and_checkout() {
    local workspace="$1" remote="$2" ref="$3" branch="$4" label="$5"
    if [[ ! -d "$workspace" ]]; then
        echo "Cloning $remote into $(basename "$workspace")/..."
        git clone "$remote" "$workspace"
    fi
    if [[ -n "$(git -C "$workspace" status --porcelain)" ]]; then
        echo "ERROR: workspace has uncommitted changes; preserve them before setup" >&2
        exit 1
    fi
    echo "Checking out $ref..."
    cd "$workspace"
    git fetch origin
    # Replay is promoted atomically; keep the existing HEAD intact on failure.
    if ! git rev-parse --verify HEAD >/dev/null 2>&1; then
        git checkout -b "$branch" "$ref"
    fi
    echo ""
    echo "$label workspace ready at: $workspace"
}

# ─── helper: apply-patch-series ──────────────────────────────────────────────
apply_patch_series() {
    local series_file="$1" patches_dir="$2"
    python3 "$SCRIPT_DIR/patch-series.py" "$PWD" "$series_file" --base "$REF"
}

# ─── V1: independently pinned bitcoin-abc base + Lotus mainnet patch series ───────────────
if [[ "$SERIES" == "v1" ]]; then
    WORKSPACE="$DAEMON_DIR/workspace-v1"
    VERSION_FILE="$DAEMON_DIR/bitcoin-abc-v1-version"
    SERIES_FILE="$DAEMON_DIR/patches/v1/series"
    PATCHES_DIR="$DAEMON_DIR/patches/v1"
    REMOTE="${BITCOIN_ABC_REMOTE:-https://github.com/Bitcoin-ABC/bitcoin-abc.git}"
    REF=$(grep -v '^#' "$VERSION_FILE" | grep -v '^$' | head -1)
    echo "bitcoin-abc ref: $REF"
    clone_and_checkout "$WORKSPACE" "$REMOTE" "$REF" "lotus-v1-work" "V1 (Lotus mainnet)"
    apply_patch_series "$SERIES_FILE" "$PATCHES_DIR"
    echo ""
    echo "V1 workspace ready at: $WORKSPACE"
    echo "Build with: make build SERIES=v1"
    exit 0
fi

# ─── doged: direct clone of doged-io/doged at pinned version ─────────────────
if [[ "$SERIES" == "doged" ]]; then
    WORKSPACE="$DAEMON_DIR/workspace-doged"
    VERSION_FILE="$DAEMON_DIR/doged-version"
    REMOTE="git@github.com:doged-io/doged.git"
    REF=$(grep -v '^#' "$VERSION_FILE" | grep -v '^$' | head -1)
    echo "doged ref: $REF"
    clone_and_checkout "$WORKSPACE" "$REMOTE" "$REF" "doged-work" "doged"
    git checkout -B doged-work "$REF"
    echo ""
    echo "doged workspace ready at: $WORKSPACE"
    echo "Build with: make build SERIES=doged"
    echo "NOTE: doged is a direct clone — no patches applied (it is its own patchset)."
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

# ─── eCash: pinned bitcoin-abc base + upstream candidate patches ────────────
if [[ "$SERIES" == "ecash" ]]; then
    WORKSPACE="$DAEMON_DIR/workspace-ecash"
    VERSION_FILE="$DAEMON_DIR/bitcoin-abc-version"
    SERIES_FILE="$DAEMON_DIR/patches/ecash/series"
    PATCHES_DIR="$DAEMON_DIR/patches/ecash"
    REMOTE="${BITCOIN_ABC_REMOTE:-https://github.com/Bitcoin-ABC/bitcoin-abc.git}"
    REF=$(grep -v '^#' "$VERSION_FILE" | grep -v '^$' | head -1)
    echo "bitcoin-abc ref: $REF"
    clone_and_checkout "$WORKSPACE" "$REMOTE" "$REF" "ecash-work" "eCash candidates"
    apply_patch_series "$SERIES_FILE" "$PATCHES_DIR"
    echo "Build with: make build SERIES=ecash"
    exit 0
fi

echo "Unsupported series: $SERIES (choose v1, ecash, doged, or bchn)" >&2
exit 1
