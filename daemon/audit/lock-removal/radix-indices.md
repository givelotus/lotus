# Lock-removal audit: radix structures and lock-free mempool indices

Repository `daemon/lotusd`, branch `origin/archive/merklix-snowball-20261024` (tip `71a6f79331`).

**Method and limits.** This is a static read of each commit's tree. Nothing was built, run or put under TSAN, so "confirmed" means established by reading the code path end to end, not by reproduction. Every file:line is at the named commit.

**Commit order.** `b033646c60` is an ancestor of `9e484521d6`, not the other way round as the brief listed them. The nestable `RCULock` arrives between them in `4ff6454942`, which is not in this review set, and that ordering matters for B2.

## Summary

| Commit | Subject | Verdict | Tier |
|---|---|---|---|
| `da31264727` | radix pinSnapshot / RadixTreeMap | **fix** | shared |
| `952db7eb9e` | txrelay_index lock-free | **pass** | v2 (diff itself is neutral) |
| `ac31d9dc2d` | mapNextTx to RadixTreeMap | **hold** | mixed |
| `77d48070c8` | live RadixTree on CTxMemPool | **fix** | shared |
| `d650d95bfb` | unbroadcast entry flag | **fix** | shared |
| `b033646c60` | borrow leaves, SHORTTX cache, socket drain | **hold** | mixed |
| `9e484521d6` | lock-free size(), RCU coalescing | **fix** | mixed |

Two defects block adoption:

- **B1:** one unauthenticated `tx` message aborts a default-configured node. It is still present at the tip.
- **M1:** `mapNextTx` leaks about 9 KB permanently per parent transaction that has two outputs spent in the mempool. The memory is invisible to `-maxmempool`. It is also still present at the tip.

---

## `da31264727` radix: pinSnapshot, forEachFrom/Prefix, RadixTreeMap

**Verdict: fix. Tier: shared.** The diff has no V2 types. It depends on `support/allocators/chunked_slab.h`, which must be in the shared tier.

### Confirmed

**R1. Removal never prunes, and keys sharing a long prefix allocate full spines. Severity: high when used for `mapNextTx`; see M1.**
- `src/radix.h:297`: `remove` CASes the leaf slot to empty and leaves the nodes in place. A node is freed only when the whole tree is released.
- `src/radix_map.h` documents `OutpointRadixKey` as 72 levels.
- The generic map therefore has no bound in terms of live size for adversarial or structured keys. Nothing in the header warns of this.
- Fix: implement pruning or path compression, or document the constraint that keys must be uniformly distributed and reject the outpoint key.

**R2. `DynamicMemoryUsage` omits all node memory. Severity: high in combination with M1.**
- `src/radix_map.h:355` returns `size() * sizeof(Entry)`.
- It excludes `RadixNode` (8 + 16×8 = 136 bytes each) and heap-owned values, such as the `std::vector<TxId>` buckets at this commit.
- Fix: count allocated nodes with an atomic counter in the tree, and report node bytes.

### Suspicions / API hazards

**R3. `pinSnapshot()` looks safe and is not. Severity: low today.**
- `src/radix.h:104` and the `RadixTreeMap` comment call it "lock-free". The `ImmutableSnapshotTag` contract requires that no source mutation be in flight.
- Pinning during a concurrent writer gives a torn snapshot.
- The only production caller, `TxRelayIndex::SetEpoch`, holds `m_mutex`, which excludes all writers, so this is safe today.
- Fix: rename it or make the writer-exclusion requirement explicit.

### Design-review hazards (W2-1, W3-1, REVIEW.md)

- **Two-atomic writer gate (findings 1 and 2):** not implemented here, so the weak-memory hole does not exist. There is no concurrent-writer claim in the actual callers: `mapNextTx` and `m_tx_tree` writers hold `cs`, and epoch writers hold `m_mutex`.
- **Clone lost update (finding 3):** requires two concurrent writers on one tree. No caller does this, so it is not reachable.
- **"Lock-free" wording:** this holds for reads only. Writes rely on external serialization, and the header should say so.

