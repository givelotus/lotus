# Validation concurrency audit: merklix-snowball series

Scope: `daemon/lotusd`, commits d9e932b64f, 0cb9f3933b, 40de4ece63, 2be6acfcc7, 5e21887803, e7054d87a7, 6eb8e0c15a, 6a1406992b, 7dc7be76bb.

The requested ref `origin/archive/merklix-snowball-20261024` does not exist locally. The commits were reached by hash; they are ancestors of `origin/snowstorm/rateless-fountain`.

Method: code reading only, with read-only git. Nothing was compiled or run. "Confirmed" means the path was traced through the code, not reproduced. File:line is at the named commit; where a commit is not named, it is 7dc7be76bb.

## Summary

| Commit | Verdict | Tier | Main reason |
|---|---|---|---|
| d9e932b64f | pass | shared | Sharding keeps key and budget. Coin helper is unused off cs_main. |
| 0cb9f3933b | fix | mixed | Lock bypass enforced only by comment; undoes d9e9's purpose. |
| 40de4ece63 | fix | mixed | Bad-signature re-verify cost; filter false-negative; no tests. |
| 2be6acfcc7 | pass | mixed | No defect found. No tests. |
| 5e21887803 | fix | v2 | Logic checks out and fixes a real divergence, but consensus code has no differential test. |
| e7054d87a7 | fix | mixed | Spent-coin opt-out enables dropped notifications; prewarm not gated on subscribers. |
| 6eb8e0c15a | fix | mixed | Reused verdict compares outputs only; lock-point logic duplicated without a test. |
| 6a1406992b | fix | mixed | `store_sig_cache` also switches off coin and TxHash checks, so tests cover a branch production does not run. |
| 7dc7be76bb | hold | mixed | Relay now depends on one narrow condition; spent-coin and RCU questions open. |

**Blocking finding outside the listed commits:** X1 below. It exists at the series' parent and lets a peer-supplied transaction spend someone else's P2PKH coin in the mempool. Fix it before relying on any batch path in this series.

No listed commit was found to let an invalid transaction into a block. `ConnectBlock` still runs `CheckTxInputsFromSpentCoins` (validation.cpp:7372), and that function calls `CheckSpentCoin` and the expiry check (tx_verify.cpp:452, 460).

## Cross-cutting

### X1. Confirmed, critical, pre-series: batch admission skips spent-coin and expiry rules

`CheckTxInputsFromResolvedCoins` (validation.cpp:1331-1391) is the batch path's copy of `Consensus::CheckTxInputs` (consensus/tx_verify.cpp:338). It omits two checks:

- the expiry check (tx_verify.cpp:370, `bad-txns-input-expired`)
- `CheckSpentCoin` (tx_verify.cpp:378): legacy tx spending a V2 coin, bridge template, witness shape, P2SH hash, P2PKH key hash

`CheckLegacyBridgeInput` (validation.cpp:6229) relies on that omitted check. Its comment says CheckTxInputs "has checked ... that the pubkey hashes to the coin's key hash", and the code then only verifies the signature against the key in the witness.

Path: SHORTTX response, `HandleShortTx` (net/v2_protocol_handler.cpp:1938), `ProcessRawTxBatch` (validation.cpp:4230), `AcceptRawTxBatch`, `PreChecksBatch` (call at 2338), script check dispatch (6444). `submitrawtxbatch` reaches it too (rpc/mempool.cpp:1454, 1772).

Failure scenario:
1. An attacker builds a version 7 transaction whose `nFlags==1` input spends a victim's P2PKH coin. The witness is `[attacker sig, attacker pubkey]`.
2. The batch path accepts it, because the hash binding is never checked and the signature is valid for the attacker's key.
3. It sits in the mempool and relays. The victim's real spend now gets `txn-mempool-conflict`, and a wallet watching the mempool sees a false payment.
4. Block assembly picks it up. `TestBlockValidity` then fails, which throws at node/miner.cpp:434 when validity testing is enabled; if disabled, the block is invalid.

The attacker pays nothing, because the transaction can never confirm. Spending an expired coin, or a legacy transaction running a V2 wire encoding as a legacy script, follows the same route.

