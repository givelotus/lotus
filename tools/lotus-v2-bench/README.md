# Lotus V2 storage performance baseline

This harness compiles the pinned native implementation at `f1c8c92d87` in Release
mode (`-O3 -DNDEBUG`), with its bundled LevelDB and CRC32C. It edits no daemon
source and starts no network service. It measures components of the development
node, not an end-to-end node TPS limit. The production node is untouched.

The native harness lives in `src/lotus_v2/perf_test/` on the companion native
branch. Build it in a fresh native worktree:

```sh
cmake -S src/lotus_v2/perf_test -B build-perf -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DLOTUS_SECP_LIBRARY=/absolute/path/to/ABC/libsecp256k1.a
cmake --build build-perf --target storage_perf -j1
```

Boost headers are currently selected from `/opt/homebrew/opt/boost/include` in
the focused CMake project. The secp library is used for the existing identity
implementation; this workload does not benchmark signature verification.

Run from this monorepo worktree, after coordinating CPU/I/O use with other jobs:

```sh
/private/tmp/lotus-v2-compiler-review-venv/bin/python tools/lotus-v2-bench/run.py \
  --binary /private/tmp/lotus-v2-perf-native-20261015/build-perf/storage_perf \
  --native /private/tmp/lotus-v2-perf-native-20261015 \
  --output tools/lotus-v2-bench/results/NEW_RESULT_DIRECTORY \
  --trials 3 --sizes 1000 10000 50000 \
  --contention 'State the observed concurrent jobs and timing coordination'
```

Every invocation requires a new `/private/tmp/lotus-v2-perf-*` home, except the
explicit reader invocation. Existing homes/output directories are refused.
Temporary homes are retained for inspection; the runner does not delete them.
Queries use `mt19937_64` with public seed `0x4c6f747573`. Coin identities are
sequential before the implementation hashes outpoints, yielding dispersed trie
keys. Coins have one branch/path, no tokens, and canonical encoding. This is a
small-output baseline, not a realistic mixture of contract/token workloads.

The runner captures raw JSONL, stderr, return codes, compiler/host metadata,
executable SHA256 and repeated min/median/max distributions. Failures and smoke
runs are preserved. Plain text build/process logs have trailing spaces removed
for Git whitespace checks; raw JSONL metrics and failure messages are retained. Functional checks compare the seeded disk root with the
independent incremental tree, validate returned values/proofs and restored roots,
and check history mappings and decoded transaction counts. Fixtures are generated
in memory, independent of existing goldens; no golden is rewritten.

Measurements include wall/user/system time, lifetime process RSS high-water,
minor/major page faults, LevelDB Env read bytes, append bytes, sync calls/time,
and logical state Gets plus deduplicated batch/node/coin payload counts. Env
counters include background compaction that overlaps a phase. Summed sync time
can exceed wall time; it is not an exclusive wall-time fraction. File sizes are
logical directory bytes after closing the DB, not device allocation or total
write amplification.

On this POSIX LevelDB, SST files can be mmap-backed. Env reads may return mapped
memory and uncompressed blocks avoid double caching. Env bytes **are not SSD
reads**, and a small configured block cache does not bound OS page-cache use.
"New process" means fresh LevelDB/application cache with uncontrolled OS cache.
No global caches are flushed and no raw device is accessed. New homes are not
claimed to represent cold-device performance.

`floor` stores the same encoded coins in the same LevelDB with the same sync
batch size but no authenticated tree/undo/index. It measures an engine floor,
**not ABC node or CCoinsViewDB throughput**. ABC has distinct coins encodings,
cache/flush semantics and consensus checks. `history` measures only the actual
TransactionHistory index insertion/reorg path, excluding block retrieval,
validation and Chronik. `decode` measures real framing plus complete transaction
commitment, excluding VM/UTXO/PoW checks. `prototype` is explicitly the standalone
whole-snapshot PersistentUtxoStore that the daemon does not link.

See [the assessment](../../docs/plans/lotus-v2-performance-baseline.md) for
source traces, findings, limitations and the purpose-built database decision.
