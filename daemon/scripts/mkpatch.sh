#!/usr/bin/env bash
# mkpatch.sh — Save current workspace changes as a named patch.
#
# SERIES=v2 (default): saves to patches/v2/<name>.patch    from workspace-v2/
# SERIES=v1:           saves to patches/v1/<name>.patch    from workspace-v1/
# SERIES=doged:        saves to patches/doged/<name>.patch from workspace-doged/
# SERIES=ecash:        saves to patches/ecash/<name>.patch from workspace-v2/ (same base)
#
# Usage: ./scripts/mkpatch.sh <patch-name>
#   e.g. ./scripts/mkpatch.sh 06-block-header

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DAEMON_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SERIES="${SERIES:-v2}"

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <patch-name>"
    echo "  e.g. $0 06-block-header"
    exit 1
fi

NAME="$1"
[[ "$NAME" == *.patch ]] || NAME="${NAME}.patch"

if [[ "$SERIES" == "v1" ]]; then
    WORKSPACE="$DAEMON_DIR/workspace-v1"
    PATCHES_DIR="$DAEMON_DIR/patches/v1"
    mkdir -p "$PATCHES_DIR"
elif [[ "$SERIES" == "doged" ]]; then
    WORKSPACE="$DAEMON_DIR/workspace-doged"
    PATCHES_DIR="$DAEMON_DIR/patches/doged"
    mkdir -p "$PATCHES_DIR"
elif [[ "$SERIES" == "ecash" ]]; then
    WORKSPACE="$DAEMON_DIR/workspace-v2"
    PATCHES_DIR="$DAEMON_DIR/patches/ecash"
    mkdir -p "$PATCHES_DIR"
elif [[ "$SERIES" == "bchn" ]]; then
    WORKSPACE="$DAEMON_DIR/workspace-bchn"
    PATCHES_DIR="$DAEMON_DIR/patches/bchn"
    mkdir -p "$PATCHES_DIR"
else
    WORKSPACE="$DAEMON_DIR/workspace-v2"
    PATCHES_DIR="$DAEMON_DIR/patches/v2"
fi

OUTPUT="$PATCHES_DIR/$NAME"

if [[ ! -d "$WORKSPACE" ]]; then
    echo "Workspace not found. Run: make setup SERIES=$SERIES"
    exit 1
fi

cd "$WORKSPACE"

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
