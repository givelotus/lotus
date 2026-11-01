# Lock-removal audit: net_processing commits

Read-only review of six commits in `/Users/shammah/repos/lotus/daemon/lotusd`. Nothing was built or run, so every finding comes from reading code at the named commit. "Confirmed" means the full path is traceable in source, not that it was reproduced at runtime.

The requested ref `origin/archive/merklix-snowball-20261024` does not exist in this clone. The six commits are reachable from `origin/snowstorm/rateless-fountain`, which is what I used. Line numbers are at the commit under review.

## Summary

| Commit | Verdict | Tier | Main point |
|---|---|---|---|
| `a5b4951884` batch relay, lock-free mempool check | pass | shared | Correct, with low-severity notes |
| `703a07c21e` AddBatch, lock-free entry lookup, INVSHORT | pass | shared | Correct; rank staleness is healed at selection |
| `447c4aac77` redundant cs_main removal | fix | shared | Logic correct; three `GUARDED_BY` removed with no replacement |
| `f8ace4160c` Epochs, ForgetShortIdRequests, unordered_set | pass | shared | One low-severity edge in the short-id skip |
| `e91e089f30` decouple tx relay and m_txrequest | **hold** | shared | Remote-triggerable deadlock, on by default |
| `b8f43cdb8b` bypass snapshot and filter, batch overhead | **hold** | mixed | Peer can make wallet notifications disappear |

No commit adds or changes a test (`git show --stat` on all six shows no test file). The hazards below would not fail any existing test that I could identify.

`AlreadyHaveTx` still calls `ActiveChain()` under `m_recent_rejects_mutex`, the `TRY_LOCK(cs_main)` is still there, and both signal-suppression flags remain at the tip of `origin/snowstorm/rateless-fountain`, 15 commits after `e91e089f30`.

---

## `e91e089f30`: hold (tier: shared)

### What each removed lock guarded

| State | Was | Now | Assessment |
|---|---|---|---|
| `m_txrequest` | `cs_main` | `cs_txrequest` (member `GlobalMutex`) | All sites hold it (checked every grep hit); correct except for what is done under it, see E1 |
| `m_txrequest.Size()` fast path | `cs_main` | relaxed atomic `m_size` | Correct. Only two mutation sites, `invrequest.cpp:432` and `:708`. Stale reads cost one redundant request or a skipped no-op forget |
| `m_recent_rejects*`, `hashRecentRejectsChainTip` | `cs_main` | `m_recent_rejects_mutex` | Data is guarded, but the lock order is wrong (E1) and the reset moved (E3) |
| `m_tx_admission_inflight_shortids` | `cs_main` | `g_msgproc_mutex` | Correct; all users are on the message thread |
| `fPreferredDownload` read | `cs_main` | atomic mirror on `Peer` | Correct; written once at VERSION (`:7173` region) |
| `fSyncStarted` read | `cs_main` | atomic mirror on `Peer` | Correct; every write site is mirrored (11409, 11424, 11428, 12034) |
| `m_next_relay_drain` | `g_msgproc_mutex` | atomic | Correct. Writer is still the message thread; a stale producer read only delays a wake to the next tick |
| `CChain::Tip()` | `cs_main` | atomic `m_tip` | Correct but currently useless: `ActiveChain()` still takes `cs_main` (E1) |

### E1. Critical, confirmed: AB-BA deadlock a peer can trigger, default configuration

`AlreadyHaveTx` lost its `cs_main` requirement but still calls `m_chainman.ActiveChain()` while holding `m_recent_rejects_mutex` (`net_processing.cpp:3980-3981`). `ActiveChainstate()` takes `LOCK(::cs_main)` (`validation.cpp:12213-12214`), so the order is `m_recent_rejects_mutex -> cs_main`.

**Cycle 1: message thread and `txadmit` thread.** `-parallelmempool` defaults to true (`node/txadmission.h:28`).

- The `txadmit` thread holds `cs_main` for all of Phase C (`validation.cpp:4079`). For every item it calls `skip_at_commit` (`validation.cpp:4116`), which calls `AlreadyHaveTx` (`net_processing.cpp:3454`). Its order is `cs_main -> m_recent_rejects_mutex`.
- The message thread calls `AlreadyHaveTx` without `cs_main` from the INV path (`:7733`, the lock was removed by this commit) and from `PrepareTxAdmission` (`:5996`, via `QueueTxForAdmission`).

