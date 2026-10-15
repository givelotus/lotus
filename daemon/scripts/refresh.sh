#!/usr/bin/env bash
# refresh.sh — Advance a series to a new upstream version.
#
#
# SERIES=v1 (default) — reapply Lotus patches onto a new bitcoin-abc commit
#   Usage: SERIES=v1 ./scripts/refresh.sh <commit-or-tag|latest> [description]
# SERIES=ecash / SERIES=bchn — refresh the corresponding reference patch series
#
# SERIES=doged — rebase the maintained ABC patchset only after refreshing its provenance manifest
# SERIES=doged-reference — update the pinned historical doged source reference

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DAEMON_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SERIES="${SERIES:-v1}"
source "$SCRIPT_DIR/upstream-ref.sh"

if [[ $# -lt 1 ]]; then
    echo "Usage: SERIES=<series> $0 <commit-or-tag|latest> [description]"
    exit 1
fi

NEW_REF="$1"
DESCRIPTION="${2:-update}"

# ─── helper: rebase a patchset-based workspace onto a new bitcoin-abc commit ──
rebase_patchset() {
    local series="$1" workspace="$2" version_file="$3"
    local series_file="$DAEMON_DIR/patches/$series/series"
    local patches_dir="$DAEMON_DIR/patches/$series"
    local old_ref
    old_ref=$(grep -v '^#' "$version_file" | grep -v '^$' | head -1)

    echo "Updating $series base: $old_ref → $NEW_REF ($DESCRIPTION)"
    if [[ ! -d "$workspace" ]]; then
        echo "Workspace not found — run: make setup SERIES=$series" >&2
        exit 1
    fi
    if [[ -n "$(git -C "$workspace" status --porcelain)" ]]; then
        echo "Workspace has uncommitted changes; refusing refresh" >&2
        exit 1
    fi
    local resolved
    resolved=$(resolve_upstream_ref "$workspace" "$NEW_REF")
    local extra=(--base "$resolved")
    [[ "$series" == v1 ]] || extra+=(--allow-empty)
    python3 "$SCRIPT_DIR/patch-series.py" "$workspace" "$series_file" "${extra[@]}"
    # Publish the pin only after the entire series succeeds.
    local pin_temp
    pin_temp=$(mktemp "$version_file.XXXXXX")
    {
        echo "$resolved"
        echo "# $DESCRIPTION"
        echo "# Previous: $old_ref"
    } > "$pin_temp"
    mv "$pin_temp" "$version_file"

    echo ""
    echo "Refresh complete. Rebuild with: make build SERIES=$series"
}

# ─── Lotus mainnet: reapply patches on a new pinned bitcoin-abc base ─────────
if [[ "$SERIES" == "v1" ]]; then
    rebase_patchset v1 "$DAEMON_DIR/workspace-v1" "$DAEMON_DIR/bitcoin-abc-v1-version"
    exit 0
fi

# ─── maintained Dogecoin series: require an explicitly refreshed provenance manifest ──
if [[ "$SERIES" == "doged" ]]; then
    echo "Dogecoin's maintained series is pinned with per-patch provenance. Do not advance only the base pin." >&2
    echo "Use make refresh-abc to replay all non-V1 ABC stacks and prepare the shared pin plus Dogecoin provenance together." >&2
    exit 1
fi

# ─── historical Doged source reference ───────────────────────────────────────
if [[ "$SERIES" == "doged-reference" ]]; then
    WORKSPACE="$DAEMON_DIR/workspace-doged-reference"
    VERSION_FILE="$DAEMON_DIR/doged-reference-version"
    OLD_REF=$(grep -v '^#' "$VERSION_FILE" | grep -v '^$' | head -1)
    echo "Advancing historical Doged reference: $OLD_REF → $NEW_REF ($DESCRIPTION)"
    if [[ ! -d "$WORKSPACE" ]]; then
        echo "workspace-doged-reference not found — run: make setup SERIES=doged-reference first" >&2
        exit 1
    fi
    cd "$WORKSPACE"
    if [[ -n "$(git status --porcelain)" ]]; then
        echo "Workspace has uncommitted changes; refusing refresh" >&2
        exit 1
    fi
    RESOLVED=$(resolve_upstream_ref "$WORKSPACE" "$NEW_REF")
    python3 "$SCRIPT_DIR/patch-series.py" "$WORKSPACE" "$DAEMON_DIR/patches/doged-reference/series" \
        --base "$RESOLVED" --allow-empty
    PIN_TEMP=$(mktemp "$VERSION_FILE.XXXXXX")
    { echo "$RESOLVED"; echo "# $DESCRIPTION"; echo "# Previous: $OLD_REF"; } > "$PIN_TEMP"
    mv "$PIN_TEMP" "$VERSION_FILE"
    echo "Build with: make build SERIES=doged-reference"
    exit 0
fi

if [[ "$SERIES" == "bitcoin" ]]; then
    WORKSPACE="$DAEMON_DIR/workspace-bitcoin"
    VERSION_FILE="$DAEMON_DIR/bitcoin-core-version"
    SERIES_FILE="$DAEMON_DIR/patches/bitcoin/series"
    OLD_REF=$(grep -v '^#' "$VERSION_FILE" | grep -v '^$' | head -1)
    if [[ ! -d "$WORKSPACE" ]]; then
        echo "workspace-bitcoin not found — run: make setup SERIES=bitcoin first" >&2
        exit 1
    fi
    if [[ -n "$(git -C "$WORKSPACE" status --porcelain)" ]]; then
        echo "workspace-bitcoin has uncommitted changes; refusing refresh" >&2
        exit 1
    fi
    echo "Updating Bitcoin Core base: $OLD_REF → $NEW_REF ($DESCRIPTION)"
    RESOLVED=$(resolve_upstream_ref "$WORKSPACE" "$NEW_REF")
    python3 "$SCRIPT_DIR/patch-series.py" "$WORKSPACE" "$DAEMON_DIR/patches/bitcoin/series" \
        --base "$RESOLVED" --allow-empty
    PIN_TEMP=$(mktemp "$VERSION_FILE.XXXXXX")
    { echo "$RESOLVED"; echo "# $DESCRIPTION"; echo "# Previous: $OLD_REF"; } > "$PIN_TEMP"
    mv "$PIN_TEMP" "$VERSION_FILE"
    echo "Refresh complete. Build with: make build SERIES=bitcoin"
    exit 0
fi

if [[ "$SERIES" == "ecash" ]]; then
    rebase_patchset ecash "$DAEMON_DIR/workspace-ecash" "$DAEMON_DIR/bitcoin-abc-version"
    exit 0
fi
if [[ "$SERIES" == "bchn" ]]; then
    rebase_patchset bchn "$DAEMON_DIR/workspace-bchn" "$DAEMON_DIR/bchn-version"
    exit 0
fi

echo "Unsupported series: $SERIES (choose v1, ecash, doged, doged-reference, bchn, or bitcoin)" >&2
exit 1
