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

## Variant C (added after the A/B plan; user question on persistent workers)
C = A with only the dispatch replaced: process-lifetime pool of min(15, hw) workers behind a mutex/condvar deque (`pool_dispatch.inc`). Same thresholds, partitioning and hash. Join = reclaim-and-run-inline if no worker has started the job, otherwise wait on it, so no deadlock and no help-while-waiting scheduler. Pool construction happens at first use (warm-up, excluded); queue is deliberately not lock-free (<=15 jobs/root). Order rotates through all 6 permutations of A/B/C, 6 reps default. C was written but **never compiled or run** (no window); expect first-compile fixes. `threads_per_root` for C should be 0 in the timed region (workers exist already, counted outside).
A/B stays the primary question; C is adopted only if it beats both with evidence, and would be a separate follow-up patch.

## Variant D (generic persistent pool with growth)
`work_pool.h`: header-only `util::WorkPool` with `Async(f)->Future<T>` (move-only callables, reclaim-or-wait `Get()`, exception propagation), `Post(f)`, and on-demand growth (kept, never shrunk) up to `LOTUS_POOL_MAX` (default 4*hw). D = A with only the dispatch replaced by `WorkPool::Shared().Async(...)`. Prototype of the API intended for later reuse by other call sites (consolidating existing pools would be a separate second refactor; `CCheckQueue` and signature pools stay untouched). Never compiled or run yet. Rotation is 8 orderings of A/B/C/D, 8 reps default. Rule: pool jobs may block only via `Future::Get()`.

## Run (only in an authorized exclusive window)
    daemon/bench/merklix-async-vs-serial/make-variants.sh
    daemon/bench/merklix-async-vs-serial/run-matrix.py benchmark-results/merklix-async-vs-serial-<date>

## Exclusive-window status
Grok's progression run (`benchmark-results/grok-progression-20261022`) is active: point 0 finished, points 374 and 527 (builds + timing) are pending. `daemon/WORKTREES.json` lists its checkout. The host also has unrelated load (load avg ~6, an `explore` loop at 100% CPU, a dart language server). I have no channel to Grok, so a window has not been agreed.

Raw samples now also record first-root wall/CPU cost (including lazy pool
creation), worker creations before timing, and subprocess wall time through
process exit (including teardown, fixture/reference and warm-up). These are
separate observables: subtracting them does not isolate pool teardown. Thread
counts and summary column labels cover all four variants.
## Resume review (2026-10-22)
The historical source pin `657edc0133cac8d54c5570506dad57bf10e300b5`
remains the intended A/B input. Grok's newer canonical progression tip is a
separate source identity; it does not invalidate this historical controlled
comparison. Before running, preserve the pinned source and build inputs under
the canonical task home and set `SRC` explicitly. Do not modify Grok inputs.

Source repairs, not yet compiled: corrected C generator argument and hoisted
its standard includes out of the production namespace. D now freezes worker
growth before shutdown joins, drains descendants on existing workers, joins
an overwritten Future, rejects consumed Get, constrains Async to movable
object results, and falls back to inline execution if initial thread creation
fails. Workers start lazily; cap zero is normalized to one. The pool must
outlive Futures; external submissions must stop before destruction; jobs may
submit descendants while draining but must not destroy the pool. Dependencies
must be acyclic. Post intentionally discards job exceptions. This is still an
experimental framework, separate from the A/B result.

`work_pool_test.cpp` prepares focused gates for move-only values/captures,
exception propagation, consumed Get, nested trees at caps1/2/4, destructor and
move-assignment joining, thread caps, and descendant draining. It has not been
compiled or executed. In a negotiated window: compile/run this gate first,
then build all variants, check every workload against the reference with short
smokes, and only then run the 8-repetition matrix. The matrix requires at least
672 seconds of timed execution plus build/reference/warm-up/drain overhead.
Whole-process RSS includes fixture/reference/warm-up. Warm pool timing excludes
pool construction and shutdown; full-lifecycle pool costs remain a separate
measurement requirement. No performance or correctness-pass claim is made.
