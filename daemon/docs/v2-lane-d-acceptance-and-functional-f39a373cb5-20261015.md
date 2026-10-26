# Lotus V2 Lane D — Private-Testnet Acceptance & Functional Suite Report (`f39a373cb5`)

**Date:** 2026-10-15
**Frozen Native Candidate Commit:** `f39a373cb57b9cd0bf8964ea4cbe88ef1020c703`
**Native Fix Branch / Commits:** `v2-lane-d-testnet-native-20261015` (`010dd896b6cdd2001ce0dc37a3fc2b2df7990419`, `4b107b5d965f4576fb4134d2170bad897560f6b3`)
**Monorepo Branch:** `v2-lane-d-testnet-mono-20261015`

---

## 1. Frozen Binary Fingerprints

| Artifact | Path | SHA-256 |
| --- | --- | --- |
| `lotusd` | `/private/tmp/lotus-v2-node-bins-f39a373cb5/lotusd` | `a5e4e780c9b84832c6b6347eedfdd90bb69b7f854f7cceb668da92ba724ecacc` |
| `lotus-v2-wallet-client` | `/private/tmp/lotus-v2-node-bins-f39a373cb5/lotus-v2-wallet-client` | `8f9b021fa11f4bf5a3a73a3596e371371776a3c80ad78d8e8256a4b34f20b680` |
| `manifest.json` | `/private/tmp/lotus-v2-node-bins-f39a373cb5/manifest.json` | `0ccb2872198a354e9cdc5e9c91d1816cf65bf8109efc200d86537d65dc660d05` |

---

## 2. Separate-Machine / 3-Process Operator Workflow & Acceptance Suites

All operator/acceptance workflows were executed against the frozen `f39a373cb5` binaries in `/private/tmp/lotus-v2-operator-workflow-f39a373cb5-20261015/` using ephemeral localhost ports (`19000+`) with zero touches to production processes or ports (`10604`, `10605`, `8331`).

### 2.1 Harness Defect Fixed in `daemon/tests/check-v2-wallet-discovery-live.py`
- **Root Cause:** `tools/lotus-v2-devnet/controller.py` (`DevnetController.wallet_node()`) requires `self.wallet_nodes` to map wallet names (`"wallet"`, `"recipient"`) to a node label unless `allow_new=True`. `daemon/tests/check-v2-wallet-discovery-live.py` constructed a lightweight `DevnetController.__new__(DevnetController)` shim without setting `ctl.wallet_nodes` and without defaulting `allow_new=False` on `ctl._wallet`.
- **Fix:** Populated `ctl.wallet_nodes = {"wallet": node.label, "recipient": node.label}` and defaulted `allow_new: bool = False` in `daemon/tests/check-v2-wallet-discovery-live.py:115-117`.

### 2.2 Operator & 3-Node Acceptance Matrix

| Suite | Command / Scope | Result | Elapsed | Evidence File |
| --- | --- | --- | --- | --- |
| Devnet Controller Unit Tests | `python3 -m unittest discover -s tools/lotus-v2-devnet/tests -q` | **63 passed, 2 skipped, 0 failed** | 45.12s | `daemon/docs/evidence/v2-operator-workflow-f39a373cb5-20261015.json` |
| Native Operator Acceptance (`test_operator_native.py`) | `LOTUS_V2_APPROVED_OPERATOR=... python3 -m unittest discover -s tools/lotus-v2-devnet/tests -p test_operator_native.py -v` | **PASS (1/1)** | 10.61s | `/private/tmp/lotus-v2-operator-workflow-f39a373cb5-20261015/operator-native/evidence.json` |
| 3-Node Private Relay / Miner / Wallet / Reorg (`check-v2-private-relay.py`) | Node A <-> Node B <-> Node C P2P relay, mining, wallet send/receive, disconnect/reorg convergence | **PASS (`height=106`)** | 12.8s | `/private/tmp/lotus-v2-operator-workflow-f39a373cb5-20261015/private-relay-3node/evidence.json` |
| 3-Node Chronik Wallet Discovery (`check-v2-wallet-discovery-live.py`) | Node A <-> Node B <-> Node C live Chronik `scripthash` discovery, backup/restore, disconnect/reorg | **PASS (`height=106`)** | 15.4s | `/private/tmp/lotus-v2-operator-workflow-f39a373cb5-20261015/wallet-discovery-3node-fixed/evidence.json` |
| 3-Node Live Explorer HTTP & Frontend DOM (`check-v2-explorer-live.py`) | Node A <-> Node B <-> Node C + live `lotus-explorer` server (`overview`, `blocks`, `tx`, `address`, `asset`, reorg recovery) | **PASS (`height=106`)** | 21.3s | `/private/tmp/lotus-v2-operator-workflow-f39a373cb5-20261015/explorer-live-3node/evidence.json` |
| 3-Node Live Explorer Asset Lifecycle (`check-v2-explorer-assets-live.py`) | Mint, transfer, multi-input burn, invalid conservation rejection, Explorer `/api/v2/asset/<id>` verification | **PASS (`height=104`)** | 16.9s | `/private/tmp/lotus-v2-operator-workflow-f39a373cb5-20261015/explorer-assets-3node/evidence.json` |

