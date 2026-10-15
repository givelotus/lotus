# Lotus V2 performance baseline and storage decision

Status: isolated measurement candidate, 2026-10-15. No production code, database
format, consensus commitment, live node, release or published asset is changed.
Native source starts at `f1c8c92d87023c620819dfc4a6bd88a28c446d46`; the companion
benchmark commits and exact executable are recorded in the results. Monorepo
base is `48a47753`. The node integration binary available on this host is Debug;
its acceptance results do not establish production performance.

## What is actually stored

| Path | Representation and engine | Work on the hot path |
| --- | --- | --- |
| ABC chainstate | `CCoinsViewDB`, canonical ABC coin encoding on `CDBWrapper`/LevelDB, fronted by `CCoinsViewCache` | `GetCoin` reads a single coin record; cache flushes serialize dirty coins with best/head block recovery markers. No V2 Merklix commitment. |
| V2 development chain | `DiskStateStore`: custom coin (`C`), collapsed sparse tree (`N`), checkpoint (`S`), undo (`U`) and optional header/active/candidate/recovery schemas on bundled LevelDB | Path-local authenticated mutations, deduplicated overlay, atomic synchronous state/root/metadata/undo batch. Full set is not copied or scanned on ordinary open/connect/lookup/disconnect. |
| V2 standalone snapshot prototype | `PersistentUtxoStore`, `snapshot.dat` plus file undo, in-memory map/tree | Copies the set, rebuilds trees, rewrites snapshots and replays undo on open; **not linked into lotusd**. |
| V2 transaction history | `TransactionHistory`, separate LevelDB with txid-to-confirmation (`T`), exact spent-outpoint (`S`), per-block undo (`B`) and anchor | Already a custom derived transaction index. One synchronous batch per indexed block, with exact predecessor mappings for reorg. No confirmed raw-wire location. |
| ABC txindex | Separate LevelDB `indexes/txindex`; txid-to-`CDiskTxPos` | Finds a raw block file, seeks to transaction position, decodes just that transaction and verifies identity. This inherited class is not V2 framing-aware. |
| Chronik V2 | Separate versioned Rust `V2Db` on RocksDB: output/location records, branch postings, UTXO rows, undo and checkpoint | One synced derived batch, separate node/index commits and adapter replay; bounded snapshots/queries. The legacy Chronik DB has its own column families. |

Source traces at the native pin: `src/txdb.cpp:102,131`,
`src/dbwrapper.cpp:105,198`, `src/lotus_v2/disk_state.cpp:1025,1547,1603`,
`src/lotus_v2/persistent_utxo.cpp:342,495,641`,
`src/lotus_v2/transaction_history.cpp:19,47,85`, `src/index/txindex.cpp:54,91`,
`chronik/chronik-db/src/db.rs:87,133`,
`chronik/chronik-db/src/v2_branch.rs:1,180,678`,
`chronik/chronik-lib/src/v2.rs:18,24,32`.

The active backend is LevelDB, while the authenticated tree, encodings, batching,
undo and recovery are already Lotus-specific. Replacing the engine with RocksDB
alone preserves per-node Gets, repeated proof/hash work, large retained undo
records and duplicate body decoding. That swap needs evidence independently of
Chronik's existing RocksDB use.

## Measurement scope and evidence

The companion [runner and metric definitions](../../tools/lotus-v2-bench/README.md)
retain exact commands, executable/source hashes, stdout/stderr, failures and
repeated distributions. Component measurements use Release `-O3 -DNDEBUG`,
AppleClang 21, portable BLAKE3 and actual bundled LevelDB/CRC32C. They use fresh
local homes and public deterministic small-output fixtures. No service, raw
device or global cache manipulation is involved. The ABC unit build/tests were
held during the measured window, but the captured host snapshot still showed
QEMU (~271% CPU), two Dart processes (~99% each) and LLVM compiler processes
(~73% and ~20%). All elapsed-time results are explicitly **contended desktop
measurements**, not an idle-host baseline. Those processes were not touched.

The generic `DiskStateStore` schema isolates tree/coin/undo cost. The daemon's
indexed header/candidate/recovery schema, VM/signature checks, network, complete
reorg coordinator and Chronik are excluded. Consequently these results are not
ABC-vs-V2 node throughput. The matched LevelDB floor uses identical encoded coin
values, sync settings and batch sizes but omits authentication/undo; its role is
to locate component cost, not stand in for ABC's different cache/flush semantics.

