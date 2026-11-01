# Integrating the lock-removal series (phase 4c)

Partial. 18 of the 29 source commits landed, whole or split, and 1 (`f8ace4160c`) was folded into its neighbour. The other 10 did not land: they were not attempted
to the end because the work stopped at a checkpoint. See
"Left out" below. Nothing was pushed. `make -C daemon source-verify` reports only "not published" for both
tiers, which is expected until someone publishes.

## Final tips

| Tier | Commit | Tree |
|---|---|---|
| `ecashd` (`daemon/ecashd`, branch `ecashd`) | `0e3cec931d0e6b327786e7ce1cb5aa5fd96a3f87` | `5096631c25028752ce06a674228270f769d2231d` |
| V2 (`daemon/lotusd`, branch `main`) | `395633723d6bce6d843bac2769fd2e4417a924d6` | `77ac8bfe008926ab5b05a24059f21e6820d61676` |

`ecashd` gained 15 commits on `713dc49df5`. V2 has 163 commits on top of it, 5 of them new since the
start of this phase. Backups: `refs/backups/pre-4c-{ecashd,lotusd}` and `refs/backups/4c-{ecashd,lotusd}-ckpt*`.

## Every source commit

| Source | Report | Outcome | Landed as | Why, and what was left out |
|---|---|---|---|---|
| `da31264727` | fix | landed | `ecashd` `2421929f8f` | R1, R2, R3 fixed |
| `952db7eb9e` | pass | landed | `ecashd` `c5e5d2ca8b` | Contention only, so its test is a stress test that means most under TSan |
| `ac31d9dc2d` | hold | landed | `ecashd` `5f0ab0b39f` | M1, M2, M3 fixed |
| `77d48070c8` | fix | landed | `ecashd` `85561a5dba` | L1 documented, L2 fixed |
| `d650d95bfb` | fix | landed | `ecashd` `ccd335dc6b` | U1 to U4 fixed |
| `39c96054f6` | fix | split | `ecashd` `8d5adafe9b`, V2 `f47752f06f` | Native exact-bytes test in V2. RPC decode hunk left out: performance only, unrelated, untested |
| `96b3326973` | pass | landed | `ecashd` `7011faa170`, V2 fixup in `13d7438029` | The restack exposed a real V2 bug: the p2p-v2 header read an empty shared payload's size. Fixed with a test |
| `a5b4951884` | pass | landed | `ecashd` `f84665d057` | No test possible: only moves work past a lock release |
| `d9e932b64f` | pass | landed | `ecashd` `0e6bc7b19c` | |
| `0cb9f3933b` | fix | split | V2 `a6724f6a2e` | `getUnlocked`/`insertUnlocked` script cache bypass left out: its safety was only a comment and it undoes sharding. Later commits use the locked calls |
| `703a07c21e` | pass | landed | `ecashd` `7a24973b30` | |
| `2be6acfcc7` | pass | split | `ecashd` `ea97ebbb8e` | V2 part (acceptor reuse, `ClearView`) not landed: it conflicts with the `e7054d87a7` work, which is left out |
| `447c4aac77` | fix | landed, changed | `ecashd` `09c70889c5` | C1 and B3 fixed. `FinishRemoveUnbroadcastBatch` dropped, which avoids C2, and B2/B6 of the same family |
| `2deccfdbf7` | hold | landed, changed | `ecashd` `a082e695ca` | No limit raises. Left out: 256 to 4096 per peer, batch raise, `MempoolToJSON` parallel path |
| `f8ace4160c` | pass | folded | into `a082e695ca` | `ForEachEpoch` and hashed in-flight set kept. `from_admission` skip left out: it would undo the A1 fix |
| `f66e475bc1` | hold | split | `ecashd` `ba53832295` | Left out: queue 16384/32768, batch 4096, `MAX_SELECTION_CHUNK` 4096, relay rate 500k, `Relay` implying preferred, `AddUnbroadcastTxBatch`, `FinishRemoveUnbroadcastBatch` |
| `e91e089f30` | hold | landed, changed | `ecashd` `0e3cec931d` | E1 to E4 fixed. Left out: atomic `CChain::m_tip`, which nothing would read |
| `40de4ece63` | fix | landed | V2 `3bd60a75f0` | Whole-batch re-verification replaced by bisection. Went to V2 whole; see tier note |
| `5e21887803` | fix | landed | V2 `395633723d` | Differential test added, legacy coin check added |
| `e7054d87a7` | fix | left out | | Stopped. Cherry-pick conflicts in five files, and the prewarm suspicions are unresolved |
| `6eb8e0c15a` | fix | left out | | Depends on `e7054d87a7` |
| `b8f43cdb8b` | hold | left out | | B1 (dropped notifications) not fixed, so it can't land |
| `6a1406992b` | fix | left out | | Depends on the above |
| `52e34975f9` | hold | left out | | C1 to C5 not fixed, so it can't land |
| `9cfddf4d37` | hold | left out | | Depends on `52e34975f9` |
| `b033646c60` | hold | left out | | Remote crash B1 not fixed, so it can't land |
| `4ff6454942` | fix | left out | | Depends on `b033646c60`. F3, F4 not addressed |
| `7dc7be76bb` | hold | left out | | Depends on the above. Relay condition not addressed |
| `9e484521d6` | fix | left out | | Depends on the above. S1, S2 not addressed |

