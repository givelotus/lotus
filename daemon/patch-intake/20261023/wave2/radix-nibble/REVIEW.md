# Isolated radix nibble extraction review

Read-only review against shared equality commit `81fce9de8e2a44d2c3d81dd87fb874d3aed5f8c4`. Source remains clean. No source edits, compilation, tests or timing runs were performed for this review. Generalized map storage and publication remain separate work.

The current compiler does **not** reduce the existing radix expression to one word load. An explicit numeric-word accessor is a plausible isolated candidate; measured benefit is still unproven.

## What the current code does

`RadixTree::RadixNode::get` in `src/radix.h` indexes children with `(key >> uint32_t(level * 4)) & 15`, traversing levels 63 down to 0 for a 256-bit key. `Uint256RadixKey::operator>>` creates a full-width result; its shift reaches the out-of-line `base_uint<256>::operator>>=` in `src/arith_uint256.cpp`. That implementation copies the integer, clears its destination words, and propagates shifted words. The subsequent mask and implicit `size_t` conversion retain only the lowest nibble.

`base_uint` stores protected `uint32_t pn[WIDTH]`, with `WIDTH = BITS / 32`. Array index zero is the least significant **numeric word**: `GetLow64`, arithmetic operations and `UintToArith256` establish this contract. `UintToArith256` explicitly reads serialized bytes with `ReadLE32`; `ArithToUint256` uses `WriteLE32`. The object byte representation is not the accessor contract.

There is no existing public indexed word, bit or nibble accessor. `GetLow64` only exposes the first two words. `arith_uint256`, as a derived class, can legally read the protected numeric words directly.

## Existing compiler evidence

`REVIEW-EVIDENCE.json` records source hashes, compiler identity, exact existing probe binary hash and its original compile/link receipt. `existing-lookup-arm64.s` is disassembly extracted from the already-built current equality probe, which instantiates the actual project `RadixTree<Entry>` with `Uint256RadixKey` and uses the exact shared Release build flags.

With Apple Clang 21.0.0, arm64, `-O3`, no LTO, the actual lookup's internal-node loop contains:

```asm
ldp q0, q1, [x20]        // read all 32 key bytes
stp q0, q1, [sp]         // copy the full key into a temporary
mov x0, sp
mov x1, x21             // current shift: 252, 248, ...
bl __ZN9base_uintILj256EErSEj  // external operator>>=
ldr w8, [x0]
and x8, x8, #0xf
```

This proves the retained shift call for this compiler/build. It is not a performance measurement or a claim about other compilers, architectures, LTO configurations, or an unbuilt candidate.

## Smallest proposed implementation

Use three narrow header changes, with tests and a separate benchmark artifact:

1. Add an inline numeric `GetNibble(unsigned index)` accessor to **`arith_uint256`**, rather than exposing generic `base_uint` storage or adding a dependency from arithmetic to the radix key. For valid indices 0..63, return `(pn[index / 8] >> (4 * (index % 8))) & 0x0fU` as `uint32_t`. A simple `index >= 64` return-zero guard gives defined out-of-range behavior without an out-of-bounds access. Valid radix indices never take that branch. Do not claim equivalence to overflowed `level * 4` expressions outside the valid range.
2. Add `Uint256RadixKey::GetNibble(unsigned index)` forwarding to `base.GetNibble(index)`. Preserve its full-width `>>`, `&`, equality and indexing conversion contracts; existing key-wrapper tests exercise those independently.
3. In the existing radix child-index helper, use an `if constexpr (requires { key.GetNibble(level); })` branch to select the explicit accessor. Keep the existing shift-and-mask fallback for integer/custom keys. `BITS` remains four and child count remains sixteen. No node layout, allocation, reference counting, equality, lock or snapshot changes.

This is portable O(1) numeric extraction: one selected `uint32_t` word, an unsigned shift in 0..28, and a four-bit mask. It needs no reinterpret cast, byte punning, object-endian assumption, unaligned access, or narrowing of a 256-bit value through a 64-bit integer or host `size_t`. The result is already 0..15 before child-array indexing. Keeping the range guard's branch versus a documented/asserted precondition is an implementation choice to measure with the normal project flags; this review does not assume assertions disappear in Release.

