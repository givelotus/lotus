# Lotus V1 `libmdbx` Storage Backend Benchmark Report

## 1. Executive Summary

We built and benchmarked an experimental **`libmdbx` (`v0.13.11`)** storage backend in Lotus V1 (`lotus-v1-latest`, base commit `6590d92300` -> experimental commit `8019da4702` on branch `v1-libmdbx-experiment`), replacing **both**:
1. **LevelDB** in `CDBWrapper` ([src/dbwrapper.h](file:///private/tmp/lotus-v1-libmdbx-wt/src/dbwrapper.h) / [src/dbwrapper.cpp](file:///private/tmp/lotus-v1-libmdbx-wt/src/dbwrapper.cpp)), backing `chainstate/` (`CCoinsViewDB`), `blocks/index/` (`CBlockTreeDB`), and `indexes/txindex/`.
2. **RocksDB** in `chronik-db` ([chronik/chronik-db/src/db.rs](file:///private/tmp/lotus-v1-libmdbx-wt/chronik/chronik-db/src/db.rs), [chronik/chronik-db/src/group.rs](file:///private/tmp/lotus-v1-libmdbx-wt/chronik/chronik-db/src/group.rs), [chronik/chronik-db/src/io/group_utxos.rs](file:///private/tmp/lotus-v1-libmdbx-wt/chronik/chronik-db/src/io/group_utxos.rs)), backing all 22 Chronik column families under `indexes/chronik/`.

### Key Highlights
- **End-to-End Block Connect (2,000 blocks, 16,433 txs, 52,246 outputs, `-chronik=1 -txindex=1`):** **`1.623s` (`1,232.0 blk/s`, `10,122.5 tx/s`)** on `libmdbx` vs. **`1.921s` (`1,041.0 blk/s`, `8,553.5 tx/s`)** on Baseline (`LevelDB + RocksDB`) — **+18.4% faster block connection throughput** (`-15.5%` wall-clock time) with identical disk bytes written (`67.05 MiB` vs `67.00 MiB`).
- **High-UTXO Script Query Latency (`2,100` UTXOs on a single script):** **`208.6 µs` p50** (`229.1 µs` mean) on `libmdbx` with `MDBX_DUPSORT | MDBX_DUPFIXED` vs. **`462.6 µs` p50** (`514.3 µs` mean) on Baseline RocksDB — **2.22x faster (`-54.9%` p50 latency)**.
- **Standard Chronik HTTP Queries:**
  - `script_history`: **`739.9 µs` p50** on `libmdbx` vs. **`913.6 µs` p50** on Baseline (**+23.5% faster**).
  - `script_utxos`: **`220.1 µs` p50** on `libmdbx` vs. **`284.1 µs` p50** on Baseline (**+29.1% faster**).
  - `tx_lookup`: **`137.4 µs` p50** on `libmdbx` vs. **`194.0 µs` p50** on Baseline (**+41.2% faster**).
- **Reindex Throughput (`0 -> 2,000`):**
  - `-reindex-chainstate -chronikreindex`: **`1.301s` (`1,537.6 blk/s`)** on `libmdbx` vs. **`1.415s` (`1,413.5 blk/s`)** on Baseline (**+8.8% faster**).
  - Full `-reindex -chronikreindex`: **`1.971s` (`1,014.5 blk/s`)** on `libmdbx` vs. **`2.084s` (`959.5 blk/s`)** on Baseline (**+5.7% faster**).
- **C++ Microbenchmarks (`lotus-bench`):**
  - `DBWrapperRead`: **`247.43 ns/read` (`4.04M reads/s`)** on `libmdbx` vs. **`284.78 ns/read` (`3.51M reads/s`)** on LevelDB (**+15.1% faster**).
  - `DBWrapperIterator`: **`71.52 ns/entry` (`13.98M entries/s`)** on `libmdbx` vs. **`84.90 ns/entry` (`11.78M entries/s`)** on LevelDB (**+18.7% faster**).
  - `CCoinsCaching`: **`4,182.60 ns/op` (`239.1k ops/s`)** on `libmdbx` vs. **`4,406.71 ns/op` (`226.9k ops/s`)** on LevelDB (**+5.4% faster**).
- **100% Protocol & Consensus Equivalence:** All 2,400 Chronik HTTP protobuf responses across `script_history`, `script_utxos`, `high_utxo_script_utxos`, `tx`, `block`, `blocks`, `token`, and `token-id/utxos` produced identical SHA-256 digests (`5db451043a011264fcfb3dd3cb849178d321f83c1fdaccb61c2e3da4cc2886b1` and `0fd922b6259d3997985d45eb1d718535fda8432f1231b3ee07aec420050fee2c`).

---

## 2. Architecture & Implementation Details

### 2.1 Vendored `libmdbx` (`src/libmdbx/`) & Upstream v0.13.11 GC Fix
- Vendored amalgamated `libmdbx` `v0.13.11` into [src/libmdbx/mdbx.c](file:///private/tmp/lotus-v1-libmdbx-wt/src/libmdbx/mdbx.c) and [src/libmdbx/mdbx.h](file:///private/tmp/lotus-v1-libmdbx-wt/src/libmdbx/mdbx.h), compiled as static library target `mdbx` with `-O3 -DNDEBUG -std=gnu11` ([src/libmdbx/CMakeLists.txt](file:///private/tmp/lotus-v1-libmdbx-wt/src/libmdbx/CMakeLists.txt)).
- **Critical Upstream `libmdbx` v0.13.11 GC Reclamation Fix ([src/libmdbx/mdbx.c#L22757](file:///private/tmp/lotus-v1-libmdbx-wt/src/libmdbx/mdbx.c#L22757)):**
  - In `gc_alloc_ex`, `mdbx_env_open` initializes meta pages with steady transaction ID `INITIAL_TXNID` (`3`). When `gc_alloc_ex` searched for reclaimable retired pages, `oldest = txn_snapshot_oldest(txn)` returned `prefer_steady.txnid` (`3`), and line 22530 computed `const txnid_t detent = oldest + 1;` (`4`).
  - Line 22757 then checked `if (... && detent == prefer_steady.txnid)` (`4 == 3`, always false!), preventing `meta_wipe_steady` from ever clearing the initial steady marker in nosync modes when `autosync_threshold == 0`. As a result, retired B+Tree pages could never be reclaimed and `chronik/mdbx.dat` ballooned to `1.625 GiB`.
  - Fixing line 22757 to `oldest == prefer_steady.txnid` and extending line 22771 to `F_ISSET(env->flags, MDBX_SAFE_NOSYNC)` enabled immediate LIFO page recycling via `MDBX_LIFORECLAIM | MDBX_COALESCE`, keeping `chronik/mdbx.dat`, `txindex/mdbx.dat`, `chainstate/mdbx.dat`, and `blocks/index/mdbx.dat` at their initial **`16 MiB`** allocation across the entire 2,000-block benchmark!

### 2.2 Phase 1: `CDBWrapper` on `libmdbx` ([src/dbwrapper.h](file:///private/tmp/lotus-v1-libmdbx-wt/src/dbwrapper.h), [src/dbwrapper.cpp](file:///private/tmp/lotus-v1-libmdbx-wt/src/dbwrapper.cpp))
- **Dynamic Geometry & Flags:**
  - `size_lower = 1 MiB`, `size_now = 16 MiB` (`4 MiB` for `memory_only`), `size_upper = 256 GiB` (`4 GiB` for `memory_only`), `growth_step = 64 MiB`, `shrink_threshold = 128 MiB`, `pagesize = -1` (OS default 16 KiB on macOS arm64).
  - Opened with `MDBX_WRITEMAP | MDBX_SAFE_NOSYNC | MDBX_NOMETASYNC | MDBX_COALESCE | MDBX_LIFORECLAIM | MDBX_NOSTICKYTHREADS | MDBX_NOMEMINIT`.
- **Zero-Allocation Read Transaction & Cursor Pooling:**
  - `CDBWrapper` maintains a mutex-guarded pool of reset `MDBX_txn` and unbound `MDBX_cursor` handles (`AcquireReadTxn` / `ReleaseReadTxn`, `AcquireReadCursor` / `ReleaseReadCursor`), using `mdbx_txn_renew` / `mdbx_txn_reset` and `mdbx_cursor_bind` / `mdbx_cursor_unbind` so point reads (`Read`, `Exists`) and `CDBIterator` creation avoid per-call heap allocations and reader-slot contention while never holding read snapshots open across calls.

### 2.3 Phase 2: `chronik-db` on `libmdbx` ([chronik/chronik-db/src/db.rs](file:///private/tmp/lotus-v1-libmdbx-wt/chronik/chronik-db/src/db.rs), [chronik/chronik-db/src/io/group_utxos.rs](file:///private/tmp/lotus-v1-libmdbx-wt/chronik/chronik-db/src/io/group_utxos.rs))
- **Column Families -> Named Subdatabases (`MDBX_dbi`):**
  - All 22 Chronik column families (`blk`, `blk_stats`, `tx`, `script_history`, `script_utxo`, `token_id_utxo`, `spent_by`, etc.) map to named `MDBX_dbi` handles in a single `mdbx.dat` environment (`pagesize = 16384`, `max_dbs = 64`).
  - Keys $> 7,500$ bytes (e.g. oversized raw `ScriptVariant::Other` scripts) are transparently normalized with a domain-separated SHA-256 prefix (`MDBX_SHA256_KEY:<32-byte-sha256>`) so arbitrary scripts never trigger `MDBX_BAD_VALSIZE`.
- **Native `MDBX_DUPSORT | MDBX_DUPFIXED` for UTXO Column Families:**
  - Replaced the emulated RocksDB merge operator on `CF_SCRIPT_UTXO`, `CF_TOKEN_ID_UTXO`, and `CF_PLUGIN_GROUP_UTXOS` with native `libmdbx` sorted duplicate sub-trees:
    - `CF_SCRIPT_UTXO` (`UtxoDataValue = i64`) uses `MDBX_CREATE | MDBX_DUPSORT | MDBX_DUPFIXED` with a fixed **20-byte** value layout: `[tx_num_be (8B), out_idx_be (4B), sats_le (8B)]`.
    - `CF_TOKEN_ID_UTXO` and `CF_PLUGIN_GROUP_UTXOS` (`UtxoDataOutput = (i64, Bytes)`) use `MDBX_CREATE | MDBX_DUPSORT` with `[tx_num_be (8B), out_idx_be (4B), sats_le (8B), script...]`.
    - Because the first 12 bytes are big-endian `(tx_num, out_idx)`, `libmdbx`'s native bytewise duplicate comparator maintains Chronik's exact `(tx_num, out_idx)` ordering without deserializing, binary-searching, or rewriting existing UTXOs on insert/spend.
    - Adding a UTXO (`WriteBatch::put_dup_cf`) executes `mdbx_cursor_put(..., MDBX_UPSERT)` in $O(\log N)$ time; spending a UTXO (`WriteBatch::delete_dup_prefix_cf`) seeks via `mdbx_cursor_get(..., MDBX_GET_BOTH_RANGE)` on the 12-byte outpoint prefix and deletes the single duplicate via `mdbx_cursor_del(..., MDBX_CURRENT)` in $O(\log N)$ time (and cancels intra-batch create+spend pairs in memory before touching the B+Tree).

---

## 3. Benchmark Results

### 3.1 C++ Microbenchmarks (`lotus-bench -filter="DBWrapper.*|CCoins.*" -min_time=500`)

| Benchmark | Baseline (`LevelDB`) | `libmdbx` (Before 3 Opts) | `libmdbx` (After 3 Opts) | Speedup (`After 3 Opts` vs. `Baseline`) |
| :--- | ---: | ---: | ---: | ---: |
| `DBWrapperRead` | `284.78 ns/read` (`3,511,469 read/s`) | `259.53 ns/read` (`3,853,129 read/s`) | **`247.43 ns/read` (`4,041,570 read/s`)** | **+15.1% faster** |
| `DBWrapperIterator` | `84.90 ns/entry` (`11,779,251 entry/s`) | `70.33 ns/entry` (`14,218,526 entry/s`) | **`71.52 ns/entry` (`13,982,174 entry/s`)** | **+18.7% faster** |
| `CCoinsCaching` | `4,406.71 ns/op` (`226,927 op/s`) | `4,311.99 ns/op` (`231,911 op/s`) | **`4,182.60 ns/op` (`239,086 op/s`)** | **+5.4% faster** |
| `DBWrapperWriteBatch` | `577.70 ns/kv` (`1,730,992 kv/s`) | `922.34 ns/kv` (`1,084,193 kv/s`) | **`945.97 ns/kv` (`1,057,119 kv/s`)** | `-38.9%` (in-place B+Tree vs. LSM memtable append) |
| `CCoinsViewDBFlush` | `720.08 ns/coin` (`1,388,743 coin/s`) | `1,117.47 ns/coin` (`894,880 coin/s`) | **`1,096.20 ns/coin` (`912,245 coin/s`)** | `-34.3%` (`+1.9%` faster vs. before 3 opts) |

### 3.2 End-to-End 2,000-Block Regtest Workload ([contrib/bench_libmdbx_vs_baseline.py](file:///private/tmp/lotus-v1-libmdbx-wt/contrib/bench_libmdbx_vs_baseline.py))
- **Workload Parameters:** `2,000` blocks, `16,433` transactions, `16,433` inputs, `52,246` outputs across `400` P2SH/P2PKH scripts, `50` P2PK scripts, LOKAD IDs, and `380` ALP tokens (genesis + send churn), plus `P2SH_OP_TRUE` accumulating `2,100` unspent UTXOs (`4,000` outputs created and `1,900` inputs spent).

#### Block Connect & Reindex Performance

| Metric | Baseline (`LevelDB + RocksDB`) | `libmdbx` (Before 3 Opts) | `libmdbx` (After 3 Opts) | Improvement (`After 3 Opts` vs. `Baseline`) |
| :--- | ---: | ---: | ---: | ---: |
| **Connect 2,000 Blocks — Wall Time** | `1.921 s` | `1.582 s` | **`1.623 s`** | **-15.5% time (+18.4% blk/s)** |
| **Connect 2,000 Blocks — Throughput** | `1,041.0 blk/s` (`8,553.5 tx/s`) | `1,264.6 blk/s` (`10,390.6 tx/s`) | **`1,232.0 blk/s` (`10,122.5 tx/s`)** | **+18.4% throughput** |
| **Block Connect Latency p50** | `0.939 ms` | `0.754 ms` | **`0.843 ms`** | **-10.2% latency** |
| **Block Connect Latency p95** | `1.311 ms` | `1.167 ms` | **`1.178 ms`** | **-10.1% latency** |
| **Block Connect Latency p99** | `1.569 ms` | `1.351 ms` | **`1.356 ms`** | **-13.6% latency** |
| **Block Connect Latency Max** | `2.902 ms` | `2.460 ms` | **`2.616 ms`** | **-9.9% latency** |
| **Block Connect Disk Written** | `67.00 MiB` (`70,254,592 B`) | `81.20 MiB` (`85,147,648 B`) | **`67.05 MiB` (`70,303,744 B`)** | **-17.4% write amp vs. Before 3 Opts** |
| **`-reindex-chainstate -chronikreindex` (0 -> 2,000)** | `1.415 s` (`1,413.5 blk/s`) | `1.183 s` (`1,690.5 blk/s`) | **`1.301 s` (`1,537.6 blk/s`)** | **+8.8% faster** |
| **Full `-reindex -chronikreindex` (0 -> 2,000)** | `2.084 s` (`959.5 blk/s`) | `1.875 s` (`1,066.5 blk/s`) | **`1.971 s` (`1,014.5 blk/s`)** | **+5.7% faster** |

#### Chronik HTTP Query Latency (`µs`)

| Query Endpoint | Count | Baseline (`RocksDB`) p50 / p95 / mean | `libmdbx` (Before 3 Opts) p50 / p95 / mean | `libmdbx` (After 3 Opts) p50 / p95 / mean | Speedup (`After 3 Opts` p50 vs. `Baseline`) |
| :--- | ---: | ---: | ---: | ---: | ---: |
| **`/script/p2sh/<hotspot>/utxos` (`2,100` UTXOs)** | 200 | `462.6 / 782.9 / 514.3 µs` | N/A | **`208.6 / 338.8 / 229.1 µs`** | **2.22x faster (-54.9% p50)** |
| **`/script/{p2sh,p2pkh}/<hash>/utxos`** | 500 | `284.1 / 366.3 / 258.0 µs` | `140.4 / 267.8 / 159.3 µs` | **`220.1 / 791.8 / 311.1 µs`** | **+29.1% faster (-22.5% p50)** |
| **`/script/{p2sh,p2pkh}/<hash>/history`** | 500 | `913.6 / 1,266.6 / 857.0 µs` | `765.4 / 1,093.7 / 720.1 µs` | **`739.9 / 1,059.2 / 683.6 µs`** | **+23.5% faster (-19.0% p50)** |
| **`/tx/<txid>`** | 500 | `194.0 / 267.8 / 201.3 µs` | `195.8 / 268.2 / 203.8 µs` | **`137.4 / 325.9 / 180.6 µs`** | **+41.2% faster (-29.2% p50)** |
| **`/block/<h>` & `/blocks/<h>/<h+10>`** | 500 | `81.6 / 145.2 / 88.6 µs` | `81.5 / 149.1 / 88.7 µs` | **`92.9 / 146.7 / 94.9 µs`** | `-12.2%` (`+11.3 µs`) |
| **`/token/<id>` & `/token-id/<id>/utxos`** | 200 | `103.2 / 215.8 / 114.9 µs` | `104.0 / 210.5 / 116.4 µs` | **`118.4 / 211.2 / 130.0 µs`** | `-12.8%` (`+15.2 µs`) |

#### On-Disk Storage Footprint (After 2,000 Blocks & Reindex)

| Directory | Baseline (`LevelDB + RocksDB`) | Experimental (`libmdbx`) | Notes |
| :--- | ---: | ---: | :--- |
| `regtest/chainstate/` | `3.95 MiB` (`4,146,662 B`) | `16.00 MiB` (`16,777,216 B`) | Single pre-allocated `size_now = 16 MiB` `mdbx.dat` |
| `regtest/blocks/index/` | `0.41 MiB` (`428,994 B`) | `16.00 MiB` (`16,777,216 B`) | Single pre-allocated `size_now = 16 MiB` `mdbx.dat` |
| `regtest/indexes/txindex/` | `0.70 MiB` (`732,777 B`) | `16.00 MiB` (`16,777,216 B`) | Single pre-allocated `size_now = 16 MiB` `mdbx.dat` |
| `regtest/indexes/chronik/` | `7.55 MiB` (`7,915,232 B`) | `16.00 MiB` (`16,777,216 B`) | Single pre-allocated `size_now = 16 MiB` `mdbx.dat` (`0` growth steps) |
| **Total DB Directories** | **`12.61 MiB` (`13,223,665 B`)** | **`64.00 MiB` (`67,108,864 B`)** | Zero file-descriptor sprawl (`4` `.dat` files vs. `90+` `.sst`/`.ldb`/`.log` files) |

---

## 4. Verification & Reproducibility

- **Worktree:** `/private/tmp/lotus-v1-libmdbx-wt` (branch `v1-libmdbx-experiment`, commit `8019da4702f7eb8610d933b8170260175b86bee7`, branched from `6590d92300`).
- **Build Directory:** `/private/tmp/lotus-v1-libmdbx-build` (Baseline build in `/private/tmp/lotus-v1-baseline-build`).
- **Benchmark Script:** [contrib/bench_libmdbx_vs_baseline.py](file:///private/tmp/lotus-v1-libmdbx-wt/contrib/bench_libmdbx_vs_baseline.py)
- **Raw JSON Outputs:**
  - Before 3 optimizations: `/private/tmp/lotus-bench-run/results_before_3_opts.json`
  - After 3 optimizations: `/private/tmp/lotus-bench-run/results.json`