### Left out

The 10 commits from `e7054d87a7` on were not judged unfixable. I stopped there because each needs a long port and
review of consensus-adjacent fast paths, and the brief says to stop at a checkpoint where both stacks build when out of
budget. Leaving them out is safe: they are optimizations, and the critical findings in them (`b033646c60` B1 in
particular) therefore aren't in either stack. The cost is that the throughput they were written for isn't there yet.
No benchmark has measured what the landed part gives.

### Tier note

The brief asks for shared mechanism in `ecashd`. `40de4ece63` and `5e21887803` went to V2 whole, including a batched
signal call and a small `GetConflictTx`/`LimitSize` shortcut the report marks as shared. They sit inside native admission
code and I didn't separate them. They could be moved down later. `SignatureCache::SetBatch`'s handling of BIP340 entries
is also in V2 only.

## Findings

"Reproduced" means a test failed before the fix and passes after it.

| Finding | Severity | Outcome | Evidence |
|---|---|---|---|
| R1, M1 radix never prunes, remote memory growth | high/critical | fixed: salted outpoint routing, per-vout lookups | Reproduced: `radix_tree_map_outpoint_nodes_stay_bounded_under_churn`, `sibling_spends_leave_no_permanent_memory` |
| R2, L2 nodes uncounted | high/medium | fixed: counted in `DynamicMemoryUsage` and `CanFit` | Covered by the two tests above |
| R3 `pinSnapshot` | low | fixed | |
| T1 snapshot teardown on the last reader's thread | low | open | Not addressed |
| M2 weakened slab tests | medium | fixed | |
| M3 blind overwrite | low/medium | fixed: `Assume` on insert, private guarded map | |
| L1 readers see compound state | low | documented | The report found no consumer it breaks |
| U1 count leak on race with removal | medium | fixed | Not reproduced: `unbroadcast_flag_count_and_log_stay_coherent` covers the invariants, not the race |
| U2, U3, U4 | low/medium | fixed | Same test |
| F1 two wires, one identity | high | already fixed earlier by `transaction(v2): reject output values that CTxOut can't hold` | Not redone |
| F2 retained bytes and byte limits | medium | handled: counted, compact-extra gate subtracts them, `-maxmempool` value unchanged | `cached_wire_bytes_match_canonical_serialization` |
| F3, F4 | low/medium | not applicable | `4ff6454942` not landed |
| C1 (447c) annotations | low | fixed | |
| C2 (447c) count underflow | low (suspicion) | avoided | Code removed |
| B2 nested `RCULock` | high | not applicable | `b033646c60` not landed |
| B1 remote crash | critical | not applicable | Not landed |
| B3 removal sequence order | low | fixed | `relay_watermark_and_removal_sequence` |
| B4, B5, B7, S1 to S3 | various | not applicable | Not landed |
| B6 skipped publish | medium | avoided | Function not landed |
| A1 scenario 1: swallowed announcements | high | fixed | Reproduced, rejected and dropped cases both failed: `short_id_announcements_outlive_the_body_in_flight` |
| A1 scenario 2: bad witness blocks a tx in V2 | high | fixed | Reproduced: `bad_witness_copy_does_not_block_its_transaction`. The report says "bad witness"; only witness arguments are outside the TxId, and scripts are inside |
| A2, C4 per-peer depth | high | not applicable | Limits not raised |
| A3 serial fallback overtakes | medium | fixed: response held if budget can't take it | Only `HasRoom` tested (`retained_budget_reports_room_as_reserve_would`). Pinning 64 MiB in a test wasn't practical, so the hold itself is untested |
| A4, A5, F2 of `f8ace4160c` | medium/low | fixed: exact keys per transaction, refcount | No separate test. The rotation case isn't exercised |
| A6 head-of-line delay | medium | not applicable | Limits not raised |
| B1 (f66e) `Relay` means preferred | low/medium | not applicable | Left out |
| B2, B3 (f66e) | low/medium | not applicable | Left out |
| B4, B5 (f66e) | medium/low | not applicable | Limits not raised |
| E1 AB-BA deadlock | critical | fixed: filters reset from `UpdatedBlockTip`, nothing locked under their mutex | Reproduced by restoring the tip read: `rejected_transaction_checks_do_not_need_the_chain_lock` failed. Run as a timeout with a second thread on `cs_main`, not under `DEBUG_LOCKORDER` |
| E1 cycle 2, with `FinalizeNode` | critical | fixed: same root cause, and `AlreadyHaveTx` now runs outside `cs_txrequest` | Not separately reproduced |
| E2 block sync skipped | medium | fixed: blocks after 1 s | No test: depends on wall-clock contention |
| E3 stale rejects reset | low/medium | fixed: same change | Test covers re-request after a new tip |
| E4 annotations | low | fixed: `Mutex` members with negative annotations, which propagated through the callers | `net_processing.cpp` builds with no new thread-safety warnings |
| 40de whole-batch re-verify | medium | fixed: bisection | `batch_admission_finds_the_bad_signature_and_keeps_the_rest` checks the outcome. It would also pass with the old fallback, because it doesn't measure the cost. So not reproduced |
| 40de filter false negative | low (suspicion) | open | `Unmark` unchanged |
| 40de verdict cached under the consensus key | low | accepted | Preparation refuses legacy coins, so the VM takes no script flags on this path |
| 5e21 no differential test | medium | fixed | `native_signature_fast_path_matches_the_vm` |
| 5e21 65-byte trailing zero divergence | consensus | fixed by that commit | Covered by the same test. I didn't run the test against the old code, so not reproduced |
| 5e21 legacy coin in `GetV2FastPathShape` | low | fixed | No test of its own |
| 5e21 `Kinds().size() == 2` | low | open | Left as it was |
| X2 `native_only` | medium (suspicion) | not applicable | Code in `7dc7be76bb`, not landed |
| 0cb9, e705, 6eb8, 6a14, 7dc7, C1 to C8, B1 to B4 (b8f4) | various | not applicable | Not landed |

