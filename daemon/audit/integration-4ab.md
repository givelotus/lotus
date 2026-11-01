# Integration report: phases 4a and 4b

Scope: `docs/plans/daemon-stack-reconciliation.md` phases 4a and 4b only. No
lock-removal, radix-index, header-history or Snowstorm commits were integrated.
Nothing was pushed, nothing was committed in the parent repository, and commit
identity was not rewritten.

## Final state

| Stack | Branch | Tip | Tree | Commits |
|---|---|---|---|---|
| ecashd | `ecashd` | `713dc49df58d8b8aeb5268d48920f4cbfaaf59fb` | `8d90730c641c26a7a200a3f13d724b56bb87eb73` | 390 above ABC |
| V2 | `main` | `8d89c417cc717a0627969adc11c0f71160063758` | `1b2b824e9ce3743b97fcf7afaa48fe847f87848f` | 156 above ecashd |

`make -C daemon sync SERIES=v2` and `daemon_sources.py verify v2` both ran at the
final tips. The sync updated the parent's `daemon/sources.json`,
`daemon/stack-review.json` and staged gitlinks. Those are uncommitted.

Backup refs: `refs/backups/pre-4ab-ecashd` (`73ed9c43ed`),
`refs/backups/pre-4ab-lotusd` (`3131330948`), `refs/backups/4ab-lotusd-ckpt1`,
`-ckpt2`, `-ckpt3`.

## Decisions for owner review

1. **ecashd behaviour changed: explicit `TXRELAY_HIGH_BANDWIDTH` negotiation is
   back.** The stack's `77bc9fb0c9` carried an unrelated reversal of that
   negotiation across six files (`txrelay_index.h`, `net_processing.cpp/.h`,
   `protocol.h`, `txrelay_tests`, `v2_protocol_handler_tests`). V2's first commit
   `8ffb7e47fe` silently undid it, so V2 had negotiation and ecashd did not. All
   the 4b performance commits were written against the non-reversed form, and
   preserved `55756f6e98` describes isolating the commit from this reversal. I
   replaced `77bc9fb0c9` with preserved `ea7b6a9386` (same message, isolated
   patch). The V2 tree is unaffected. To reverse this, restore `77bc9fb0c9`'s
   hunks in `b930fac0fb`, but the 4b commits would then need rework.
2. **`9fa971b340` + `6e70bcae21` stayed one separate commit**, `910c80c77a`,
   rather than folding into the RPC drain commit. It is a distinct mechanism
   (asynchronous completion, awaitables, fences).
3. **`962cc0f66f` moved from V2 to ecashd** as `713dc49df5`. It has no V2 rules,
   and `commitment.cpp` is in ecashd. Its tests moved from V2-only
   `lotus_v2_tests.cpp` to `mempool_overlay_tests.cpp`. Author, date and message
   are unchanged, so the `[NATIVE]` subject prefix is now misleading.
4. **`f9a6aad483` and `39ccdbac31` stayed in V2 conservatively.** Both are
   candidates to split in phase 5:
   - `f9a6aad483` uses `RunParallelSigningWork`, `AddLegacySchnorr` and V2 monetary
     tests. ecashd still has unconsolidated `OverlayWorkerPool` and
     `SigningWorkerPool`.
   - `39ccdbac31`'s mechanism is shared (`SmtFind` exists in ecashd), but its test
     uses the V2-only `Coin.expiration_height`.