Failure scenario, requiring no funds:

1. A peer sends one transaction that fails validation. `ProcessInvalidTx` sets `m_has_recent_rejects`, which enables the branch at `:3978`.
2. The peer sends at least two more transactions, valid or not, so the `txadmit` thread enters Phase C and holds `cs_main`. `skip_at_commit` runs before validity is checked.
3. The peer sends an INV. The message thread takes `m_recent_rejects_mutex` at `:3980` and blocks on `cs_main` at `:3981`.
4. The `txadmit` thread reaches its next item and blocks on `m_recent_rejects_mutex`.

`cs_main` is now held forever. Message handling, block validation and every RPC that needs `cs_main` all stop. The window is the whole Phase C hold, not a narrow race, so ordinary mainnet traffic with a single rejected transaction can also hit it.

**Cycle 2: message thread and socket thread.**

- `SendMessages` holds `cs_txrequest` (`:12163`) and calls `AlreadyHaveTx` (`:12210`), giving `cs_txrequest -> m_recent_rejects_mutex -> cs_main`.
- `FinalizeNode`, called from `DeleteNode` on the socket thread (`net.cpp:2255`, `:3924-3927`), holds `cs_main` (`:3029`) and takes `cs_txrequest` (`:3063`).

A peer that keeps disconnecting while tx requests are due can hit this. It wedges socket I/O as well.

**Why nothing caught it.**

- `ActiveChain()` is annotated `EXCLUSIVE_LOCKS_REQUIRED(GetMutex())` (`validation.h:1865`), so clang should warn at `:3981`. `-Wthread-safety` is on (`src/CMakeLists.txt:262`), but I found no `-Werror` in that file, and GCC ignores the annotations.
- A `DEBUG_LOCKORDER` build should abort at the first inverted pair. I infer this from the code; it was not run.

**Fix.**

- Do not touch `cs_main` from `AlreadyHaveTx`. Read the tip hash lock-free (`node::GetGlobalSnapshotPublisher().Load()->best_block_hash`, or a dedicated atomic), or reset the filters from `UpdatedBlockTip`.
- Annotate `!m_recent_rejects_mutex` and `!cs_txrequest` on callers. Make both plain `Mutex`, not `GlobalMutex`, so negative annotations apply.
- In `SendMessages`, collect `requestable` under `cs_txrequest`, evaluate `AlreadyHaveTx` outside it, then re-lock to record `RequestedData`.
- Add a regression test: hold `cs_main` on another thread while a rejected tx and an INV are processed, and run under `DEBUG_LOCKORDER`.

### E2. Medium, confirmed: `TRY_LOCK(cs_main)` silently skips block sync and peer eviction

`check_block_sync` runs only if `TRY_LOCK` succeeds once out of IBD (`:12110-12117`). That lambda holds stall detection, block-download timeout, headers-sync timeout, `ConsiderEviction` and **`getdata` for blocks** (`:11946-12102`).

Scenario: a peer floods transactions, so Phase C holds `cs_main` most of the time. Each `SendMessages` pass then has a good chance of skipping all of this for that peer, with no retry flag other than the next loop. Direct fetch in `ProcessHeadersMessage` still works, but blocks that depend on `FindNextBlocksToDownload` and eviction of bad outbound peers are delayed for as long as the flood lasts. Delay is not permanent, because a later pass can win the lock. I did not measure how long.

Fix: fall back to a blocking `LOCK` once a per-peer deadline passes (for example 1s since the last successful pass), or block when the peer has known blocks we still need.

### E3. Low-medium, confirmed: rejects reset no longer runs when the filters are empty

The tip check moved inside `if (flags)` (`:3978-3991`), so `hashRecentRejectsChainTip` now goes stale whenever the filters are empty, instead of being refreshed on nearly every `AlreadyHaveTx`. `ProcessInvalidTx` resets correctly before inserting (`:5876-5886`). The other insert sites do not:

- Avalanche rejection (`:9472` region)
- Avalanche finalized conflicts (`:9568` region)
- Orphan with rejected parents (`:6130` region)
- Package hash (`:6284` region)

