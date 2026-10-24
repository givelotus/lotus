# Reconciliation and voting over mempool epoch candidates

**Current implementation scope:** [permissionless adaptive pairwise reconciliation](research/pairwise-reconciliation-scheduler.proposed.md) proceeds independently of staking, Avalanche, epoch finality and a causal clock. The lifecycle below constrains a future integrated epoch implementation; it must not be installed as an eligibility gate on ordinary reconciliation. The isolated scheduler experiment does not itself repair existing full-set representation limits or implement authoritative epoch sealing.

Status: core lifecycle architecture approved after two independent review rounds, 2026-10-21. The real Avalanche-based clock mechanism and authoritative trace vectors remain unresolved and unapproved; production protocol/lifecycle promotion stays paused for that contract. The earlier full-mempool design omitted the user's epoch ownership requirement and its reviews do not cover this lifecycle. Generic immutable canonical-node storage remains reusable.

## Related research

Alternative epoch-formation designs are investigated outside this specification: the [root-gossip loop proposal](research/epoch-root-gossip-loop.proposed.md) (shared slot names, forwarded preferences, repeated voting, locked-root catch-up) and its companion studies in [research/](research/README.md). None of them amends the lifecycle below. Candidate-context validation can require bounded bodies not admitted in the conflicting live mempool; see the root-gossip study before treating the resident-body-only fast path in §4 as universal.

## 1. The required behavior

At the epoch boundary, N1 has `AB | D`, while N2/N3 have `ABC | D` (`ACB` is the same set). The left side is the epoch under reconciliation and voting; the right side is the open top. N1 recovers C for that epoch while ordinary new transaction E arrives. The result must be `ABC | DE`.

The epoch is revised and voted on again. If peers still disagree, its new proposal is reconciled again. One reconciliation cycle is not assumed to finalize an epoch. Merely inserting C into the global current mempool, producing `AB | DCE`, does not meet the requirement.

## 2. State and ownership

Use the existing canonical TxId/TxHash Merklix node engine for all views. There is one global admitted transaction store M. Roots share immutable nodes and transaction bodies; candidate membership is scoped metadata/view ownership, not another global admission authority or SID registry.

For one chain anchor, maintain:

