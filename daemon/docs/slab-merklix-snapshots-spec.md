# Slab-backed persistent Merklix snapshots with lazy commitments and incremental MinHash

Status: **implemented in production call paths on review source
`922eb4a7f9d8ec8af7a5e64d521454c572ece937`, based on repaired 527
`0f42fcfde6d36fd4326b8de18df17ce740b22446`. All 1,200 native cases pass with the matched allocator-OFF profile; the unchanged tree code retains its prior
400-round ThreadSanitizer stress and two-node scope-5 recovery/mining pass. Three microbenchmark repetitions at
5k/100k/500k are recorded; canonical patch 528 is integrated by commit `90e98bf0`; matched 527/528 node benchmarks are running separately; results are not yet available.** This document is the
specification for the follow-up recorded in
[`lazy-merklix-snapshot-followup.md`](lazy-merklix-snapshot-followup.md). It
does not change consensus hashing, block validity, transaction validation or
epoch finality.

| Item | Value |
| --- | --- |
| Base source | repaired 527 tip `0f42fcfde6d36fd4326b8de18df17ce740b22446`, tree `a2c855dc0f6d16fa260549c40958ba37aecb03b9`; earlier `385b64d7` and halted `657edc0133` remain historical recovery |
| Source lane | `daemon/worktrees/merklix-slab-source` (linked worktree of `~/repos/lotus-v2-repaired-source`), branch `review/merklix-slab-snapshot-20261022` |
| Code | `src/lotus_v2/tx_merklix.{h,cpp}`, `src/lotus_v2/minhash.{h,cpp}`, integration in `mempool_overlay`, `primitives/block.cpp`, `txmempool`, `net/full_mempool_reconciliation`, `node/snapshot.cpp`, `node/metrics_collectors.cpp` |
| Tests | `src/test/tx_merklix_tests.cpp` (+ updated `full_mempool_reconciliation_tests.cpp`) |
| Wire change | full-mempool reconciliation (scope 5) frames are version 2; offers carry a 64-value bottom-k MinHash. Approved by the user: no released v1 peers exist. |

## 1. Inventory of the existing structures (what is replaced, what remains)

| Structure | Where | Keyed by / commits to | Disposition |
| --- | --- | --- | --- |
| `TxOverlayArena` | `lotus_v2/mempool_overlay` | TxId → (TxId, TxHash); consensus Subtree A | **Replaced in production** by `txmerklix::Tree` inside every `MempoolOverlayLayer`. Kept only as a legacy reference for equivalence tests and A/B microbenchmarks. It is append-only: every insert/erase appends a fresh root-to-leaf path and nothing is reclaimed until `Reset`; freezing an epoch deep-copied the whole vector. |
| Full-mempool reconciliation `Snapshot` build | `net/full_mempool_reconciliation` | (TxId, TxHash); same Subtree A digest | **Replaced**: captures now pin the mempool's working tree in O(1) under `cs_main`+`mempool.cs` instead of copying every `CTransactionRef` under the locks and rebuilding/eagerly hashing a private compressed trie (O(n log n)). The transaction-vector constructor remains as the bounded page verifier (≤64 bodies), the test entry point and an explicit fallback (`capture_fallbacks`). |
| `MempoolSnapshotTree` (ABC `RadixTree` + RCU, `SnapshotAllocator`) | `node/snapshot` | TxId → full immutable RPC entry | **Retained.** It serves RPC entry reads (fees, depends, spentby), carries no commitment, and already has RCU lifetime and slab allocation. Merging it would add a second payload and lifetime protocol to the commitment tree with no hashing benefit. |
| `SmtNode` / `UtxoOverlayArena` | `lotus_v2/mempool_overlay` | Outpoint → coin; consensus UTXO state root | **Retained.** Different key space, leaf encoding, expiry metadata and the consensus state-root contract; out of scope for this change. |
| `TxRelayIndex` short-id epochs | `net/txrelay_index` | SipHash short ids | **Retained.** Short-id relay, not a Merklix commitment. |
| Block `hashMerkleRoot` / `TransactionRoot` | `lotus_v2/commitment` | consensus | **Unchanged.** Blocks are still validated from their own transactions; the tree only supplies equal Subtree A roots to template/preview/sealed-header paths, exactly as `TxOverlayArena` did. |

## 2. Canonical commitment (unchanged consensus definition)

For a set S of non-coinbase identity pairs (TxId, TxHash):

