#!/usr/bin/env bash
# refresh.sh — Advance a series to a new upstream version.
#
# SERIES=v2   — rebase Lotus new-chain patches onto a new bitcoin-abc commit
#   Usage: SERIES=v2 ./scripts/refresh.sh <bitcoin-abc-commit> [description]
#
# SERIES=v1   — add a new lotusd version as an incremental patch
#   Usage: SERIES=v1 ./scripts/refresh.sh <lotusd-tag> [description]
#   Example: SERIES=v1 ./scripts/refresh.sh v10.4.11 "lotusd v10.4.11"
#
# SERIES=doged — update workspace-doged to a newer doged commit/tag
#   Usage: SERIES=doged ./scripts/refresh.sh <doged-commit-or-tag> [description]
#   Example: SERIES=doged ./scripts/refresh.sh v0.5.0 "doged v0.5.0"

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DAEMON_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SERIES="${SERIES:-v2}"

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

# ─── V1: add new lotusd version as an incremental patch ──────────────────────
if [[ "$SERIES" == "v1" ]]; then
    WORKSPACE="$DAEMON_DIR/workspace-v1"
    LOTUSD_VERSION_FILE="$DAEMON_DIR/lotusd-version"

    if [[ ! -d "$WORKSPACE" ]]; then
        echo "workspace-v1 not found — run: make setup SERIES=v1 first"
        exit 1
    fi

    OLD_REF=$(grep -v '^#' "$LOTUSD_VERSION_FILE" | grep -v '^$' | head -1)
    echo "Advancing v1: $OLD_REF → $NEW_REF ($DESCRIPTION)"

    cd "$WORKSPACE"

    # Ensure lotusd remote exists
    if ! git remote get-url lotusd &>/dev/null; then
        git remote add lotusd https://github.com/LotusiaStewardship/lotusd.git
    fi
    git fetch lotusd --tags

    # Compute diff from current state to new lotusd ref
    DIFF_FILE="/tmp/v1-upgrade-${NEW_REF//\//-}.diff"
    git diff HEAD "lotusd/$NEW_REF" > "$DIFF_FILE" 2>/dev/null \
        || git diff HEAD "$NEW_REF" > "$DIFF_FILE"
    LINES=$(wc -l < "$DIFF_FILE")
    echo "Diff: $DIFF_FILE ($LINES lines)"

    if [[ $LINES -eq 0 ]]; then
        echo "No changes between current HEAD and $NEW_REF — nothing to do."
        exit 0
    fi

    # Apply and commit
    git apply --whitespace=nowarn "$DIFF_FILE"
    git add -A
    git commit -m "lotusd $NEW_REF: $DESCRIPTION" --no-verify

    # Update lotusd-version
    {
        echo "$NEW_REF"
        echo "# $DESCRIPTION"
        echo "# Previous: $OLD_REF"
    } > "$LOTUSD_VERSION_FILE"

    # Determine next patch number
    LAST_NUM=$(grep -v '^#' "$DAEMON_DIR/patches/v1/series" | grep -v '^$' \
        | grep -oP '^\d+' | sort -n | tail -1)
    NEXT_NUM=$(printf "%02d" $((10#$LAST_NUM + 1)))
    PATCH_NAME="${NEXT_NUM}-version-${NEW_REF#v}.patch"

    echo ""
    echo "Next steps:"
    echo "  make mkpatch SERIES=v1 NAME=$PATCH_NAME"
    echo "  Add '$PATCH_NAME' to patches/v1/series"
    echo "  Update lotusd-version comments"
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

# ─── V2: rebase Lotus new-chain patches onto new bitcoin-abc commit ───────────
rebase_patchset v2 "$DAEMON_DIR/workspace" "$DAEMON_DIR/bitcoin-abc-version"
