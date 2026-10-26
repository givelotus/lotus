# Shared performance placement audit

Primary target: the shared eCash engine and WIP Lotus tail. Lotus V1 remains a donor/optional maintenance target, kept running; this is not a V1 modernization project. The initial audit was read-only. The authorized first fee-worker rehome subsequently completed the exact-tree and test gates described below. Production data and benchmark identities remain unchanged.

## Frozen audit baseline

- Shared375: `47765534500efe516e9306a6426d9c9ad9d216a4`.
- Native154 / total529: `a2af4764d116fa37fed463af1ffd3c6fb0514f76`, tree `f58bb4951d4431ab30f1b0363c7368f6969a5cb4`.
- Source authority: existing `daemon/worktrees/merklix-slab-source`, branches `daemon/ecash` and `daemon/v2`.
- Existing preserved source bundle: `daemon/patch-intake/20261022/mempool-consistency-policy/source-freeze.bundle`; source owner reports verified529 commits/two branch refs. Its tracked source proof/gates are in the same directory. Full tracked-tree and every dirty delivery must additionally be accounted for before relocation; this report does not substitute for that gate.
- V1 was only read: existing mainnet checkout HEAD `94999af5264212cbb5195d4a3cedc2d68265a6d1`, older ABC pin `8c67fe1e85`. It has distinct GetId/GetHash, SIGHASH_LOTUS/Taproot and no current snapshot/fee-worker/native-VM framework. No V1 repo/module is removed or newly created.

## Immediate findings

Many major mechanics are already shared: immutable RPC snapshots020/021, publication coalescing034/048/051, mempool slab058, block-index slab068, transaction slab069, persistent range executor, decode/precompute before cs_main, staged/queued admission, CoW slab369, no-writer-grace-period immutable roots371, jemalloc372 and incremental relay window373. File namespace `lotus_v2` alone does not prove a component is confined to the native tail.

In particular `CloneChainStateOnly`, `GetUnbroadcastTxCount`, lazy snapshot vectors and lazy mining publication are already at the shared tip. They must not be counted again as stranded optimizations.

| Priority | Current owner | Proposed action | Boundary that must remain native |
|---|---|---|---|
| First | Native149 `6216b51e90` | Rehome node-owned fee-policy worker and cached admission-policy publication after the shared dependency closure. Eight of ten files text-apply at shared tip; context.h and snapshot.cpp need mechanical context resolution. | Resource-unit/consensus EMA/floor semantics remain unchanged; no V2 fee/burn rules imported into another chain. |
| Next split | Native041/042 | Extract only additional generic reset-generation/defer-cancellation/publication mechanics into existing shared snapshot owners. Two041 mempool files text-apply; consumer/test contracts still required. | Native template/root/monetary/header/RPC adapters. Existing shared clone/count/lazy fixes are not new work. |
| Next split | Native151 `dcc95d5b97` | Shared full-membership manager, bounded ownership/budgets and useful-deadline scheduling, with explicit chain identity/hash/codec adapter. Six of nine files text-apply; native tests must be separated. | Native body/witness identity tests and commitment policy. Retain normal validation, exact-body proof and DoS limits. |
| Next split | Native154 `a2af4764d1` | Shared slab/refcount/path-copy/immutable pin/MinHash machinery; retain a chain commitment adapter. | Current tree includes native header.h and exact native TxRoot tags/folding. This is NOT a pure reordering until interface prerequisites are separately resolved. |
| Next split | Native048/050/055 | Known-parent index reuse, prefetch/bulk plumbing and dirty-overlay mechanics into shared admission/overlay owners. | nFlags structural input eligibility, native UTXO/state import, VM and resource costs. |
| Later split | Native134 | Generic lifecycle is reusable, but MiningPoolManager is absent shared and originates native059. Only2/10 files text-apply;134 stays native until a separate poolcore/nativeadapter extraction. | Native payout/share/header/discovery adapters135–137; never reinterpret payouts. |
| Retain native | Native147/148/150/152/153 | Host BIP340-cache wiring, witness transfer, exact resolved-wrapper reuse and advisory native crypto warming. Generic cache/snapshot/precompute foundations are already shared. | Native VM, domain/message/encoding/coin binding and per-run effects. These are not missing generic optimizations merely because they improve performance. |
| Retain native; extract utility only with a consumer | Native016/054/056/060 | Generic MDBX lifetime/parallel/slab helpers may be extracted. | Native JMT/SMT database format, commitments, expiry/reorg/monetary state. V1 LevelDB is not replaced. |

The machine-readable candidate file covers15 groups/29 selected owners with exact commits, every changed file, prerequisites, proposed placement, tests and risks. All154 retained owners are enumerated; the other owners are classified as native rule/codec/wallet/Chronik adapters or fixtures. This is a placement audit, not a fresh exhaustive correctness review of every line.

## First reviewable relocation

Start with149 only, after preservation below. Its compiled controller is already shared031, producers020/034 and RPC policy043 already exist, and Boost/node lifecycle are present. Move the existing logical commit into the shared tier using the branch-first workflow; resolve the two anchor/context differences without changing end-state bytes. Retain every production, lifecycle, queue, test and build hunk. Remove the original native149 occurrence, not its implementation. The source owner should run the configured branch-aware sink/rebase helper only against the authoritative assigned source checkout, not assume a different workspace is safe.

