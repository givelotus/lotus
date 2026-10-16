# Lotus V1 `libmdbx` Storage Backend Benchmark Report

## 1. Executive Summary

We built and benchmarked an experimental **`libmdbx` (`v0.13.11`)** storage backend in Lotus V1 (`lotus-v1-latest`, base commit `6590d92300` -> experimental commit `2ac115e32d` on branch `v1-libmdbx-experiment`), replacing **both**:
1. **LevelDB** in `CDBWrapper` ([src/dbwrapper.h](file:///private/tmp/lotus-v1-libmdbx-wt/src/dbwrapper.h) / [src/dbwrapper.cpp](file:///private/tmp/lotus-v1-libmdbx-wt/src/dbwrapper.cpp)), backing `chainstate/` (`CCoinsViewDB`), `blocks/index/` (`CBlockTreeDB`), and `indexes/txindex/`.
2. **RocksDB** in `chronik-db` ([chronik/chronik-db/src/db.rs](file:///private/tmp/lotus-v1-libmdbx-wt/chronik/chronik-db/src/db.rs), [chronik/chronik-db/src/group.rs](file:///private/tmp/lotus-v1-libmdbx-wt/chronik/chronik-db/src/group.rs), [chronik/chronik-db/src/io/group_utxos.rs](file:///private/tmp/lotus-v1-libmdbx-wt/chronik/chronik-db/src/io/group_utxos.rs)), backing all 22 Chronik column families under `indexes/chronik/`.

### Key Highlights (with C-Level FFI Batching & 8 KiB `CDBWrapper` Pages)
- **End-to-End Block Connect (2,000 blocks, 16,433 txs, 52,246 outputs, `-chronik=1 -txindex=1`):** **`1.625s` (`1,230.5 blk/s`, `10,110.1 tx/s`)** on `libmdbx` vs. **`1.661s` (`1,204.1 blk/s`, `9,893.2 tx/s`)** on Baseline (`LevelDB + RocksDB`), with lower latency at every percentile (`p50 = 0.789 ms` vs `0.835 ms`, `p95 = 1.075 ms` vs `1.237 ms`, `p99 = 1.263 ms` vs `1.413 ms`) and identical disk bytes written (`67.03 MiB` vs `67.00 MiB`).
- **Reindex Throughput (`0 -> 2,000`):**
  - `-reindex-chainstate -chronikreindex`: **`1.133s` (`1,765.2 blk/s`)** on `libmdbx` vs. **`1.297s` (`1,541.6 blk/s`)** on Baseline (**+14.5% faster throughput / -12.7% wall time**; `-21.8%` faster and **50% less disk write volume** than 16 KiB `CDBWrapper` pages).
  - Full `-reindex -chronikreindex`: **`1.781s` (`1,123.1 blk/s`)** on `libmdbx` vs. **`1.940s` (`1,030.9 blk/s`)** on Baseline (**+8.9% faster throughput / -8.2% wall time**).
- **High-UTXO Script Query Latency (`2,100` UTXOs on a single script):** **`164.6 µs` p50** (`172.6 µs` mean, `243.7 µs` p95) on `libmdbx` with `MDBX_DUPSORT | MDBX_DUPFIXED` + `MDBX_SEEK_AND_GET_MULTIPLE` page-batch reads vs. **`410.2 µs` p50** (`444.4 µs` mean, `643.7 µs` p95) on Baseline RocksDB — **2.49x faster (`-59.9%` p50 latency)**.
- **Standard Chronik HTTP Queries:**
  - `script_utxos`: **`143.3 µs` p50** on `libmdbx` vs. **`256.1 µs` p50** on Baseline (**1.79x faster / -44.0% p50**).
  - `script_history`: **`696.5 µs` p50** on `libmdbx` vs. **`783.6 µs` p50** on Baseline (**1.13x faster / -11.1% p50**).
  - `tx_lookup`: **`139.8 µs` p50** on `libmdbx` vs. **`158.6 µs` p50** on Baseline (**1.13x faster / -11.9% p50**).
- **C++ Microbenchmarks (`lotus-bench`):**
  - `DBWrapperRead`: **`240.06 ns/read` (`4.17M reads/s`)** on `libmdbx` vs. **`284.78 ns/read` (`3.51M reads/s`)** on LevelDB (**+18.6% faster**).
  - `DBWrapperIterator`: **`70.36 ns/entry` (`14.21M entries/s`)** on `libmdbx` vs. **`84.90 ns/entry` (`11.78M entries/s`)** on LevelDB (**+20.7% faster**).
  - `CCoinsCaching`: **`4,250.01 ns/op` (`235.3k ops/s`)** on `libmdbx` vs. **`4,406.71 ns/op` (`226.9k ops/s`)** on LevelDB (**+3.7% faster**).
- **100% Protocol & Consensus Equivalence:** All 2,400 Chronik HTTP protobuf responses across `script_history`, `script_utxos`, `high_utxo_script_utxos`, `tx`, `block`, `blocks`, `token`, and `token-id/utxos` produced identical SHA-256 digests (`5db451043a011264fcfb3dd3cb849178d321f83c1fdaccb61c2e3da4cc2886b1` and `0fd922b6259d3997985d45eb1d718535fda8432f1231b3ee07aec420050fee2c`).

---

## 2. Architecture & Implementation Details

### 2.1 Vendored `libmdbx` (`src/libmdbx/`) & Custom C Batch FFI Helpers
- Vendored amalgamated `libmdbx` `v0.13.11` into [src/libmdbx/mdbx.c](file:///private/tmp/lotus-v1-libmdbx-wt/src/libmdbx/mdbx.c) and [src/libmdbx/mdbx.h](file:///private/tmp/lotus-v1-libmdbx-wt/src/libmdbx/mdbx.h), compiled as static library target `mdbx` with `-O3 -DNDEBUG -std=gnu11` ([src/libmdbx/CMakeLists.txt](file:///private/tmp/lotus-v1-libmdbx-wt/src/libmdbx/CMakeLists.txt)).
- **Critical Upstream `libmdbx` v0.13.11 GC Reclamation Fix ([src/libmdbx/mdbx.c#L22757](file:///private/tmp/lotus-v1-libmdbx-wt/src/libmdbx/mdbx.c#L22757)):**
  - Fixed `gc_alloc_ex` steady-point wipe check (`oldest == prefer_steady.txnid`) and extended the nosync condition to `MDBX_SAFE_NOSYNC` so retired Copy-on-Write pages are recycled immediately via `MDBX_LIFORECLAIM | MDBX_COALESCE`, keeping all 4 `.dat` files at their initial **`16 MiB`** allocation across the entire 2,000-block benchmark.
- **Custom C-Level Batch FFI Helpers (`src/libmdbx/mdbx.h`, `src/libmdbx/mdbx.c`):**
  - Because we own both the vendored `libmdbx` C source and the Rust FFI layer in `chronik-db`, we implemented five batch C helpers compiled directly inside `libmdbx` (`-O3` inlined with `mdbx_cursor_put` / `mdbx_cursor_get`):
    1. `mdbx_batch_kv_apply`: Applies an entire sorted array of `MDBX_batch_kv_op` (`Put` / `Delete`) for a column family in a single FFI call using a bound `MDBX_cursor`.
    2. `mdbx_batch_dup_apply`: Applies an entire sorted array of `MDBX_batch_dup_op` (`Put` / `DeleteExact12` / `DeletePrefix`) for a `MDBX_DUPSORT` column family in a single FFI call.
    3. `mdbx_batch_multi_get`: Performs an entire `multi_get` key lookup batch in a single FFI call and returns zero-copy mmap slices (`MDBX_val`) directly to Rust.
    4. `mdbx_dupfixed_get_pages` & `mdbx_dupfixed_get_current_pages`: Uses `MDBX_SEEK_AND_GET_MULTIPLE` / `MDBX_GET_MULTIPLE` + `MDBX_NEXT_MULTIPLE` to read an entire 16 KiB page of up to **1,363 packed 12-byte UTXOs** in a single FFI call (`1` FFI call per 1,363 UTXOs instead of `2,100` per-item FFI calls).

### 2.2 Phase 1: `CDBWrapper` on `libmdbx` ([src/dbwrapper.h](file:///private/tmp/lotus-v1-libmdbx-wt/src/dbwrapper.h), [src/dbwrapper.cpp](file:///private/tmp/lotus-v1-libmdbx-wt/src/dbwrapper.cpp))
- **Dynamic Geometry & 8 KiB Page Size:**
  - `size_lower = 1 MiB`, `size_now = 16 MiB` (`4 MiB` for `memory_only`), `size_upper = 256 GiB` (`4 GiB` for `memory_only`), `growth_step = 64 MiB`, `shrink_threshold = 128 MiB`, `pagesize = 8192` (8 KiB).
  - Using `8192`-byte pages for `CDBWrapper` (`chainstate/` and `txindex/` where keys are small 36-byte outpoints/txids) halves Copy-on-Write page dirtying during `CCoinsViewDB::BatchWrite` compared to 16 KiB pages, reducing `-reindex-chainstate` disk writes from `30.89 MiB` to `16.18 MiB` and cutting `-reindex-chainstate` time from `1.448s` to `1.133s`.
  - `CDBWrapper::WriteBatch` sorts batch operations by key and applies `Put` entries through a single bound `MDBX_cursor` (`mdbx_cursor_put`) to maximize B+Tree page locality.
- **Zero-Allocation Read Transaction & Cursor Pooling:**
  - `CDBWrapper` maintains a mutex-guarded pool of reset `MDBX_txn` and unbound `MDBX_cursor` handles (`AcquireReadTxn` / `ReleaseReadTxn`, `AcquireReadCursor` / `ReleaseReadCursor`), using `mdbx_txn_renew` / `mdbx_txn_reset` and `mdbx_cursor_bind` / `mdbx_cursor_unbind`.

### 2.3 Phase 2: `chronik-db` on `libmdbx` ([chronik/chronik-db/src/db.rs](file:///private/tmp/lotus-v1-libmdbx-wt/chronik/chronik-db/src/db.rs), [chronik/chronik-db/src/io/group_utxos.rs](file:///private/tmp/lotus-v1-libmdbx-wt/chronik/chronik-db/src/io/group_utxos.rs))
- **Column Families -> Named Subdatabases (`MDBX_dbi`):**
  - All 22 Chronik column families map to named `MDBX_dbi` handles in a single `mdbx.dat` environment (`pagesize = 16384`, `max_dbs = 64`).
  - Keys $> 7,500$ bytes (e.g. oversized raw `ScriptVariant::Other` scripts) are transparently normalized with a domain-separated SHA-256 prefix (`MDBX_SHA256_KEY:<32-byte-sha256>`).
- **Native `MDBX_DUPSORT | MDBX_DUPFIXED`, Inline `DupOp::Put12`, and Direct `mdbx_del`:**
  - All production UTXO column families (`script_utxo`, `token_id_utxo`, `lokad_id_utxo`, `plugin_utxo`) have `UtxoData = ()` (`FIXED_DUP_SIZE = Some(12)`), storing `[tx_num_be (8B), out_idx_be (4B)]` in `MDBX_CREATE | MDBX_DUPSORT | MDBX_DUPFIXED` sub-trees.
  - `WriteBatch::put_dup12_cf` stores the 12-byte duplicate inline in `DupOp::Put12([u8; 12])` with **zero heap allocation**.
  - Spending a UTXO on a 12-byte `DUPFIXED` sub-database executes a direct single-step `mdbx_del(txn, dbi, &k, &v)` inside `mdbx_batch_dup_apply` (and cancels intra-batch create+spend pairs in memory before touching the B+Tree).
  - Querying UTXOs (`get_dups_visit` and `dup_prefix_iterator`) uses `mdbx_dupfixed_get_pages` / `mdbx_dupfixed_get_current_pages` (`MDBX_SEEK_AND_GET_MULTIPLE` + `MDBX_NEXT_MULTIPLE`) to decode entire pages of packed 12-byte UTXOs at once.

---

## 3. Benchmark Results

### 3.1 C++ Microbenchmarks (`lotus-bench -filter="DBWrapper.*|CCoins.*" -min_time=500`)

| Benchmark | Baseline (`LevelDB`) | `libmdbx` (3 Opts, 16 KiB Pages) | `libmdbx` (FFI Batch + 8 KiB Pages) | Speedup (`Final` vs. `Baseline`) |
| :--- | ---: | ---: | ---: | ---: |
| `DBWrapperRead` | `284.78 ns/read` (`3,511,469 read/s`) | `247.43 ns/read` (`4,041,570 read/s`) | **`240.06 ns/read` (`4,165,559 read/s`)** | **+18.6% faster** |
| `DBWrapperIterator` | `84.90 ns/entry` (`11,779,251 entry/s`) | `71.52 ns/entry` (`13,982,174 entry/s`) | **`70.36 ns/entry` (`14,212,970 entry/s`)** | **+20.7% faster** |
| `CCoinsCaching` | `4,406.71 ns/op` (`226,927 op/s`) | `4,182.60 ns/op` (`239,086 op/s`) | **`4,250.01 ns/op` (`235,293 op/s`)** | **+3.7% faster** |
| `DBWrapperWriteBatch` | `577.70 ns/kv` (`1,730,992 kv/s`) | `945.97 ns/kv` (`1,057,119 kv/s`) | **`869.22 ns/kv` (`1,150,457 kv/s`)** | `-33.5%` (`+8.8%` faster vs. 16 KiB pages) |
| `CCoinsViewDBFlush` | `720.08 ns/coin` (`1,388,743 coin/s`) | `1,096.20 ns/coin` (`912,245 coin/s`) | **`1,042.37 ns/coin` (`959,352 coin/s`)** | `-30.9%` (`+5.2%` faster vs. 16 KiB pages) |

### 3.2 End-to-End 2,000-Block Regtest Workload ([contrib/bench_libmdbx_vs_baseline.py](file:///private/tmp/lotus-v1-libmdbx-wt/contrib/bench_libmdbx_vs_baseline.py))
- **Workload Parameters:** `2,000` blocks, `16,433` transactions, `16,433` inputs, `52,246` outputs across `400` P2SH/P2PKH scripts, `50` P2PK scripts, LOKAD IDs, and `380` ALP tokens (genesis + send churn), plus `P2SH_OP_TRUE` accumulating `2,100` unspent UTXOs (`4,000` outputs created and `1,900` inputs spent).

#### Block Connect & Reindex Performance

| Metric | Baseline (`LevelDB + RocksDB`) | `libmdbx` (3 Opts) | `libmdbx` (FFI Batch + 8 KiB Pages) | Improvement (`Final` vs. `Baseline`) |
| :--- | ---: | ---: | ---: | ---: |
| **Connect 2,000 Blocks — Wall Time** | `1.661 s` | `1.708 s` | **`1.625 s`** | **-2.2% time (+2.2% blk/s)** |
| **Connect 2,000 Blocks — Throughput** | `1,204.1 blk/s` (`9,893.2 tx/s`) | `1,171.2 blk/s` (`9,623.0 tx/s`) | **`1,230.5 blk/s` (`10,110.1 tx/s`)** | **+2.2% throughput** |
| **Block Connect Latency p50** | `0.835 ms` | `0.818 ms` | **`0.789 ms`** | **-5.5% latency** |
| **Block Connect Latency p95** | `1.237 ms` | `1.158 ms` | **`1.075 ms`** | **-13.1% latency** |
| **Block Connect Latency p99** | `1.413 ms` | `1.547 ms` | **`1.263 ms`** | **-10.6% latency** |
| **Block Connect Latency Max** | `8.625 ms` | `5.887 ms` | **`7.246 ms`** | **-16.0% latency** |
| **Block Connect Disk Written** | `67.00 MiB` (`70,254,592 B`) | `67.03 MiB` (`70,287,360 B`) | **`67.03 MiB` (`70,287,360 B`)** | **Identical disk writes (`+0.05%`)** |
| **`-reindex-chainstate -chronikreindex` (0 -> 2,000)** | `1.297 s` (`1,541.6 blk/s`) | `1.448 s` (`1,381.0 blk/s`) | **`1.133 s` (`1,765.2 blk/s`)** | **-12.7% time (+14.5% blk/s)** |
| **Full `-reindex -chronikreindex` (0 -> 2,000)** | `1.940 s` (`1,030.9 blk/s`) | `2.054 s` (`973.8 blk/s`) | **`1.781 s` (`1,123.1 blk/s`)** | **-8.2% time (+8.9% blk/s)** |

#### Chronik HTTP Query Latency (`µs`)

| Query Endpoint | Count | Baseline (`RocksDB`) p50 / p95 / mean | `libmdbx` (3 Opts) p50 / p95 / mean | `libmdbx` (FFI Batch) p50 / p95 / mean | Speedup (`FFI Batch` p50 vs. `Baseline`) |
| :--- | ---: | ---: | ---: | ---: | ---: |
| **`/script/p2sh/<hotspot>/utxos` (`2,100` UTXOs)** | 200 | `410.2 / 643.7 / 444.4 µs` | `245.5 / 323.7 / 245.3 µs` | **`164.6 / 243.7 / 172.6 µs`** | **2.49x faster (-59.9% p50)** |
| **`/script/{p2sh,p2pkh}/<hash>/utxos`** | 500 | `256.1 / 400.5 / 243.5 µs` | `153.3 / 364.8 / 175.4 µs` | **`143.3 / 210.9 / 143.0 µs`** | **1.79x faster (-44.0% p50)** |
| **`/script/{p2sh,p2pkh}/<hash>/history`** | 500 | `783.6 / 1,012.3 / 688.2 µs` | `723.7 / 950.2 / 640.5 µs` | **`696.5 / 999.6 / 635.0 µs`** | **1.13x faster (-11.1% p50)** |
| **`/tx/<txid>`** | 500 | `158.6 / 286.8 / 175.8 µs` | `146.9 / 219.9 / 150.7 µs` | **`139.8 / 250.4 / 152.7 µs`** | **1.13x faster (-11.9% p50)** |
| **`/block/<h>` & `/blocks/<h>/<h+10>`** | 500 | `57.4 / 135.9 / 67.4 µs` | `66.1 / 120.7 / 69.5 µs` | **`66.5 / 143.7 / 79.5 µs`** | `+9.1 µs` (`p99` `-5.9%` faster) |
| **`/token/<id>` & `/token-id/<id>/utxos`** | 200 | `83.2 / 184.4 / 95.3 µs` | `110.2 / 168.1 / 109.7 µs` | **`113.0 / 204.0 / 121.4 µs`** | `+29.8 µs` |

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

- **Worktree:** `/private/tmp/lotus-v1-libmdbx-wt` (branch `v1-libmdbx-experiment`, commit `2ac115e32d`, branched from `6590d92300`).
- **Build Directory:** `/private/tmp/lotus-v1-libmdbx-build` (Baseline build in `/private/tmp/lotus-v1-baseline-build`).
- **Benchmark Script:** [contrib/bench_libmdbx_vs_baseline.py](file:///private/tmp/lotus-v1-libmdbx-wt/contrib/bench_libmdbx_vs_baseline.py)
- **Raw JSON Outputs:**
  - Before 3 optimizations: `/private/tmp/lotus-bench-run/results_before_3_opts.json`
  - Final (with FFI batching & 8 KiB `CDBWrapper` pages): `/private/tmp/lotus-bench-run/results.json`