A new process has fresh application/LevelDB state while the OS cache is
uncontrolled. The POSIX LevelDB may return mmap spans for SST reads; Env bytes
are engine API traffic, not physical device bytes or IOPS. Background compaction
can overlap phase boundaries. Process RSS is a lifetime high-water, not isolated
phase allocation. Sync duration sums all counted file calls, including concurrent
engine work. Logical transaction stats on the commit-only phase include staging
work whose elapsed time is separately reported.

### Repeated component results

All values below are median (min–max) across three **contended** trials on Apple
M5 Max, 48 GiB RAM, macOS 26.6. The full [63 successful invocation records](../../tools/lotus-v2-bench/results/coordinated-baseline/provenance.json),
[raw metrics](../../tools/lotus-v2-bench/results/coordinated-baseline/records.json)
and [distributions](../../tools/lotus-v2-bench/results/coordinated-baseline/summary.json)
are retained. These are elapsed times for the named operations, not node TPS.

| UTXOs | Seed, 100 coins/sync batch (ms) | 1,000 warm authenticated lookups (ms) | 1,000 new-process first lookups (ms) | Stage 100 spends + 100 creates (ms) | Commit staged replacement only (ms) | Disconnect replacement (ms) |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1000 | 78.44 (72.19–88.49) | 22.10 (19.55–24.36) | 39.25 (35.86–41.37) | 11.30 (9.40–11.63) | 5.02 (4.02–5.52) | 43.32 (37.22–44.26) |
| 10000 | 1311.20 (1204.10–1430.16) | 38.40 (34.76–40.48) | 61.30 (58.50–62.21) | 19.96 (19.15–20.55) | 6.71 (5.88–6.98) | 104.26 (101.15–106.45) |
| 50000 | 9343.03 (9292.27–9395.39) | 68.53 (68.02–70.53) | 72.33 (70.86–73.22) | 34.89 (34.70–35.05) | 5.82 (5.38–7.55) | 137.32 (132.93–141.55) |

| UTXOs | Gets per authenticated lookup | Deduplicated seed tree-node writes | Seed logical batch payload (MB) | Seed Env append bytes (MB) | Append / payload during seed | Peak RSS at end of seed (MiB) |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1000 | 14.359 | 5,196 | 2.23 | 2.25 | 1.01× | 7.38 |
| 10000 | 17.644 | 83,982 | 35.02 | 167.69 | 4.79× | 38.03 |
| 50000 | 19.971 | 534,304 | 220.21 | 1582.81 | 7.19× | 69.95 |

The append/payload ratio is an **observed engine-file ratio for this phase**,
including overlapping compaction and LevelDB framing. It is not physical SSD
write amplification or a whole-lifecycle total. Some background work falls in
later phases. The 50k seed also records a median 15 major faults; it does not
establish sustained device saturation.

At 1k UTXOs, 1,000 authenticated lookups make exactly 14,359 logical Gets with
zero Env file reads and median 21.948 ms user CPU. The coin-only LevelDB floor
for the same 1,000 query identities takes median 0.567 ms (0.512–0.641 ms), one
Get per query. Authentication/encoding/traversal cost is present even when
nothing reaches a file read. These operations have different guarantees; this
is a component floor, not an ABC performance comparison.

At 10k UTXOs, increasing seed batches from 100 to 1,000 reduces median elapsed
time from 1,311.2 to 688.8 ms, logical Gets from 230,020 to 131,839, deduplicated
node writes from 83,982 to 51,717, and Env appends from 167.7 to 57.9 MB. The
fixture demonstrates a batching opportunity; changing block batching or durable
publication semantics requires a separate implementation/correctness review.
At 10k, warm lookup medians with 64 KiB vs 8 MiB block caches are 39.65 vs
38.40 ms. mmap/OS caching and concurrent compaction prevent treating this as a
meaningful memory-bound cache comparison.