### Checked and correct

- `insertOrAssign` (`radix.h:384`): each CAS failure path re-seeks. The old leaf reference is released exactly once, under RCU, and a failed `newChild` CAS clears the slot before destruction, so no double release occurs.
- `forEachPrefix`: the `level` wrap at full depth is harmless because `level` is not read after the loop.
- `forEachFrom`: order and pruning are correct.
- `keyAtLeast`: consistent with nibble order for `arith_uint256`-based keys.
- `TOP_LEVEL` is 71 for outpoints and 31 for the 128-bit key.
- Slab reuse happens only after the RCU grace period, because all deletes go through `registerCleanup`.

### Tests

Tests are included and would fail to compile without the change. The "concurrent" case has one writer thread (its comment says "multiple threads") and only pins while single-threaded. It does not exercise pinning under concurrency, or memory bounds.

---

## `952db7eb9e` txrelay_index: lock-free reads

**Verdict: pass. Tier: v2.** The diff adds no V2 types, but the file it changes calls `lotus::v2::DeriveEpochSipHashKey` (`src/net/txrelay_index.cpp:20-22`) and only serves the negotiated short-id relay. It can move to a shared tier only if that key derivation moves too.

### Checked

- **Writers:** every tree mutation (`Add`, `Remove`, the `SetEpoch` replay, `pinSnapshot`) holds `m_mutex`. The private rebuild tree has a single owner until publication.
- **Publication:** `m_published_epochs` uses atomic shared_ptr load and store with acquire/release everywhere, including initialization.
- **Readers:** `Find`, `FindEpoch`, `Current`, `Epochs` and `Size` keep the snapshot alive through a shared_ptr. Buckets are immutable entries replaced by CoW, so a reader never sees a vector mid-mutation.
- **Compound state:** `RemoveFromEpoch` removes `short_id_of` before the bucket, so a concurrent `Find` can briefly return `HAVE` for a transaction being removed. Callers must already tolerate that, because mempool membership is checked separately.
- **Memory:** epoch trees are discarded per block and keys are SipHash or random TxId, so the spine problem does not apply. Non-pruned nodes are bounded by churn within one epoch.
- **Collisions:** a bucket's CoW cost is bounded because 64-bit collisions are rare.

### Suspicions

- **T1. Low.** The last reader to drop an old `EpochSnapshot` tears down a whole tree on that thread, through about 2n `registerCleanup` calls (a `std::function` plus a `std::map` node each). A network thread may therefore absorb an O(mempool) stall at each new block. Consider releasing old epochs on a dedicated thread. Not measured.

### Tests

None added and none concurrent. Existing index tests were not re-run.

---

## `ac31d9dc2d` mapNextTx to RadixTreeMap

**Verdict: hold. Tier: mixed.** The added `input.nFlags != 3` in `CanFitRawTxBatch` (`src/txmempool.cpp:1212`) is a V2 field. That hunk belongs in the V2 tier; the rest is portable.

### Confirmed

**M1. Remote, permanent, unaccounted memory growth. Severity: critical/high (remote DoS), and it also occurs under ordinary traffic.**
- Location: `src/txmempool.cpp:217` (insert), `:313` (erase), `src/txmempool.h:378`, combined with R1 and R2.
- Mechanism: `(txid,0)` and `(txid,1)` differ only in the last nibble, so inserting both creates a node at nearly every level from the shallow random depth (about 5) down to level 0. That is roughly 67 nodes × 136 bytes ≈ 9 KB. `erase` frees only the leaf `Entry`. The spine stays until `_clear()`, and a later parent has a different txid, so spines are never reused.
- Trigger: a parent with two outputs and a child spending both, which is about 550 bytes of standard transactions at the minimum relay fee. Two separate children work too, as does any transaction spending two outputs of one confirmed parent, because `mapNextTx` also keys confirmed prevouts.
- Why limits do not help: `DynamicUsage(mapNextTx)` (`:1191`) counts only `Entry` bytes, so `-maxmempool` eviction never sees the growth, and `CanFitRawTxBatch` (`:1205`) under-reports likewise.
- Impact: about 1 GiB per 115k such parents. Eviction or expiry does not recover it, only a restart does. A node also leaks steadily under normal traffic.
- W2-3 flagged this design ("72 nodes for two sibling claims and does not prune"). The implementation ignored that warning, and no later commit up to the tip adds pruning.
- Fix options:
  1. Key on a salted hash of the outpoint for point lookups, plus a per-entry children scan or a txid→outputs structure for the prefix scan.
  2. Use a compressed, pruned trie with RCU-reclaimed nodes.

  In either case, add node accounting and a test asserting bounded nodes after churn.

