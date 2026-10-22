# Merklix TransactionSubtreeA: std::async vs serial

**STATUS: harness prepared, NOT yet measured.** No compile or benchmark has been run, because no exclusive host window exists (see below). No performance claim is made.

## Verified identity (read-only checks, no CPU-heavy work)
- Canonical manifest: `benchmark-results/grok-progression-20261022/manifest.json`, candidate commit `c7cf36456179e9a7ccdae3be03a749d3f07c8bda`, manifest sha256 `acc5bc80bde249d4f624da7ea9deb54a332e53507eb2b7e6539fb492b8de537d` (as recorded by Grok's checkpoint; I did not recompute it).
- `/Users/shammah/repos/lotus-v2-repaired-source` HEAD `657edc0133cac8d54c5570506dad57bf10e300b5`, tree `9a06a5a1c13780ae91390c4407ad90fefd35bbea`, clean. This equals manifest entry 527 (final V2) exactly.
- `src/lotus_v2/commitment.cpp` sha256 `06e16b3fc6ce2a60832fdf00aa76b7ec639d53e7c93201344a4b3c679e628bba`; it already contains the span-partition change (`7e2b98f01a`).

## Actual parallelism thresholds (read from source, lines 71-96)
Async launch iff `depth < 4 && entries.size() >= 64 && !left.empty() && !right.empty()`; `std::launch::async` on the LEFT child, right child runs on the caller, then `future.get()`. So at most 1+2+4+8 = 15 threads created per root, only when both sides are non-empty. Keys concentrated in a few prefixes get one-sided splits and therefore fewer/no spawns at depths 2-3.

## Design
- A = byte-identical copy of production `commitment.cpp`. B = same file with `false &&` prepended to the single dispatch condition (one-line diff, enforced by `make-variants.sh`). Same harness object, tagged_hash, BLAKE3 lib, flags (`-O3 -DNDEBUG`, system allocator).
- Timed: whole `BuildTxSubtreeA` call (pointer-array allocation, partition, thread create, join, future destruction). Not timed: fixture, reference check (independent recursive vector implementation, checked before timing, and root printed), warm-up (3 roots), process start.
- Samples: one process each, >=1.5 s, >=7 repetitions, A/B order alternated; wall, process CPU (getrusage), peak RSS, `pthread_create` count via dyld interposition; concurrency cases use 4 and 16 caller threads.

## Run (only in an authorized exclusive window)
    daemon/bench/merklix-async-vs-serial/make-variants.sh
    daemon/bench/merklix-async-vs-serial/run-matrix.py benchmark-results/merklix-async-vs-serial-<date>

## Exclusive-window status
Grok's progression run (`benchmark-results/grok-progression-20261022`) is active: point 0 finished, points 374 and 527 (builds + timing) are pending. `daemon/WORKTREES.json` lists its checkout. The host also has unrelated load (load avg ~6, an `explore` loop at 100% CPU, a dart language server). I have no channel to Grok, so a window has not been agreed.
