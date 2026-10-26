# Wave 3 radix / conditional-claim review

Status: independent read-only design review. No source mutation, checkout switch, worktree/clone, build, test, model checker or benchmark run. This report is uncommitted for root review. It does not approve the submitted algorithm.

## Frozen inputs and actual current contract

Source inspected using Git objects in `daemon/worktrees/grok-progression-source`, never the changing working files:

- Shared C4 `fec2cab9ce9d8f2ba2bb451ce2bdcdc3a7897830`: `src/radix.h`, `src/rcu.h`, `src/rcu.cpp`, `src/txmempool.h`, `src/node/snapshot.h/.cpp`, `src/test/radix_tests.cpp`.
- Native C4 `8b55e7c8de373d2097da1ebacfcf14fd1098d046` is the planned native consumer boundary. W2 live-map/generalized-map changes are not present at this boundary.
- Equality repair `81fce9de8e2a44d2c3d81dd87fb874d3aed5f8c4` supplies full-width key comparisons. Preserve it; it does not establish multiwriter/snapshot safety.

`ImmutableSnapshotTag` explicitly requires a pinned, stable source: no source mutation in flight, either because it is published immutable or because an exclusive writer lock is held through root sharing. It is not currently a live-snapshot API. The shared snapshot builder obeys that contract: `CaptureMempoolEntriesLocked` holds `mempool.cs`, forks the immutable previous tree, mutates a private builder, then publishes it. Live `mapTx`, `mapNextTx`, parent/child bookkeeping and snapshot dirty state still rely on external mempool writer serialization. The radix stress test covers concurrent mutations, but not the proposed concurrent live snapshot contract.

## Findings requiring correction

### 1. The two-atomic writer gate has a weak-memory exclusion hole

The proposed acquire/release operations do not create one common order across `m_snapshot_seq` and `m_active_writers`. Consider this reduced litmus, initially both zero:

```cpp
// Writer W                              // Snapshot S
seq.load(acquire); // reads 0
active.fetch_add(1, acq_rel);             seq.compare_exchange_strong(0, 1, acq_rel);
a = seq.load(acquire);                   b = active.load(acquire);
// a == 0: enter write                   // b == 0: pin root
```

The outcome `a == 0 && b == 0` is not excluded by the stated C++ orderings. Each acquire can read the initial value of its own atomic; neither reads from the other thread's release. Consequently no cross-thread synchronizes-with edge forces the desired exclusion. This is a memory-model counterexample, not a claimed observed failure on the current Apple machine. Acq_rel RMW is not a universal fence that combines different atomic objects into a sequentially consistent total order. See the primary C++ draft rules for [atomic order](https://eel.is/c++draft/atomics.order) and [per-object modification order](https://eel.is/c++draft/intro.races).

If S shares the root while W has passed an unshared ancestor, W can mutate descendants after the snapshot pins them. Thus even a correct local node-freezing algorithm does not repair this root-pin exclusion hole.

A corrected blocking baseline can use one combined atomic state (exclusive snapshot flag plus active writer count), so reservation and exclusion arbitrate in the same modification order. Writer entry CAS-increments only while the exclusive flag is clear; snapshot CAS-sets that flag, blocks new entries, waits for the existing count to drain, pins the root, then releases the flag. Serialize multiple snapshot owners, define overflow, use RAII release, and prove the memory-order protocol. Alternatively use a fully proved sequentially consistent two-object protocol first, then optimize with model-check evidence. Merely changing one load to acquire is insufficient.

### 2. The suggested design is not lock-free and has no 50ns bound

A paused snapshot owner holding the odd sequence blocks every writer. Concrete freeze-owner stall: B begins cloning shared node N and freezes its children; the last external snapshot then releases N, making N exclusive again; B pauses before publishing its replacement. Other writers reach N, observe `!isShared()`, descend to a frozen child, and restart from the root forever. They do not enter the shared-node clone path and have no descriptor to help complete B's publication. This schedule needs only snapshot release plus concurrent source writers. It is a spin reader/writer gate plus owner-dependent node freezing. That can still be a measured engineering option, but it must not be presented as eliminating coordination or as true lock-freedom.

