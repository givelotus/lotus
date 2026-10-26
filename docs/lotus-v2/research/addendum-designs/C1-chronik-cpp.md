# C1 — Native C++ Chronik: implementation-ready design

Status: design. It replaces the starting plan
`lotus-v2-optimizations/docs/plans/chronik-cpp-port-and-remove-rust-plan.md`
where the two disagree. All sources below come from `lotus-v2-repaired-source` at
`3cf1891b91`, read with `git show`. The working tree there is checked out at
`596537e978`, a different commit; the two commits differ outside `chronik/`.

Fixed user decisions:
- Pure C++20. No Rust, Cargo, Corrosion or cxxbridge.
- Order: first the eCash tier, then the V2 tier.
- Usable by BCHN, Dogecoin and Bitcoin Core, with a thin host layer.
- Wire-compatible with the protobuf HTTP and WebSocket API.
- No Electrum.
- The Rust implementation stays in the tree and is selectable by a build option.
- Served by the existing Boost.Beast server.

---

## 0. Decisions in one page

| # | Decision | Why (short) |
|---|---|---|
| D1 | New code lives in `chronik/native/`, namespace `chronik::native`. CMake option `CHRONIK_IMPLEMENTATION={rust,native}` (default `rust`), alongside the existing `BUILD_CHRONIK`. `native` never calls Cargo or Corrosion and has no Rust toolchain requirement. | Lets the two implementations coexist. Only one is linked, so there is no symbol clash. |
| D2 | The core depends only on: C++20 std, libmdbx (vendored), libprotobuf, Boost (header-only Asio/Beast), and a SHA-256 hook provided by the host. It never includes node headers. Everything node-specific goes through `chronik::native::Host` (§2). | Keeps the core thin and portable to BCHN, Core and Doged, so it can be upstreamed. |
| D3 | **On-disk schema = the Rust Chronik schema v13, byte-for-byte**, on the same MDBX environment layout, flags and table names, at the same path. Native opens existing Rust-built data **without a reindex**, and vice versa. Rust's later schema ideas are *not* adopted in this port. | No migration is needed. Switching implementation is safe. Parity can be proven by **dumping and diffing the DBs** (§8). Schema optimisation becomes a separate, measured v14 later. |
| D4 | **UTXO values (sats, and scripts for token groups) stay stored in Chronik tables**, as in Rust. Queries never read `CoinsTip()`. Consistency rule: *every response is computed from one Chronik snapshot* (one MDBX read txn plus one mempool copy at the same generation). Full input data for `/tx` is read from immutable blk/rev files at the offsets Chronik stored. | The starting plan's `CoinsTip()` reads are wrong while Chronik lags or is mid-reorg, take `cs_main` per UTXO, and depend on the host. Costs are in §3. |
| D5 | Storage sits behind `KvStore` (§4). There are two backends: `MdbxStore` (default, schema-compatible) and `LevelDbStore` (optional, for BCHN upstreaming). The LevelDB backend has the same *logical* schema; its physical keys are different and documented. | Satisfies the request for LevelDB support without making MDBX DUPSORT part of the logical contract. |
| D6 | Indexing runs single-writer and synchronously in the core. **The host adapter owns threading**: eCash/Lotus run indexing on the existing eCash-060 worker queue; BCHN, Core and Doged run it inline on the validation-signals thread. | Patch 060 is eCash-tier-only code. BCHN and Core have no `SyncTransactionQueue` hook. |
| D7 | HTTP and WS logic sits behind a transport-neutral `Router` and `WsSession` (§6). There are two transports: (a) in-process `/chronik/*` on the host's Beast server (eCash tier; replaces the patch-075 proxy when native), and (b) a standalone Beast listener for `-chronikbind` (all hosts; replaces axum). Blocking query work runs on a Chronik query pool and never on io threads. | Beast is required. BCHN and Core have libevent HTTP servers without WebSocket support. |
| D8 | Tokens: SLP and ALP are a **core module** (chain-agnostic script parsing), enabled per host capability. CashTokens are a **BCHN extension**; initially only the wrapped raw script bytes are kept, as today. Lotus V2 branches/assets and the V2 native service are a **V2-tier extension** (`chronik/native/ext/lotus_v2/`). Python plugins are **not ported**. | §5 |
| D9 | Electrum: no endpoints on any host. Setting any `-chronikelectrum*` argument is an `InitError`. The scripthash index (an HTTP feature) stays. | User decision |
| D10 | Wire parity is proven by: DB dump equality, an HTTP/WS corpus diff against the Rust build on the same chain, ported Rust unit-test vectors, and every non-Electrum, non-plugin `chronik_*.py` functional test (§8). | §8 |

---

## 1. What was verified vs assumed

**Verified in source** (`3cf1891b91` unless noted):
- **Crates:** 14 Rust crates under `chronik/` (about 63k lines incl. tests). The proto is `chronik/chronik-proto/proto/chronik.proto` (695 lines). Its only `map<>` fields are plugin maps (lines 129, 149, 183, 197), which are empty without plugins.
- **Schema version:** `CURRENT_INDEXER_VERSION = 13` (`chronik-indexer/src/indexer.rs:59`).
- **UTXO data:** `UtxoDataValue = i64` (`group.rs:162`), with `FIXED_DUP_SIZE = Some(12 + 8)` (`:165`). Script groups use it (`groups/script.rs:81`). `UtxoDataOutput = (i64, Bytes)` (`group.rs:183`). Rust therefore **stores sats** (and scripts, for token/plugin groups).
- **Query-time disk reads:** `ChronikBridge::load_tx` reads tx data and undo from disk at stored offsets (`chronik-cpp/chronik_bridge.cpp:383-399`). `undo_pos == 0` means coinbase.
- **Validation interface:** `TransactionAddedToMempool(tx, spent_coins, seq, entry_time)` (`src/validationinterface.h:73-82`, eCash 059). `SyncTransactionQueue()` virtual at `:55` (eCash 060). Patch 060 adds the `BoundedTaskQueue` worker: 256 MiB / 65,536 tasks, fail-closed shutdown.
- **HTTP server:** Beast exposes `RegisterHTTPAsyncHandler` (coroutine) and `RegisterPublicHTTPPrefix` (`src/httpserver.h:72-99`). `/chronik` is currently a reverse proxy (`httpserver.cpp:357-381, 853-1000`) to axum on `-chronikbind`.
- **Entry points:** `chronik::Start/Interrupt/Stop` in `chronik/chronik-cpp/chronik.h`.
- **Test gating:** `test/config.ini.cmake.in` has `ENABLE_CHRONIK` and `ENABLE_CHRONIK_PLUGINS`. There are 50 `chronik_*.py` functional tests. Of these, Electrum: `chronik_electrum_basic.py` and `chronik_electrum_blockchain.py`; plugins: `chronik_plugins.py`, `chronik_plugin_groups.py`, `chronik_plugins_setup.py`.
- **WS fan-out:** tokio broadcast capacities: blocks 16, txs 32, group 16 (`subs.rs:56-57`, `subs_group.rs:46`). Lagged receivers drop messages silently (`ws.rs:600, 642`).
- **History paging:** `MIN/MAX_HISTORY_PAGE_SIZE = 1/200` (`query/group_history.rs:33-35`).
- **Protobuf in the build:** used by Qt (`src/qt/CMakeLists.txt:240-255`, `find_package(Protobuf CONFIG)` with fallback). Packages `native_protobuf` and `protobuf` exist in depends.
- **libmdbx vendoring:** `src/lotus_v2/vendor/libmdbx/` (eCash 004). `CDBWrapper` is MDBX-backed (eCash 005).
- **Rust DB internals (from a full read of `chronik-db`):** postcard + serde values, env flags and geometry, the 31 table names, merge emulation, the 7500-byte key hashing, refusal of legacy RocksDB artifacts, and the V2 `v2_index` environment (schema 3, 16 DBIs, `v2_tx_NNNNN.dat` flat files). See §4.
- **V2 C++ sink:** a C++ `ChronikSink` interface already exists in `src/lotus_v2/chronik_sync.h` (v2/021). Nothing in CMake defines `LOTUS_V2_CHRONIK_CXX`, so its Rust sink is unused.
- **Host adapters:** BCHN, Core and Doged were taken from `lotus/daemon/` docs and patches only (`docs/shared-chronik-source-and-hosts.md`, `chronik/hosts/{abc,bitcoin-core,bchn}/`, `patches/doged/0042,0044,0076-0083,0110`). Their exact API names are in §7.

**Defects observed in the current Rust/bridge code.** The port must not copy these, and parity tests list them as expected differences:
1. **Compile hazard:** `chronik_bridge.cpp:719-739` defines `V2FeeRateInfo get_v2_fee_rate_info()`, but that type is declared in neither bridge. This is likely a compile error; the coordinator should check it.
2. **V2 txid from a legacy-shaped tx:** `lookup_spent_coins` rebuilds a legacy-shaped transaction (`chronik_bridge.cpp:447-466`). For V2 transactions, the txid it computes probably differs from the real one.
3. **Per-IP limit behind the proxy:** the `-chronikmaxsubsperip` limit keys on the proxy socket address, so every `/chronik/ws` client counts as loopback. Native in-process WS uses the real peer address.
4. **Unverified undo indexing:** `BridgeTxInputs` skips `nFlags==3` inputs but indexes `spent_coins[idx]` by raw position (`:140-148`). Not verified either way.

**Assumed (not verified):**
- Exact eCash/Lotus mainnet UTXO counts and Chronik DB sizes. The cost figures in §3 are estimates and are labelled as such.
- That Rust ignores unknown `meta` keys. `io/metadata.rs` reads only named keys, but nothing iterates `meta`; the first parity test confirms it (§4.4).
- prost and libprotobuf both emit fields in field-number order with proto3 default omission. That makes byte equality expected. Parsed-message equality is the hard acceptance criterion.
- BCHN and Doged sources were not read; there are no local clones, by instruction. Their details come from the `lotus/daemon` docs and patches.

---

## 2. Host-adapter boundary

### 2.1 Neutral data model — `chronik/native/include/chronik/native/types.h`

