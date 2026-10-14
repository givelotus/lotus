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
SOURCE_VERSION="$(sed -nE 's/^[[:space:]]*VERSION ([0-9]+\.[0-9]+\.[0-9]+)$/\1/p' "$SOURCE/CMakeLists.txt")"
[[ "$SOURCE_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "Source has no unique semantic project version." >&2; exit 1; }
LOTUS_CHRONIK="${LOTUS_CHRONIK:-ON}"
LOTUS_NNG="${LOTUS_NNG:-ON}"
for feature in "$LOTUS_CHRONIK" "$LOTUS_NNG"; do
    [[ "$feature" == ON || "$feature" == OFF ]] || { echo "Feature switches must be ON or OFF." >&2; exit 1; }
done
export LOTUS_CHRONIK LOTUS_NNG
mkdir -p "$CANDIDATE"
CANDIDATE="$(cd "$CANDIDATE" && pwd)"
git clone --no-hardlinks --dissociate "$SOURCE" "$CANDIDATE/source"
git -C "$CANDIDATE/source" checkout --detach "$SOURCE_COMMIT"
python3 "$SCRIPT_DIR/patch-series.py" "$CANDIDATE/source" "$DAEMON_DIR/candidates/guix/series" --base "$SOURCE_COMMIT"
cd "$CANDIDATE/source"
printf 'source_commit=%s\nsource_tree=%s\nadapted_commit=%s\nadapted_tree=%s\nsource_date_epoch=%s\nchronik=%s\nnng=%s\n' \
    "$SOURCE_COMMIT" "$SOURCE_TREE" "$(git rev-parse HEAD)" "$(git rev-parse 'HEAD^{tree}')" "$SOURCE_EPOCH" "$LOTUS_CHRONIK" "$LOTUS_NNG" > "$CANDIDATE/inputs.txt"
export HOSTS=x86_64-linux-gnu JOBS="${JOBS:-2}"
export SOURCE_DATE_EPOCH="$SOURCE_EPOCH" FORCE_SOURCE_DATE_EPOCH=1
FORCE_VERSION="$SOURCE_VERSION"
export FORCE_VERSION
export DISTNAME="lotus-${FORCE_VERSION}" OUTDIR_BASE="$CANDIDATE/output"
./contrib/guix/guix-build
cp "$CANDIDATE/inputs.txt" "$CANDIDATE/output/inputs.txt"

# Exercise the archive itself with a new, disconnected datadir on this builder.
ARCHIVE="$CANDIDATE/output/x86_64-linux-gnu/lotus-${FORCE_VERSION}-x86_64-linux-gnu.tar.gz"
mkdir "$CANDIDATE/extracted" "$CANDIDATE/smoke-data"
tar -C "$CANDIDATE/extracted" -xzf "$ARCHIVE"
BIN="$CANDIDATE/extracted/lotus-${FORCE_VERSION}/bin"
"$BIN/lotusd" --version
"$BIN/lotus-cli" --version
ldd "$BIN/lotusd" | tee "$CANDIDATE/output/runtime-libraries.txt"
if grep -q 'not found' "$CANDIDATE/output/runtime-libraries.txt"; then
    echo 'Archive has unresolved runtime dependencies.' >&2
    exit 1
fi
CLI=("$BIN/lotus-cli" "-datadir=$CANDIDATE/smoke-data" -rpcport=18432)
cleanup() { "${CLI[@]}" stop >/dev/null 2>&1 || true; }
trap cleanup EXIT
NODE_ARGS=("-datadir=$CANDIDATE/smoke-data" -rpcport=18432 -listen=0 -connect=0 -dnsseed=0 -discover=0 -assumevalid=0 -daemonwait)
[[ "$LOTUS_CHRONIK" != ON ]] || NODE_ARGS+=(-chronik=1 -chronikbind=127.0.0.1:18431)
"$BIN/lotusd" "${NODE_ARGS[@]}"
timeout 60 "${CLI[@]}" -rpcwait getblockchaininfo
"${CLI[@]}" verifychain 4 0
# An empty watch-only wallet confirms packaged wallet RPC support without keys.
"${CLI[@]}" createwallet guix-smoke true true
"${CLI[@]}" getwalletinfo
"${CLI[@]}" unloadwallet guix-smoke
if [[ "$LOTUS_CHRONIK" == ON ]]; then
    python3 "$SCRIPT_DIR/check-v1-chronik.py" --cli "$BIN/lotus-cli" --datadir "$CANDIDATE/smoke-data" --rpcport 18432 --chronik-url http://127.0.0.1:18431 --heights 0
fi
cleanup
trap - EXIT