Limits of this finding: the check that a SHORTTX response was solicited (`solicited_txs`, above line 1855) was not traced, so I can't say how easily an unsolicited peer gets there. An attacker announcing its own transaction looks sufficient. The RPC path has no such filter. Tests I found for these reject reasons call the consensus functions directly (`tx_verify_bridge_tests.cpp`, `lotus_v2_tests.cpp:2355`); I found none through `ProcessRawTxBatch`, but that search was not exhaustive.

Attribution: the parent of d9e932b64f already has this function without either check (validation.cpp:947 there), and `HandleShortTx` already calls `ProcessRawTxBatch`. This series did not introduce it.

Fix: replace the copy with `Consensus::CheckTxInputsFromSpentCoins`, or export `CheckSpentCoin` and add the expiry check. Add a test that sends each reject case through `ProcessRawTxBatch`.

### X2. Suspicion, medium: `native_only` treats bridge inputs as native (present at 7dc7be76bb; introducing commit not traced)

`native_only` (validation.cpp:3337-3341) treats any `nFlags==1` input as a pure V7 input. A bridge input spending a P2SH coin also has `nFlags==1`, yet runs the legacy interpreter under script flags (`CheckLegacyBridgeInput`, 6236-6246). The comment "Pure V7 inputs execute the same fixed VM profile" is false for it, so the consensus-flag re-run is skipped, and the standard-flag verdict and sigcheck count are cached under the consensus key (3360-3363).

The result is safe if script validity under `next | STANDARD` implies validity under `next`. Sigcheck counts could differ between flag sets, and upstream treats that as a bug worth detecting. I did not establish a case where they differ. Fix: test the resolved coin for `IsLegacy()`, not the input flag.

### X3. Out of scope but interacting: 52e34975f9 drops notifications

`suppress_staged_signals` (validation.cpp:5037-5040) drops `TransactionAddedToMempool` when `n >= 128` and no subscriber wants spent coins. `HasSpentCoinsSubscribers` comes from e7054d87a7. In my earlier read, the wallet's `NotificationsProxy` and `PeerManager` both opt out, so "no spent-coin subscribers" does not mean "no subscribers". The wallet would miss these transactions. Suspicion, high if confirmed; I did not trace wallet recovery or confirm how `TxRelayIndex` is fed on this path. Fix: test for any subscriber that needs the event, not for spent-coin interest.

## Per commit

### d9e932b64f: pass, shared

Checked:
- Key is still salted SHA256(TxHash || flags) truncated to 28 bytes, and TxHash commits to witnesses.
- Shard index uses key bytes that are salted, so a peer can't aim at one shard. Budget is split per shard and the total is preserved (scriptcache.h `setup_bytes`). Each shard has 1/16 of the capacity, which is fine for random keys.
- `has_entries` is safe under the locks.

Notes:
- Test `ccoins_side_effect_free_lookup` would fail without the helpers, but is single-threaded. There is no concurrent test of the sharded cache.
- `PeekCoin` (coins.cpp:132) has an unenforced "no concurrent writer" precondition. All production calls I found are under cs_main (validation.cpp:1873, 2292), so this is low risk. Add an annotation.

### 0cb9f3933b: fix, mixed

Split: script cache changes are shared; `SmtFindBorrowed` is v2.

Checked:
- All production `getUnlocked`/`insertUnlocked` calls (validation.cpp:814, 845, 2441, 2619, 5071, 5208, 5773, 5922, 6200) sit in functions that hold cs_main. `CheckInputScripts` and `AcceptRawTxBatch` assert it; `CheckInputScriptsReusing` has the annotation. Parallel workers do not touch this cache in the code I read. I found no live race.
- `SmtFindBorrowed` (mempool_overlay.cpp:571): returned pointers borrow from a snapshot root that the caller holds. Immutable nodes, depth bound. No defect.

Findings:
- **Confirmed, medium: lock requirement is a comment.** scriptcache.h:170 and 186 have no `AssertLockHeld(cs_main)` or `EXCLUSIVE_LOCKS_REQUIRED`. A future caller from a worker, which is what the class comment at d9e9 invites, corrupts a non-thread-safe CuckooCache: wrong sigcheck counts or a false cache hit, and so a skipped script check. Tests still call the locked variants, so TSan sees nothing. Fix: annotate and assert, or delete the unlocked variants.
- **Confirmed, low: design contradiction.** The class comment still says sharding allows access "across worker threads without cs_main", but production now never takes those locks. Either keep the locks, whose uncontended cost is small, or remove the sharding and update the comment.
- No test touches this commit's behaviour.