Scenario: the tip advances with empty filters, avalanche inserts a rejected txid, and the next `AlreadyHaveTx` sees a stale hash and wipes it. The tx can then be downloaded again, and `GetAvalancheVoteForTx` no longer reports it as invalid.

Fix: one helper that resets on tip change, called from every insert site, or a reset from `UpdatedBlockTip`.

### E4. Low, confirmed: thread-safety annotations weakened without replacement

- `AlreadyHaveTx`, `ProcessValidTx` and `PrepareTxAdmission` dropped `cs_main` with no `!m_recent_rejects_mutex` or `!cs_txrequest` added.
- `ForgetShortIdRequests` lost its annotation entirely (`:1674`). `cs_txrequest` is non-recursive, so a call with it held self-deadlocks undetected. No current caller does this; `MarkPeerKnownTxBatch` inlines the loop to avoid it.
- `handle_done_item` is `NO_THREAD_SAFETY_ANALYSIS` (`:3574`), which also disables checking of its `FinishTxAdmission` call. The runtime logic is correct: `any_needs_cs_main` covers REPLAY and every non-VALID result, and `Assert(cs_main_held)` backs it.
- `cs_txrequest` and `m_recent_rejects_mutex` are member `GlobalMutex`es. That type exists for mutexes at global scope, where negative annotations cannot work. Using it on members is what let E1 through.

### Checked and correct

- **Teardown.** `TxAdmissionSender` holds a `CNode` reference and a `PeerRef`, so `FinalizeNode` cannot run until queued work completes. `StopTxAdmission` fences producers under `g_msgproc_mutex`. An announcement added for a disconnecting peer cannot outlive `DisconnectedPeer`.
- **Atomic versus individual.** `ProcessTxAdmissionDone` still handles results individually and in order; only `relay_batch` flushes at the end. Unchanged by this commit.
- **`ProcessValidTx` without `cs_main`.** Its body touches only `m_txrequest`, the orphanage and relay, each with its own guard.
- **First-gate skip at `:11350`.** Everything in that block is tied to headers relay or initial sync. `m_best_header` is dereferenced later only when `fSyncStarted`, which requires the gate to have passed.
- **Check-then-add on INV.** A tx confirmed between `AlreadyHaveTx` and `AddTxAnnouncement` is caught by the second check at `:12210`.
- **GETDATA now follows GETSHORTTX.** Requests have no required order.
- **`SetTip` and `m_tip`.** `vChain` is modified only in `SetTip`, and the store comes last.
- **Announcement writers.** I traced `AddRelayShortIdAnnouncements` to the V2 handler (`net/v2_protocol_handler.cpp:383`) and assumed it runs on the message thread, as the rest of that handler's request path does. I did not trace that call chain to its root.

---

## `b8f43cdb8b`: hold (tier: mixed)

**What to split.**

- Shared: `ShortIdBucket`; `DynamicMemoryUsageLocked`, `LimitSize` and `mapDeltas` fast paths; snapshot entry-tree bypass (`ChainAndMempoolSnapshot` exists in `ecashd`).
- V2 only: `PrepareNativeCryptoFromSnapshot` (no match in `ecashd` `src/validation.cpp`), `NativeAdmissionPreparation`, `store_sig_cache`, `can_fast_verify`, and `FromV2Output`.
- Separately reviewable: the raw-batch RPC fast path (`batch_accepted`), which should not travel with the lock and bypass changes.

### B1. High, confirmed: mempool notifications silently dropped for batches of 128 or more

When `n >= 128` and no subscriber wants spent coins, `suppress_staged_signals` (`validation.cpp:4258`) and `suppress_batch_signals` (`:2204`) make `Finalize` skip enqueueing the signal. The sequence number is still consumed (`:2131`), and nothing fires later: `batch_signals` stays empty at `:2259` and `:4343`.

- `TX_ADMISSION_MAX_BATCH` is 4096 (`net_processing.cpp:94`), and the queue fills from the network, so a peer can reach 128 by sending 128 transactions quickly.
- `node/interfaces.cpp:461` forwards this signal to `chain::Notifications` clients, including the wallet. An incoming payment in a large batch is not seen until it confirms.
- Consumers also see a gap in `mempool_sequence`.
- `PeerManager`'s own `m_txrelay_index` subscription is compensated by the relay path, which is probably why this went unnoticed.

