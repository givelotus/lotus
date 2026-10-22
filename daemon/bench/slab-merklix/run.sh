#!/usr/bin/env bash
# Build and run the slab Merklix microbenchmarks and the standalone TSAN
# stress against an exact source checkout and its configured build directory.
# Usage: run.sh <source-dir> <build-dir> <out-dir> [sizes...]
# The build directory must already contain the CMake build of <source-dir>
# (liblotus_v2_header.a etc.). Measurements are microbenchmarks only.
set -euo pipefail
SRC=$(cd "$1" && pwd)/src
BLD=$(cd "$2" && pwd)
OUT=$3
shift 3
SIZES=("$@")
[[ ${#SIZES[@]} -gt 0 ]] || SIZES=(5000 100000 500000)
HERE=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$OUT"
LIBS=("$BLD/src/lotus_v2/liblotus_v2_header.a" "$BLD/src/lotus_v2/liblotus_v2_blake3.a"
      "$BLD/src/libutil.a" "$BLD/src/crypto/libcrypto.a" "$BLD/src/crypto/libcrypto_arm_shani.a"
      "$BLD/src/secp256k1/libsecp256k1.a")
clang++ -std=c++20 -O2 -DNDEBUG -I"$SRC" -I"$SRC/lotus_v2" -I"$BLD/src" -I/opt/homebrew/include \
  "$HERE/microbench.cpp" "${LIBS[@]}" -o "$OUT/microbench"
TS="$OUT/tsan"
mkdir -p "$TS"
for f in blake3.c blake3_dispatch.c blake3_portable.c blake3_neon.c; do
  clang -O1 -g -fsanitize=thread -c "$SRC/lotus_v2/vendor/blake3/$f" -o "$TS/$f.o"
done
clang++ -std=c++20 -O1 -g -fsanitize=thread -I"$SRC" -I"$SRC/lotus_v2" -I"$BLD/src" \
  "$HERE/tsan_stress.cpp" "$SRC/lotus_v2/tx_merklix.cpp" "$SRC/lotus_v2/minhash.cpp" \
  "$SRC/lotus_v2/tagged_hash.cpp" "$SRC/lotus_v2/commitment.cpp" "$SRC/crypto/siphash.cpp" \
  "$TS"/*.o -o "$TS/tsan_stress"
{
  echo "{"
  echo "  \"source_head\": \"$(git -C "$SRC/.." rev-parse HEAD)\","
  echo "  \"source_tree\": \"$(git -C "$SRC/.." rev-parse HEAD^{tree})\","
  echo "  \"source_dirty\": $( [[ -z $(git -C "$SRC/.." status --porcelain --untracked-files=no) ]] && echo false || echo true ),"
  echo "  \"microbench_sha256\": \"$(shasum -a 256 "$OUT/microbench" | cut -d' ' -f1)\","
  echo "  \"microbench_cpp_sha256\": \"$(shasum -a 256 "$HERE/microbench.cpp" | cut -d' ' -f1)\","
  echo "  \"tsan_stress_sha256\": \"$(shasum -a 256 "$TS/tsan_stress" | cut -d' ' -f1)\","
  echo "  \"compiler\": \"$(clang++ --version | head -1)\","
  echo "  \"host\": \"$(sysctl -n machdep.cpu.brand_string) $(sysctl -n hw.ncpu)cpu\","
  echo "  \"started_utc\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\""
  echo "}"
} > "$OUT/identity.json"
TSAN_OPTIONS="halt_on_error=1 exitcode=66" "$TS/tsan_stress" 400 > "$OUT/tsan_stress.log" 2>&1
echo "tsan_exit=$?" >> "$OUT/tsan_stress.log"
for rep in 1 2 3; do
  "$OUT/microbench" "${SIZES[@]}" > "$OUT/microbench-rep$rep.jsonl"
done
date -u +%Y-%m-%dT%H:%M:%SZ > "$OUT/finished_utc.txt"