Disputed: none. Every finding I checked against the code held, apart from the wording noted at A1 scenario 2.

Costs I accepted:

- A rejected short-ID body now costs one extra request per announcer, since their announcements stay registered.
- Repeat bodies of an invalid native transaction are validated again, since native rejections no longer enter the TxId
  filter. Their sender is still punished.
- The rejects filter resets through the validation queue, so a retry after a new tip can lag slightly.
- `ForEachEpoch` has thread-safety analysis turned off, so that its lambdas can state their own lock requirements.

## Limits

None changed. `max_per_peer` 256, `max_total` 16384, `TX_ADMISSION_MAX_BATCH` 256, `MAX_SELECTION_CHUNK` 256,
`DEFAULT_TXRELAY_RATE_MAX` 250000 and the short-ID delays all keep their `ecashd` `73ed9c43ed` values. One new constant:
`MAX_BLOCK_SYNC_DEFERRAL` of 1 s, which isn't a raised limit.

## Built and run

- All targets (`all test_bitcoin test-avalanche test-pow bitcoin-bench`) with `ninja -j12` on both final tips. The only
  failure is the known `test_lotus_v2_candidate_body_pool` link error, in V2.
- Only new tests and a few neighbouring ones, as instructed. No full suite.
- Last run at the final tips, all passing:
  - `ecashd`: `radix_tree_map_outpoint_nodes_stay_bounded_under_churn`, `radix_tree_map_salted_outpoint_lookup`,
    `sibling_spends_leave_no_permanent_memory`, `unbroadcast_flag_count_and_log_stay_coherent`,
    `rejected_transaction_checks_do_not_need_the_chain_lock`, `short_id_announcements_outlive_the_body_in_flight`,
    `unnotified_pushes_wake_the_consumer_on_notify`, `rolling_bloom_empty_filter_shortcuts_stay_correct`,
    `txpool_empty_follows_adds_and_erases`.
  - V2: `batch_admission_finds_the_bad_signature_and_keeps_the_rest`, `native_signature_fast_path_matches_the_vm`,
    `bad_witness_copy_does_not_block_its_transaction`, `rejected_transaction_checks_do_not_need_the_chain_lock`,
    `short_id_announcements_outlive_the_body_in_flight`.
- The other new tests passed when their commits were made but were not rerun at the final tips.
- Tests were not all rerun after the later restacks, and individual commits weren't built one by one: builds happened at
  checkpoints.
- TSan: not done. No separate build directory was set up.

## Identity

Every commit above `713dc49df5` in `ecashd`, and all 163 V2 commits, now have author and committer
`Shammah Chancellor <shammah.chancellor@notvalid.com>`. This includes 7 older V2 commits whose author email was rewritten
because the restack rewrote them anyway. Trees were compared before and after that rewrite and match.

## Tooling defects

- `make -C daemon sync` stops on a rebase conflict and needs a hand-run `git rebase --continue` and rerun. This is as
  documented, not a defect, and rerunning worked here.
- `git status` in `daemon/lotusd` reports "diverged from origin/main" by hundreds of commits, which is expected for a
  stack but makes the output useless at a glance.
- No defect found in `daemon_sources.py` in this phase. The 4ab concern about rerunning after a hand-resolved cascade didn't
  come up.

## Publishing the reports

`daemon/audit/lock-removal/README.md` says not to publish those reports until the findings are fixed. Findings for the 10
commits left out remain open against the source branch `origin/snowstorm/merklix-snowball`, including the remote crash at
its tip, so that condition isn't met.