* key bit d of a TxId is `(id[d/8] >> (d%8)) & 1` (LSB-first, "canonical order");
* `Empty = TaggedHash(TxRoot, 0x02)`;
* `Leaf(id, hash) = TaggedHash(TxRoot, 0x00 || id || hash)`;
* `Node(d, L, R) = TaggedHash(TxRoot, 0x01 || u16le(d) || L || R)`;
* `Sub(S, d) = Empty` if S is empty, `Leaf` of the single member if |S| = 1,
  otherwise `Node(d, Sub(S0, d+1), Sub(S1, d+1))` where S_b holds members whose
  bit d is b.

The block transaction root combines the coinbase leaf with `Sub(S, 0)`
(`TransactionRootFromSubtreeA`). `TransactionSubtreeA` in `commitment.cpp` is the
reference; the new tree is tested against it (`BuildTxSubtreeA`) and against the
legacy arena.

## 3. Node layout, handles and canonical path compression

Only real branch points are stored. A branch records `split`, the first bit at
which its members differ. A member set with one element is its leaf. Between a
parent at split p and a child at split c > p+1 the canonical tree has c−p−1
unary levels; they are not stored and are folded on demand:

```
DigestAt(child, p+1):
    x = NodeDigest(child)                 // digest at the child's own split
    for d = child.split-1 down to p+1:
        x = bit(child.key, d) ? Node(d, Empty, x) : Node(d, x, Empty)
```

This is identical to the old full-recon compressed trie. Branch `key` is any
member key; bits below `split` are the shared prefix (they remain valid after
members leave, because every remaining member shares them).

```
struct Branch (96 B)                      struct Leaf (144 B)
  atomic<u32> refs                          atomic<u32> refs
  atomic<u64> generation                    atomic<u64> generation
  u32 child[2]   (handles)                  atomic<u8> hash_state
  u32 count      (members below)            u32 payload_bytes
  u16 split                                 u64 minhash  (cached element value)
  atomic<u8> hash_state  Dirty|Busy|Clean   Hash key (TxId), Hash tx_hash
  Hash key (prefix representative)          Hash digest (cache)
  Hash digest (cache, digest at split)      shared_ptr<const void> payload (body)
```

Handles are 32-bit: `0` is null, branch handles are slab slots ≥ 1, leaf handles
are `0x80000000 | slot`. Strong references (child slots, tree roots, snapshot
roots) own one reference count each and can never be stale. Weak references
(`Store::WeakRef {handle, generation}`) are validated with the slot generation
(ABA protection) and an increment-if-nonzero compare-and-swap; they are an
available API, used by tests, not by production paths (see §10).

The structure is canonical: for a given member set every insertion/deletion
order yields the same branch points, splits and counts (tested through roots and
equal leaf enumeration).

## 4. Slab allocation, slot reuse and reclamation

* One `Store` per tree family (shared by a tree, its copies and its snapshots)
  holds two slabs (`Branch`, `Leaf`). Chunks have stable addresses: 11
  geometric chunks of 64…65,536 slots, then 65,536-slot chunks, up to 2^26 slots
  per kind. Readers on any thread resolve `handle → chunk → slot` with acquire
  loads; chunks are published with release stores before any handle into them
  can be published. Small temporary stores (page verification) therefore cost a
  few KB, not a 4096-slot chunk.
* Allocation and free-list pushes take the store's allocation mutex (short,
  uncontended in steady state). Nothing here is lock-free and it is not
  documented as such.
* `Release(n)`: atomic `fetch_sub(acq_rel)`; when a node's count reaches zero
  the releasing thread owns it: it drops a leaf's body reference, pushes a
  branch's children on an explicit bounded stack (≤ 2×260 entries), and returns
  freed slots to the free lists in batches of 1024 per mutex acquisition. A
  dead snapshot is therefore reclaimed by whichever thread drops the last
  reference (e.g. the network thread), in batches that bound mutex hold time.
* Every allocation assigns a fresh 64-bit identity from a store-wide monotonic
  counter, including after all chunks have been trimmed. Counter exhaustion
  rejects allocation; identities never wrap or reset. Free slots have zero
  references, and weak acquisition holds the allocation mutex through validation
  and retention. Weak acquisition also requires the family writer lock so it
  cannot invalidate the unique-path mutation proof.
* `Tree::Clear()` by the store's sole owner calls `TrimIfUnused()`: when no node
  is live the slab chunks are returned to the allocator (retained memory after a
  mempool spike is bounded by the live working set plus snapshot divergence).