| Component/workload | Elapsed ms, median (min–max) |
| --- | ---: |
| One historical metadata read: prior block changed 100 coins to 100 new coins | 3.66 (3.59–3.73) |
| One historical metadata read: prior block changed 1,000 coins to 1,000 new coins | 21.44 (21.37–22.98) |
| Disconnect 1,000-spend/1,000-create replacement | 631.05 (629.39–638.17) |
| Open after 100 metadata commits, fixed 100 UTXOs | 16.34 (15.29–17.44) |
| Open after 1,000 metadata commits, fixed 100 UTXOs | 18.67 (17.51–54.77) |
| 1,000 lookups at 100 metadata commits, fixed 100 UTXOs | 26.74 (26.09–27.16) |
| 1,000 lookups at 1,000 metadata commits, fixed 100 UTXOs | 26.61 (26.59–31.36) |
| History index only: 100 blocks × 100 transactions | 456.16 (436.04–692.82) |
| History index only: 1,000 blocks × 100 transactions | 5886.48 (5758.77–6503.27) |
| History index disconnect: 10 blocks × 100 transactions | 42.08 (41.12–42.17) |
| One 1,000-transaction block framing decode + commitment | 1.99 (1.92–2.06) |

Historical metadata retrieval is measured independently of full validated body
retrieval: those fixtures use opaque metadata, and the changed-node undo lookup
already validates every undo row. The cost rises from 3.66 to 21.44 ms per read
when the replacement changes 100 vs 1,000 coins at the same 10k cardinality.
No direct random-access confirmed-wire endpoint was measured. The block decoder
separately handles a 109,135-byte fixture with 1,000 transactions; it copies
frames and recomputes the complete commitment. Body-validation/VM costs and the
source-traced repeated consumers are additional costs, not included in the
reported decoder timing.

With a fixed 100 UTXOs, both height opens issue three logical Gets, and both
1,000-lookup phases issue 11,161 Gets. The 999 empty metadata commits take
median 3.674 s, including 3.628 s summed sync duration and only 15.6 ms user CPU.
This isolates per-checkpoint persistence latency at bounded height; it does not
benchmark the daemon's indexed header/candidate query paths.

History catchup includes actual txid/txhash confirmations, one consumed outpoint
per transaction, exact mapping undo and synced anchors. It excludes reading or
validating blocks and Chronik. At 100k transactions it appends a median 348.6 MB
at the Env layer and ends near 30 MB of logical index files after the ten-block
undo/reopen workload; compaction and synchronous indexing deserve profiling.

The non-daemon snapshot prototype is retained as an architectural control:
seeding 100/1,000 coins in 100-coin batches takes median 1.23/47.69 ms. Reopening
after one undo takes 0.058 ms for the now-empty store and 13.23 ms for 900 coins.
Those are different resulting cardinalities and durability mechanisms; they
are not a daemon backend comparison or proof of an asymptotic timing bound.

The initial smoke runs were made while the inherited ABC build was active and
are preserved only as harness validation. Two early decode fixture failures
(`coinbase data`, `transaction header`) are retained; the final fixture satisfies
the existing codec. They do not indicate daemon validation failures.

## Priorities supported by measurements and source traces

1. **Avoid repeated retained-body work.** Historical `ReadRetainedState` loads a
   complete immutable undo value and validates every changed node/coin, even
   when the caller only needs metadata/body (`disk_state.cpp:641`).
   `ReadRetainedBlockBody` then copies context/body, decodes every transaction and
   authenticates the commitment (`disk_body.cpp:14`). `PoolCoordinator::Body`
   decodes the same wire again, and history catchup computes identities again
   (`pool_coordinator.cpp:58,121`). Chronik's `MakeChronikBlock` also repeats
   complete-root and identity computation after `ReadConnectedBody`
   (`chronik_sync.cpp:7,131`). The node's 64 KiB `readblock` response repeats the
   whole-body operation for every chunk (`development_node_command.cpp:1185`).
   First experiment: one authenticated immutable decoded-body view per block ID,
   shared by chunk replies/history/Chronik, with bounded memory and explicit
   retention. Separate immutable body storage from mutation undo after measuring
   a complete read/reorg workload; retain all identity/state/PoW checks at the
   trust boundary.
2. **Reduce authenticated UTXO CPU work before changing disks.**
   `AuthReadCoin` generates/verifies a full proof, reads its terminal coin, then
   reads the requested coin again and re-encodes to compare
   (`disk_state.cpp:906,935`). Insert/erase repeat membership authentication and
   recursively parse/hash shared upper paths for each mutation
   (`disk_state.cpp:838,855,1570`). The final write batch deduplicates node keys,
   but that does not deduplicate all computation. Test bounded parsed-node caches
   keyed by verified root/version, a trusted checked coin result reused within
   one transaction, and bulk path updates that hash shared ancestors once.
   Preserve exact roots/proofs and corruption detection; do not simply remove
   authentication from the API.
