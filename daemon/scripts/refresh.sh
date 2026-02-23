#!/usr/bin/env bash
# refresh.sh — Update to a new base version.
#
# SERIES=v2: rebase eCash patch series onto a new eCash commit
# SERIES=v1: advance LotusiaStewardship/lotusd to a new tag or commit
#
# Usage: ./scripts/refresh.sh <new-commit-or-tag> [description]
#   V2: ./scripts/refresh.sh abc123def456 "eCash v0.27.0"
#   V1: ./scripts/refresh.sh v10.4.11 "LotusiaStewardship v10.4.11"

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DAEMON_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SERIES="${SERIES:-v2}"

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <new-commit-or-tag> [description]"
    exit 1
fi

NEW_REF="$1"
DESCRIPTION="${2:-update}"

# ─── helper: advance a direct-clone workspace ────────────────────────────────
advance_clone() {
    local series="$1" version_file="$2" workspace="$3" branch="$4"
    local old_ref new_ref="$NEW_REF" desc="$DESCRIPTION"
    old_ref=$(grep -v '^#' "$version_file" | grep -v '^$' | head -1)
    echo "Updating $series base: $old_ref → $new_ref ($desc)"
    { echo "$new_ref"; echo "# $desc"; echo "# Previous: $old_ref"; } > "$version_file"
    if [[ -d "$workspace" ]]; then
        cd "$workspace"
        git fetch origin
        git checkout -B "$branch" "$new_ref"
        echo "Workspace updated to $new_ref"
    else
        echo "Workspace not found — run: make setup SERIES=$series"
    fi
    echo "Refresh complete. Rebuild with: make build SERIES=$series"
    exit 0
}

# ─── V1: advance lotusd version ───────────────────────────────────────────────
if [[ "$SERIES" == "v1" ]]; then
    advance_clone v1 "$DAEMON_DIR/lotusd-version" "$DAEMON_DIR/workspace-v1" lotusd-work
fi

# ─── doged: advance doged version ────────────────────────────────────────────
if [[ "$SERIES" == "doged" ]]; then
    advance_clone doged "$DAEMON_DIR/doged-version" "$DAEMON_DIR/workspace-doged" doged-work
fi

# ─── V2: rebase eCash patch series ────────────────────────────────────────────
WORKSPACE="$DAEMON_DIR/workspace"
ECASH_VERSION_FILE="$DAEMON_DIR/ecash-version"
SERIES_FILE="$DAEMON_DIR/patches/series"
PATCHES_DIR="$DAEMON_DIR/patches"

OLD_COMMIT=$(grep -v '^#' "$ECASH_VERSION_FILE" | grep -v '^$' | head -1)
echo "Updating V2 base: $OLD_COMMIT → $NEW_REF ($DESCRIPTION)"

{
    echo "$NEW_REF"
    echo "# $DESCRIPTION"
    echo "# Previous: $OLD_COMMIT"
} > "$ECASH_VERSION_FILE"

echo "Resetting workspace to new base..."
cd "$WORKSPACE"
git fetch origin
git checkout -B lotus-work "$NEW_REF"

echo "Re-applying patch series..."
FAILED=0
while IFS= read -r line; do
    [[ "$line" =~ ^#.*$ || -z "$line" ]] && continue
    PATCH="$PATCHES_DIR/$line"
    if [[ ! -f "$PATCH" ]]; then
        echo "  ERROR: patch not found: $PATCH"
        FAILED=1
        continue
    fi
    echo -n "  applying $line... "
    if git apply --whitespace=nowarn "$PATCH" 2>/dev/null; then
        git add -A
        git commit -m "Apply patch: $line" --no-verify 2>/dev/null || true
        echo "OK"
    else
        echo "CONFLICT — manual resolution needed"
        echo "    Patch: $PATCH"
        FAILED=1
    fi
done < "$SERIES_FILE"

if [[ $FAILED -eq 1 ]]; then
    echo ""
    echo "Some patches need manual resolution."
    echo "Fix conflicts in $WORKSPACE, then run: make mkpatch NAME=<patch-name>"
    exit 1
fi

echo ""
echo "Refresh complete. Rebuild with: make build"
