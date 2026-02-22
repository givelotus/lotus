#!/usr/bin/env bash
# refresh.sh — Rebase the patch series onto a new eCash base commit.
# Updates ecash-version, resets workspace to the new base, and attempts
# to re-apply all patches. Reports conflicts for manual resolution.
#
# Usage: ./scripts/refresh.sh <new-ecash-commit> [tag-description]
#   e.g. ./scripts/refresh.sh abc123def456 "eCash v0.27.0"

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DAEMON_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
WORKSPACE="$DAEMON_DIR/workspace"
ECASH_VERSION_FILE="$DAEMON_DIR/ecash-version"
SERIES_FILE="$DAEMON_DIR/patches/series"
PATCHES_DIR="$DAEMON_DIR/patches"

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <new-ecash-commit> [description]"
    exit 1
fi

NEW_COMMIT="$1"
DESCRIPTION="${2:-eCash update}"

OLD_COMMIT=$(grep -v '^#' "$ECASH_VERSION_FILE" | grep -v '^$' | head -1)
echo "Updating eCash base: $OLD_COMMIT → $NEW_COMMIT ($DESCRIPTION)"

# Update the version file
{
    echo "$NEW_COMMIT"
    echo "# $DESCRIPTION"
    echo "# Previous: $OLD_COMMIT"
} > "$ECASH_VERSION_FILE"

# Reset workspace
echo "Resetting workspace to new base..."
cd "$WORKSPACE"
git fetch origin
git checkout -B lotus-work "$NEW_COMMIT"

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
        echo "    Workspace: $WORKSPACE"
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
