# Growth-dependent admission audit

Audited source: `aed364af278a26e71d34ecfa3569ea870e82ccfb`, tree `5caf8ba1cb66ca15e50c0c761bae744a779d5798`, byte-equivalent to the ALL5 benchmark source `2ec38f9dc7`. This audit ran **no compilers, nodes or benchmarks**. The source ledger records complexity, frequency, locks and next checks for 11 mechanisms.

## What the completed measurement establishes

The unsampled 64K pilot reports completion checkpoints through 60,000 transactions. The first 12,000 completed in 0.948 seconds (12,659 tx/s), compared with 3.406 seconds for 48,000–60,000 (3,523 tx/s). This is a real within-run slowdown in the observed run. It does **not** establish O(N²), identify which component caused it, or rule out memory/host pressure. The last 12K took about 3.6 times as long as the first 12K. Raw inputs, their SHA256, and every 4K interval are preserved in `64k-completion-curve.json`.

The existing one-second early profile shows snapshot clone/grace work, VM preparation, admission waits and reconciliation. It does not show the later slowdown directly. The 500K attempt is owned by the benchmark agent; attempt4 is preparing the workload and deep samples at 50K/250K/450K. No deep sample was available when this first report was written. Earlier 500K attempts admitted zero timed transactions, so no 500K result is claimed here.

## Prioritized findings

### 1. Every changed-entry snapshot copy performs a global writer grace period under the mempool lock

`CaptureMempoolEntriesLocked` (`src/node/snapshot.cpp:176`) clones `prev->entry_tree`. Generic `RadixTree(const RadixTree&)` (`src/radix.h:65`) shares the root then calls `RCULock::synchronize`. It must protect against a concurrent mutator that already entered an unshared source node. The published snapshot, however, has **no such mutator**: its mutable builder exists only locally during capture, then moves into `shared_ptr<const MempoolSnapshotTree>`. Published trees are never subsequently changed. The caller pins the previous snapshot while making the next clone.

Consequently an explicit immutable-source clone can safely share the root without waiting for generic mutable-source writers. This preserves normal CoW updates and all deferred node reclamation. It does **not** remove the generic concurrent-copy barrier or skip reader lifetime protection. Early profile evidence includes 55 overlapping inclusive frame ticks in `PublishMempoolSnapshot → CaptureMempoolEntriesLocked → RadixTree copy`; these are not CPU percentages or exact lock duration.

Prepared source commit **`e3b73ec3a2`** in `/Users/shammah/repos/lotus-v2-repair-work/growth-algorithm-source` adds this narrow constructor and uses it only at the published mempool tree copy. A lasting radix regression exercises independent clone mutations, immutable original preservation, and descendants surviving the original publication. `git diff --check` passes. **Not built or run; no performance claim.** Validation target: native `radix_tests` and snapshot/RCU/mempool suites, then the identical fixed-work admission comparison and deep-grace counters if necessary. Review must preserve the no-surviving-mutable-builder invariant.

The generic grace scan is O(T) in participating threads, plus reclaimable cleanup work and waits for readers. It is not by itself an O(N) mempool scan. Longer reader sections or cleanup backlogs can nevertheless amplify it as the process grows.

### 2. Reconciliation's 4,096 cap does not bound collection and sorting

`TxRelayIndex::AdmittedSince` scans the recent window under its index mutex. It also traverses the too-new tail before skipping it. `PeerManagerImpl::RelayReconSet` then resolves all eligible IDs under `mempool.cs`, before `NormalizeCtorTxList` sorts and truncates to 4,096. Therefore the periodic work is O(W) under the pool lock plus O(W log W) sorting, where W is the live time-window population. At a fixed arrival rate W grows during window fill and eventually plateaus; it is **not necessarily total mempool N**.

The scoped list is already normalized, yet `ComputeScopedMerklixRoot` normalizes it again, and `BuildTxSubtreeA` sorts identity pointers again. The latter two sorts are capped, so their overhead should not be confused with the unbounded initial collection. Root recursion also allocates left/right vectors by depth and can launch at most 15 asynchronous splits at depths below four; it is not unbounded one-thread-per-leaf creation.

Next controlled check: compare early/late depths with reconciliation work/cadence unchanged, recording collected-window size, selected size, lock hold duration, normalize duration and root duration. A diagnostic recon-OFF pair can attribute the path but is not a production fix. Prefer maintaining/caching a canonical window membership snapshot or selecting the exact smallest unique IDs with bounded storage before resolving references. Preserve the exact current min-ID cap semantics, epoch membership, re-admission/removal behavior, short-ID collisions and committed root. Never truncate by arrival order as an optimization.

### 3. Batch relay has an exact-size reserve that can become quadratic in queue backlog

`RelayTransactionBatch` calls `m_relay_queue.reserve(m_relay_queue.size() + txs.size())` on each enqueue under the queue mutex. If the consumer is delayed, repeated batches can reallocate and copy every preceding batch, giving O(Q² / b) aggregate entry copying until drain. `DrainRelayQueue` swaps the vector into a local batch, so the queue restarts without retaining its old capacity.

This affects dedicated batch submission. The ordinary individual relay used by the current JSON-RPC-array diagnostic uses normal `push_back`, with geometric growth. Therefore this is **not an explanation for the existing ordinary-array 64K curve**. Small fix candidate: preserve geometric growth for batch appends and optionally reuse drained capacity. Reproducer: intentionally hold the consumer, enqueue equal batches, compare allocations/copied entries and verify byte-identical FIFO/local flags; then measure the real dedicated batch path. No patch prepared for this item until source ownership is coordinated.