```cpp
#pragma once
#include <array>
#include <cstdint>
#include <memory>
#include <optional>
#include <span>
#include <string>
#include <vector>

namespace chronik::native {

using Bytes = std::vector<uint8_t>;
// 32-byte hashes in the node's INTERNAL (little-endian) byte order, exactly as
// Rust Chronik stores them (TxId::to_bytes / BlockHash::to_bytes).
struct Hash32 {
    std::array<uint8_t, 32> b{};
    auto operator<=>(const Hash32 &) const = default;
};
using TxId = Hash32;
using BlockHash = Hash32;

struct OutPoint { TxId txid; uint32_t out_idx{}; auto operator<=>(const OutPoint&) const = default; };

struct TxOutput {
    int64_t sats{};
    // Host-defined "indexed script" bytes. ABC: scriptPubKey. BCHN: CashTokens
    // wrapped script (token prefix || scriptPubKey). Lotus V2: the synthetic
    // native-output frame produced by the V2 adapter (see §7.2). The core never
    // interprets these bytes beyond script classification/compression.
    Bytes script;
};

struct Coin { TxOutput output; int32_t height{}; bool is_coinbase{}; };

struct TxInput {
    OutPoint prev_out;
    Bytes script;            // scriptSig, or host-defined (V2: coinbase data / witness[0].script)
    uint32_t sequence{};
    std::optional<Coin> coin;  // spent coin; nullopt only for coinbase
};

struct Tx {
    TxId txid;               // host-computed (ABC: GetId; Core: stripped GetHash; Lotus: merkleized)
    int32_t version{};       // signed: Doged needs negative versions; ABC casts back to uint32 in proto
    std::vector<TxInput> inputs;
    std::vector<TxOutput> outputs;
    uint32_t locktime{};
    // Full wire serialization when it differs from the legacy-shaped re-serialization
    // the core would otherwise need (Core witness, V2 native wire). If empty, the
    // host's LoadRawTx / RawTxBytes are authoritative. wire_size is ALWAYS set.
    Bytes raw;
    uint32_t wire_size{};
    bool is_coinbase() const { return inputs.size() == 1 && inputs[0].prev_out.txid == Hash32{}; }
};
using TxRef = std::shared_ptr<const Tx>;

struct BlockTx { TxRef tx; uint32_t data_pos{}; uint32_t undo_pos{}; }; // undo_pos==0 <=> coinbase

struct BlockInfo {
    BlockHash hash, prev_hash;
    int32_t height{};
    uint32_t n_bits{};
    int64_t timestamp{};
    uint32_t file_num{}, data_pos{}, undo_pos{};
    uint64_t size{};          // serialized block size (Core: with witness)
};

struct Block {
    BlockInfo info;
    std::vector<BlockTx> txs; // vtx order; txs[0] is the coinbase; inputs carry spent coins from undo
};

enum class MempoolRemovalReason : uint8_t { Expiry, SizeLimit, Reorg, Block, Conflict, Replaced, Other };

struct HostCapabilities {
    bool avalanche = false;            // Block/Tx Finalized+Invalidated events, preconsensus query
    bool slp_alp_tokens = false;       // allows -chroniktokenindex (core SLP/ALP module)
    bool allow_pause_on_this_chain = false; // -chronikallowpause permitted (never on mainnet)
    bool witness = false;              // Tx::raw carries witness serialization
    std::string network;               // "main","test","regtest",... for defaults and log
    uint16_t default_http_port = 0;    // -chronikbind default port
    std::string client_name;           // ChronikInfo.version uses FormatFullVersion() via host
};

} // namespace chronik::native
```

The core stores only `Hash32`, `int64_t` and offsets. It never computes txids, header hashes or block-tx offsets; the host computes all chain-specific values.

### 2.2 Host interface — `chronik/native/include/chronik/native/host.h`

```cpp
#pragma once
#include <chronik/native/types.h>
#include <chrono>
#include <functional>
#include <string_view>

namespace chronik::native {

struct BroadcastResult { bool ok{}; TxId txid; std::string error; };   // error = "<TransactionError>: <msg>"
struct FeeRateInfo { int64_t sats_per_kb{}; uint32_t vsize{}; };
struct DecodedTx { bool ok{}; Tx tx; std::string error; };           // spent coins NOT resolved
struct SpentCoinLookup { std::vector<OutPoint> not_found; std::vector<OutPoint> to_uncache; };

/**
 * Everything the indexer core needs from the node. Thread rules:
 *  - Every method is callable from any Chronik thread (writer, query pool, init).
 *  - The core NEVER calls a Host method while holding its exclusive state lock.
 *  - Methods may take host locks (cs_main, mempool.cs) internally and must not
 *    call back into Chronik.
 * Errors: return values for expected misses; throw std::runtime_error for I/O
 * corruption (the core maps it to FatalError on the writer, 500 on queries).
 */
class Host {
public:
    virtual ~Host() = default;
    virtual const HostCapabilities &Capabilities() const = 0;

    // ---- chain view (validated/active chainstate only) ----
    virtual std::optional<BlockInfo> ActiveTip() const = 0;
    virtual std::optional<BlockInfo> LookupBlock(const BlockHash &) const = 0; // any branch
    virtual std::optional<BlockInfo> ActiveAtHeight(int32_t height) const = 0;
    virtual std::optional<BlockInfo> FindFork(const BlockHash &) const = 0;    // last common active ancestor
    virtual BlockHash GenesisHash() const = 0;
    // Exact raw header bytes (80 ABC/BCHN/Core, 160 Lotus V1, 134 Lotus V2, variable Doged AuxPoW).
    virtual Bytes RawHeader(const BlockInfo &) const = 0;
    // Batch form; returns a prefix if the range runs past the active tip.
    virtual std::vector<Bytes> RawHeadersByRange(int32_t start, int32_t end) const = 0;

    // ---- immutable block storage (no cs_main needed by contract) ----
    // Load + decode block, spent coins from undo, per-tx data_pos/undo_pos (host computes
    // first-tx offset: header size [+ vMetadata] + CompactSize(n_tx), witness-aware sizes).
    virtual Block LoadBlock(const BlockInfo &) const = 0;
    virtual Tx LoadTx(uint32_t file_num, uint32_t data_pos, uint32_t undo_pos) const = 0;
    virtual Bytes LoadRawTx(uint32_t file_num, uint32_t data_pos) const = 0;

    // ---- mempool / relay ----
    virtual DecodedTx DecodeRawTx(std::span<const uint8_t> raw) const = 0; // rejects trailing bytes
    // Fill inputs[i].coin from CoinsTip+mempool view (broadcast/validate token checks only).
    virtual SpentCoinLookup LookupSpentCoins(Tx &tx) const = 0;
    virtual void UncacheCoins(std::span<const OutPoint>) const = 0;
    virtual BroadcastResult Broadcast(std::span<const uint8_t> raw, int64_t max_fee_sats) const = 0;
    virtual int64_t CalcMaxFee(size_t tx_size) const = 0;  // host default max raw-tx fee rate
    virtual std::optional<FeeRateInfo> MempoolFeeRate(const TxId &) const = 0;
    virtual int64_t EstimateFeeRateSatsPerKb() const = 0;
    virtual int64_t MinRelayFeeRateSatsPerKb() const = 0;
    // nullopt <=> capability absent (Core/BCHN); core then reports is_final=false.
    virtual std::optional<bool> IsFinalizedPreConsensus(const TxId &) const = 0;
    // Waits until every event already published by the node has been applied by Chronik
    // (eCash: SyncWithValidationInterfaceQueue, which fences the 060 worker; inline hosts:
    // host SyncWithValidationInterfaceQueue()).
    virtual void SyncWithIndexer() const = 0;

    // ---- process ----
    virtual bool ShutdownRequested() const = 0;
    virtual void FatalError(std::string_view log_msg, std::string_view user_msg) const = 0;
    virtual void Log(std::string_view msg, bool debug_category_only) const = 0;
    virtual std::string FormatFullVersion() const = 0;
    virtual void Sha256(std::span<const uint8_t>, uint8_t out[32]) const = 0; // scripthash, key hashing
};

} // namespace chronik::native
```

### 2.3 Indexer event API — `chronik/native/include/chronik/native/indexer.h`

The host adapter turns its validation signals into these calls. The calls must be made from **one thread at a time, in signal order**.

```cpp
#pragma once
#include <chronik/native/host.h>
#include <chronik/native/store.h>

namespace chronik::native {

struct IndexerParams {
    std::filesystem::path datadir_net;   // index at <datadir_net>/indexes/chronik (same as Rust)
    bool wipe = false;                   // -chronikreindex / -reindex
    bool token_index = true, lokad_id_index = true;
    std::optional<bool> scripthash_index;// unset => Rust default semantics (off without Electrum)
    size_t tx_num_cache_buckets = 10, tx_num_cache_bucket_size = 100'000;
    bool perf_stats = false;
    StoreBackend backend = StoreBackend::Mdbx;
};

class Extension;  // §5.3

class Indexer {
public:
    // Opens/creates the store, verifies schema (§4.4), runs resync (§3.3) synchronously.
    static std::unique_ptr<Indexer> Open(const Host &, IndexerParams,
                                         std::vector<std::unique_ptr<Extension>> exts);
    // Events (writer thread only):
    void OnTxAddedToMempool(TxRef tx, int64_t time_first_seen);   // tx inputs carry spent coins
    void OnTxRemovedFromMempool(const TxId &, MempoolRemovalReason);
    void OnBlockConnected(const BlockInfo &);                    // indexer calls Host::LoadBlock
    void OnBlockConnected(Block &&);                             // or pre-loaded block
    void OnBlockDisconnected(const BlockInfo &);
    void OnBlockFinalized(const BlockInfo &);                    // avalanche hosts only
    void OnBlockInvalidated(const BlockInfo &);
    void OnTxFinalized(const TxId &);
    void OnTxInvalidated(TxRef);
    void Interrupt();   // stop HTTP/WS sessions, refuse new queries
    void Close();       // flush+sync store

    QueryApi &Queries();   // §6, thread-safe
    SubscriptionHub &Subs();
};

} // namespace chronik::native
```

