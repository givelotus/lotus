#!/bin/sh
set -eu
# Run from the native clone; this measures core only, not linked Chronik server.
: "${COVERAGE_OUTPUT:?Set fresh absolute output directory}"
mkdir -p "$COVERAGE_OUTPUT/profiles"
export CARGO_TARGET_DIR="$COVERAGE_OUTPUT/target"
export LLVM_PROFILE_FILE="$COVERAGE_OUTPUT/profiles/core-%p-%m.profraw"
export RUSTFLAGS='-C instrument-coverage'
cargo +1.93.0 test --locked -j2 -p bitcoinsuite-core lotus_v2 -- --nocapture
RUST_SYSROOT=$(rustc +1.93.0 --print sysroot)
LLVM_TOOLS="$RUST_SYSROOT/lib/rustlib/aarch64-apple-darwin/bin"
"$LLVM_TOOLS/llvm-profdata" merge -sparse "$COVERAGE_OUTPUT"/profiles/*.profraw -o "$COVERAGE_OUTPUT/core.profdata"
# Cargo builds a single matching package unit-test executable.
find "$CARGO_TARGET_DIR/debug/deps" -type f -name 'bitcoinsuite_core-*' -perm -111 > "$COVERAGE_OUTPUT/objects.txt"
# Export step is deliberately Python to preserve filenames as arguments.
python3 - "$COVERAGE_OUTPUT" "$LLVM_TOOLS" "$PWD/chronik/bitcoinsuite-core/src/lotus_v2.rs" <<'PY'
import pathlib,subprocess,sys
out,llvm,src=map(pathlib.Path,sys.argv[1:]);objects=out.joinpath('objects.txt').read_text().splitlines()
if len(objects)!=1:raise SystemExit(f'Expected one test binary, found {len(objects)}; inspect objects.txt')
args=[objects[0],'-instr-profile='+str(out/'core.profdata'),str(src)]
for fmt,name in [('text','core.json'),('lcov','core.lcov')]:
 with (out/name).open('w') as f:subprocess.run([str(llvm/'llvm-cov'),'export','-format='+fmt,*args],stdout=f,check=True)
subprocess.run([str(llvm/'llvm-cov'),'show',*args,'-format=html','-output-dir='+str(out/'html'),'-show-branches=count'],check=True)
PY
