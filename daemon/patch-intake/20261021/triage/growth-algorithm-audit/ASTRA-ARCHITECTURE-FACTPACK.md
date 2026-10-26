# Reconciliation architecture: source facts for independent design review

Status: production implementation PAUSED for the user-requested Astra architecture and repeated source-grounded reviews. This is not a validated implementation proposal. Existing unbuilt candidates are preserved. Source facts below refer to tested 521-derived commit `2b61dded451755e175681f41a57281a5c0554e32`, tree `2b4fef46071b44cc8789a49553b3d112b4fd084e`, available in `/Users/shammah/repos/lotus-v2-repair-work/recon-fullscope-source` (which also has clearly unbuilt experimental commits).

## Failure requiring repair

`benchmark-results/20261021/native-network-batch500k-v1/REPORT.md` and missing-set diagnostics: origin accepted 500,000 timed native transactions in 44.93844s, plus 3,200 warmup. After 600s inventory was 503200 / 499882 / 502279; missing sets 3318 / 921, intersection one. None of those missing IDs was in origin's lowest 4096 IDs. Unbroadcast counters were zero. This is a local high-bandwidth/whitelisted relay result, not a WAN/default-relay claim.

## Three different existing stores: do not conflate them

1. `src/lotus_v2/mempool_overlay.h:30`: UTXO `SmtNode` has `array<shared_ptr<const SmtNode>,2> child`. Immutable subtrees have reference ownership.
2. `src/node/snapshot.h:132`: `MempoolSnapshotTree` is the published entry radix tree, with intrusive refcount/RCU. It retains immutable transaction references. Its numeric high-bit radix ordering and metadata are not the consensus canonical transaction commitment.
3. `src/lotus_v2/mempool_overlay.h:76-134`: canonical `TxOverlayArena` stores `TxOverlayNode.left/right` uint32 indices into `mutable vector<TxOverlayNode> nodes_`. Mutation path-copies nodes within the same arena; independent arena copy copies the whole vector. `EnsureDigest` mutates dirty digest fields. Thus its current value-copy is neither O(1) generation pinning nor safe concurrent lazy hash versus mutable arena update. This is the specific representation gap to repair, rather than introducing a second independently maintained whole-mempool authority.

Canonical transaction leaves commit both TxId and TxHash. Route is byte0 bit0 first (`TxKeyBit` in `src/lotus_v2/commitment.cpp`), unlike published numeric radix ordering AND unlike existing wire byte0 high-nibble-first `GetMerklixNibble` (`src/net/v2_protocol_handler.h:272`). Multi-key unary paths are tagged/hashed at each depth; singleton is directly a leaf. Any replacement must preserve canonical root bytes exactly, including deletion collapse and unary paths.

## Existing overlay update / epoch lifecycle and consumers

`CTxMemPool::FlushPendingOverlayAdds` (`src/txmempool.cpp:499`) under pool.cs applies deferred adds/removes to `GetSpeculativeOverlay`; removal-heavy path can rebuild current live set, explicitly preserving frozen consensus epochs. Overlay stores all non-coinbase live pool transactions, with full transaction references; it is not inherently just a mining-selected subset.

`MerklixOverlayManager::FreezeEpochBatch` (`src/lotus_v2/mempool_overlay.cpp:2589`) eagerly obtains transaction and UTXO roots, pushes a value-copy of `speculative_layer_` into `frozen_epochs_`, increments next_epoch_id_, and returns frozen layer. It DOES NOT clear/reset speculative transactions or begin an empty delta layer. Frozen layers are cumulative snapshots today, not disjoint recent-admission batches. `frozen_epochs_` is a vector without per-peer completion or retention budget. Reset/chain reanchor handles its contents separately.

`CTxMemPool::FreezeEpochBatch` (`src/txmempool.cpp:551`) flushes changes then freezes and publishes RPC snapshot. Production callers are Avalanche `Processor::tryFreezeAndRegisterNextEpochBatch` and finalization path (`src/avalanche/processor.cpp:1700-1840`). Those compare cumulative transaction counts and parent batch IDs; blindly resetting speculative layer would change finality/pipelining semantics. Sealed-header reconstruction also scans frozen and speculative layers (`src/net/v2_protocol_handler.cpp:524`), while miner/validation/RPC snapshots use speculative overlay roots. Current frozen epoch therefore must not be redefined solely for relay convenience.

User intent: each overlay is latest unreconciled epoch; clarify implementation design in that model, including how cumulative state and epoch-delta metadata relate. A single peer completing cannot globally declare an epoch reconciled. Admission/removal during a network round must path-copy the next generation while that round retains a fixed root/membership/key. No mempool lock held across network round.

## Current coverage failures / bounds