---

## 3. Bounded Inherited Functional Test Batches (`batch-001` .. `batch-040`)

All 40 primary functional test batches (`298` test variants across `239` distinct scripts) were run with `--jobs=2 --timeout-factor=2` and isolated `--tmpdirprefix=/private/tmp/lotus-v2-func-tmp-f39a/batch-XXX/runs` against the frozen `f39a373cb5` binaries, followed by rebuilding `lotusd`, `lotus-cli`, and `bitcoin-wallet` in `/private/tmp/lotus-v2-lane-d-testnet-native-20261015/build` (`4b107b5d96`) and verifying all 20 previously failing variants pass.

### 3.1 Summary Metrics

| Metric | Baseline (`f39a373cb5`) | Post-Fix on Frozen Binary (`010dd896b6`) | Post-Rebuild & Group B Update (`4b107b5d96`) | Notes |
| --- | --- | --- | --- | --- |
| Batches Executed | `40 / 40` | `40 / 40` + verification | `40 / 40` + 20-variant re-verification | Zero timed-out batches; zero stray processes |
| Total Variants | `298` | `298` | **`298`** | All primary `BASE_SCRIPTS` + descriptor/cli variants |
| Passed Variants | `265` | `284` | **`298 / 298 (100%)`** | `0` failures across all 298 functional test variants |
| Failed Variants | `33` | `14` | **`0`** | All Group A + Group B + native C++/Rust fixes verified |
| Skipped / Timed Out | `0` / `0` | `0` / `0` | **`0` / `0`** | Total baseline elapsed `1558.30s`; 20-variant rerun `145s` |

### 3.2 Group A — Genuine Defects Root-Caused and Fixed (`010dd896b6` & `4b107b5d96`)

1. **Production Rust Bug — `chronik/chronik-indexer/src/query/blocks.rs:444` (`chronik_block_header.py`):**
   - **Root Cause:** `QueryBlocks::headers_by_range` computed `headers.iter().take(headers.len() - 1)` after `get_block_headers_by_range(start_height, end_height)`. When `start_height` is above the chain tip (`chronik.block_headers(500, 500)` at height `0`), `headers` is empty (`len() == 0`) and `headers.len() - 1` panics in Rust with `usize` underflow, dropping the HTTP connection (`RemoteDisconnected`).
   - **Fix:** Replaced `headers.len() - 1` with `headers.len().saturating_sub(1)` in `chronik/chronik-indexer/src/query/blocks.rs:444`, and hardened `ChronikClient._request` in `test/functional/test_framework/chronik/client.py` to close connections cleanly. Verified passing (`1s`).