Fix: keep the signal and drop only the spent-coins cost, for example enqueue one shared batch event, or suppress only when no subscriber at all overrides the callback. Add a test that a subscriber sees all 128 or more.

### B2. Medium, confirmed: production path chosen by a test hook

`store_sig_cache = bool(options.test_between_phases)` (`validation.cpp:4202`).

- Tests that set the hook (`mempool_admission_tests.cpp:568`, `lotus_v2_tests.cpp:809`, `:882`) run the old cache path. Production runs the new one, so those tests do not cover the production path.
- In production, staged signatures are never written to the signature cache, and `Get` is no longer consulted (`:3981-3988`, same in `:3614` for raw batches). Block connection then re-verifies signatures for these transactions.
- This looks like cost rather than a validity problem. The null `cache_entry32` is safe (`lotus_v2/signing.cpp:774`).

Fix: make this an explicit option set the same way in tests and production, and measure block-connect time before deciding to drop the cache.

### B3. Low, confirmed: snapshots above 128 entries are no longer point-in-time

With `entry_tree` null, `EnsureMempoolTxIds` and `EnsureMempoolVectors` (`node/snapshot.cpp:891-896`, `:923`) and `PopulateMiningTemplate` (`:475`) read the live pool lazily. So `mempool_size`, `mempool_sequence` and the template's tip can describe an earlier moment than the data.

- The live view is always newer, so a client replaying from `mempool_sequence` still converges (replay is idempotent).
- A template from an older snapshot is built on a tip that is already stale, so harm is limited.
- Worse in practice: a verbose `getrawmempool` or `getmempoolentry` now copies the whole pool under `mempool.cs` per new snapshot, where it used to read off-lock. This is an RPC-driven admission stall, not a peer one.

Fix: document that these snapshots are not immutable, and rate-limit or cache the copy.

### B4. Low, suspicion: new lock order `mempool_vectors_mutex -> mempool.cs`

`EnsureMempoolVectors` and `EnsureMiningTemplate` hold the vectors mutex and then take `cs` (`snapshot.cpp:905/923`, `:965` then `:475`). I found no `cs -> vectors` path in the callers I read (`rpc/mempool.cpp:499`, `:513`, `rpc/mining.cpp:1513`, `node/mining_pool.cpp:463`, `snapshot.cpp:1148-1181`), but `rpc/blockchain.cpp:1392` I did not trace fully. `EnsureMiningTemplate` is `NO_THREAD_SAFETY_ANALYSIS`, so the compiler cannot check it.

### "Bypass" answers: is it correct at every size, and can a peer drive it?

A peer can trivially exceed both thresholds, so these are the normal paths on any busy node. Existing tests use tiny pools (for example 3 transactions at `txrelay_tests.cpp:1268`) and `REQUIRE(entry_tree)`, so none exercise the large-pool path.

- **`UtxoFastFilter` above 256 entries (`txmempool.cpp:208`): correct.** Every decision now uses authoritative `mapNextTx` (`isSpent`, `GetConflictTx`, `IsSpentFast`, `AcceptSingleTransaction`, `PrepareNativeCrypto`). `MayExistInChainOrMempoolFast`, `IsSpentFast` and `GetUtxoFastFilter` have no non-test callers I could find, so the filter is effectively write-only. Mark and unmark can now be unbalanced, but nothing reads the result. Suggest deleting it.
- **`entry_tree` above 128 entries: correct for all consumers found.** `RelayReconSet` (`net_processing.cpp:4200`), `PopulateMiningTemplate`, both `Ensure*` functions and `PrepareNativeCrypto` all have fallbacks. `CloneChainStateOnly` does not copy `entry_tree`, so readers see null rather than stale data. The 128 crossing forces a full rebuild, which is cheap at that size. See B3 for the cost above it.
- **`LimitSize` early return: correct.** The expiry and size tests match what `Expire` and `TrimToSize` would do.
- **`batch_accepted` fast path:** same result as the old path, which also reported success without re-checking eviction. Only `rpc/mempool.cpp` passes `precomputed_batch`. `v2_protocol_handler.cpp:1898` does not, so its results are unaffected. The `else` at the `it->second` use is reached only when `!fast_accepted`, so no `end()` dereference.
- **`ShortIdBucket`: correct.** Insert, remove and find all handle the single-entry and multi-entry cases.
- **`m_batch_parent_indices` lazy allocation: correct.** The one reader handles empty (`validation.cpp:2124`).
- `mapNextTx.contains` from `PrepareNativeCrypto` is now read off-lock. `radix_map.h:333` looks RCU-based, but I did not verify every write path against it.

