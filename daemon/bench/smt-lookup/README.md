# Immutable SMT lookup comparison

Compiled/linked and functionality-smoked on macOS arm64; **controlled paired measurements have not run**. This compares actual production `SmtFind` implementations linked from independently frozen native archives. It does not copy/reimplement the lookup algorithm in the driver. The same driver source/object, compiler options, input tree and query sequence must be used for both variants. `run-pairs.py` rejects differing driver objects or tree roots and any lookup error.

`lookup.cpp` constructs 65,536 deterministic coins before timing, validates/warms the query set, then measures hit and absent-outpoint lookups using 1 or 4 reader threads. Threads each own a snapshot; creation, tree construction and warmup are outside the measured interval. Timed operations include the real SmtFind key hashing, root pin, traversal and returned Coin ownership. There are no writes or new input allocations during timing. Checksums and per-result validation prevent unused results from disappearing. Timer reads are amortized over 256 operations.

The result unit is **validated SMT lookups/second**, never transaction admission, network convergence, block throughput or finality TPS. A five-second duration is required per process. The default matrix has three alternating pairs per case, rotating case order, with all raw trials retained. Median before/after values and per-pair ratios are reported without combining unrelated cases.

Root must grant each build/timing window. `build.py --approve-compilation` and `run-pairs.py --approve-timing` acquire the shared host lock. These flags do not themselves constitute a host grant. The timing runner also rejects visible build processes and verifies frozen binaries, driver identity and external library identities. Root separately controls other indexer/benchmark work. Partial attempts retain STATE.json but are not publishable as a complete comparison.

Existing C11 preservation receipt:
`daemon/patch-intake/20261023/atomic-performance-series/smt-borrowed-traversal/C11-BASELINE-PRESERVATION.json`.
The original C11 binaries/cache plus 32 project archive/shared-library/object artifacts were copied and hash-verified into
`~/repos/archive/builds/lotus-bench/smt-borrowed-traversal/c11-baseline` before any builder reuse. This baseline is native item11 on its original C4 prefix; it does not contain the separate C5 pool consolidation.

Reproduce after root grants the relevant windows (paths below are relative to the canonical task home):

```bash
# After candidate correctness gates: freeze its actual build products before any further reuse.
python3 daemon/bench/smt-lookup/freeze.py \
  --build ~/repos/archive/builds/lotus-bench/atomic-native-verdict-reuse-build \
  --output ~/repos/archive/builds/lotus-bench/smt-borrowed-traversal/candidate \
  --source-commit <candidate-commit-or-exact-base> --source-tree <exact-tested-tree> \
  --gate-receipt <candidate-receipt-with-binary-hashes>

# Link each variant from its own frozen archives and rpath.
python3 daemon/bench/smt-lookup/build.py \
  --frozen ~/repos/archive/builds/lotus-bench/smt-borrowed-traversal/c11-baseline \
  --output ~/repos/archive/builds/lotus-bench/smt-borrowed-traversal/micro-before \
  --approve-compilation
python3 daemon/bench/smt-lookup/build.py \
  --frozen ~/repos/archive/builds/lotus-bench/smt-borrowed-traversal/candidate \
  --output ~/repos/archive/builds/lotus-bench/smt-borrowed-traversal/micro-after \
  --approve-compilation

python3 daemon/bench/smt-lookup/run-pairs.py \
  --before ~/repos/archive/builds/lotus-bench/smt-borrowed-traversal/micro-before/lookup \
  --after ~/repos/archive/builds/lotus-bench/smt-borrowed-traversal/micro-after/lookup \
  --output benchmark-results/20261023/smt-borrowed-lookup-pairs \
  --approve-timing
```

`build.py --plan-only` writes the exact proposed compiler/linker command without launching a compiler. The initial baseline command plan is preserved under the canonical SMT intake as `micro-plan-before/`. The link recipe derives from the real Ninja unit-test link command, replaces the test object list with the standalone driver, and preserves all production library dependencies. The standalone recipe compiled/linked both frozen variants and passed eight one-second, 128-coin functionality smokes on macOS arm64; see the canonical SMT intake MICRO-SMOKE.json. Those trials are explicitly not a performance comparison. Other platforms remain unvalidated; preserve failed attempts and review driver-only linkage needs rather than modifying production code to satisfy the benchmark.

Copied original test binaries may reference their original build directory through rpath. Their full project dylib closure is preserved too; set DYLD_LIBRARY_PATH to the frozen `src` directory when replaying them. New micro binaries explicitly use the matching frozen variant rpath. Runtime/compiler/library hashes and exact source/gate receipts accompany each artifact. No source checkout, mailbox, pin or active module is changed by these tools.

Native daemon paired measurements remain a separate root-owned step after the microbenchmark. A microbenchmark improvement alone is not adoption evidence for native TPS.