**Error rule:** a failing writer event calls `Host::FatalError` and puts the indexer in `failed` state, in which every query returns `500`. This is the same as Rust's `ok_or_abort`.

### 2.4 Adapter responsibilities, per host

Each adapter is a `chronik/native/hosts/<host>/` directory compiled into the node. It contains:
1. a `Host` implementation;
2. a validation-interface subscriber that converts host types into neutral types and calls `Indexer::On*`;
3. `chronik::Start/Interrupt/Stop`, with the signatures of `chronik/chronik-cpp/chronik.h`, so `init.cpp` is unchanged on ABC;
4. argument parsing (a port of `ParseChronikParams`).

The core never sees `CTransaction`, `CBlockIndex`, `Coin`, `Amount`, `Config` or `NodeContext`.

| Concern | ABC/eCash (eCash tier) | Lotus V2 (V2 tier) | BCHN `abd433ab` | Doged (174-patch series) | Bitcoin Core `f13ae519` |
|---|---|---|---|---|---|
| Header | 80 B | 134 B | 80 B | variable; `index.GetBlockHeader(blockman)` reads AuxPoW from disk (0044/0077) | 80 B |
| First-tx offset | `nDataPos + 80 + CompactSize(n)` | `+134` | as ABC | `GetSerializeSize(block.GetBlockHeader())` (0076) | as ABC, tx sizes with `TX_WITH_WITNESS` |
| TxId | `tx.GetId()` | V2 txid (native identity, *not* legacy-shaped recompute) | `tx.GetId()` | `GetId()` | `tx.GetHash()` (stripped); `Tx::raw` = witness bytes |
| Output script | `scriptPubKey` | synthetic native-output frame (§7.2) | `token::WrapScriptPubKey(tokenDataPtr, spk)` | `scriptPubKey` | `scriptPubKey` |
| Block/undo read | `m_blockman.ReadBlock/ReadBlockUndo`, `ReadTxFromDisk/ReadTxUndoFromDisk` | same, plus V2 conversion | `ReadBlockFromDisk`, `UndoReadFromDisk`, `OpenBlockFile/OpenUndoFile` + `CAutoFile` (un-static `OpenUndoFile`) | ABC API + `ReadBlockHeaderFromDisk` | `ReadBlock/ReadBlockUndo` + new XOR-aware `ReadIndexedTransaction(Undo)` (never raw FILE) |
| Mempool add | `TransactionAddedToMempool(tx, spent_coins, seq, entry_time)` | same | `CaptureMempoolAdmission` hook (`validation_hooks.h`) | ABC form | `NewMempoolTransactionInfo` + `spent_coins`, `acceptance_time` (node patch) |
| Mempool remove | `TransactionRemovedFromMempool` | same | `CaptureMempoolRemovals(descendants_first)` | same | `TransactionRemovedFromMempool`, child-first mirror |
| Block connect | `BlockConnected(role,…)`; skip `ASSUMEDVALID` | same | `BlockConnected(block, index, conflicts)`; conflicts are removed first, `DescendantsFirst()` | ABC | `BlockConnected(role,…)`; skip `!role.validated`; `MakeIndexedBlockDurable` |
| Block disconnect | `BlockDisconnected(block, index)` | same | `(block)`; the index is looked up under `cs_main` | ABC | `(block, index)` |
| Avalanche | yes (4 callbacks) | yes (V2 tier keeps parking/avalanche, v2/042) | no | retained, off by default (0086) | no |
| Threading (D6) | 060 worker (`BoundedTaskQueue`) | same | inline on scheduler thread | inline | inline |
| `SyncWithIndexer` | `validation_signals->SyncWithValidationInterfaceQueue()` (fences the worker via `SyncTransactionQueue`) | same | `::SyncWithValidationInterfaceQueue()` | ABC | `validation_signals->SyncWithValidationInterfaceQueue()` |
| Broadcast | `node::BroadcastTransaction` | same | `AcceptToMemoryPool` + `ForEachNode(PushInventory)` | ABC | `BroadcastTransaction(..., MEMPOOL_AND_BROADCAST_TO_ALL)`; `max_fee=0` → Core default |
| Refusals | prune | prune | prune; `-chroniktokenindex=1` | prune | prune; background assumeutxo chainstate; `loadtxoutset` while `-chronik` |
| Capabilities | avalanche, slp_alp | avalanche; slp_alp per V2 decision (§5) | none | avalanche (off by default), slp_alp as Rust Doged | witness |

**Doged signed versions.** Doged patch 0078 changes `chronik.proto` `Tx.version` from `uint32` to `int32`. The native core compiles the **same** `chronik.proto` file the Rust build uses, so Doged's proto patch applies to both implementations. The core writes the field as `pb.set_version(static_cast<decltype(pb.version())>(tx.version))`, which needs no profile flag.

---

## 3. Consistency model (problem 2)

### 3.1 Decision

UTXO values stay in Chronik's own tables, exactly as Rust Chronik v13 stores them:
- `script_utxo`, `v2_branch_utxo`, `v2_asset_utxo`: 20-byte DUPFIXED entries. Layout: `tx_num BE8 ‖ out_idx BE4 ‖ sats LE i64`.
- `token_id_utxo`: postcard `(sats, script)` after the 12-byte outpoint.

Queries never read `CoinsTip()` and never take `cs_main` for UTXO data.

**Consistency rule (normative):**
1. **One snapshot per response.** A response is built from exactly one `Snapshot`, which holds:
   - one MDBX read transaction;
   - `mempool_view`, a copy of the mempool entries the query touches, taken under the shared state lock while the read txn is open;
   - `tip`, Chronik's own indexed tip.

   Data from the node chainstate is never mixed in.
2. **Writer publish order.** The writer commits block N's DB txn and applies block N's mempool removals while holding the exclusive state lock, in one critical section. A snapshot therefore sees either the whole block or none of it, and the mempool always agrees with the DB.
3. **What clients see.**
   - `/blockchain-info` reports Chronik's indexed tip, not the node tip, so a lagging Chronik is visible to clients.
   - During a reorg, responses reflect the last fully applied block event. Each disconnect is one atomic step, as in Rust.
4. **Immutable file reads.** Reads from blk/rev files (`/tx`, `/raw-tx`, history pages) happen after the lock is released, using offsets from the snapshot. Those files are immutable while referenced, because pruning is refused on every host.
   - If Chronik is ahead of the node after a crash (§3.3), offsets are re-validated by resync before queries are served.

### 3.2 Cost justification (estimates; assumptions stated)

**Option A (chosen): store sats, as Rust does.**
- **Extra disk:** 8 B per confirmed UTXO in `script_utxo` (20 B vs 12 B per dup), plus the branch/asset copies in V2.
  - At 15M UTXOs (assumed order of magnitude for eCash): about 120 MB.
  - At 100M UTXOs: about 0.8 GB.
  - Compared with total Chronik index size, which is dominated by history pages, `tx`, `spent_by` and lookups, this is assumed to be a low single-digit percentage.
- **Write cost:** none extra. The writer already has the coin values in hand (block outputs and undo coins).
- **Query cost:** one cursor walk, `GET_MULTIPLE` over DUPFIXED pages. That is about 0.05–0.2 µs per UTXO in page cache, with no lock.

**Option B (starting plan): `CoinsTip().AccessCoin()` per UTXO under `cs_main`.**
- **Latency per lookup (estimated):**
  - CCoinsViewCache hit: about 0.3–1 µs.
  - Miss, served from chainstate MDBX in page cache: about 2–5 µs.
  - Cold SSD: about 50–200 µs.
- **Large addresses:** an address with 50k UTXOs (exchange, faucet) needs 50k lookups. That holds `cs_main` for about 25–250 ms warm, or seconds cold.
- **Batches:** `/script/batch/utxos` accepts 500 scripts per request, which multiplies the above.
- **Who waits:** while `cs_main` is held, block connection, mempool acceptance and RPC all wait.
- **Cache side effects:** misses pollute `dbcache`. Undoing that needs `Uncache`, which takes `cs_main` again; Rust already pays this on its broadcast path (`uncache_coins`).
- **Correctness:**
  - **Lag.** Chronik trails the chainstate by up to the 060 queue bound (65,536 events / 256 MiB). During startup catch-up it can trail by any number of blocks. In that window, outputs spent in un-indexed blocks are missing from `CoinsTip`, while Chronik's history still shows them unspent. Outputs created in un-indexed blocks are not yet in Chronik's index. The result is a response that matches neither state.
  - **Mid-reorg.** The chainstate is already on the new fork while Chronik still holds outputs from disconnected blocks. Coin values may come from a different transaction under the same outpoint, which BIP30-style duplicates make possible on legacy chains.
  - **Expiry (Lotus V2).** C17a fee-backed UTXO expiry (v2/055) removes coins from the chainstate on the chain's schedule, not on Chronik's.
  - **Portability.** It needs per-host coin APIs: `GetCoin` returns a bool on BCHN and `std::optional` on ABC/Core, and Core requires role checks.

Option B saves at most about 1 GB of disk. In exchange it puts `cs_main` on the query path, makes answers depend on scheduling, and breaks D3 (byte compatibility). It is rejected.

The `/tx` input values are also not duplicated. Rust already reads them from rev files, and native keeps that: those files are immutable and need no lock. This is the only "zero duplication" that is safe.

### 3.3 Startup, catch-up, crash recovery (port of `indexer.rs:380-456`)

Behaviour is the same as Rust.
1. **Verify schema** (§4.4).
2. **Compare tips.**
   - If the DB tip ≠ the node's active tip, call `Host::LookupBlock(db_tip)`.
   - If that finds nothing (the node lost the block after a crash), fail with Rust's `CannotRewindChronik` text and advise `-chronikreindex`.
   - Otherwise `FindFork`, then disconnect from DB height down to fork+1. Each disconnect does `LoadBlock` and `OnBlockDisconnected`.
3. **Optional reindexes.** Run the LOKAD-ID and scripthash reindexes if they were just enabled.
4. **Catch up.** For each `h` in `db_tip+1 ..= node_tip`: `ActiveAtHeight(h)`, `LoadBlock`, connect. This is one write txn per block.
5. **Abort on shutdown.** `ShutdownRequested()` is checked every block.
6. **Progress logging.** Log every 100 blocks.

