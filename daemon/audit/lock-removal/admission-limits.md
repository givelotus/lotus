# Admission pipeline and limits audit

Scope: `2deccfdbf7`, `f66e475bc1`, `52e34975f9`, `9cfddf4d37`, all ancestors of `origin/archive/merklix-snowball-20261024`.
Read-only source review through Git objects. Nothing was built, run or benchmarked. Any timing below uses an assumed per-operation cost and is labelled as such. Memory figures for the Bloom filter are computed from the constructor formula; other memory figures are estimates.

## Verdicts

| Commit | Verdict | Tier | Reason |
|---|---|---|---|
| `2deccfdbf7` | **hold** | shared | INVSHORT announcements can be swallowed with no recovery request; per-peer limit raised 16x with the global limit unchanged; no tests. |
| `f66e475bc1` | **hold** | shared | Limits raised again; `relay` permission now implies preferred, beyond the existing checks. Bloom, Notify and orphan fast paths are fine and can be split out. |
| `52e34975f9` | **hold** | mixed | 3.5 GiB connection-only memory exposure; 2 peers can fill the queue; full reconciliation disabled by any tracked request; no lock-hold limit. |
| `9cfddf4d37` | **hold** | mixed | Request delays cut 20x and 100x, removing the protection against request-race stalls. Other hunks look right. |

None of the four commits touches a test file (`git show --stat` shows zero under `src/test`, `test/functional` or any `/test/`). So no test in these commits fails without the change. `txadmission_queue_tests.cpp` sets explicit limits, so no existing test pins the defaults either. Nothing here shows the changes were checked.

## Every limit changed

| Constant | Base | 2deccf | f66e | 52e3 | 9cfd | What it protected |
|---|---|---|---|---|---|---|
| `Limits::max_per_peer` | 256 | 4096 | 16384 | 65536 | 65536 | One peer's share of the admission queue, and the point where backpressure starts |
| `Limits::max_total` | 16384 | 16384 | 32768 | 131072 | 131072 | Global queue count |
| `Limits::max_total_bytes` | 64 MiB | 64 MiB | 64 MiB | 128 MiB | 128 MiB | Global serialized bytes; there is no per-peer byte limit |
| Peers needed to fill the count limit | 64 | 4 | 2 | 2 | 2 | Derived |
| `TX_ADMISSION_MAX_BATCH` | 256 | 2560 | 4096 | 4096 | 4096 | Size of one staged batch, so `cs_main` hold time |
| `m_tx_admission_retained_budget` | 64 MiB | | | 128 MiB | | Decoded SHORTTX bodies held outside the queue (global) |
| `m_tx_inventory_known_filter` | 50000 | | | 350000 | | Per-peer memory |
| `MAX_SELECTION_CHUNK` | 256 | | 4096 | | | Refs and lookups per inner selection pass |
| `DEFAULT_TXRELAY_RATE_MAX` | 250k/s | | 500k/s | | | Per-peer announcement rate |
| `SHORTID.max_peer_request_in_flight` | 5000 | | | | 8192 | Threshold for the overloaded penalty |
| `SHORTID.nonpref_peer_delay` | 200 ms | | | | 10 ms | Lets preferred peers announce first |
| `SHORTID.overloaded_peer_delay` | 2000 ms | | | | 20 ms | Penalty for peers sitting on requests |

Unchanged but relevant: `max_peer_announcements` 100000 (short ID), `getdata_interval` 2 s, `TX_REQUEST_PARAMS`, `DEFAULT_TXRELAY_TICK` 10 ms, `MAX_RELAY_MESSAGES_PER_WINDOW` 1000/s, `DEFAULT_MAX_PEER_CONNECTIONS` 1024.

All queue limits are compile-time, with no option. The `ecashd` commit pinned by this repository's `HEAD` (`73ed9c43ed`) still has 256/16384/64 MiB, batch 256, filter 50000, rate 250k and the 5000/200/2000 short-ID values.

The message of `52e34975f9` says "raise shortid inflight limit", but that commit leaves `SHORTID_REQUEST_PARAMS` at 5000. The change is in `9cfddf4d37`.

---

## `2deccfdbf7`: pipeline SHORTTX/INVSHORT, per-peer limit 4096. **hold**, tier `shared`

The code is the negotiated short-ID path that `ecashd` already carries, plus the queue. No V2 types, no wire change.

### Confirmed

**A1. High. INVSHORT announcements are swallowed while a transaction is in flight, and nothing requests it again if admission does not succeed.**
`net_processing.cpp:7409-7414`, map filled at `:3501`. Still present at `9cfddf4d37` `:7759-7765`.
- A short ID that matches `m_tx_admission_inflight_shortids` skips `ReceivedInv`. The peer's txid goes into its known filter and is removed from what we would announce to it.
- `PrepareTxAdmission` (`:5854`, existing code) has already run `ForgetInvId` on the short-ID keys of every announcer before the verdict, for any body, solicited or not.
- So once a body is queued, no short-ID announcement for that transaction exists, and later ones are dropped.