The wait includes arbitrary in-flight write duration and scheduler delay; pinning the pointer itself being short does not bound the complete operation. Two shared cache-line RMWs on every insertion/removal may become a new throughput bottleneck. Measure the gate separately and under snapshots at realistic cadence.

`get`'s pointer traversal is bounded by key depth, but the public operation includes `RCULock` and reference acquisition/release. Current RCU registration uses a CAS loop, cleanup scans thread records and may destroy retired trees, and thread teardown/grace-period paths use synchronization. Therefore the complete public lookup cannot be advertised as unconditionally wait-free simply because it avoids the new writer gate.

### 3. Freezing direct child slots addresses a real race, but is not a complete proof

Concrete race in the current unmodified algorithm:

1. Tree S and a retained snapshot own node N. Writer B in S observes N shared and starts copying N, reading child slot x into N'.
2. The other snapshot releases its ownership, making N exclusive again while B is still copying.
3. Writer A in S observes N unshared and successfully changes `N.children[x]`.
4. B successfully swaps N' into S's parent slot. N' contains the old x; A's successful update is unreachable.

Freezing N's child slots before reading them prevents that specific CAS from succeeding behind B's copy. Do not claim that the same four-step example still succeeds unchanged after the tag fix.

For writers already below an ancestor, the necessary invariant is stronger: every successful mutating CAS must remain reachable from the committed live root, or must be prevented/retried by a completed freeze on the exact slot it changes. A writer can have passed an ancestor slot before that slot is frozen; the ancestor tag is not an automatic recursive freeze. The proof must cover shared-reference counts rising/falling during cloning, source-snapshot destruction, competing copies at several depths, failed parent CAS, and a writer already deep inside descendants. With a corrected root gate some apparent deep-write counterexamples are prevented by writer drain or preserved shared reachability; I have not proved the complete proposed freeze protocol correct or found a separate decisive deep-write counterexample independent of the broken gate. This is an explicit proof gap, not an invented new bug report.

Restart correctness also requires restoring `level`, `eptr` and expected element together. The existing macro/goto control flow makes omission likely. Prefer a single auditable retry loop/state machine over adding scattered restarts to the macro.

### 4. Tag and lifetime details must be exhaustive

- Mask BOTH const and non-const `getNode` overloads and both leaf access paths. Audit refcount increment/decrement, traversal and destructor paths, not only insertion.
- An empty element is currently raw `1`; its frozen representation becomes raw `3`. It must decode to null leaf, and writers must detect its frozen state before treating it as an insertable empty slot.
- Four-byte alignment is a new generic leaf contract. Enforce it only where involved types are complete, audit every existing instantiation/custom allocator, and preserve allocator rebinding/alignment guarantees. Adding `alignas` to a hypothetical map entry does not prove all T instantiations conform.
- Copy construction may freeze the source, but must never copy frozen tags into a writable clone. Reference increments must exactly match newly owned outgoing edges; failed installation must drop every copied edge exactly once.
- `RCULock` protects lifetime, not snapshot immutability or mutator linearizability. It must be active BEFORE the first pointer load used to acquire an intrusive reference.
- Current `RCULock` is non-nestable (`readLock` asserts `!isLocked`). Admission cannot hold one across an operation and call radix methods that open another. Supply audited `WithinReadSection` variants or narrow the outer pin scope and retain intrusive owners.
- A gate only in `insert` and `remove` is incomplete once `insertOrAssign`, conditional operations, assignment, clear/root replacement and live map wrappers exist. Define concurrency contracts for every mutator; cold `_clear()` is still concurrent with unlocked admissions unless it participates in the protocol. Move/destruction while active operations run requires explicit exclusion/lifetime rules.

### 5. W3-2 needs a precise conditional-operation contract

`insertOrGet` must bind the supplied key to the immutable entry's key; accepting unrelated `key` and `value.getId()` permits inconsistent structure. Return an owned existing leaf under RCU protection. Reuse one implementation core for `insert`, `insertOrGet` and any overwrite method so freeze/gate rules cannot diverge.

