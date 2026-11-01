# Header history integration (plan phase 4d)

Integration of the seven audited commits into Lotus V2, following [header-history.md](header-history.md). Nothing was pushed, and no production node or `daemon/workspace-v1` was touched.

## Final state

| Tier | Branch | Tip | Tree |
|---|---|---|---|
| Lotus V2 | `main` in `daemon/lotusd` | `d2aefc19ba528933b0a7ef443eb383dee5729001` | `05d8896c34c604b761a82ebfbbfe7f7fcf97afe3` |
| Shared engine | `ecashd` in `daemon/ecashd` | `b92c9ec65a` (unchanged) | `36fe0013dbcb663463d3690bc083e4611ce776c4` |

The topic is seven contiguous commits on top of `4a1f9a8e10`. Backups are under `refs/backups/4d/` in `daemon/lotusd`; `main-before` is the starting tip.

`make -C daemon sync SERIES=v2` recorded these tips in the working tree of the parent repository: `daemon/sources.json`, `daemon/stack-review.json` and the staged `daemon/lotusd` gitlink. `docs/lotus-v2/header-history-tree.md` and this report are also uncommitted. The ledger (`stack-ledger.json`) and topics file (`stack-topics.json`) were not updated.

## Source commits

| Source | Audit verdict | Outcome | Commit in V2 |
|---|---|---|---|
| `d35486f823` | pass | Landed, with a written message | `8bb8cbb945` rpc(v2): bind verifytxoutproof to the local block body |
| `b64c479f54` | fix | Landed. Count bound into the root, file format removed | `1ec1ddb7db` lotus_v2: add the header history tree and its frontier |
| `e51a216083` | fix | Landed. Fixture constants moved out to the commit that changes hashes; `AdvanceMonetary` no longer carries the parent's root | `54571c1472` lotus_v2: add history_root to the committed monetary state |
| `044e2575da` | fix | Landed. The tree is memory only | `ddca096a86` validation: keep a header history tree on each Chainstate |
| `02daf12fa5` | fix | Landed. Missing frontier fails, fast-sync checks the root, fixtures regenerated here | `a23aa87e0e` lotus_v2: commit each block's history root in its state root |
| `da9b570e5a` | hold | **Left out.** No RPC exists | none |
| `4f611ecbe2` | fix | Landed. RPC and file tests removed, missing coverage added | `d2aefc19ba` test: cover the header history tree and its commitment |
| (new) | H2 | New commit | `747221cd3b` wallet(v2): check importprunedfunds proofs against the block |

## Findings

