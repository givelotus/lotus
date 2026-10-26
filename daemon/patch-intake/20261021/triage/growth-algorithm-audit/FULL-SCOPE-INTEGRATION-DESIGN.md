> SUPERSEDED / DESIGN REVIEW HOLD: independent canonical authority and fixed public salt choices below were rejected by subsequent user steering. Production work is paused for Astra architecture review. Read ASTRA-ARCHITECTURE-FACTPACK.md for current source facts and constraints. This file is preserved as an exploratory draft, not an integration instruction.

# Full-scope lazy Merklix recovery — implementation design

User-directed replacement for the fixed4,096/minimum-ID/recent-window reconciliation selector. The bounded-range MERKLIXPAGE exploration is explicitly superseded and must not be integrated. Starting source is tested521-derived `2b61dded451755e175681f41a57281a5c0554e32`, tree `2b4fef46071b44cc8789a49553b3d112b4fd084e`; canonical refs have moved independently and are not presumed byte-equivalent.

## Reuse and invariants

The published `MempoolSnapshotTree` already pins immutable `CTransactionRef`s containing both TxId and TxHash and records changed IDs. Its ordinary numeric radix traversal **is not the canonical Merklix commitment**. Full-scope capture will feed those exact existing delta transactions to a parallel immutable canonical view, sharing transaction references and unchanged CoW nodes. No serialized-transaction copy or whole-arena freeze is needed. Parent/child/unbroadcast-only metadata changes whose TxId/TxHash do not change must preserve canonical/SID roots unchanged.

Canonical root order is `tx_id[depth / 8] >> (depth % 8) &1`: byte0 bit0 first. A singleton is a direct leaf; multiple keys sharing a prefix retain the tagged unary binary depths. The new16-way persistent tree folds four binary levels with exact depth tags and preserves these rules. Differential tests compare `BuildTxSubtreeA`, including adversarial shared prefixes and deletions. Lazy hashes are owned by immutable nodes, so unchanged subtrees retain their cached digest across generations.

Existing GF wire prefix order is byte0 high nibble first, which differs from canonical bit order. A newly negotiated **FULL_MEMPOOL scope on existing merklixsync/getmerklixbuck/merklixbuck/getshorttx/shorttx messages** will explicitly use canonical prefix order; existing scopes retain their old order. No new page command or implicit independently rotating subset.

## Generation construction and bounded queries

The engine has a canonical TxId/TxHash tree with cached count/s1/s3/s5 and a persistent SID collision index. Each `With(tx)` / `Without(txid)` changes only the edited paths. Generations pin unchanged nodes. A global root hashes all structural nodes once on first query; later roots hash only edited nodes. Prefix queries descend the trie and read cached aggregates rather than materializing/sorting all transactions. SID requests descend the SID index and the declared canonical prefix; returning k matching collisions costs O(depth+k), avoiding a full collision scan followed by truncation.

Reconciliation never filters by admission age. Whole-root comparison includes the full published mempool, including higher IDs and transactions older than30seconds. Existing bounded recent-relay indexing remains useful to announcement logic but cannot define the authoritative recovery set.

Root hashing runs outside `cs_main` and the mempool/index mutexes. The existing persistent overlay hashing pool is exposed through `ForEachOverlayHashShard`; only the outer root dispatches at most16 shards, with serial recursion below it. No per-node std::async or new worker pool. Instrumented hash-computation counts must show initial structural-node work, no work on repeated roots and limited changed-path work after k edits.

## Round and key identity

A round pins both sides' immutable generations. Request contexts distinguish a sender round from the epoch/key identity, so later publications do not silently change a response's scope. Existing generic salt validation cannot be reused blindly: GF caches and the SID tree are structurally tied to the complete key/mask/domain. Wire metadata and validated context caches must carry that binding.

The current implementation plan uses a deterministic network/domain-specific key for FULL_MEMPOOL recovery rather than rekeying every CoW publication or blocking admission to rebuild M entries on each block. Ordinary relay short IDs keep their existing per-block epoch rotation. A fixed key is not a consensus authenticator: per-prefix cryptographic hashes and full-ID prefix resolution must prevent short-ID collisions from hiding a difference, and all collider responses stay bounded. This choice must be explicit in the implementation/spec and reviewed; it must not be smuggled in as reuse of an old epoch cache. An epoch-rotated alternative requires off-lock rebuild plus mutation catch-up, a separate O(M) maintenance boundary.

## Zoom and terminal progress

Existing16-way subdivision and GF(2^64) s1/s3/s5 recovery remain the algorithm. FULL_MEMPOOL descriptors widen depth to0..256 and prefix to32bytes; counts must cover full-pool sizes. Each child carries a prefix commitment so equal counts/syndromes cannot mask an actual root difference. Requests descend only mismatching prefixes; a message still contains at most16 children. At a full256-bit ID prefix there is at most one TxId in a mempool; no truncated4,096-element terminal list can permanently exclude a tail.

Body requests carry their declared prefix, a bounded SID list and pinned round context. Responses must match that prefix/context. Request budgets are flow control, never membership truncation: a skipped/delayed prefix remains eligible in subsequent rounds. Context retention is bounded with explicit FIFO expiry/retry; evicted contexts must not fall back to scanning the live pool.

## Required evidence

- Deterministic >4,096 missing high-ID transaction, including age>30seconds.
- Balanced differences, dense shared prefixes and forced SID collisions, without relying solely on count positivity.
- Pinned old generations across admission/removal/churn and body responses tied to the right round.
- Maximum-depth/empty/singleton/unary-root and malformed-prefix bounds.
- Instrumented hash-node count/structural sharing; no full-list materialization per poll or prefix.
- Existing focused native suites; then exact500K3-node convergence and inventory/digest checks under N1/runtime coordination.

No native test or throughput claim is made by this design file. Engine source candidate `67909cca63` is prepared; protocol integration and full tests are in progress. Initial-relay/request-state repair is an independent lane and may be validated sooner.