Required new-prefix evidence: compile shared daemon/core, fee queue overflow/newest absolute sample, generation/reorg reset, shutdown/drain and RPC fee-policy parity. Then replay the native suffix and its actual native fee/VM/snapshot checks. No benchmark is needed to prove a source-history-only move and no existing performance result is reattributed to a different tree without identity proof.

The pool/relay/tree items are deliberately not bundled into that first move: textual applicability is not a semantic dependency proof. Snapshot and tree extraction requires explicit interface work if the shared build otherwise lacks native types. That work must be isolated and reviewed as source changes rather than hidden in a supposedly tree-preserving shuffle.

## Hard preservation and accounting gate

1. Preserve all529 commits, original branch refs, all tracked files and dirty/untracked deliveries. Verify the existing recovery bundle plus any additional dirty-artifact archive; keep original refs and source. No force deletion, GC, pruning or production changes.
2. Before each move/split, fill a source-hunk→destination-owner map for **every** production/test/build/config/doc hunk, including metadata/deletions/binary deltas. The pre-move ledger here contains154 owners,2,312 file deltas and5,550 textual hunks, each with SHA256 plus whole-commit/file/metadata hashes. `proposed_new_owner:null` intentionally means no relocation has occurred. Every original hunk needs exactly one reviewed destination/disposition; textual similarity/title matching is insufficient.
3. A pure reorder/split must finish at the exact original **complete Git tree** `f58bb495…`, not just selected production files. Fail closed on `git diff --exit-code ORIGINAL_TIP NEW_NATIVE_TIP --` and unequal tree IDs; retain the actual diagnostic. All intermediate mailboxes/commits and buildable causal prerequisites must replay. Shared prefix changes intentionally and needs its own build/behavior gates.
4. Any necessary adapter, namespace, include, API or prerequisite change must be a separately recorded source delta, independently reviewed/tested, with exact intended tree change. Never hide it as a pure move. Native adapters must remain explicit.
5. Final branch split is linear, with no unsquashed fixups. Bug repairs fold into their causal owners using the prescribed fixup/autosquash workflow; genuinely distinct features retain one logical commit. Regenerate/pin through lotus-git tooling, not hand-edited maintained mailboxes. Preserve old refs/bundles and do not create private repos/submodules until this checkpoint is accepted and complete.

V1 may later consume suitable shared mechanics with its older API adapters and targeted tests. It is also a donor for correctly separated TxId/TxHash behavior. No migration of V2 BIP340 VM, address/header/currency/sighash/expiry rules into V1 is proposed. Mainnet state, published assets and validated V1 semantics remain untouched.

## Reproducibility and limits

`native-owner-source-inventory.json`: all154 retained native owners, exact source commits, messages and paths. `shared-mechanics-existing.json`: actual shared owner references. `PLACEMENT-CANDIDATES.json`: actionable groups. `NATIVE-HUNK-ACCOUNTING.json`: untouched source-hunk ledger. `shared-text-prerequisite-check.json`: read-only temporary-index applicability checks; they establish text context only, not builds, behavior or consensus safety. No source repository, branch or index was mutated by these checks.

## First actual batch: fee worker rehomed

The fee worker is now shared376, commit `59cf9ad39a529449eba48dc9544bcac3c0538071`. The final Lotus tip is `32573c721f1f31db5b67e8d1d7c31e2c4ec15f58`:376 shared +153 native =529 total. Complete final tree `f58bb4951d4431ab30f1b0363c7368f6969a5cb4` is byte-for-byte identical to the preserved pre-shuffle tree; the complete Git diff is empty and no fixup commits remain.

The original375 shared commits are unchanged. All154 original native owners and all5,550 original hunks have destination mappings. Added/deleted line sequences are identical for2,310 of2,312 file deltas. The two explicitly reviewed exceptions are041/149 snapshot.cpp: the generic time/backlog producer and include originally introduced in041 are now available at the shared fee-worker introduction. Original worker/body bytes are transplanted exactly; the native041 adapter retains its native fields. `SNAPSHOT-HUNK-EXCEPTIONS-PROOF.json` mechanically checks both expected file blobs. Every intermediate tree across the entire529-commit chain was reconstructed by applying each commit delta through a temporary index and matched exactly.

Validation: the new shared daemon/core build passed428 actions in87.34s; all8 fee-worker cases/48 assertions passed (generation, overflow, concurrency, stop/drain); a real node passed the explicit-check/default/reorg/shutdown functional. The final native unfiltered gate passed1,203/1,203 cases and31,483,542 assertions in43.68s using the preserved actual529 test binary whose complete source tree exactly matches the rehomed endpoint. No newly compiled native binary is claimed. Both original source heads and the new heads are preserved by refs/bundles; source and benchmark recovery records remain available.

The optional archival mailboxes are generated from the reviewed source commits using lotus-git export helpers, never hand edited. `FIRST-REHOME-HUNK-MAPPING.json`, `EXACT-TREE-PROOF.json`, `FULL529-REPLAY.json`, `PROMOTED-SOURCE.json` and actual build/test receipts provide the handoff. The first batch does not claim new runtime speedups: it changes placement, not the final implementation.

Pool134 was deliberately not moved. Actual source inspection found its manager implementation first appears at native059 and is absent the shared prefix. Moving134 alone would leave undefined types/missing code. Its generic service lifecycle can be rehomed only after a separate poolcore/nativeheader-payout adapter split. Next small candidates remain snapshot reset/defer hooks, followed by authenticated relay core and persistent-tree/hash-policy separation; each needs the same preservation/tree/test gate. V1 maintenance is optional, not this batch’s critical path.
