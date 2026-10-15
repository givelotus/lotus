#!/usr/bin/env bash
# setup.sh — Create or replay a daemon build workspace.
#
# SERIES=v1 (default):           clone bitcoin-abc at bitcoin-abc-v1-version, apply V1 patch series (153 patches)
# SERIES=doged:        clone the shared Bitcoin ABC pin and apply maintained Dogecoin patches
# SERIES=doged-reference: clone the pinned historical doged-io/doged reference
# SERIES=bchn/ecash:   pinned base only; experimental features require explicit review
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
    local extra=(--base "$REF")
    [[ "${3:-}" != base-only ]] || extra+=(--allow-empty)
    python3 "$SCRIPT_DIR/patch-series.py" "$PWD" "$series_file" "${extra[@]}"
}

# Bitcoin Core is a separate BTC source pin, not the ABC binary named bitcoind.
if [[ "$SERIES" == "bitcoin" ]]; then
    WORKSPACE="$DAEMON_DIR/workspace-bitcoin"
    REF=$(head -1 "$DAEMON_DIR/bitcoin-core-version")
    clone_and_checkout "$WORKSPACE" "${BITCOIN_CORE_REMOTE:-https://github.com/bitcoin/bitcoin.git}" "$REF" "bitcoin-core-work" "Bitcoin Core BTC"
    apply_patch_series "$DAEMON_DIR/patches/bitcoin/series" "$DAEMON_DIR/patches/bitcoin" base-only
    exit 0
fi

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

# ─── doged: current-ABC Dogecoin implementation ─────────────────────────────
if [[ "$SERIES" == "doged" ]]; then
    WORKSPACE="$DAEMON_DIR/workspace-doged-abc"
    VERSION_FILE="$DAEMON_DIR/bitcoin-abc-version"
    SERIES_FILE="$DAEMON_DIR/patches/doged/series"
    PATCHES_DIR="$DAEMON_DIR/patches/doged"
    REMOTE="${BITCOIN_ABC_REMOTE:-https://github.com/Bitcoin-ABC/bitcoin-abc.git}"
    REF=$(grep -v '^#' "$VERSION_FILE" | grep -v '^$' | head -1)
    echo "Dogecoin Bitcoin ABC ref: $REF"
    clone_and_checkout "$WORKSPACE" "$REMOTE" "$REF" "doged-abc-work" "Dogecoin on Bitcoin ABC"
    python3 "$SCRIPT_DIR/patch-series.py" "$PWD" "$SERIES_FILE" --base "$REF" \
        --provenance "$PATCHES_DIR/manifest.json" --expect-tree 2b378152efca0ea2c578433f348e71db367202b0
    echo ""
    echo "Dogecoin workspace ready at: $WORKSPACE"
    echo "Build with: make build SERIES=doged"
    echo "Maintained 174-patch Dogecoin series on the immutable ABC pin."
    exit 0
fi

# ─── historical doged source reference ───────────────────────────────────────
if [[ "$SERIES" == "doged-reference" ]]; then
    WORKSPACE="$DAEMON_DIR/workspace-doged-reference"
    VERSION_FILE="$DAEMON_DIR/doged-reference-version"
    REMOTE="${DOGED_REMOTE:-https://github.com/doged-io/doged.git}"
    REF=$(grep -v '^#' "$VERSION_FILE" | grep -v '^$' | head -1)
    echo "doged reference: $REF"
    clone_and_checkout "$WORKSPACE" "$REMOTE" "$REF" "doged-reference-work" "historical Doged reference"
    apply_patch_series "$DAEMON_DIR/patches/doged-reference/series" "$DAEMON_DIR/patches/doged-reference" base-only
    echo "Build with: make build SERIES=doged-reference"
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
    apply_patch_series "$SERIES_FILE" "$PATCHES_DIR" base-only
    echo ""
    echo "BCHN workspace ready at: $WORKSPACE"
    echo "Build with: make build SERIES=bchn"
    echo ""
    echo "Experimental mining candidates are excluded; see docs/support-matrix.md."
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
    apply_patch_series "$SERIES_FILE" "$PATCHES_DIR" base-only
    echo "Build with: make build SERIES=ecash"
    exit 0
fi

echo "Unsupported series: $SERIES (choose v1, ecash, doged, doged-reference, bchn, or bitcoin)" >&2
exit 1
