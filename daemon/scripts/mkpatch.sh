#!/usr/bin/env bash
# mkpatch.sh — Export the current committed change with its complete metadata.
#
# SERIES=v1 (default):           saves to patches/v1/<name>.patch    from workspace-v1/
# SERIES=doged:        saves to patches/doged/<name>.patch from workspace-doged/
# SERIES=ecash:        saves to patches/ecash/<name>.patch from workspace-ecash/
#
# Usage: ./scripts/mkpatch.sh <patch-name>
#   e.g. ./scripts/mkpatch.sh 06-block-header

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DAEMON_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SERIES="${SERIES:-v1}"

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
    WORKSPACE="$DAEMON_DIR/workspace-ecash"
    PATCHES_DIR="$DAEMON_DIR/patches/ecash"
    mkdir -p "$PATCHES_DIR"
elif [[ "$SERIES" == "bchn" ]]; then
    WORKSPACE="$DAEMON_DIR/workspace-bchn"
    PATCHES_DIR="$DAEMON_DIR/patches/bchn"
    mkdir -p "$PATCHES_DIR"
else
    echo "Unsupported series: $SERIES (choose v1, ecash, doged, or bchn)" >&2
    exit 1
fi

OUTPUT="$PATCHES_DIR/$NAME"

if [[ ! -d "$WORKSPACE" ]]; then
    echo "Workspace not found. Run: make setup SERIES=$SERIES"
    exit 1
fi

cd "$WORKSPACE"

# Commit first: this makes authorship, rationale and the exact change reviewable.
if [[ -n "$(git status --porcelain)" ]]; then
    echo "Commit your intended patch (including its rationale) first; workspace must be clean." >&2
    exit 1
fi
if [[ "$NAME" == */* || "$NAME" == .* || -e "$OUTPUT" ]]; then
    echo "Invalid patch name or patch already exists: $NAME" >&2
    exit 1
fi
if [[ "$(git rev-list --parents -n 1 HEAD | wc -w)" -ne 2 ]]; then
    echo "HEAD must be one non-merge patch commit." >&2
    exit 1
fi
TEMP=$(mktemp "$PATCHES_DIR/.mkpatch.XXXXXX")
trap 'rm -f "$TEMP"' EXIT
git -c format.signature= format-patch --stdout --binary --full-index --no-stat -1 HEAD > "$TEMP"
if ! grep -q '^diff --git ' "$TEMP"; then
    echo "HEAD has no patch to export." >&2
    exit 1
fi
mv "$TEMP" "$OUTPUT"
echo "Saved: $OUTPUT"
echo "Review it and add $NAME to $PATCHES_DIR/series in the intended order."