Resync runs on the init thread before the subscriber registers, so no events are lost. Events published between the end of resync and registration are prevented by registering *under the same cs_main hold* that reads the final tip. The ABC adapter does this; for BCHN and Core it is a `LOCK(cs_main)` around read-tip + `RegisterValidationInterface`, then a second catch-up pass. The Rust adapters already rely on this ordering.

### 3.4 Threading model

| Thread | Owner | Does |
|---|---|---|
| init | host | `Indexer::Open` (resync), transport start |
| writer | host adapter: eCash/Lotus = 060 worker; BCHN/Core/Doged = scheduler thread | `On*` events. Heavy work (LoadBlock, building the batch) happens **without** the state lock. Then `X-lock{ commit txn; apply mempool delta; bump generation }`. Then WS publish. |
| query pool | core (`QueryPool`, default `min(8, hw/2)`, hidden `-chronikqueryworkers`) | executes handlers: `S-lock{ open read txn; copy mempool slice }`, then unlock, then disk reads and proto build |
| io | host Beast threads (in-process) or Chronik listener `io_context` (2 threads) | parse, route, `co_await` the pool result, write. Never blocks. |
| ws sessions | io executors, one strand each | per-subscription ring buffers (§6.3) |

**Locks:**
- `std::shared_mutex state_`: the writer takes it exclusive; snapshot capture takes it shared.
- The core never calls `Host` while holding `state_` exclusively.

**Lock order:** host locks (cs_main, mempool.cs) → never acquired while holding `state_`. Snapshot capture copies only Chronik-owned memory.

---

## 4. Storage (problem 3)

### 4.1 Interface — `chronik/native/include/chronik/native/store.h`

```cpp
#pragma once
#include <cstdint>
#include <filesystem>
#include <memory>
#include <optional>
#include <span>
#include <string_view>

namespace chronik::native {

enum class StoreBackend { Mdbx, LevelDb };
using ByteView = std::span<const uint8_t>;

struct TableSpec {
    std::string_view name;               // exact Rust CF name, e.g. "script_utxo"
    enum class Kind { Plain, Dup } kind = Kind::Plain;
    std::optional<uint32_t> dup_fixed_size; // Dup only; MDBX_DUPFIXED when set
};
using TableId = uint16_t;

class Cursor {             // ordered iteration over one table
public:
    virtual ~Cursor() = default;
    virtual bool SeekFirst() = 0;
    virtual bool SeekLast() = 0;
    virtual bool SeekGe(ByteView key) = 0;        // MDBX_SET_RANGE
    virtual bool SeekLe(ByteView key) = 0;        // MDBX_TO_KEY_LESSER_OR_EQUAL
    virtual bool Next() = 0;
    virtual bool Prev() = 0;
    virtual ByteView Key() const = 0;
    virtual ByteView Value() const = 0;
};

class DupCursor {          // the duplicate values of one key, ascending
public:
    virtual ~DupCursor() = default;
    virtual bool Seek(ByteView key) = 0;
    virtual bool SeekValueGe(ByteView key, ByteView value_prefix) = 0; // GET_BOTH_RANGE
    virtual bool Next() = 0;
    virtual ByteView Value() const = 0;
    virtual size_t CountRemaining() = 0;
};

class ReadTxn {
public:
    virtual ~ReadTxn() = default;
    virtual std::optional<ByteView> Get(TableId, ByteView key) const = 0; // view valid until txn ends
    virtual std::unique_ptr<Cursor> OpenCursor(TableId) const = 0;
    virtual std::unique_ptr<DupCursor> OpenDupCursor(TableId) const = 0;
    virtual uint64_t EstimateEntries(TableId) const = 0;
};

class WriteTxn : public ReadTxn {   // reads observe this txn's own writes
public:
    virtual void Put(TableId, ByteView key, ByteView value) = 0;
    virtual void Del(TableId, ByteView key) = 0;
    virtual void PutDup(TableId, ByteView key, ByteView value) = 0;   // idempotent
    virtual void DelDup(TableId, ByteView key, ByteView value) = 0;   // exact
    virtual void DelDupByPrefix(TableId, ByteView key, ByteView value_prefix) = 0;
    virtual void Clear(TableId) = 0;                                   // mdbx_drop(…, false)
    virtual void Commit() = 0;   // throws on failure; txn unusable after
};

class KvStore {
public:
    virtual ~KvStore() = default;
    static std::unique_ptr<KvStore> Open(StoreBackend, const std::filesystem::path &dir,
                                         std::span<const TableSpec> tables);
    static void Destroy(StoreBackend, const std::filesystem::path &dir);
    virtual TableId Table(std::string_view name) const = 0;
    virtual std::unique_ptr<ReadTxn> BeginRead() const = 0;   // any thread, concurrent
    virtual std::unique_ptr<WriteTxn> BeginWrite() = 0;       // writer thread only
    virtual void Sync(bool force) = 0;
};

} // namespace chronik::native
```

Merge operators are **not** part of the interface. Every Rust merge (history append and trim, lookup list insert, spent_by insert) becomes an explicit read-modify-write in the `WriteTxn`. This is exactly what Rust's MDBX merge emulation does at commit (`db.rs` `write_batch`), so the resulting bytes are identical.

### 4.2 `MdbxStore`: must match the Rust env exactly

Rust `db.rs` values to reproduce:
- **One env** at `<datadir_net>/indexes/chronik/`.
- **Limits:** `max_readers=256`; `max_dbs=max(n_tables+16, 64)`.
- **Geometry:** lower 1 MiB, initial 16 MiB, upper 256 GiB, growth 64 MiB, shrink 128 MiB, pagesize 16 KiB.
- **Flags:** `MDBX_SAFE_NOSYNC|MDBX_NOMETASYNC|MDBX_LIFORECLAIM|MDBX_NOSTICKYTHREADS|MDBX_NOMEMINIT`, mode 0600. `MDBX_OPT_SYNC_BYTES=16 MiB`, `SYNC_PERIOD=65536`. `Close()` calls `mdbx_env_sync_ex(force)`.
- **Tables:** one named DBI per table with `MDBX_CREATE`. `DUPSORT` (+`DUPFIXED` when fixed) is used **only** for the five group-UTXO tables.
- **Long keys:** a key longer than 7500 bytes is stored as `"MDBX_SHA256_KEY:" ‖ sha256(key)`. This is physical-layer behaviour inside `MdbxStore`, using `Host::Sha256` injected at open.
- **Reader pooling:** up to 32 read txns and 32 cursors.

The vendored libmdbx is linked from `src/lotus_v2/vendor/libmdbx` (`lotus_v2_mdbx` target). Out-of-tree hosts (BCHN, Core, Doged) receive the same vendored copy through the shared-source export (§9).

### 4.3 `LevelDbStore` (optional; for BCHN)

- **Location:** one LevelDB at `<datadir_net>/indexes/chronik-leveldb/`, a different directory so it is never confused with MDBX.
- **Plain table key:** `varint(table_index) ‖ key`. The `table_index` mapping is fixed: the table's position in the `kTables` array (§4.5), stored in `meta`.
- **Dup table key:** `varint(table_index) ‖ varint(len(key)) ‖ key ‖ dupvalue`, with an empty value. Iterating a member's dups is a prefix scan, and dup order matches MDBX (memcmp of values).
- **Long keys:** no hashing. LevelDB has no key-length limit, and logical keys never depend on it.
- **ReadTxn** = a `leveldb::Snapshot`.
- **WriteTxn** = a `WriteBatch` plus an in-memory ordered overlay (read-your-writes). Commit uses `sync=false`; `Sync(force)` writes an empty batch with `sync=true`.
- **Comparator:** bytewise, the default.

The LevelDB backend is not byte-compatible with Rust data. It is selected by the hidden `-chronikdbbackend=leveldb` and only exists when built with `CHRONIK_NATIVE_LEVELDB=ON`. Opening it on an MDBX index directory, or the reverse, is an error.

### 4.4 Schema version, metadata and migration

- **`meta` keys and values:** `SCHEMA_VERSION` = postcard u64 13; `TOKEN_INDEX_ENABLED`, `LOKAD_ID_INDEX_ENABLED`, `SCRIPTHASH_INDEX_ENABLED` = postcard bool.
- **Version semantics** match `verify_schema_version`: >13 → `ChronikOutdated`; <13 → `DatabaseOutdated (-chronikreindex)`; missing on a non-empty DB → `MissingSchemaVersion`; undecodable → `CorruptedSchemaVersion`. An empty DB is written as 13.
- **Index flags:**
  - Disabling the token or LOKAD index clears those tables.
  - Enabling the token index on a non-empty DB is an error.
  - Enabling the LOKAD or scripthash index on a non-empty DB triggers that index's reindex, as in Rust.
- **Legacy RocksDB refusal:** port the same refusal. If the directory contains `CURRENT`, `IDENTITY`, `rocksdb.bak`, `MANIFEST-*`, `OPTIONS-*` or `*.sst`, opening fails with the same guidance text.
- **New meta key `NATIVE_LAST_WRITER`** (postcard String, e.g. `"native/<FormatFullVersion>"`) is written on every open. It is diagnostic only. The first parity step confirms that Rust opens a DB containing it (assumption in §1).
- **Plugin data:** if `plugin_meta` is non-empty (the DB was built with Rust plugins), native refuses to open and says "built with Chronik plugins; reindex with -chronikreindex or use the Rust build". This fails closed instead of silently desynchronising plugin tables.
- **Migration:**
  - From Rust v13 (MDBX): **none**; the data is shared directly.
  - From Doged legacy schemas 10–12: native does not port Doged's `upgrade_10_to_11/11_to_12/12_to_13` (patches 0082/0110); it requires `-chronikreindex`. Rust Doged keeps its upgrader, and an upgraded DB is v13 and can then be shared.
  - From LevelDB to MDBX, or the reverse: reindex.
- **Why reindex is acceptable for the non-shared cases:** they are rare. They replay only local blk/rev files at Chronik's indexing speed, with no network, and `-chronikreindex` already exists.

