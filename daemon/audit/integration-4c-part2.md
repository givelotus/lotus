# Integrating the lock-removal series, part 2 (phase 4c)

This pass covered the 10 commits the first pass left out (`integration-4c.md`). 7 landed in part, usually as a
small share of the source commit, and 3 did not land at all. No queue, batch, filter, rate or short-ID delay limit
changed. Nothing was pushed, and the parent repository has no new commits.

Most of the code in these commits stayed out on purpose. It either raised limits without evidence, or restructured
validation in ways the tests don't exercise. Benchmarks are due later, and they should decide whether any of it
comes back.

## Final tips

| Tier | Commit | Tree |
|---|---|---|
| `ecashd` (`daemon/ecashd`, branch `ecashd`) | `b92c9ec65aa0a0e05e326bc6e906dc3ef5403e35` | `36fe0013dbcb663463d3690bc083e4611ce776c4` |
| V2 (`daemon/lotusd`, branch `main`) | `4a1f9a8e100bd1980b0d669725bc07e58a64d323` | `30e8120f338c3394d12cac53195f7e443c6f8c79` |

`ecashd` gained 10 commits on `0e3cec931d`. V2 gained 5 commits and now has 168 on top of `ecashd`. All commits use
the required author and committer.

`make -C daemon source-verify` reports only "not published" for both tiers, which is expected until someone publishes.
`make -C daemon sync SERIES=v2` left `daemon/ecashd`, `daemon/lotusd`, `daemon/sources.json` and
`daemon/stack-review.json` modified in the parent, uncommitted as instructed.

Backups are under `refs/backups/`:

- `pre-4c2-{ecashd,lotusd}`: the starting points
- `4c2-{ecashd,lotusd}-ckpt1`, `-pre-ckpt2` and `-ckpt2`: checkpoints
- `4c2-lotusd-bad-merge-6fa9a53`: the broken commit described under "What went wrong"

## New commits

| Tier | Commit | Subject | Test |
|---|---|---|---|
| `ecashd` | `fa8f505f70` | rcu: let read sections nest | `rcu_tests/rcu_read_sections_nest` |
| `ecashd` | `9a303b468b` | radix, mempool: look up entries without touching reference counts | `radix_tests/radix_borrowed_lookups_leave_reference_counts_alone` |
| `ecashd` | `3fd914ebe4` | net: skip the mempool lookup when selecting relay inventory | `relay_inventory_queue_tests/entry_facts_follow_the_rank`, `txrelay_tests/relay_selection_rechecks_recorded_facts_after_a_removal`, updated `persistent_inventory_unchanged_turn_has_bounded_lookup_work` |
| `ecashd` | `a833aee25c` | net: store the usual single transaction inline in short-ID buckets | `txrelay_tests/shortid_buckets_keep_every_colliding_transaction` |
| `ecashd` | `bc2d456801` | mempool: return early when limiting the pool finds nothing to do | `mempool_tests/limit_size_acts_only_when_there_is_something_to_do`. This doesn't change behaviour, so the test also passes without the commit. It only guards the behaviour. |
| `ecashd` | `6232d21ded` | mempool: read the transaction count without cs | `mempool_tests/size_reads_do_not_wait_for_the_mempool_lock` |
| `ecashd` | `a44006f9dc` | validation: don't build spent coins for subscribers that won't read them | `mempool_admission_tests/large_batches_notify_subscribers_that_decline_spent_coins` |
| `ecashd` | `5c4031f17c` | amount: format RPC amounts without printf | `amount_tests/univalue_conversion_matches_printf_formatting` |
| `ecashd` | `4319df0626` | txadmission: drain one peer's queue without taking turns | `txadmission_queue_tests/single_peer_batches_keep_the_counts` |
| `ecashd` | `b92c9ec65a` | net: don't let relaying a departed transaction put it back in the index | `txrelay_tests/relaying_a_departed_transaction_leaves_no_trace` |
| V2 | `c061395289` | validation(v2): look up the mempool without refcounts in batch prechecks | `mempool_admission_tests/batch_prechecks_hold_up_against_a_nonempty_pool` |
| V2 | `d9d9980941` | mempool(v2): don't let the UTXO fast filter decide conflicts | `mempool_overlay_tests/fast_filter_does_not_hide_a_mempool_spend` |
| V2 | `d0a13d0c34` | lotus_v2: ask the deferred kinds whether a run can be skipped | `SkippingTheRunNeedsEveryKindToAllowIt` in `test_lotus_v2_deferred_checks` |
| V2 | `766438d417` | validation(v2): verify raw batch signatures before taking cs_main | `lotus_v2_tests/raw_batch_preparation_is_bound_to_tip_and_coins` |
| V2 | `4a1f9a8e10` | net(v2): take cs_main in SendMessages only for a new V2 known block | `txrelay_tests/send_messages_takes_cs_main_only_for_a_new_v2_known_block` |