`removeIf` must re-evaluate its predicate after CAS failure when another same-key leaf replaces the old leaf. Returning failure just because the CAS saw a new leaf is not sufficient if the predicate was true throughout the operation. Specify a pure predicate safe to invoke repeatedly; it cannot read unsynchronized mutable state. A successful CAS transfers the removed tree-owned reference into the return value without an extra decrement; failed attempts retain no phantom ownership.

Per-node reclamation under RCU prevents allocator address reuse during an active read section, but does not create a unique logical admission owner. Two submissions can share the same `CTransactionRef`; `owner.get() == tx.get()` then matches both attempts. Rollback must use a per-attempt claim token/generation, not transaction pointer identity alone. A previously removed and re-claimed same transaction must not be erased by an older attempt's rollback. This is a caller/protocol requirement in addition to the generic map API. The separate admission reviewer has been notified.

## Corrected implementation choices

Do not silently downgrade the objective to a single serialized writer. Keep the existing externally serialized builder as a preservation/correctness baseline only.

For an initial genuine multiwriter candidate, the smallest easily reviewable proof surface is immutable published nodes plus root-CAS path copying:

1. Pin one immutable published root descriptor under RCU.
2. Build a private replacement path from the pinned root, sharing immutable untouched subtrees; batch sorted updates to copy common ancestors once and allocate nodes from the existing slab.
3. CAS the root descriptor to commit. On failure discard the candidate references and retry/rebase against the winning root.
4. Snapshot acquisition only pins the immutable root descriptor. No writer drain or in-place published-node mutation is needed.
5. Include a unique publication generation/descriptor identity and safe reclamation so an old descriptor cannot be republished as an unrelated generation. Define linearization at successful root CAS; no-op cases need their own linearization points.

This has one contended root and allocation/retry amplification, so it is a correctness-first MULTIWRITER candidate to benchmark, not a prediction of 500K TPS. Full API lock-freedom also depends on actual atomics, allocation and reclamation; measure CAS retries, nodes copied, refcount traffic and retained bytes. Do not remove path copying on exclusively referenced published nodes without introducing and proving a generation protocol.