**M2. The slab tests were weakened, removing the check that would have caught this. Severity: medium.**
- `src/test/mempool_tests.cpp` removed the `mapNextTx` allocator assertions.
- Its replacement, `BOOST_CHECK_EQUAL(pool.mapNextTx.DynamicMemoryUsage(), 0U)` after clear, is true by construction when `size()` is 0.
- `MempoolSizeLimitTest` no longer includes `mapNextTx` in retained bytes.
- Fix: restore equivalent node-level assertions.

**M3. Blind overwrite replaces exclusivity with last-writer-wins. Severity: low/medium hardening.**
- `src/txmempool.cpp:217` uses `insertOrAssign` and ignores the result. W2-3 warned against exactly this.
- If a conflicting claim ever reaches `addUnchecked`, the old code kept the first claimant and the new code silently keeps the last. Either way, the `erase(prevout)` at `:313` removes a claim belonging to the other transaction, because it does not compare the owner.
- I found no production path that reaches this: admission checks conflicts under `cs` and batch paths check duplicate prevouts. The invariant is simply no longer asserted.
- Fix: use `insert` and `assert` success, and make erase conditional on the owner in debug or check builds.

### Removal of `GUARDED_BY(cs)`

`src/txmempool.h:378` loses thread-safety checking for the whole structure, including writers. Each tree operation stays linearizable, but `isSpent()` and `mapNextTx.contains()` are now lock-free readers of compound state (see 77d4 L1). `GetConflictTx` keeps a stale `EXCLUSIVE_LOCKS_REQUIRED(cs)`. Suggested fix: keep writer methods behind a `cs`-asserting wrapper.

### Checked and correct

- Parent/child semantics: `forEachPrefix` with `TXID_PREFIX_NIBBLES` = 64 is equivalent to the old `lower_bound` scan, and the unit is correct (nibbles, not bytes). The set deduplicates children. The test covers near-neighbour txids and `n` ≥ 256.
- `removeConflicts` now holds a strong ref while recursing, which is safer than before.
- Callbacks under `forEachPrefix` take no nested `RCULock`, so they are safe even on the non-nesting RCU at this commit.

---

## `77d48070c8` live RadixTree indices

**Verdict: fix. Tier: shared.**

### Confirmed

**L2. Tree nodes are uncounted. Severity: medium/low.**
- `m_tx_tree` (`src/txmempool.h:353`) allocates nodes that `DynamicMemoryUsage` omits.
- TxIds are effectively random, so depth is about log16(n). Node count tracks peak live size rather than cumulative history, because an empty slot in an existing node is reused.
- This is an accounting error of perhaps tens of bytes per transaction, not a leak. Grinding txids to deepen paths costs 2^(4d) work.
- Fix: count nodes (R2).

### Suspicions

**L1. Lock-free readers see compound state mid-update. Severity: low; no breaking consumer found.**
- `src/txmempool.cpp:204` publishes the entry to `m_tx_tree` before `mapNextTx` (`:218`), parent/child links and totals. Removal erases `mapNextTx` (`:314`) well before `m_tx_tree` (`:336`).
- Previously `LOCK(cs)` hid these windows and hid whole batches: a reader could not observe a partially committed package. `exists()` can now be true while the transaction's inputs are not yet in `mapNextTx`.
- I found no lock-free consumer that combines the two. Validation readers holding `cs` see a consistent state, the `validation.cpp` readers are explicitly hints, and the staged-admission check below is sound.
- Fix: document the contract on `exists`/`get`/`info`: per-index linearizable only, with no cross-index atomicity.