Avoid optimizing `operator>>` itself to return just low bits: callers and current tests require the complete shifted 256-bit value. Avoid serializing the whole key to bytes on each lookup, which preserves semantics but reintroduces copying. Avoid widening `RadixTree` into a new map API for this change.

## Correctness gates

- Compare the accessor against the existing shift/mask oracle for **all 64 valid levels** over zero, all ones, every one-hot bit 0..255, alternating patterns, asymmetric per-word values, and runtime-generated full-width keys.
- Explicitly test nibble levels 0, 7/8, 15/16, 23/24, 31/32, 39/40, 47/48, 55/56 and 63; also check level 64 returns zero if that accessor contract is adopted.
- Retain the equality repair and its same-low64/different-high-bit regressions unchanged. Check actual tree insert, exact hits, path-sharing misses, duplicate insert, removal and immutable snapshots with keys differing in every relevant high/low position.
- Run the same targeted shared suites as equality: radix, snapshot RCU, relay, mempool and block encodings; compile daemon/CLI/tests with the same Release/Chronik-OFF flags, `-j10`, and zero new diagnostics. Include existing integer and adapter radix tests to verify the fallback.
- Inspect the newly built lookup assembly: the specialized path should have the numeric word load/shift/mask and no full-width shift call. The generic fallback and full-width wrapper shift remain valid. Compile coverage on a 32-bit or big-endian target is useful supplemental evidence if available; this host cannot supply runtime results for them.

## Paired measurement plan

Baseline is **the equality tip above**, not the buggy pre-equality tree. Candidate differs only in extraction. Use immutable source/binary/compiler/config hashes and identical flags. Root schedules an exclusive host slot; no build, indexer, profiler or competing benchmark may overlap measurements.

Generate deterministic, runtime-seeded corpora outside timing and record the seed/dataset hash. Use 4,096 and 65,536 entries with three distributions: uniform full-width keys; identical low64 with varied high words; and a long common high prefix with varied low words. Record insertion/query order. For misses, use absent full-width keys deliberately sharing existing paths. Validate uniqueness and expected hit/insert counts outside timing.

Measure these distinct workloads; do not combine their rates:

- **Extraction:** feed runtime-loaded keys and varying levels through each implementation. Rotate a runtime cursor through a shuffled `(key, level)` schedule. Accumulate returned nibbles into a checksum consumed using the repository's `ankerl::nanobench::doNotOptimizeAway`. Make both inputs observable to the optimization barrier as needed. Validate equal checksums, and inspect assembly so constant inputs, invariant hoisting or dead-code elimination cannot silently remove extraction. Do not mark key memory volatile merely to force loads and then attribute that extra cost to production extraction.
- **Actual public radix lookup:** build the real `RadixTree` once outside timing; replay the same shuffled hit and path-sharing miss queries through `get`, consuming returned pointers/checksums. Keep per-call RCU/refcount costs because production `get` includes them. An additional pinned-read-section `getWithinReadSection` result may isolate traversal, but must be labeled separately rather than substituted for the public call.
- **Actual radix insertion:** precreate immutable entry objects outside timing; insert the same ordered distinct keys into a fresh actual tree per sample. Time the insertion loop including its real node allocations/CAS/RCU costs. Verify all insertions succeeded and final lookups match. Reclaim/destroy the prior tree and synchronize RCU outside timing before the next sample. Avoid repeated insertions into an already populated tree, which would measure duplicate rejection instead.

Warm both binaries before sampling, then run at least **three alternating before/after pairs** (`A B A B A B`) for each labeled workload/dataset with identical iteration counts and warmup policy. Preserve raw per-run latency/rate/checksum, medians, spread and pairing order. No profiled rate is an adoption result. Report a compact table with change, workload, before, after, adoption status and source report; do not infer node admission TPS or peer convergence from these microbenchmarks. If extraction improves but public lookup/insert does not materially improve, report that result and avoid claiming a system speedup.
