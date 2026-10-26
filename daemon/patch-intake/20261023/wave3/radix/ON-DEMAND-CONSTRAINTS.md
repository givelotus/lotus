# Governing user constraint: mutable live generation, snapshots on demand

This addendum supersedes the pre-clarification architecture recommendation. The exact previous review is preserved as `REVIEW-before-on-demand-clarification.md`, SHA256 `5ff00e618bd479e3e14ab344f2324ce6d8bda50d743f91da9b7b1fdfe2c96f19`; its correctness findings remain relevant, but its proposed full-root-CAS hot path is NOT selected.

The target is a genuinely concurrently mutable live tree. Ordinary admission/lookups do not create a published immutable root or calculate a committed Merklix digest. A consumer explicitly requests a stable snapshot cut; later writes preserve that cut through generation-aware lazy divergence. Hashing is a separate on-demand operation over the pinned contents. Root-CAS full-path copying remains a comparison experiment only, not the final hot-path design.

## Existing local implementation is already the semantic baseline

Native C4 `8b55e7c8de373d2097da1ebacfcf14fd1098d046` contains `src/lotus_v2/tx_merklix.h/.cpp`. This is distinct from generic `src/radix.h`; do not conflate their key routing, hashing rules or synchronization contracts.

`txmerklix::Tree` already uses mutable live views, slab slots, path-unique in-place updates, O(1) structural `Pin()` and lazy hashes. Its explicit contract is single writer under one family writer lock, including when multiple trees share a Store. Path uniqueness uses every ancestor's ownership, not just a leaf refcount. `Snapshot` supports immutable traversal, `RootDigest()` and bucket descriptors; digests are derived Dirty/Busy/Clean caches. Store allocation and slot returns use a short mutex. `CTxMemPool::PinTxMerklixSnapshot()` currently requires mempool.cs.

The new work should preserve those semantics while redesigning concurrent mutation and capture. Simply removing the existing writer-lock requirement or adding atomic refcounts would create races on plain children/count/sketch/root fields. Conversely, replacing all live updates with whole-root immutable publication would miss the clarified objective.

## Primary-source pattern that matches the objective