Scenarios:
1. Sender disconnects. Peer A sends T (unsolicited TX is allowed), then closes. `ThreadTxAdmission` sees `fDisconnect` and returns `DROPPED` (`9cfddf4d37` `:3500-3505`, `:3651`). All short-ID announcers of T have been forgotten and none is retried. There is no attacker requirement beyond having heard T. With no attacker at all, an honest high-rate peer crashing with a deep queue loses up to `max_per_peer` transactions for this node: 256 at base, 65536 at `52e34975f9`.
2. V2 only, and more serious. `TxId` omits native witnesses (comment at `9cfddf4d37` `validation.cpp:2659`). A peer sends T' with T's TxId and a bad witness. T' fails, `ProcessInvalidTx` adds the TxId to `m_recent_rejects` (`9cfddf4d37` `:6057`, unconditional for this failure class), and honest announcements were forgotten or swallowed. T is blocked until the next tip resets the filter. The reject-filter half predates this commit; the swallow removes the remaining honest announcements. The attacker is punished per connection, but needs only one body per censored transaction.

Recovery is only an Avalanche poll, a block, a full-TxId INV, or full reconciliation. `52e34975f9` disables the last under load (C3).

Fix: while in flight, record the announcement rather than dropping it: track `req_key` in `m_txrequest` without making it requestable, or keep a per-key announcer list released on any non-`VALID` verdict and on `DROPPED`. Do not forget short-ID announcements in `PrepareTxAdmission`; forget them only on a `VALID` verdict. For V2, do not add witness-committing failures to a TxId-keyed reject filter.

**A2. High. Per-peer limit raised 16x with the global limit unchanged, removing the isolation between peers.**
`txadmission.h:99-100`. Peers needed to fill the count limit go from 64 to 4, and to 2 by `52e34975f9`.
- Round-robin `TakeBatch` still bounds *service* share, but not *admission to the queue*. Once `m_count == max_total`, `HasRoom` fails for an honest peer, whose bodies go to `held_txs` and whose reads stop. Each freed slot goes to whichever peer's `ProcessMessages` turn comes first.
- A flooder delivers up to 4096 per SHORTTX message (with a `sendcmpct(1)`, see below), against an honest peer's few. So the flooder claims most slots after each batch.
- The `txadmission.h` class comment ("a flooding peer cannot delay others by more than one slot per turn") is no longer accurate for queue entry.

Unsolicited SHORTTX is reachable by anyone: `v2_protocol_handler.cpp:1759-1763` treats `m_bip152_highbandwidth_from` as opt-in, and `SENDCMPCT` with `hb=1` sets it directly from the peer (`net_processing.cpp:7825`). This predates these commits, but it makes the new per-peer depth reachable with no solicitation.

Worked numbers at `52e34975f9` (the end state; the limits table above has the history):
- One peer: 65536 entries. At 4096 per message, that is 16 messages, each of at most 2 MiB. With 60-byte transactions only about 4 MB of accounted bytes, so the byte limit does not help.
- Two peers: the whole queue.
- Memory outside accounted bytes, estimated at 1 KiB per decoded transaction object (not measured; `sizeof(CTransaction)` plus inputs/outputs not determined exactly): 131072 x (1 KiB + 48-byte item + deque overhead) is about 140 MiB, against about 18 MiB at base. Plus `m_tx_admission_inflight` (about 8 MiB) and the short-ID map at 2 epochs (262144 entries, about 23 MiB).
- Worst total with bodies: 128 MiB queued + 128 MiB retained + about 170 MiB overhead, about 430 MiB, against about 150 MiB at base.
- No penalty for a sustained version: transactions that spend real UTXOs and fail the fee check return `TX_MEMPOOL_POLICY`, which does not punish (`9cfddf4d37` `net_processing.cpp:3340`). A script-invalid flood does get punished, but only when its verdict is handled.

Fix: revert to `max_per_peer` at most `max_total / 64`, or make per-peer capacity dynamic (a peer may exceed its fair share only while the queue is below a low watermark). Add a per-peer byte limit. Reserve global headroom so one peer cannot take the last slots.

**A3. Medium. Admitting SHORTTX while verdicts are pending breaks per-peer ordering on the serial fallback, and removes the implicit one-response-at-a-time limit.**
`:10330-10337`. Before, a SHORTTX waited for `m_tx_admission_pending == 0`. Now it does not.
- If `TryReserve` fails, `ProcessShortTxResponse` runs `ProcessSingleTx` for each body on the message thread (`9cfddf4d37` `:4527-4533`), overtaking the same peer's earlier queued transactions. A child overtakes its parent, gets `TX_MISSING_INPUTS` and goes to the orphanage. It recovers, at a cost in orphan slots.
- Forcing that fallback needs the retained budget pinned. A wire message is at most 2 MiB, and a peer holds one response at a time (`held_txs` non-empty returns before polling), so pinning 128 MiB takes 64 peers. That is available with 1024 connections. The result is 4096 script-checked admissions per message, under `g_msgproc_mutex` and `cs_main`, on the thread that serves all peers.
- W2-10 asked for exactly this order and error semantics to be preserved. They are preserved on the queue path, not on this one.

