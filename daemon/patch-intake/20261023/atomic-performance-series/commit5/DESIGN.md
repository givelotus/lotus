# C5 plan: consolidate native overlay and signing workers

Status: READ-ONLY PLAN. No source edits, checkout switches, new worktrees, builds, tests or benchmarks. Host belongs to root's native C4 gate. This is authorized Wave1 only; no Wave2 implementation is included.

Exact reviewed native C4 input: `8b55e7c8de373d2097da1ebacfcf14fd1098d046`, tree `2ac7093521dcf926c15eb9b77babb881ddff771a`. Root must finish its C4 gate and assign the implementation checkout/base before mutation. Current executor lane stays on its existing committed shared C4 checkout.

## Concrete change

Remove `OverlayWorkerPool` in src/lotus_v2/mempool_overlay.cpp and `SigningWorkerPool` in src/lotus_v2/signing.cpp. Add `<util/parallel_range.h>` to each. All seven existing dispatch sites (two overlay helpers plus five signing sites) submit to the SAME `util::GetParallelRangeExecutor()` already supplied by C4. No new static executor or compatibility pool, queue, generic index API, node-thread dependency, protocol/data-structure change or deferred-admission preparation work is needed.

Keep callback bodies and existing logical worker/chunk calculations. Adapt every indexed dispatch with a range over logical IDs:

```cpp
util::GetParallelRangeExecutor().Run(
    logical_threads, 1, [&](size_t first, size_t last) {
        for (size_t t = first; t < last; ++t) original_callback(t);
    });
```

When the existing callback is inline, retain its original body inside that loop. These logical IDs are NOT physical worker IDs. The common pool may run fewer physical participants, especially for explicit signing requests above hardware; its range callback still covers every logical ID exactly once. On contention or same-executor recursion, Run invokes the complete logical range on the caller. Thus the adapter loops every index: substituting only callback(0) would drop static chunks and can accept unchecked signatures or omit overlay updates.

Overlay's dynamic active-shard helper can keep its existing atomic-next loop as the range callback, ignoring its begin/end parameters. That preserves work assignment and visits every active shard. A static mapping rewrite is unnecessary for C5.

## Exact source inventory / guards

| Source | Frozen blob | Class-only removal bytes / SHA256 |
| --- | --- | --- |
| src/lotus_v2/mempool_overlay.cpp | `a3bcf64addbd7a983bd3847f2d42599f5a69adc3` |3241 / `89a7c8bc0a82c18a39d01596a6fee023646376673e347f9dfebde8cfec5a9b2f` |
| src/lotus_v2/signing.cpp | `45560ac20a275a18619225d0329d6804c24a38e7` |3241 / `8fe946db499c31a6b443d1aacdd46a7c7825cfdb8d10cf69d8dd11add35e3eba` |

Class-only slices start exactly `class OverlayWorkerPool {` / `class SigningWorkerPool {` and end at the corresponding column-zero `\n};`, excluding its trailing newline. Assert exactly one match and expected bytes/hash before removal. Keep surrounding anonymous namespaces and all neighboring functionality. No history rewrite is needed to introduce this distinct feature commit.

Overlay endpoint dispatches: lines166 and200. Range helper consumers (all current min_per_thread32): lines617,626,979,1555,1564. Shard helper consumers: lines655,835,1018,1392,1617,2007. These paths cover sparse UTXO updates, transaction preparation, persistent overlay batch mutation and shard folding; final root composition stays after synchronous worker drain.

Signing endpoint dispatches: VerifyAll native952 / legacy975, FirstFailingIndex native1002 / legacy1036, RunParallelSigningWork1072. Its public declaration in signing.h remains unchanged. Native RPC mempool.cpp:1268 is the sole RunParallelSigningWork caller outside signing.cpp; do not edit its decoder algorithm/cutoff/wire/error logic.

Remove unused condition_variable/mutex includes from both files only if final usage audit confirms none remain. Overlay's functional include also becomes unused; signing retains functional for its public callback definition. Both retain thread for hardware_concurrency and atomic for existing work/error state. No broad formatting cleanup.

## Preserve exact caps and range geometry