* Finalized cumulative parent F, identified by exact parent BatchId (or the chain's empty initial parent).
* One revisable epoch slot e = `(parent_block_hash, parent_batch_id, epoch_seq)`. Its working candidate W_e includes F and the selected current epoch members. A local owner generation distinguishes a cancelled/recreated slot even if wire fields repeat.
* Immutable proposal P_e,r: exact membership root plus complete announcement commitments and unique BatchId. The local revision r is bookkeeping; wire identity is BatchId. A working root is never itself a mutable vote target.
* Open top U: admitted live identities not assigned to W_e. In the ordinary live/eligible case, `U = M \ W_e`; epoch delta is `W_e \ F`. Neither is computed from count subtraction. A changed-path maintained view or direct scoped membership queries may implement this relation.
* Per-peer reconciliation round R: exact slot, immutable remote proposal, immutable local candidate revision captured for comparison, prefix cursor and request ownership. Round completion is separate from epoch voting/finalization.

This first implementation supports one revisable epoch at a time, plus finalized ancestors and many concurrent peer rounds for that epoch. The successor is opened only after its parent proposal finalizes. This is a deliberate simplifying rule consistent with deriving the next slot from the last finalized batch; it avoids silently rebasing already-voted descendants. Ordinary admissions continue into U throughout. Multiple simultaneously revisable epochs are outside this contract.

At the epoch cut, under the mempool/epoch mutation owner, select the complete eligible top membership into W_e over F and open an empty U. Subsequent ordinary admissions change M/U, not W_e. The cut does not hash the whole tree under the lock; it captures owned roots and metadata. Existing cumulative frozen layers are not sufficient to identify these memberships without the explicit owner relationship.

## 3. AB|D with C recovery and E admission

| Event | Global M | Working W_e | Open U | Proposal/votes |
|---|---|---|---|---|
| Epoch e opened; D subsequently arrives | ABD | AB | D | Immutable P_AB; votes belong only to its BatchId |
| N1 compares against peer's P_ABC | ABD | AB | D | Round pins `(P_AB, P_ABC)` |
| E arrives normally | ABDE | AB | DE | P_AB and comparison pair unchanged |
| C passes normal validation and verified epoch association | ABCDE | ABC | DE | P_AB superseded locally; prepare P_ABC/new local proposal |
| ABC candidate/announcement checks complete | ABCDE | ABC | DE | Fresh root-bound votes for new BatchId; no AB confidence carry |
| Another discrepancy is disclosed | unchanged until admitted | possibly another revision | unrelated top stays separate | Pin a new proposal pair, zoom, revise and vote again |

If C arrives normally before its recovery response, M already contains C and U initially includes it. Verified epoch association moves its classification from U to W_e without reinsertion. If the valid recovery path is first, the admission operation carries its epoch target through validation and associates that admitted incarnation. Duplicate responses are idempotent. A short asynchronous interval between global admission and association is permitted, but the pending association is explicit, owned and bounded; it cannot be mistaken for a completed epoch revision.

If AB finalization wins before C association, AB stays finalized and C belongs to the current top/successor. The example's ABC result applies while e is revisable; no protocol can revise a finalized root by relabeling votes.

## 4. Admission carries a trusted, owned epoch target

The transaction consensus serialization is unchanged. Epoch/proposal association belongs to GETSHORTTX/SHORTTX request context and the local admission job, not a new transaction field.

When scheduling a recovery request, store an owned `EpochAssociationTarget` containing the local slot owner generation, slot identity, exact remote BatchId/root, originating peer/connection/context/request identity and captured local candidate revision. The target is created only by the validated round registry, never by copying an arbitrary peer-provided epoch number. It keeps required proof/context ownership alive within the round's reservation, with explicit cancellation. No raw pointer to a vector entry or mutable epoch object survives asynchronous validation.

The response path:

1. Match exact outstanding peer/connection/context/request ownership, scope, prefix and mode. Verify exact TxId/TxHash and membership/reconstruction against the pinned remote proposal. A decoded SID alone is not membership evidence.
2. Pass body plus the owned target through ordinary transaction validation/admission, including asynchronous/batched queueing. No epoch context grants a validation bypass. The already-present fast path requires the same resident TxId **and TxHash**; `exists(TxId)` alone is insufficient.
3. Record the admitted exact incarnation (TxId, TxHash, admission generation or equivalent stable entry identity). Under the mutation owner, recheck current chain parent, revisable slot owner, target validity and that this exact incarnation remains admitted. An expired/finalized/cancelled target cannot rewrite historical membership. A still-valid body may remain in M/U through ordinary admission.
4. Prepare the candidate addition against the current W_e and its parent state. This must be dependency-closed and valid for that candidate, not merely valid against global M. Hash/state work happens outside mutation locks on owned candidate views. At the final commit, recheck the captured parent, W_e revision, live target/slot generation and the exact resident TxId/TxHash/admission incarnation again; any can change during preparation. A removed/re-added C cannot be promoted through its old callback even if W_e never changed. Retry boundedly against current W_e where appropriate, merging idempotently rather than overwriting another worker's C/F addition.
5. Atomically commit the new W_e, remove the identity from top classification if present, increment working revision, supersede the old local preferred proposal, cancel its local polling eligibility and queue fresh proposal preparation. M contains the transaction only once. Until a complete new proposal is ready, the slot is pending and does not emit a positive vote for stale membership.

Candidate validation includes the full TxId/TxHash commitment, exact count, ordered-identity digest (`short_ids_hash` currently hashes CTOR TxIds), UTXO result, parent block and parent BatchId relationship. Candidate UTXO/cost/fee data may reuse existing overlay machinery, but must describe W_e, not M including U. A C that depends on D from U cannot make a claimed ABC candidate valid unless D is already in F/W_e. Do not silently import unrelated top entries to make an invalid advertised set pass. The transaction can remain globally valid while that candidate remains unready/rejected.

Removal/replacement changes M and its mutable ownership classification and invalidates in-flight association for the old incarnation. A removed member of the revisable delta W_e\F revises/invalidates W_e under the same owner before finalization can commit. A member of finalized F is different: never erase it from F or rewrite a cumulative parent obligation. Block consumption changes the chain anchor through the normal transition; other removal/conflict cases invoke existing finalized-transaction policy and invalidate/suspend the current slot if its exact parent can no longer be realized. Published P_e,r roots remain immutable. Reorg cancels old-parent mutable slots, request targets and proposal eligibility; retained historical objects are not current-chain acceptance evidence. Compatible live transactions are reassigned through normal new-parent validation, not old callback replay.

## 5. Zoom is always between two frozen versions of the same epoch

A disagreement or a poll for an unknown/unready proposal starts reconstruction of that exact proposal. Pin the remote P_Q and a local P_L/W_e revision for the same slot. The round's compare pair is immutable until the round ends/cancels. It never substitutes the full current M, open U or a newer W_e while processing another response.

At root equality, both captured transaction memberships match; full announcement/state validation is still required for voting. Otherwise compare canonical prefix digests. A mismatch causes the existing sixteen-way Merklix expansion. All sixteen children must fold to the pinned parent digest using canonical absolute-depth/singleton rules. Only mismatching children are explored. Counts are checked for shape/overflow and used as bounded hints; current canonical hashes do not independently authenticate numeric counts.

Where available, same-domain GF(2^64) s1/s3/s5 differences try to recover one or two SID hints. Resolve bounded candidates and patch a temporary local prefix; only an exact match to the pinned remote prefix digest establishes the hinted difference. On ambiguity, excess differences, collision, missing SID lookup or failed digest verification, zoom deeper. Prefixes extend to all 256 TxId bits; exact leaf TxId/TxHash recovery is the terminal fallback. No first-4096 or age-selected subset and no truncated terminal list.

For AB versus ABC, zoom reaches the prefix containing C, or BCH identifies C in a larger mismatched prefix. The resulting verified identity is carried to the admission/association path above. E's arrival in U cannot change that compare pair or its prefix hashes. If C changes W_e, the old pair still refers to AB/ABC; its remaining disclosures can be safely verified against those roots, but cannot establish completion of the newer local proposal by implication. New voting/reconciliation uses a fresh pair with the new root. Round state and old proposals are bounded; cancellation restarts from current roots without reusing stale equality conclusions.

Keep two kinds of progress separate:

* Prefix progress: completed/missing ranges for one pinned pair; body transfer and admission outcomes are tracked independently.
* Avalanche progress: confidence and preference for one immutable BatchId, under existing quorum/threshold rules.

Finishing zoom is not finalization. A vote disagreement is not proof that the compared data was invalid. A working revision is not permission to transfer either prefix equality facts or vote confidence to a different BatchId. Unchanged authenticated subtrees may reuse computation, but not unsupported whole-round conclusions.

## 6. Proposal, vote and finalization state machine

For the current slot, use explicit states:

`OPEN -> PREPARING(r) -> READY(P_r) -> POLLING(P_r)`

An ordinary top admission leaves these states unchanged. A verified candidate association/removal moves the slot back to `PREPARING(r+1)`, marking P_r `SUPERSEDED` for local polling. A missing remote proposal is `RECONSTRUCTING`, not invalid. Preparation/round failure may retry/back off without manufacturing a vote. A locally verified ready proposal becomes the slot's sole preferred proposal; only that exact eligible proposal receives local positive preference votes. A truly invalid proposal is rejected on its own evidence. Finalization is an atomic transition from a complete eligible preferred proposal to `FINALIZED(P_r)`.

Different BatchIds in the same slot are alternatives/revisions, not automatically transaction conflicts. Remove the current “different root poisons entire slot” rule and the rule that every nonzero vote marks an epoch conflicted. Known-but-incomplete/reconstructing proposals return existing neutral/unknown `UINT32_MAX`, not definitive rejection `1`; accept is `0`. The neutral value is inconclusive and must not become conflict evidence. A complete valid but nonpreferred alternative may receive a negative preference response, but that response does not mean consensus-invalid, does not poison the slot, and does not permanently ban later valid revisions.

Within a slot, preference follows the locally selected dependency-valid W_e revision. Learning valid missing epoch members can enlarge it; local conflicts/replacements follow existing transaction admissibility/conflict rules, not arrival-order-only acceptance of an arbitrary remote root. Remote candidates may be reconstructed without replacing W_e or being positive-vote eligible. Compatible cumulative membership can converge by learning missing members; root disagreement alone does not establish an incompatible spend. Revisions are rate/work/retention bounded; a malicious peer cannot allocate arbitrary epoch slots or force unbounded candidate history.

Existing vote identities remain exact BatchIds, but local poll bookkeeping additionally binds a monotonically increasing preference activation token `(slot_owner_generation, working_revision, activation_generation)`. This prevents an AB→ABC→AB cycle from crediting old AB responses to a newly activated AB record. Each activation, including reuse of a previously seen identical BatchId, starts a fresh VoteRecord. Outgoing query item records capture that activation token with the existing poll/response round; stale-token responses are discarded before confidence mutation. Timeout/cancel cleanup also checks activation ownership and cannot consume a new record's in-flight state. In-flight responses cannot restore superseded eligibility. No threshold is weakened, and no all-peers-complete barrier is invented. Existing Avalanche sampling/quorum assumptions still govern distributed preference; this repair adds the explicit local exclusive-slot eligibility gate that prevents independent old/new records from both finalizing locally.

Finalization and candidate promotion share one serialization point. Before recording finalized status or invoking callbacks, verify atomically: current parent/slot, exact preferred BatchId/revision/activation, full local candidate validation, applicable unchanged quorum/threshold result, and no already-finalized winner for that slot. If candidate promotion wins first, delayed AB finalization fails the version/preference check. If AB finalization wins first, late C cannot revise it and is left in U/successor. A denied transition emits no Finalized update, recently-finalized marker, callback or next-epoch trigger; all processor/net_processing paths must consume the successful owner transition, rather than independently finalizing from a raw VoteRecord threshold. Do not first mark a batch finalized and optionally try to find its bodies afterward, as current source does.

Finalization fixes F := P_r, ends the revisable slot, and permits opening successor e+1 from current U over that exact parent BatchId. Previously published incompatible/superseded roots may survive only for bounded historical request/vote cleanup, never as a second finalized winner. Existing block pre-consensus policy can inspect finalized cumulative roots; no block consensus rule or already finalized root is rewritten by reconciliation.

## 7. Wire and context binding

Use the existing Merklix command family and the existing epoch-batch concept with an explicitly negotiated versioned extension. Actual source calls the scope `EPOCH_BATCH = 0x02`; older prose calls it PRECONSENSUS_EPOCH. Preserve old layouts for peers lacking the capability; they cannot claim this lifecycle. Do not advertise the earlier FULL_MEMPOOL scope as a substitute for epoch candidate reconstruction.

Epoch voting under these semantics requires a lifecycle-capable participating cohort. Do not count an old peer's incompatible batch behavior as if it implements exclusive preference/version rules, and do not reduce quorum, stake or confidence thresholds to compensate for too few capable peers. Without the unchanged required quorum among eligible participants, no epoch finality is claimed; ordinary transaction/block availability remains available.

Every extended command has `scope:u8, version:u8, context_id:32`. For an epoch offer, context_id is a sender-owned immutable proposal-view token. The offer additionally carries the complete existing 168-byte `MempoolBatchAnnouncement`, an explicitly recognized sketch-domain identifier (or sketches absent), and the root's sixteen canonical descriptors. Verify its computed BatchId and slot before allocating substantial work. The existing announcement already binds parent block, parent batch, epoch sequence, transaction root, UTXO root, count and ordered-identity digest; do not add a mutable “epoch transaction” consensus field.

Local round registry binds `(peer, connection, scope/version, context_id)` to the exact remote announcement/BatchId, captured local root/revision and owned slot generation. GETMERKLIXBUCK/MERKLIXBUCK and GETSHORTTX/SHORTTX echo context_id plus non-reused request_id; request ownership additionally binds prefix/depth/mode. Thus bodies crossing the admission queue retain the trusted target without carrying an untrusted standalone transaction epoch tag. Fresh proposals have fresh view tokens; token reuse cannot mutate an existing request's meaning.

Wire discovery must be implemented, not assumed from existing stubs. The epoch scheduler invokes the owner when a valid parent and adaptive cut condition permit a new candidate; the current tryFreezeAndRegisterNextEpochBatch has no production caller at the audited pin. A new READY proposal sends its AVABATCH announcement and bounded matching epoch Merklix offer to negotiated peers. An unknown MSG_AVA_MEMPOOL_BATCH poll triggers a bounded GETDATA request for that exact BatchId; serving that inventory type returns the matching AVABATCH and an epoch view offer if retained/available. Receiving the announcement stores an unready bounded candidate and starts reconstruction only after the matching owned offer is accepted. An unavailable/expired proposal remains neutral and retryable; an unknown poll does not create arbitrary accepted slot state. No new page/download command is required, but existing GETDATA/AVABATCH dispatch must actually support this path and honor request/rate/byte bounds.

Reuse the reviewed bounded prefix/body encoding mechanics: u16 depth 0..256, full canonical 32-byte prefix, exact child digests, checked u64 descriptor counts, optional s1/s3/s5, bounded SID hint mode and exact identity mode, complete/explicitly unavailable terminal bodies, limits checked before allocation. Child index bit j is canonical path bit depth+j; the first fold split is even/odd indices. Scope-specific root offers include the announcement; old full-pool epoch_id-only offers do not. Full precise serializers and capability numbers must be checked against the final integration base before code promotion.

Epoch sketch identity must be fixed for a compare pair. This lifecycle does not authorize a global fixed salt or arbitrary per-peer key rebuild. Start with the recognized existing chain-epoch SID domain for shared-cache reuse, recording it independently from the voting slot. If retired, keep exact prefix/TxId reconstruction available with sketches absent; voting-epoch identity and SipHash-key epoch are not the same field. Changing this key policy to the older plan's per-voting-epoch derivation is a separate explicit decision with O(N) rekey cost.

## 8. Storage, concurrency and resource boundaries

The owned immutable canonical node engine, nonblocking completed-hash cache publication, changed-path updates and bounded hash workers from the earlier source-grounded design remain applicable. Global M publication and epoch W_e publication are different events; a root obtained from global mapTx cannot be passed off as the epoch root. Existing UTXO/monetary overlay machinery must be invoked for the selected candidate membership when preparing its announcement. No O(N) full-pool copy/hash per peer poll, no new persistent SID tree and no independent relay admission authority.

Serialize mutable epoch/top classification with mempool membership/incarnation changes under the established owner/lock discipline. One safe integration is mempool.cs protecting mutable W_e owner/revision/top association, with expensive candidate preparation outside it. PREPARING→READY also commits under this owner with the exact captured generation/revision; delayed ABC preparation after removal/reorg/a newer revision must fail its comparison and cannot reinstall preferred ABC. The owner commits state before emitting immutable events. Consumers validate event token/activation against current owner eligibility; a queued stale supersession/READY event cannot authorize a new positive vote or poll from an old processor copy.

The processor receives events after releasing mempool.cs; it must not acquire mempool.cs while holding voteRecords or cs_mempoolBatches in an inverse order. Before finalization, the version-checked owner operation is the shared race boundary; external callbacks run after locks are released. A check followed by unlocked registration/finalization is insufficient. Implementers must document actual lock order/owner handoff and test it, including readiness and removal races, not merely add another mutex.

Bound active proposals, epochs, rounds, admission targets, prefixes, candidate patches, workers, bodies and all side maps together. One revisable slot and a bounded finalized/retained history replace unbounded arbitrary epoch_seq metadata. Count new candidate views against conservative full reachable-root exposure reservations, including retained bodies and cache/scratch values. Cancelled work retains its charge until it drains. Existing finalized policy records cannot be evicted in a way that silently forgets an active policy obligation; history retention follows chain-parent lifecycle and existing policy requirements.

Use fair admission and bounded per-peer work. Never evict useful older work merely to accept a new peer offer. Unknown/unadmitted offers may be dropped/deferred without an undefined status reply; BUSY answers actual requests only. Lifetimes and budgets may cancel reconstruction, not mutate finalized proposals or silently mark incomplete prefixes complete. Late valid bodies fall back to ordinary M/U admission if the target is gone; unsolicited policy still applies.

## 9. Required tests and explicit limits

* Exact three-node `AB|D`, `ABC|D`, `ACB|D` scenario, C/E in both orders, followed by fresh ABC votes. Show a second mismatch/zoom/revision/vote cycle rather than assuming one pass finalizes.
* Force BCH collision/overcapacity, exact prefix descent and unchanged compare roots while W_e/U mutate. Verify prefix cursor and Avalanche confidence remain separate.
* Already-admitted C, duplicate responses, two peer workers adding C/F concurrently, removal/readd incarnation races and same TxId/different TxHash. Assert no lost update, double admission or stale association.
* Candidate dependency on top-only D, incorrect announced UTXO/parent/digest, missing candidate bodies and neutral votes. No positive vote or finalized status before full candidate checks.
* Delayed AB vote/finalization racing C promotion in both orders. Exactly one finalized winner; no AB confidence transfer to ABC; no whole-slot poison from neutral/rejection or compatible revisions.
* Parent reorg, cancelled/expired owner target, late body, arbitrary epoch_seq flooding, bounded old proposal versions, worker cancellation and retained-root memory accounting.
* Publication failure injection/retry proves paired global numeric/canonical views remain coherent; scoped candidate publication is audited independently.
* Existing canonical root/hash/sharing/concurrency gates and exact 500k three-node inventory/digest convergence remain necessary for full availability, but do not replace these epoch/voting tests. No WAN ceiling or production-finality claim follows from loopback convergence.

This protocol cannot prove that every peer has revealed every possible eligible transaction before finality. A proof of membership in an immutable advertised proposal proves set association, not an objective wall-clock creation/admission time; clocks cannot authenticate an unstated transaction origin. The user's explicit requirement to admit recovered missing C into an epoch already under voting supersedes the older plan's blanket local pre-voting-admission cutoff. Do not silently retain that cutoff and strand C. Revisions are bounded/rate-limited and can be deferred on resource exhaustion, but no unconditional anti-drip convergence claim is made. Progress requires honest service, sufficient resources and existing Avalanche/network assumptions. Discovered valid missing epoch membership is routed into the revisable candidate, followed by a fresh proposal/vote cycle, without dragging unrelated top arrivals into it or rewriting finalized history.

## 10. Real clock contract still required (open)

Audited source has no distributed vector clock. Local epoch counters, parent BatchIds, poll round numbers and vote confidence do not constitute one, and the older plan's finalized-epoch causal header and separate bucket-progress vector are not an implemented per-origin transaction clock. Remote progress claims cannot replace local finality; a clock alone cannot authenticate C's membership in a proposal.

A selected mechanism must specify origin identity, update/receive/merge rules, cut creation, trust, wire commitments and bounds before machine-readable clock/lifecycle vectors or an implementation harness can be accepted. Observer-only timestamps are not a substitute. Candidate mechanisms (the exact parent-BatchId chain as a scalar causal order, bounded peer-progress observations, an authenticated heartbeat DAG, and publisher microbatch chains with committed contributions) are compared in the [clock option study](research/epoch-clock-open-questions.md) and the [committed-contribution review](research/epoch-contribution-proposal.md); none is selected, and the lifecycle above is not amended into publisher-cut semantics.
