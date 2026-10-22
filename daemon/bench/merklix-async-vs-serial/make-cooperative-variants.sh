#!/bin/sh
# Separate build products: never overwrite the completed A/B/C/D study binaries.
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
OUT=${OUT:-$HERE/build-e}
export OUT
"$HERE/make-variants.sh"
python3 - "$OUT" <<'PY'
import pathlib,sys
out=pathlib.Path(sys.argv[1]);s=(out/'commitment_D.cpp').read_text()
s=s.replace('#include "work_pool.h"','#include "cooperative_work_pool.h"')
s=s.replace('util::WorkPool::Shared()','util::CooperativeWorkPool::Shared()')
(out/'commitment_E.cpp').write_text(s)
PY
CXX=${CXX:-/usr/bin/c++}
CFLAGS="-std=c++20 -O3 -DNDEBUG -pthread -I$SRC/src -I$SRC/src/lotus_v2 -I$HERE"
$CXX $CFLAGS -DBENCH_COOPERATIVE_ENTRY -c "$HERE/bench.cpp" -o "$OUT/bench_E.o"
$CXX $CFLAGS -c "$OUT/commitment_E.cpp" -o "$OUT/commitment_E.o"
$CXX -O3 -pthread "$OUT/bench_E.o" "$OUT/commitment_E.o" "$OUT/tagged_hash.o" "$OUT/libblake3.a" -o "$OUT/bench_E"
$CXX -std=c++20 -O3 -DNDEBUG -pthread -I"$HERE" "$HERE/mixed_pool_bench.cpp" -o "$OUT/mixed_pool_bench"
shasum -a 256 "$HERE/cooperative_work_pool.h" "$HERE/bench.cpp" "$HERE/mixed_pool_bench.cpp" "$OUT"/bench_[ACDE] "$OUT/mixed_pool_bench" > "$OUT/E-HASHES.txt"