### 4.5 Logical schema v13 (authoritative for the port)

**Notation:**
- `BE4/BE8`: big-endian fixed width.
- `pc(...)`: postcard. LEB128 varint for u16–u128; zigzag+varint for i32/i64; raw u8 and bool; `[u8;N]` raw; `Vec`/`Bytes`/`String` = varint length + items; `Option` = tag byte; enum = varint index + fields; struct = fields in order; `BTreeMap` = varint length + sorted pairs.
- `pc*(...)`: postcard items concatenated with no length prefix.
- Hashes are in internal LE order, except where marked `rev`.

| Table | Key | Value | Notes |
|---|---|---|---|
| `meta` | ASCII name | pc value | §4.4 |
| `blk` | height i32 BE4 | pc `SerBlock{hash[32], n_bits u32, timestamp i64, file_num u32, data_pos u32}` | `prev_hash` comes from height−1 |
| `blk_stats` | height BE4 | pc `BlockStats{block_size u64, num_txs u64, num_inputs u64, num_outputs u64, sum_input_sats i64, sum_coinbase_output_sats i64, sum_normal_output_sats i64, sum_burned_sats i64}` | |
| `lookup_blk_by_hash` | `(seahash(hash) as u32)` BE4 | pc `Vec<i32>` sorted heights | insert = RMW binary insert; duplicate → error |
| `tx` | tx_num BE8 | pc `SerTx{txid[32], data_pos u32, undo_pos u32, time_first_seen i64}` | `undo_pos==0` ⇔ coinbase |
| `blk_by_first_tx` | tx_num BE8 | height BE4 (raw) | |
| `first_tx_by_blk` | height BE4 | tx_num BE8 (raw) | |
| `lookup_tx_by_hash` | `seahash(txid)` BE8 | pc `Vec<u64>` sorted | |
| `spent_by` | **pc varint** tx_num | `pc*(SpentByEntry{out_idx u32, tx_num u64, input_idx u32})` sorted by out_idx | key is a varint, not BE |
| `<g>_history` | member ‖ page BE4 | `pc*` varint u64 tx_nums, strictly ascending | 1000 per page; empty page → delete |
| `<g>_history_num_txs` | member | u32 BE4 (raw) | |
| `<g>_utxo` (Dup) | member | `tx_num BE8 ‖ out_idx BE4 ‖ suffix` | suffix: Value groups = sats **LE** i64 (DUPFIXED 20); Output groups = pc `(i64, Bytes)` |
| `scripthash` | `sha256(script)` **rev** 32 | compressed script | only when enabled, written when num_txs was 0 |
| `token_meta` | genesis tx_num BE8 | pc `TokenMeta{token_id[32] LE, token_type: enum{Slp(SlpTokenType), Alp(AlpTokenType)}}` | `SlpTokenType` 0 Fungible, 1 MintVault, 2 Nft1Group, 3 Nft1Child, 4 Unknown(u8); `Alp` 0 Standard, 1 Unknown(u8) |
| `token_genesis_info` | genesis tx_num BE8 | pc `GenesisInfo{ticker Bytes, name Bytes, mint_vault_scripthash Option<[20]>, url Bytes, hash Option<[32]>, data Option<Bytes>, auth_pubkey Option<Bytes>, decimals u8}` | |
| `token_tx` | tx_num BE8 | pc `DbTokenTx{token_tx_nums Vec<u64>, group_token_indices BTreeMap<u32,u32>, inputs Vec<DbToken>, outputs Vec<DbToken>, flags u8}` | `DbToken` 0 NoToken, 1 Atoms(u32,u64), 2 MintBaton(u32), 3 UnknownSlp(u8), 4 UnknownAlp(u8); flag bit 1 = has mint vault |
| `plugin_*` (5 tables) | — | — | opened, never written by native; non-empty → refuse (§4.4) |

**Groups (`<g>`) and member encodings:**
- `script` (Value): `compress_script_variant`, i.e. Core `ScriptCompression`. P2PKH `00‖h20`; P2SH `01‖h20`; P2PK compressed = 33-byte key; uncompressed `04|(y&1) ‖ x32`; other = `VARINT(len+6) ‖ script`.
- `token_id` (Output): token_id **rev** 32.
- `lokad_id` (history only): 4 raw bytes.
- `v2_branch` and `v2_asset` (Value, V2 tier only): raw native 32 bytes.

**The `kTables` array:** a constexpr array of the 31 Rust names, in the order listed in `chronik-db` `db.rs`. The V2 names (`v2_branch_*`, `v2_asset_*`) are always opened, even on the eCash tier. Rust's eCash-tier build creates them too, because they come from the same `db.rs` CF list in this stack. This keeps the env identical across tiers.

**TxNum / page bookkeeping:**
- `next_tx_num` = last `tx` key + 1.
- A block's tx range is `[first_tx_by_blk[h], first_tx_by_blk[h+1])`, or up to `next_tx_num` for the tip.

**Hashing:** `seahash` is ported bit-exactly from the Rust crate (`seahash::hash`, default keys) into `codec/seahash.cpp`. Golden vectors are taken from Rust (§8.1).

### 4.6 V2 native environment (V2 tier)

This is a separate env at `<datadir_net>/indexes/chronik/v2_index`, reproduced byte-for-byte from `chronik-db/src/mdbx.rs` + `v2_branch.rs` / `v2_explorer.rs` / `v2_asset.rs`:
- **Env:** `MAX_DB 32`, 256 readers. Geometry: upper 16 GiB, growth 16 MiB, shrink 64 MiB, pagesize 4 KiB. Flags `NOSTICKYTHREADS|LIFORECLAIM` with durable sync; mode 0644.
- **16 DBIs:** `meta`, `block_receipts`, `undo`, `tx_locations`, `outputs`, `postings` (DUPSORT|DUPFIXED 36), `explorer_height/block/block_tx/tx/txhash/input/witness`, `asset_summary/event/output`. Key prefixes and postcard records are as inventoried in the Rust source. `explorer_block_tx` stores `txid‖txhash` (64 B), which is what the code writes; the comment in `mdbx.rs` is wrong.
- **Binding:** `SCHEMA_VERSION=3`. `v2-binding` = `pc((3u32, Binding{chain_id,genesis,profile}))`. A mismatch refuses to open.
- **Flat files:** `v2_tx_NNNNN.dat` segments, 2 GiB rotation. pwrite + fdatasync before the MDBX commit; truncated on disconnect.
- **Per-block limits:** 4096 txs, 65,536 changes, 32 MiB.
- **Postcard size caps:** Record 1200 B, explorer 16 KiB, asset 512 B, batch 32 MiB.

This is `KvStore`-backed through the same `MdbxStore` class, configured with a second `EnvOptions` profile. The flat-file writer is `ext/lotus_v2/flat_files.cpp`.

---

## 5. Token and protocol indexing (problem 4)

### 5.1 Placement

| Protocol | Placement | Enabled when |
|---|---|---|
| SLP (Fungible, MintVault, NFT1 Group/Child) and ALP (EMPP `SLP2` Standard), plus burn summary | **core** `chronik/native/core/token/`, a port of `bitcoinsuite-slp` (parse, color, verify, burn_summary, empp, lokad_id) and `chronik-db/io/token` | `HostCapabilities::slp_alp_tokens && -chroniktokenindex` (default 1 where capable) |
| LOKAD-ID group | core group | `-chroniklokadidindex` (default 1) |
| Script group + scripthash | core group | always / `-chronikscripthashindex` |
| TxId subscription "group" (WS only) | core (`subs`) | always |
| CashTokens | **BCHN extension** (`hosts/bchn/`). Initial: none beyond wrapped-script bytes in `TxOutput::script`, as the current BCHN Rust adapter does. Future semantic index → open question Q2. | BCHN only |
| Lotus V2 branches/assets (`v2_branch_*`, `v2_asset_*` groups in the legacy env) | **V2 extension** `ext/lotus_v2/groups.cpp` | V2 tier |
| Lotus V2 native service (`v2_index`, `/v2/*`, `/v2/explorer/v1/*`) | **V2 extension** `ext/lotus_v2/service*.cpp` | V2 tier |
| Python plugins | **not ported** (`BUILD_CHRONIK_PLUGINS=ON` with `native` is a CMake FATAL_ERROR). `/plugin/*` routes return Rust's plugins-disabled error. Proto `plugins` maps stay empty. | never |

Doged runs SLP/ALP exactly as its Rust fork does (capability on). Core runs with the token index forced off, as its Rust adapter does.

### 5.2 Determinism requirement

The SLP/ALP port must reproduce Rust behaviour exactly, including the error strings in `TokenFailedParsing` and `TokenFailedColoring`, burn summaries, and `is_invalid`, because those strings are on the wire.

Port order inside one block is the Rust order: topological batch sort (`io/token/batch.rs`). It includes the early-skip when `token_meta` is empty and the block has no GENESIS.

### 5.3 Extension interface — `chronik/native/include/chronik/native/extension.h`

```cpp
#pragma once
#include <chronik/native/types.h>
#include <chronik/native/store.h>

namespace chronik::native {

struct IndexTx { const Tx *tx; uint64_t tx_num; bool is_coinbase; std::span<const uint64_t> input_nums; };
struct MemberItem { uint32_t idx; Bytes member; };   // idx: input or output index

enum class UtxoData { None, Value /*sats LE, dupfixed 20*/, Output /*pc(i64,Bytes)*/ };

/** A history(+utxo) group. Tables: <name>_history, <name>_history_num_txs, [<name>_utxo]. */
class GroupDef {
public:
    virtual ~GroupDef() = default;
    virtual std::string_view Name() const = 0;
    virtual UtxoData Utxos() const = 0;
    virtual void InputMembers(const IndexTx &, std::vector<MemberItem> &out) const = 0;
    virtual void OutputMembers(const IndexTx &, std::vector<MemberItem> &out) const = 0;
};

class Router;   // §6
class SubscriptionHub;

/** Host/tier-supplied indexing extension (V2, future CashTokens). */
class Extension {
public:
    virtual ~Extension() = default;
    virtual std::vector<const GroupDef *> Groups() const { return {}; }
    // Called with the same Block as the core, AFTER the core's txn commits (separate env)
    // or inside it (same env) — the extension declares which:
    enum class Txn { SameEnv, OwnEnv };
    virtual Txn TxnMode() const = 0;
    virtual void Open(const std::filesystem::path &index_dir, bool wipe) {}
    virtual void Resync() {}       // after core resync (V2: checkpoint pop + replay)
    virtual void Connect(const Block &, WriteTxn *same_env_txn) = 0;
    virtual void Disconnect(const Block &, WriteTxn *same_env_txn) = 0;
    virtual void RegisterRoutes(Router &) {}
    virtual void RegisterWsScriptTypes(SubscriptionHub &) {} // e.g. "v2-branch","taproot","v2-asset"
    virtual void Close() {}
};

} // namespace chronik::native
```