### Answering W2-4 and W3-4

- **Lifetime:** RCU plus `RCUPtr` is correct. All decrements defer through `registerCleanup`.
- **Metadata:** the `GetInfo` fields are `const` apart from `m_modified_fee`, now atomic. `UpdateModifiedFee` is a load/store, safe only because writers hold `cs`, which they do. `entryId` is non-atomic but set before the seq_cst CAS publication (`addUnchecked` start).
- **Unsafe-if-read fields:** `m_parents` and `m_children` are `reference_wrapper`s into `mapTx` nodes and would dangle if read through a retained `getEntry()` result. No lock-free caller reads them: `snapshot.cpp:201` and `validation.cpp:2294` hold `cs`, and I did not find a parent/child read on the two remaining `getEntry` callers in validation (`:4092`, `:4476`), though I did not read every line downstream of them. Worth a comment.
- **Clear:** `_clear` swaps the tree under RCU before `mapTx.clear()`. Readers keep the old tree or see empty. Safe.
- **Re-admission:** a new entry object means a fresh flag and id, and old readers keep the old entry. Safe.

### Tests

`lock_free_tx_tree_lookups` is single-threaded. It would fail without the change only because `getEntry` would not compile. It does not exercise any race.

---

## `d650d95bfb` unbroadcast entry flag

**Verdict: fix. Tier: shared.** The diff contains no V2 types. It relies on the snapshot publisher and `submitrawtxbatch` being present in the tier.

The commit removes `cs` from a path that takes `cs` anyway when it publishes, so the lock removal buys almost nothing and costs the atomicity below. **Simplest fix for U1 to U3: take `cs` for the whole of `AddUnbroadcastTx`,** which is local-origin and rare.

### Confirmed

**U1. Count leak when `AddUnbroadcastTx` races removal. Severity: medium.**
- `src/txmempool.cpp:1237-1247`. T1 gets the entry. T2 (block or eviction) runs `removeUnchecked`, where the flag is still false so no decrement happens, and removes it. T1's `SetUnbroadcast(true)` succeeds on the detached entry and increments the count.
- The entry is gone, so nothing ever decrements. `unbroadcastcount` is wrong until restart, and the `count == 0` fast paths stop working.
- Old code performed `exists` plus insert under `cs`.
- `_clear` has the same race: `:478` zeroes the count before the tree is cleared.
- Not a memory-safety issue, because T1 holds a ref. Triggered by RPC submission racing a block.

**U2. Log entry lost, so a transaction is never retried. Severity: low/medium.**
- `GetUnbroadcastTxs` at `:1251-1253`: it loads `count == 0`, then T1 increments and pushes, then T2 takes the mutex and `clear()`s T1's entry.
- The flag stays true and the count stays 1, but the txid is no longer in the log, so `ReattemptInitialBroadcast` and mempool dump skip it.
- Fix: re-read the count under the mutex.

**U3. Transient count underflow. Severity: low.** `SetUnbroadcast(true)` precedes `fetch_add`, so a concurrent remover can `fetch_sub` first, making `size_t` wrap. A snapshot published in that window reports about 1.8e19.

**U4. The log grows with cumulative submissions. Severity: low/medium, local RPC only.**
- `:1243` appends on every add. It is compacted only by `GetUnbroadcastTxs`, which runs from the periodic rebroadcast task and on dump. Entries for fetched or removed transactions stay until then.
- At the batch-RPC rates this branch targets, that is 32 bytes × rate × the rebroadcast interval. Compaction then holds the log mutex over O(n log n) work and blocks adders, which can be inside `pool.cs`.
- Peers cannot reach this path. Fix: compact on a size threshold.

### RPC freshness (W2-6)