3. **Measure durable checkpoint frequency.** State and history each request
   synchronous writes (`disk_state.cpp:781`, `transaction_history.cpp:35`).
   macOS bundled LevelDB attempts `F_FULLFSYNC` (`leveldb/util/env_posix.cc:375`).
   Small commits can spend most elapsed time waiting for persistence. Test
   grouping derived history replay with one atomic anchor/undo batch and reducing
   redundant checkpoint work. State/root/undo and recovery journal durability,
   publication fences and poisoned-store behavior are required; disabling sync
   is not a valid performance fix.
4. **Tune the existing engine before replacing it.** V2's open options do not
   install a Bloom filter (`disk_state.cpp:1032`), while ABC's `CDBWrapper` uses
   ten bits/key (`dbwrapper.cpp:108`). Test negative-key-heavy insert/undo lookups
   with Bloom filters, write-buffer sizes and bounded file/node caches. The
   measured seed append/payload ratio grows to 7.19× at 50k UTXOs; profile where
   compaction rewrites tree/coin data versus retained immutable undo and body
   bytes. Bodies appear in both before/after checkpoint payloads of adjacent
   undo records (`disk_state.cpp:336,1640`), so separating immutable data from
   mutable tree keys is a focused layout alternative. None of these prospective
   tuning benefits is measured by this baseline.
5. **Measure storage layout after those fixes.** Every authenticated lookup can
   touch logarithmically many independently encoded tree nodes. Upper-node page
   grouping or an immutable path-copy layout may reduce random reads while
   preserving every existing `UtxoNode`/leaf hash and proof. Test once working
   sets exceed memory, with actual page-fault/device counters, compaction stalls,
   crash recovery and long reorgs. Increase sizes gradually rather than
   extrapolating these bounded fixtures to billions of UTXOs.

The whole-set copying in `PersistentUtxoStore` is real but belongs to the
standalone prototype. Applying its scaling findings to the daemon would be an
architecture error. In the measured disk backend, opening validates schema/head
and the root node plus explicitly selected indexes; it does not replay the full
UTXO set. History catchup uses the active height index, not a tip-to-genesis walk
for every fresh request. Candidate and ancestry range queries have explicit
budgets; finality policy can scan candidate ranks/ancestry
(`disk_state.cpp:1377`), so fork-heavy workloads remain an independent experiment.

## MonadDb comparison and break-even experiments

Monad's [primary documentation](https://docs.monad.xyz/monad-arch/execution/monaddb)
describes a native persistent Patricia trie, path-copy versions, sequential
writes, asynchronous Linux `io_uring`, optional regular-file/block-device use and
inline compaction. Its MIP-8 storage pages commit groups of 128 EVM slots using
BLAKE3. Those claims describe Monad's design, not measured Lotus speedups.

