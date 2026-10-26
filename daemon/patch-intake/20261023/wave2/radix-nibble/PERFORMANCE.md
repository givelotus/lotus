# Numeric radix nibble candidate

Single-host microbenchmarks support the candidate. Shared source commit `510ab830b2` is independently validated; root integration/push remains pending. Baseline is equality tip `81fce9de8e2a44d2c3d81dd87fb874d3aed5f8c4`.

The corpus contains100000 deterministic random256-bit keys, seed20261023. Every workload has three alternating before/after pairs with at least5 active seconds per sample. Values below are medians in **ns/operation**; lower is better.

| Change | Workload | Before | After | Adoption status | Source report |
|---|---|---:|---:|---|---|
| Direct numeric-word nibble | Extraction, varying levels/runtime keys | 9.521 | 2.382 | Validated candidate; integration pending | [Raw summary](benchmark/SUMMARY.json) |
| Direct numeric-word nibble | Actual public radix get,50/50 hit/miss | 87.516 | 64.196 | Validated candidate; integration pending | [Raw summary](benchmark/SUMMARY.json) |
| Direct numeric-word nibble | Actual fresh-tree radix insert | 90.811 | 70.899 | Validated candidate; integration pending | [Raw summary](benchmark/SUMMARY.json) |

All individual pairs improve. Min–max sample ranges before/after are8.741–10.474 /2.345–2.564 for extraction,85.930–90.166 /64.164–67.670 for lookup, and85.867–98.827 /67.530–86.401 for insertion. Insertion has the widest spread; it remains a three-pair synthetic result, not a claim about every distribution or workload. No additional sizes, distributions or CoW timing were run.

The18 reported samples contain90.051 active seconds and145.686 loop-adjacent wall seconds. Entry preparation, fresh-tree destruction, validation and RCU reclamation are excluded from insertion active time; real node allocation/CAS/RCU insertion work stays inside. Wall timing includes loop-adjacent lifecycle costs but excludes corpus/setup construction. All checksums passed their expected values; per-operation checksum matches exactly within every before/after pair. Dataset SHA256 is `165121e33979ee68088a3d9ecad8ce8e681303012fb7347f02658a83e696f2cc`.

Compiler and linker settings match after normalizing respective build/output paths and the deliberate baseline-header override. Baseline links preserved equality-build libraries, candidate links candidate-build libraries; all library/binary hashes are retained. Runtime inputs plus compiler barriers prevent extraction folding. Existing optimized assembly retains full-width shift calls in baseline timed functions and uses numeric uint32 loads/shifts/masks with no such calls in candidate timed functions.

See [validation receipt](BENCHMARK-VALIDATION.json), [raw samples](benchmark/RAW-RESULTS.json), [build identities](benchmark/BUILD.json), [matching settings](benchmark/SETTINGS-COMPARISON.json), [harness](benchmark/radix_nibble_bench.cpp), and [pair runner](benchmark/run-pairs.py). Compiler/tests completed before timing; root reserved the host exclusively. Smoke outputs are preserved separately and excluded from these figures.

These are extraction/radix microbenchmarks. They establish no daemon admission TPS, all-peer convergence, combined speedup, other-platform performance or published-release result.