Fix: in the fallback, hold the message as `m_tx_admission_held_msg` until pending is zero. Better, apply TCP backpressure rather than validating serially on the message thread.

**A4. Medium. Short-ID map leak across epochs.**
Insert at `:3501` uses the epochs at queue time; erase at `:3557` uses the epochs at verdict time. An epoch rotation in between leaves the old-epoch key. Only `clear()` when the in-flight set is empty reclaims it.
- A flooder can keep the in-flight set non-empty indefinitely, and sustained honest load may too.
- Bound per rotation: in-flight count x 1 key. At 131072 in flight and about 88 bytes per node, that is about 11.5 MiB per block. Worst case with 2-minute blocks is about 345 MiB/hour, with no upper limit.
- Stale keys are otherwise harmless, since INVSHORT for an unindexed epoch is rejected first (`:7732`).

Fix: store the key list with the in-flight item and erase exactly those keys, or key the map by epoch and drop the whole epoch on rotation.

**A5. Low. Grinded short-ID collisions.**
`emplace` does not overwrite, and erase by key removes the entry for both transactions. The code's own comment (`ShortIdFor`) puts a collision at about 2^32 SipHash operations with a public epoch key. A collision here marks the wrong txid as known to the announcer and skips a request. The effect is limited by the existing "delayed, not lost" recovery, but that recovery is weakened by A1 and C3.

**A6. Medium. Head-of-line delay for non-pipelined messages grows with queue depth.**
`:10337-10342`. PING, HEADERS, CMPCTBLOCK, BLOCK, GETDATA and others wait until that peer's pending count reaches zero. That wait is now up to 65536 verdicts rather than 256. Only the peer's own messages are delayed, so this is a harm to honest bursty peers rather than an attack. Illustrative only, assuming 30k admissions/s shared across 10 active peers (3k/s per peer): 256 takes 85 ms, 65536 takes about 22 s. An honest outbound peer that relays a burst then delivers its block announcement that late.

Fix: exempt block-related and ping messages from the hold, or limit depth so the hold stays in the millisecond range.

### Checked and correct
- `MempoolToJSON` parallel path produces the same array contents and order. `setStr` on separate elements has no sharing.
- Moving the known-filter update after the request loop is safe, and in-flight hits are appended before it runs.
- Producer fencing: `Assert(pushed)` still holds, since `g_msgproc_mutex` serializes producers and the consumer only frees space. This is not remotely triggerable.
- FIFO per peer is preserved on the queue path, so same-peer parent and child stay in order there.
- `++missing` before the `TooManyAnnouncements` break overcounts by one. Metric only.

---

## `f66e475bc1`: whitelist bypass, batched notify, fast paths. **hold**, tier `shared`

No new V2 types. The `snapshot.cpp` context uses `input.nFlags`, which `ecashd` does not have, so the hunk needs porting; its logic is generic. Split: bloom, notify, `HasOrphans` and `AlreadyHaveTx` reorder are fine. Hold the limit raises and the whitelist change.

### What grants the bypass, and can a default config grant it?

- The bypass tests `HasPermission(NetPermissionFlags::Relay)` for both `TX_REQUEST_PARAMS` and `SHORTID_REQUEST_PARAMS`. `HasFlag` is a bit test, `Relay` is non-zero, and `ForceRelay` includes `Relay`.
- **A default config grants it to nobody.** Permission flags start at `None`, and only `-whitelist`, `-whitebind`, `-p2pwebsocketpeer` keys or shared-HTTP listener permissions add to them (`net.cpp:700-719`, `:1843-1868`).
- **A bare `-whitelist=<range>` or `-whitebind=<addr>` does grant it**, because `Implicit` plus the default `DEFAULT_WHITELISTRELAY = true` adds `Relay` (`net.cpp:708-714`). `Implicit` also adds `NoBan`. `noban@` alone does not grant `Relay`.
- Risky but common configs: `-whitelist=127.0.0.1` on a node whose Tor or proxy inbound arrives on localhost, and `-whitebind` on a publicly reachable port. In both, anonymous peers get the bypass. Those configs were already unsafe, as the next finding explains.

### Confirmed

**B1. Low to medium. `relay` permission now means "preferred", which changes the trust model and is undocumented.**
`net_processing.cpp:2714-2720`, `:2782`, `:7449` (at `9cfddf4d37`: `:938-941`, `:1493-1496`, `:7753-7756`).
- Before: `Relay` skipped the announcement cap and the overloaded penalty. Preference came from `fPreferredDownload` (`9cfddf4d37` `:7353`): outbound or `NoBan`, not addr-fetch, and can serve blocks.
- Now: any `Relay` peer is preferred, so it has zero delay and takes priority over non-preferred candidates.
- What actually changes depends on how the permission was granted:

| Grant | Before | Now |
|---|---|---|
| Bare `-whitelist` or `-whitebind` (`Relay` + `NoBan`) | Preferred if it advertises block serving, which a peer can claim freely | Also preferred if it advertises nothing, or is an addr-fetch connection |
| Explicit `relay@` or `forcerelay@` without `noban` | Not preferred when inbound | Preferred |

- So an anonymous peer in the Tor/localhost or public `-whitebind` configs could already get preference by setting a service bit. This commit removes that small hurdle, and extends preference to the narrower `relay@` grant, which an operator would reasonably read as being about relaying only.
- Failure: such a peer is first choice for each transaction it announces and has no announcement cap. Each withheld request costs 2 s for short IDs and **60 s for full-TxId requests**, with no penalty. Several such peers multiply the stall.
- `relay`'s description in `NET_PERMISSIONS_DOC` and the `ComputeRequestTime` doc comment do not mention this.

Fix: remove preference from `Relay`; add an explicit permission if operators want it. If retained, require `NoBan` too and document it.

**B2. Low to medium. `FinishRemoveUnbroadcastBatch` skips the snapshot publish when the pool has more than 64 entries.**
`txmempool.cpp:1371`. The live flag and count are updated but the published snapshot is not, and `MarkSnapshotEntryChanged` is never called for these entries.
- `getmempoolentry`/`getrawmempool verbose` use `e.unbroadcast` (`rpc/mempool.cpp:474`), and `getmempoolinfo` uses `snap.unbroadcast_count` (`:847`).
- Above 64 entries these report stale values. The per-entry value stays wrong until that entry is otherwise republished (if a snapshot reuses unchanged entries; see "could not determine").
- 64 is an arbitrary threshold, so tests with small pools (such as `mempool_unbroadcast.py`) will not catch it.

Fix: keep the batched publish, but mark entries changed and defer flushing to the next publish rather than returning early.

**B3. Low. `AddUnbroadcastTxBatch` skips `MarkSnapshotEntryChanged` when deferred.**
`txmempool.cpp:1304`. It is safe only for entries added in the same defer scope (`addUnchecked` marks those). An entry added earlier and flagged here under a defer would not be republished. After `9cfddf4d37` the RPC path no longer calls this function. Remove it or mark unconditionally.

**B4. Medium, limits.** See A2 and C2: `TX_ADMISSION_MAX_BATCH` 4096 at `:94`, 16384/32768 at `txadmission.h:99-100`.

### Suspicion

**B5. Low to medium. `DEFAULT_TXRELAY_RATE_MAX` 500k/s applied to stock ABC peers.**
`net_processing.h:111`. `TxRelayTickBudget()` at `:12003` does not depend on negotiated features. With a 10 ms tick the budget is 5000 per tick (40000 with 8-tick catch-up, against 2500/20000 before). As 36-byte INV entries that is up to 18 MB/s per stock peer, under load. A stock peer tracks about 5000 announcements per peer and silently ignores the excess, so relay is wasted rather than broken. This is wire-compatible but should be limited for peers without short IDs. Whether a real mempool sustains this rate was not determined.
Also, `:11994` compares against the default, so an operator who explicitly set the old default `-txrelayratemax=250000` silently loses catch-up.

### Checked and correct
- **Bloom fast path** (`bloom.cpp:233,251,271`): correct. `m_has_entries` is set on first insert and cleared only by `reset`, under the caller's existing lock. Skipping `std::fill` is safe since no bits have been set. This is a plain flag, not the rejected lock-free rotation from W3-9; retention is unaffected.
- **`Push(notify=false)` + `Notify()`**: no lost wakeup, since the push happens under `m_mutex` before notify, and the 100 ms timed wait covers any exception between the two.
- **`AlreadyHaveTx` reorder**: same boolean result, and the tip-reset still comes first. Single call in `PrepareTxAdmission` removes a duplicate.
- **`HasOrphans`/`TxPool::Empty`**: every mutation of `m_pool_txs` goes through `AddTx` or `EraseTxNoLock`, which both update `m_size`. Orphans are added under `g_msgproc_mutex`, the same as `ProcessValidTx`. A stale result on the admission thread in `skip_at_commit` gives the same outcome as losing the race.
- **`MAX_SELECTION_CHUNK`**: total lookups remain bounded by the tick budget, and only chunk size changed. Pass.
- **`EnsureMempoolTxIds`**: sorted at this commit, under the same mutex. Pass.

---

## `52e34975f9`: batching and limits. **hold**, tier `mixed`

