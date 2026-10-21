# Incremental reconciliation candidate — native validation pending

Source commit: `b93b9c7b4df95693dbf6e7e14e3a0c83bb50c998`.
Parent: `e3b73ec3a2` (explicit stable immutable-root clone), based on maintained517 `aed364af`.
Branch: `work/growth-incremental-recon-window-20261021` in the repaired-source Git repository.
Source worktree: `/Users/shammah/repos/lotus-v2-repair-work/growth-algorithm-source`.
An unchanged Git-format export is in `daemon/patch-intake/20261021/exports/growth-incremental-recon-window/`.

No native build, C++ test execution or benchmark has run on this candidate yet. `git diff --check` passes. Do not count the patch as integrated or as a measured performance improvement. N1 owns the coordinated compile/test window; the allocator agent is reviewing lifetime invariants without running builds.

## Maintained state and complexity

The current admission deque is retained, as are the existing epoch short-ID maps and the reference `AdmittedSince` API. A new incremental query view keeps:

- Numeric deque cursors delimiting `[since, until)` eligibility. They survive deque append and adjust on pruning.
- A per-ID count of eligible occurrences. This preserves duplicate admission/removal/re-add semantics, including the old eligible occurrence of a re-added ID.
- A persistent numeric-ID radix tree containing eligible IDs still indexed in the current epoch. CoW nodes and leaves use the existing concurrent slab allocator.

For ordinary monotonically advancing queries, each admission occurrence enters and exits the eligible range at most once. Eligibility maintenance is therefore **O(N·d)** in cumulative accepted occurrences, where radix depth `d<=64` for256-bit keys (expected logarithmic shallow paths), plus expected-O(1) hash accounting. `Add`/`Remove` repair current membership in O(d). This replaces repeated O(W) dedup/hash allocation and O(W logW) sorting.

Pinning one candidate root is constant-sized work while holding the index writer mutex. No writer can have entered an unshared source node, because all candidate-tree writers require that mutex. Subsequent writes see the shared root and use existing CoW paths. The generic `RadixTree` copy barrier remains intact.

Outside the index mutex, a candidate traversal joins IDs to one pinned published mempool entry tree. There is no `mempool.cs` acquisition in the normal path. Traversal stops after4,096 live/non-null/non-coinbase IDs, in exactly the numeric order used by the old normalization. Stale index entries are filtered **before** the cap, so missing low IDs do not hide later valid IDs. With S stale low-prefix candidates, lookup work is O((4096+S)·d); S is callback lag, not silently assumed zero. A malicious or stalled notification backlog can increase S. No finite bound on S is claimed.

A specialized `getWithinReadSection` allows the join without nesting RCU read guards: the outer tree traversal already owns a guard. It asserts that a read guard exists. Both trees are pinned through the join. It does not remove reader grace-period reclamation.

## Explicit exceptional paths

These still have potentially large work under the index mutex and must not be concealed as constant-time:

- First query and epoch/cutoff resets rebuild the eligible index once, O(W·d), rather than per query. Existing epoch short-ID rebuild is separately O(M).
- A backwards `since` or `until` resets the cached cursors and rebuilds. Production's normal fixed-duration forward-moving query avoids this; arbitrary query callers do not get the amortized guarantee.
- Out-of-order admission timestamps preserve the exact legacy reverse-scan/break behavior using a full fallback scan, O(W·d). An inversion count tracks when pruning removes all out-of-order edges; normal incremental operation then resumes. A single clock jump does not permanently disable incremental processing.
- If no valid published mempool entry tree exists (initialization or standalone tests), resolve the pinned candidate list against the live pool under `mempool.cs`, preserving filter-before-cap. This remains O(W) collection and potentially O(W) lookup. The node normally publishes its entry tree from pool construction onward.

The claim is amortized moving-window upkeep, **not** a universal worst-case real-time latency bound, and not a claim that every block-transition epoch rebuild is O(logM). A large accumulated delta after a stalled query consumer is processed once under the index mutex; further chunking may be warranted if measured.

## Correctness checks prepared

`txrelay_tests/recon_window_pinned_index_matches_scan` runs deterministic randomized Add/Remove/re-add, queries, epoch changes and pruning against the unchanged old scanner, starting with6,000 IDs and keeping an old pinned root across mutations. It includes exact half-open cutoffs, backwards ranges, backwards admission timestamps and return to normal operation after pruning inversions.

`txrelay_tests/recon_window_cap_follows_live_membership` supplies7,000 IDs with the first1,500 numeric IDs absent from the live view. This catches an incorrect implementation that caps before checking live membership. It compares the exact4,096-ID selection, derived subtree root and all16 bucket count/XOR summaries, and separately checks forced short-ID collisions preserve every full ID.

The immutable clone parent has a separate radix test for independent descendants and the original publication's lifetime. Existing relay/protocol tests must continue to pass. New tests preserve lasting semantic guarantees; they are not assertions that a one-time conversion occurred.

## Validation still required

Build `lotusd` and `test_bitcoin` in the coordinated incremental build. Run native radix, relay, snapshot/RCU and protocol-handler suites. Then compare identical finite-work admission cohorts with unchanged fee policy and sufficiently high valid fixture fees, default reconciliation still enabled. Sample actual ingestion at matched pool depths and inspect callback/index/mempool wait chains. Record the candidate source, tree, binary and actual accepted inventory. Keep incomplete long-run attempts and resource effects visible.