### 40de4ece63: fix, mixed

Split: `GetConflictTx`, batched signals and the size check are shared; the UTXO filter and batch Schnorr path are v2.

Checked:
- Batch verification uses fresh strong randomizers (`batch_randomizers.h`) and fails closed. One bad signature can't validate another, and any batch failure leads to individual re-preparation. Failure attribution is right.
- Verdicts survive only after `VerifyAll` or individual re-verify (validation.cpp:2653, 3763 at this commit).
- `MatchesContext` compares tip hash, height, MTP, flags and rules under cs_main. Activation boundaries therefore invalidate a preparation.
- Fee and min-fee rules are rechecked in `FinalizeDeferredPreChecks` and hysteresis in `AcceptSingleTransaction`.
- `TryVerify` matches `CheckRegularTransaction` for duplicate and null inputs, sizes, values, maturity, expiry and conservation. It has no `MIN_TX_SIZE` check, but this is unreachable: a V2 output needs a branch, which puts the smallest transaction at about 106 bytes, over the limit of 100. Add an assert to document that.
- Filter inserts and erases are paired with mapNextTx at this commit, and an exact spent-outpoint set sits behind it.

Findings:
- **Confirmed, medium: peer can force re-verification of a whole batch.** One invalid signature, or leftovers from a tx whose `Prepare` returned nothing after adding items, makes `worker_sig_failed` re-prepare all `work`, not just that worker's slice (validation.cpp:4965-4971 at 7dc7). Cost is roughly N single verifies per bad tx, repeatable, bounded by `TX_ADMISSION_MAX_BATCH`, with no penalty beyond normal rejection. `FirstFailingIndex` exists. Fix: bisect, and re-prepare only the failing items.
- **Suspicion, low: filter false negative.** `Unmark` erases a 64-bit fingerprint while another outpoint may share it. Salted, so not attacker-targetable. Theoretical only. Fix: count fingerprints, or confirm the exact set is always consulted.
- **Confirmed, low: reused verdict cached under the consensus key without a consensus-flag run** (validation.cpp:1921 at this commit). Safe for pure V2 since the VM takes no script flags. See X2 for the bridge case.
- No tests.

### 2be6acfcc7: pass, mixed

Split: thread-local salt and `MempoolAddedBatch` are shared; `ClearView` reuse is for the native path.

Checked:
- `RandomSalt` is seeded through `FastRandomContext`, with the deterministic branch only for tests. No security issue found. Each thread's stream is separate, and hashers remain internally consistent per instance.
- Reused `MemPoolAccept`: `m_view` is cleared for every case except reused-valid, which does not read the view. A leftover cached output is harmless under cs_main.
- Batched signals keep sequence order within a batch.

Note: no tests, and the batch signal is what X3 later suppresses.

### 5e21887803: fix, v2

Checked:
- Mode 0/1/2 preimages (`ComputeV2FastPathSighashFromSpk45`, validation.cpp:680 at 7dc7) match `SigningMessage`. Own-input layout matches `EncodeInputCore` then CompactSize coin wire (`transaction.cpp:97-145`, `signing.cpp:94-104`), excluding arguments.
- `BatchSigCollector::Add` uses the first 64 bytes, and the mode is bound in the message. Mode validity is established by shape first.
- Mode 2 requires `i < vout.size()` and a short script, matching `CheckLegacyBridgeInput`.
- **Sigcheck parity resolved, no defect.** Fast path reports 0 sigchecks. The native VM path does not touch `metrics`; only `RunLegacyScript` counts (validation.cpp:6285-6535 vs 6541-6544). Slow and fast paths therefore agree at 0 for native-coin shapes, including `ConnectBlock`.
- Single-input transactions add directly to the shared collector, and multi-input ones stage then merge, so a failed input leaves nothing behind.

This commit also corrects a real divergence: at 40de4ece63 (validation.cpp:580) the fast path accepted a 65-byte signature with trailing byte 0, which `VerifyBip340Signature` rejects. That was consensus-relevant, since this code also runs in block validation.

