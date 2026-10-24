# Performance waves: current checklist

Canonical home: `/Users/shammah/repos/lotus-v2-optimizations`.
Updated 2026-10-23. This is the consolidated checklist; original plans and detailed reviews remain preserved below.

**Status meanings:** `gated` means implemented with recorded passing build/correctness gates, not necessarily integrated or performance-adopted. `prototype` means source exists but is not yet validated. `reviewed` means design only. Source pins, production branches and releases have not been promoted by these experiments.

## Wave 1 — 12 original items

Seven items have implementations with passing correctness gates (1–6 and 11); item 7 is partially implemented; items 8, 9, 10 and 12 remain unimplemented. Integration, intermediate-commit closure and performance adoption are separate work.

| ID | Original item | Current state | Remaining / dependency |
|---|---|---|---|
| W1-1 | Repair private-relay capability ownership | Gated; shared/native owner repair candidate | All affected owner and full endpoint gates passed; preserve this repair through subsequent moves. [Ownership review](upstream-repair-consolidation/PRIVATE-RELAY-OWNERSHIP-REVIEW.md). |
| W1-2 | Persistent relay precomputation executor | Gated; in C4 review candidate | Shared and native correctness gates passed; keep cap/index/null semantics. [Plan](atomic-performance-series/PLAN-v1.json), C2 receipts. |
| W1-3 | Persistent parallel TransactionSubtreeA | Gated; in C4 review candidate | Exact roots/empty/singleton/duplicate behavior checked; common-executor adapter retained. [Delivery](atomic-performance-series/commit3/START-HERE.txt). |
| W1-4 | Consolidate script workers on common executor | Shared/native endpoint gated | Shared 1,029 and native 1,211 full cases passed. Intermediate native32 compile defects are being moved from their later repair owners; latest exact-tree candidate `962cc0f6` builds/links prefix32, which then fails the first genesis assertion. Print-only diagnostics confirm both Merkle and block hash mismatch; coupled earlier serialization prerequisites are being audited before relocation. [Endpoint results](atomic-performance-series/THROUGH4-RESULT.json), [owner repair](atomic-performance-series/C4-PREFIX-API-RESULT.json). |
| W1-5 | Consolidate native overlay/signing pools | Gated candidate `935d1fb3` | Build, 131 targeted cases, metrics ×30 and functional gates passed. Separate denomination fixture fixup retained. Combined C5+C11 candidate `26bed6b9` is pushed with independent tree/preservation proof; combined gate is running, performance adoption pending. [Delivery](atomic-performance-series/commit5/START-HERE.txt). |
| W1-6 | Parallel SHORTTX decoding/precomputation | Gated shared candidate `642ef621` | 39 targeted cases and relay functional passed. Shared/native integration and performance comparison pending; native scanner currently does extra first-pass parsing, so no speedup assumed. [Delivery](atomic-performance-series/commit6/START-HERE.txt). |
| W1-7 | Persistent ranked relay backlog; eliminate repeated full scans/heaps | Partial | 7a standalone indexed queue `523b2a6b` gated. 7b admission-suffix reader `9b257564` gated. Bounded PeekPrefix refinement `597ee467` passed queue/relay/handler gates. 7c production SendMessages integration passed corrective build, targeted units and INVSHORT/fanout functionals with zero new warnings; source commit/bundle delivery pending. First warning-bearing attempt preserved. Combined native integration and paired performance are pending. No reverse-subscription index is used. Preserve stale/re-admission ordering, bounded body retention and future committed-frontier dependency. [Review](atomic-performance-series/commit7/REVIEW.md), [foundation](atomic-performance-series/commit7/foundation/START-HERE.txt). |
| W1-8 | Sharded flat TxRelayIndex | Reviewed competing direction; unimplemented | Compare against W2-2 radix index; choose deliberately rather than layering competing authoritative indexes. Preserve collision and epoch/window semantics. |
| W1-9 | Batch INV/INVSHORT lock work and exact membership fast path | Planned; unimplemented | Membership overlaps W2-4. Keep false-positive hints separate from authoritative duplicate/request decisions; split index changes from lock-scope changes. |
| W1-10 | Prepare raw atomic batches outside global locks | Design reviewed; unimplemented | Shared coherent confirmed-coin provider is a prerequisite; package fee/error/atomicity semantics remain mandatory. [Preparation review](atomic-performance-series/snapshot-review/REVIEW.md), [coin provider](atomic-performance-series/snapshot-review/CONFIRMED-COIN-PROVIDER-REVIEW.md). |
| W1-11 | Reuse completed native VM/script verdicts | Gated candidate `2d64521c`; paired benchmark complete | 3 focused cases, 73 affected cases and native/staged-P2P functionals passed. Exact witness/Coins/context and completed record-free success required. C5 pool changes are not included in this isolated candidate. Observed medians +2.4% admission/+1.9% exact peer completion; modest result, not a major speedup. Receiving-peer staged admission is the target; raw producer batch path is unchanged. [Report](atomic-performance-series/commit11/BENCHMARK-REPORT.md), [Delivery](atomic-performance-series/commit11/START-HERE.txt). |
| W1-12 | Per-peer Asio strand processing | Design reviewed; unimplemented | Resolve global routing/queue consumer ownership, shared state, producer fencing and teardown lifetimes first. [Review](atomic-performance-series/snapshot-review/STRAND-REVIEW.md). |