- `getmempoolentry` and `getmempoolinfo` read the snapshot. At this commit every non-`unchecked` state change republishes and reads the live flag, so the final publish wins even when two publishes race. Freshness is preserved here. It regresses at `b033` (B6).
- `unchecked` removals skip the publish, which is fine because the removal itself republishes.
- Re-admission: a new entry starts unbroadcast=false, matching the old removal-from-set behaviour. A stale log entry is filtered by the flag check. Correct.

### Tests

None added.

---

## `b033646c60` borrow RCU leaves, SHORTTX cache, socket drain

**Verdict: hold. Tier: mixed.** Split as follows:

- **Shared:** `radix.h`, `radix_map.h`, `txmempool` borrow APIs; `net.cpp` drain; `relay_inventory_queue` caching and the `SendMessages` changes; the `rpc`/`snapshot` tweaks, which are unrelated to the rest and should be their own commit.
- **V2:** `v2_protocol_handler` cache, `ProcessMessages` SHORTTX/INVSHORT/GETSHORTTX coalescing, the `txrelay_index` changes, and the `validation.cpp` `v2_*`/`nVersion == 7` paths.

### Confirmed

**B1. Remote crash: one `tx` message aborts the node. Severity: critical. Still present at tip `71a6f79331`.**
- `src/validation.cpp:2160` (and `:2096`, `:2168`): this commit changes `PreChecksBatch` from `m_pool.exists()` to `existsWithinReadSection()`, which does `assert(RCULock::isLocked())` (`src/radix.h`). It adds an `RCULock` only around the `AcceptRawTxBatch` caller (`:3073`).
- The other caller has none: `MemPoolAccept::PrepareStaged` (`:4206`, call at `:4249`) holds `cs_main` and `pool.cs`, and no `RCULock` is held on its path. At `9e484521d6` and at the tip, the `RCULock` sites in `validation.cpp` are only lines 2584, 3114, 4865, 4923 and 5045, none of which enclose `PrepareStaged` (`9e48`: `:4262`, call at `:4305`).
- Path: `tx` message → `QueueTxForAdmission` → `ThreadTxAdmission` (`DEFAULT_PARALLEL_MEMPOOL = true`) → `AcceptToMemoryPoolStaged` → `has_legacy` → `PrepareStaged` → `PreChecksBatch`.
- Preconditions: `nVersion` 1 or 2, passes context-free and standardness checks, mempool non-empty. The assertion comes **before** any input lookup, so no valid UTXO, signature or fee is needed.
- Assertions cannot be compiled out: `src/util/check.h:38` errors on `NDEBUG`.
- `src/node/transaction.cpp:267` indicates local submission uses the same parallel path. I did not trace that one to the assertion.
- Corroboration: `src/test/mempool_admission_tests.cpp` (`:421` at `9e48`) feeds `nVersion = 2` batches to `AcceptToMemoryPoolStaged` with a non-empty pool from the second batch, so by my reading it should abort. **Not run.**
- Not determined: whether a V2-activated chain rejects legacy versions earlier. I found no such rule (`tx_verify.cpp:74` accepts 1, 2 and 7), and did not enumerate every activation-gated check.
- Fix: `PreChecksBatch` already holds `cs`, so use the self-locking `exists()`/`contains()`, or open an `RCULock` in `PrepareStaged`. Add a regression test.

**B2. Nested `RCULock` aborts at this commit only. Severity: high for bisection; fixed by `4ff6454942`.**
- `src/validation.cpp:3073` holds RCU while `PreChecksBatch` calls `GetConflictTx` (`:2103`, `:2170`), which opens another `RCULock` through `withLeaf`.
- At this commit `RCUInfos::readLock` still asserts `!isLocked()`, so `submitrawtxbatch` with a conflicting transaction aborts.
- Fix: squash the nesting change before this commit.

**B3. Removal sequence is bumped before the removal is visible. Severity: low.**
- `src/txmempool.cpp:275` increments `m_removal_sequence` at the start of `removeUnchecked`. The tree removal is at `:349`.
- A reader can read the new sequence, still find the entry, and cache it under the new sequence. The cached result then looks valid after the transaction is gone.
- This affects `SendMessages` (announcing a transaction no longer held; the peer gets `notfound`) and the SHORTTX cache (serving a removed transaction until the next removal).
- No consensus effect. Fix: bump after removal, or bump both before and after.

