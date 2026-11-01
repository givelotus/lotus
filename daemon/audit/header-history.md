# Header history audit

Audit of seven Lotus V2 commits against `docs/lotus-v2/header-history-tree.md`.

This was a read-only audit of git objects. Nothing was built or run, so no finding has been reproduced. Each finding is marked **Confirmed** (traced through the code by hand) or **Suspected** (inferred, and the gap is stated).

Paths are relative to `daemon/lotusd`. Line numbers are at `4f611ecbe2` unless noted.

## Verdicts

| Commit | Subject | Verdict | Reason |
|---|---|---|---|
| `d35486f823` | Bind `verifytxoutproof` to the local body | **pass** | No bypass found. Only test gaps remain. The wallet has the same flaw (H2), which needs its own commit. |
| `b64c479f54` | `HeaderHistoryFrontier` and `HeaderHistoryTree` | **fix** | The tree algorithm is correct. `total_count` is unauthenticated (M1), and the file loader has no integrity check (M2). |
| `e51a216083` | Commit to `history_root` in `MonetaryState` | **fix** | A regtest fixture looks stale (M5), the encoding drops the root (M6), and `StateRoot` accepts a zero root at any height (M4). |
| `044e2575da` | Maintain and persist the tree on `Chainstate` | **fix** | Reconciliation is correct, but the file is an unverified cache that can be removed (M2, L1, L2, L3). |
| `02daf12fa5` | Wire the frontier through snapshots and templates | **fix** | The normal path is sound. A missing parent frontier fails open (M3), and fast-sync doesn't check the commitment (M4). |
| `da9b570e5a` | Header history RPCs | **hold** | A proof can't be tied to a header (H1). Fixing it needs a decision on anchor semantics and proof format. |
| `4f611ecbe2` | Tests | **fix** | One test skips the case that exposes M1, and restart, fast-sync, snapshot and template paths have no coverage. |

**No critical finding.** I found no consensus divergence on the normal paths. There are two high findings: H1 is in this series, and H2 is an older wallet flaw of the same kind that `d35486f823` fixes.

**Fix M1 first if you choose to bind the count into the root.** That changes every consensus root and every derived fixture.

### Before merging

- **Branch:** these commits are on `snowstorm/*` branches, not `main`. `4f611ecbe2` and `main` diverge from merge base `0a880a8a40`, with 531 and 518 commits on each side. `daemon/AGENTS.md` says Snowstorm work enters a stack only if the owner says so.
- **After moving them:** the validation line numbers will shift, and the `chainparams` assumeutxo constants will need regenerating on the target tip. I didn't audit how the commits interact with `main`.
- **Identity:** all seven commits have author and committer `Canonical patch progression <patch-progression@localhost>`, and no message body. `daemon/AGENTS.md` requires the project identity and messages that explain the change.

## Answers to the audit questions

### Consensus

| Question | Answer | Evidence |
|---|---|---|
| Is the root deterministic? | Yes on normal paths. The frontier is derived from the parent's frontier plus the parent hash, keyed by block hash. | `primitives/block.cpp:640-676, 848` |
| Does it depend on restart path? | No in normal operation. Each `.bin` file stores its frontier, and the root is recomputed on load. | `primitives/block.cpp:251-254, 324-326, 548-550` |
| Reorg and undo | Sound. Frontiers are per block, so a fork can't inherit another fork's frontier. The on-disk tree reconciles separately. | `validation.cpp:6769-6770, 6994-6995` |
| Reindex | Sound. Blocks are replayed through `ConnectBlock`, and a wipe removes the tree file. | `validation.cpp:4320-4325` |
| Assumevalid | Not skipped. The state root check is outside the `fScriptChecks` condition. | `validation.cpp:6225-6243` |
| Snapshot load | Same frontier, built from header ancestors. The chain is set before the tree syncs. | `validation.cpp:11393-11395, 11426-11431` |
| Fast-sync | Same frontier for honest chains, but see M4. | `validation.cpp:3718-3751` |
| Pruned startup | Unaffected. The frontier comes from `.bin` files and the block index. I found no `.bin` deletion in `primitives/block.cpp` or `node/blockstorage.cpp`. | `node/blockstorage.cpp:737-739` removes only block and undo files |
| Genesis | Correct. An empty frontier gives a null root and the 130-byte preimage, so the genesis hash is preserved. Height 1 commits `HeaderLeafHash(0, genesis)`. | `lotus_v2/sparse_state.cpp:397-407`, `lotus_v2/header_history.cpp:83-90` |
| Validation vs template | Same inputs and same formula on all paths I traced. The lookup logic is written out three times, which invites drift. Template reuse is guarded by same parent hash, height and MTP. | `primitives/block.cpp:640-671, 1392-1417, 1436-1469`, `node/snapshot.cpp:474-479` |