If root contention becomes limiting, independently evaluate a proven concurrent-trie/generation/indirection design rather than extending ad hoc tags. The original [Concurrent Tries with Efficient Non-Blocking Snapshots paper](https://chara.epfl.ch/~prokopec/ctries-snapshot.pdf) explicitly addresses ancestor/descendant lost updates through indirection and provides atomic snapshots. It is a relevant source design, not a drop-in patch or evidence that this radix code already has those guarantees.

A corrected combined-state writer gate can remain an optional comparison experiment. Label its blocking behavior honestly and keep it separate from the immutable-root-CAS design; do not hide a global writer serialization behind a lock-free name.

## Direct architecture comparison and precise progress scope

| Design | Published state / write commit | Snapshot pin | Owner pause / contention | Review position |
|---|---|---|---|---|
| Existing private builder under external writer lock | Mutable private builder, immutable after publication | Stable-source intrusive root copy, no grace period | Builder serializes writers; published readers proceed | Preserve as correctness baseline; it does not satisfy concurrent-commit objective |
| Submitted mixed mutable/frozen nodes plus drain gate | Leaf CAS after in-place descent, occasional shared-node copies | Stops new writers and drains old ones before root ref increment | Snapshot owner blocks all writers; frozen-exclusive owner pause can prevent writer progress; submitted weak orders fail exclusion | Do not implement verbatim or call lock-free |
| Corrected combined-state gate plus proven freeze protocol | Same mixed update strategy, but exclusion arbitrates on one atomic | Same drain-and-pin operation | Still blocking; gate may wait for arbitrary writer/scheduler time | Optional independently benchmarked comparison only; complete descendant reachability proof still required |
| Immutable published nodes plus private path copy / root CAS | Build complete candidate privately; successful root CAS is whole-map write linearization | Load immutable root descriptor and take owned reference inside RCU section | Failed writers retry after some other publication succeeded; paused private builder does not block others | Smallest genuine concurrent-publication candidate to implement/prove first |
| Generation/indirection trie with helpable operation descriptors | Fine-grained commits validated against root generation; visible incomplete operations can be completed/aborted by helpers | Publishes/pins a new generation without draining every writer | Can avoid owner-dependent freezes, but needs complete descriptor/renewal/reclamation proof | Larger follow-on design if measured root-CAS contention requires it; not a few-tag amendment |

For immutable-root CAS, no writer exposes partially initialized nodes. The candidate descriptor contains a complete root and generation; release publication and acquire lookup expose fully initialized immutable contents. A snapshot retains exactly the descriptor it acquired, even if the live root changes immediately afterward. Its acquisition performs one root load and one intrusive reference increment under RCU, independent of transaction count; closing the current RCU read scope may perform deferred cleanup, so public-call wall time is not a strict constant bound in this implementation. No eager leaf traversal, rehash or global writer drain belongs in acquisition.

A snapshot of the immutable-root design linearizes at the root load whose live descriptor it retains, provided the RCU section starts before that load and object lifetime/root publication rules prevent descriptor ABA. If the API permits old descriptors to be republished, add a fresh publication descriptor rather than recycling a logical generation. Snapshot destruction and long-lived pins can postpone reclamation and raise retained memory; this is not a reason to recycle still-reachable slab slots.

The root-CAS UPDATE ALGORITHM is lock-free only under the usual explicit assumptions: lock-free target atomic, finite bounded nonblocking candidate construction/allocation and reclamation operations, and no external lock needed by callbacks. Each failed strong CAS witnesses a competing publication; a descheduled writer whose candidate is still private leaves no published obstruction. The existing allocator/RCU implementation must be audited before claiming the entire public API lock-free. A normal root descriptor is already fully committed, so this simple design needs no helpable pending descriptor; helping becomes necessary if an alternative exposes a multi-step pending/frozen operation in shared state.

One root cache line may limit multicore throughput. Record successful/failed CAS counts, private path construction retries, copied nodes and bytes, refcount operations, allocator stalls and snapshot-held bytes. Batch disjoint sorted updates into one candidate to share copied ancestors and one publication, while keeping batch/package semantics explicit. A Ctrie-style design may reduce root contention, but a radix-only proof does not make input claims, membership, counters and transaction publication across several indexes one atomic mempool commit.

## Required deterministic validation before promotion

Random 8-writer/2-snapshot stress is useful but insufficient. Add a serial-history/linearizability oracle and deterministic barriers around these events:

- Writer paused after passing an unshared root; snapshot attempts to pin; snapshot contents remain stable after the writer resumes. Include two snapshot owners.
- Shared node clone paused after reading a child; last external snapshot releases; competing writer mutates that child; reproduce the pre-fix lost update and prove the chosen replacement design prevents it.
- Writer paused two or more levels down while an ancestor copy/freezing proceeds. Exercise same and disjoint descendant slots and snapshot destruction/recreation. Verify each successful write is reachable and every retained snapshot has one consistent immutable content set.
- Freeze owner paused before publication. Demonstrate the submitted blocking baseline stalls (and label it), or require the genuine lock-free candidate's other threads to help/continue.
- Frozen empty/node/leaf decoding, failed clone CAS at each level, exceptions/allocation failure before publication, and exact destructor/allocation accounting after all external owners release.
- `insertOrGet` many contenders: exactly one winning attempt, all others get its value; remove/overwrite/reinsert interleavings and `removeIf` predicates changing with a same-key replacement. Include two attempts sharing one transaction pointer but different claim tokens.
- Public API RCU nesting rules, snapshot copies of snapshots, source destruction with surviving snapshots, clear/assignment concurrent-operation contract, and slab reuse only after a grace period. Call `RCULock::synchronize()` only after exiting read sections and joining relevant threads.

Model-check a minimal publication/gate litmus using Relacy/CDSChecker or equivalent C++ memory-model tool; execute sanitizer builds and arm64/x86-64 stress later under root's host schedule. TSAN does not prove the all-atomic ordering or linearizability properties. No model check, sanitizer run, stress test or new throughput result was performed for this report.