**B4. SHORTTX cache hit sends under the handler mutex, and cached payloads are uncounted. Severity: low.**
- `src/net/v2_protocol_handler.cpp:1617-1632` calls `PushMessage` inside `LOCK(m_mutex)`. This serializes all peers' handler work on the send path and adds a lock edge from `m_mutex` to the send locks. I did not find an inverse edge.
- The cache (`:1654`, depth 4) retains up to 4 responses of up to 4096 transactions each. Entries are evicted only by a later fill, not when they go stale, and the bytes are in no memory accounting. A peer can choose to pin large payloads, bounded at 4 × maximum response size.
- Fix: push outside the lock, and evict on sequence change.

**B5. Socket drain overshoots the flood limit. Severity: low.**
- `src/net.cpp:2542-2544`: the loop checks `fPauseRecv`, which is updated only by `MarkReceivedMsgsForProcessing`, and that now runs after the loop. The check is therefore stale within a poll.
- Overshoot is up to 16 × 64 KiB ≈ 1 MiB per peer per poll past `m_recv_flood_size`, then the pause takes effect. It is bounded, but it multiplies per-peer work per poll by 16 on the socket thread.
- The close, error and disconnect paths are correct.

**B6. `FinishRemoveUnbroadcastBatch` skips publishing when the pool is larger than 64. Severity: medium for RPC correctness.**
- `src/txmempool.cpp:1415` returns early. The function was introduced between `d650` and `b033`, and this commit's `ResolveRelayShortIds` relies on it. On that path neither the publish nor `MarkSnapshotEntryChanged` runs.
- `unbroadcastcount` stays stale until the next publish, indefinitely on an idle pool.
- `getmempoolentry` reads `e.unbroadcast` from the snapshot and may stay true until that entry next changes. I confirmed the skipped mark; I did not confirm the end-to-end RPC result on large pools, where `entry_tree` capture may be bypassed.
- `test/functional` unbroadcast tests would use small pools and would not detect this.
- Fix: always mark the entry changed, and defer only the publish.

### Suspicions

**B7. Coalescing loop. Low.** `src/net_processing.cpp:10955`: up to 8 relay messages per peer per scheduling turn, against 1 elsewhere, reduces fairness between peers. A coalesced non-relay `tx` runs through serial `ProcessMessage` rather than the parallel admission branch, a behaviour change that looks unintended. An exception from a coalesced message is logged under the first message's type. I found no memory-safety problem.

### Checked and correct

- **Borrowed pointers:** every `withLeaf`/`withEntry*` callback copies out (`TxId`s, `shared_ptr`, scalars). No pointer or reference escapes a read section in this commit's call sites.
- **Lifetime:** `CTransactionRef` is copied under RCU, and the entry cannot be freed before the grace period.
- **Null dereference on `txinfo.tx`:** when `!need_tx_ref`, `tx` stays null. All dereferences are guarded by `m_bloom_filter` or `high_bandwidth_peer`, the same conditions that compute `need_tx_ref`, and `m_bloom_filter_mutex` is held across the whole selection, so `filterload` cannot flip it. No null dereference.
- **`SetUnbroadcast(false)` under RCU:** the exchange gives exactly-once decrement against `RemoveUnbroadcastTx`.
- **Cache key:** includes scope, context id, sequence and the exact short-id vector, so a cached response cannot be served across epochs.
- **`precomputed_short_id`:** used only after `key_matches` is re-verified under `m_mutex`.

### Tests

None added.

---

## `9e484521d6` lock-free size() and RCU coalescing

**Verdict: fix. Tier: mixed.** Shared: `size()`, `txrelay_index` RCU, and the `SubmitPackage` section. V2: the `v2_prewarm_*` removal, `nVersion == 7` phase B, and the native snapshot paths.

