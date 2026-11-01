# libmdbx on Lotus V1 and Bitcoin Core: partial review

**Status: stopped early at the owner's request.** These patches are to be rebased after the
bitcoin-abc reset. Nothing was ported. This records what the review established before it stopped.

Neither PR is safe to use as written. PR #24 (V1) is the dangerous one: it has no data migration
and its durability settings don't survive a power cut.

How far each claim was checked:

- **Experiment:** measured with the harness in `daemon/docs/evidence/mdbx-v1-core/powerloss-sim/`.
- **Compared:** byte comparison against an upstream release.
- **Read:** concluded from reading the code. Not run.
- **Unverified:** a plausible risk that still needs a test.

## Final commits

None. There are no port commits on any branch.

| Item | State |
|---|---|
| `daemon/lotusv1` | Local branch `lotusv1` created from `origin/lotusv1` at the pin `b78b0cac568f`. The checkout was previously detached at the same commit. The commit has not moved. |
| `daemon/bitcoind` | Still detached at the pin `f13ae519de94`. `mdbx/storage-backend` was not created. |
| Pins | Unchanged. `make sync` was not run, and `sources.json` and `stack-review.json` are unmodified. |
| Backup refs | `refs/backups/mdbx-port/lotusv1-pre` and `refs/backups/mdbx-port/bitcoind-pre`, both at the pins. |
| Parent repository | New tracking refs for the two PR branches (fetched without prune). Uncommitted: this report and the evidence directory. |

Nothing had moved, so nothing needed restoring.

## The owner's question: migration and layout

The owner recalled "something to do with the migration or the layout". Both have real problems.
The migration problem in V1 is the most severe finding here, and is probably what was remembered.
That last part is an inference: nothing in the patches says which problem the owner meant.

### Migration

