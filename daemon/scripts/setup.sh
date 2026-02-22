#!/usr/bin/env bash
# setup.sh — Create or reset the daemon build workspace.
# Clones eCash at the pinned commit, then applies the patch series.
#
# Usage: ./scripts/setup.sh [--reset]
#   --reset  wipe existing workspace and start fresh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DAEMON_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
WORKSPACE="$DAEMON_DIR/workspace"
ECASH_VERSION_FILE="$DAEMON_DIR/ecash-version"
SERIES_FILE="$DAEMON_DIR/patches/series"
PATCHES_DIR="$DAEMON_DIR/patches"
ECASH_REMOTE="git@github.com:Bitcoin-ABC/bitcoin-abc.git"

# Read pinned commit (first non-comment line)
ECASH_COMMIT=$(grep -v '^#' "$ECASH_VERSION_FILE" | grep -v '^$' | head -1)
echo "eCash base commit: $ECASH_COMMIT"

if [[ "${1:-}" == "--reset" ]]; then
    echo "Resetting workspace..."
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
    # Skip comments and blank lines
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
echo "Workspace ready at: $WORKSPACE"
echo "Build with: make build"
