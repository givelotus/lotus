# Native signed-batch profile: next measured limit

Baseline compiled3cfb7031/treea576cd04, same tracked tree as frozen native review and consolidated native endpoint. Binary and tool identities: benchmark-results/20261023/native-batch-profile-baseline/INPUTS.json. Real native BIP340 transactions; 800K presigned distinct fixtures, eight submitters, three nodes sharing this host. The five-second ingestion was sampled at1ms for four seconds; instrumented TPS is intentionally excluded from timing tables. Exact source inventory and clean node exits passed.

The message-handler thread has2,940 wall-stack samples:1,468 (49.93%) are relay topological comparisons,33 (1.12%) other relay heap work,959 (32.62%) mutex waits, with the rest other work. These are blocked-inclusive thread samples, not CPU-time shares. Across16 RPC executor threads:24,184 condition-wait samples,21,254 mutex-wait samples,1,412 other-execution samples and190 curve samples. Signature workers perform real Schnorr batch verification. Aggregate wait counts include idle workers and must not be interpreted as time spent consuming CPU.

## First bounded repair

Candidate4278a1fb resolves each inventory candidate's mempool admission ID once under a coherent view and performs pure integer heap comparisons. Original code took the recursive mempool lock and hashed both IDs for every comparison. Existing entries precede stale IDs and admission order remains topological; rate limits, peer known filtering, negotiated push capability and validation remain unchanged. The relay reference vector reserves only the tick budget, rather than the entire backlog. The native relay test now checks exact announcement order, in addition to16 announcements/pushes and known-ID exclusion.

This is a new measured optimization candidate, separate from the tree-preserving HTTP history fold. It does not claim to reach100K TPS. Matched native before/after timing is required before adoption.

## Remaining algorithmic issue

Both original and rank-cached variants still scan and heapify the whole unsent peer backlog at each bounded relay tick. For a fixed backlogN drained in chunksB with no new arrivals, repeated rebuilding alone sums to O(N²/B), plus pop operations. A fixed-rate capped queue under sustained arrivals can keep scanning an ever-growing backlog. The profile establishes cost and contention in this workload; a single five-second run does not establish an empirical quadratic scaling curve.

A following design should retain per-peer admission order across ticks with O(logN) enqueue/remove and bounded drain work, while handling mempool removal/re-admission, parent routes, known-inventory filtering, peer teardown and reorgs. Ranking must be captured from validated mempool state with a consistent lock order, not invented from a peer-provided ID. Late/stale entries require explicit handling. Benchmark backlog growth and all-peer completion separately from RPC acceptance; do not raise the rate limit or drop unsent inventory to disguise the problem.