---

## `447c4aac77`: fix (tier: shared)

### What each removed lock guarded

- **`cs_main` over inventory selection in `SendMessages`.** No chain or `CNodeState` state is used in that block any more (no `ActiveChain` or `State` in `:11645-11919` at `e91e089f30`). The relevant data has its own guards.
- **`cs_main` over `RefreshRelayInventoryAdmissions`.** This kept admission and removal stable while a suffix was applied. Now nothing does, and the ranks it writes can be stale. That is safe because selection re-reads the live entry and corrects any mismatch before sending (`:11833-11845` at `e91e089f30`), so ranks only affect ordering.
- **`mempool.cs` in `ResolveRelayShortIds`.** Replaced by atomic `SetUnbroadcast` exchange, so only one of this path or `RemoveUnbroadcastTx` in `removeUnchecked` (`txmempool.cpp:322`) can decrement for an entry.

### C1. Low, confirmed: annotations removed with no replacement

`blockSinceLastRollingFeeBump`, `rollingMinimumFeeRate` and `nextEntryId` lost `GUARDED_BY(cs)` for atomics (`txmempool.h:260`, `:262`, `:275`). Writes are still load-then-store, so they are safe only while all writers hold `cs`, and the compiler no longer checks that. `nextEntryId` is the exact reservation-versus-publication hazard from W3-8.

Fix: add `AssertLockHeld(cs)` at each write through a small setter, and comment that readers may be lock-free.

### C2. Low, suspicion: count underflow on `_clear`

`_clear` stores 0 into `m_unbroadcast_count`. If `ResolveRelayShortIds` has already flipped entries, `FinishRemoveUnbroadcastBatch` then subtracts (`txmempool.cpp:1304-1308`) and wraps the `size_t`. The result is that `GetUnbroadcastTxCount() > 0` stays true, costing fast-path skips only. Needs a concurrent `_clear`, and I did not establish that any production path does this while peers are active.

### Checked and correct

- **Fast path at `net_processing.cpp:4488`.** It can advance the cursor past an entry that has a reserved ID but is not published yet, or past a re-admission whose old removal was already counted. Either way the peer's rank stays old until selection corrects it. So ordering may lag briefly, but no announcement is lost. The stale-queue scan and double read of the removal sequence are correct.
- **`m_removal_sequence` coverage.** `removeUnchecked` and `_clear` are the removal paths.
- **Parent routes at `:4389`.** Skipping for local transactions and for `targets <= fanout` is correct: those cases send to all candidates anyway.
- **`GetMinFee` fast path.** Same result as the slow path when no decay applies.
- **Merged `cs_main` scope for block getdata.** No ordering change.

---

## `a5b4951884`: pass (tier: shared)

Checked:

- **`exists` before queueing (`net_processing.cpp:4215`, `:4240`).** `m_tx_tree` is the live tree, not a snapshot, so this is a correct read. A duplicate takes `PrepareTxAdmission` and stops, which is what `QueueTxForAdmission` would have done. `ForceRelay` peers skip the check, preserving forced relay.
- **`is_local=false` in the batch.** Correct: the flag is per-entry, so a newly admitted entry is not unbroadcast.
- **W2-10.** `ProcessTxBatch` keeps its one-pass individual semantics and reject handling. Relay now happens after snapshot publication, which is an improvement.

Low-severity notes:

- **A1.** Reservation is computed from the first `exists` pass, and bodies are queued from the second. A tx removed between the two is held without budget. Bounded by one message; not worth a fix.
- **A2.** Relay now runs after `cs_main` is released. If a tx is evicted inside the batch, `TxRelayIndex::Remove` can run before `AddBatch`, leaving the index reporting HAVE until the epoch rotates. A peer's INVSHORT for it is then treated as known. The drain correctly marks the tx stale, so nothing bad is announced.
- **A3.** `ProcessPackageResult` calls `ProcessValidTx` without the batch, so a package child can enter the queue before earlier batch members. Harmless, because peer queues sort by entry ID.