The exceptions are the fail-open path (M3) and the fast-sync gap (M4).

### Tree correctness

Hand traces of the fold, proof builder and verifier agree, including these boundaries:

- **Counts:** 0, 1, 2, 3, 4, 5, 6 and 65, covering powers of two and partial right edges.
- **Large counts:** shifts and depth stay in range up to `D = 64`, and `(idx + 1) << k` can't overflow when `idx` is even.
- **Domain separation:** the leaf prefix `0x00` and internal prefix `0x01` are distinct, and payloads differ in length (73 and 98 bytes). Level, height and chain ID are all hashed. I found no second-preimage route (`header_history.cpp:40-59`).
- **PopBack:** it trims each level to `count >> k`, and the frontier is rebuilt correctly (`header_history.cpp:272-290`).
- **Index bounds:** the builder and verifier both reject `height >= count` and `total_count == 0`.

The one defect is that `total_count` isn't authenticated (M1).

### Persistence

- **Crash between writes:** safe. The tree is saved before the coins flush (`validation.cpp:6519-6526`), and it only ever feeds consensus through the side map (see M3). On restart, `SyncHeaderHistoryTreeToChain` pops and re-appends until the file matches `m_chain` (`validation.cpp:4371-4418`).
- **Crash during write:** temp file and rename leave the old file in place.
- **Missing or truncated file:** rejected, and rebuilt from the chain.
- **Corrupt file:** not detected unless the size is wrong or the top leaf differs (M2).
- **Durability:** no fsync (L1).
- **Growth:** linear and in practice bounded, but rewritten in full under `cs_main` (L3).

### RPC

- **Input bounds:** adequate. Heights are range-checked, `stoi` is guarded, and the proof decoder requires an exact length with at most 64 siblings. Oversized input is limited only by the RPC body limit.
- **`cs_main`:** short after startup. `getheaderhistoryproof` does an O(log H) build. `verifyheaderhistoryproof` takes no lock.
- **Can it be misread?** Yes (H1, M1).

### `d35486f823`

I found no bypass.

- **The fix:** the old code returned `vMatch` without comparing the proof's root to anything. The new code requires all of the following (`merkleblock.cpp:235-290`):
  - the body hashes to the expected block hash
  - the native `BlockMerkleRoot` matches the header and isn't mutated
  - the proof's root equals the legacy root computed from the local body
  - every matched txid equals the body's txid at that position
- **Witness binding:** `BlockMerkleRoot` covers both `TxHash` and `TxId` (`consensus/merkle.cpp:86-99`), so witness tampering in the local body is caught.
- **Missing body:** throws "Block not available (pruned data)" when `hasData()` is false.
- **Unreadable or corrupt body:** throws. Neither case returns an empty or a success result.
- **Reorg during the unlocked read:** rechecked afterwards, and it throws.

Not read: `TransactionRoot` internals and `ReadBlock`. The authentication doesn't depend on `ReadBlock` checking anything.

### Tests