* Long-lived snapshots keep exactly their reachable version alive. Memory
  retained by a snapshot is its structure not shared with newer versions: at
  most one path copy per distinct modified path since the pin, plus removed
  leaves/bodies.

## 5. Ownership, safe snapshot acquisition and mutation

**Writer contract.** All `Tree` objects sharing a store are mutated under one
external writer lock. In production every tree lives in a
`MempoolOverlayLayer` owned by `CTxMemPool::m_merklix_overlay`, which is
`GUARDED_BY(cs)`; temporary layers (RPC template fallback, tests) own private
stores.

**Path-unique rule.** During an update from the writer's root, a node is
*unique* iff it and every ancestor on the path has `refs == 1` (acquire load).
Only unique nodes are mutated in place; any other node on the modified path is
copied (path copying). Correctness argument:

1. A node reachable from any snapshot or other tree has, on its path from the
   writer's root, an ancestor (possibly itself) with `refs ≥ 2`: pinning or
   copying adds a reference at the root; copying a shared branch adds a
   reference to each child it shares.
2. Only the writer (under the writer lock) increases reference counts (pin,
   tree copy, path copy, new branch above an existing subtree). Other threads
   only decrease them. Hence an observed `refs == 1` cannot become 2
   concurrently.
3. A concurrent release that turns 2 into 1 happens after the releasing owner's
   last read (its holder stops using a snapshot before dropping it), and its
   `acq_rel` decrement synchronizes with the writer's acquire load, so the
   reader's accesses happen-before any in-place write.

**Safe acquisition (no load/retain race).** There is no published atomic root
that readers load. A snapshot is created by `Tree::Pin()` under the writer lock:
it increments the root's count and returns `shared_ptr<const Snapshot>`.
Readers receive the snapshot object through ordinary synchronized hand-off
(`shared_ptr` copies inside the reconciliation manager, which holds its own
mutex). A reader therefore never retains a node it merely loaded.

**Operations and reference transitions** (`r` is the node returned for a
position; the parent stores `r` and, if `r ≠ old`, releases `old`):

| Case | Unique path | Shared path |
| --- | --- | --- |
| Insert new key below branch b | recurse; if child returned itself, `Touch(b)` (recount, mark Dirty) | copy b (retain sibling), store new child |
| New key diverges above n (at split p) | new branch {n, leaf}; `retain(n)` — parent then releases its old ref: net 0 | same (n untouched) |
| Replace (same TxId, new TxHash) | new leaf; old leaf released by parent | same |
| Erase leaf under b (sibling s) | b collapses: return s with `retain(s)`; parent releases b, which frees b and the leaf | parent copies itself pointing at s; b stays with snapshots |
| Unchanged (identical pair) | nothing touched, no version change | same |

## 6. Writable views versus pinned advertised snapshots

* `txmerklix::Tree` — the writable reconciliation/admission view. Admission,
  removal and reconciliation recovery all reach it through normal mempool
  admission (`addUnchecked` → deferred overlay adds → `FlushPendingOverlayAdds`
  → `AddTransactionsToOverlayBatch` → `MempoolOverlayLayer` → `Tree::Insert`;
  `removeUnchecked` → `Tree::Erase`). Reconciliation-recovered bodies go
  through `ProcessShortTxResponse` and ordinary admission; they never touch a
  pinned target.
* `txmerklix::Snapshot` — an immutable version: root, member count, membership
  version, payload-byte charge and the bottom-k sketch, all captured together.
  Advertised reconciliation offers, served pages, RPC template roots and
  frozen epoch layers use pinned/shared versions. A new write after a pin
  copies the touched path and can never change the pinned set.
* An advertised root identifies one exact pinned set; the next capture is a
  new version.

## 7. Dirty propagation and lazy hashing

* New and in-place-modified nodes are `Dirty`. Every modified path is fully
  dirty (copies start Dirty; `Touch` marks unique ancestors). Clean subtrees
  keep their cached digests, so repeated edits on shared ancestors during a
  batch are coalesced: an ancestor is rehashed once when a commitment is
  requested, not once per edit.
* Ordinary readers (`Contains`, `FindHash`, prefix `Leaves`, enumeration,
  counts) never hash. A commitment is computed only by `RootDigest()`/`At()`
  when a caller needs it: block template and preview, sealed-header matching,
  epoch batch freeze/announce, and advertised reconciliation roots/children.
