# Commit4: common range executor, review prototype

Status: PASS; committed candidate 61ffeaa7ef62f57c08ad14531fbc8dc39e65befa. Build,90 targeted unit cases and isolated admission functional pass. No performance claim.

The shared util::ParallelRangeExecutor retains Run(count, grain, rangeFn) and adds TryRun(count, grain, rangeFn). TryRun returns false without invocation on same-executor recursion or concurrent multi-participant dispatch. Run then invokes the entire range inline. Workers transport exceptions, drain before rethrow, and join at destruction. Nonblocking dispatch avoids waiting for another executor job while holding caller locks; arbitrary blocking inside callbacks still requires an independent lifetime/locking audit.

The inline GetParallelRangeExecutor() accessor owns one process-lifetime pool shared across translation units. Capacity is hardware_concurrency, matching script parallelism; individual callers continue selecting work/grain. Optional fourth max_participants argument defaults to unlimited within pool capacity; preserve cap8 relay/decode with Run(count, grain, rangeFn, 8). Directly constructed ParallelRangeExecutor instances remain supported for isolated unit tests. Singleton destruction requires all client threads to be joined before static teardown, as the previous private singleton did. Pool creation is lazy at accessor use, but all bounded worker threads are initialized once.

validation.cpp removes ParallelScriptWorkerPool. Worker-index call sites dispatch the logical range [0,num_workers) and invoke every prior worker ID once, preserving collector indices/count even when physical worker capacity is lower. Staged admission uses its existing atomic task allocator from each participant. RunOnValidationWorkers retains an explicit TryRun/inline fallback, including max_threads=0 behavior (one inline runner).

No new shared code depends on Lotus consensus. Existing shared-history validation.cpp itself already contains lotus_v2 calls; the changed call sites include AcceptRawTxBatch collectors and ConnectBlock collectors. Native validation.cpp must receive the corresponding worker-index adapters if its diff context differs; do not omit these just because shared code builds.

## Required integration ownership adapters

- Commit2 net_processing.cpp local static relay executor must become util::GetParallelRangeExecutor(), retaining cap8 with the optional fourth Run argument; separate current local instances would still duplicate threads.
- Commit3 src/lotus_v2/commitment.cpp local static TransactionSubtreeA executor must use this accessor once Commit4 is present. Commit3 stays independently buildable before this dependency.
- Commit6 SHORTTX decode must use this accessor.
- Commit5 removes OverlayWorkerPool and SigningWorkerPool separately. Overlay ParallelForRange needs exact range coverage and its current minimum-grain/16-cap policy reviewed; ParallelFor16Shards needs active-shard index mapping. Signing VerifyAll/FirstFailingIndex need all logical chunk IDs invoked, original deterministic earliest-index scan, both Schnorr/legacy branches and collector lifetime preserved. Use range loops over chunk IDs so contended/recursive inline fallback still processes every chunk (simply calling old callback with index0 would silently drop chunks). Native tests, mempool tests and metrics x30 belong to Commit5.

## Gates after host slot

Use the point378 BUILD.json Release, Chronik OFF flags, -j10. Capture configure/build logs and cache hash, binary SHA256 and source tree identity. Compare warnings with baseline; strict clang thread annotations unchanged. Run util_tests, mempool_admission_tests, txvalidationcache_tests and validation_tests (fixture suite; initial AUTO-only search missed it). New util cases check explicit TryRun contention with no callback invocation, recursion rejection, exact logical-index coverage, worker exception transport and reuse after failure. Existing persistent TLS reuse, Run recursion and contended caller tests remain.

After gates pass, commit one logical change using requested committer identity, export format-patch and verified recovery bundle into this intake, record commit/tree/hashes and push status (no remote push). Root integrates; prototype is not integrated.

## Clang lock-analysis structure

The utility includes only threadsafety.h for annotated StdMutex. Nested StateLock is a condition-variable-compatible scoped RAII adapter over std::unique_lock<StdMutex>; constructor/destructor and lock/unlock carry capability annotations. m_job, remaining, generation, error and stop are GUARDED_BY(m_mutex). State-acquiring APIs carry LOCKS_EXCLUDED; CV predicates require the state capability explicitly. Execute operates on immutable Job snapshot copied under state lock, avoiding unlocked reads of guarded members. No blanket suppression or sync.h/node dependency is introduced. Existing validation annotations remain unchanged.

condition_variable_any replaces condition_variable so it can wait with the annotated custom lock. Its implementation can add internal synchronization/allocation overhead; paired measurements are required before any performance claim. m_dispatch remains a standard nonblocking dispatch mutex: no mutable job data relies on it alone, so state fields are protected by analyzable m_mutex.

Publication: dispatcher owns m_dispatch, writes job descriptor/error/remaining/generation under m_mutex, then notifies. Workers observe generation and snapshot Job under m_mutex. All participants execute immutable descriptor outside control lock; each background worker decrements completion under m_mutex after Execute. Caller waits for zero before clearing descriptor or propagating error. Constructor finishes m_workers before external use; destructor requires all submitting callers already joined. Error and stop use state lock, recursion activation is TLS.

Verified delivery: DELIVERY.json; source commit/export and incremental bundle preserved in this directory. No remote push. Root integrates the candidate; local ownership adapters remain explicit.
