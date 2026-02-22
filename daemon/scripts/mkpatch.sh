#!/usr/bin/env bash
# mkpatch.sh — Save current workspace changes as a named patch.
# Use this after editing files in the workspace to capture changes
# back into the patch series.
#
# Usage: ./scripts/mkpatch.sh <patch-name>
#   e.g. ./scripts/mkpatch.sh 06-block-header

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DAEMON_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
WORKSPACE="$DAEMON_DIR/workspace"
PATCHES_DIR="$DAEMON_DIR/patches"

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <patch-name>"
    echo "  e.g. $0 06-block-header"
    exit 1
fi

NAME="$1"
[[ "$NAME" == *.patch ]] || NAME="${NAME}.patch"
OUTPUT="$PATCHES_DIR/$NAME"

if [[ ! -d "$WORKSPACE" ]]; then
    echo "Workspace not found. Run: make setup"
    exit 1
fi

cd "$WORKSPACE"

# Diff against HEAD (staged + unstaged changes)
DIFF=$(git diff HEAD)
if [[ -z "$DIFF" ]]; then
    DIFF=$(git diff --cached HEAD)
fi

if [[ -z "$DIFF" ]]; then
    echo "No changes in workspace to save."
    exit 1
fi

echo "$DIFF" > "$OUTPUT"
echo "Saved: $OUTPUT"
echo "Lines: $(wc -l < "$OUTPUT")"