## Every source commit

| Source | Report | Outcome | Landed as | Left out, and why |
|---|---|---|---|---|
| `e7054d87a7` | fix | split | `ecashd` `a44006f9dc`, `bc2d456801`; V2 `766438d417` (reimplemented) | The source's own prewarm path, in favour of the existing native preparation. The index `contains` fast path and precomputed short IDs: little value without dedupe. Phase C reuse of flags and acceptor, the SMT-first preparation order and the pessimistic `CanFitRawTxBatch`: not reached, no evidence of need. |
| `6eb8e0c15a` | fix | split | V2 `766438d417` (reuse, with the binding the finding asked for), `4a1f9a8e10` (narrowed gate) | The `m_initial_sync_checked` replacement for `m_sync_started`: the V2 gate fixes the reported bypass without changing sync semantics. Elapsed-tick catch-up (up to 8 ticks): a relay rate raise. Wake dedupe: wakes can't be observed in the unit harness, and the benefit is unmeasured. The in-flight check in `ProcessShortTxResponse`: it only trims over-reservation of the admission budget. |
| `b8f43cdb8b` | hold | split | `ecashd` `a833aee25c`, `a44006f9dc` (notification opt-out only) | The notification skip for large batches and `store_sig_cache` (both must-fix, so never landed). The snapshot `entry_tree` bypass and the filter bypass above 256: magic thresholds, and the bypass would also disable native preparation. Direct-format RPC output. |
| `6a1406992b` | fix | left out | None | `m_txid` in the mempool entry: 32 bytes per entry for an unmeasured locality gain. Vectorised `getrawmempool` and the raw UniValue array: depends on the live-tree path left out above, and carries a `setRawArrayStr` hazard. `ResolveShortIds`/`PartitionShortIds`, in-batch parents in staged admission and the `DecodeShortTxResponse` change: not reached. |
| `52e34975f9` | hold | split | `ecashd` `5c4031f17c`, `4319df0626` | Short-ID in-flight raise, known-filter raise to 350000, retained budget raise to 128M: limits with no evidence. The full reconciliation gate: must-fix. `tx_check` `GetTotalSize` hunk: `Serialize` already special-cases size computation, so no gain. `track_routes`: unmeasured. The fast-confirmed path behind `pool.size() > 6400`: magic threshold, tests never run that branch, skips coin checks. |
| `9cfddf4d37` | hold | left out | None | Short-ID delay cuts and `MAX_SELECTION_CHUNK`: limits with no evidence. Parallel `EnsureMempoolTxIds`: depends on the live-tree path left out above. `RecursiveDynamicUsage` cache: trivial in `ecashd`, a V2-only candidate for the benchmarks. `cleared_indices`: it corrects a `clear_limit` bug from `52e34975f9`, whose code didn't land. |
| `b033646c60` | hold | split | `ecashd` `fa8f505f70`, `9a303b468b`, `3fd914ebe4`; V2 `c061395289` | 1 MB socket drain and message coalescing: raises per-peer work with no evidence. SHORTTX response cache: uncounted memory, no evidence. The `*WithinReadSection` lookups: deliberately not added, which removes the crash. |
| `4ff6454942` | fix | split | `ecashd` `fa8f505f70` (nesting), `b92c9ec65a` (the hazard, in the code that exists) | Deferred `AddTxIdBatch`: duplicates the add the notification already does, and is the source of the reported re-add. Direct-format 16-shard `getrawmempool`: depends on the live-tree path left out above. |
| `7dc7be76bb` | hold | left out | None | `NotifyBatchRelay`: must-fix, so relay stays explicit at its call sites. Worker pass precomputing entries: part of the same restructure, no evidence. `MarkPeerKnownTxBatch` and metrics at flush only: small, unmeasured. |
| `9e484521d6` | fix | split | `ecashd` `6232d21ded`; V2 `c061395289` (RCU section per transaction) | The remaining validation restructure, which builds on the fast-confirmed path above. The RCU section covers only duplicate and conflict checks, not coin lookups. |

## Findings

"Reproduced" means a test failed or the process aborted before the fix, as described.