## Things that are not per-transaction whole-mempool copies

- Snapshot capture updates only changed IDs, at O(K·d), with 4-bit radix depth d bounded by 64 for a 256-bit key. Expected shallow random-key paths grow logarithmically. A full reset is an explicitly different path.
- Ring retention (1,024 snapshots) pins old versions, but shared subtrees prevent deleting a complete N-entry tree on every retirement. Destruction can cascade through retired changed nodes; cleanup runs under RCU unlock and publication can release references under `pool.cs` and its own mutex. Measure backlog and lifetime rather than labeling this O(N²) from destructor samples.
- `DynamicMemoryUsage` uses cached usage/container sizes/allocated arena counts. It does not iterate the transaction map per admission. Rebound size-class count is independent of mempool size.
- The unbroadcast count copy and dedicated batch full-set classification copy are repaired. Membership still costs O(log U) per changed entry, and scheduled rebroadcast intentionally copies its U-entry set. That scheduled retry is distinct from a per-transaction O(U) count.
- Expiry normally stops at the first nonexpired entry; the fresh benchmark has no old prefix. A large already-finalized expired prefix can be rescanned on repeated admissions, but this is a separate long-lived-pool case.
- Exact UTXO filter tables grow geometrically. Rehashing creates individual O(N) events, amortized O(1) inserts. Fixed-size Bloom negative tests can saturate and become less useful. Retain exact membership/collision checks, and correlate actual rehash events/false-positive rate with chunk stalls before attributing the scaling curve.
- Scalar RPC reads no longer materialize roots. Overlay admission appends pending deltas; explicit mining/root consumers flush them. Root construction visible on periodic reconciliation is a separate path from scalar read publication.

## Validation and continuation

`SOURCE-LEDGER.csv` is the source-backed checklist. The prepared immutable-copy source change is a distinct optimization, not proof an old hunk was lost. No consensus rules, hash result, wire behavior, canonical branch pointer or patch series was changed by this audit. Later 500K evidence must be appended with exact source/host/memory context; do not fit an asymptotic law from this single 64K curve.


## Actual 50K-depth profile received after the source pass

Raw sample: `/Users/shammah/repos/lotus-v2-benchmark-results/native-all5-size-scaling-v1/accepted500k-attempt4-swap4g/node0-depth-50000.sample.txt`. Source and SHA256 with selected frame lines are preserved in `50k-selected-frames.json`. This sample was collected in the running exact500K attempt; the overall run had not finished when this section was appended.

A concrete blocking chain is now visible:

1. The scheduler's `TransactionAddedToMempool` callback enters `TxRelayIndex::Add` and waits for the index mutex for **313 of its 779 wall-thread sample ticks** (sample lines53–59). This is not a CPU utilization ratio.
2. Simultaneously the message handler spends repeated substantial sampled intervals in `TxRelayIndex::AdmittedSince`, including current-membership hashing, allocating/populating the `seen` unordered set, and freeing it while the index mutex remains held. It then enters `RelayReconSet`'s all-window `mempool.get` loop and normalization. The exact frame lines/counts are in the selected-frames JSON; do not sum overlapping frames.
3. Ordinary RPC completion waits for the validation notification queue. The queue's blocked relay callback therefore turns background reconciliation's growing scans into a foreground RPC completion stall, beyond its direct competition for `mempool.cs`.

This validates the **active mechanism and contention chain** behind priority1 reconciliation. It still does not establish that all late-depth slowdown is from this mechanism; later250K/450K samples and controlled fixed-source comparisons remain necessary. The 50K sample also shows radix cleanup, but not a sufficient basis to call it the primary growth cause.

A safe repair must separate constructing the reconciliation candidate set from long index critical sections, avoid repeatedly normalizing known-canonical lists and avoid resolving unlimited refs only to truncate afterward. Simply capping the first4,096 arrival-ordered candidates would change the canonical selected set and is unacceptable. Dropping live-membership checks also changes removal/re-admission behavior. Maintain an indexed/cached view with explicit mutation invalidation, or demonstrate exact-equivalent bounded selection before changing the path.


## Attempt4 stopped on fee policy after210K completion checkpoints

The attempted500K run stopped with `rpc-fee-hysteresis-insufficient, required_fee_sats=1001` against the fixed1,000-sat fixture. Last fully completed checkpoint:210,000 requests at64.523seconds; partial failed arrays may have admitted additional transactions. This is **not** a completed500K benchmark, validation failure, or resource abort. Active50K sample remains valid diagnostic evidence.

The resulting observed curve is not a continuously accelerating quadratic decline: after about80K completions it mostly plateaus near2.4–3.1K tx/s through210K. Reconciliation's configured30-second recent window offers a source-backed explanation for a bounded moving-window cost that fills then stabilizes, but a controlled comparison is still required to establish attribution. Exact10K intervals and log SHA are in `attempt4-partial-210k-curve.json`.

Post-rejection diagnostic samples at `json_rpc_batch50_steady.diagnostics/node0.sample.txt` also show heavy periodic `AdmittedSince` / `RelayReconSet` activity near the larger pool, but writers have stopped: **do not label those as active-ingestion deep profiles**. There are no250K/450K active samples.