`NormalizeCtorTxList` (`src/net/v2_protocol_handler.cpp:36-55`) sorts/uniques and unconditionally truncates to 4096 BEFORE root and bucket summaries. `GetScopedTransactions` calls it in all fallback/provider paths (769,781). `BuildSyncSummary` and `BuildSubBucketSummary` materialize this scope repeatedly; subdivisions only support depths 8,12,16 today. Terminal overflow list is itself capped. Equal-count/extras suppression in relay-epoch diff can hide balanced missing sets; each subtree needs sufficient authenticated identity, not count-only progress.

`PeerManagerImpl::RelayReconSet` (`src/net_processing.cpp:3975`) chooses recent admissions within configured window (default 30s), excludes newest two polling intervals, pins candidate tree and joins published membership, then stops at lowest 4096 live IDs. `MaybeReconcile` (4031) round-robins negotiated peers, skips empty summaries, and prunes old window history. Age is not evidence of reconciliation; missing high IDs can age out permanently. Keeping this path as sole authoritative repair set is incorrect.

The fixed cap existed in original `92f36b6549643e68cfdff30cd08c5f48f12acc16` (tested history import `3a7173fde303d5ee47dc251dcdbcadd8a90537e2`), including a hardening test that asserts it. No source comment found establishing it as a temporary stub. Later recent-window commit `f2578bcba8d3ee35ecadeaf91bfed4f81b671de4` explicitly intended to keep differences small. Do not invent original cap rationale.

## Design requirements and unresolved choices

- Repair existing canonical overlay store with O(1) root pin/copy, immutable topology, shared unchanged nodes, independent lifetime and thread-safe lazy digest. Compact slab/refcount or equivalent is fine; literal shared_ptr on every node is not required.
- Initial hash O(number of structural nodes); explicit <=256 depth/unary bound. k updates touch changed paths, repeated root query zero hashes. No full-list sort/freeze per poll or O(M) admission work. Include counters and independent canonical-root oracle.
- Reuse existing persistent 16-worker overlay hash pool (`ParallelFor16Shards` in mempool_overlay.cpp). Existing dispatch serializes via dispatch mutex and is nonreentrant; only outer root dispatch or an explicit reentrancy guard. No per-node threads.
- Round context must bind immutable root/generation, epoch/key and query identity throughout summary/zoom/body resolution. Expired/evicted context must explicitly restart, never silently respond from mutable live membership or pretend empty.
- Retention needs per-peer progress, count/bytes/time bounds, churn/backpressure behavior, late-peer full-live fallback, and mined/reorg semantics. Retaining every historical root forever is unacceptable; dropping a transaction from live membership does not mean every frozen round may silently change.
- Preserve existing Merklix 16-way zoom + BCH GF(2^64) s1/s3/s5 intent. Per-message/peer work bounded without truncating declared scope. Deep prefixes up to full key may need explicit negotiated wire extension; old stock peers must never receive unknown private fields/commands.
- GF/SID aggregates depend on salt, scope, context, mask and epoch. Canonical root is key-independent, GF cache is not. Fixed public network salt was an unreviewed exploratory shortcut, NOT authorized final design; assess chosen-ID/DoS, keyed session caches and off-lock bounded work. Never simply XOR or share aggregates across incompatible keys.
- Exact-root equality can differ for same TxId/different TxHash (witness). Clarify reconciliation identity and witness-resolution behavior, not just ID count.

## Preserved source-only experiments (not approved / not compiled)

`/Users/shammah/repos/lotus-v2-full-mempool-view`: commits 67909cca63 / e6c838a5c3 / 6331926c5c contain generic persistent canonical trie, fixed-key derived GF/SID index, prefix APIs, optional hash counters and tests. Existing worker wrapper is 932f94e32b (duplicate child cherry 555c54b57a). These demonstrate mechanisms only; integrate by repairing existing authoritative overlay representation if architecture accepts them, not by maintaining competing full-pool state. My experimental worktree contains wrapper and first two engine commits, nothing wired into production.

`FULL-SCOPE-INTEGRATION-DESIGN.md` in this directory is explicitly superseded where it proposes parallel canonical authority or fixed public salts. MERKLIXPAGE prototype commit 41b38b14b0 is also superseded and preserved on archive/superseded-recon-range-prototype-20261021; do not integrate it as stopgap.

Independent narrow initial-relay request-state repair is owned by `/root/private_relay_capability_repair`; it reuses authoritative InvRequestTracker for initial epoch short IDs, leaves generic scope pending API bounded. It does not solve permanent Merklix scope coverage by itself.

Required review/tests: >4096 high-ID loss older than 30s; balanced differences; dense shared prefixes; forced SID collisions; retained round through add/remove/readd/mining/reorg; max key/depth/empty; expired context restart; multiple peers and late joining; resource bounds and structural sharing; independent exact-root oracle; then N1 focused compilation and runtime-owner exact500K convergence.