## Wave 2 — all 11 original items retained

| ID | Original item | Current state | Remaining / dependency |
|---|---|---|---|
| W2-1 | Radix equality, nibble extraction, snapshots and generalized map | Split into logical subchanges | Full-width equality `81fce9de` gated (77 cases and actual-tree negative control). Portable nibble extraction `510ab830` gated: 91 cases and three alternating pairs per extraction/lookup/insertion microbench workload; no daemon TPS claim. Generalized RadixTreeMap, overwrite/prefix/lower-bound APIs, OutpointRadixKey and safe live snapshot API are not implemented. [Equality](wave2/radix-equality/START-HERE.txt), [nibble](wave2/radix-nibble/REVIEW.md). |
| W2-2 | Radix-based TxRelayIndex with pinned epoch descriptors | Reviewed; unimplemented | Requires safe map/publication lifecycle. Competes with W1-8. Atomic shared_ptr alone is not a lock-free proof. |
| W2-3 | Radix outpoint spend map replacing mapNextTx | Reviewed; unimplemented | Requires W2-1 foundation; retain duplicate/conflict semantics, prefix units and exact parent/child behavior. Blind overwrite must not replace input exclusivity. |
| W2-4 | Live mempool transaction tree and exact fast reads | Reviewed; unimplemented | Lifetime retention does not synchronize mutable entry metadata; membership, metadata, counts and clear/re-admission need defined publication. Overlaps W1-9. |
| W2-5 | Store binary dependency/spentby IDs in snapshots | Gated shared candidate `765c3623` | Build, 72 focused cases and package functional passed. Original identity `6428d422` preserved; metadata-only author correction has identical tree. Shared integration and native string-consumer adapters pending. [Delivery](wave2/binary-snapshot-ids/DELIVERY.json), [current identity](wave2/binary-snapshot-ids/ROOT-STATUS.json). |
| W2-6 | Atomic unbroadcast entry flags/count and compact log | Reviewed; unimplemented | Coordinate flag/count/log with membership/removal/re-admission. Preserve RPC freshness and snapshot semantics. Local-origin relay hint remains part of the scope. |
| W2-7 | Dirty-entry epoch stamp and flat change log | Reviewed; unimplemented | Must include deletion tombstones, remove/re-add, clear, dedup and epoch rollover; live-entry stamp alone is insufficient. |
| W2-8 | Retain canonical transaction wire bytes in slab tail | Reviewed; unimplemented | Audit all construction/ownership/serialization contexts and memory trade-off; no wire/consensus changes. |
| W2-9 | Shared immutable network payload buffers | Reviewed; unimplemented | Cover copying, checksums, all transports, compression/encryption boundaries and asynchronous send lifetime. |
| W2-10 | Batch admission-completion relay; stage scoped SHORTTX intake | Reviewed; unimplemented | Preserve callback/error order and existing atomic-versus-individual semantics; depends on staged/package prerequisites. |
| W2-11 | Unified group-commit RPC admission coordinator | Reviewed; unimplemented | Requires safe package preparation, fairness, byte/transaction/hold-time limits and completion ordering. Queue capacity alone is not the design. |

Original Wave 2 scope and concerns: [WAVE2-REVIEW.json](atomic-performance-series/WAVE2-REVIEW.json). Proposed unsafe recipes are retained as review history, not silently implemented.

## Wave 3 — all 10 original items retained; no implementation yet

**Governing clarification:** mutable live tree/generation; pin snapshots on demand; compute hashes/sketches lazily for the requested cut. Per-update full-root copying/publication is an unselected comparison. Cross-index admission/package commit atomicity does not imply a hot full-tree snapshot per transaction.