Split:
- **Shared:** `amount.cpp`, `tx_check.cpp`, `net_processing.cpp`, `txadmission.*`.
- **V2:** `TryVerifyV2ConfirmedFastPathFromSmt`, `NativeAdmissionPreparation` changes, `PrepareFastConfirmed`, and the `submitrawtxbatch` fee-hysteresis response path (`lotus::v2::FeeHysteresisController`).
- **Generic, in `validation.cpp`:** the locking restructure of Phase C. It needs separate review from the fast path because it also affects legacy transactions.

### Confirmed

**C1. High. Known filter costs 3.6 MiB per peer, for connecting alone.**
`net_processing.cpp:516`. Computed from the `CRollingBloomFilter` constructor:

| nElements | Hashes | Filter bits | Words | Per peer | At 1000 inbound |
|---|---|---|---|---|---|
| 50000 | 20 | 2,156,646 | 67,396 | 0.51 MiB | 0.50 GiB |
| 350000 | 20 | 15,096,522 | 471,768 | 3.60 MiB | **3.51 GiB** |

- `DEFAULT_MAX_PEER_CONNECTIONS` is 1024. The filter is built in `SetTxRelay` when a peer's VERSION asks for relay (`:7335`), and `vector::resize` zero-fills, so pages are committed.
- Attack: about 1000 TCP connections, each sending a VERSION, with no transactions. The cost to the node is 3.5 GiB, and stock ABC peers can do it. Eviction only replaces one connection with another.
- The filter does not even cover what it was enlarged for: at the new 500k/s rate, 350000 entries is 0.7 s of announcements.

Fix: keep 50000 on the shared tier. Size on demand (start small and grow for peers with real sustained traffic), or use one shared structure rather than one per peer. Add a global budget.

**C2. High. No limit on cs_main/pool.cs hold time per batch.**
`validation.cpp:4915`, `:5004`; batch size `net_processing.cpp:94` (f66e).
- Before, `pool.cs` was taken briefly in Phase C and `cs_main` was held across at most 256 transactions. Now both are held across up to 4096, including `FlushStateToDisk(PERIODIC)` at `:5004` and `pool->check`. `TakeBatch` has no byte limit.
- Legacy Phase A is the same: `PrepareStaged` holds `cs_main` and `pool.cs` for the batch (`9cfddf4d37` `validation.cpp:4199-4263`).
- Attack, with no penalty: transactions spending real, distinct UTXOs and paying below the minimum relay fee. They need the coin lookups and then return `TX_MEMPOOL_POLICY`. I did not trace the exact check order for every path, so the lookup count is an upper bound.
- On `lotusd`, with `MAX_V2_TX_INPUTS` 256: 4096 x 256 is 1,048,576 coin lookups per batch, 16x the 65,536 at base, and about 43 MiB, within the byte limit. Illustrative: 1 us per cached lookup is about 1 s; 20 us per disk miss is about 21 s.
- On the shared tier there is no input cap, only the 100 KB standard size. About 1300 x 2400 inputs is 3.1M lookups per batch at 128 MiB, against 614k at base, so 5x.
- During this, block validation, RPC and every `cs_main` user wait. W2-11 said: "byte/transaction/hold-time limits... Queue capacity alone is not the design." Those limits are not present, though the metric (`mempool_admission_lock_hold_seconds`) is.

Fix: limit each batch by transactions **and** total inputs **and** bytes, chosen from measured hold time. Release and re-take locks between sub-batches. Move `FlushStateToDisk` outside `pool.cs`.

**C3. High. Full reconciliation is disabled while any request is tracked or any transaction is in flight.**
`net_processing.cpp:11484` (`9cfddf4d37` `:11501-11503`). The gate is global, not per peer: `m_tx_admission_inflight.empty() && TxRequestSize() == 0 && (...)`.
- On a node with real traffic, the tracker is rarely empty. Under load it is effectively never empty.
- Attack: one peer sends a full-TxId INV for an unknown txid every 60 s and never answers. Each announcement stays `REQUESTED` for the 60 s `getdata_interval`, so `m_txrequest.Size()` stays above zero and `m_full_recon.Tick` is disabled for all peers. Short IDs do the same with one announcement every 2 s.
- `Tick` is not only the offer. It also sends `pending_control`, drives paged fetch and admission, and enforces `IDLE_LEASE` (60 s) and `ABSOLUTE_LEASE` (30 min). Skipping it stops sessions in progress and stops expiring leases, so pinned snapshots stay pinned until a tick finally runs. That counts against the `full-recon pinned snapshot budget`.
- Full reconciliation is the backstop for missed transactions (A1), so it is off exactly when it is needed. `-txreconfull` defaults on.

Fix: remove the gate. If cost is the concern, gate only `StartOffer` on load, with a deadline so it cannot be starved, and always run lease expiry, `pending_control` and in-progress sessions.

**C4. High, limits.** 65536/131072/128 MiB at `txadmission.h:99-101`. See A2.