"Reproduced" means a test written first failed on the code before the fix (with the source commits picked but unfixed). Output is summarised under [What was run](#what-was-built-and-run).

| Finding | Outcome |
|---|---|
| **H1** proofs can't be tied to a header | **Not fixed; the RPC stayed out.** Making it correct isn't simple: it needs an anchor definition, a proof format that opens `state_root`, and a verifier that resolves a header. The spec's status now says the RPCs are not implemented and sets out the open question. See [Questions for the owner](#questions-for-the-owner). |
| **H2** `importprunedfunds` accepts forged proofs | **Confirmed and fixed in V2. Reproduced.** The forged proof imported and the wallet recorded the transaction. It does not apply to `ecashd`: that tier still compares the proof's root to `header.hashMerkleRoot` (`src/wallet/rpc/backup.cpp:468`). V2 dropped that comparison because its headers commit a native root. The RPC now needs the block on disk and refuses on a node that pruned it. |
| **M1** `total_count` unauthenticated | **Fixed. Reproduced** (leaf 0 of 65 verified claiming 66, 100 and 128; leaf 0 of 100 verified claiming 65). `root = H(chain_id \|\| 0x02 \|\| u64_le(count) \|\| tree_root)`, with the null root kept at count 0. Spec and fixtures updated. |
| **M2** no integrity check on the tree file | **Fixed by removing the file**, after confirming `m_chain` holds every hash. `CChain::SetTip` fills every ancestor from `pprev`. Pruning deletes only block and undo files, not index entries. A snapshot needs its base header in the index, and index entries link to genesis. The rebuild reads no block data. This also removes L1 and L2 for the tree, and the flush-time rewrite in L3. Rebuild cost at startup was not measured. Test: `blocks_commit_root_of_all_ancestors_and_tree_rebuilds`. It clears and rebuilds the tree on an unpruned chain; the pruned and snapshot cases rest on the code reading above, plus the snapshot path in `feature_assumeutxo.py`. |
| **M3** missing parent frontier gives a wrong root | **Fixed. Partly reproduced:** the non-null root for an unknown parent failed on the unfixed code, but the `ConnectBlock` half did not. It reported a valid block there because `SetV2StatePersistDir("")` did nothing in that version of the test, so the `state.Error` path was never shown failing before the fix. The test now uses an empty temporary directory. One helper now derives the frontier for all three paths. The side map `g_v2_next_frontier_by_prev` is gone. A frontier that is missing or doesn't cover exactly `nHeight - 1` blocks gives a null root, and `ConnectBlock` returns `state.Error`, so the block isn't marked invalid. The block relay code treats a null root as a mismatch, as it did a wrong root. Several tests depended on the old fail-open path and had to state their assumptions; see the V2 commit message. |
| **M4** fast-sync doesn't check the commitment | **Fixed. Reproduced** (pivots committing a zero root and a wrong root were both accepted and activated). The pivot's root must equal the one derived from local headers. Peel and assumeutxo derive it and let the header comparison authenticate it. The zero-root branches and the optional message field are gone. **`StateRoot` itself still accepts a zero root above height 0**, because the library engine (M6) produces those; the rejection is in the node's fast-sync path. |
| **M5** stale regtest 299 entry; series doesn't bisect | **Confirmed and fixed.** The 299 entry was stale: on the unfixed code `feature_assumeutxo.py` failed with `assumeutxo block hash in snapshot metadata not recognized`. Entries 110 and 299, `test_assumeutxo` and the functional test's hashes are regenerated in the commit that starts computing roots, so `test_assumeutxo` passes at each commit. The functional test's spend amount is also corrected, from 24,990,000 to 2,500. |
| **M6** lossy encoding, library engine | **Partly fixed, and not in the decisions list.** `AdvanceMonetary` returns a zero root, so a forgotten overwrite fails. Still open: `EncodeMonetaryState` drops the root, `DecodeMonetaryState` accepts 56 or 88 bytes, and the library engine (`StageCompleteBlock`, `PeelBlockReverse`) doesn't implement the commitment. The commit message says so. See [Questions](#questions-for-the-owner). |
| **L1** no fsync | Gone for the tree. **Open** for `WriteV2BlockStateFile`, which still doesn't sync before the rename. |
| **L2** shared path, dead flag | Fixed by removing the file and `m_coinsdb_in_memory`. |
| **L3** linear cost | Whole-file rewrite and double load are gone. The 96 bytes per block in memory remain. |
| **L4** trailer handling | Fixed in part: the trailer is mandatory, trailing bytes are rejected, and the count is checked against height at use. **Open:** a read failure partway down a delta chain is still treated as reaching an unpersisted genesis (older behaviour). |
| **L5** O(H) work per call | Peel reads from the tree when the parent is on the active chain; the redundant frontier in `AdvanceV2BlockMonetaryState` is gone; a missing ancestor now asserts. Activation still does one O(H) pass. |
| **L6** spec drift | Spec updated. The aliases went with the RPC. |
| **L7** trailing bytes after a `CMerkleBlock` | Not changed; the audit marked it optional. |
| **L8** fixed test temp path | Gone with the persistence test. New tests use unique directories. |

## What was built and run

**Reproduction on the unfixed picks:** four new tests produced 16 failures, covering M1, M3 (the root half only), M4 and H2. Plain `feature_reindex.py` passed on that binary.

**All targets:** `ninja -j12 -k 0` in `daemon/.build/v2`. Everything built at the final tip except the known `test_lotus_v2_candidate_body_pool` link failure, which is the only failed target.

**Per commit:** each topic commit was checked out, built (`test_bitcoin`, `lotusd`) and had its own tests run. This was not all targets at each commit.

```text
8bb8cbb945  build ok  merkleblock_tests                                    pass
747221cd3b  build ok  wallet_tests/importprunedfunds_rejects_forged_proof  pass
1ec1ddb7db  build ok  validation_tests                                     pass
54571c1472  build ok  validation_tests, ecash_state_sync_tests             pass
ddca096a86  build ok  validation_tests, ecash_state_sync_tests             pass
a23aa87e0e  see note  validation, chainstatemanager, miner, candidate state,
                      protocol handler, state sync, shard tests            pass, earlier tree
d2aefc19ba  build ok  lotus_v2_header_history_tests                        pass
```

Note on these results: after this table was run, I moved one removal down into `ddca096a86` and folded regenerated height 299 values into `a23aa87e0e`. `ddca096a86` was then rebuilt and retested, which is the row above; it had failed to build before that move. The checks in the `a23aa87e0e` row ran on its earlier version `9870c34035`; the final tree, which differs by that move and the 299 values, was not built or tested on its own. The tip, which carries the same values, was. The first four commits keep the same trees they were tested with, though their hashes changed when messages were rewritten.

**Mistake caught along the way:** my first regeneration of the height 299 values used a functional test chain cache created by the unfixed binary. `feature_assumeutxo.py` then failed after `-reindex`, with block 1 rejected as `bad-blk-stateroot`, because the cached blocks had old roots. No code was at fault. I deleted that cache and regenerated all the values from a clean one, and the whole test then passed.

**Unit suites at the tip, all passing:** `lotus_v2_header_history_tests`, `validation_tests`, `ecash_state_sync_tests`, `native_state_sync_tests`, `v2_candidate_state_tests`, `fast_sync_shard_tests`, `mempool_overlay_tests`, `validation_block_tests`, `miner_tests`, `merkleblock_tests`, `v2_protocol_handler_tests`, `validation_chainstatemanager_tests`, `wallet_tests`, `blockfilter_index_tests`, `tx_verify_bridge_tests`, `pmt_tests`.

**Functional at the tip:** `feature_assumeutxo.py` (whole test, including background validation, restarts and `-reindex`), `rpc_txoutproof.py` and `feature_reindex.py` pass, using a chain cache generated by the final code. `feature_assumeutxo.py` needs the `protobuf` Python module, which I installed in a scratch directory.

Known-answer vectors were computed with a Python script from the spec's formulas using the `blake3` package, and match the node. No full suite was run, as instructed.

## Open

- **`wallet_importprunedfunds.py` doesn't reach the changed RPC.** It stops at line 62 with `Insufficient funds`, because it sends a hard-coded 100,000 from a chain with far smaller coinbases. It fails the same way without the wallet fix, and I didn't change it. So the wallet fix is covered by the new unit test, not by this functional test.
- **Pruned startup wasn't run.** The tree rebuild for a pruned node is confirmed by reading the code only.
- **M6, L1 (state files), the older L4 path and L7** remain as described above.
- **`StateRoot` still accepts a zero root above height 0.** Only the node's fast-sync path rejects it.
- **Spec and P02 differ:** see question 5.
- **Bookkeeping:** `daemon/stack-ledger.json` and `daemon/stack-topics.json` don't record this topic yet. Nothing has been published, so the parent gitlink points at unpushed commits until a publish.
- **The full sweep hasn't run.** Hard-coded block hashes or amounts in tests outside the suites above may still need regenerating; every block hash above genesis changed.

## Questions for the owner

1. **What is a proof's anchor?** Block `H` commits only the `H` blocks below it. So either the anchor is the highest block covered, whose root is committed by block `H+1`, and the tip's root isn't committed by anything yet; or the anchor is the block whose header commits the root, so the count equals its height and height 0 can't be an anchor. The audit recommends the second. Spec section 3.5 has the rest of what the RPC needs.
2. **Should the tree stay on `Chainstate`?** With the RPC out, its only consumer is the fast-sync peel, which could rehash instead. It costs about 96 bytes per block in memory. I kept it because the proof work will need it. Remove it if proofs aren't coming soon.
3. **Should the library engine implement the commitment (M6)?** Until it does, its roots above genesis don't match real headers, and `StateRoot` can't require a non-null root above genesis.
4. **Does V2 still need `importprunedfunds`?** It no longer works for the pruned case it was written for.
5. **P02 needs the count binding.** `docs/lotus-v2/decisions/commitments-and-state.md` describes the history root, and I was only permitted to edit `header-history-tree.md`, so P02 doesn't mention the binding yet.