| ID | Original item | Current state / correction required |
|---|---|---|
| W3-1 | Concurrent radix writers and live snapshots | Reviewed; redesign required. Generation/I-node/local-GCAS with a helpable requested snapshot cut is the prototype direction. Preserve existing native slab/mutable-live/lazy-hash contracts. Submitted two-atomic writer gate does not establish exclusion; no 50ns/wait-free claim. |
| W3-2 | insertOrGet and conditional removeIf | Reviewed; unimplemented. Requires proven map linearization/reclamation, predicate retry and per-attempt claim ownership. |
| W3-3 | Derived parent/child traversal and immutable/atomic entry metadata | Reviewed; unimplemented. First resolve concurrent authoritative indexes, parent/removal lifecycle and coherent views. Correct prefix units to 64 nibbles and avoid quadratic linear dedup. |
| W3-4 | Atomic counters, fee-delta fast path and entry sequencing | Reviewed; unimplemented. Counters alone do not make compound state atomic. Reservation IDs must not be mistaken for committed publication; preserve topological order and a committed frontier. |
| W3-5 | Atomic input claiming with rollback | Reviewed; unimplemented. Pending is not committed duplicate. Unique attempt tokens, multi-input/package visibility, parent reservations and capacity/abort handling are prerequisites. |
| W3-6 | Sharded execution cache and non-mutating coin lookup | Reviewed; unimplemented. Cache sharding and a coherent immutable coin provider are separate logical prerequisites; non-inserting lookup alone is not concurrent-writer safe. |
| W3-7 | Chain context snapshot and admission/block epoch coordination | Reviewed; unimplemented. Cover every cache/DB/chainstate mutator, full lifetime rules, nested RCU constraints and cold-lock/writer-drain deadlocks. |
| W3-8 | Remove cs_main/pool.cs from concurrent admission | Reviewed; unimplemented. Requires safe authoritative indexes/allocator, commit descriptors, package/parent/capacity lifecycle, ordered outbox and overlay add/remove/reset cuts. Genuine disjoint concurrent commits remain the target. |
| W3-9 | Concurrent rolling Bloom filter / inventory lock removal | Reviewed; submitted rotation is unsafe. Resolve fresh-insert erasure, generation reuse/reset/lifetime and coupled pending/known/stalled peer state. Measure actual contention. |
| W3-10 | MPSC relay ingress queue | Reviewed; submitted fetch_add sketch incomplete. Define capacity/full/reuse/publication holes, lossless fallback, wakeup/shutdown and explicit consumer ownership before strand changes. |

Reviewed plan: [REVIEWED-PLAN.json](wave3/REVIEWED-PLAN.json).
Detailed audits: [radix](wave3/radix/REVIEW.md), [on-demand constraints](wave3/radix/ON-DEMAND-CONSTRAINTS.md), [admission](wave3/admission/REVIEW.md), [network queues](wave3/network-queues/REVIEW.md).
Additional atomic prerequisites may be necessary; the numbered labels do not justify bundling unrelated mechanisms into one commit.

## Integration and measurement checklist

- [ ] Close intermediate native-owner build/test failures without changing the frozen endpoint source tree; retain both failed attempts and exact old→new ledgers.
- [ ] Fold the separately gated currency fixture repair into its original native currency owner, preserving every assertion and the final tree.
- [ ] Integrate gated C5, C6, C11, equality and binary-ID candidates onto the correct shared/native boundaries; test combined results. A preserved candidate is not integrated.
- [ ] Finish queue foundation → admission-suffix API → production integration as separate gated changes.
- [x] Finish nibble correctness gates and scoped paired microbenchmarks; lookup rates are not daemon TPS.
- [x] Complete C11 three alternating before/after pairs. Distinguish prepared fixture count from actually timed transaction count; report raw admission and exact all-peer completion independently.
- [ ] Profile the combined native endpoint again and investigate regressions rather than assume each candidate is faster.
- [ ] Measure accepted-block processing separately. No current result establishes block-confirmed or Avalanche-finalized TPS.
- [ ] Adopt measured improvements and preserve rejected/unmerged experiments, reports, source refs/bundles and cleanup disposition.
- [ ] Broader source-owner/logging consolidation and remaining migration work stay open; do not declare the overall goal complete at an intermediate milestone.

All performance claims require matched source/binary/config identities and at least three alternating isolated pairs. No build/indexer runs during timed benchmarks. Keep one owner-granted heavy host window and at most one worktree level; reused lane names and current owners are recorded in `daemon/WORKTREES.json`.