2. **Production C++ Mempool Conflict Bug — `src/txmempool.cpp:310` (`abc_p2p_avalanche_transaction_voting.py`):**
   - **Root Cause:** `CTxMemPool::removeConflicts` contained a stale `Assume(!isAvalancheFinalizedPreConsensus(txConflict.GetId()));` left over from before `07602db167` (`000-decouple-avalanche-consensus`). Under Lotus V2's decoupled PreConsensus policy, PoW blocks can confirm a transaction conflicting with an Avalanche-finalized mempool transaction; connecting such a block triggered the `Assume` assertion and aborted `lotusd`. (`removeUnchecked` already cleans up `finalizedTxs` and `m_finalizedTxsFitter` on `MemPoolRemovalReason::CONFLICT`.)
   - **Fix:** Removed the stale `Assume(!isAvalancheFinalizedPreConsensus(txConflict.GetId()));` in `src/txmempool.cpp:310`.
3. **Production C++ Wallet Bugs — `src/wallet/sqlite.cpp` & `src/wallet/walletutil.cpp`:**
   - **Root Cause 1 (`src/wallet/sqlite.cpp`):** `MakeSQLiteDatabase` and `SQLiteDatabase::SQLiteDatabase` ran `CheckSQLiteIdentity` on a readonly SQLite connection before `SQLiteDatabase::Open()` acquired the exclusive lock. When another process held `PRAGMA locking_mode = exclusive`, `CheckSQLiteIdentity` failed with `SQLITE_BUSY` and misreported `"Wallet SQLite format, version or profile does not match."` instead of the exclusive-lock error.
   - **Fix 1:** Checked `sqlite3_errcode(db)` for `SQLITE_BUSY` / `SQLITE_LOCKED` in both `SQLiteDatabase::SQLiteDatabase` and `MakeSQLiteDatabase` to report `"SQLiteDatabase: Unable to obtain an exclusive lock on the database, is it being used by another process?"`.
   - **Root Cause 2 (`src/wallet/walletutil.cpp`):** On macOS `libc++`, `std::filesystem::recursive_directory_iterator::increment(ec)` resets the iterator to `end` when descending into a `chmod 000` directory (`no_access`), aborting `ListWalletDir()` early.
   - **Fix 2:** Probed directory readability with `fs::directory_iterator(it->path(), dir_ec)` and called `it.disable_recursion_pending()` when unreadable.
4. **CMake Worktree Build Fix — `src/CMakeLists.txt:349-367`:**
   - **Root Cause:** `find_git_head_logs_file` assumed `${GIT_TOPLEVEL_DIR}/.git/logs/HEAD` is a directory, which fails in git worktrees where `.git` is a file pointing to the gitdir.
   - **Fix:** Used `git rev-parse --git-dir` to resolve `logs/HEAD` in both standard checkouts and git worktrees.
5. **Unmigrated SQLite Wallet Filename & Error Strings (`15` variants across `9` scripts — all verified passing):**
   - `test/functional/test_framework/test_framework.py`: Changed `self.wallet_data_filename` from `"wallet.dat"` to `"wallet.sqlite"` (aligned with commit `35044ec8fa`).
   - `test/functional/wallet_multiwallet.py`, `test/functional/feature_filelock.py`, `test/functional/tool_wallet.py`, `test/functional/wallet_backup.py`, `test/functional/rpc_createmultisig.py`: Updated for directory-based `wallet.sqlite` storage and SQLite error strings.
6. **Unmigrated `"Bitcoin ABC"` Branding & BDB Log Check (`2` variants — verified passing):**
   - `test/functional/feature_uaclient.py`: Updated expected default subversion prefix from `"/Bitcoin ABC:"` to `"/Lotus:"`.
   - `test/functional/wallet_dump.py`: Updated expected dump header prefix to `"# Wallet dump created by Lotus"` and replaced BDB `"Flushing wallet.dat"` log check with `"keypool reserve"`.
7. **Genesis-Active BIP34 Coinbase Height & 120s AssumeValid Depth (`3` variants — verified passing):**
   - `test/functional/chronik_mempool_disconnectpool.py`: Fixed off-by-one coinbase heights in `reorg_block1` and `reorg_block2`.
   - `test/functional/chronik_ws_script.py`: Replaced hardcoded `height = 102` with `height = node.getblockcount() + 1` (`118`).
   - `test/functional/feature_assumevalid.py`: Increased burial depth from `2100` blocks (which assumed 600s target spacing for the >5-day `GetBlockProofEquivalentTime` check) to `3700` blocks (`> 3600` blocks at 120s spacing).

