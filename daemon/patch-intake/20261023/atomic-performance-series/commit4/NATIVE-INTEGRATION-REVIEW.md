# Native compatibility review for shared Commit4

Read-only review, 2026-10-23. No source edits, builds, tests, ref updates, worktrees or compatibility pools were made. Proposed snippets below are NOT validated source. Root owns review/application and prefix compilation.

Frozen inputs:

- Shared through Commit2: `f3cd28393c0eb436a65f6b1b5f090ec742288cec`.
- Native through Commit3: `c78796a2c7c5c3dc8166e6b68e0c9130ce0d0a64`.
- Tested standalone shared Commit4 delivery: `61ffeaa7ef62f57c08ad14531fbc8dc39e65befa`, on original shared base `cbc4e72925652e3c8676ed0b24fce22874be0dc1`. Root is integrating it onto the newer shared tip separately.

## Complete pool inventory and causal owners

`git grep ParallelScriptWorkerPool::` over all tracked native source finds exactly these four endpoint calls, all in validation.cpp. Native history does not add a fifth endpoint call. It does re-emit two inherited calls in native rewrites, plus relocate the old pool class. These additions must be adapted at their native owners; endpoint-only substitutions are insufficient.

| Native endpoint line | Call/context | Original shared owner | Native owner requiring replay adaptation |
| --- | --- | --- | --- |
| 2499 | `Run(num_workers, worker_fn)` in AcceptRawTxBatch | `beb7c3e2f61f94f63bb66c64882a636bf6e0725a` parallel staged atomic batch scripts | `c6ec6c37f18c77e602939052bd77719049bcccdb` reconcile native batch/block admission: re-emits call while restructuring its surrounding batch/collector code |
| 3460 | `Run(threads, [&](size_t) {...})` in AcceptToMemoryPoolStaged | `ab3a5b89c12b8d907a546b52de1655cde69bb750` staged admission outside cs_main | No native-added call: retain shared C4 adapter at every prefix; native source shifts surrounding lines |
| 5855 | `Run(num_workers, worker_fn)` in ConnectBlock, guarded by `if (n_pool > 0)` | `0d4644d71129f2d61fabda53e6ca2a141360ef2b` legacy Schnorr MSM/cache integration | `79deb7b835ee9b60bcdd4ca4d0e7dfaa7fb41cc8` V2 input checks on script queue: re-emits call under native pool/queue split |
| 8096 | `TryRun(threads, work)` in RunOnValidationWorkers | `1dd8af305ec04bf324bd7b9f1015e0db34ac08d3` block-validation scaling benchmark drivers | No native-added call: retain shared C4 TryRun plus explicit inline fallback at every prefix |

A separate earlier native owner is essential: `af197eafaf4a23fca9ec6311a43310fbc193b5ba` removes the old shared class at its original location and adds it inside an anonymous namespace immediately before AcceptRawTxBatch. The complete class body is byte-identical at shared f3, this native owner and the native endpoint. Extracting from `class ParallelScriptWorkerPool {` through its closing `};` gives SHA256 `12a9245d7f4fd1fd37c267a114876f95cf6b93e6dd87a2f4e7fac1bed23014cc` at all three refs. This is a relocation of already-removed shared machinery, not an independent native implementation. Suppress both obsolete relocation hunks at af197; do not reintroduce class, singleton, threads, an empty namespace or a temporary compatibility pool.

Inventory method: native-range `git log -G 'ParallelScriptWorkerPool::Instance'` identifies only c6ec and79deb; `-G 'class ParallelScriptWorkerPool|ParallelScriptWorkerPool\('` identifies af197. Endpoint blame distinguishes the two native re-emissions from the inherited staged/merkle calls. No source outside validation.cpp references this pool.

## Ordered native replay positions and exact dedup sentinels

Positions are1-based `git rev-list --reverse f3cd28393c0eb436a65f6b1b5f090ec742288cec..c78796a2c7c5c3dc8166e6b68e0c9130ce0d0a64` (154 native commits):

| Position | Frozen owner | Required action |
| --- | --- | --- |
| 13 | `75e6ecd45efbf49cf9f62d3fc4f588342a971f88` | SigningWork API becomes available; preserve its native pool until explicit C5 |
| 32 | `af197eafaf4a23fca9ec6311a43310fbc193b5ba` | Suppress relocation/resurrection of obsolete identical shared pool; preserve shared C4 consumers |
| 50 | `c6ec6c37f18c77e602939052bd77719049bcccdb` | Adapt newly emitted native batch dispatch to tested range/index loop; preserve native RPC decoder's earlier SigningWork dependency/cap16 |
| 94 | `79deb7b835ee9b60bcdd4ca4d0e7dfaa7fb41cc8` | Adapt newly emitted guarded ConnectBlock dispatch; preserve independent queue Complete |
| 154 | `c78796a2c7c5c3dc8166e6b68e0c9130ce0d0a64` | Replace local subtree executor ownership with getter, preserving fourth-argument cap8 |

