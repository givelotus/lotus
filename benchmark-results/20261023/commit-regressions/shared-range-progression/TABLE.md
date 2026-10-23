# ABC-anchored commit progression

Study status: complete_with_failures. Rates are RPC acceptance/read measurements. Each populated cell is a median; sample counts and ranges are in SUMMARY.csv. Failed samples contribute no rate.

Points identify the frozen shared ABC/eCash Git stack through378. This is not the native V2 endpoint.

| Point | Commit | Individual tx/s | Arrays50 tx/s | Loaded tx/s | Concurrent reads RPC/s |
|---:|---|---:|---:|---:|---:|
| 0[^p0] | 1fb7db17c1 | 13,176 | 15,005 | 5,267 | 8,241 |
| 3[^p3] | a49f42c8e8 | 13,441 | 13,801 | 5,473 | 8,483 |
| 14[^p14] | e2b8bf4fb5 | 12,847 | 16,968 | 5,531 | 8,519 |
| 24[^p24] | ccb612cd05 | 13,352 | 15,329 | 5,347 | 8,438 |
| 31[^p31] | ef6f32cd1c | 12,448 | 14,976 | 5,132 | 8,532 |
| 44[^p44] | 596492b6b3 | 11,724 | 15,598 | 5,282 | 8,798 |
| 78[^p78] | 439e420c91 | 13,338 | FAIL | 5,533 | 8,873 |
| 94[^p94] | 1ebbab52a8 | FAIL | FAIL | 5,084 | 8,121 |
| 378[^p378] | d38c382061 | 12,164 | 24,129 | 5,281 | 8,266 |

Individual-owner attribution is pending for coarse intervals. A positive interval can conceal a regression inside it.

[^p0]: Unmodified Bitcoin ABC 1fb7db17; no optimization commits.
[^p3]: 1–3: linked-worktree metadata, Currency-mode caching and O(1) unbroadcast count.
[^p14]: 4–14: salted-hasher seeding, word hash comparison, UTXO reserve/admission fast paths and optional full-pool diagnostics.
[^p24]: 15–24: MDBX and persistent Merklix arenas, cut-through storage, lazy UTXO SMT, geometric growth and mempool overlay wiring.
[^p31]: 25–31: Merklix reconciliation/epoch machinery, cached quorum metrics and combined snapshot publication/read consumers.
[^p44]: 32–44: package RPCs, state sync, signature-cache and batch verification work, fee controller, staged validation and snapshot coalescing.
[^p78]: 45–78: mining/storage changes, adaptive fee policy, deferred overlay work, witness/input handling, persistent executor, slabs and contiguous transactions.
[^p94]: 79–94: parsing/storage and ARM SHA256, Beast HTTP including repaired body buffer, template APIs, CoW slabs/radix and fee worker. jemalloc remains OFF in this matched profile.
[^p378]: 95–378: remaining networking, metrics, native Chronik and logging work, bounded RPC commit owner and persistent-tree reuse. Chronik and extra transports remain OFF.

Failed samples (not throughput results):

- Point 94, round 1, single_tx_steady: N/A; no throughput credited. Evidence: /Users/shammah/repos/lotus-v2-optimizations/benchmark-results/20261023/commit-regressions/shared-range-progression/round-1/point-094/single_tx_steady
- Point 94, round 2, json_rpc_batch50_steady: N/A; no throughput credited. Evidence: /Users/shammah/repos/lotus-v2-optimizations/benchmark-results/20261023/commit-regressions/shared-range-progression/round-2/point-094/json_rpc_batch50_steady
- Point 78, round 2, json_rpc_batch50_steady: N/A; no throughput credited. Evidence: /Users/shammah/repos/lotus-v2-optimizations/benchmark-results/20261023/commit-regressions/shared-range-progression/round-2/point-078/json_rpc_batch50_steady
- Point 78, round 3, json_rpc_batch50_steady: N/A; no throughput credited. Evidence: /Users/shammah/repos/lotus-v2-optimizations/benchmark-results/20261023/commit-regressions/shared-range-progression/round-3/point-078/json_rpc_batch50_steady
- Point 94, round 3, json_rpc_batch50_steady: N/A; no throughput credited. Evidence: /Users/shammah/repos/lotus-v2-optimizations/benchmark-results/20261023/commit-regressions/shared-range-progression/round-3/point-094/json_rpc_batch50_steady