**C5. Medium. One bad signature pushes the whole batch to single-threaded verification, now at 16x the size.**
`validation.cpp:4855-4880`. If `combined_sigs.VerifyAll()` fails, each prepared transaction is re-verified one at a time on the admission thread. The pattern predates this commit; the batch size changed. Round-robin guarantees an attacker a slot in each batch, so one bad transaction per batch suffices. With at most 16 inputs on the fast path: 4096 x 16 x an assumed 50 us is about 3.3 s per batch (256 at base: about 0.2 s). The attacker is punished and disconnected when the verdict is handled, so each identity gets few rounds, but connections are cheap. This runs outside `cs_main`, so it affects throughput rather than the rest of the node.

Fix: bisect the batch rather than falling back to linear verification, and parallelize the fallback.

**C6. Medium, fixed by the next commit.** `net_processing.cpp:4477`. `clear_limit` stops clearing at the first held transaction, but `continue`-path items after it have `request_cleared=true`. Their requests stay `REQUESTED` until the 2 s expiry. `9cfddf4d37` corrects this with `cleared_indices`. Squash.

### Suspicion

**C7. Low. Unlocked reads in Phase B.** `native_pool->mapNextTx.contains()` at `validation.cpp:4785` and `exists()` run with no `pool.cs`. `mapNextTx` is a `RadixTreeMap` with no `GUARDED_BY`. If that map's reads are safe alongside writers, the logic holds: `pool_size`/`GetTransactionsUpdated` are read before Phase B and compared under the lock, so any concurrent change voids `pool_unchanged_since_phase_b` and full checks run. Radix read safety itself is for the lock-removal reviewers; I did not establish it.

**C8. Low. Guard downgrade.** `MatchesContext` in fast mode compares only `GetId()` (`:351`), and the code's own comment warns "TxId omits native witnesses". Harmless today, since `checks[i]` belongs to `txs[i]`, but the guard no longer detects a mismatch. Use `GetHash()`. The chain ID check is dropped too; the snapshot's context already covers it.

### Fast path: what I checked

No consensus defect found in the V2 fast path, but I reviewed it for admission correctness rather than proving equivalence with `Prepare()`.
- `TryVerifyV2ConfirmedFastPathFromSmt` covers the `CheckTransactionCommon` rules in stricter form: output cap, size, value range, totals, null prevout, duplicates (O(n^2) on at most 16). Also maturity and expiry.
- Skipping coin checks is justified: `MatchesContext` pins tip hash, height, MTP and flags, so the snapshot's UTXO root is the current tip's.
- Duplicates are caught: `batch_has_duplicate_txid` and `_prevout` void the skip, intra-batch parents disable the fast path, and live `mapNextTx` catches a transaction already in the pool even if `entry_tree` is stale.
- `fast_skip_commit_check` skips `AlreadyHaveTx`, including `m_recent_rejects`, only when the pool is unchanged. A transaction rejected between queueing and commit could be retried; validation still decides. Low.
- Behaviour depends on `pool.size() > 6400` in several places. That is a magic number with no test on either side.

### Checked and correct
- **RPC format:** the raw `submitrawtxbatch` path emits the same keys in the same order as the object path (`txid`, `required_cu`, `required_fee_sats`, `recommended_sdk_fee_sats`, `allowed`, `size`, `fees{base, effective-feerate, effective-includes}`). `size` equals `virtual_size` for non-negative values. `append_amount` matches `Amount::operator UniValue`. The raw path needs at least 64 transactions and all accepted.
- **Limit of raw arrays:** `setRawArrayStr` leaves `values` empty, so `size()` is 0. Fine for JSON output; any in-process caller that indexes the result would see an empty array. None found in the RPC itself.
- **`Amount::operator UniValue`:** same output for `decimals > 0`. With `decimals == 0` it would emit `"1."`; the old code printed a digit there. Currencies in the tree use non-zero decimals (values not exhaustively checked).
- **`tx_check.cpp:38`:** `GetTotalSize()` is `m_serialize_size`, computed in each constructor I read from wire length or `SizeComputer` (`transaction.cpp:454, :465, :743`). Equal to `GetSerializeSize` provided wire parsing rejects non-canonical encodings, which `ReadCompactSize` does. This is consensus code, so it deserves a focused test.
- **`TakeBatch` single-peer path:** bookkeeping correct.
- **`track_routes`:** with `targets <= fanout`, every target is picked, so no route is needed. On a later increase in peers, a child's parent may lack a route for one transition. Harmless.
- **`defer_shortid_erase`:** correct; the only defect is A4.
- **Parallel sections:** `worker_collectors[tid]` per participant; `checks[i]` per index; signature cache written after join.

---

## `9cfddf4d37`: request delays, parallel txids, streamlined batch. **hold**, tier `mixed`

Split:
- **Shared:** `SHORTID_REQUEST_PARAMS` (as policy, if wanted), `cleared_indices` and held-drain, `core_memusage.h`, `primitives/transaction.h` cache, `radix.h`, `AddUnbroadcastItersBatch`.
- **V2-tree only:** `snapshot.cpp` uses `m_tx_tree`, absent from `ecashd`; `validation.cpp` `m_v2_pre_coins_matched`.
- Hold only the first hunk. The rest can proceed after squashing.