Safe dedup evidence at frozen position32, `src/validation.cpp` lines1912–2038:

- Envelope starts exactly `namespace {\nclass ParallelScriptWorkerPool {\npublic:`.
- Envelope ends exactly `\n};\n} // namespace`, immediately before `PackageMempoolAcceptResult MemPoolAccept::AcceptRawTxBatch(` after blank separation.
- Complete envelope excluding trailing newline:4215 UTF-8 bytes, SHA256 `b4aecf0ccb2ed6daf3e17365a3f763818ef49bcb64a15a85ed429428d5c2d25b`.
- Class-only sentinel starts `class ParallelScriptWorkerPool {` and ends its first column-zero `\n};`; SHA256 `12a9245d7f4fd1fd37c267a114876f95cf6b93e6dd87a2f4e7fac1bed23014cc` at shared f3, position32 and native endpoint.

Require exactly one matching class and exact expected bytes/hash in frozen incoming source before suppressing it. Fail reconciliation if hashes/counts differ. Do not regex-delete arbitrary anonymous namespaces or any neighboring native code. Because the parent after C4 has no class, classify native's old-location delete as already removed and its moved insertion as obsolete duplicate ownership; retain unrelated native changes in that owner. Verify each rewritten prefix has zero class/name references; the two later native dispatch emissions must be changed at their own positions.

## Minimal adapters using the already-tested range API

The existing Commit4 API suffices. It avoids adding another untested overload during native history reconciliation. Preserve callback bodies and their logical IDs; do not replace an indexed callback with a single `worker_fn(0)` fallback.

At native c6ec's new AcceptRawTxBatch dispatch, use the same tested adapter as shared C4:

```cpp
util::GetParallelRangeExecutor().Run(
    num_workers, 1, [&](size_t begin, size_t end) {
        for (size_t tid = begin; tid < end; ++tid) worker_fn(tid);
    });
```

This invokes every logical ID in `[0,num_workers)` exactly once, including contention/recursion or physical capacity lower than requested IDs. Preserve native worker_collectors allocation, per-workspace produced-record flags, native deferred checks, error ordering, cache/VM context and signature collector merging. Only dispatch changes.

At native79deb's new ConnectBlock call, retain its native guard AND queue completion sequence:

```cpp
if (n_pool > 0) {
    util::GetParallelRangeExecutor().Run(
        num_workers, 1, [&](size_t begin, size_t end) {
            for (size_t tid = begin; tid < end; ++tid) worker_fn(tid);
        });
}
const auto queue_error = control->Complete();
```

Do not move Complete into the pool guard. Preserve queued V2 checks, queued collectors, pool_ks indexing, tx_produced, sigcheck accounting and the deterministic sequential-error reconciliation following completion. This native callback is not interchangeable with the older shared ConnectBlock callback.

For inherited staged admission, retain shared C4's `Run(threads,1,[&](size_t,size_t){ original atomic-next body })`. No per-ID collector exists there, so one dynamic work loop per physical participant is sufficient. For inherited RunOnValidationWorkers, retain the tested range-signature work lambda, `TryRun(max(threads,1),1,work)` and explicit `work(0,1)` fallback. `max_threads=0` still provides one runner, and nested/contended callers never wait for another executor job.

Keep `<util/parallel_range.h>` from shared C4. Native rewrite hunks must not remove this still-used include. No native consensus symbols enter the utility.

## Optional worker-index overload, if root prefers fewer adapter bodies

An additional overload can centralize the loops, but it would be new shared API/source requiring its own compile/util gate before native consumers are replayed. A clear name avoids ambiguity with range semantics:

```cpp
template <typename Fn>
bool TryRunWorkers(size_t workers, Fn &&fn) LOCKS_EXCLUDED(m_mutex) {
    return TryRun(std::max<size_t>(workers, 1), 1,
                  [&](size_t begin, size_t end) {
                      for (size_t tid = begin; tid < end; ++tid) fn(tid);
                  });
}
template <typename Fn>
void RunWorkers(size_t workers, Fn &&fn) LOCKS_EXCLUDED(m_mutex) {
    if (!TryRunWorkers(workers, fn)) {
        for (size_t tid = 0; tid < std::max<size_t>(workers, 1); ++tid) fn(tid);
    }
}
```

