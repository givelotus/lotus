# Current primary mempool versus immutable read views

Read-only source audit at `a429917c018437d38f684c2a6bb5b839a0437157` in `~/repos/lotus-v2-repair-work/recon-storage-latest-source`. No source changes, compiler, benchmark, node or cache operations. The coordinator reports the normal native Chronik-ON build and overlay checks passed on this candidate; this audit did not run them independently. The final normal gate also passed RPC snapshots, Lotus V2, standalone block assembler and preconsensus batch suites; endpoint performance and protocol convergence remain separate.

## What the candidate actually implements

It **does not** replace the mutable primary mempool with one CoW primary from which all readers retain the current root. Three structures remain:

| Structure | Role and ownership | Writer behavior |
|---|---|---|
| `CTxMemPool::mapTx` | Primary mutable Boost.MultiIndex container of `RCUPtr<CTxMemPoolEntry>`. Has hashed TxId, modified-feerate, entry-time and entry-id indexes. Entries retain shared immutable CTransaction bodies but mutable fee/dependency/finality bookkeeping. | Mutated under mempool.cs; transaction admission and chain changes also hold cs_main. Container nodes use the existing single-lock ChunkedSlabAllocator. |
| `node::MempoolSnapshotTree` | Separate numeric-order ABC radix read index with immutable `MempoolEntrySnapshot` values. Each value shares the CTransactionRef, but copies fee/time/edge/unbroadcast metadata. | Capture copies a published tree root O(1), then path-copies shared radix branches and replaces changed entry snapshots. Unshared private builder branches may be updated in place until publication. |
| Existing transaction `TxOverlayArena` | Canonical LSB-first TxId/TxHash membership/commitment structure. This candidate replaces its mutable vector backing with independently owned immutable path-copied nodes. | Publication applies final mapTx identity deltas; owned roots pin O(1), unchanged nodes/bodies/completed hash values are shared. It remains derived from mapTx, not its replacement. |

Source: `src/txmempool.h:293` through `343`; `src/kernel/mempool_entry.h:56`; `src/node/snapshot.h:108` through `148`; `src/lotus_v2/mempool_overlay.h:77` onward; `src/txmempool.cpp:508` onward.

The completed canonical/numeric publication tuple pairs a root, numeric generation and membership sequence. A relay capture extracts only its owned canonical root and sequence, then releases the tuple; it does not retain the numeric tree or RPC snapshot. The 1,024-entry RPC ring retains numeric generations but deliberately no canonical graph. This solves the canonical pin/lifetime problem without unifying primary/read-index maintenance.

Source: `src/node/snapshot.h:138`, `294`; `src/node/snapshot.cpp:1028`, `1260`; `CTxMemPool::PublishCanonicalTransactionMembership`.

## Lock, allocation and retirement facts

* Numeric capture and canonical path copying happen under mempool.cs. Admission normally already holds cs_main. These operations are not moved to a background worker by this repair.
* Numeric snapshot values and radix nodes use the concurrent slab allocator. Canonical nodes/control blocks and completed Hash values do too. Fast magazine hits avoid heap allocation, but empty magazines refill under a pool mutex, and slab chunk allocation may call the heap on the same requesting thread. Since publication runs inside admission locks, **refills can still occur under mempool.cs and cs_main**. There is no unconditional zero-malloc-under-lock guarantee.
* `mapTx` and `mapNextTx` still use their separately protected chunked slabs. This is not the same allocator ownership model as independently reclaimed read nodes.
* Numeric nodes/values use intrusive RCUPtr reference counts. Last release registers an RCU cleanup; RCULock destruction invokes ready cleanup callbacks on that thread. Cleanup storage itself uses a per-thread map of callbacks. Retirement is not an automatically dedicated asynchronous reclamation thread, and ready destruction can run while the caller still holds admission locks.
* Canonical nodes use ordinary shared ownership. The final release synchronously destroys uniquely owned descendants, cached Hash values and body references on the releasing thread. A writer replacing a root or current tuple may perform those releases under its locks; a reader may perform the final release after dropping its pin. No dedicated deferred canonical-root retire queue is introduced. Bulk clear can make a large old graph eligible for synchronous reclamation if nobody else pins it.
* RPC publication uses an atomic shared_ptr operation and the publisher's writer mutex. “Does not take cs_main/mempool.cs on reads” is the precise claim; the C++ shared_ptr atomic operation is not universally guaranteed hardware lock-free.

Source: `src/radix.h:93`, `190` through `208`, `386` onward; `src/rcu.h:64` through `79`, `239` through `251`; `src/rcu.cpp:208`; `src/support/allocators/chunked_slab.h:482`, `585`, `633`; canonical `TxNodeAllocator`/`TxOverlayNode::~TxOverlayNode`; snapshot publisher `Publish`.

## What is actually coalesced

Dedicated submitrawtxbatch wraps package admission in ScopedSnapshotDefer. The phased transaction-batch path also defers publication for its batch. These paths reduce the number of publication tuples.

