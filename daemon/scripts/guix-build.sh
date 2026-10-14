#!/usr/bin/env bash
# Prepare and build an isolated Guix candidate; never edits the input workspace.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DAEMON_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
if [[ $# != 2 ]]; then
    echo "Usage: $0 CLEAN_LOTUS_SOURCE NEW_BUILD_DIRECTORY" >&2
    exit 2
fi
SOURCE="$(cd "$1" && pwd)"
CANDIDATE="$2"
[[ "$(uname -s)" == Linux ]] || { echo 'Guix containers require Linux; use artifact-only guix-daemon.yml CI.' >&2; exit 1; }
[[ ! -e "$CANDIDATE" ]] || { echo 'Build directory already exists; preserve it and select a new path.' >&2; exit 1; }
[[ -z "$(git -C "$SOURCE" status --porcelain --untracked-files=no)" ]] || { echo 'Source has tracked modifications.' >&2; exit 1; }
command -v guix >/dev/null
SOURCE_COMMIT="$(git -C "$SOURCE" rev-parse HEAD)"
SOURCE_TREE="$(git -C "$SOURCE" rev-parse 'HEAD^{tree}')"
SOURCE_EPOCH="$(git -C "$SOURCE" show -s --format=%at HEAD)"
mkdir -p "$CANDIDATE"
CANDIDATE="$(cd "$CANDIDATE" && pwd)"
git clone --no-hardlinks "$SOURCE" "$CANDIDATE/source"
git -C "$CANDIDATE/source" checkout --detach "$SOURCE_COMMIT"
git -C "$CANDIDATE/source" -c user.name='Lotus Guix candidate' -c user.email='builds@givelotus.org' am --committer-date-is-author-date --keep-non-patch "$DAEMON_DIR/candidates/guix/000-lotus-guix-linux.patch"
cd "$CANDIDATE/source"
printf 'source_commit=%s\nsource_tree=%s\nadapted_commit=%s\nadapted_tree=%s\nsource_date_epoch=%s\n' \
    "$SOURCE_COMMIT" "$SOURCE_TREE" "$(git rev-parse HEAD)" "$(git rev-parse 'HEAD^{tree}')" "$SOURCE_EPOCH" > "$CANDIDATE/inputs.txt"
export HOSTS=x86_64-linux-gnu JOBS="${JOBS:-2}"
export SOURCE_DATE_EPOCH="$SOURCE_EPOCH" FORCE_SOURCE_DATE_EPOCH=1
FORCE_VERSION="$(cat "$DAEMON_DIR/release-version")"
export FORCE_VERSION
export DISTNAME="lotus-${FORCE_VERSION}" OUTDIR_BASE="$CANDIDATE/output"
./contrib/guix/guix-build
cp "$CANDIDATE/inputs.txt" "$CANDIDATE/output/inputs.txt"