5. **Not integrated: a 4-line `policy_fee_tests` fix.** Preserved variant
   `7b414aacd3` of the admission-fee commit has this fix ("A successful admission
   can update local policy..."). It is absent from the pin and not named in the
   task, so I left it out. It is the only content difference between
   `db080db230` and the integrated ecashd base other than the listed fixups and a
   comment (see Verification).

## Outcome of every named commit

### 4a, ecashd

| Commit | Outcome |
|---|---|
| `f316d1831f` | Folded into `7178fc7dd1` rpc: publish immutable snapshots. Conflict resolved below. |
| `6c0e90dfa2` | Folded into `cc46bd526d` policy: compute local admission fees. Clean. |
| `94453bdd7d` | Folded into `4aa0e3ddda` net: announce by 8-byte short ids, using preserved variant `903e88c613` (same, plus two negotiation test hunks) and an amend for 94453's comment. |
| `9fa971b340` | Integrated as `910c80c77a` rpc: complete queued admissions through callbacks and awaitables. |
| `6e70bcae21` | Folded into `910c80c77a`. |

### 4a, V2

Hashes are final. Conflict-resolved restacks are described below.

| Commit | Outcome |
|---|---|
| `ccd348d557` | Folded into `66b9ccdf07` chain: brand daemon. Clean. |
| `2d06152a39` | Folded into `a957b815ea` consensus(v2): connect native state. Clean. |
| `fc94e9e640` | Folded into `9274a46c73` miner(v2): adapt O(1) overlay. Clean. |
| `1086dc10df` | Folded into `270dbcbeaa` validation(v2): prepare advisory native crypto. Clean. |
| `64176c73eb` | Folded into `270dbcbeaa`. Clean. |
| `4d77f464f4` | Folded into `270dbcbeaa`. Clean. |
| `13ff619f0f` | Already present through ecashd `910c80c77a` in all files but one test line. That line's V2 form is amended into `f0b708be57` rpc(v2): adapt blockchain (V2 RPC returns `GetId`, ecashd `GetHash`). |
| `bd9ec02d9b` | **Moved to ecashd.** The target commit is ecash-tier. Lands in `aef935bcf9` net: admit peer transactions, via patch-equal preserved `3381e41ebd`. Its `AdmissionLockTimer` hunk lands in `e2b5a31bf7` metrics: measure admission lock scopes, via preserved `0cc18e2f17`, because the timer does not exist earlier. |
| `aa1a3f1eb7` | **Moved to ecashd**, in `aef935bcf9`, same route. |
| `d78bd86556` | **Moved to ecashd**, in `aef935bcf9`, same route. |

### 4b, ecashd

All cherry-picks were clean, in the order of the source branch.

| Commit | New commit |
|---|---|
| `cbc4e72925` | `297c8cc497` net: resolve relay heap admission ranks |
| `f3cd28393c` | `676aa97985` net: reuse bounded persistent workers |
| `fec2cab9ce` | `814227aa5f` Consolidate validation work on the common range executor |
| `17e0aa086b` | `d8751ad437` Parallelize bounded SHORTTX decoding |
| `8dc53cadf6` | `a9dcfb56e3` Compare all 256 bits of radix keys |
| `2ec84cbbe9` | `320e13c82a` Extract radix nibbles directly |
| `948d9d0326` | `970a18ed86` snapshot: keep dependency edges as binary IDs |
| `4ca83ed0cc` | `3b261a9956` Add indexed relay inventory queue foundation |
| `597ee467a9` | Already present. The `PeekPrefix` fixup is already in `4ca83ed0cc`; verified. |
| `6e67af334b` | `57e40ddd25` Expose copied mempool admission suffix facts |
| `b106c9e7a7` | `b7cc063a82` Retain ranked peer inventory across relay ticks |

### 4b, V2

| Commit | Outcome |
|---|---|
| `962cc0f66f` | **Moved to ecashd** as `713dc49df5`. See decision 3. |
| `f9a6aad483` | `3d9e25d7eb` Consolidate native overlay and signing workers. Clean. |
| `26bed6b96b` | `0d407fc3e5` validation: reuse complete native staged script successes. Clean. Native rules, so it stays in V2. |
| `39ccdbac31` | `8d89c417cc` lotus: borrow SMT descendants. Clean. |

## Non-trivial conflicts

Reference trees were ecash perf `db080db230`..`b106c9e7a7` and V2 final-version
chain `a49f5b962b`..`39ccdbac31`.

**ecashd**

- `7178fc7dd1`, `src/rpc/mempool.cpp`: `f316d1831f` assumes hysteresis and
  `fee_info`, which arrive later in `7d1a384836`. Kept the scalar form at the
  parent and re-merged hysteresis at `7d1a384836`.

**V2, restack onto ecashd**

- `8ffb7e47fe` test: kept HEAD's comment. Its reversal-undo hunks disappeared, as
  expected from decision 1.
- `04dd49d442` rpc(v2): publish native state roots: V2 replaces the shared
  publisher with a 1024-entry ring and template history, while ecashd adds separate
  scalar publication. Small V2 adaptation: kept the ring, added
  `MempoolInfoSnapshot`, an `m_info` member and `LoadMempoolInfo()`, stored info
  under `m_publish_mutex` in `Publish`, and removed `using ChainTipSnapshot`. Kept
  both sides' tests. After 4b, took the V2 blobs of `snapshot.cpp/.h` and
  `snapshot_rcu_tests.cpp` and applied the V2 hunks of preserved `7e67f457cc`
  (TxId dependency edges).
- `f0b708be57` rpc(v2): adapt blockchain: merged includes and helpers; kept
  `co_return tx->GetId().GetHex();`.
- `67e877c949` policy(v2): relay and accept: removed `IsDisallowedNonV7Tx`, kept
  the async helpers.
- `a957b815ea` consensus(v2): whitespace only; took HEAD.
- `c62d7bd6f9` validation(v2): reconcile native batch: `validation.cpp` taken from
  reference `a9702c458e` (differences were only the conflict hunks and the pool
  removal). `rpc/mempool.cpp` took theirs, because V2's `RunParallelSigningWork`
  decode replaces the ecashd executor there.
- `6d135e3104` v2: run V2 input invocations: `if (n_pool > 0)
  { GetParallelRangeExecutor().Run(...) }` plus `control->Complete()`. Byte-identical
  to reference `949bb4767a`.

**V2 test adaptation, build break fixed in the causing commits**

`src/test/rpc_snapshot_read_tests.cpp` from ecashd `970a18ed86` did not compile on
V2 (`overlay_all_fit_candidate`, `GetMiningTemplate`, `ctor_active` do not exist
there). The file now matches reference `39ccdbac31` exactly:

- Mining-template API lines are folded into `04dd49d442`, where V2 removes that API.
- The native-transaction fixture is folded into `3d424a3eed` test(v2): validate
  native RPC snapshots, where the suite switches to `NativeSnapshotChainSetup`.

## Verification against the preserved work

- **ecashd 4a:** `git diff db080db230 3566595c1e` (the tip after 4a) contains only
  the listed fixups, HTTP move `221e907464` (already in the stack), the
  `policy_fee_tests` difference of decision 5, and a comment.
- **ecashd 4b:** `git diff db080db230 3566595c1e` and `git diff b106c9e7a7 b7cc063a82`
  have the same patch-id (`940c6c3b70`). The trees differ by the same amount before
  and after the ten picks, so those picks changed exactly what they changed in the
  preserved stack.
- **V2:** `git diff 39ccdbac31 HEAD` was reviewed before the test adaptation.
  Differences were the expected ones: async additions, `fee_hysteresis`, snapshot
  `m_info`, miner `fc94e9e640`, the `4d77f464f4` test, moved tests, a comment, and
  `policy_fee_tests`. The one unexpected item, the fixture above, is now resolved.

## Builds

All builds used `nice -n 10`, `ninja -j12 -k 0`, `CARGO_BUILD_JOBS=12`, under
`daemon/.build/`, targets `all test_bitcoin test-avalanche test-pow bitcoin-bench`.
`scripts/build.sh` was not used because it runs `ninja -j18` and builds only the
daemon and CLI targets. Configure flags matched it. Logs are in
`daemon/.build/logs/`.

| Build | Result |
|---|---|
| ecash tip after 4a, `3566595c1e` | Pass |
| ecash positions `cc46bd526d`, `4aa0e3ddda`, `aef935bcf9`, `e2b5a31bf7`, `b930fac0fb`, `910c80c77a` | Pass |
| ecash position `7178fc7dd1` | **Fail**: `preconsensus_batch_tests.cpp:711`, `updatedBlockTip` is private. Not caused by the fold, which touches only `snapshot.cpp/.h`, `rpc/mempool.cpp`, `snapshot_rcu_tests`, `atomic_snapshot.h`. Inferred pre-existing at that position; not baseline-built. Later positions pass. |
| ecash positions, all 11 4b commits through final `713dc49df5` | Pass |
| V2 tip after 4a, `0f3eece88f` | **Fail** on `test_lotus_v2_candidate_body_pool` only |
| V2 tip after 4b, `8fa2c9c9f0` | **Fail**: `rpc_snapshot_read_tests.cpp` (fixed, above) and `test_lotus_v2_candidate_body_pool` |
| V2 final `8d89c417cc` | **Fail** on `test_lotus_v2_candidate_body_pool` only. `lotusd` and every other target build. |
| Baseline: `test_lotus_v2_candidate_body_pool` at old pin `3131330948`, exported copy, Chronik off | **Same failure**, so pre-existing |

`test_lotus_v2_candidate_body_pool` fails to link because the test defines global
`operator new/delete` while the build force-loads `libjemalloc_pic.a` (four
duplicate symbols). It is not an integration break and was left unfixed.

### V2 positions

I built nine V2 commits that took a fold or a hand resolution (log
`posbuild-v2.txt`). `67e877c949` policy(v2) and the first commit, successor of
`8ffb7e47fe`, were hand-resolved but not position-built. **Eight of the nine fail. I found none caused by this
integration.** V2's interior commits did not build before this work either:
they use declarations that arrive in later commits. I compared each failure against
the same-subject commit in the old pin by inspecting the source, not by building
those pin commits. Only the `candidate_body_pool` link failure has a baseline build.

| Commit | Result | Cause |
|---|---|---|
| `66b9ccdf07` chain | Pass | |
| `a957b815ea` consensus(v2) | **Configure fails** | `src/test/CMakeLists.txt` lists `v2_wallet_tests.cpp`, added later by the wallet commit. Pin `31910defb2` has the same. |
| `9274a46c73` miner(v2) | **Fail** | `FeeHysteresisController`, `ComputeMerkleRootFromLeftSpine` used before declared. Pin `3440002c19` has the same references and no declaration. |
| `04dd49d442` rpc(v2): publish | **Fail** | `rpc/mining.cpp` not yet adapted (next commit), and `validation.cpp` as below. Source-level comparison covered only part of the `rpc/mining.cpp` error list. No `rpc_snapshot_read_tests.cpp` error, so that fold works here. |
| `f0b708be57` rpc(v2): adapt | **Fail** | `validation.cpp`: `ScopedChainSnapshotDefer`, `PublishBestHeaderSnapshot`, as below. |
| `3d424a3eed` test(v2) | **Fail** | Same. Pin `0afdaf8613` has the same references and no declaration. Its `validation.cpp` differs from ours only by the `fec2cab9ce` executor change. No `rpc_snapshot_read_tests.cpp` error. |
| `c62d7bd6f9` validation(v2): reconcile | **Fail** | `addUnchecked` called with 4 arguments, declared with 3. Pin `b1a34d7c65` has the identical call and declaration. |
| `6d135e3104` v2: input invocations | **Fail** | `ecash_state_sync_tests.cpp`: `m_coinbase_version` undeclared. Declared later by `1dcfa13f48` mining(v2). Pin `425dbf80a2` has the same references and no declaration. |
| `270dbcbeaa` validation(v2): prepare | **Fail** on `candidate_body_pool` only | Pre-existing, above. |

`test_lotus_v2_candidate_body_pool` also fails at each position that gets that far.
Because the interior does not build, V2's per-commit build gate cannot currently be
met, and the V2 folds are verified at the final tip rather than at their own commits.
Making the interior bisectable was not attempted: it is out of scope and would be
reordering, not integration.


## Tests

Only tests new in the integrated commits were run, as filtered cases. No full
suites. **All listed cases passed.** Logs: `test-ecash-4a.log`, `test-ecash-4b.log`,
`test-v2-4a.log`, `test-v2-4b.log`.

- **ecashd at `3566595c1e`:** `snapshot_publication_concurrent_coherent_scalars`;
  txrelay `stock_peer`, `private_relay_requires`, `private_relay_local`,
  `no_body_push_by_default` cases; `v2_protocol_handler` `permissions_follow_fixed_relay_tick`,
  `single_tx_relays_wait_for_the_relay_tick`; txadmission `retained_*` (2);
  validationinterface async cases.
- **ecashd at `713dc49df5`:** `util_tests` `parallel_range_*` (2);
  `v2_protocol_handler_tests` `shorttx_parallel_decode_matches_serial_wire` plus 2;
  `radix_tests` (4); `rpc_snapshot_read_tests` `snapshot_graph_ids_*` (1);
  `relay_inventory_queue_tests` (6); `mempool_tests` `relay_admission_suffix_*` (3);
  `txrelay_tests` `persistent_inventory_*` (3); `mempool_overlay_tests`
  `transaction_subtree_a_*` (2); `validationinterface_tests` admission cases (3);
  `mempool_admission_tests` `rpc_barrier_survives_throw_after_callback_registration`.
- **V2 at `0f3eece88f`:** `shorttx_uses_bounded_admission_and_orders_following_ping`,
  `permissions_follow_fixed_relay_tick`, `single_tx_relays_wait_for_the_relay_tick`;
  `v2_staged_native_signatures_warm_*`, `v2_async_admission_prepares_without_cs_main`;
  `validationinterface_tests` (8); `snapshot_publisher_concurrent_rcu_stress`;
  txrelay (4); txadmission (2).
- **V2 at final `8d89c417cc`:** `native_signing_work_uses_common_executor_fallback`,
  `v2_nullfail_and_batch_sig_collector`, `v2_staged_native_success_reuse_and_authoritative_fallback`,
  `v2_staged_native_deferred_results_are_not_reused`; `mempool_overlay_tests` (5:
  `overlay_roots_survive_*`, `smt_lookup_*` (2), `transaction_subtree_a_*` (2));
  `snapshot_graph_ids_*`; `v2_protocol_handler_tests` (4); `parallel_range_*` (2);
  `radix_tests` (4); `relay_inventory_queue_tests` (6); `relay_admission_suffix_*`
  (3); `persistent_inventory_*` (3); `rpc_barrier_survives_*`;
  `validationinterface_tests` admission cases (3); `snapshot_publisher_concurrent_rcu_stress`.

An earlier V2 test run after 4b was discarded. `test_bitcoin` had failed to compile,
so the run used a stale binary, and most filters matched no cases.

## Tooling defects found

- **Rerunning sync after a hand-resolved cascade replays the wrong range.**
  AGENTS.md says to resolve and rerun. But a failed sync never saves the new ecash
  tip, so the cascade uses the old tip as its base. That tip is still an ancestor
  of V2 HEAD, so it started replaying the ecash perf commits (it stopped at
  `297c8cc497`). I aborted and ran `Project.sync('v2')` with `_cascade_children`
  stubbed out, from a scratch script. `daemon_sources.py` was not changed.
- **`scripts/build.sh`** ignores the job limit needed on this machine (`-j18`).