**V1 (PR #24): there is no migration, from either LevelDB or RocksDB. (Read)**

`CDBWrapper` in patch 249 opens `mdbx.dat` in the existing directory and never looks at the LevelDB
files. The only references to them are in the wipe path. `chronik-db` drops the `rocksdb` crate, so
nothing can read the old index, and it has no check for one. On a real V1 datadir, the expected
sequence is:

1. `chainstate/`, `blocks/index/` and `indexes/txindex/` each get a new empty `mdbx.dat` beside the
   intact LevelDB files. The node sees an empty block index and an empty chainstate and starts from
   genesis, without an error.
2. `FindNextBlockPos` takes its position from `m_blockfile_info[nFile].nSize`, which is now 0, and
   `FlatFileSeq::Open` opens the file with `rb+`. New blocks should therefore **overwrite the
   existing `blk00000.dat` from offset 0**, and the same applies to later files.
3. Chronik starts a new index beside the orphaned RocksDB files.

Step 2 is the data-loss step. I read the write path but did not trace every startup path for a guard,
and **I did not run this**. Test it on a throwaway datadir before relying on it. The baseline LevelDB
binary at `daemon/.build/v1/src/lotusd` can create that datadir.

Rollback is not safe either. The LevelDB files survive unless `-reindex` runs, because
`WipeMdbxFilesInDir` deletes them. But if step 2 happens, those files index block data that has been
overwritten.

**`ecashd` (the later version) is better, but don't copy it unchanged. (Read)**

- It adds `MigrateFromLevelDBIfPresent`. Resuming after a crash during the copy looks fine, because
  LevelDB stays in place until the end and a rerun overwrites the same keys.
- **It doesn't sync before moving the source files.** It commits under `MDBX_SAFE_NOSYNC`, then moves
  LevelDB into `leveldb.bak` with no `mdbx_env_sync_ex`. After a power cut in that window, MDBX can
  roll back to an earlier steady checkpoint while `CURRENT` is already gone. The next start would
  accept a partial database as complete. In a chainstate that means missing coins, which could make
  the node reject valid blocks. Severity high, not reproduced.
- Errors from `fs::rename` are ignored while moving the files.
- `leveldb.bak` is deleted by `-reindex`, and any earlier backup is deleted by the next migration.
- It correctly refuses to open an existing RocksDB Chronik index, with instructions for rebuilding.
  Its commit message records that an earlier version moved the files and returned an empty index.
  V1 needs this refusal, or a real migration. The refusal is the smaller change, since Chronik can be
  rebuilt from block files if they haven't been pruned.
- Its rollback only returns to the state at migration time, and needs hand-moving files. I found no
  tooling or tested procedure for it.

**Core (PR #25) has two-way migration, with bugs. (Read)**

The default stays `leveldb`, and this version does sync before moving files.

- `MoveLevelDBFilesToBackup` moves every file except `mdbx.*`. That includes `base_blockhash` in a
  snapshot chainstate directory, which `node/utxo_snapshot.cpp` reads from that directory. High for
  assumeutxo users.
- `MigrateFromMdbxIfPresent` runs after `leveldb::DB::Open`, which has already created `CURRENT`. So
  `has_backup_mdbx`, which requires `CURRENT` to be absent, can never be true, and restoring from
  `mdbx.bak` is dead code.
- Rename errors are ignored here too. If `mdbx.dat` fails to move, the next LevelDB start destroys the
  newer LevelDB data and re-imports the stale `mdbx.dat`. That silently rolls the chainstate back.
- A crash partway through the file move can leave `CURRENT` beside missing table files, so LevelDB
  would refuse to open until someone repairs it by hand.

### On-disk layout

- **Both formats share one directory, with no format marker. (Read)** `mdbx.dat` sits inside
  `chainstate/`, `blocks/index/`, `indexes/txindex/` and `indexes/chronik/`. The code picks a format by
  which files exist, so an interrupted move is ambiguous. In V1 the old files are simply ignored.
- **Chronik's schema version doesn't change. (Read)** Patch 249 turns the UTXO column families from a
  merged serialized list into one `MDBX_DUPSORT` entry per UTXO, but doesn't touch `chronik-indexer`,
  so `CURRENT_INDEXER_VERSION` stays 13. Nothing separates this layout from later MDBX layouts.
- **Long scripts may stop Chronik from indexing. (Read, effect unverified; potentially high)** The
  script group uses script bytes as the key. Patch 249's own comment puts the limit at about 8,150
  bytes with 16 KiB pages, while RocksDB had no comparable limit. `MAX_SCRIPT_SIZE` limits script
  execution, and as far as I know it doesn't limit output size in a block. A miner could then include
  a valid output too long to be a key. Variable-size `UtxoDataOutput` values in dupsort tables may be
  limited the same way. I found no handling in the PR or in `ecashd`. This needs a Chronik test, and a
  check of existing V1 mainnet scripts against the limit.
- **Page sizes disagree, and can't be changed later without rewriting the file.** `CDBWrapper` uses
  8 KiB in PR #24 and 4 KiB in `ecashd` and Core. Chronik uses 16 KiB in PR #24 and `ecashd`. Choose
  deliberately before any V1 node writes real data.
- **libmdbx versions differ. (Compared)** PR #24 and #25 vendor v0.14.4 under `src/libmdbx/`. `ecashd`
  has v0.13.11 under `src/lotus_v2/vendor/libmdbx/`. So `ecashd`'s fixes have not been tested against
  v0.14.4.
- **The 256 GiB cap per database. (Read, sizes not measured)** I have no measurements of V1 or BTC
  database sizes in MDBX, so I can't say it is enough. A BTC `txindex` is the first place to check.
  Hitting the cap returns `MDBX_MAP_FULL`, which `HandleError` turns into a fatal database error.
- **32-bit. (Read)** `256LL << 30` truncates to 0 in a 32-bit `intptr_t` in V1's C++, and the Rust
  `256 << 30` won't fit a 32-bit `isize`. `release-daemon.yml` lists only 64-bit targets for the
  entries I checked, so this matters little for V1. Core handles it with a 512 MiB branch.
- **Corruption check in `ecashd`. (Read, unverified)** It treats nonzero bytes 150 to 178 of `mdbx.dat`
  as corruption. That depends on the meta page layout and appears written to satisfy `feature_init`.
  Don't port it to v0.14.4 without checking.

## Findings

| # | Sev. | Target | Finding | Status |
|---|---|---|---|---|
| 1 | Critical | V1 | No LevelDB or RocksDB migration; node restarts from genesis and may overwrite block files | Read, not run |
| 2 | Critical | V1 | `WRITEMAP\|UTTERLY_NOSYNC\|NOMETASYNC`: database unusable after a simulated power cut | Experiment, simulated |
| 3 | High | V1 | `MDBX_CHECKING=-1` disables all checks, including `ENSURE()` and panics | Read |
| 4 | High | V1 | Chronik key and dupsort value limits versus long scripts | Read, effect unverified |
| 5 | High | `ecashd` migration, if ported | No sync before moving LevelDB away | Read |
| 6 | High | Core | Migration moves `base_blockhash` | Read |
| 7 | Medium | Core | `mdbx.bak` restore is dead code; ignored renames can cause a stale re-import | Read |
| 8 | Medium | Both | "Unmodified upstream" is true only of the vendor commit | Compared |
| 9 | Medium | Core | Threads are sticky, so an iterator open on a thread may conflict with a read or write on that thread | Unverified |
| 10 | Medium | Core | `struct DBContext` beside the member `DBContext()` may fail on GCC ("changes meaning") | Unverified, no GCC here |
| 11 | Low | Both | `NOTICE` and `COPYRIGHT` not vendored; upstream ships both and the licence is Apache-2.0 | Compared |
| 12 | Low | V1, `ecashd` | `EstimateSizeBytes` returns the whole database size for an empty range | Read |
| 13 | Open | Both | Whether `SAFE_NOSYNC` passes the power-loss experiment | **Not established**, see below |

No fixes were made.

### Crash durability (findings 2 and 13)

Simulated power cut on macOS arm64, 60 images per configuration. Each image combines the file at the
last explicit sync with an arbitrary subset of the pages changed since, with boot ids invalidated.
This is not a real power cut, and nothing ran on Linux.

| Configuration | Power-loss result | Valid? | `kill -9`, 25 rounds |
|---|---|---|---|
| PR #24: patched `mdbx.c`, `UTTERLY_NOSYNC` | 30 failed to open, 30 failed during a full scan, all `MDBX_CORRUPTED` | Yes | 25 of 25 exact committed state |
| Upstream `mdbx.c`, same flags | 60 of 60 failed to open, `MDBX_CORRUPTED` | Yes | 25 of 25 |
| PR #25: patched `mdbx.c`, `WRITEMAP\|SAFE_NOSYNC` | 42 scan errors, 10 exact, 8 wrong state | **No** | 25 of 25 |
| `ecashd` flags: upstream `mdbx.c`, `SAFE_NOSYNC` | 42 scan errors, 10 exact, 8 wrong state | **No** | 25 of 25 |

- **The two `SAFE_NOSYNC` power-loss rows are a harness defect and say nothing about those settings.**
  libmdbx took steady checkpoints at transactions 200 and 203 during the phase I treated as unsynced,
  because the file stayed at 16 MiB. So those images are not states a power cut could produce. The
  matching counts in both rows are a further sign of this. **So `SAFE_NOSYNC` is not shown to be safe
  or unsafe.** The harness needs a fix and a rerun: rebuild the baseline from the newest steady
  checkpoint, or pre-grow the file. That is a small rebuild, so I did not do it after the stop request.
- **The `UTTERLY_NOSYNC` rows are valid.** The checkpoint from the explicit sync was the only one, and
  all three meta pages were weak by the end (`202/1 203/1 204/1`). Continued writes wipe the
  checkpoint, so a sync doesn't protect anything once writing resumes. No silent wrong state appeared
  in these 120 images, though only a full scan was used to detect damage.
- **`kill -9` looks fine** in the harness for all four, because the page cache survives the process.
  This was a small test program, not a node. `feature_mdbx_crash.py` was not ported or run.
- The harness never calls `mdbx_chk`, although it builds it.

**What the node assumes (Read):** V1 fsyncs block files, then writes the block index with sync, then
writes coins without sync (`txdb.cpp:197`). That is safe on LevelDB because a crash leaves a prefix of
the writes, and the node can replay from there. PR #24 breaks this, so the expected outcome of a power
cut is a full reindex, or a resync if blocks were pruned.

`ecashd` uses `SAFE_NOSYNC|NOMETASYNC` without `WRITEMAP`, with 1 s and 16 MiB sync thresholds, a sync
at shutdown, a synced final coins batch, and a fatal error if the block file flush fails. From reading
`env_sync`, a forced sync clears `NOMETASYNC` and the other lazy flags, so an explicit sync should be
fully durable. This is the best available starting point, subject to the rerun above.

### The "unmodified upstream" claim (finding 8)

The four vendored files in patch 248 and in Core patch 02 are **byte-identical** to upstream's
`libmdbx-amalgamated-0.14.4.tar.xz` (SHA-256 prefix `0dd6bf6048d5d208`; I checked V1's copy against
the tarball). But both integration patches then edit `mdbx.c`, with the same hunk, so the library that
ships is not upstream:

- `default_prefault_write` is forced off.
- The default log level drops from `NOTICE` to `FATAL`.
- `meta_wipe_steady` skips its msync under `UTTERLY_NOSYNC`, removing the ordering upstream relies on.
  Core's flags don't reach this branch.
- macOS changes to `HW_MEMSIZE` and `HOST_VM_INFO64_COUNT`. The bug they fix is plausible, but I did
  not confirm it.

V1's CMake also forces `MDBX_CHECKING=-1` and `MDBX_MMAP_NEEDS_JOLT=0`. For the rebase, the first two
edits look replaceable with runtime settings (`mdbx_env_set_option`, `mdbx_setup_debug`), and the wipe
edit should go with `UTTERLY_NOSYNC`. That is unverified. The macOS fix would need upstreaming or a
clearly labelled local patch.

### Other points you asked about

- **Consensus in V1:** the file list changes storage code only, with no validation rules (Read).
  Storage can still affect consensus, since a chainstate with missing coins rejects valid blocks.
- **Core interface commit:** it reads as a behaviour-preserving refactor, and the default stays
  `leveldb` (Read). It was not compiled or tested.
- **Batch and key order:** V1's stable sort with last-write-wins matches LevelDB batch semantics, and
  sorted unsigned-byte order appears to match MDBX's default (Read).
- **Benchmarks: unverified, and the PR contradicts itself.** The PR body says `DBWrapperRead` is 12.10x
  faster and `DBWrapperWriteBatch` 10.86x faster. Its report says 1.11x and about 40% slower. The body
  says 27 column families, the report 22. I measured no performance.

## Built and run

- **Built:** baseline V1 at the unchanged pin: `lotusd`, `lotus-cli`, `test_lotus` in
  `daemon/.build/v1` with `ninja -j12` (exit 0, no MDBX code). These were not run.
- **Run:** only the harness above, compiled against upstream v0.14.4 with and without the PR's `mdbx.c`
  hunk. Results are in `report-macos-arm64.json`.
- **Not done:** no port, no Core build, no `daemon/.build/bitcoin-mdbx`, no unit or functional tests, no
  node-level crash or migration test, no Linux run.
- **Not reviewed:** most of the 2,255-line `db.rs` diff, including the batch and iterator paths and
  `mdbx_batch.c` prefix deletes; a line-by-line diff against `ecashd`'s `chronik-db`.

## Decisions for the owner

1. **Durability versus speed.** I'd rule out `UTTERLY_NOSYNC` on V1: a power cut left the database
   unusable in every simulated image. Choosing `SAFE_NOSYNC` should wait for the corrected experiment.
   The fallback is `MDBX`'s default durable mode, with an unmeasured speed cost.
2. **Chronik on upgrade.** Refuse and require `-chronikreindex` (what `ecashd` does), or build a real
   RocksDB import, which means keeping that dependency. Pruned nodes can't rebuild by reindexing.
3. **LevelDB rollback for V1.** Decide whether a backup at migration time is enough or a tested way back
   is required. Migration also temporarily needs disk space for both copies.
4. **libmdbx version and page sizes.** Decide before V1 data exists in this format. This should also
   settle whether `ecashd` moves off v0.13.11.
5. **Upstreaming to Core.** The Apache-2.0 vendored dependency, the size of the import and the
   process-wide backend global are all likely review questions. I didn't assess how upstream would respond.

## When the rebase resumes

1. Fix the harness and rerun the `SAFE_NOSYNC` rows.
2. Run finding 1 for real, using the baseline binary to create a LevelDB datadir.
3. Test finding 4 with a long-script block.