Findings:
- **Confirmed, medium: no differential test for consensus-critical code.** A hand-built preimage duplicates `SigningMessage`, and any drift becomes a chain split between fast and slow paths. The bug it fixes shows the risk. Fix: a test that runs every mode through both paths and compares verdict, sigchecks and message bytes, including malformed signatures.
- **Confirmed, low: `GetV2FastPathShape` does not check `prev_out.IsLegacy()`** (validation.cpp:~616). A legacy coin with a crafted 45-byte script has the right shape. Normal paths reject it through `CheckSpentCoin` first, but X1's path does not, so such a coin is spendable with no signature there. Fix: add the check.
- **Confirmed, low: `Kinds().size() == 2` as a proof of "empty records pass"** (validation.cpp:~975). True for the current kinds. A swapped kind keeps the count. Fix: compare identity or a capability flag.

### e7054d87a7: fix, mixed

Split: spent-coin subscriber, trim and expire shortcuts, `CanFitRawTxBatch` and `ApplyDelta` are shared; prewarm is v2.

Checked:
- Prewarm runs outside cs_main on an immutable SMT root, and results are revalidated under cs_main by tip hash. `regular_tx_valid=true` is set before signatures, based on `TryVerify`, whose rules I compared. Acceptable.
- `pool_unchanged` skip: counters are read before the read phase, `nTransactionsUpdated` moves on add, remove and clear, and duplicates in the batch disable it.
- `CanFitRawTxBatch` is a pessimistic bound. Package atomicity holds.

Findings:
- **Suspicion, medium: prewarm fast branch not gated on spent-coin subscribers** (`use_fast_confirmed_smt`, validation.cpp:3990 at 7dc7; staged path does gate, 4864). The `PreChecksBatch` fast branch (2115-2165) leaves `m_resolved_inputs` empty, so `Finalize` falls to `GetSpentCoins(ws.m_ptx, m_view)` (2505) with `Assume` only. If `m_view` can't resolve the coin at that point, Chronik gets null spent coins when the pool exceeds 6400. I did not establish `m_view`'s backend at that moment. Fix: gate the branch, or move snapshot coins into the workspace.
- **Suspicion, low: subscriber registering between phases** gets an aliased empty coin vector from `PrepareFastConfirmed`.
- **Suspicion, low, likely another reviewer's area: `TxRelayIndex` fast `Add` early return** if the txid is in `short_id_of`. A remove then re-add before epoch republication could drop the re-add.
- **Confirmed, low: `m_snapshot_changed_entries` as a vector** grows without bound if never drained; duplicates are idempotent.
- See X3. No tests.

### 6eb8e0c15a: fix, mixed

Split: `SendMessages` and relay wake plus lock points are shared; prewarm reuse is v2.

Checked: the `net_processing` part belongs to the networking reviewer and was not audited in depth here. Prewarm verdict reuse still requires the fast shape and `std_deferred_only`.

Findings:
- **Confirmed, medium: reuse compares `TxOut` only at this commit** (validation.cpp:2717-2719). There is no tip or flag check, so a prewarm result can cross a tip change. Safe for maturity and expiry only if the normal branch recomputes them, which X1 shows is incomplete for expiry. 6a1406992b adds a tip check for coin reuse only. Fix: bind the verdict to tip hash and flags, as `MatchesContext` does.
- **Confirmed, low: `CalculateLockPointsFromResolvedCoins` rewrite duplicates BIP68** (validation.cpp:1029) with no test. Mint inputs (`nFlags==3`) are skipped here and get height 0 in `CalculateSequenceLocks` (tx_verify.cpp:~137). Benign since the deserializer forces their sequence to final. Whether signed `nVersion >= 2` matches the original cast was not compared, though version 7 and 1/2 are the only values I saw. Fix: reuse the original or add a parity test.

### 6a1406992b: fix, mixed

Split: TxId inlining, univalue, getrawmempool and relay index are shared; in-batch preparation is v2.

Checked:
- In-batch parents: `parent_idx < ws_idx` is enforced, a child before its parent falls to normal resolution or a missing-input rejection, and `conflict-in-package` catches in-batch double spends (validation.cpp:3061).
- `test_accept` results don't relay.
- Sigcheck for fast path remains 0, consistent with 5e21 above.