### Confirmed

**D1. High. The request-delay cuts remove the protection that the delays exist to provide. An inbound peer can win requests and stall transactions at almost no cost.**
`net_processing.cpp:224-231`.

The design (`invrequest.h`): "An attacker that races the network will be unsuccessful if all preferred connections are honest." That holds only if the non-preferred delay exceeds the lag of an honest preferred announcement.
- **10 ms is one relay tick** (`DEFAULT_TXRELAY_TICK`), and below typical WAN round-trip time. An honest outbound peer announcing the same transaction cannot normally arrive inside it. Once the attacker's announcement passes `reqtime`, it is requested, and nothing else is requested for that key until expiry.
- **Stall per win: 2 s** (`getdata_interval`). There is no penalty for not answering.
- **Overloaded penalty is gone in practice.** Old: at 5000 in flight, the attacker's `reqtime` was +2200 ms, so honest peers won. New: at 8192 in flight, +30 ms, so the attacker still wins.

Worked numbers for one inbound peer:
- Old: at most about 2500 tx/s stalled (5000 per 2 s) before losing nearly every race, and only for transactions honest preferred peers delivered more than 200 ms later than the attacker.
- New: the first 8192 per 2 s at +10 ms, and beyond that still only +30 ms. Effectively every transaction the attacker hears first, with a +2 s delay each.
- With at least one honest preferred announcer, the second attempt goes to that peer, so the stall is about one interval. With no preferred announcer, k attacker peers give about k x 2 s on average, up to the attacker's connection count. Up to about 1000 inbound slots are available by default, though a real network would normally have honest non-preferred announcers among them, so selection is random among candidates.
- Attacker cost: 8 bytes per short ID, no transaction bodies, no misbehaviour score.
- Multiplied across hops, relay latency rises for everything that passes through nodes under attack.

Effect on privacy: **announcement timing is not changed by any of the four commits** (tick and trickle are untouched, apart from the rate budget), so origin-inference from INV timing is unaffected. The narrower effect is faster probing: an inbound peer can test mempool membership by sending an INVSHORT and watching for a GETSHORTTX, now in 10 ms rather than 200 ms. The in-flight map also makes in-flight state observable. Low.

Also, 8192 in flight can exceed one 4096-entry GETSHORTTX, so requests are split across messages (handled at `:12428`). `FilterRequestedShortTxResponse` handles this through the tracker. Fine.

Fix: restore 200 ms and 2000 ms as defaults on all tiers. If low-latency relay is required on a trusted cluster, use an explicit opt-in option or a `-whitelist` flag rather than changing the public default. Any lowering should be justified by a measured distribution of honest preferred-announcement lag, and an adversarial test where a withholding inbound peer races an honest outbound peer. A withholding penalty (reduce preference for peers whose requests time out) would make lower delays more defensible.

### Suspicion

**D2. Low. `getrawmempool` reads the live tree, not the snapshot.**
`snapshot.cpp:892-913`. The live-tree branch came from `b8f43cdb8b`; this commit adds the sharded form. The result can be newer than `snap.mempool_sequence` returned next to it. A client that replays notifications after the returned sequence sees idempotent adds, so this seems benign, but the `ChainAndMempoolSnapshot` is no longer an immutable cut, and the list is cached on the snapshot once built. Transient memory: `16 x (N/14 + 64)` TxIds is about 1.14N x 32 bytes (10M transactions is about 366 MiB), retained as about 320 MiB until the snapshot is replaced. RPC-driven only. Ordering: the `std::sort` was removed before this commit (in `b8f43cdb8b` or `6a1406992b`, not separately audited); this commit keeps radix order.

### Checked and correct
- **`forEachTopChildBorrowed`:** `CHILD_PER_LEVEL` is 16 (`BITS = 4`), matching 16 shards. The root-leaf and empty cases are handled. `RCULock` is taken per worker; the leaf lives under RCU while borrowed. `GetTxId()` is immutable. Lifetime rests on the RCU cleanup semantics, which I did not trace to the release path.
- **Executor:** concurrent or recursive submissions run on the caller, so holding `mempool_vectors_mutex` across `Run` cannot deadlock against the dispatcher.
- **`mark_unbroadcast`:** `SubmitPackage` at `validation.cpp:3361` is the only success route in `AcceptRawTxBatch`, so no accepted batch misses it. `size_before_limit` comparison protects `batch_iters` from dangling after eviction. Equivalent to the old condition.
- **`cleared_indices` and held-drain clearing** (`:4477-4516`, `:10632-10658`): correct, and fixes C6. Items returned as held are not cleared. Clearing after `PrepareTxAdmission` is safe under `g_msgproc_mutex`.
- **`RecursiveDynamicUsage` cache:** `CTransaction` is immutable, relaxed atomic is fine, zero is never cached, and copies don't exist.
- **`m_v2_pre_coins_matched` skip at `:3309`:** skips only script-cache insertion. Block validation re-verifies. Performance trade, not a correctness issue.