* Cache publication: compute the digest, then `CAS(Dirty → Busy)`; the winner
  writes the 32 bytes and stores `Clean` with release; the loser simply uses its
  own value (no waiting, no concurrent non-atomic writes). Readers read a cached
  digest only after an acquire load of `Clean`. Only exclusively owned nodes are
  ever set back to `Dirty`, so no hasher can observe that transition.
* A pinned snapshot can be hashed outside every node lock by any number of
  threads; its digests fill the same caches the working tree uses (shared
  nodes), so the mempool's next template root reuses them.
* Large dirty versions (≥ 4096 members) are completed with up to 16 parallel
  subtree hashers at the 4-bit frontier (`std::async`; thread exhaustion falls
  back to serial hashing).

## 8. Incremental MinHash

* **Sketch**: bottom-k MinHash, k = 64, over the set of identity pairs
  (TxId, TxHash) — the same elements as the Merklix leaves, so equal roots imply
  equal sketches.
* **Element value**: `SipHash-2-4(key0=0x6c6f7475732d6d68 "lotus-mh",
  key1=0x2d74786964763031 "-txidv01", TxId || TxHash)`, cached in the leaf.
  Deterministic and comparable across nodes; not secret (see failure cases).
* **Set semantics**: inserting an identical pair is no change; replacing a
  TxId's TxHash erases the old element and inserts the new one in the same
  mutation; duplicate values are kept with multiplicity, matching the
  reference (sort all values, take the 64 smallest).
* **Maintainer** (`minhash::Maintainer`): sorted candidate buffer targeting 256
  values (all threshold ties are retained, so hash collisions can exceed that
  target). Invariant: when capped, the buffer equals *every* member value
  ≤ threshold (with multiplicity); otherwise it holds all members. Insert adds
  values ≤ threshold and, above 256, drops every copy of the maximum (lowering
  the threshold). Erase removes one copy if ≤ threshold. If a capped buffer
  falls below 64 values the next minima are unknowable locally: a rebuild is
  flagged and performed lazily at a sketch export, scanning cached
  leaf values (O(n), no hashing). Pinning copies at most 64 ready values or
  records a pending refill without scanning. Snapshot sketch access performs
  that refill once, synchronized with `call_once`, over the immutable pinned
  leaves after capture locks are released. At least 193 sampled deletions separate two
  rebuilds; with random deletions a sampled member is hit with probability
  ≈ 256/n, so the amortized cost is O(1) per deletion. The adversarial worst
  case (deleting exactly the smallest values, e.g. ground low-value
  transactions being mined) costs one O(n) scan per 193 deletions.
* **Estimator**: Jaccard J from the 64 smallest values of the union of two
  sketches; estimated remote-only members `|B| − J(|A|+|B|)/(1+J)`.
* **Use**: offers carry the sketch; receivers compute J and the remote-only
  estimate against their own pinned capture, record them, and compare the
  estimate with the members the authenticated traversal actually recovered
  (Prometheus `fullrecon_sketch_*`). The sketch never decides what is fetched,
  accepted, voted or finalized; the authenticated root/children/page digests
  do. A peer can lie about its sketch; the only effect is a wrong hint.

## 9. Atomic consistency

Membership, version, payload charge and sketch are updated in the same
`Insert`/`Erase` call under the writer lock; `Pin()` captures root, count,
version, payload bytes and ready sketch values or a pending-refill marker
together. A pending snapshot sketch is derived only from that snapshot’s pinned
leaves; later working-tree mutations cannot affect its version or sketch. Any digest ever
computed for a snapshot is a pure function of its immutable reachable
structure, so a completed Merklix digest always describes the same version as
its sketch. The reconciliation cache key remains (reset sequence, size, anchor)
from the existing code; the pinned version is exposed for diagnostics.

## 10. Is a hash-to-handle index needed?

No. Every consumer addresses data by structure, not by digest: reconciliation
requests carry a per-offer context bound to the pinned snapshot plus a
canonical prefix; sealed-header and avalanche matching compare a requested root
with a handful of layer roots (speculative + frozen epochs). An index would add
a second lifetime protocol for no lookup that exists today. If one is added
later it must store `WeakRef {handle, generation}` (never strong references),
insert only roots whose digests are `Clean`, resolve with `TryRetain` and then
re-check the cached digest, and be pruned when resolution fails.

## 11. Writer concurrency and cache synchronization

* One writer at a time per store (mempool `cs`). Multiple-writer CAS retries or
  per-node locks were not introduced; single-writer ownership was benchmarked
  first, as required.
