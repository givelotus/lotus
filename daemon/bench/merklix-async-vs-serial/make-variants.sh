#!/bin/sh
# Builds A (production commitment.cpp, byte-identical copy) and B (same file,
# one token changed). Run ONLY inside an authorized exclusive window.
set -eu
SRC=${SRC:-/Users/shammah/repos/lotus-v2-repaired-source}
HERE=$(cd "$(dirname "$0")" && pwd)
OUT=$HERE/build
mkdir -p "$OUT"
EXPECT_COMMIT=657edc0133cac8d54c5570506dad57bf10e300b5
if [ -f "$SRC/SOURCE.json" ]; then
    python3 - "$SRC" "$EXPECT_COMMIT" <<'VERIFY'
import hashlib,json,pathlib,sys
root=pathlib.Path(sys.argv[1]); manifest=json.loads((root/'SOURCE.json').read_text())
assert manifest['commit']==sys.argv[2], 'source commit mismatch'
for name,digest in manifest['files'].items():
    assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest, name
VERIFY
else
    [ "$(git -C "$SRC" rev-parse HEAD)" = "$EXPECT_COMMIT" ] || { echo "source commit mismatch"; exit 1; }
    [ -z "$(git -C "$SRC" status --porcelain)" ] || { echo "source dirty"; exit 1; }
fi
cp "$SRC/src/lotus_v2/commitment.cpp" "$OUT/commitment_A.cpp"
# B: the only change is disabling the recursive async dispatch condition.
sed 's/if (depth < 4 && entries.size() >= 64 && !left.empty() && !right.empty()) {/if (false \&\& depth < 4 \&\& entries.size() >= 64 \&\& !left.empty() \&\& !right.empty()) {/' \
    "$OUT/commitment_A.cpp" > "$OUT/commitment_B.cpp"
# C: persistent fixed pool (pool_dispatch.inc) replacing only std::async dispatch.
python3 - "$OUT/commitment_A.cpp" "$OUT/commitment_C.cpp" "$OUT/commitment_D.cpp" "$HERE/pool_dispatch.inc" "$HERE/work_pool.h" <<'PY'
import sys
a=open(sys.argv[1]).read(); inc=open(sys.argv[4]).read()
old="""        auto left_future = std::async(std::launch::async, [left, depth]() {
            return TransactionSubtreeA(left, depth + 1);
        });
        const Hash right_hash = TransactionSubtreeA(right, depth + 1);
        return TxNodeAtDepth(depth, left_future.get(), right_hash);
"""
new="""        ForkJoin fj([left, depth]() { return TransactionSubtreeA(left, depth + 1); });
        const Hash right_hash = TransactionSubtreeA(right, depth + 1);
        return TxNodeAtDepth(depth, fj.Join(), right_hash);
"""
assert a.count(old)==1
marker="Hash TransactionSubtreeA(std::span<const TxIdentityPair *> entries,"
assert a.count(marker)==1
headers="\n".join(line for line in inc.splitlines() if line.startswith("#include"))
inc="\n".join(line for line in inc.splitlines() if not line.startswith("#include"))
a=headers+"\n"+a.replace(old,new).replace(marker,inc+"\n"+marker)
open(sys.argv[2],"w").write(a)
PY
# D: generic persistent pool with growth (work_pool.h); same thresholds/partitioning.
python3 - "$OUT/commitment_A.cpp" "$OUT/commitment_D.cpp" <<'PY'
import sys
a=open(sys.argv[1]).read()
old="""        auto left_future = std::async(std::launch::async, [left, depth]() {
            return TransactionSubtreeA(left, depth + 1);
        });
        const Hash right_hash = TransactionSubtreeA(right, depth + 1);
        return TxNodeAtDepth(depth, left_future.get(), right_hash);
"""
new="""        auto left_future = util::WorkPool::Shared().Async([left, depth]() {
            return TransactionSubtreeA(left, depth + 1);
        });
        const Hash right_hash = TransactionSubtreeA(right, depth + 1);
        return TxNodeAtDepth(depth, left_future.Get(), right_hash);
"""
assert a.count(old)==1
inc='#include "work_pool.h"\n'
marker='#include "tagged_hash.h"\n'
assert a.count(marker)==1
open(sys.argv[2],"w").write(a.replace(old,new).replace(marker,marker+inc))
PY
diff -u "$OUT/commitment_A.cpp" "$OUT/commitment_D.cpp" > "$OUT/A-vs-D.diff" || true
diff -u "$OUT/commitment_A.cpp" "$OUT/commitment_B.cpp" > "$OUT/A-vs-B.diff" || true
diff -u "$OUT/commitment_A.cpp" "$OUT/commitment_C.cpp" > "$OUT/A-vs-C.diff" || true
[ "$(grep -c '^[-+][^-+]' "$OUT/A-vs-B.diff")" = 2 ] || { echo "B must differ by exactly one line"; exit 1; }
CXX=${CXX:-/usr/bin/c++}
CFLAGS="-std=c++20 -O3 -DNDEBUG -pthread -I$SRC/src -I$SRC/src/lotus_v2 -I$HERE"
BL=$SRC/src/lotus_v2/vendor/blake3
# BLAKE3 compiled once from vendored sources (NEON path), shared by both.
for f in blake3 blake3_dispatch blake3_portable; do
  /usr/bin/cc -O3 -DNDEBUG -DBLAKE3_NO_SSE2 -DBLAKE3_NO_SSE41 -DBLAKE3_NO_AVX2 -DBLAKE3_NO_AVX512 -DBLAKE3_USE_NEON=1 -c "$BL/$f.c" -o "$OUT/$f.o"
done
/usr/bin/cc -O3 -DNDEBUG -DBLAKE3_NO_SSE2 -DBLAKE3_NO_SSE41 -DBLAKE3_NO_AVX2 -DBLAKE3_NO_AVX512 -DBLAKE3_USE_NEON=1 -c "$BL/blake3_neon.c" -o "$OUT/blake3_neon.o"
ar rcs "$OUT/libblake3.a" "$OUT"/blake3*.o
$CXX $CFLAGS -c "$SRC/src/lotus_v2/tagged_hash.cpp" -o "$OUT/tagged_hash.o"
$CXX $CFLAGS -c "$HERE/bench.cpp" -o "$OUT/bench.o"
for v in A B C D; do
  $CXX $CFLAGS -c "$OUT/commitment_$v.cpp" -o "$OUT/commitment_$v.o"
  $CXX -O3 -pthread "$OUT/bench.o" "$OUT/commitment_$v.o" "$OUT/tagged_hash.o" "$OUT/libblake3.a" -o "$OUT/bench_$v"
done
shasum -a 256 "$SRC/src/lotus_v2/commitment.cpp" "$OUT/commitment_B.cpp" "$OUT/commitment_C.cpp" "$OUT/commitment_D.cpp" "$HERE/pool_dispatch.inc" "$HERE/work_pool.h" "$HERE/bench.cpp" "$OUT/bench_A" "$OUT/bench_B" "$OUT/bench_C" "$OUT/bench_D" "$OUT/libblake3.a" > "$OUT/HASHES.txt"
cat "$OUT/HASHES.txt"
