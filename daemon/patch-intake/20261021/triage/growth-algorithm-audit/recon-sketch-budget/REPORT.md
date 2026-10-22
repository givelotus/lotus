# Reconciliation ownership primitives — source checkpoint

Source-only checkpoint, 2026-10-21. No compiler, test binary, daemon or benchmark was run in this lane. The helpers are not integrated into publication, overlay nodes, relay rounds or a scheduler. The epoch/working-candidate lifecycle remains under separate architectural review; these primitives do not select it.

Source worktree: `/Users/shammah/repos/lotus-v2-repair-work/recon-sketch-budget-source`.
Base: `0858ed52a2505d6bb03c09491e9ccf3b20b4ef3f`.
Commits, in order:

* `6af055511e`: budget/domain/cache primitives and nine source tests.
* `01097df102`: move cache helper to the core overlay layer.
* `22021a464d`: const completed-cache publication and bounded shared control-block allocation.

## Integration API

`net/recon_resource_budget.h`, namespace `txrelay`:

* `ReconResourceBudget({bytes, distinct_roots, consumers})`: explicit bounds, no guessed default R.
* `TryReserve(owning_root, complete_root_exposure, work_bytes)` returns a shared RAII reservation or a reason: invalid, bytes, root count, consumer count.
* The same immutable root identity charges complete exposure once; each admitted consumer additionally charges its work bound. Copy the reservation into queued/running tasks. Release it only after those tasks stop and release their private results/buffers.
* A last root owner is destroyed outside the accounting mutex and remains charged until destruction finishes. Bulk clear cannot make an old retained root free for accounting. Root identities use non-null owned pointers; represent empty roots with an owned sentinel.
* Caller-provided root exposure must include reachable nodes, retained bodies and completed-cache allowances. Work bounds must include response buffers, temporary patch nodes, private computation and CAS-loser values. Fixed manager metadata is bounded by configured root/consumer ceilings; allocator overhead remains a separately bounded measurement obligation.

`lotus_v2/overlay_sketch_cache.h`, namespace `lotus::v2::reconcache`:

* A node embeds exactly `std::array<ReconSketchSlot, 2>`.
* `ReconSketchDomain` includes algorithm/version, complete raw epoch identity, k0/k1 and mask.
* One globally owned `ReconSketchDomains` registry selects current/previous domains after the caller validates the epoch. `TryInstall(slot, domain)`, `TryStart(slot)`, `Retire(slot)`, `Drained(slot)` control two fixed slots.
* `Job` is copyable ownership. All copies must drain before a retired slot is replaced. Cancellation prevents new jobs, cache reads and completed publication; existing round membership is outside this helper and may continue exact zoom.
* `cache[job.Slot()].Read(job, summary)` checks the complete domain through a unique token. On a miss, compute privately, then `Publish(job, summary)`; a failed publish does not imply computation failed. No cache state marks an in-progress owner or makes readers wait for it.
* Atomic shared-pointer operations and a short completed-publication/retirement mutex are used. They are not promised lock-free. Computation never holds that mutex, and mempool mutation must not call registry retirement or wait on jobs.
* Cached values contain immutable `{token, count, s1, s3, s5}`. An allocator rebound to the actual `allocate_shared` control block enforces at most 256 requested allocation bytes per completed value. Exactly two slot values are retained per node; concurrent private/loser values belong in worker reservations. Cache tokens are process-wide monotonic and fail closed on exhaustion, preventing stale hits even if a registry is recreated.
* This helper does not compute SIDs or field arithmetic, maintain a SID tree, introduce peer keys, or implement recursive traversal. The parent summary engine walks the existing owned overlay children and uses its existing epoch SipHash/GF routines.

## Authored checks (unrun)

Nine Boost cases cover worker ownership surviving bulk clear/cancel request, shared root accounting, fifth-root deferral without eviction, uint64 overflow, charged destruction outside the budget mutex, delayed jobs blocking rekey/late publication, two fixed slots over repeated rekeys, stale-token registry recreation, and concurrent publication of complete immutable values.

`git diff --check` passed. CMake includes the two implementations in `server` and the new test source in the existing test suite. Native compile/runtime and independent Astra review are required before promotion. No R/default lifetime or performance claim has been validated.