Ordinary queued individual RPC submission is different: `RpcAdmissionDispatcher::Impl::Run` drains a slice and holds cs_main once, but it does **not** install a slice-wide ScopedSnapshotDefer. Its per-request commit calls ordinary admission and can then add the unbroadcast marker. Thus the queue currently coalesces chain-lock acquisition, not necessarily numeric/canonical publication. JSON-RPC arrays alone do not create a mempool snapshot batch.

Even when publication is deferred, `PublishCanonicalTransactionMembership` loops over changed IDs and calls InsertTxLeaf/EraseTxLeaf separately. Each edit copies its canonical path; intermediate roots are released. It is O(k*D), with repeated copying of overlapping paths, not a grouped batch builder that copies each common branch once. The numeric builder has a different optimization: after one immutable root clone, its newly unshared branches may be mutated in place for subsequent edits. Do not claim those two writer algorithms are equivalent.

Source: `src/rpc/mempool.cpp:1704`; `src/validation.cpp:1787`, `2375`, `3327`; `src/node/transaction.cpp:185` through `229`; `src/txmempool.cpp:508` through `540`, `1271`; `src/node/snapshot.cpp:178` through `221`.

## Remaining variable-sized work

`MakeMempoolEntrySnapshot` builds a set of parent TxId strings, copies it into depends, reserves/appends/sorts spentby strings, and produces another immutable metadata value. Capture removes/inserts radix values for every changed snapshot ID. Delta sets, pending overlay vectors, package workspaces and other bookkeeping still allocate. Canonical leaves share transaction bodies, so they do not duplicate complete transaction serialization, but their insertion performs body-exposure accounting over the immutable transaction's nested storage. Existing UTXO/CTOR overlay bookkeeping and FreezeEpochBatch copies are outside the storage-only repair.

Source: `src/node/snapshot.cpp:140` through `174`; `src/txmempool.h:745` onward; `src/txmempool.cpp:253` through `266`; canonical `TxBodyExposure`; existing `MempoolOverlayLayer` maps/vectors.

## Gap to the requested primary-CoW architecture

The user's stronger architecture would make the authoritative state itself immutable by generation: readers retain that current root; writers change owned paths and publish the result. This candidate provides that property **only for the existing canonical transaction overlay**, while continuing to maintain the mutable primary and numeric RPC projection.

Potential directions deserve a separate source-grounded design rather than an instant rewrite: evaluate whether immutable entry metadata can become the authoritative leaf shared by read paths and secondary fee/time/dependency indexes; decide how multi-index invariants and writer-private transient batch updates remain atomic; and account all retained versions/reclamation before replacing mapTx. Canonical commitment order differs from numeric/RPC ordering, so an index/view may still be necessary even with shared authoritative leaves. An owned immutable read root also does not, by itself, remove serialization of conflicting transaction commits or chain-tip consistency checks.

This audit identifies the gap; it neither approves a wholesale primary-container migration nor adds that work to the current validation gate.

## Selective CoW: the specific optimization the user means

The intended optimization is valid: an exclusively owned writer-private node can be edited in place; a node retained by another generation must be cloned before editing. The current canonical arena does **not** implement that fast path. `TxOverlayNode` has const child links and topology (`mempool_overlay.h:79–100`); `InsertAt`/`EraseAt` rebuild ancestors through `MakeBranch` (`mempool_overlay.cpp:890–943`). It always copies affected canonical paths, even if no application reader retains a generation. `Reserve` is a no-op (`mempool_overlay.h:120`), so it does not provide an outside-lock refill guarantee. Numeric Radix, by contrast, checks `isShared()` before its private edit (`radix.h:190–208`); its copy barrier also protects a writer that entered an unshared source before a reader shared the root.

A safe canonical selective-CoW implementation needs more than a raw ownership-count test. Current publication itself retains the root, even without external readers; baseline writer/publication references first need an explicit ownership protocol. Reader capture and transition to writer-exclusive mutation must synchronize. Otherwise a writer can observe one reference just before a reader obtains a root, then mutate data the reader considers immutable. A brief capture gate is one possible design; an atomic writer claim with reader retry is another, but changes reader progress/latency guarantees. An ordinary seqlock does not legalize races on non-atomic child links. None of these alternatives is implemented or selected by this audit.

Sharing also propagates through ancestors: a child may have only one direct parent link while that parent is reachable from two retained roots. The writer must first clone a shared ancestor, making child sharing explicit, or carry the shared-ancestor condition down its traversal. Testing each child's reference count independently before that step would corrupt old views. Prefix pins and active hashing tasks count as retained readers too; cached digests can only be invalidated on genuinely exclusive nodes.

This can avoid copies of existing exclusive branches and repeated batch ancestors. New leaves/branch structure, transaction payloads, and slab refills still require storage; it does not imply zero allocations. A primary-CoW migration and selective canonical-node edits are related but distinct changes. The completed normal gate proves neither has already happened, and this source audit deliberately makes no new production edit.
