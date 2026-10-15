# V2 coverage measurement

This is development-candidate evidence, not mainnet approval. Native source pin is
`f1c8c92d87023c620819dfc4a6bd88a28c446d46`; compiler/reference source pin is
`48a47753500a968a7f28590deda9f6c0575ccf7d`. All work used separate clones/worktrees,
with no production node, peer, chain data, or release changes.

## First measured results

| Scope | Tests | Lines/statements | Branches | Functions |
|---|---:|---:|---:|---:|
| Python reference, every package module | 95 passed | 2640/3212 (82.19%) | 1059/1508 (70.23%) | not supplied by coverage.py |
| Compiler emitted JavaScript, all `dist/**/*.js` | 159 passed | 5520/5927 (93.13%) | 2628/3258 (80.66%) | 353/364 (96.98%) |
| Native mapped V2 + wallet C++ (execution coverage; 5 failures) | 31 passed, 5 failed | 14996/20381 (73.58%) | 7521/13440 (55.96%) | 1284/1508 (85.15%) |
| Rust core V2 production module | 4 passed | 134/136 (98.53%) | not emitted | 12/12 (100%) |

Python's combined statement/branch percentage is 78.37%; it must not be mistaken
for its line percentage. No Python lines are excluded. Node reported 93.76% lines / 83.83% branches / 96.79% functions; Node and c8 use different
coverage models, and the table uses c8 LCOV counters; consult `compiler-js.json` and `compiler-js.lcov` for c8's exact
denominators. TypeScript builds without source maps, so emitted JavaScript coverage
is not exact TypeScript source-line coverage. All emitted modules are included,
including unused CLI modules. These are distinct language measurements; no combined
percentage is meaningful.

JSON and LCOV are in `evidence/v2-coverage/`; HTML archives extract to an ordinary
browser-readable index. Test logs record skips and unavailable optional native
compiler stages. Reference/compiler coverage was gathered from passing test runs; earlier dependency
failures were corrected by installing requirements, without changing test expectations.

## Reproduction

Use Python 3.13 in a fresh virtualenv with `coverage==7.16.2`,
`tools/lotus-v2-reference/requirements-vm.txt`, and `jsonschema`. From the reference
directory, set `COVERAGE_PYTHON` and a fresh absolute `COVERAGE_OUTPUT`, and run
`../lotus-v2-coverage/reference.sh`. From the compiler directory after `npm ci`,
set `LOTUS_V2_PYTHON` to that Python, prepend its directory to PATH, set a fresh
`COVERAGE_OUTPUT`, and run `../lotus-v2-coverage/compiler.sh`.
Node was v26.10.0; TypeScript is lockfile 5.9.3, c8 is pinned to 10.1.3.

Configure native in a real clone (the full build reads `.git`):

```sh
cmake -S "$NATIVE" -B "$NATIVE/build-coverage" -G Ninja \
  -DCMAKE_BUILD_TYPE=Debug -DUSE_LINKER= \
  -DCMAKE_C_COMPILER=/opt/homebrew/opt/llvm/bin/clang \
  -DCMAKE_CXX_COMPILER=/opt/homebrew/opt/llvm/bin/clang++ \
  '-DCMAKE_C_FLAGS=-fprofile-instr-generate -fcoverage-mapping' \
  '-DCMAKE_CXX_FLAGS=-include algorithm -include atomic -include vector -include array -include string -include memory -include functional -include map -include set -include limits -fprofile-instr-generate -fcoverage-mapping' \
  -DBUILD_CHRONIK=OFF -DBUILD_BITCOIN_QT=OFF -DENABLE_MAN=OFF \
  -DPython_EXECUTABLE=/opt/homebrew/bin/python3.13
python3 tools/lotus-v2-coverage/native.py "$NATIVE" "$FRESH_OUTPUT"
python3 tools/lotus-v2-coverage/diff.py "$NATIVE" "$FRESH_OUTPUT/native.json" \
  --baseline f5cd728ab > "$FRESH_OUTPUT/changed-lines.json"
```

Compiler, llvm-profdata and llvm-cov are matching Homebrew LLVM 23.1.2.
The forced standard-library includes compensate for inherited sources relying
on transitive includes (`crypto/sha256.cpp`, `init.h`, `node/ui_interface.h`) with this libc++ version;
no production source is edited. This is a coverage-build compatibility condition.
`USE_LINKER=` selects the system linker because this installation's lld does not
link the project. Build concurrency is capped at two.