* Readers/hashers/releasers on other threads interact only through atomic
  reference counts, the digest CAS protocol and the allocation mutex.
* Snapshot release may free large divergent versions on the releasing thread,
  in 1024-slot batches.

## 12. API contracts

```cpp
namespace lotus::v2::txmerklix {
class Tree {             // single writer; copy = O(1) structural share
  Change Insert(id, hash, payload = {}, payload_bytes = 0); // Unchanged|Inserted|Replaced
  bool   Erase(id);                       // false if absent (no change)
  void   Clear();                         // trims the store when solely owned
  optional<Hash> FindHash(id) const;      // never hashes
  size_t Count() const; uint64_t Version() const; uint64_t PayloadBytes() const;
  Hash   RootDigest() const;              // lazy; writer lock held
  Sketch CurrentSketch() const;           // bottom-k, rebuilds if flagged
  shared_ptr<const Snapshot> Pin() const; // O(1) + 64 values; writer lock held
};
class Snapshot {         // immutable; any thread
  size_t Count(); uint64_t Version(); uint64_t PayloadBytes(); const Sketch &GetSketch();
  Hash RootDigest() const;                         // lazy, thread-safe
  Descriptor At(prefix_bits, depth) const;         // count + digest at depth
  optional<vector<const Leaf*>> Leaves(prefix, depth, max) const; // canonical order
};
}
// CTxMemPool
shared_ptr<const txmerklix::Snapshot> PinTxMerklixSnapshot() const; // cs held; flushes deferred overlay ops;
                                                                    // nullptr if overlay != mapTx
// MempoolOverlayLayer
Hash GetSubtreeARoot() const;            // lazy completion
shared_ptr<const txmerklix::Snapshot> PinTxTree() const;
void AdoptTxTree(Tree); size_t AddTransactionBatch(entries, bool tree_already_contains);
```

## 13. Integration points (reviewed call paths)

| Path | Before | After |
| --- | --- | --- |
| Admission (`addUnchecked` → deferred adds → `FlushPendingOverlayAdds`) | arena path append per tx (parallel batch insert ≥16) | `Tree::Insert` per tx: in place on unique paths, no hashing, MinHash updated, body charge recorded (`OverlayPayloadBytes`) |
| Removal (`removeUnchecked`, deferred removes) | arena path append | `Tree::Erase`: collapse/in-place, slots reclaimed when unshared |
| Block connect (`ConnectBlockReset` → `ReanchorExistingTxs`) | every speculative and frozen tx re-inserted into fresh arenas, full rehash | trees adopted unchanged (`AdoptTxTree` + `tree_already_contains`), cached digests survive; mismatch rebuilds from the entry map |
| Epoch freeze (`FreezeEpochBatch`, avalanche processor) | deep copy of the arena vector (including garbage) | O(1) tree share; next write copies one path |
| Template / preview / sealed header / avalanche batch roots | `SubtreeARoot` (lazy arena digests) under `cs` | `GetSubtreeARoot` (lazy tree digests) under `cs`; unchanged consensus roots |
| RPC `getblocktemplate` snapshot roots (`MiningTemplateSnapshot::EnsureRoots`) | arena root hashed under `TRY_LOCK(cs)` | tree pinned under the lock, root hashed after release |
| Full-mempool reconciliation capture | copy all refs under `cs_main`+`cs`, O(n log n) private build + eager hashing | O(1) pin under the locks; lazy hashing at offer time (`fullrecon_commitment_microseconds_total`); pages served from leaf payloads; MinHash in offers |
| RPC entry reads (`MempoolSnapshotTree`) | radix RCU | unchanged |

## 14. Worked examples

Keys are shown by their first canonical bits (bit 0 first).

1. **Insert into an unshared tree.** Members A=`000…`, B=`011…`. Root is a
   branch at split 1 (bit 0 equal, bit 1 differs), key A. Insert C=`010…`:
   bits 0–1 match prefix `0?` up to split 1, bit 1 of C is 1 → descend to B
   (a leaf at depth 2). C and B differ first at bit 2: new branch {C, B} at
   split 2 with B retained; the root (refs 1) is unique, so its child slot is
   overwritten in place, B's extra reference is dropped, and the root is marked
   Dirty. One leaf and one branch allocated, no copies, no hashes.