The V2 groups use `SameEnv`. The V2 native service uses `OwnEnv`; its errors are logged and do not abort, which keeps Rust semantics (`bridge.rs:561-575`).

---

## 6. HTTP and WebSocket

### 6.1 Router — `chronik/native/include/chronik/native/http.h`

```cpp
#pragma once
#include <functional>
#include <map>
#include <string>
#include <chronik/native/types.h>

namespace chronik::native {

struct HttpRequest {
    std::string method;                         // GET POST OPTIONS
    std::string path;                           // without /chronik prefix, without query
    std::multimap<std::string, std::string> query;
    std::string content_type;
    Bytes body;                                 // <= 2,000,000 B (MAX_REQUEST_BODY_SIZE) else 413
    std::string peer_ip;                        // real client (in-process) or socket peer
};
struct HttpResponse {
    int status = 200;
    std::string content_type = "application/x-protobuf";
    std::vector<std::pair<std::string, std::string>> headers; // CORS, Allow, cache-control
    Bytes body;
};

/** Transport-neutral. Handle() may block: transports MUST call it on the QueryPool. */
class Router {
public:
    using Handler = std::function<HttpResponse(const HttpRequest &, const std::vector<std::string> &params)>;
    void Add(std::string method, std::string pattern, Handler);  // "/script/:type/:payload/utxos"
    HttpResponse Handle(const HttpRequest &) const;              // 404 "Not found" fallback
};

class WsSession {                    // implemented by the transport
public:
    virtual ~WsSession() = default;
    virtual void SendBinary(Bytes) = 0;     // non-blocking enqueue
    virtual void Close() = 0;
    virtual const std::string &PeerIp() const = 0;
};
class WsHandler {                    // implemented by the core, one per session
public:
    virtual ~WsHandler() = default;
    virtual void OnBinary(std::span<const uint8_t>) = 0;  // pb::WsSub
    virtual void OnText() = 0;                            // -> WsMsg.error
    virtual void OnClosed() = 0;
};
using WsAccept = std::function<std::unique_ptr<WsHandler>(std::shared_ptr<WsSession>)>;

} // namespace chronik::native
```

### 6.2 Routes and semantics (port 1:1 from `chronik-http/src/server.rs:183-311`, `handlers.rs`, `protobuf.rs`, `error.rs`)

**Routes:**
- **Info and blocks:** GET `/blockchain-info`, `/chronik-info` (version = `Host::FormatFullVersion()`), `/block/:h`, `/block-header/:h?checkpoint_height`, `/block-txs/:h?page&page_size`, `/blocks/:s/:e`, `/block-headers/:s/:e?checkpoint_height`.
- **Transactions:** GET `/unconfirmed-txs`, `/tx/:txid`, `/token/:txid`, `/raw-tx/:txid`.
- **POST (+OPTIONS):** `/validate-tx`, `/broadcast-tx`, `/broadcast-txs`, `/script/batch/utxos` (≤500), `/script/batch/summary`.
- **Groups:** GET `/script/:type/:payload/{history,confirmed-txs,unconfirmed-txs,utxos}`, `/token-id/:id/{…,utxos}`, `/lokad-id/:id/{history,confirmed-txs,unconfirmed-txs}`.
- **Plugins:** `/plugin/...` returns the disabled-plugins error.
- **Pause:** `/pause` and `/resume` return 403 unless `-chronikallowpause` is set and the chain is not mainnet.
- **WebSocket:** `/ws`.

**Request and response rules:**
- **Errors:** body `pb::Error{msg}`. The status is parsed from the `"NNN: "` prefix, so the core's internal errors are typed `ChronikError{int status; std::string msg}`. Unprefixed errors become 500 "Unknown error, contact admins". 5xx responses are logged.
- **POST bodies:** Content-Type must be `application/x-protobuf`, otherwise 400.
- **OPTIONS:** returns `Allow: OPTIONS, HEAD, POST`.
- **CORS:** `-chronikcors` adds `Access-Control-Allow-Origin: *` and allows any method/headers, matching tower-http `CorsLayer::permissive` output. The exact header set comes from capturing the Rust responses in §8.3.
- **Paging:** page_size default 25, allowed range 1..200 (`MIN/MAX_HISTORY_PAGE_SIZE`). History ordering is the Rust order: confirmed newest first in `/history`, mempool by `(time_first_seen, txid)`.

**Broadcast:**
1. Optional token checks: `DecodeRawTx`, `LookupSpentCoins`, then SLP/ALP. Any burn or parse failure rejects the whole batch with 400.
2. For each tx: `Host::Broadcast(raw, CalcMaxFee(len))`. On failure: `UncacheCoins` and `400: Broadcast failed: …`.
3. Release the snapshot, then `Host::SyncWithIndexer()`.
4. Optionally wait for finalization via a hub subscription: up to 120 s, timeout → 504.

**`/validate-tx`:** never touches the mempool.

### 6.3 WebSocket (port of `ws.rs`)

**Framing:**
- Client → server: binary `pb::WsSub` with sub types blocks(2), txs(8), script(3), token_id(4), lokad_id(5), plugin(6) (error), txid(7).
- Text frames get an error reply.
- Maximum message/frame size 20,000 B.
- Pong is sent in reply to Ping. The server sends a Ping with payload `"Bitcoin ABC Chronik Indexer"` after 45 s idle (5 s on regtest), and the timer resets on every loop.

**Server messages:**
- `WsMsg{error|block|tx}`. `MsgBlock.coinbase_data` is set only on DISCONNECTED and INVALIDATED.
- Consecutive identical messages are suppressed per session.

**Subscription limits:**
- `-chronikmaxsubs` (10M), `-chronikmaxsubsperip` (75k), `-chroniksubsmaxscriptsize` (201); exceeding them returns a `503:` error message.
- Duplicate subscriptions are ignored. Unsubscribing releases the slot.

**Fan-out (exact Rust semantics):**
- Each subscription has a ring buffer: blocks 16, txs 32, per-group 16.
- Overflow drops the **oldest** message silently. This equals tokio broadcast `Lagged` being ignored.
- The hub publishes after the writer's commit, outside `state_`.

**Event ordering per tx:** ADDED, then REMOVED or CONFIRMED, then FINALIZED; the same sequence as Rust (verified by `chronik_ws_ordering.py`).

### 6.4 Transports — `chronik/native/transport/`

1. **`beast_listener.{h,cpp}`** (all hosts):
   - Standalone listener on each `-chronikbind`. Default `127.0.0.1` and `::1`, on `HostCapabilities::default_http_port`.
   - Boost.Beast HTTP/1.1 with keep-alive and WebSocket on `/ws`.
   - Its own `io_context` with 2 threads.
   - Each request is posted to `QueryPool`.
   - No TLS and no zstd, matching axum today.
2. **`host_beast_bridge.{h,cpp}`** (eCash/Lotus host only):
   - When `CHRONIK_IMPLEMENTATION=native`, `src/httpserver.cpp` stops proxying.
   - It registers an in-process async handler for `/chronik` (strip prefix, call `Router` via the pool, `co_await` completion) and routes `/chronik/ws` upgrades to `WsAccept` through a small hook `SetChronikInProcessHandlers(...)`. That hook replaces `ProxyChronikHTTP`/`ProxyChronikWebSocket` when set.
   - Existing httpserver behaviour stays: public-prefix rules, `-rpcallowip` gating, zstd response compression, the 256 MiB cap.
   - `peer_ip` is the real client address, which fixes the per-IP limit defect (§1).

Interrupt order is the same as Rust: `chronik::Interrupt()` stops both transports and makes the router answer 503 before `StopHTTPServer` and before node subsystems tear down. `Stop()` comes after the validation queue is flushed.

---

## 7. Per-host adapter notes

### 7.1 ABC / eCash tier (`hosts/abc/`)
- **Source:** port `chronik-cpp/chronik_bridge.cpp` bridge logic (block/tx conversion, offsets, fee functions) and the 060 worker (`chronik_validationinterface.cpp`). The worker keeps `src/util/bounded_task_queue.h` and its fail-closed overflow → `StartShutdown()`.
- **Mempool entry time:** `TransactionAddedToMempool` with `entry_time`. If it is 0, fall back to `mempool->info(txid).m_time` on the signals thread (same as now).
- **ASSUMEDVALID:** skip such events.
- **Args:** reuse `init.cpp` registration unchanged. Electrum args → `InitError("Electrum is not supported by the native Chronik implementation")`.