---

## Hazards from the earlier reviews, answered for this code

| Item | Answer |
|---|---|
| **W1-6** parallel SHORTTX decode | Not changed here, and no speedup claim is made. Decode still runs on the message thread, before the rate limit (`v2_protocol_handler.cpp:1721` before `:1736`), and a malformed message costs only a rate-limit count. A3 increases how often it is reached. |
| **W2-10** batch completion, staged SHORTTX | Verdict order and relay order hold on the queue path. Not held on the serial fallback (A3). `DROPPED` plus forgotten announcements is a real loss path (A1). Atomic-versus-individual semantics: staged commit stays per-transaction. |
| **W2-11** group commit | "Queue capacity alone is not the design" describes what these commits do. Fairness: service only, not entry (A2). Byte limit: global only, none per batch or per peer. Transaction limit: raised. Hold-time limit: none (C2). Completion ordering: preserved. |
| **W3-10** MPSC relay ingress | No fetch_add ring exists in this code; the hazards (holes, reuse, full-drop, wake-before-publish) do not arise. The admission queue stays mutex-based and lossless: full leads to held then TCP backpressure. Notify follows publication. `DrainRelayQueue` stays a single consumer under `g_msgproc_mutex`. Overflow behaviour unchanged. |
| **W3-9** Bloom (network-queues review) | `m_has_entries` is a plain flag under the existing lock; no rotation race. Retention, false-positive rate and capacity semantics unchanged. But the review said to measure before changing filters, and C1 changes capacity 7x with no measurement or memory limit. |

## Compatibility with stock Bitcoin ABC

No wire format changes in any of the four commits. Short-ID messages stay behind `sendinvshort` negotiation, so stock peers never see them, and consensus rules are unchanged. `tx_check.cpp` and `amount.cpp` should produce identical results.

But stock peers are subject to the new local limits, and can exploit them with ordinary messages: C1 (filter, VERSION only), A2 and C2 (queue and batch, `tx` only). These are policy decisions that should not be defaults on the shared tier:

| Change | Shared-tier default |
|---|---|
| Queue limits, batch size, retained budget | Keep base values, until a dynamic design and measured limits exist |
| Filter 350000 | Keep 50000 |
| Short-ID request delays | Keep 200/2000 ms |
| `Relay` implies preferred | Off |
| `DEFAULT_TXRELAY_RATE_MAX` | Keep 250k, and limit further for peers without short IDs |
| Full reconciliation gate | Remove |
| `MAX_SELECTION_CHUNK`, Bloom fast path, notify, `HasOrphans`, `AlreadyHaveTx` reorder, `RecursiveDynamicUsage` cache, `TakeBatch` fast path | Safe to adopt |

## Tests that should exist

None of these exist today, and each should fail on the current code:
1. Sender disconnects with a queued body; an honest short-ID announcer is still fetched (A1).
2. Bad-witness copy of a V2 transaction; the honest version is still admitted (A1).
3. A withholding inbound peer racing an honest outbound peer; delivery from the outbound peer within a bound (D1).
4. Two flooding peers and one honest peer; the honest peer's admission latency is bounded (A2).
5. Filter memory at max peers, against a budget (C1).
6. Full reconciliation progresses while `TxRequestSize() > 0` (C3).
7. Epoch rotation with in-flight items; the short-ID map returns to empty-equivalent size (A4).
8. Batch lock-hold time against a limit, with real UTXOs (C2).
9. `getmempoolentry` `unbroadcast` after short-ID fetch, with more than 64 pool entries (B2).
10. Whitelisted peer with no `NoBan` is not preferred (B1).

## Could not determine

- Actual timings and admission rates. Nothing was run; timing figures are illustrative and labelled.
- Exact `sizeof(CTransaction)` and allocation per decoded transaction; the 1 KiB figure is an estimate.
- Whether existing functional tests pass at these commits. `p2p_tx_relay_invshort.py` has no timing constants I could find that pin the old delays, and `test_framework/p2p.py` `NONPREF_PEER_TX_DELAY = 2` already disagrees with the tree's 200 ms.
- `RadixTreeMap` and RCU read safety alongside writers (C7, D2), left to the lock-removal reviewers.
- Whether `PublishMempoolSnapshot` reuses unchanged entries in every mode, which sets how long B2's stale per-entry flag lasts. Large pools appear to bypass `entry_tree` since `b8f43cdb8b`, and that path reads live entries.
- Full equivalence of the V2 fast path and `Prepare()`, and all later stages in `AcceptRawTxBatch` for workspaces with empty `m_resolved_inputs` after the `PreChecksBatch` early return. I traced the sig-check skip at `:3097`, not every later reader.
- Real-world rate at which honest preferred announcements lag, which sets how often D1's race is won without any special positioning.
