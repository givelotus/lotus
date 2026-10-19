# Implementation Plan: Port Chronik to Pure C++ (`libmdbx` + `Boost.Beast` + `Protobuf`) and Remove Rust / Cargo / RocksDB

**Target Baseline:** Layers directly on top of the `Boost.Beast` HTTP/WebSocket server (`ecash-boost-beast-http-ws-p2p-plan.md`) in the `ecash/` (`v1`) patch stack, with a small `v2/` extension for `nVersion == 7` Lotus V2 transactions.

---

## 1. Architectural Motivation & Overview

Currently, enabling `-DBUILD_CHRONIK=ON` pulls in:
- An entire Rust/Cargo build system (`Corrosion`, `RustHelper.cmake`, `Cargo.lock` with 300+ crates),
- `cxxbridge` code generation (`chronik-bridge` and `chronik-lib`),
- A second embedded key-value database (**RocksDB**, running alongside `libmdbx` and competing for RAM/IO),
- A second HTTP/WebSocket server (**`tokio` + `hyper` + `axum`**, running alongside `src/httpserver.cpp`),
- Duplicate Rust re-implementations of `CTransaction`, `CBlockHeader`, `CScript`, `TxId`, and `Coin` (`bitcoinsuite-core`).

With `Boost.Beast` (HTTP/1.1 + WebSockets) and `libmdbx` already in C++, and `Protobuf` (`protoc` / `libprotobuf`) already in `depends/packages/protobuf.mk` and CMake, we can replace all 63,000 lines of Rust/Cargo/RocksDB/`cxxbridge` with **~3,000 lines of native C++20** inside `chronik/chronik-cpp/`:

1. **100% Wire-Compatible Protobuf + WebSocket API:**
   - Compiles the existing [`chronik/chronik-proto/proto/chronik.proto`](file:///Users/shammah/repos/lotus-v2-optimizations/daemon/workspace-v2/chronik/chronik-proto/proto/chronik.proto) (`proto3`) directly into C++ (`chronik.pb.h` / `chronik.pb.cc`) via CMake's `protobuf_generate_cpp`.
   - Every HTTP endpoint (`/blockchain-info`, `/chronik-info`, `/block/:hash_or_height`, `/blocks/:start/:end`, `/block-header/...`, `/block-headers/...`, `/tx/:txid`, `/raw-tx/:txid`, `/unconfirmed-txs`, `/validate-tx`, `/broadcast-tx`, `/broadcast-txs`, `/script/:type/:payload/history|utxos|confirmed-txs|unconfirmed-txs`, `/token/:txid`, `/token-id/:token_id/...`, `/lokad-id/:lokad_id/...`, `/ws`) returns byte-for-byte identical `application/x-protobuf` messages, so `chronik-client` (JS/TS/Rust/Python) works with zero changes.
2. **Single Storage Engine (`libmdbx`):**
   - Stores Chronik's index tables in `<datadir>/indexes/chronik/` using `libmdbx` (`MDBX_WRITEMAP | MDBX_LIFORECLAIM`), sharing the same ultra-fast memory-mapped B+Tree engine we already use in the daemon and eliminating RocksDB completely.
3. **Dual `v1`/`v2` (`ecash`) + `v7` (`Lotus V2`) Indexing:**
   - Because legacy/eCash transactions have `nVersion == 1` or `2` and Lotus V2 transactions have `nVersion == 7`, the C++ indexer supports **both** without conflict:
     - For `nVersion == 1, 2` (in the base `ecash/` patch series): indexes `scriptPubKey` (`p2pk`, `p2pkh`, `p2sh`, `other`), `scripthash`, `lokad_id`, and full **SLP (`v1`, `MintVault`, `NFT1`) & ALP (`EMPP`)** token coloring so the `ecash/` C++ Chronik patch can be ported to any eCash / Bitcoin ABC / Lotus v1 daemon.
     - For `nVersion == 7` (layered in `v2/`): indexes `vBranches[0..2]` (`BranchRoot`), native `tokenId` (`HAS_TOKEN`), and `state_root` (`HAS_STATE`) into the same `libmdbx` tables plus the `/v2/*` explorer routes.
4. **Zero Rust / Zero Cargo / Zero `cxxbridge`:**
   - Removes `include(RustHelper)` and `corrosion_import_crate` from `chronik/CMakeLists.txt` and root `CMakeLists.txt`. `ninja bitcoind` compiles Chronik in `< 3 seconds` as pure C++ translation units.

---

## 2. `libmdbx` Schema & Zero-Duplication Storage Optimizations (`chronik/chronik-cpp/chronik_db.h`)

A naive indexer duplicates transactions, block heights, 32-byte `TxId`s, and UTXO payloads (`nValue`, `scriptPubKey`) that `bitcoind` already stores in `blk*.dat`, `rev*.dat`, and `CoinsTip()`. Our C++ `ChronikDb` preserves **all** of Chronik's compact `TxNum` + flat-file pointer optimizations and goes **one step further** by reading unspent `Coin` payloads directly from `Chainstate::CoinsTip()` in-process so UTXO payloads are **never stored in both databases**:

### The 6 Core Storage Optimizations

1. **Zero Duplicate Transaction or Undo Storage (`data_pos` & `undo_pos` Flat-File Pointers):**
   - `ChronikDb` never stores raw transactions or spent input `Coin`s.
   - Every transaction in the blockchain is assigned a monotonically increasing 64-bit serial number `TxNum` (`0, 1, 2, ...` in exact block order).
   - `CF_TX` (`tx`) maps `uint64_be(tx_num) (8B) -> SerTx { TxId(32B), data_pos(4B), undo_pos(4B), time_first_seen(8B) }` (**48 bytes total**, fixed size!).
   - Because coinbase transactions have no undo data and real undo offsets in `rev*.dat` are never `0`, `undo_pos == 0` encodes `is_coinbase = true` in 0 extra bytes.
   - Even `block_height` is omitted from `CF_TX`: instead, `CF_BLK_BY_FIRST_TX` (`uint64_be(first_tx_num) -> uint32_be(height)`) and `CF_FIRST_TX_BY_BLK` (`uint32_be(height) -> uint64_be(first_tx_num)`) store just **one 12-byte row per block**, resolving any `tx_num` to its `block_height` via a single `MDBX_TO_KEY_LESSER_OR_EQUAL` cursor seek!
   - When `/tx/:txid`, `/raw-tx/:txid`, or `/script/.../history` needs full transaction/input data, C++ reads `(file_num, data_pos, undo_pos)` directly from `bitcoind`'s `blk?????.dat` and `rev?????.dat` via `node::ReadRawFromBlock` / `ReadTxFromDisk`.

2. **Zero Duplicate UTXO Storage Across `CoinsTip()` and Chronik (`12-byte DbOutpoint` + `MDBX_DUPSORT | MDBX_DUPFIXED`):**
   - In Rust Chronik, because `chronik-db` lived across the Rust FFI boundary without direct access to `Chainstate::CoinsTip()`, `CF_SCRIPT_UTXO` had to store `20B (tx_num, out_idx, sats)` and `CF_TOKEN_ID_UTXO` had to store `12B (tx_num, out_idx) + 8B sats + variable scriptPubKey`—duplicating UTXO data that `bitcoind` already stores in `chainstate/utxo` (`CoinsTip()`)!
   - Because C++ Chronik runs in-process inside `bitcoind`/`lotusd`, **every confirmed unspent output in Chronik's UTXO index is guaranteed to exist in `m_node.chainman->ActiveChainstate().CoinsTip()` (`CCoinsViewCache`)**!
   - Therefore, **all** UTXO index tables (`script_utxo`, `token_id_utxo`, `v2_branch_utxo`, `v2_asset_utxo`) use `MDBX_DUPSORT | MDBX_DUPFIXED` where each duplicate value is **strictly the 12-byte `DbOutpoint` (`uint64_be(tx_num) || uint32_be(out_idx)`)**:
     - Zero `sats`, zero `scriptPubKey`, zero `height`, and zero `is_coinbase` bytes are duplicated in Chronik's UTXO tables!
     - Using `MDBX_DUPSORT | MDBX_DUPFIXED`, `libmdbx` packs all 12-byte `(tx_num, out_idx)` outpoints for an address or token into a headerless contiguous array on B+Tree leaf pages, readable in a single `MDBX_GET_MULTIPLE` call.
     - When serving `/script/:type/:payload/utxos`, `/token-id/:id/utxos`, or `/v2/.../utxos`, C++ resolves `tx_num -> txid` from `CF_TX` and reads `CoinsTip().AccessCoin(COutPoint(txid, out_idx))` in-process from `CCoinsViewCache` (`libmdbx` chainstate) to get `nValue`, `scriptPubKey`, `nHeight`, `IsCoinBase()`, and V2 `tokenId`/`vBranches` with zero disk duplication!

3. **8-Byte `CheapHash` Reverse Lookup (`CF_LOOKUP_TX_BY_HASH`, `CF_LOOKUP_BLK_BY_HASH`) — No Duplicate 32-Byte Hashes:**
   - Storing a naive `TxId(32B) -> TxNum(8B)` index would store every 32-byte `TxId` a second time (already stored in `CF_TX`).
   - Instead, `CF_LOOKUP_TX_BY_HASH` maps an **8-byte `CheapHash`** (`CSipHasher(0, 0).Write(txid).Finalize()` / `SeaHash` big-endian) $\rightarrow$ `uint64_be(tx_num)` using `MDBX_DUPSORT | MDBX_DUPFIXED`!
   - Similarly, `CF_LOOKUP_BLK_BY_HASH` maps a **4-byte `CheapHash`** of `BlockHash` $\rightarrow$ `uint32_be(height)` using `MDBX_DUPSORT | MDBX_DUPFIXED`.
   - To look up a `TxId`, `ChronikDb` computes the 8-byte `CheapHash`, fetches the matching `tx_num` duplicate(s) from `CF_LOOKUP_TX_BY_HASH`, reads `CF_TX[tx_num]`, and verifies `ser_tx.txid == txid`. This shrinks the reverse hash index by **75%** (8B key instead of 32B key) and uses `MDBX_DUPFIXED` instead of custom merge operators!

4. **`CScriptCompressor` Script Key Compression (`chronik_script.h`):**
   - Keys in `CF_SCRIPT_HISTORY`, `CF_SCRIPT_HISTORY_NUM_TXS`, and `CF_SCRIPT_UTXO` use `CompressScript` (`CScriptCompressor` format: `0x00 || 20B PKH`, `0x01 || 20B SH`, `0x02/0x03 || 32B compressed pubkey`, `0x04/0x05 || 32B uncompressed pubkey`), saving 5–33 bytes on every single key in the database while grouping in memory by raw `CScript` span before compressing once per unique script in a block batch.

5. **Compact `TxNum`-Based `CF_SPENT_BY` (`spent_by`):**
   - To populate `TxOutput.spent_by` (`{ txid, input_idx }`) on `/tx/:txid` without storing 32-byte spending `txid`s, `CF_SPENT_BY` uses `MDBX_DUPSORT | MDBX_DUPFIXED` mapping `uint64_be(funded_tx_num) (8B)` $\rightarrow$ **16-byte fixed duplicate entries**: `uint32_be(out_idx) || uint64_be(spending_tx_num) || uint32_be(spending_input_idx)`.
   - On `ConnectBlock`, each non-coinbase input inserts one 16-byte `MDBX_DUPFIXED` entry under `funded_tx_num`. On `DisconnectBlock`, `mdbx_del` deletes that exact `(funded_tx_num, 16B dup)` pair in $O(\log N)$ with zero read-modify-write!

6. **Compact `TxNum`-Based `DbTokenTx` (`CF_TOKEN_TX`, `CF_TOKEN_META`, `CF_TOKEN_GENESIS_INFO`):**
   - Instead of storing 32-byte `TokenId`s on every token transaction input and output, a token is identified internally by its `GENESIS` transaction's 8-byte `token_tx_num` (`TxNum`).
   - `CF_TOKEN_META` maps `uint64_be(token_tx_num) -> TokenMeta { TokenId(32B), TokenType(2B) }` (34B fixed), `CF_TOKEN_GENESIS_INFO` maps `uint64_be(token_tx_num) -> serialized GenesisInfo`, and `CF_TOKEN_TX` maps `uint64_be(tx_num) -> DbTokenTx { token_tx_nums[], group_token_indices, inputs[DbToken], outputs[DbToken], flags }`.
   - Burn amounts, token tx type (`GENESIS`/`MINT`/`SEND`/`BURN`), and validation diagnostics are not bloated onto disk—they are re-evaluated in microseconds on demand from the pre-colored `DbToken` inputs when `/tx/:txid` is queried.

---

### Complete `libmdbx` DBI Table Layout (`<datadir_net>/indexes/chronik/`)

| DBI Name | `MDBX` Flags | Key Format | Value Format | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| `meta` | `MDBX_CREATE` | `string` (`"schema_v"`, `"tip_height"`, `"tip_hash"`, `"next_tx_num"`) | Raw bytes | Tracks schema version, indexed chain tip, and next `TxNum` |
| `blk` | `MDBX_CREATE` | `uint32_be(height)` (4B) | `SerBlock`: `hash(32B) \|\| n_bits(4B) \|\| timestamp(8B) \|\| file_num(4B) \|\| data_pos(4B)` (52B) | Block metadata + flat-file pointer |
| `blk_stats` | `MDBX_CREATE` | `uint32_be(height)` (4B) | `SerBlockStats`: `block_size(8B) \|\| num_txs(8B) \|\| num_inputs(8B) \|\| num_outputs(8B) \|\| sum_input_sats(8B) \|\| sum_coinbase_output_sats(8B) \|\| sum_normal_output_sats(8B) \|\| sum_burned_sats(8B)` (64B) | Block statistics for `/block/:hash_or_height` & `/blocks/:start/:end` |
| `lookup_blk_by_hash` | `MDBX_DUPSORT \| MDBX_DUPFIXED` | `CheapHash32(block_hash)` (4B) | `uint32_be(height)` (4B fixed dup) | Compact 4B-hash $\rightarrow$ `height` reverse lookup |
| `tx` | `MDBX_CREATE` | `uint64_be(tx_num)` (8B) | `SerTx`: `txid(32B) \|\| data_pos(4B) \|\| undo_pos(4B) \|\| time_first_seen(8B)` (48B) | Maps `tx_num` $\rightarrow$ `blk*.dat` / `rev*.dat` byte offsets (`undo_pos == 0` $\iff$ coinbase) |
| `blk_by_first_tx` | `MDBX_CREATE` | `uint64_be(first_tx_num)` (8B) | `uint32_be(height)` (4B) | Resolves any `tx_num` $\rightarrow$ `block_height` via `MDBX_TO_KEY_LESSER_OR_EQUAL` |
| `first_tx_by_blk` | `MDBX_CREATE` | `uint32_be(height)` (4B) | `uint64_be(first_tx_num)` (8B) | Lists all `tx_num`s in block `height` (`[first_tx_num[h] .. first_tx_num[h+1])`) |
| `lookup_tx_by_hash` | `MDBX_DUPSORT \| MDBX_DUPFIXED` | `CheapHash64(txid)` (8B) | `uint64_be(tx_num)` (8B fixed dup) | Compact 8B-hash $\rightarrow$ `tx_num` reverse lookup (saves 24B per tx vs 32B `TxId` key!) |
| `spent_by` | `MDBX_DUPSORT \| MDBX_DUPFIXED` | `uint64_be(funded_tx_num)` (8B) | `out_idx(4B BE) \|\| spending_tx_num(8B BE) \|\| input_idx(4B BE)` (16B fixed dup) | Tracks which tx/input spent each output without storing 32B `txid`s |
| `script_history` | `MDBX_CREATE` | `compressed_script \|\| uint32_be(page_num)` | Packed `uint64_be(tx_num)[]` (`<= 1000` txs/page) | Paginated `/script/:type/:payload/history` & `confirmed-txs` |
| `script_history_num_txs` | `MDBX_CREATE` | `compressed_script` | `uint32_be(num_txs)` (4B) | Total confirmed tx count for script pagination |
| `script_utxo` | `MDBX_DUPSORT \| MDBX_DUPFIXED` | `compressed_script` | `DbOutpoint`: `tx_num(8B BE) \|\| out_idx(4B BE)` (**12B fixed dup**) | Unspent outpoints for script; `Coin` payload read directly from `CoinsTip()`! |
| `scripthash` | `MDBX_CREATE` | `sha256(script)` (32B) | `compressed_script` | Optional `-chronikscripthashindex=1` Electrum scripthash $\rightarrow$ script lookup |
| `lokad_id_history` / `num_txs` | `MDBX_CREATE` | `lokad_id(4B) [\|\| page_num(4B)]` | Packed `uint64_be(tx_num)[]` / `num_txs(4B)` | Paginated `/lokad-id/:id/history` & `confirmed-txs` |
| `token_meta` / `genesis_info` / `token_tx` | `MDBX_CREATE` | `uint64_be(token_tx_num or tx_num)` (8B) | `TokenMeta` (34B) / `GenesisInfo` / `DbTokenTx` | Compact `TxNum`-indexed SLP/ALP token metadata & per-tx coloring |
| `token_id_history` / `num_txs` / `utxo` | `MDBX_CREATE` / `DUPFIXED` | `token_id(32B)` | Paginated `tx_num[]` / `num_txs(4B)` / **12B `DbOutpoint` dup** | `/token-id/:id/history` and `/token-id/:id/utxos` (reads `Coin` from `CoinsTip()`!) |
| `v2_branch_*` & `v2_asset_*` | `MDBX_CREATE` / `DUPFIXED` | `branch_root(32B)` or `asset_id(32B)` | Paginated `tx_num[]` / `num_txs(4B)` / **12B `DbOutpoint` dup** | Lotus V2 (`nVersion == 7`) 3-branch & native asset history and UTXOs |

---

## 3. Staged 5-Commit Implementation Plan

### Commit 1: `chronik-cpp: compile chronik.proto to C++ and implement zero-duplication libmdbx ChronikDb engine`

#### Files to Create / Modify
- `chronik/chronik-cpp/chronik_db.h` (new)
- `chronik/chronik-cpp/chronik_db.cpp` (new)
- `chronik/chronik-cpp/chronik_script.h` (new: `CScriptCompressor` wrapper + payload classification for `p2pk`, `p2pkh`, `p2sh`, `other`, and `scripthash` SHA256)
- `chronik/CMakeLists.txt` (add `find_package(Protobuf REQUIRED)` and `protobuf_generate_cpp` on `chronik-proto/proto/chronik.proto`)

#### Exact Implementation Steps
1. Generate `chronik.pb.h` and `chronik.pb.cc` from `chronik/chronik-proto/proto/chronik.proto` via `protobuf_generate_cpp`.
2. Implement `ChronikDb` wrapping `MDBX_env*`:
   - `Open(const fs::path &db_dir, bool wipe)`: opens the DBIs above (`meta`, `blk`, `blk_stats`, `lookup_blk_by_hash`, `tx`, `blk_by_first_tx`, `first_tx_by_blk`, `lookup_tx_by_hash`, `spent_by`, `script_history`, `script_history_num_txs`, `script_utxo`, `scripthash`, `lokad_id_history`, `lokad_id_history_num_txs`, `token_meta`, `token_genesis_info`, `token_tx`, `token_id_history`, `token_id_history_num_txs`, `token_id_utxo`, `v2_branch_*`, `v2_asset_*`).
   - `ConnectBlock(const CBlock &block, const CBlockIndex &bindex, const CBlockUndo &block_undo)`:
     - Calculates exact `data_pos` (`bindex.nDataPos + 80 + CompactSize(vtx.size())`) and `undo_pos` (`bindex.nUndoPos + CompactSize(vtx.size() - 1)`) for every `block.vtx[i]` using `tx.GetSerializeSize()` and `::GetSerializeSize(block_undo.vtxundo[i - 1])`.
     - Within a single atomic `MDBX_txn` write transaction:
       - Writes `SerBlock` to `blk`, `SerBlockStats` to `blk_stats`, `(CheapHash32(block.GetHash()), height)` to `lookup_blk_by_hash`, and `first_tx_num <-> height` to `blk_by_first_tx` and `first_tx_by_blk`.
       - Assigns sequential `tx_num` to each `block.vtx[i]`, writes 48-byte `SerTx` to `tx`, and inserts `(CheapHash64(txid), tx_num)` into `lookup_tx_by_hash`.
       - Resolves all input `prevout.GetTxId()`s in batch via `lookup_tx_by_hash` $\rightarrow$ `input_tx_nums`.
       - Inserts 16-byte `(out_idx, tx_num, input_idx)` into `spent_by` under `input_tx_num`.
       - Updates `script_utxo` (`MDBX_DUPSORT | MDBX_DUPFIXED` with **12-byte `DbOutpoint`** `tx_num || out_idx` — deleting spent input `DbOutpoint`s via `mdbx_del` and inserting new output `DbOutpoint`s via `mdbx_put`) and appends `tx_num` to `script_history` pages (`1000` `tx_num`s/page) and `lokad_id_history`.
       - Updates `meta` and commits the `MDBX_txn`.
   - `DisconnectBlock(const CBlock &block, const CBlockIndex &bindex, const CBlockUndo &block_undo)`:
     - Exact reverse of `ConnectBlock`: deletes new output `DbOutpoint`s from `script_utxo`, re-inserts spent input `12-byte DbOutpoint`s from `block_undo` back into `script_utxo`, deletes the block's `spent_by` 16-byte duplicates, trims `script_history` / `lokad_id_history` pages, and removes the block's `tx` and `blk` entries.
   - `QueryGroupUtxos`:
     - Reads the 12-byte `(tx_num, out_idx)` duplicates from `script_utxo` / `token_id_utxo` / `v2_*_utxo`, resolves `tx_num -> SerTx` (`txid`, `is_coinbase`) and `block_height` (from `blk_by_first_tx`), filters out any outpoints spent in `ChronikMempool`, and reads the `Coin` (`nValue`, `scriptPubKey`, V2 fields) **directly from `m_node.chainman->ActiveChainstate().CoinsTip().AccessCoin(COutPoint(txid, out_idx))`** under `LOCK(cs_main)` (or a batched `CoinsTip()` read)!
3. Add a C++ unit test verifying `ConnectBlock`, `DisconnectBlock`, `load_tx` from `blk*.dat`/`rev*.dat` offsets, and `QueryGroupUtxos` reading `Coin` values from `CoinsTip()`.

---

### Commit 2: `chronik-cpp: add native C++ SLP (v1/NFT1/MintVault) and ALP token coloring engine`

#### Files to Create / Modify
- `chronik/chronik-cpp/chronik_slp_alp.h` (new)
- `chronik/chronik-cpp/chronik_slp_alp.cpp` (new)
- `chronik/chronik-cpp/chronik_db.cpp`

#### Exact Implementation Steps
1. Implement deterministic SLP and ALP parsing, topological batch sorting, and coloring in `chronik_slp_alp.cpp` (~750 lines of clean C++):
   - **Early-Block Fast Skip:** Just like `TokenWriter::insert` in `chronik-db`, if `token_meta` is empty and the block batch contains no `GENESIS` transactions, skip token indexing for the entire block in $O(1)$.
   - **SLP Parser (`OP_RETURN <"SLP\0"> <token_type> <tx_type> ...`):**
     - Supports `SlpTokenType::FUNGIBLE (0x01)`, `MINT_VAULT (0x02)`, `NFT1_GROUP (0x81)`, `NFT1_CHILD (0x41)`.
     - Parses `GENESIS`, `MINT`, `SEND`, and `BURN`.
   - **ALP Parser (`OP_RETURN <OP_RESERVED> <"SLP2" Pushdata>...`):**
     - Parses EMPP sections matching `"SLP2"` (`STANDARD = 0`), supporting multi-token `GENESIS`, `MINT`, `SEND`, `BURN` within a single transaction.
   - **Compact `DbTokenTx` Persistence:**
     - Stores `TokenMeta` (34B) and `GenesisInfo` keyed by the `GENESIS` transaction's 8-byte `token_tx_num`, and `DbTokenTx` (referencing `token_tx_nums` by compact index rather than 32-byte `TokenId`) in `token_tx`.
     - Stores 12-byte `DbOutpoint` (`tx_num || out_idx`) in `token_id_utxo` (`MDBX_DUPSORT | MDBX_DUPFIXED`), reading the `sats` and `scriptPubKey` from `CoinsTip()` and the token amount from `token_tx[tx_num]` on query!

---

### Commit 3: `chronik-cpp: add in-memory mempool indexer and ChronikIndexer validation hooks`

#### Files to Create / Modify
- `chronik/chronik-cpp/chronik_mempool.h` (new)
- `chronik/chronik-cpp/chronik_mempool.cpp` (new)
- `chronik/chronik-cpp/chronik_indexer.h` (new)
- `chronik/chronik-cpp/chronik_indexer.cpp` (new)
- `chronik/chronik-cpp/chronik_validationinterface.cpp`

#### Exact Implementation Steps
1. Implement `ChronikMempool` (guarded by `std::shared_mutex` for concurrent HTTP reader access):
   - Tracks unconfirmed transactions (`txid -> MempoolTxEntry`), unconfirmed `script_txs`, unconfirmed `script_utxos`, unconfirmed `spent_outpoints` (so `/script/.../utxos` excludes confirmed UTXOs spent in the mempool, or marks them appropriately), unconfirmed `lokad_txs`, and unconfirmed `token` state.
2. Implement `ChronikIndexer`:
   - On startup (`Start()`): checks `ChronikDb::GetTip()` against `ChainActive().Tip()`, rewinds any disconnected fork blocks (`rewind_indexer`), and catches up any missing blocks `start_height + 1 ..= tip_height` from `blk*.dat` / `rev*.dat` up to `ChainActive().Tip()` (so unclean shutdowns before the async queue drains recover 100% automatically).
   - Implements the 8 `CValidationInterface` methods called by `ChronikValidationInterface`'s background worker thread:
     - `handle_tx_added_to_mempool`
     - `handle_tx_removed_from_mempool`
     - `handle_block_connected`
     - `handle_block_disconnected`
     - `handle_block_finalized`
     - `handle_block_invalidated`
     - `handle_tx_finalized`
     - `handle_tx_invalidated`
   - Broadcasts real-time events (`AddedToMempool`, `RemovedFromMempool`, `Confirmed`, `Reorg`, `Finalized`, `BlockConnected`, `BlockDisconnected`, `BlockFinalized`) to the WebSocket subscription hub.
3. Ensure `ChronikValidationInterface::SyncTransactionQueue()` overrides `CValidationInterface::SyncTransactionQueue()`:
   - Pushes a `std::promise<void>` barrier task onto `ChronikValidationInterface::m_queue` and waits for `m_worker_thread` to reach it whenever `ValidationSignals::SyncWithValidationInterfaceQueue()` or `ValidationSignals::FlushBackgroundCallbacks()` is called (so `generatetoaddress`, `invalidateblock`, `syncwithvalidationinterfacequeue`, and `Shutdown` deterministically wait for Chronik's background worker queue to drain).

---

### Commit 4: `chronik-cpp: serve all Chronik protobuf HTTP routes and /ws WebSockets via Boost.Beast`

#### Files to Create / Modify
- `chronik/chronik-cpp/chronik_http.h` (new)
- `chronik/chronik-cpp/chronik_http.cpp` (new)
- `chronik/chronik-cpp/chronik_ws.h` (new)
- `chronik/chronik-cpp/chronik_ws.cpp` (new)
- `src/httpserver.cpp`

#### Exact Implementation Steps
1. **Protobuf HTTP Route Dispatcher (`chronik_http.cpp`):**
   - Registers all Chronik routes directly on `Boost.Beast` (both under `/chronik/*` on the main RPC port `8332`/`10604` AND on the standalone `-chronikbind` listener `8321` so existing configs work 100% unchanged):
     - `GET /blockchain-info` $\rightarrow$ `pb::BlockchainInfo`
     - `GET /chronik-info` $\rightarrow$ `pb::ChronikInfo`
     - `GET /block/:hash_or_height`, `GET /block-header/:hash_or_height`, `GET /block-txs/:hash_or_height`
     - `GET /blocks/:start/:end`, `GET /block-headers/:start/:end`
     - `GET /tx/:txid`, `GET /raw-tx/:txid`, `GET /unconfirmed-txs`, `GET /token/:txid`
     - `POST /validate-tx`, `POST /broadcast-tx`, `POST /broadcast-txs`
     - `GET /script/:type/:payload/history`, `/confirmed-txs`, `/unconfirmed-txs`, `/utxos`
     - `POST /script/batch/utxos`, `POST /script/batch/summary`
     - `GET /token-id/:token_id/history`, `/confirmed-txs`, `/unconfirmed-txs`, `/utxos`
     - `GET /lokad-id/:lokad_id/history`, `/confirmed-txs`, `/unconfirmed-txs`, `/utxos`
     - `GET /pause`, `GET /resume`
   - Sets `Content-Type: application/x-protobuf` (and CORS headers when `-chronikcors=1`).
2. **WebSocket Pub/Sub Hub (`chronik_ws.cpp`):**
   - Handles `/ws` (and `/chronik/ws`) upgrades via `Boost.Beast` WebSocket streams.
   - Parses incoming `pb::WsSub` binary protobuf frames (`is_unsub`, `sub_type`: `blocks`, `txs`, `script`, `token_id`, `lokad_id`) and pushes `pb::WsMsg` binary protobuf frames to subscribed clients.

---

### Commit 5: `build: remove Cargo, Corrosion, cxxbridge, RocksDB, and Rust crates from Chronik build`

#### Files to Modify / Delete
- `CMakeLists.txt` (remove `Corrosion` / `Rust` requirement when `BUILD_CHRONIK=ON`)
- `chronik/CMakeLists.txt` (replace Cargo/Corrosion/`cxxbridge` targets with pure C++ `add_library(chronik ...)` linking `lotus_v2_mdbx` / `libmdbx` and `Protobuf::libprotobuf`)
- Delete Rust workspace crates (`chronik/chronik-lib`, `chronik/chronik-db`, `chronik/chronik-http`, `chronik/chronik-indexer`, `chronik/chronik-bridge`, `chronik/bitcoinsuite-*`, `chronik/abc-rust-*`, `chronik/chronik-plugin*`, `Cargo.toml`, `Cargo.lock`).

#### Verification
1. Configure with `-DBUILD_CHRONIK=ON` on a machine without invoking `cargo` or `rustc`.
2. Run existing Python Chronik functional tests (`test/functional/chronik_*.py`) to verify protobuf wire compatibility across blocks, transactions, script history/UTXOs, SLP/ALP tokens, `lokad_id`, and WebSockets.