[Scala's Ctrie documentation](https://docs.scala-lang.org/overviews/parallel-collections/ctries.html) describes a mutable trie with requested snapshots: snapshot capture creates a new root, while later accesses lazily rebuild touched parts and preserve the retained version. This is a suitable lifecycle model. It does not require a snapshot or a Merkle hash after each transaction.

The [original concurrent-trie paper](https://chara.epfl.ch/~prokopec/ctries-snapshot.pdf) uses stable indirection nodes, generation-checked local updates and helping. A snapshot rotates the live root generation through a conditional root operation that also checks the old root's main state. Older-generation operations must resolve consistently or restart. Mismatched branches renew lazily as later operations touch them. Snapshot capture does not wait for every writer to exit or recursively copy the entire tree. The paper's managed-memory algorithm is a source design, not a proof that our C++ adaptation already works.

The [official TrieMap implementation](https://raw.githubusercontent.com/scala/scala/2.13.x/src/library/scala/collection/concurrent/TrieMap.scala) supplies concrete reference points: `GCAS` publishes a proposed local main value with predecessor metadata; `GCAS_Complete` commits it or restores the predecessor according to generation/read-only state; `GCAS_READ` helps pending proposals. Root `RDCSS_Complete` validates expected main state or restores the old root, and its abort-aware reads avoid a root/child helping cycle. `readOnlySnapshot` advances the live generation and retains the prior root. Ordinary updates use local I-node publication; they do not install a new whole-tree root on every update. Main structural payloads are immutable local replacements, which is compatible with a logically mutable live tree.

Fetched primary PDF/source bytes and hashes are recorded in `PRIMARY-SOURCE-RECEIPTS.json`; whole upstream documents remain research evidence in the ignored canonical archive, not vendored source. The Scala URL is a moving branch, so use the captured hash when reproducing this review.

## Candidate A: generation/I-node adaptation — recommended prototype direction

This is a proposed C++ adaptation requiring a complete state-machine proof and tests, not an implementation-approved patch.

1. Keep a stable live generation/root between actual snapshot requests. Use immutable transaction/key payloads and stable I-node handles whose atomic main references can change locally. Disjoint-prefix writers should normally update different I-nodes.
2. Represent a generation using a non-reused identity whose lifetime is owned by roots/nodes. Slab address reuse alone is not generation identity; preserve the existing slot generation protection where handles can outlive reclamation.
3. Every local structural publication uses the same auditable generation-aware commit protocol. A plain `if (current_generation == start_generation) child.CAS(...)` is insufficient: a snapshot can cut between that check and the CAS. A visible proposal has a unique descriptor/state that helpers can commit or abort; no owner-only frozen bit may strand the tree.
4. Snapshot capture must validate both live root identity and its expected local main state. A one-word root CAS after an unprotected copy of root.main can miss a root-level update. Use the fully specified conditional/root descriptor protocol, including helping precedence, rather than layering independent generation tests around ordinary CAS.
5. The cut orders overlapping writes. A logically committed write before the cut belongs to the retained version; an operation that has not committed before the cut must either resolve before that cut consistently or restart in the new live generation. Physical cleanup can finish later, but a snapshot reader must resolve pending state to the same logical contents every time. The root descriptor protocol and child commit protocol must share one linearization argument.
6. A writer encountering an old-generation branch renews only the necessary current-generation access path/indirection before changing it. Shared old-generation content remains preserved for snapshot readers. Within an unchanged generation, repeated local updates do not repeatedly publish the entire root or copy all ancestors to the top.
7. Mutable live reads use the protocol's checked/helping read and a short RCU scope, returning owned immutable leaf values. Read-only snapshot traversal uses its captured generation and must not renew or mutate logical snapshot content. Existing public RCU non-nesting rules still apply.
8. Include insert, erase, overwrite, insertOrGet, conditional remove, clear, snapshot-of-snapshot, moving handles and root replacement in the protocol contract. Stable I-node lifetime is not permission to leave ancestor compaction unproved; use tombstone/cleanup states or defer compaction until proved. Preserve exact key equality repair.
9. Begin with explicit conservative atomic ordering, model-check it and relax only with evidence. Java's volatile/CAS assumptions do not mechanically prove C++ acquire/release correctness. Reuse the existing RCU/slab infrastructure only after proving descriptor, generation and shared outgoing-edge ownership.
10. A bounded batch may update local nodes together or amortize preparation, but package atomicity/commit boundaries remain explicit. The name BatchTxn is not a requirement. One-map GCAS does NOT atomically publish input claims, transaction membership, counters, fees, notifications and other maps; that remains the separate admission commit-descriptor protocol.

The constant structural work of successful cut acquisition is a generation/root descriptor operation and lifetime pin, not traversal/hash calculation. Contention can force retries; helping can perform another operation's completion; allocation/reclamation can block. Thus do not promise O(1) total wall time, wait-freedom, lock-free allocation or 50ns capture. State the algorithm's progress assumptions and measure contention separately.

## What 'in place' does and does not promise

Candidate A mutates the live tree's local atomic links/I-node main references directly. It may allocate a small replacement structural payload for a changed I-node. This is fundamentally different from per-update whole-root path-copy/publication, but it is not zero-allocation mutation of every existing byte.

If physical child-array mutation of uniquely owned nodes is also required, treat it as a further optimization. A reference count of one does not establish absence of RCU readers or an in-flight snapshot operation. The optimization needs an exclusive mutation claim coupled to generation validation, coherent readers for all affected fields, and a helpable abort/commit path. Preserve parallel writers; do not silently introduce a global writer lock to obtain that claim. A corrected drain gate can be a separately labeled blocking baseline, not a substitute for the requested architecture.

As another comparison, [constant-time snapshots of collections of CAS objects](https://arxiv.org/abs/2007.02372) retain version histories and return snapshot handles, allowing later historical reads. This can preserve physically mutable links, but old-snapshot read cost and version retention grow with updates. It is an alternative research track, not a reason to add MVCC machinery before measuring the generation prototype.

## Lazy Merklix hashes and MinHash must name a stable cut

This part is our integration design, not a claim made by Ctrie.

- Preserve the exact existing commitment: raw 256-bit TxId routing, LSB-first bit order, path-compressed branch depth, leaf TxId+TxHash commitments, empty hash and unary-run folding. A Ctrie routes by hash and may alter physical shape during cleanup; none of that may silently alter the Merklix logical root. Generation metadata, I-node/descriptor addresses, balancing shape and allocator slot identity are excluded from the logical digest.
- Live lookup/mutation requires no Merklix digest. `Pin()` captures contents; `RootDigest()` or bucket-proof operations on that pin trigger hashing. These are separate API costs and should be benchmarked separately.
- Memoize only content proven stable for the pinned generation. A cached parent hash on a mutable live ancestor is unsafe even when the parent pointer is unchanged: a descendant I-node may have committed a new child underneath it. Do not key a digest solely by a mutable I-node address or by the live root pointer.
- Initial correctness implementation can use a per-snapshot hash sidecar keyed by stable node/slot generation and snapshot identity. Reuse across snapshots only when a sealed subtree token proves identical logical descendants; no root-wide hashing on admission is necessary. Shared unchanged subtrees should eventually reuse their valid digest, but that optimization needs an explicit identity/invalidation proof.
- Hashers may fill derived cache cells through atomic state/result publication without changing logical contents. Hashing a pinned snapshot must not traverse the current live version. Allocation failure or a stalled hasher must not block transaction mutation; a losing hasher can compute privately if useful, as the current native design already does.
- A MinHash summary must correspond to the same pinned cut as its root/buckets. Current `minhash::Maintainer` is not automatically multiwriter-safe. Either include a safely versioned summary in the capture/commit design or derive/refill it lazily from the pinned leaves. Do not combine a new root with an unrelated live sketch. Incremental inserts/deletes and lazy refill can remain separate optimizations.
- Bound generation/descriptor lifetime, slab return batches and outstanding snapshots. A paused reader can delay reclamation; never recycle a still-pinned slot to satisfy memory pressure. Report retained bytes and oldest pin age alongside allocation counts.

## Required proof and test changes

Carry forward the original report's weak-memory, tag, conditional ownership and RCU findings. Replace the proposed drain-based acceptance test with tests of the chosen generation state machine:

- Pause a writer after it has descended, cut a snapshot, then resume. It must commit consistently before the cut or fail/retry in the new generation; retained leaf sets never change afterward.
- Force a pending child GCAS while root capture is pending. Helpers must finish/abort without a helping cycle and without waiting for the original owner. Test both relative orderings and root-main mismatch.
- Keep a writer paused indefinitely after a visible proposal while unrelated writers and snapshot operations make progress. A design that only spins on its frozen bit fails this test.
- Compare many retained cuts with a serial-history oracle; mutate disjoint and same prefixes, release snapshots out of order, clear/re-add, compact branches and recycle slab slots after grace periods.
- Assert exact canonical Merklix roots against the existing serial reference; verify first on-demand hashing, repeated cache hits and mutation of a descendant while live parent identity remains unchanged. The old pin's digest/sketch must remain stable; the new pin must include the change.
- Audit every C++ atomic transition and memory ownership edge, then model-check a minimal state machine; TSAN/stress supplements the proof but does not prove all-atomic linearizability.

No new source implementation, model check, sanitizer run, stress test or performance number has been produced by this addendum. Existing lock contracts stay in force until a reviewed replacement passes these gates.