---

## `703a07c21e`: pass (tier: shared)

Checked:

- **`UpdateRankIfPresent` (`relay_inventory_queue.h:229`).** Same transitions as `SetRank` for existing records, without inserting.
- **`AddBatch`/`AddUnlocked`.** Same idempotence as `Add`, one lock per batch.
- **INVSHORT without `cs_main` (`net_processing.cpp:7305-7345`).** `TooManyAnnouncements`, `ComputeRequestTime` and `ReceivedInv` match `AddTxAnnouncement` at this commit, including `preferred` (no permission clause existed yet, so none was lost). Known-filter handling matches `AddKnownTx`.
- **Lock-free `getEntry` in selection (`:11519`).** Entry ID and modified fee are set before `m_tx_tree.insert` (`txmempool.cpp:177-200`), and only immutable fields are read (`GetEntryId`, `GetSharedTx`, `GetFee`, `GetTxSize`). Different entries in one chunk may reflect different moments, which selection tolerates. This answers the W2-4 concern about metadata publication.

---

## `f8ace4160c`: pass (tier: shared)

Checked: `ForEachEpoch` (`txrelay_index.h:124`) matches `Epochs()` in content and order, with the snapshot pinned for the call. `m_tx_admission_inflight` is never iterated, so `unordered_set` with a salted hasher is safe.

- **F1. Low, confirmed.** Skipping `ForgetShortIdRequests` on results (`net_processing.cpp:5779`, `:5811`) relies on the forget at queue time. A short-id announcement under an epoch that started while the tx was in flight is not in the in-flight map, so it stays registered. If the tx was valid, `:12189`-style cleanup removes it. If it was invalid, we send one needless GETSHORTTX, and the response clears it.
- **F2. Low, suspicion (introduced by an earlier commit, retained here).** Erase uses current epochs (`:3560`), but insert used epochs at queue time (`:3503`), so entries for a rotated-out epoch stay until in-flight empties. Sustained traffic can stop it emptying, giving slow growth of at most the in-flight count per rotation. `emplace` also keeps only the first txid for a colliding key, and the later erase removes it. Fix: store the exact keys inserted per txid.

---

## Earlier design hazards, answered for this code

| Item | Answer |
|---|---|
| W1-9 batch INV/INVSHORT | Partly implemented. Index lookup is authoritative and remains separate from Bloom hints. The index and lock changes were not split as recommended. No false-positive hint decides a request |
| W1-12 per-peer strands | Not introduced. The message thread remains the single consumer, and `g_msgproc_mutex` still serializes `DrainRelayQueue`. New: `txadmit` shares locks with it, see E1 |
| W2-4 live tree reads | Fine for fields read here; see `703a07c21e` |
| W2-10 admission relay batch | Order and individual semantics preserved |
| W3-8 remove cs_main from admission | Not done. Phase C still holds `cs_main`; only post-admission bookkeeping moved out. `nextEntryId` is atomic but assigned under `cs`. The watermark can lead publication, which is tolerated (see `447c4aac77`) |
| W3-9 concurrent Bloom | Not implemented. All filters stay under mutexes, so the generation-rotation hazards do not apply. Peer known filter and pending inventory remain under one `m_tx_inventory_mutex` |
| W3-10 MPSC ring | Not implemented. Still mutex plus vector, so no holes or capacity failure. New wake happens after append, which is the right order. Queue remains unbounded in the same way as before; `targets.empty()` still drops a batch, as before |

---

## Could not determine

- Actual runtime behavior: nothing was built, and neither deadlock was reproduced.
- Whether the root CMake turns the `AlreadyHaveTx` thread-safety warning into an error. It does not in `src/CMakeLists.txt`.
- How much E2 delays block download under a real flood.
- **Pre-existing and outside these commits, worth its own look:** `m_recent_rejects` and `ForgetInvId` are keyed by TxId, and this tree computes separate TxId and TxHash (`primitives/transaction.cpp:300-337`). If TxId excludes witnesses for version 7 transactions, a peer could send a bad-witness copy of an honest transaction and have its TxId rejected until the next tip change, and also clear other peers' announcements (`PrepareTxAdmission` forgets them before validating). I did not read `ComputeTxIdentities` closely enough to confirm it, or check for a witness-specific exemption in the result handling.