| Helper | Existing behavior to preserve |
| --- | --- |
| Overlay ParallelForRange(count,min_per_thread) | zero count returns; hardware>=1; max_threads=min(hw,16); needed_threads=(count+min_per_thread-1)/max(1,min_per_thread); num_threads=min(max_threads,max(1,needed)); one thread calls fn(0,count); otherwise chunk=ceil(count/num_threads), worker t handles [t*chunk,min(count,(t+1)*chunk)) if nonempty |
| Overlay ParallelFor16Shards | active_list enumerates shard IDs0..15 in order; empty returns; singleton executes directly; num_threads=min(active_count,hw,16); dynamic atomic next_idx maps into active_list and each active shard runs once |
| Signing EffectiveBatchThreads(total,requested) | total<32 returns1; requested==0 selects min(max(hw,1),16); requested>0 is NOT capped16 or hardware here; final logical threads=min(selected,ceil(total/16)). Preserve this explicit-request distinction |
| VerifyAll / FirstFailingIndex | partition item arrays by exact floor boundaries total*t/threads and total*(t+1)/threads; retain logical thread count, native/legacy branches, early-invalid atomic and ordered chunk scan |
| RunParallelSigningWork(total,min_grain,fn) | zero returns; grain=max(min_grain,1); total<2*grain calls inline; otherwise logical threads=min(max(hw,1),16,ceil(total/grain)); preserve exact floor-based callback slices and single-thread path |
| Native RPC decoder | n<32 serial cutoff; invokes RunParallelSigningWork(n,8,fn) above cutoff; current cap16 is intentional native behavior, unlike shared decoder cap8; preserve16 |

The common singleton's physical limit remains hardware, with defaults also bounded by the logical count passed to Run. Thus overlay/default signing/signing-work caps stay16; no additional fourth-argument cap is required when dispatching the already-capped logical count. Explicit VerifyAll/FirstFailingIndex requests can remain larger LOGICAL counts while physical participants are hardware-bounded, without losing any callback indices. No attempt to spawn extra workers to match those explicit requests.