`RunWorkers` fallback must iterate every logical ID; invoking only fn(0) drops static chunks in signing/overlay follow-ons. Zero workers intentionally matches old worker API behavior (fn(0) once); range Run(0,grain,fn) remains a no-op. Direct two-argument Run/TryRun overloads could delegate to these helpers, but explicit names make semantics easier to review. This snippet is proposed, not applied/tested.

## Commit3 pool ownership adapter

Native Commit3 owner is endpoint `c78796a2c7c5c3dc8166e6b68e0c9130ce0d0a64`. Its TransactionSubtreeA has `static util::ParallelRangeExecutor executor;`, default maximum8, then `executor.Run(count,1,...)`, where count<=16 occupied prefixes. On replay onto C4 replace only ownership and preserve its physical cap8 explicitly:

```diff
-    static util::ParallelRangeExecutor executor;
-    executor.Run(count, 1, [&](size_t begin, size_t end) {
+    util::GetParallelRangeExecutor().Run(count, 1, [&](size_t begin, size_t end) {
         // Existing occupied-prefix callback body stays byte-identical.
-    });
+    }, /*max_participants=*/8);
```

Keep recursive computation/folding/order/exception behavior from tested Commit3. A hardware-sized common getter without fourth-argument8 would widen this job from8 to16 on larger hosts. Apply this causal ownership adapter at the replayed C3 owner, not as an invisible end-only repair. Shared Commit2 relay needs the analogous cap8 owner adapter; root already owns that integration.

## Native RPC decoder and later Commit5 dependency

`src/rpc/mempool.cpp::DecodeRawTxBatchParallel` intentionally changes at native c6ec. It removes the shared local `ParallelRangeExecutor decoder_workers` and util include, installs a serial `n<32` path, and invokes `lotus::v2::RunParallelSigningWork(n,8,rangeFn)` for larger batches. That symbol's declaration and implementation first exist at native `75e6ecd45efbf49cf9f62d3fc4f588342a971f88` (signing identities/Schnorr tests), before c6ec. Preserve this native decoder transition during C4 replay. Do not reintroduce the shared decoder body, n<=8 cutoff, or duplicate locals as a pool compatibility repair.

Current native RunParallelSigningWork has its own SigningWorkerPool dependency. It computes grain=max(min_grain,1), returns inline below2*grain, then threads=min(hardware,16,ceil(total/grain)); its logical worker callback computes exact floor-based slices `total*t/threads` through `total*(t+1)/threads`. This native RPC path currently caps16, unlike shared decoder cap8. That difference belongs to the preserved native owner and must not be silently normalized in C4. Root should decide any behavior/policy change separately.

Commit5 should retain RunParallelSigningWork's declaration and caller ABI and route its logical chunk IDs through the common getter after removing SigningWorkerPool. The smallest owner-preserving bridge is:

```cpp
util::GetParallelRangeExecutor().Run(
    threads, 1, [&](size_t first, size_t last) {
        for (size_t t = first; t < last; ++t) {
            const size_t begin = (total_items * t) / threads;
            const size_t end = (total_items * (t + 1)) / threads;
            if (begin < end) fn(begin, end);
        }
    });
```

Keep current earlier grain/cutoff/thread-count calculations so cap16 and exact callback slice boundaries survive. The other signing VerifyAll and FirstFailingIndex call sites must similarly invoke every logical chunk ID and preserve earliest-index scans in both native and legacy signature branches. C5 must also replace OverlayWorkerPool separately as planned, including active-shard mapping. No temporary pool with independent threads is justified.

## Promotion and prefix gates

Before rewriting native ancestry, root must preserve frozen inputs in a verified recovery bundle/dirty-state record and retain old refs. Record one ownership-ledger row for af197 suppression of identical moved machinery, c6ec dispatch adapter,79deb guarded dispatch adapter, inherited shared C4 adapters and C3 cap8 ownership adapter. These are reviewed API/ownership compatibility diffs, not a claim of exact tree-preserving reorder.

At each adapted native owner, compile its prefix independently; every subsequent prefix must reference only APIs already supplied by shared C4 or earlier native owners. Require no remaining `ParallelScriptWorkerPool` definition/reference after af197, no duplicate local subtree pool after C3, and preserve all4 callback paths. The native RPC must still resolve RunParallelSigningWork from75e onward and at c6ec's first caller.

Run root's shared/native correctness gates on the final reviewed composition, including util_tests, validation_tests, mempool_admission_tests, txvalidationcache_tests, native/VM/block queue coverage, RPC decoder malformed-tail/first-failure/order checks and mempool_parallel_admission.py lifecycle coverage. Commit5 adds native signing/overlay/mempool/metrics x30 gates. No performance claim follows from these compatibility changes, especially with C4's condition_variable_any control-lock overhead.