2. **Pin, then write.** `s = tree.Pin()` makes root refs 2. Erasing A finds the
   root shared: recursion returns null for A, the root collapses to its
   sibling, so the tree's new root is the existing branch {C, B} (retained).
   The old root still points at A and {C, B}; `s.RootDigest()` hashes A, the
   {C,B} branch (shared with the tree, filling its cache for both) and the old
   root, yielding the pinned set's commitment.
3. **Unary folding.** Two keys differ first at bit 255 (see test
   `adversarial_prefixes_and_deepest_split`): one stored branch at split 255;
   the root digest applies 255 folds with empty siblings, exactly as
   `TransactionSubtreeA` recurses through 255 single-sided levels.
4. **MinHash deletion.** With 1,000 members the buffer holds the 256 smallest
   values. Deleting the 193 smallest leaves 63 < 64: `Pin()` records a pending
   refill. The next snapshot `GetSketch()` scans its 807 remaining cached leaf
   values and exports the exact 64 smallest, even if the working tree has since
   changed (test `pin_defers_exhausted_sketch_refill_to_immutable_snapshot`).

## 15. Failure cases and handling

| Failure | Handling |
| --- | --- |
| Overlay membership ≠ `mapTx` at capture | `PinTxMerklixSnapshot` returns null; capture rebuilds from copied refs (`fullrecon_capture_fallbacks_total`) |
| Adopted tree ≠ re-added entries during re-anchor | tree rebuilt from the authoritative entry map before any root is used |
| Slab exhaustion (2^26 slots per kind) | `std::length_error` from the allocating writer; the budget checks of the callers bound real usage far below |
| Allocation failure during a path copy | strong-exception path: retained siblings and new leaves are released before rethrow |
| Erase of a non-member | returns false; no version/sketch change |
| Sketch erase of an unknown value (contract violation) | flags a rebuild, restoring exactness |
| Thread exhaustion during parallel completion | serial completion |
| Ground low MinHash values / dishonest peer sketch | biased hint only; authenticated traversal unaffected |
| Concurrent hashers on one snapshot | CAS; loser uses its own value |
| Snapshot released on a network thread while mempool writes | atomic decrements; batched frees under the allocation mutex |
| Stale weak handle after reuse | generation mismatch → `kNull` |
| Body-less leaf (fixtures) asked for a page | `Page()` returns "unavailable" (never a partial page) |

## 16. Validation and evidence

See [`../../benchmark-results/20261022/slab-merklix-v1/REPORT.txt`](../../benchmark-results/20261022/slab-merklix-v1/REPORT.txt)
for exact source/binary hashes, test outcomes and measurements.

## 17. Remaining limitations

* MinHash values are public and grindable; the sketch is a hint only.
* Captures still charge each pinned snapshot's full structural size against the
  reconciliation budget (conservative, unchanged policy) even though most nodes
  are shared with the mempool.
* The mempool's `std::map` entry index, UTXO overlay and RPC radix index are
  still copied/maintained as before; only the transaction commitment tree
  changed.
* Multi-writer stores are unsupported by contract; nothing is lock-free.
* First commitment completion is slower in the 500k microbenchmark (24.8 ms vs
  17.3 ms). Snapshot/admission benefits must be evaluated separately.
* Last-owner reclamation is synchronous: the 500k long-lived snapshot release
  measured 48.8 ms median. Batching limits mutex hold time, not total pause.
* `RetainedBytes`/benchmark slot-byte counters cover constructed slots, not
  unused chunk capacity, allocator overhead, transaction bodies or process RSS.
* Deferred overlay additions still require flushing under the mempool lock;
  the constant-time guarantee is structural root acquisition after those updates.
* A depleted working sketch stays depleted until `CurrentSketch` refills it;
  distinct pins can independently refill their immutable sketches. Threshold
  hash ties may grow the candidate buffer beyond its 256-value target.

## 18. Shared lifetime repair before matched endpoints

The matched allocator-OFF comparison uses repaired 527 `0f42fcfd` and 528
`922eb4a7`. Both inherit the same signature-cache lifetime fix in ecash/025
(global 26) and exact-transaction admission fixture repair in ecash/348 (global
349). Their complete native gates pass (1,187 / 1,200 cases); all 528 mailbox
intermediate trees replay exactly. No assertion is weakened or skipped, and no
generic/cooperative executor is included. Existing 385/c4 artifacts remain
historical. Exact endpoint hashes and causal before/after evidence are under
`daemon/patch-intake/20261022/tls-cache-lifetime-repair/`.
