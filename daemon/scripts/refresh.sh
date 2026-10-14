#!/usr/bin/env bash
# refresh.sh — Advance a series to a new upstream version.
#
#
# SERIES=v1 (default) — reapply Lotus patches onto a new bitcoin-abc commit
#   Usage: SERIES=v1 ./scripts/refresh.sh <bitcoin-abc-commit> [description]
# SERIES=ecash / SERIES=bchn — refresh the corresponding reference patch series
#
# SERIES=doged — update workspace-doged to a newer doged commit/tag
#   Usage: SERIES=doged ./scripts/refresh.sh <doged-commit-or-tag> [description]
#   Example: SERIES=doged ./scripts/refresh.sh v0.5.0 "doged v0.5.0"

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DAEMON_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SERIES="${SERIES:-v1}"

if [[ $# -lt 1 ]]; then
    echo "Usage: SERIES=<series> $0 <new-ref> [description]"
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
    git -C "$workspace" fetch origin
    local resolved
    resolved=$(git -C "$workspace" rev-parse --verify "$NEW_REF^{commit}")
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

# ─── doged: update workspace-doged to a newer commit/tag ─────────────────────
if [[ "$SERIES" == "doged" ]]; then
    WORKSPACE="$DAEMON_DIR/workspace-doged"
    VERSION_FILE="$DAEMON_DIR/doged-version"

    OLD_REF=$(grep -v '^#' "$VERSION_FILE" | grep -v '^$' | head -1)
    echo "Advancing doged: $OLD_REF → $NEW_REF ($DESCRIPTION)"

    if [[ ! -d "$WORKSPACE" ]]; then
        echo "workspace-doged not found — run: make setup SERIES=doged first"
        exit 1
    fi

    cd "$WORKSPACE"
    if [[ -n "$(git status --porcelain)" ]]; then
        echo "Workspace has uncommitted changes; refusing refresh" >&2
        exit 1
    fi
    git fetch origin --tags
    RESOLVED=$(git rev-parse --verify "$NEW_REF^{commit}")
    python3 "$SCRIPT_DIR/patch-series.py" "$WORKSPACE" "$DAEMON_DIR/patches/doged/series" \
        --base "$RESOLVED" --allow-empty

    PIN_TEMP=$(mktemp "$VERSION_FILE.XXXXXX")
    {
        echo "$RESOLVED"
        echo "# $DESCRIPTION"
        echo "# Previous: $OLD_REF"
    } > "$PIN_TEMP"
    mv "$PIN_TEMP" "$VERSION_FILE"

    echo ""
    echo "doged workspace now at: $NEW_REF"
    echo "Rebuild with: make build SERIES=doged"
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

echo "Unsupported series: $SERIES (choose v1, ecash, doged, or bchn)" >&2
exit 1