See [Test assessment](#test-assessment).

## Findings

### H1: Proofs can't be tied to a chain header, and `valid: true` is easy to misread

**High. Confirmed. `da9b570e5a`.**

Four things combine:

1. **Caller-supplied root.** `verifyheaderhistoryproof` takes `expected_root` from the caller and only checks the hash chain (`rpc/blockchain.cpp:4056-4078`). It doesn't consult the active chain. The spec promises anchor resolution with `[expected_root_or_anchor]` (spec section 3.4), which isn't implemented.
2. **Anchor off by one.** The RPC uses `target_count = anchor.nHeight + 1` (`rpc/blockchain.cpp:3984-3985`), but block `H` commits only `H` leaves. So `history_root` at anchor `H` is committed by block `H+1`, not by the anchor. The test records this: "total_count == 51 means history_root is committed in block 51" for anchor 50 (`src/test/lotus_v2_header_history_tests.cpp:570`).
3. **Default anchor is uncommitted.** With the default tip anchor, the returned root isn't committed by any existing block.
4. **No path from root to header.** The root sits inside `StateRoot(chain, height, utxo_root, monetary || history_root)`. A client needs the UTXO root and monetary state to open it. The proof format doesn't carry them. A grep of `src/rpc` and `src/node` for likely field names found no RPC returning them, though other spellings aren't excluded. Spec section 1 says the latest header plus a proof of about 1 KB is enough, which the format doesn't deliver.

**Failure scenario:** a light client or bridge fetches `proof_hex` and `history_root` from an untrusted node and verifies them, as the tests do at lines 529 and 584. The node builds its own tree containing a fabricated block hash at height `h`. The result is `valid: true` with that hash and height.

An honest client can't do better through this interface, because it has no way to compare the root to a header. Nothing in the tree consumes these RPCs yet, so there is no live exposure today.

**Fix (needs a decision):**

- Define the anchor as "the block whose header commits this root", so the count equals the anchor height. Reject an anchor at height 0.
- Add an opening to the proof: `utxo_root` and the 56-byte monetary state. Verify it against the anchor's `state_root`.
- Make `verifyheaderhistoryproof` take an anchor block and resolve the header itself. If a raw-root mode stays, make it explicit and name the result `hash_chain_valid` with `anchored: false`.
- Update the help text, which still says "MMR" and "peak bagging", and add the spec's `anchor_height` and `anchor_block_hash` fields.

### H2: `importprunedfunds` accepts forged proofs (not in this series)

**High. Confirmed. Older code, from `2294f519a2`.**

This is the flaw `d35486f823` fixes, in a second consumer. `src/wallet/rpc/backup.cpp:468` only checks that `ExtractMatches(...)` isn't null. It never compares the root or the transaction count to anything. It then records the transaction as `CONFIRMED` in the named block (`backup.cpp:483-497`). The RPC is registered at `backup.cpp:2522`, and `BUILD_WALLET` defaults to on (`src/CMakeLists.txt:17`).

**Failure scenario:** someone sends a victim a transaction paying the victim's wallet, plus a hand-built `CPartialMerkleTree` containing that txid and any real block's header. The victim imports it. The wallet shows a confirmed payment that was never mined.

**Fix:** in a new commit, read the body and call `VerifyMerkleBlockAgainstAuthenticatedBlock`, and refuse when the body isn't available. This loses the RPC's pruned-node use, so consider whether it should survive at all in V2.

### M1: `total_count` isn't authenticated

**Medium. Confirmed. `b64c479f54`.**

The root doesn't commit to the count, and `VerifyHeaderInclusionProof` only uses `total_count` for the depth and the null-sibling pattern (`header_history.cpp:108-128`).

**Worked example:** take a real tree of 65 leaves and the proof for leaf 0, then change `total_count` to 66.

- The depth is still 7.
- Every sibling is non-null, and every `right_subtree_start` (`1 << k`, at most 64) is below 66.
- The hash chain is unchanged, so the proof verifies.

Any claimed count from 65 to 128 works for that leaf. Claims can also understate: leaf 0 in a tree of 100 verifies with a claim of 65. The RPC reports the claimed value as fact (`rpc/blockchain.cpp:4088`). The test suite avoids this case by trying `target_count + 1` only for the last leaf (`src/test/lotus_v2_header_history_tests.cpp:195-199`).

The leaf's position and hash remain bound, so this doesn't allow a false inclusion. It does make proofs malleable, and a client that reads `total_count` as the chain length at the anchor is wrong.

**Failure scenario:** a client treats `total_count` as the anchor's height, without comparing it to a header, and accepts a proof against a root from a different height.

**Fix:** since V2 is unreleased, bind the count: `root' = H(chain_id || 0x02 || u64_le(count) || tree_root)`, keeping the null root at count 0. This changes all roots, so regenerate fixtures. Separately or instead, give the verifier a required `expected_total_count` taken from the anchor header.

### M2: The tree file has no integrity check

**Medium. Confirmed. `b64c479f54`, `044e2575da`.**

`LoadFromFile` checks the magic, the lengths and the absence of trailing bytes (`header_history.cpp:441-514`). It doesn't check that the frontier, leaf hashes and levels agree with each other. `SyncHeaderHistoryTreeToChain` compares only the top leaf to the chain (`validation.cpp:4371-4378`). The file has no checksum and no chain ID.

**Failure scenario:** a bit flips in `m_levels` or `m_frontier` while the size stays correct.

- `getheaderhistoryproof` returns wrong siblings, or a wrong root with a matching wrong proof. The verifier then reports `valid: true` for a root no block commits.
- A flip in `m_block_hashes` changes the hash inside `proof_hex`, while the separate `block_hash` field still shows the correct value from the index.
- A corrupt `m_frontier` also reaches the consensus side map (`validation.cpp:4374`). It takes effect only when a parent frontier is missing (M3).

The corruption persists: it is saved back on every flush and survives until the file is deleted or a reorg pops past it.

**Fix:** delete the file. `m_chain` already has every hash, and the existing reconcile loop rebuilds the tree. That's roughly two hashes per block at startup, which I'd estimate at seconds for millions of blocks (not measured). This also removes L1, L2, the flush-time append and pop at `validation.cpp:6499-6518`, and most of L3. If the file must stay, recompute all levels from the leaves on load and compare them.

### M3: A missing parent frontier silently produces a wrong root

**Medium. Confirmed code path, narrow trigger. `02daf12fa5`.**

If the parent frontier is unavailable and the side map misses, the code appends the parent hash to an empty frontier. It gets `count = 1` at any height, with no error (`primitives/block.cpp:665-671, 1415-1417, 1464-1469`). No code checks that the frontier count equals `nHeight`. `ConnectBlock` then rejects the block with `bad-blk-stateroot` as `BLOCK_CONSENSUS` (`validation.cpp:6238-6243`).

**Failure scenario:** a local state problem makes a node permanently mark a valid block invalid, and it stays on its own fork. This could be a damaged trailer on a full or imported snapshot, or a parent loaded without a frontier, combined with a side-map miss. The side map is bounded to 512 entries and cleared when full, and it only holds entries from chain tips.

I didn't find a trigger in normal operation. A missing parent already gives a wrong UTXO root here (older behaviour), so this path adds another way to fail rather than the first one.

**Fix:**

- Add one helper for the three copies. It returns an error unless the parent frontier exists with `count == nHeight - 1`. Surface that as `state.Error`, not `state.Invalid`.
- Remove `g_v2_next_frontier_by_prev`. Its only effect is to support parents without a frontier, which shouldn't exist.
- Treat a missing `.bin` trailer as corruption (L4).

### M4: Fast-sync doesn't check the history commitment

**Medium. Confirmed. `e51a216083`, `02daf12fa5`.**

There are two gaps in `ActivateVerifiedFastSyncPivot`:

- **No comparison.** The peer's `history_root` is checked against the header's state root (`validation.cpp:3734-3739`) but never against the locally derived `pivot_frontier`. The import then overwrites it with the derived root (`primitives/block.cpp:1631-1634`).
- **Zero root accepted.** If the zero-root preimage matches the header, a pivot above height 0 is accepted with no history commitment (`validation.cpp:3721-3733`). `PeelFastSyncBlock` tolerates the same case (`validation.cpp:4077-4088`). `StateRoot` has no height check to prevent it (`lotus_v2/sparse_state.cpp:397`).

**Failure scenario:** a pivot header has proof of work but commits a wrong or zero `history_root`, which full validation would reject.

- A fast-syncing node accepts it.
- For a wrong root, the stored root differs from the header's, so the next restart fails in `LoadChainTip`, where the state root comparison returns false (`validation.cpp:9312-9313`).
- `ExportUtxoRoots` also refuses to serve that pivot (`lotus_v2/fast_sync.cpp:701-705`).

`StartFastSyncSwarm` is only called from an RPC (`rpc/blockchain.cpp:3747`), so the operator picks the pivot and this isn't remotely triggerable by choosing a pivot. I didn't assess how a node would come to hold such a header as its choice.

**Fix:**

- Require `monetary.history_root == HeaderHistoryRoot(pivot_frontier)` at the pivot and in the peel, using the frontier as the expected value rather than a fallback.
- Delete both zero-root branches and the 56-byte tolerance. `daemon/AGENTS.md` and the project's unreleased-tier rule don't call for compatibility here.
- Make `StateRoot`'s form depend on height: a null root only at height 0, and a non-null root above it.
- For assumeutxo, deriving the root from headers is reasonable. The second clause at `validation.cpp:11403-11407` should go.

### M5: The regtest 299 assumeutxo entry looks stale, and the series doesn't bisect

**Medium. Stale entry Suspected. Bisect break Confirmed. `e51a216083`.**

- **Stale entry (Suspected).** `e51a216083` updates the height 110 assumeutxo entry but not height 299 (`kernel/chainparams.cpp:481-497`). Both were last regenerated together in `d2d7c38b04`. Block hashes cover the state root, and the state root changes at every height above 0. So the 299 `blockhash` should change too, and `feature_assumeutxo.py` (`SNAPSHOT_BASE_HEIGHT = 299`) should fail. I didn't run it. The series touches no functional test for this.
- **Bisect break (Confirmed).** `e51a216083` changes the height 110 constant, but `test_assumeutxo` isn't updated until `4f611ecbe2`. The unit test therefore fails on the four commits from `e51a216083` to `da9b570e5a`. The new constants also can't match the tree until `02daf12fa5`, when the root starts being computed.

**Fix:** regenerate the 299 entry, run the assumeutxo tests, and squash the constant and test updates into the commit that changes block hashes.

### M6: The monetary encoding drops the root, and the library engine doesn't implement it

**Medium. Confirmed. `e51a216083`, `02daf12fa5`.**

- **Lossy encoding.** `EncodeMonetaryState` still returns 56 bytes without the root, while `MonetaryState::operator==` includes it. Decode accepts both 56 and 88 bytes, including an 88-byte form with a zero root (`lotus_v2/sparse_state.cpp:357-392`). A round trip silently loses the field.
- **Carried stale root.** `AdvanceMonetary` copies `parent.history_root` into the child (`lotus_v2/monetary.cpp:266`). Any caller that doesn't overwrite it commits the parent's root. The node's callers do overwrite it.
- **Library divergence.** `StageCompleteBlock` and the ordinary connect path compute child state roots with no frontier (`lotus_v2/block_transition.cpp:726-735`, `lotus_v2/block.cpp:510-527`). The two engines therefore disagree for the same block.
- **Library peel.** `PeelBlockReverse` decodes a 56-byte parent state and compares to the parent header (`lotus_v2/fast_sync.cpp:1433, 1506-1512`). `PeelDiskBlockReverse` writes that 56-byte form back as metadata (`fast_sync.cpp:1603-1604`). Against real headers above height 1, these should fail.

The node's own fast-sync path doesn't use these library functions. It reconstructs the root at `validation.cpp:4061-4066`. A grep found no node caller of the library peel, and it found `StageCompleteBlock` reached only through `disk_block.cpp`.

**Failure scenario:** someone wires a library path to real headers and gets a state root mismatch on every block, or adds a new caller of `AdvanceMonetary` that commits a stale root.

**Fix:** decide whether the library engine must implement P02. If so, add the frontier to its parent context. If not, document it as development-only. Have `AdvanceMonetary` return a zero root so a forgotten overwrite fails loudly, and use one encoding.

### Low

**L1: No fsync. Confirmed. `b64c479f54`.** Neither `SaveToFile` (`header_history.cpp:427-433`) nor the frontier-carrying `WriteV2BlockStateFile` (`primitives/block.cpp:260-266`) syncs before the rename. A power loss can leave a damaged file under the final name, and for the tree that compounds M2. *Fix:* use `FileCommit` and sync the directory, or delete the tree file.

**L2: Shared path and a dead flag. Confirmed. `044e2575da`.** Background and snapshot chainstates use the same `v2_state/header_history_tree.bin` (`validation.cpp:4347`), so each overwrites the other's copy. Reconciliation corrects this, at the cost of pops and rebuilds. `m_coinsdb_in_memory` is written once and never read (`validation.cpp:4319`), so in-memory chainstates still use the disk file. *Fix:* delete the file, or add a per-chainstate suffix, and remove the flag.

**L3: Linear cost under `cs_main`. Confirmed. `044e2575da`.** The tree uses about 96 bytes per block in RAM and on disk (32 for the leaf hash, about 64 for levels). At the 2-minute spacing, that's about 25 MB a year, and it can't be pruned. The whole file is rewritten on each full flush while holding `cs_main`. `LoadGenesisBlock` also loads the whole file and clears it, because the tip is null, before `LoadChainTip` loads it again (`validation.cpp:4353-4359, 10045`). The 100M leaf limit at `header_history.cpp:477` is about 380 years away, and exceeding it only forces a rebuild. *Fix:* delete the file, and keep the in-memory tree or derive proofs from the block index.

**L4: Trailer handling. Confirmed. `02daf12fa5`.**
- A trailer whose length can't be read is accepted as "no frontier" (`primitives/block.cpp:306-308`).
- A trailer that is present but corrupt makes the read fail. Mid-chain, that's treated as reaching an "unpersisted genesis ancestor" with an empty base (`primitives/block.cpp:497-505`). This is older handling that the trailer now also feeds.
- The frontier count isn't checked against height.

*Fix:* make the trailer mandatory, reject trailing bytes, and pass the height so the count can be checked.

**L5: O(H) work per call under `cs_main`. Confirmed. `02daf12fa5`.** `BuildAncestorHistoryFrontier` rehashes the whole chain on every `PeelFastSyncBlock` call (`validation.cpp:3672-3690, 4059-4060`), and once at pivot and snapshot activation. Its `if (!anc) break;` would silently return a short frontier. `AdvanceV2BlockMonetaryState` also computes a frontier the peel always overwrites (`primitives/block.cpp:1707-1712`). The peel already does O(UTXO) work, so this may not dominate. *Fix:* use `m_header_history_tree.GetFrontierAt()`, and make a missing ancestor an error.

**L6: Spec and interface drift. Confirmed. `da9b570e5a`.**
- The spec gives `<datadir>/blocks/header_history_v2.dat`. The code uses `v2_state/header_history_tree.bin`.
- The result fields differ from spec section 3.4.
- `height` and `blockhash` duplicate `leaf_height` and `block_hash`, against the no-compatibility rule for unreleased tiers.

*Fix:* update the spec and remove the aliases.

**L7: `d35486f823` minor points. Confirmed.** Trailing bytes after the `CMerkleBlock` aren't rejected (older behaviour). Any RPC caller can force a full block read and root computation per call, which is acceptable for an authenticated interface. *Fix (optional):* reject trailing bytes.

**L8: Test temp path. Confirmed. `4f611ecbe2`.** `persistence_roundtrip_and_corruption_rejection` uses a fixed directory under the system temp path and removes it (`src/test/lotus_v2_header_history_tests.cpp:340-342, 428`), so parallel runs can collide. *Fix:* use the fixture's per-test directory.

## Test assessment

Nothing was executed. "Fails without the change" is reasoned from the code.

| Test | Fails without the change? | Notes |
|---|---|---|
| `rpc_txoutproof.py` forgeries | Yes | The old code returned the forged txid, so `assert_equal(..., [])` fails. |
| `merkleblock_verify_native_body_authentication` | Can't compile without the commit | Its forgery and witness cases exercise the new checks directly. |
| `chainstate_sync_and_rpc_proofs_end_to_end` | Yes | Line 487 fails if blocks don't commit `history_root`. |
| Frontier, proof, reorg and encoding unit tests | Can't compile without the commit | They check internal consistency well. |

**Changes these tests wouldn't catch:**

- Swapping or removing the `0x00` and `0x01` prefixes, removing the level byte, or changing the tag. Prover and verifier change together, and there are **no known-answer vectors**. Another implementation couldn't check itself against the spec.
- Removing the flush-time append and pop at `validation.cpp:6499-6518`.
- Removing the "must be non-null" verifier checks. These are redundant with the root comparison, so this one is harmless.

**Not covered at all:**

- `total_count` malleability, which the test steps around (M1)
- interior corruption of the tree file (M2)
- `Chainstate`-level reorg (only the tree class is tested), restart reconciliation, reindex and crash windows
- assumeutxo and fast-sync with a real frontier, including the zero-root branches (M4), `Peel`, and the `.bin` trailer round trip
- equality of template and validation roots (`ComputeV2StateRootFromTemplate` against `ComputeV2BlockStateRoot` and the overlay path)
- the side map and the fail-open path (M3)
- malformed RPC input and numeric-string heights
- any functional test of the new RPCs: only `src/rpc/blockchain.cpp` and the unit test reference them
- `verifytxoutproof` with a missing body, a corrupt body, or a reorg during the read

## What I couldn't determine

- **Whether the code builds and tests pass.** Compilation is assumed, including the `ScopedV2ChainId` include path in `rpc/txoutproof.cpp`, which I expect comes through other headers.
- **M5's stale 299 entry.** It's inferred and needs a run of `feature_assumeutxo.py`.
- **Which root path `TestChain100Setup` exercises.** It could be the overlay or the full block path, so I can't say which one line 487 covers.
- **The V2 wallet's exposure to M6.** `wallet/v2_payment.cpp:44-45` compares `StateRoot` using library store metadata to the tip's state root. If that store ever holds real node headers, it would report a commitment mismatch. I didn't trace how the store is populated.
- **Interaction with `main`.** The audit covers these commits as they sit on their branch.
- **Lock order.** `SetV2NextBlockHistoryFrontierForPrev` takes `g_v2_utxo_mutex` under `cs_main`. I saw no reverse order in `primitives/block.cpp`, but I didn't do a whole-program check.
- **Internals not read:** `TransactionRoot`, `ReadBlock`, `CacheV2BlockStateLocked` eviction, and `ConnectBlock` outside the state root sections.
- **Performance claims.** All costs are arithmetic or estimates, not measurements.