| Finding | Outcome | Reproduced? |
|---|---|---|
| `b033646c60` B1: `existsWithinReadSection` asserts a lock `PrepareStaged` doesn't hold | Fixed by construction. No lookup requires a read section, and sections nest. | Yes. With a temporary `containsWithinReadSection` in `PreChecksBatch`, the new test aborted with `Assertion failed: (RCULock::isLocked())` in `findLeaf`. |
| `b033646c60` B2 | Fixed. Nesting landed first, and the conflict path is covered through a raw batch. | Not separately. |
| `b033646c60` B6 | Not applicable. `FinishRemoveUnbroadcastBatch` didn't land. `ResolveRelayShortIds` uses `RemoveUnbroadcastTx` under `cs`. | No, the code isn't present. |
| `b033646c60` B3, B4, B5, B7 | B3 was fixed in the first pass. The code behind the others didn't land. | No. |
| `b8f43cdb8b`: batches of 128+ skip `TransactionAddedToMempool` with no spent-coins subscriber | The skip didn't land. A test with 200-transaction batches guards it. | Not against the source's code. |
| `b8f43cdb8b`: `store_sig_cache` tied to the test hook | Didn't land. Signature cache writes are unchanged. | No, the code isn't present. |
| `52e34975f9` C3: `m_full_recon.Tick` starved by tracked requests | The gate didn't land, and `Tick` is still ungated in `SendMessages`. **No regression test was written**, so nothing stops the gate returning. | No. |
| `7dc7be76bb`: relay depends only on `NotifyBatchRelay` | Didn't land. Relay stays explicit in the RPC and short-transaction paths. | No, the code isn't present. |
| `6eb8e0c15a`: reused verdict compares `TxOut` only, with no tip or flags binding | Fixed. Reuse needs a matching tip, median time, flags, chain and rules, and every coin field. | Yes, by weakening the new code. An output-only comparison gives 4 failures, and removing the context check gives 1. The source's own code was not run. Flags can't move without moving the tip in this test, so they aren't tested on their own. |
| `4ff6454942`: deferred `AddTxIdBatch` can re-add a removed txid | The deferred add didn't land. **The same hazard existed in code already landed**, in `RelayTransaction` and `RelayTransactionBatch`, and is fixed in `b92c9ec65a`. | Yes, for the existing paths: without the fix the index holds 3 entries where 1 is correct. |
| First pass, `40de` filter false negative | Fixed in `d9d9980941`. The filter now only serves native preparation, where admission checks conflicts again. | Yes: with the gates restored, `isSpent` and `GetConflictTx` both fail. |
| First pass, `5e21` `Kinds().size() == 2` | Fixed in `d0a13d0c34`. Each kind now declares whether the run can be skipped. | Not applicable: this was a latent risk, and today's consensus registry behaves the same before and after. |
| First pass, T1: epoch teardown on a reader thread | **Open.** This work didn't touch it. | No. |

No finding was disputed. The closest case is C6 in `admission-limits.md`, which doesn't arise because its code didn't land.

## Limits changed

None. All of these remain at their previous values:

- Queue, batch, known-filter and retained-budget limits
- `MAX_SELECTION_CHUNK`
- Relay rate
- Short-ID delays and the in-flight limit

No V2-only raises were made either.

## Built and run

All targets (`all test_bitcoin test-avalanche test-pow bitcoin-bench`) were built with `ninja -j12` at the final tips in
`daemon/.build/ecash` and `daemon/.build/v2`. `ecashd` has no failures. V2 has only the known
`test_lotus_v2_candidate_body_pool` link failure.

Run at the final tips:

- `ecashd`: the 12 new or updated test cases, all passing.
- V2: those 12 plus 6 more (18 cases), all passing. The 6 are 4 new cases, plus
  `rpc_batch_snapshot_tests/testrawtxbatch_and_submitrawtxbatch_all_or_nothing` and
  `lotus_v2_tests/v2_staged_native_success_reuse_and_authoritative_fallback`, which exercise the changed paths.
- V2: `test_lotus_v2_deferred_checks`, passing.

Beyond the "new tests only" rule, I ran three whole suites, because `b92c9ec65a` changes what relaying does to the
index. All pass:

- `txrelay_tests` on both tiers
- `v2_protocol_handler_tests` (28 cases) on V2

**Not run:** the full unit suites, functional tests, TSan, and any benchmarks. `test-avalanche` and `test-pow` were built
but not run. These commits change lock-free reads, so TSan coverage in the final sweep matters.

`send_messages_takes_cs_main_only_for_a_new_v2_known_block` relies on real time: another thread holds `cs_main` for up to
1.5 s. A machine stalled for over a second could make it fail spuriously.

## What went wrong

- **A commit with conflict markers.** During the second restack, the file had two conflicts and my script resolved one, but
  I added and committed it anyway. The commit, `6fa9a531a3`, had markers and a spliced test, and `sync` accepted and pinned
  it. I found this before any build. I rebuilt the test file from the parent commit plus the intended test, amended, and
  resynced to `4a1f9a8e10`. No commit in the V2 stack (168) or the top 30 of `ecashd` now has markers in `src/`. The bad
  commit is kept at `refs/backups/4c2-lotusd-bad-merge-6fa9a53`. `sync` does not check for markers, which may be worth
  adding.
- **A first draft that broke a test.** My first version of `b92c9ec65a` also dropped departed transactions from the relay
  queue, which broke `persistent_inventory_matches_full_scan_across_mutations`. That test relays before admitting. The
  queue change wasn't needed, so it was removed.
- **A commit made before its failure check.** I committed `d9d9980941` before confirming its test failed without the fix.
  I did that check straight afterwards and it failed as it should.