### Confirmed

**S1. The commit claims RCU coalescing but leaves B1 in place. Severity: critical (inherited).** It adds five sections and none covers `PrepareStaged`. `validation.cpp:2195` and `:4305` still reach the assertion. The nesting change in `4ff6454942` does not help, because no outer lock exists on this path.

### Suspicions

**S2. Long read sections stall global reclamation. Severity: low/medium.**
- `src/validation.cpp:2584` holds RCU across `ConsensusScriptChecks` and `Finalize` for a whole package. `:5045` holds it across `n` calls to `AcceptSingleTransaction`.
- While they run, no thread's retired objects can be freed, so retired memory grows for the batch's duration, bounded by batch size. Any `synchronize()` caller also waits.
- A thread that calls `synchronize()` from inside a read section never returns, because it waits on its own state in `hasSyncedTo`. Holding a lock while calling it deadlocks against a reader blocked on that lock.
- `synchronize()` is reached only through generic `RadixTree` copy and copy-assign (`radix.h:75`, `:119`) and thread exit. `validation.cpp` and `txmempool.cpp` contain no `withPeerManager` calls, and I found no such copy on the admission path. I did not trace every validation-signal callback, so absence of deadlock is **not proven**.
- Fix: narrow the sections to the tree operations, since script checks need no RCU. Assert `!isLocked()` in `synchronize()`.

**S3. Cleanups run while `m_mutex` is held. Low.** `src/net/txrelay_index.cpp:300`, `:330`: `RCULock` is declared after `LOCK(m_mutex)`, so `~RCULock` runs deferred deletes inside the critical section. No cleanup takes that mutex, so this costs latency only.

### Checked and correct

- **`size()`:** every `mapTx` mutation updates the cache (`txmempool.cpp:193`, `:355`, `:511`). Writers hold `cs`. It may disagree transiently with `m_tx_tree`, which is harmless because no caller combines them for a decision.
- **`pool_unchanged_since_phase_b` (`validation.cpp:5016`):** the counters are captured before phase B and compared under `cs`. `nTransactionsUpdated` is incremented after all index updates in `addUnchecked` and `removeUnchecked`, so an in-progress writer cannot produce a false "unchanged". Phase B reads live `mapNextTx`, which also covers a stale `entry_tree` for duplicates. Sound.
- **Removal of the `RCULock` from `process_range` and the phase B worker:** the remaining `*WithinReadSection` calls in those workers are in the new narrow scopes (`:4865`, `:4923`). `SmtFindBorrowed` walks a persistent `shared_ptr` tree pinned by the snapshot, so it never depended on RCU. Correct.
- **Removal of `v2_prewarm_mempool_clean`:** deletes a conflict-check skip and is a safety improvement.
- **`submitrawtxbatch`:** `LOCK2(cs_main, mempool.cs)` is correct and matches the callee's assertions.

### Tests

None added.

---

## Security answers

| Question | Answer |
|---|---|
| Remote use-after-free | None found. Every reclamation goes through RCU, and the borrowed pointers I checked do not escape. |
| Remote crash | **Yes: B1.** One unauthenticated `tx` message aborts the node. |
| Remote unbounded memory | **Yes: M1.** Permanent, and invisible to `-maxmempool`. |
| Remote CPU | Bounded: B5 (×16 socket work per poll), B7 (×8 messages per turn). Trie depth is capped at 72. |
| RPC-reachable | B2 (abort at `b033` only), U1 (count leak), U4 (log growth). |

## Could not determine

- Actual runtime behaviour: nothing was built, run, or put under TSAN.
- Shutdown: I checked destructor mechanics (`~RadixTree`, `~RCUInfos`, static slab allocators outlive thread-locals on the main thread), but not the complete node teardown order against every lock-free reader.
- Absence of an RCU deadlock across all validation-signal callbacks (S2).
- Whether activation-gated rules reject legacy transactions before the B1 assertion on a V2 chain.
- End-to-end `getmempoolentry` staleness on large pools (B6).