The native driver enumerates every focused target declared by `src/lotus_v2`,
records each exit status, requires a per-test `%p` profile, rejects existing raw
profiles, merges all profiles and exports JSON, LCOV and HTML with branches,
expansions and instantiations. Tests and vendored BLAKE3 are excluded from the
production V2 denominator. Every production `.cpp`/`.h` is explicitly inventoried;
files with no emitted mapping are listed as **unmeasured**, never silently treated
as covered. Header/template instantiations and macro expansions can produce
multiple regions; LLVM branch totals are not a count of unique source decisions.

The diff report uses maintained baseline `f5cd728ab`, intersects added source
lines with LLVM counted segments, and separately lists every unmapped added line.
Unmapped lines include both non-executable text and uninstrumented files, so they
must be inspected before computing a changed-line percentage. Inherited unchanged
code is outside this changed-line denominator; native V2 modules also have their
own inventory because they are entirely new relative to ABC `1fb7db17`.

## Gaps and path coverage

Full execution-path coverage is unmeasured and cannot be inferred from branch
coverage: loops, VM programs, network input, and state sequences admit unbounded
paths. LLVM 23's MC/DC compiler flag was tested on a tiny separate probe; its
machine-readable report is `mcdc-tool-probe.json`. This demonstrates toolchain
support only. Production was **not** compiled with MC/DC in this first run, and
MC/DC is not full path coverage.

The native instrumented run failed five tests: reorg recovery (`zero genesis work anchor`),
peer transport (action/read/write count assertion), peer dispatcher (`zero genesis work anchor`),
block preview (monetary tail/time context), and block assembler (genesis anchor mismatch).
Their profiles are retained in the aggregate and exact logs are supplied. The measurement
is execution evidence and **does not validate the native build**. The driver exports
all results and exits unsuccessfully when any test fails. No fixture or consensus code
was modified.

LLVM reports 648 missing profile records with CFG hash zero (see
`native-profile-mapping-warnings.log`); all warnings were inspected, and none has
a nonzero CFG hash. These are functions without an emitted matching counter record,
including unused inline functions; the warnings are retained rather than suppressed.
The mapped totals exclude 42 inventoried files without mappings, including headers
without executable regions and seven `.cpp` files. Native commands, Chronik sync,
block/transaction seal helpers, Avalanche chain adapter and wallet client need separate
coverage. The gap report has exact source branches and summaries. Largest measured
branch gaps include VM (916), peer dispatcher (492), disk state (321), wallet payment
(294), and wallet node provider (256). Wallet objects were included explicitly, so
unexecuted wallet code contributes zero coverage rather than disappearing.

Native focused tests exercise bounded reorg/recovery, disk/state storage, transaction
rejection, relay and peer state scenarios. The scenario inventory records exact bounded test entrypoint calls; a complete
state-transition matrix still needs mapping to each case and failure condition. Fault injection for short writes, fsync/rename errors,
restart at each journal phase, and VM rejection at each validation boundary should
be prioritized against uncovered code rather than adding tests to raise a number.

Wallet v2 object mappings are included, but wallet unit/integration execution and
complete daemon command/RPC paths and real-node integration profiles are **not measured**.
Rust core V2 encoding/validation is measured separately with Rust1.93.0 and its matching
LLVM21.1.8 tools (`rust-core.sh`); source lines before inline cfg(test) at line299 give
134/136 production lines. Raw Rust exports also include inline test lines; the summary
filters those explicitly. Stable Rust emits no branch mapping here, so its zero branch
denominator means unavailable. Chronik Rust server/indexer/database modules remain unmeasured. Chronik is OFF for the native coverage build. Existing passing integration
and Rust checks are separate evidence and supply no coverage percentages. Coverage
of compiler optional native fixtures is also not implied by Python execution.
There is no arbitrary 100% gate and no defensive/error-path exclusion.

The reference gap inventory (`reference-gaps.json`) shows the largest measured gaps
in VM (167 missing branches), block validation (64), signing (49), cost accounting
(49), and VM context (27). These are actual uncovered branch counters, not claims
that every gap is an untested security condition.

Native and Rust raw JSON reports are gzip-compressed; decompress before feeding them
to JSON tooling. HTML archives contain the actual per-source reports, including unexecuted
lines. `--export-existing` regenerates native exports from the recorded complete profile
inventory without rerunning tests; it refuses changed target inventories or missing profiles.

The maintained-baseline diff has 531 covered of 637 mapped added lines (83.36%),
with 2383 added lines explicitly unmapped across 34 changed files. This conditional
percentage omits unmapped code and is not overall new-code coverage.
`new-modules-since-abc.json` separately inventories every added V2/wallet module line
since ABC `1fb7db17`; its unmapped lines include test files and non-executable text.