The inspected source is pinned in
[the source audit manifest](../../tools/lotus-v2-bench/results/monad-source-audit.json)
to `4a0c81f543ac4ffec043da87dacf7f78c27c6d0e`:
[versioned DB API](https://github.com/category-labs/monad/blob/4a0c81f543ac4ffec043da87dacf7f78c27c6d0e/category/mpt/db.hpp),
[updated-child writes](https://github.com/category-labs/monad/blob/4a0c81f543ac4ffec043da87dacf7f78c27c6d0e/category/mpt/trie.cpp#L530),
[compaction policy](https://github.com/category-labs/monad/blob/4a0c81f543ac4ffec043da87dacf7f78c27c6d0e/category/mpt/update_aux.cpp#L895),
[async file requests](https://github.com/category-labs/monad/blob/4a0c81f543ac4ffec043da87dacf7f78c27c6d0e/category/async/io.cpp#L279),
and [storage pool](https://github.com/category-labs/monad/blob/4a0c81f543ac4ffec043da87dacf7f78c27c6d0e/category/async/storage_pool.cpp).
The implementation exposes version validity checks and updates only changed
children; compaction distinguishes frequently updated and slower rings with
retention thresholds. This carries nontrivial reclamation and recovery machinery.
No Monad code is copied into Lotus, and no Monad benchmark is run here.

For Lotus, outpoint keys are cryptographically dispersed; a spend removes one
coin and creates new coins rather than repeatedly overwriting adjacent EVM
storage slots. Page locality therefore needs measurement. Grouping physical
nodes in storage while retaining their exact logical hashes/proofs can be an
implementation change. Committing pages in place of Lotus leaves, as MIP-8 does
for slots, changes state roots/proofs and requires a separately reviewed
consensus change. It is outside this task.

A purpose-built store becomes a candidate only if an optimized LevelDB baseline
still misses an explicit block-validation/reorg/read-latency target and profiles
attribute the gap to serial random I/O, compaction or engine amplification. The
break-even experiment should compare equal authenticated operations, durability,
cache/RSS budget, retained versions and hardware. Measure total bytes written
(including compaction/GC), device reads/page faults, CPU hashing/encoding, latency
percentiles and restart/reorg time over sustained overwrite/delete churn. A
packed layout should save enough measured read/write work to outweigh its own
COW version retention and GC, not merely beat an unoptimized small benchmark.
Async reads require independent work to overlap; Lotus's serialized transaction
root updates currently limit that opportunity. Linux `io_uring` also needs a
portable fallback and an independently measured scheduler/prefetch plan.

Before promotion, a custom store needs atomic durable publication of root,
monetary state, active headers and recovery journal; checksummed versioned roots;
ambiguous-write handling; torn-write/power-loss injection; corrupt-node detection;
reader leases and safe version reclamation; exact disconnect/reconnect and
finality/parking semantics; capacity refusal; deterministic snapshot migration
with root verification; restart/resume and rollback to the previous format. An
append-only COW tree alone does not satisfy those requirements. The current
measurement supports testing a purpose-built layout, but does not yet justify
replacing LevelDB: redundant authenticated CPU work and durable small-batch
frequency are demonstrated, the existing engine has untested simple tuning
options, and sustained physical-device behavior is unmeasured.

## Raw transaction index decision

The status/history index already resolves txid to selected txhash and block.
`PoolCoordinator::ReadWire` currently serves pending pool wire only
(`pool_coordinator.cpp:188`); there is no confirmed raw transaction locator in
that index. The inherited ABC txindex's file position model cannot be reused
unchanged for V2 frames or LevelDB-embedded block bodies.

| Option | Cost and fit | Required safeguards |
| --- | --- | --- |
| Existing block lookup plus full decode | Lowest new storage; current body/undo and repeated commitment cost | Cache authenticated immutable views; explicit body availability/pruning errors |
| txid/txhash to block ID plus frame offset/length | Small derived rows; avoids repeated frame search once body is loaded | Bind exact txhash and block identity, canonical frame bounds, active status/reorg undo, index checkpoint, pruning/retention contract |
| Same locator plus append-only block-body file | Enables positioned file reads of one transaction | Durable file/index ordering, checksums and frame identity validation, crash rollback, file lifetime/reclamation, migration from embedded bodies |
| Duplicated raw wire in tx index | Simple point retrieval, additional bytes and write/compaction load | Atomically fenced index anchor, txid/txhash variants, reorg semantics, bounded retention/pruning and crash rebuild |

An offset into a LevelDB value is not an independently seekable file offset:
LevelDB must still fetch the containing value. Measure immutable body separation
and decoded-block caching before choosing duplicated wire. A minimal derived
frame locator can be added independently of the consensus UTXO store if confirmed
raw transaction latency becomes a product requirement. The decisive benchmark
is repeated single-transaction lookup in large blocks, with warm/new-process
caches, known block vs global lookup, catchup/reorg churn and retention enabled.
Compare locator reads with duplicated wire at equal durability and memory budget.
No measured confirmed-wire endpoint or sustained device-bound workload currently
establishes that a bespoke raw transaction database is necessary.

## Remaining node-level experiments

Build matched Release ABC and V2 binaries from immutable pins in separate clones,
choose comparable small-output validation workloads, and keep differences in VM,
commitment and sync semantics explicit. Measure block acceptance, steady-state
spend/create, template construction, deep reorg and index catchup with Chronik
both enabled and disabled. Retain failures and per-block distributions. Scale
UTXOs and height independently into working sets above memory, on dedicated
Linux SSD hardware with permitted device telemetry, without flushing global
caches. The current actual Debug node acceptance and inherited ABC test passes
are correctness evidence; they are not the missing matched performance trial.
