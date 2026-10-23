# Small, upstream-first source order — promoted

Current shared branch: `31540ff49727af2b928ffd3b9c514b28ee609342` (377 owners). Current Lotus branch: `761483a23b6914c3bd5c5654995293fe6e3b5338` (153 native owners). Total530, linear, no fixup commits remain. Whole tracked Lotus tree is exactly `f58bb4951d4431ab30f1b0363c7368f6969a5cb4`; shared endpoint remains exactly `cbc200b39c19ae38458e169bdd0d285b6691a650`.

| Position | Purpose |
|---|---|
|1|Existing linked-worktree CMake metadata fix, extracted from adaptive-policy owner|
|2|Currency option cache|
|3|Single random-context salted hash seeding|
|4|Portable numeric hash word comparison and separate equality|
|5|Stake commitment hash hoist|
|6|Coins hash-bucket reservation|
|7|Single-input duplicate and disabled-sequence fastpaths|
|8–10|Original small fixture repairs and ancestor API prerequisite|
|11|Optional topological checker and regtest-specific default policy, with all C++ assertions|

Each optimization remains a separate source commit. Comparator semantics remain full-width numeric ordering with portable endian/alignment handling; this is not a SIMD or daemon-TPS claim. Original standalone comparator evidence remains at `daemon/patch-intake/20261021/exports/hash-comparison-optimization/REPORT.md`.

Checker's exact functional file is now a companion of class-attribute framework owner180, where it can actually import/run. Its production, C++ tests and explicit functional invariant-check flag are early. No assertion or test file was dropped. Later SHORTTX flags and structured logging tests stay in their own causal owners. All production/test/build/config/docs signed source-line operations are accounted in FINAL-OWNER-MAPPING, with explicit transfers for the CMake hunk and functional file. Repeated identical context lines can change Git hunk alignment; these cases are recorded and their signed-line multisets match exactly. Whole endpoint trees independently match.

Validation: early7 daemon/core normal build passed448 actions. Initial configure refusal exposed the preexisting worktree metadata prerequisite and is preserved. After extracting its exact existing hunk, early11 daemon/core build passed339 actions in61.4s. Six relevant suites passed43 cases/2,454,499 assertions, including checker/default-policy, amount, comparator, coins, hasher and transaction-validation coverage. All530 source deltas and all530 actual archival mailbox payloads replayed to every expected intermediate tree. No benchmark rerun was needed or performed.

Native full1203/1203 evidence is reused explicitly from the identical complete f58 source tree, recorded in `../native-final1203-result.json`; this is not a freshly compiled native-binary claim. The final shared endpoint is identical to batch2's built/tested cbc200 source. Current build cache contains the early checker prefix; preserved early binaries/cache/config are listed in EARLY-CHECKER-ARTIFACTS.json.

The six-commit reorder used a deterministic normal Git rebase; checker moved through ordinary Git edits and a folded include-order fixup. Original529 history and refs remain in pre-order.bundle and refs/backups/upstream-priority-20261022. source-after-order.bundle preserves current both branches and requires the recorded ABC base. No force push, GC, production/datadir or release changes occurred. Root-owned dirty instructions/layout/recovery files were excluded.

Remaining work is explicit: the larger allocator/CoW/storage/admission groups and broad logging/P2P order still need dependency-aware placement. Pool native134 cannot move alone: its manager first exists native059. Full-reconciliation and persistent-tree mechanics need reviewed generic-engine/native-proof adapters. This checkpoint does not claim those interface splits or the whole migration complete. V1 remains a donor and optional maintenance target, not a modernization dependency.
