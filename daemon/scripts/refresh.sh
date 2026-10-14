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
    {
        echo "$NEW_REF"
        echo "# $DESCRIPTION"
        echo "# Previous: $old_ref"
    } > "$version_file"

    if [[ ! -d "$workspace" ]]; then
        echo "Workspace not found — run: make setup SERIES=$series"
        exit 1
    fi

    echo "Resetting workspace to new base..."
    cd "$workspace"
    git fetch origin
    git checkout -B lotus-work "$NEW_REF"

    echo "Re-applying $series patch series..."
    local FAILED=0
    while IFS= read -r line; do
        [[ "$line" =~ ^#.*$ || -z "$line" ]] && continue
        local patch="$patches_dir/$line"
        if [[ ! -f "$patch" ]]; then
            echo "  ERROR: patch not found: $patch"
            FAILED=1
            continue
        fi
        echo -n "  applying $line... "
        if git apply --whitespace=nowarn "$patch" 2>/dev/null; then
            git add -A
            git commit -m "Apply patch: $line" --no-verify 2>/dev/null || true
            echo "OK"
        else
            echo "CONFLICT — manual resolution needed"
            echo "    Patch: $patch"
            FAILED=1
        fi
    done < "$series_file"

    if [[ $FAILED -eq 1 ]]; then
        echo ""
        echo "Some patches need manual resolution."
        echo "Fix conflicts in $workspace, then run: make mkpatch SERIES=$series NAME=<patch-name>"
        exit 1
    fi

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
    git fetch origin --tags
    git checkout -B doged-work "$NEW_REF"

    {
        echo "$NEW_REF"
        echo "# $DESCRIPTION"
        echo "# Previous: $OLD_REF"
    } > "$VERSION_FILE"

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