### 7.2 Lotus V2 tier (`hosts/abc/` patched in place, plus `ext/lotus_v2/`)
- **Headers and outputs:** 134-byte headers. Output scripts become the synthetic native frame that `BridgeTxOutputScript` builds (`chronik_bridge.cpp:44-93`): `flags ‖ value LE8 ‖ token_id ‖ branches ‖ paths` when `scriptPubKey.size() ≤ 1 && vBranches` is set. It is kept byte-identical so `script_*` keys match Rust.
- **Input scripts:** `vCoinbaseData` or `vWitnesses[0].script` when `scriptSig` is empty.
- **Native block conversion:** reuse V2 C++ (`ToV2Transaction`, `EncodeTransaction`, `MakeChronikExplorerFacts`) from `chronik.cpp:258-462` to build `ext::lotus_v2::NativeBlock`. The service implements the existing `lotus::v2::ChronikSink` interface (`src/lotus_v2/chronik_sync.h`) as `NativeChronikSink`, which makes the dead `CxxChronikSink` path obsolete.
- **Spent-coin lookup:** must use the real V2 txid, not the legacy-shaped recompute (defect §1.2).
- **V2 resync:** pop checkpoints until one matches the active chain, then replay. Stop silently at the first error, then `publish_authority`.
- **Authority fence:** port the fence semantics (`invalidate/suspend/publish_authority_context/publish_authority`) exactly, so `/v2/*` returns 503 `index_unavailable` while it is fenced.
- **V2 routes:**
  - JSON `/v2/status`, `/v2/branches/{utxos,outputs}` (32 KiB body cap; 174-byte hex cursors; page 1–100), `/v2/utxos/:txid/:out_idx`.
  - Explorer under `/v2/explorer/v1/...` (18 routes, 256 KiB response cap, `cache-control: no-store`). Error bodies and status codes (400/404/409/413/416/503) are as in `chronik-http/src/v2*.rs`.
  - JSON is built with the host's UniValue, with key order as in Rust's serde output.
  - `start_v2_server` (separate listener) is unused in Rust and is **not** ported.

### 7.3 BCHN (`hosts/bchn/`, shared-source export)
- **APIs used:** `::NodeContext`, `::ChainActive()`, `::LookupBlockIndex`, `*pcoinsTip`, `g_mempool`, `ReadBlockFromDisk(..., Params().GetConsensus())`, `UndoReadFromDisk`, `CAutoFile(OpenBlockFile/OpenUndoFile, SER_DISK, CLIENT_VERSION)`.
- **Mempool events:** come only through the node-side hooks in `src/chronik/validation_hooks.h` (`HasMempoolObserver`, `CaptureMempoolAdmission`, `CaptureMempoolRemovals`).
- **Conflicts:** conflicts in `BlockConnected` are emitted as removals first, `DescendantsFirst()`.
- **Registration:** global `RegisterValidationInterface`.
- **Storage:** the LevelDB backend is available (`CHRONIK_NATIVE_LEVELDB=ON`) using BCHN's vendored leveldb. Default stays MDBX.
- **Configuration:** ports 8331/18331/18440. Log category `BCLog::CHRONIK`.
- **Broadcast:** `AcceptToMemoryPool(...)` + `PushInventory`. `CalcMaxFee` uses `(COIN/10)/SATOSHI` per kB.
- **Transport:** standalone Beast listener only (BCHN has no Beast server).

### 7.4 Dogecoin (`hosts/doged/`)
- **Base:** the ABC adapter, plus:
  - `RawHeader = ser(index.GetBlockHeader(blockman))`, variable length.
  - First-tx offset from `GetSerializeSize(block.GetBlockHeader())`.
  - `int32` version proto.
- **Headers-only AuxPoW indexes** (0174 gap): `RawHeader` throws "block body unavailable", which the core turns into a 404 for that header. Chronik never needs headers of blocks without bodies, because it only indexes connected blocks.
- **Avalanche:** capability on, but events only arrive if `-avalanche` is on (0086 default off).
- **Ports:** 22554 (0117).

### 7.5 Bitcoin Core (`hosts/bitcoin-core/`)
- **Txids and witness:** stripped txid. `Tx::raw = TX_WITH_WITNESS` bytes, and `wire_size` = witness size. Offsets advance by witness size. `/raw-tx` returns witness bytes. Broadcast parses `TX_WITH_WITNESS` and rejects trailing bytes.
- **Storage:** XOR-aware `ReadIndexedTransaction(Undo)` through `BlockManager`; never raw `FILE`.
- **Chainstate roles:** `ValidatedChainstate()` everywhere. Refuse background assumeutxo and `loadtxoutset`.
- **Mempool:** `NewMempoolTransactionInfo{spent_coins, acceptance_time}` (node patch); missing spent coins → shutdown request.
- **Durability:** `MakeIndexedBlockDurable` before indexing each block.
- **Registration:** `RegisterSharedValidationInterface`.
- **Capabilities:** token index forced off; no avalanche.
- **Build:** links into `bitcoin_node PRIVATE`.
- **Witness codec:** the existing Rust witness-codec overlay is unnecessary, because the host computes txids and raw bytes.

---

## 8. Test plan and acceptance criteria (problem 5)

### 8.1 Unit tests (`chronik/native/test/`, target `test_chronik_native`; links the core only, plus a `FakeHost`)
1. **Codecs:**
   - postcard (varint/zigzag edge values, Option, enum, BTreeMap, `pc*` lists);
   - seahash;
   - script compression;
   - every value struct in §4.5.

   Golden bytes come from a **test-only Rust exporter**: a new `chronik/chronik-db/tests/export_native_golden.rs` writes JSON fixtures to `chronik/native/test/fixtures/`. The fixtures are committed. *Acceptance:* every fixture round-trips byte-exactly.
2. **Store conformance:** one suite, run against `MdbxStore` and `LevelDbStore`: ordering, `SeekLe`, dup semantics, read-your-writes, snapshot isolation under a concurrent writer, `Clear`, the >7500-byte key path (MDBX).
3. **SLP/ALP:** translate all Rust tests in `bitcoinsuite-slp/tests/*.rs` (29 files) and `chronik-db/src/io/token/tests/*.rs` (8 files) to table-driven C++ cases. *Acceptance:* case count ≥ Rust `#[test]` count for those files, with all passing.
4. **Indexer properties:** a random chain generator with spends, tokens, LOKAD and reorgs (depth ≤ 6). Property: `dump(connect(B); disconnect(B)) == dump(before)` for every table. Resync tests cover tip ahead, behind and forked.
5. **Mempool:** add, remove, conflict and confirm sequences. The mempool view equals what the DB+mempool union would give.
6. **Concurrency:** TSan run; the writer at full rate with 16 query threads; every response is self-consistent (UTXO set ∩ mempool-spent = ∅).
7. **Adapter tests in `test_bitcoin`:** port `chronik/test/bridgeprimitives_tests.cpp` and `chronikbridge_tests.cpp` expectations (block/tx offsets, coin conversion, V2 synthetic scripts) against the ABC adapter.

### 8.2 Functional tests
- **Config:** `test/config.ini.cmake.in` gains `ENABLE_CHRONIK_NATIVE` and `ENABLE_CHRONIK_ELECTRUM` (= rust implementation).
- **Framework:** `test_framework.py` gains `skip_if_no_chronik_electrum()`, used by the two Electrum tests. Plugins tests already skip, because `ENABLE_CHRONIK_PLUGINS` is OFF.
- **Acceptance (eCash tier):** with `-DCHRONIK_IMPLEMENTATION=native`, all **45** remaining `chronik_*.py` pass unmodified except for these gating lines. This includes `chronik_rpc_port_proxy.py` (in-process now; same external behaviour), `chronik_ws_ordering.py`, `chronik_resync.py` and `chronik_shutdown.py`.
- **Acceptance (V2 tier):** the same set, with V2 fixtures from v2/034 and v2/035.

### 8.3 Parity against Rust (the proof)

The tool is `contrib/chronik-parity/` (Python), plus `chronik-native-dump` (C++ tool in `chronik/native/tools/`).

**Dump format:** `chronik-native-dump` prints every table as `table\tkey_hex\tvalue_hex`, sorted, with dup values expanded. It reads any v13 MDBX env, including Rust-built ones.

**Steps:**
1. **Deterministic chain run.** `parity_chain.py` builds two nodes from two build trees (rust, native) with `-mocktime`. It feeds an identical block/tx stream: a fixture chain of 400 blocks covering P2PKH/P2SH/P2PK/other scripts, OP_RETURN LOKAD, every SLP/ALP type including invalid/burn cases, mempool conflicts, three reorgs, and `invalidateblock`/`reconsiderblock`.
   - *Acceptance:* the dumps are identical at every 50 blocks and at the end.
2. **HTTP corpus.**
   - Requests: every route, for every block, tx, script, token and LOKAD seen in the run; pagination edges (page 0, last page, size 1/200/201); malformed params; bad content types; oversized bodies; the 500-script batch limit; `/validate-tx` and `/broadcast-tx` (on cloned nodes).
   - *Acceptance:* identical status and content-type for 100% of requests. Parsed protobuf equality for 100%; byte equality expected for 100%, with any byte-only difference listed and justified. Error `msg` strings are identical.
   - Known accepted differences are only the §1 defects (V2 spent-coin txid; per-IP key) and `ChronikInfo.version`, which is the same function anyway.
3. **WebSocket corpus.** Scripted subscriptions to all sub types across the run.
   - *Acceptance:* identical message sequences per session (no lag; ring capacities not exceeded).
4. **Cross-open.**
   - Rust-built DB → native continues 100 blocks → Rust reopens and continues → dumps equal a single-implementation run.
   - Also run with `NATIVE_LAST_WRITER` present.
5. **Mainnet-scale replay** (eCash tier on eCash mainnet; V2 tier on the V2 devnet chain):
   - Use isolated datadirs with APFS-cloned blk/rev files and their own ports (the existing isolation practice).
   - *Acceptance:* dump-equality spot checks at 10 heights. HTTP corpus sampled at 10,000 random txs and 1,000 scripts with no difference.
   - *Performance:* full index throughput ≥ 0.9× Rust on the same host; p50 and p99 latency for `/tx`, `/script/.../utxos` (10k-UTXO script) and `/block-txs` ≤ 1.2× Rust; peak RSS ≤ Rust.

### 8.4 Build acceptance
- `-DBUILD_CHRONIK=ON -DCHRONIK_IMPLEMENTATION=native` configures and builds with **no `cargo`/`rustc` on PATH**.
- `-DCHRONIK_IMPLEMENTATION=rust` is unchanged: all `check-crates` and the 50 tests behave as before.
- Each build passes the other's absence check: a native build contains no `chronik_lib` symbols; a rust build contains no `chronik::native` symbols.

---

## 9. File layout

