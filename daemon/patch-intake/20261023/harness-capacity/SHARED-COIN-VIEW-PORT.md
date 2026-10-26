# Shared immutable coin views for eCash and snapblock

Status: inspected follow-up design, not an implemented or integrated eCash UTXO snapshot feature. No eCash consensus/header/coin encoding change is proposed here.

## Evidence and scope

The RPC worker/concurrency comparisons and 64-client lock profiles used shared ABC/eCash, with legacy transactions. Their preparation-lock measurements cannot be attributed to native V2. Native V2 already has `PrepareNativeCryptoFromSnapshot`, a pinned native UTXO root and an immutable mempool entry tree. Its native signature/context adapter must remain in the V2 tier.

At shared `d38c382061`, `src/coins.h` still defines `CCoinsMap` as a mutable `std::unordered_map`, and `CCoinsViewCache::FetchCoin` can modify that cache even through a const API. The shared `ChainAndMempoolSnapshot` publishes headers, scalars and the persistent mempool entry tree; it does not expose a coherent confirmed-coins snapshot.

The backing shared engine is already MDBX. `CDBWrapper` pools read-only transactions and opens the environment with `MDBX_NOSTICKYTHREADS`. A database read transaction can pin an MVCC generation. The current `DBBackgroundHandle` is a guarded callback/lifetime-detachment facility; holding it does not keep the database alive or pin one database generation. It is not itself the required snapshot.

## Proposed shared contract

A pinned `CoinsReadView` should own:

- The exact block anchor and chainstate identity, plus the height/rule context needed by preparation.
- A read-only MDBX transaction for a stable backing-store generation.
- A persistent CoW overlay of coin-cache changes relative to that database generation.
- A coherent immutable mempool view, including the information required to mask spent outputs and resolve unconfirmed parents.

The lookup order is the captured mempool/coin overlays, then the captured database generation. An explicit removal entry must hide an output that still exists in the older database generation. This is temporary overlay bookkeeping, not an indefinitely retained history of spent outputs.

Snapshot acquisition should retain roots/leases. It must not scan or copy the whole UTXO set or coin cache. Use batch CoW updates and the shared slab-backed persistent-tree mechanisms where suitable. Variable script data and complete outpoint identity must be retained correctly; key hashing must not silently overwrite colliding outpoints. Hash computation is optional for ordinary lookups and can be lazy for reconciliation/proof users.

## Coherence and lifecycle work

1. Add an explicit MDBX read-view lease. Define cross-thread use and serialization rules: `NOSTICKYTHREADS` does not imply simultaneous unsynchronized use of one transaction/cursor is safe. Database resize, replacement and shutdown must not invalidate pinned views.
2. Maintain the persistent dirty overlay on every authoritative coin addition, spend and undo operation, including the cache-flush path. Do not add an unused mirror that callers never consult.
3. Publish the block anchor, database-generation lease, coin-overlay root and mempool generation together at an existing writer checkpoint. A cache flush changes the database base and overlay together. An old pinned view keeps its original pair.
4. Bound snapshot lifetime/retention and monitor pinned MDBX pages. Long-lived readers can delay physical reclamation; the port must not recreate historical-snapshot amplification.
5. Use the shared view for advisory eCash preparation and snapblock speculative validation. Copy/retain everything asynchronous work needs; never retain an unlocked pointer into `cacheCoins`.
6. Keep authoritative commit checks. Recheck chain context, coin availability/conflicts and relevant policy before mutation. Revalidate the relevant read set; invalidating every prepared transaction whenever an unrelated mempool arrival changes the overall generation would destroy throughput. A stale view must cause retry/fallback, not authorize acceptance or cause a permanent invalid verdict.
7. Route the V2 native commitment/signature representation through its adapter. Do not import native version-7 rules, expiration policy or header commitments into ABC.

## Required behavior checks before adoption

- A view remains stable across cache mutation, dirty-cache flush and subsequent database writes.
- Spending an output cannot resurrect it through a fallback to the old database generation.
- Reorgs and same-height competing tips keep old views coherent and force current-state rechecks.
- Confirmed and unconfirmed parent lookups, parent eviction/conflicts and missing snapshot coverage behave correctly.
- Chainstate/database replacement, resize, shutdown and cross-thread retirement preserve lifetimes.
- Ordinary reads and snapshot acquisition remain bounded; benchmark update cost, retention and reclamation across increasing UTXO/mempool sizes.
- Snapblock and ordinary admission actually consume this view. Tests must exercise those real integration points, not just a standalone container.

Implement on the shared eCash tier first, then retain the V2 adapter. Keep candidate source, an ownership ledger and both tier validation gates in this canonical repository. This follow-up is not yet claimed delivered.