Findings:
- **Confirmed, medium: one flag controls two unrelated things, and tests run the other branch.** `verify_coins_tip=store_sig_cache` (validation.cpp:4035) and `store_sig_cache=bool(options.test_between_phases)` (4332; at 7dc7, 4533 and ~4954). In production `MatchesContext` compares TxId, which omits V2 witnesses, instead of TxHash, and drops the chain-id comparison (validation.cpp:361-367). Production also never compares confirmed coins with `CoinsTip`.
  - All reorg and mutation tests (`lotus_v2_tests.cpp:809-1071`, `mempool_admission_tests.cpp:568`, `txvalidationcache_tests.cpp:136`) set `test_between_phases`, so they prove the branch production doesn't use. `can_try_fast_confirmed` requires `!test_between_phases`, so no test reaches it. No test references `PrepareFastConfirmed`, `AllConfirmedInputs` or `v2_fast_path_verified`.
  - I found no live attack: the preparation is built from the same transaction object in the same call, and coins come from a tip-bound immutable root.
  - Fix: separate parameters, keep the TxHash and chain-id comparisons (they cost little), and add production-mode tests.
- **Confirmed, low: `ConsensusScriptChecks` does not populate the script cache in production** (validation.cpp:2434), and `store_sig_cache` false leaves the signature cache empty too. Blocks re-verify these signatures. Safe direction, but W1-11's verdict reuse is not realized.

### 7dc7be76bb: hold, mixed

Split: batch relay hook and deferred metrics are shared; pre-allocated entries and fast-confirmed are v2.

Hold until the relay condition and the two open questions below are answered.

Checked:
- `pre_allocated_entry` is used only when fee, height and sigchecks match (validation.cpp:2157-2162).
- The fast-confirmed SMT path checks flags 0, one branch, one path, fee_per_output 0, maturity and expiry (780-830).

Findings:
- **Confirmed, medium: relay depends on one condition.** `HandleShortTx`'s success branch no longer fills `accepted_txs`, and the RPC dropped its fallback. Both depend on `NotifyBatchRelay` (validation.cpp:4267-4271), which needs `m_tx_results.size()==package.size()` or `batch_accepted`. Any other valid result relays nothing, silently. The callback also relays the whole package, including members trimmed by `LimitSize` or already present. Fix: relay from actual acceptance results, and test that trimmed members aren't relayed.
- **Suspicion, low: callback lifetime.** `m_batch_relay_cb.reset()` (net_processing.cpp:1008) protects the `std::function`, not the captured `this` (3442-3447). An in-flight callback during shutdown could use a dying `PeerManagerImpl`. Shutdown order was not determined. Fix: clear the mempool's callback and wait, or hold shared ownership.
- **Suspicion, low: long RCU read section.** `RCULock` spans each worker's loop, including `VerifyAll` (validation.cpp:4005, 4199). Writers calling `synchronize`, possibly holding cs_main, would wait for it. This is not a proven deadlock, and I did not trace the writers. Fix: release before `VerifyAll`.
- See the e7054d87a7 spent-coin suspicion, which this commit widens.

## Answers to the review documents

**W1-10 (package atomicity).** Kept. Pass 1 completes before submit, and any failure returns before anything is inserted.

**W1-11 (exact witness, coins and context).** Partly. Script cache key includes witnesses and flags. Coin metadata comes from a tip-bound root. The production branch of `MatchesContext` compares TxId rather than TxHash (6a1406992b). Verdict reuse is also not achieved in production, so blocks re-verify.

**W3-6 (shard safety).** Key and budget are preserved. The guard is removed by 0cb9f3933b, safe today only because all callers hold cs_main, and not enforced. Coin helper is conditionally safe, with the same enforcement gap.

**W3-7 (root and tip coherence).** No epoch gate was added. Instead `GetV2BlockStateSnapshot(tip hash)` binds the root (node/snapshot.cpp ~1422), `MatchesContext` compares tip under cs_main, and Phase C holds cs_main. SMT is immutable, so reads don't mix with database state. This handles reorgs for `native` preparation. The exception is 6eb8e0c15a's `TxOut`-only reuse.

**wave3/admission/REVIEW.md.** The `GetDirtyCount` concern doesn't apply to these commits. Hints stay non-authoritative. Raw-batch all-or-nothing is preserved.

## Not determined

- Whether X1 is reachable by an unsolicited peer (`solicited_txs` filter not traced).
- `m_view`'s backend when `GetSpentCoins` runs in `SubmitPackage`.
- Shutdown order for the relay callback.
- Wallet recovery for suppressed notifications (X3).
- Whether RCU writers can hold cs_main while waiting.
- Runtime behaviour of everything: nothing was built or executed.

## Tests

Only d9e932b64f adds a test. The other eight touch nothing in `src/test`, so none of their changes has a test that would fail without it.