```
chronik/native/
  CMakeLists.txt                       # targets: chronik_native_core, chronik_native_host_<h>, tools, tests
  include/chronik/native/{types,host,store,indexer,extension,http,query}.h
  core/codec/{postcard.h,postcard.cpp,seahash.cpp,script_compress.cpp,hex.cpp}
  core/db/{schema.h,schema.cpp,mdbx_store.cpp,leveldb_store.cpp,metadata.cpp}
  core/index/{blocks,txs,block_stats,reverse_lookup,spent_by,group_history,group_utxos,tx_num_cache}.cpp
  core/groups/{script,lokad_id,token_id}.cpp
  core/token/{slp_parse,alp_parse,empp,color,verify,burn_summary,token_batch,token_io}.cpp
  core/mem/{mempool,mem_group_history,mem_group_utxos,mem_spent_by,mem_tokens}.cpp
  core/indexer/{indexer,resync,avalanche,merkle,pause,snapshot}.cpp
  core/query/{blocks,txs,group_history,group_utxos,tx_token_data,broadcast,batch}.cpp
  core/http/{router,handlers,protobuf_io,errors}.cpp
  core/ws/{hub,ws_handler,limits}.cpp
  transport/{query_pool,beast_listener,host_beast_bridge}.cpp
  hosts/abc/{abc_host,abc_subscriber,abc_entry,abc_args}.cpp   # eCash tier
  ext/lotus_v2/{groups,native_block,service,flat_files,explorer,assets,http_v2,http_explorer}.cpp  # V2 tier
  tools/chronik_native_dump.cpp
  test/{*.cpp,fixtures/*.json}
contrib/chronik-parity/{parity_chain.py,corpus.py,compare.py,README.md}
```

`chronik.proto` is shared from `chronik/chronik-proto/proto/` and compiled with `protobuf_generate` (Qt's `find_package(Protobuf CONFIG)` fallback pattern). BCHN, Core and Doged hosts receive `chronik/native/` plus `chronik-proto/proto/` and the vendored libmdbx through the existing shared-source export (`daemon/scripts/export-chronik.py`, `ChronikProvider.cmake`). The export gains a `native` profile that ships no Rust files. Host-specific directories ship only to their host.

---

## 10. Patch-by-patch commit plan

Numbers are positions to append. eCash tier: after `ecash/101`. V2 tier: after `v2/057`. Each patch builds and passes its tests with `CHRONIK_IMPLEMENTATION=native`, and leaves the `rust` build unchanged.

### eCash tier

| # | Subject | Files |
|---|---|---|
| 102 | `build(chronik): add CHRONIK_IMPLEMENTATION={rust,native} and native skeleton` | `CMakeLists.txt` (Rust/Corrosion only when `rust`), `chronik/CMakeLists.txt` (dispatch), `chronik/native/CMakeLists.txt`, `src/config/CMakeLists.txt`/`bitcoin-config.h.cmake.in` (`ENABLE_CHRONIK_NATIVE`), `test/config.ini.cmake.in`, `chronik/native/include/chronik/native/types.h` |
| 103 | `chronik(native): postcard, seahash and script-compression codecs with Rust golden fixtures` | `core/codec/*`, `chronik/chronik-db/tests/export_native_golden.rs` (test-only), `test/codec_tests.cpp`, `test/fixtures/codec.json` |
| 104 | `chronik(native): KvStore interface and MDBX backend matching the Rust environment` | `include/.../store.h`, `core/db/mdbx_store.cpp`, `core/db/schema.{h,cpp}`, `test/store_tests.cpp` |
| 105 | `chronik(native): metadata, schema verification and legacy-artifact refusal` | `core/db/metadata.cpp`, `test/metadata_tests.cpp` |
| 106 | `chronik(native): block, tx, block-stats, reverse-lookup and spent-by tables` | `core/index/{blocks,txs,block_stats,reverse_lookup,spent_by,tx_num_cache}.cpp`, tests, fixtures |
| 107 | `chronik(native): group history/UTXO engine with script and LOKAD-ID groups` | `include/.../extension.h`, `core/index/group_*.cpp`, `core/groups/{script,lokad_id}.cpp`, tests |
| 108 | `chronik(native): SLP and ALP parsing, coloring, verification and token tables` | `core/token/*`, `core/groups/token_id.cpp`, `test/token_*_tests.cpp` (translated Rust cases) |
| 109 | `chronik(native): in-memory mempool index` | `core/mem/*`, tests |
| 110 | `chronik(native): indexer, resync, avalanche, merkle checkpoints and pause` | `include/.../{host,indexer}.h`, `core/indexer/*`, `test/indexer_property_tests.cpp`, `test/fake_host.{h,cpp}` |
| 111 | `chronik(native): query layer and protobuf HTTP router` | `include/.../{http,query}.h`, `core/query/*`, `core/http/*`, protobuf codegen in `chronik/native/CMakeLists.txt`, tests |
| 112 | `chronik(native): WebSocket hub, limits and subscriptions` | `core/ws/*`, tests |
| 113 | `chronik(native): query pool and standalone Beast listener` | `transport/{query_pool,beast_listener}.cpp`, tests |
| 114 | `chronik(native): ABC host adapter, worker subscriber and in-process /chronik on the Beast server` | `hosts/abc/*`, `transport/host_beast_bridge.cpp`, `src/httpserver.{h,cpp}` (`SetChronikInProcessHandlers`; the proxy stays for `rust`), `src/test/chronik_native_abc_tests.cpp`, `src/CMakeLists.txt` (link) |
| 115 | `test(chronik): gate Electrum tests and add native parity tooling` | `test/functional/test_framework/test_framework.py`, `chronik_electrum_{basic,blockchain}.py`, `contrib/chronik-parity/*`, `tools/chronik_native_dump.cpp` |
| 116 | `chronik(native): optional LevelDB backend` | `core/db/leveldb_store.cpp`, `chronik/native/CMakeLists.txt` (`CHRONIK_NATIVE_LEVELDB`), `test/store_tests.cpp` (parametrised) |

### V2 tier

| # | Subject | Files |
|---|---|---|
| 058 | `chronik(native,v2): adapt ABC host adapter to 134-byte headers, native outputs and V2 identities` | `hosts/abc/abc_host.cpp`, `src/test/chronik_native_abc_tests.cpp` (V2 expectations from v2/035) |
| 059 | `chronik(native,v2): V2 branch and asset groups` | `ext/lotus_v2/groups.cpp`, tests, golden fixtures for `v2_*` tables |
| 060 | `chronik(native,v2): native V2 service env, flat files, explorer and asset indexes` | `ext/lotus_v2/{service,flat_files,explorer,assets,native_block}.cpp`, `src/lotus_v2/chronik_sync.{h,cpp}` (`NativeChronikSink`), tests ported from `v2_branch.rs`/`v2_asset_test.rs`/`v2_explorer_model_tests.rs` |
| 061 | `chronik(native,v2): /v2 and /v2/explorer/v1 JSON routes and v2 WebSocket script types` | `ext/lotus_v2/{http_v2,http_explorer}.cpp`, tests ported from `v2_explorer_http_tests.rs` and `v2tests/*` |
| 062 | `test(chronik,v2): native parity corpus for V2 routes and envs` | `contrib/chronik-parity/*` (V2 corpus), dump tool (`v2_index` support) |

### Out-of-tree host series (shared Chronik export; not eCash/V2 tiers)
- `daemon/chronik/hosts/{bchn,bitcoin-core}/native/0001-...patch`: adapter directory and node hooks. The node hooks reuse the existing node mailbox patches for spent coins, durability and hooks.
- `daemon/patches/doged/0175-...`: Doged adapter.

These are separate reviews, after eCash 115 passes.

---

## 11. Risks

| Risk | Mitigation |
|---|---|
| SLP/ALP port diverges (wire-visible token status and errors) | Translated Rust tests; token-heavy parity fixture chain; mainnet sample corpus |
| Postcard or seahash subtle mismatch corrupts a shared DB | Golden fixtures before any writer lands (103); cross-open test; `NATIVE_LAST_WRITER` diagnostics; dump diff on every parity run |
| libprotobuf/abseil in depends and cross builds (only Qt used it so far) | Use Qt's proven `find_package(Protobuf CONFIG)` pattern. CI cross-builds native before 114 lands. Keep `protobuf-lite` runtime only (`option optimize_for = LITE_RUNTIME` via a generated copy if needed) |
| Blocking work on io threads stalls the node HTTP server | All handlers run on `QueryPool`. Lint rule: transports only call `Router::Handle` via the pool |
| Long reader snapshots inflate MDBX (MVCC retention) | Snapshot is held only per request; history/utxo queries are bounded by paging; batch ≤500 |
| Writer overflow (060 bound) caused by contention | The writer never waits on readers except the brief exclusive section. The queue bound is unchanged |
| Upstream BCHN/Core reviewers object to Beast or MDBX | LevelDB backend exists. Transport is isolated (Q4) |
| Rust behaviour defects get "fixed" silently | §1 list is the only accepted divergence; everything else must match |

---

## 12. Open questions (few)

1. **Q1 Default switch.** When should `CHRONIK_IMPLEMENTATION` default flip to `native`, and when is the Rust tree deleted? Proposal: flip after §8.3 step 5 passes on both tiers; deletion is the user's later decision.
2. **Q2 CashTokens semantics on BCHN.** Should native add a CashTokens category/NFT index? That requires new `chronik.proto` fields, so it cannot be wire-identical to existing clients.
3. **Q3 V2 tier SLP/ALP.** Should SLP/ALP stay enabled on Lotus V2 (Rust currently runs it on V2 synthetic scripts), or be capability-off there?
4. **Q4 BCHN transport.** Is the standalone Beast listener acceptable for BCHN upstreaming, or is a libevent-HTTP + external-WS transport required? This affects only `transport/`, not the core.


## Decisions (user, 2026-10-19) — answer section 12

1. Switch the `CHRONIK_IMPLEMENTATION` default to `native` once the parity
   tests pass on both tiers. Deleting the Rust tree is a later user decision.
2. Yes: BCHN gets a CashTokens category/NFT index, as a BCHN extension with
   new additive `chronik.proto` fields (existing clients unaffected). After
   core parity.
3. No: SLP/ALP indexing is off in the V2 tier (capability off); on in eCash.
4. Yes: the standalone Beast listener is fine for BCHN.