Potential preexisting edge cases (e.g. overlay's numerator with min_per_thread0, very-large-size arithmetic) are outside C5; current consumers all pass32. Do not fold unrelated arithmetic/API policy changes into the pool consolidation.

## Safety / lifecycle requirements

- No blocking acquisition of shared dispatch: C4 TryRun failure causes Run's caller fallback. Nested overlay/signing work on the common pool executes inline, avoiding self-wait. Cross-subsystem contention must similarly complete on its caller while another task owns the pool.
- This proves only executor dispatch behavior, not arbitrary user-callback deadlock freedom. Callbacks must not wait for outer application locks; preserve current lock scopes and disjoint slice/shard ownership. Overlay callbacks write independent elements/shards and final fold reads only after Run drains.
- Every logical chunk ID is invoked once. FirstFailingIndex must preserve native-before-legacy ordering and the legacy base offset items_.size(), deterministic smallest failing index and bisection within first failing chunk. Keep chunk_ok as vector<uint8_t>, not vector<bool>.
- Keep VerifyAll's native/legacy signatures, randomizer/cryptographic checks, cancellation/error behavior and const collector lifetimes. Do not weaken existing tests or assertions. Common executor drains every participant and transports callback exceptions to the submitter.
- The process pool owns worker threads and joins at process teardown after callers stop; removed private pools no longer each own N-1 threads. Final grep must find no OverlayWorkerPool/SigningWorkerPool definitions or references and no local replacement executor in these files.
- C4's annotated StateLock/immutable Job design remains unchanged. Adding the utility header must not add NO_THREAD_SAFETY_ANALYSIS or other suppressions; preserve native locking annotations. No mutable executor control state is added in native files.

## Concrete tests to add

Use public native APIs and actual common accessor; avoid exposing private helper APIs just for testing. Prefer extending existing fixtures/data generation to keep expensive signature setup bounded.

1. RunParallelSigningWork range/ownership test in lotus_v2_tests: uneven count257, grain8; collect exact visits and callback boundaries. Assert one visit/item and original floor-based partitions for native cap16/hardware. Check zero, below-cutoff and uneven counts. For explicit ownership proof, hold a common pool dispatch on a helper thread using promises, invoke signing work on test caller, assert all nested callbacks execute on that caller and all items are covered. Skip only parallel-contention-specific expectation on hardware<=1; retain coverage assertions.
2. Recursive signing-work test: invoke RunParallelSigningWork inside a GetParallelRangeExecutor().Run callback; compare callback thread to its immediate outer caller, exact item visits, and completion. Also throw from an inner range callback and verify exception reaches outer submitter after all dispatched participants drain, then a subsequent job succeeds. Assert thread-local activation unwinds correctly through repeated nested calls.
3. Extend v2_nullfail_and_batch_sig_collector to invoke valid/corrupt VerifyAll and FirstFailingIndex inside common-pool callbacks (and under deterministic external contention). Cover both native and legacy arrays, corruptions in separate chunks, earliest of two failing native indices, native-priority versus legacy offset, and a legacy-only collection. Test requested thread counts1,4,default0 and a logical request above hardware when item count is sufficient; expect identical truth/failing index. This catches dropped nonzero logical chunks during fallback.
4. Extend overlay tests using existing seeded batch-vs-serial fixtures: normal, nested-common-dispatch and externally-contended modes on independent overlay instances, with enough inputs (>=65, preferably existing larger fixture) to cross grain32 and populate all16 shards. Compare exact UTXO/transaction roots, counts and lookup results after insert/erase, remove/readd and batches. Existing batched_inserts_match_serial_inserts_while_growing and monaddb_16_shard_parallel_merklix_and_prefetch are good reusable fixtures. No shared mutable overlay between test threads.

Contention harness must be deterministic and cleanup-safe: helper starts a >=2-participant common dispatch, signals entry, then waits for release. Execute consumer on a second bounded helper future if necessary; if it fails to finish promptly, release blocker and join both BEFORE reporting failure, preventing a failed assertion from leaving the suite hung. Use RAII release/join on exceptions. For new tests, collect atomic mismatch counters in worker callbacks; make Boost assertions on the test thread after join, rather than depending on assertion framework thread safety.

## Build / warning / correctness gates after root grants slot

1. Freeze exact C4 base/source hashes and reviewed diff; preserve prototype in canonical commit5 before build. Reuse assigned/registered checkout only, no extra worktree/clone/replay repo.
2. Release -j10 using the recorded Chronik-OFF baseline flags. Build native daemon/CLI/test targets. Capture configure/build/cache/compiler/source identities and elapsed build time. Compare warning file+message counts against root's exact native C4 logs, normalizing source line shifts. All new warnings fail; preserve inherited warnings and verify blob identity for unchanged warning sources. Pay special attention to header instantiation thread-safety diagnostics in native signing/overlay, shadow/sign conversions in loop adapters and test captures/lifetimes.
3. Immediate mandatory unit gates: lotus_v2_tests, mempool_tests, metrics_tests repeated30 times. Add mempool_overlay_tests because it directly exercises every migrated overlay family, plus util_tests to retain common recursion/exception/participant-limit coverage. Existing mempool tests include deferred-overlay remove/readd, randomized rebuild parity and contended warm-reader behavior; metrics tests have exact threaded counter/sample-drop accounting and must not be loosened for stress passes.
4. Run native RPC decoder acceptance coverage from root's existing native C4 suite/functional manifest, including malformed batch errors/lowest failing position and n31/n32 threshold. Run isolated mempool_parallel_admission.py with own build/config/temp/cache/ports for script/overlay/shutdown lifecycle. Native signing standalone test can additionally run using its existing signing_test CMake target with -Werror and the exact local secp archive if root requires; src include path already admits util/threadsafety, no production node dependency is added.
5. Preserve all results, dirty-source export before any corrective history work, exact source/binary/config hashes, source commit patch and verified recovery bundle. Commit this one logical native pool-consolidation feature only after gates. No remote push, publication, history rewrite, adoption or throughput claim without root action.

No benchmark run is necessary for correctness promotion. Any performance claim would require >=3 alternating before/after pairs, isolated host and exact workload/source identity. Existing test-emitted BIP340 timings are diagnostic output, not controlled benchmark evidence. The shared condition_variable_any overhead and changed contention behavior make inference from thread count alone insufficient.