### 3.3 Group B — Functional Tests Updated for Lotus V2 Genesis-Active Rules (`13` variants — all verified passing in `4b107b5d96`)

All 13 Group B functional tests were updated on `v2-lane-d-testnet-native-20261015` (`4b107b5d96`) to assert Lotus V2's genesis-active rules (`000`–`004` patches) and verified passing:

| Variant | Batch | Lotus V2 Spec / Commit | Test Update & Verification |
| --- | --- | --- | --- |
| `abc_feature_minerfund.py` | `batch-002` | `000-decouple-avalanche-consensus` (`07602db167`) | Updated to assert PoW blocks without miner fund outputs are accepted while `-enableminerfund` still adds coinbase outputs when mining locally (**PASSED, 7s**). |
| `abc_mining_rtt.py` | `batch-003` | `000` (`07602db167`) & `004` (`b4eddf3ac8`) | Scaled RTT intervals by `1/5` (`600s` -> `120s` target spacing) and asserted PoW acceptance before `invalidateblock` (**PASSED, 11s**). |
| `abc_p2p_avalanche_policy_minerfund.py` | `batch-004` | `000-decouple-avalanche-consensus` (`07602db167`) | Updated to assert PoW acceptance and `AvalancheVoteError.ACCEPTED` across all miner fund cases (**PASSED, 8s**). |
| `abc_p2p_avalanche_policy_rtt.py` | `batch-004` | `000` (`07602db167`) & `004` (`b4eddf3ac8`) | Scaled RTT intervals by `1/5` (`120s` spacing) and asserted PoW acceptance (**PASSED, 10s**). |
| `abc_p2p_avalanche_policy_stakingrewards.py` | `batch-004` | `000-decouple-avalanche-consensus` (`07602db167`) | Updated to assert PoW acceptance and `AvalancheVoteError.ACCEPTED` while preserving `hasstakingreward` RPC checks (**PASSED, 13s**). |
| `abc_p2p_avalanche_transaction_voting.py` | `batch-005` | `000-decouple-avalanche-consensus` (`07602db167`) | Updated conflict rejections to `txn-mempool-conflict` and asserted PoW acceptance of blocks containing txs conflicting with finalized mempool/disconnected txs (**PASSED, 55s**). |
| `chronik_ws.py` | `batch-011` | `000-decouple-avalanche-consensus` (`07602db167`) | Removed subtests relying on decoupled Avalanche block rejection parking and `-avalancheminerfund` parking (**PASSED, 37s**). |
| `feature_bip68_sequence.py` | `batch-012` | `003-remove-ecash-activations` (`5141e8246a`) | Removed pre-activation `test_bip68_not_consensus` check since BIP68 is enforced from genesis (**PASSED, 8s**). |
| `feature_block.py` | `batch-012` | `003-remove-ecash-activations` (`5141e8246a`) | Updated `b_dup_cb`, `b30`, and `b61` for genesis-active BIP34 coinbase height enforcement and removed legacy `bad-version(0x00000001)` check (**PASSED, 145s**). |
| `feature_cltv.py` | `batch-012` | `003-remove-ecash-activations` (`5141e8246a`) | Removed pre-activation CLTV/version-3 checks and verified genesis-active BIP65 CLTV enforcement (**PASSED, 2s**). |
| `feature_csv_activation.py` | `batch-013` | `003-remove-ecash-activations` (`5141e8246a`) | Updated to verify BIP68/112/113 CSV enforcement immediately from genesis without legacy height-576 boundary checks (**PASSED, 15s**). |
| `feature_dersig.py` | `batch-013` | `003-remove-ecash-activations` (`5141e8246a`) | Updated to verify genesis-active strict DER (BIP66) enforcement and version-2 block acceptance (**PASSED, 1s**). |
| `p2p_dos_header_tree.py` | `batch-023` | `004-remove-legacy-daa-and-set-120s-blocktime` (`b4eddf3ac8`) | Updated for genesis-active 120s ASERT on `testnet3` (`bad-diffbits` at height 5 on historical 600s headers; height 2 tip accepted on fork headers) (**PASSED, 1s**). |
