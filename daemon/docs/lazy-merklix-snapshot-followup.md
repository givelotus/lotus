# Follow-up: slab-backed Merklix snapshots with lazy hashes and incremental MinHash

Recorded 2026-10-22 from the tree/snapshot design discussion. Status: proposed
optimization, not implemented or benchmarked as a unified mechanism. This does
not change consensus hashing, transaction validation, or epoch finality rules.

## Goal

Ordinary leaf lookups and reconciliation updates should maintain the canonical
path-compressed sparse tree without calculating intermediate Merklix hashes.
Snapshots should retain a coherent structural root cheaply. Calculate its dirty
hashes when an epoch boundary, block operation, or reconciliation commitment
actually requires them; do not force unrelated readers to pay that cost.

## Two view states, with hashing requested separately

1. **Writable working view.** Reconciliation may add/remove validated members
   and maintain its MinHash incrementally. Mutate exclusively owned nodes in
   place; copy any shared path before changing it. Ordinary admissions must still
   follow the pending/working-overlay membership rules, rather than leaking into
   a pinned reconciliation target.
2. **Pinned snapshot.** Retain the structural root, membership version, and the
   matching MinHash state. Its membership cannot change while it is advertised,
   served, or hashed. Subsequent working-view changes use copy-on-write. Hashing
   this snapshot fills derived caches, without changing its logical contents.

These are ownership states of one representation, not necessarily two separate
trees or mutually exclusive global operating modes. A working view can advance
while several older snapshots are being read. An advertised root identifies one
exact pinned set; an updated working set is a new candidate/version.

## Candidate representation and lifetime

- Immutable transaction leaves; slab-backed branch slots addressed by compact
  handles. Branch metadata records the canonical prefix/branch position and
  child handles independently of cached digests.
- Invalidate hashes on affected paths. Hash dirty branches bottom-up on a pinned
  snapshot, reusing clean subtree hashes and coalescing repeated changes to shared
  ancestors during a batch.
- Optional hash-to-handle index for completed roots/subtrees needed by the wire
  protocol. This is derived metadata: dirty nodes need not have current entries.
  A published hash must never resolve to subsequently mutated contents. Index
  ownership must participate in lifetime management or use safe weak handles.
- Safe root acquisition and RAII ownership must prevent load/retain races.
  Reference counts, RCU/hazards, and generation-tagged slot reuse need an explicit
  design. A raw atomic root load alone is insufficient. Do not claim formal
  lock-freedom merely because publication uses an atomic operation.
- In-place writes are permitted only under proven exclusive ownership and writer
  coordination. Pinning a mutable root must establish that ownership boundary
  safely. Cached-hash writes also require synchronization for concurrent hashers.
- Current code has separate indexed path-copying overlay arenas and a
  pointer-based reference-counted RPC radix index. Audit reuse and replacement
  opportunities before adding another independent store.

## MinHash requirements

- Specify sketch type, size, deterministic hash seeds/domain, and set semantics.
  Sketch state must describe the same membership version as its snapshot.
- Insertions update the sketch incrementally; duplicate membership must not
  count twice. Batch updates should avoid repeatedly processing common paths.
- Deletions require special handling: keeping only each minimum (or a fixed
  bottom-k sample) cannot always recover the next minimum after sampled members
  are removed. Evaluate auxiliary ordered candidates, composable subtree
  summaries, or a bounded rebuild strategy; measure memory and worst-case cost.
- MinHash is a similarity/fetching hint, not a membership proof or voting
  authority. An advertised sketch is not authenticated by a Merklix root alone.
  Do not let sketch accuracy determine validity or finality.

## Evaluation before integration

Compare against the actual current overlay and RPC read-index implementations.
Measure snapshot capture separately from lazy commitment completion; include
allocation count, admission lock time, lookup throughput, reconciliation update
cost, retained memory, and reclamation pauses. Exercise 5k/100k/500k members,
batched random changes, repeated edits on shared paths, deletes, and long-lived
snapshots. Confirm canonical root equivalence, snapshot stability during writes,
matching snapshot/sketch versions, exact sketch reference results, and safe slot
reuse. Benchmark single-writer ownership first; multiple-writer CAS retries and
per-node locks are design choices to justify, not prerequisites.
