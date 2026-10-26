# Bounded development-chain candidate selection

Status: **implementation proposal for review, 2026-10-15**. This is the next
socket-free storage/coordinator packet needed for a usable isolated development
chain. It adds no consensus fork-choice rule, network activation or parameter
selection. [P04](../../decisions/header-and-mining.md) supplies accumulated
work and equal-work behavior; the [recovery proposal](lotus-v2-reorg-recovery.md)
supplies resumable execution. Clock policy remains an explicit development
integration choice, with D12 production choices open.

This document was written in a fresh worktree from `8914db51`, merged forward to
monorepo `cd04e0cf`. The inspected chain-index API is native
`97b78c6849e11f3be7188593c70a3387e0db84a4`; subsequent root source was also inspected
for the integrated download interface. The proposed recovery API/source were
read at `/private/tmp/lotus-v2-header-reorg-coordinator-20261015`, on that same
native base. At inspection, the draft header SHA256 was
`5e361c497e795f7e31832cd0508137b4bef81747069bbdbe339ef0110836ad70` and source SHA256
was `fb652a557b51047ffb38797075014d4520736d73bf3b054f95f1d722a6257b94`.
These identify inspected drafts, not reviewed runtime or release evidence.

## 1. Concrete gap and implementation target

`AdmitDevelopmentHeader` validates contextual ASERT/MTP/PoW and stores H.
`IndexedHeader` retains u320 accumulated work and the maximum timestamp of its
entire ancestry. `HeaderStage::Connected` means ever fully connected, not active
membership or available body bytes. A/I bind the active height mapping and tip to
the live S/coin/root/monetary tuple in one batch.

`PlanHeaderFork` compares exactly one supplied target to one expected active tip.
It returns bounded path lists, requires strictly greater work, and checks the
candidate's maximum ancestor timestamp. It does not enumerate candidates, find
the greatest eligible work, classify descendants of an invalid body, obtain
missing bodies or activate a chain. Repeatedly calling it with whichever peer
last announced a tip is not a candidate selector.

The next packet must enumerate the retained candidate inventory independently
of announcement order, identify the highest-work eligible header needing data,
and identify the highest-work body-ready branch worth attempting. Only complete
contextual execution may establish a new fully valid stable tip. Header-only
work and a body-ready attempt are not that conclusion.

The existing download coordinator already supplies bounded peer/BlockID jobs,
full/compact fallback, deferred recovery and connection-lifetime guards. The
recovery draft already supplies one pinned target attempt and exact source
restoration. The selector connects those interfaces; it does not replace them.

## 2. Inventory, validity and eligibility stay separate

Add a persistent candidate index in the same database as H/A/I/S. A process-local
heap populated only by recent peer announcements is insufficient after restart.

| Record / state | Meaning |
| --- | --- |
| Work-ordered candidate row | Retained nonactive admitted header, keyed by big-endian u320 work then BlockID; summarizes height and maximum ancestor time |
| Parent-to-child row | Bounded child-prefix enumeration for side-header cleanup and invalid-descendant propagation |
| Deterministic invalid-root fact | Exact previously admitted block whose complete, commitment-matching body failed deterministic contextual execution |
| Pending invalidation cursor | Durable bounded traversal of that root's retained descendants |
| Inventory counters/revision | Checked row/byte totals, schema/profile and resumable scan fencing |
| Body availability | Separate authenticated staged/retained body source; never inferred from HeaderChecked or Connected |
| Temporary candidate state | Eligible, future deferred, missing parent/body, resource blocked or recovery pending; never a permanent-invalid flag |

Candidate rows cover every retained nonactive header, including intermediate
headers. A missing/invalid high-work child must not hide a usable parent branch.
Active ancestors need no candidate row; disconnected headers become candidates
in the same atomic transition that removes their active mappings. A newly active
header leaves the candidate inventory in that transition. Historic H/undo/body
records retain their existing meanings.

The contextual header-admission path must reserve inventory space and publish
H, candidate/child rows and counters together. A later best-effort candidate write
after H publication would leave a durable admitted header invisible to selection.
Likewise connect/disconnect updates must keep candidate membership consistent
with A/I/S in the same batch. In candidate-index mode, trusted raw header/commit
capabilities must perform these updates or refuse the bypass; a second legacy
writer path cannot leave an admitted header outside the inventory. No second database is introduced.

Only an internal typed deterministic-validation result can create an invalid-root
fact. Malformed supplied body bytes, root/size mismatch during compact recovery,
unavailable parent/context/body data, lookup errors, temporary clock eligibility,
policy refusal, unsupported implementation, quota exhaustion and storage failure
do not create one. A definitive nonexistent or already-spent input in a complete,
commitment-matching body checked against its authenticated exact parent state is
deterministic consensus invalidity. Distinguish `CoinReadResult::Missing` in that
resolved state from `CoinReadResult::Error` or unavailable validation context.
`PrepareDevelopmentSwitch` returning InvalidBody can mean bad supplied framing or
header binding; that result alone must not globally invalidate the named header.
No diagnostic-string parsing or monetary `prev_work` ranking is permitted.

## 3. Ranked selection with bounded queries

Rank using `CompareChainWork` over the existing mathematical u320 accumulated
work. Never compare height, target difficulty alone, fee revenue, monetary state
or advisory votes instead. A successful replacement must be strictly heavier
than the stable active tip. At equal work retain that tip.

For equal-work nonactive candidates above the active threshold, BlockID byte order
may provide a stable local attempt/download order. This orders work, not consensus
validity: it creates no obligation to replace an already stable equal-work tip.

Read work-ordered rows in descending work with explicit per-call limits on rows,
iterator steps, underlying Gets, decoded bytes and resident candidates. Validate
summaries against H before using them. Existing PlanHeaderFork/Get accounting is
reused for ancestry and active-membership checks; an iterator is separately
charged before each Seek/Next/value operation. A max-Gets limit alone does not
bound an iterator scanning many entries.

A resumable scan carries a fixed-size ordered-key cursor, stable-source ID,
profile, invalidation epoch, body-availability epoch, sampled eligibility time/window
and scan revision. Do not load/sort every historical
header. An incomplete scan reports Progress/CapacityRefused and cannot claim a
global best result. New header insertion does not continually reset a lower-page
cursor: finish the bounded retained-window pass, probe new top work under a
separate bounded budget, then begin the next revision. A completed competitive
prefix may prune lower-work rows once none can outrank its ready choice; that is
an ordering proof, not an incomplete top-K approximation. A stable-tip change or
invalidity epoch change invalidates the selection view and requires revalidation.

Return separate choices:

1. **Best eligible header needing data:** the highest-work retained eligible branch
   not known invalid, with bounded missing-body IDs and its required parent path.
2. **Best body-ready attempt:** the highest-work retained eligible branch whose
   required replacement bodies can be authenticated and pinned within local
   limits. Full contextual execution still occurs in the recovery coordinator.

The first unavailable header must not permanently starve the second choice.
Missing-body work enters bounded download scheduling; resource-blocked attempts
receive an explicit retry condition/backoff. Selection among currently available
work is an availability limitation, not a declaration that a higher unavailable
chain is invalid. No claim of having activated the globally greatest fully valid
chain is made while required higher-work data remains unavailable.

Before preparing an attempt, fence the expected stable source, recheck candidate
work/ancestry, body availability, invalidity epoch and current clock eligibility,
and reserve complete preparation/restoration/invalid-receipt resources. A stale
view returns Stale, never a guessed fork. Record the earliest eligibility threshold
of skipped higher-work future candidates. Advancing time that crosses that
threshold requires bounded reranking before dispatching a lower choice; ordinary
clock ticks that cross none do not restart every page. Compute each threshold as
`maximum > window ? maximum - window : 0`. Clock rollback or window change
invalidates eligibility caches immediately. Body-arrival epochs similarly trigger
revalidation of competing availability before a best-ready claim. While that
work is incomplete return Progress, not an unjustified RetainActive/Ready. Only one prepared/recovering attempt may
own the writer. Higher-work arrivals wait in bounded inventory until it finishes.

## 4. Clock rollback and deterministic invalid descendants

Eligibility checks the authenticated maximum of **all** candidate ancestor times:
`maximum > now && maximum - now > future_window`. Do not check only the tip and do
not compute overflow-prone `now + future_window`. Clock source, now and window are
caller supplied. Future-deferred headers remain candidates and are reconsidered
on clock advances, restart and explicit polling.

The proposed development policy matches the recovery plan: a backward clock does
not detach an already stable valid tip or authorize a lower-work replacement.
Report that active tip's temporary ineligibility separately. A strictly heavier
candidate still needs its entire ancestry eligible. After recovery mutation has
started, loss of target eligibility restores the pinned source; deterministic
source restoration bypasses the new clock gate. These operational choices need
review before node integration; they do not close P04's production time decision.

A deterministic invalid-root fact excludes its retained descendants. Publish the
fact and a durable propagation cursor before allowing another selection attempt.
Process a bounded number of child rows per call. While propagation is incomplete,
selection is fenced; new side headers may only enter a separately bounded staging
queue, not escape through an unmarked descendant. This avoids an unbounded single
write or a repeated ancestry scan to genesis for every new header.

After propagation, descendants are excluded from the work index or carry an
explicit inherited-invalid reference. New children of excluded parents reject
at candidate admission without transaction execution. Preserve the causal root
fact across restart and reannouncement. An invalid fact contradicting an already
fully validated stable source is a local profile/index/validation fault: stop and
reconcile it; do not silently invalidate the source and choose another branch.

## 5. Durable recovery handoff and restoration failures

The inspected recovery draft deletes J at terminal completion before returning
`failed_block`/`replacement_invalid`. Recording that failure later in a selector
callback leaves a crash gap. This does not undermine per-step active-state safety;
it means the current coordinator is not a durable global candidate selector.

Choose one concrete extension: **a terminal receipt retained until selector
acknowledgement**. In the same batch that clears J, write a bounded canonical
receipt containing profile/schema, attempt/revision, source/target/current stable
IDs, terminal outcome and optional typed deterministic failed block. Its identity
binds the final source/target state tuple. No peer-supplied invalid flag is trusted.

Use typed terminal outcomes `CompletedTarget`, `RestoredSourceInvalidReplacement`
and `RestoredSourceDeferred`; a deterministic failed-block field is permitted only
for the second outcome. Minimal recovery additions are
`ReadDevelopmentSwitchReceipt(max_bytes, ...)` and an expected-receipt/stable-tip
acknowledgement batch hook. The selector acknowledgement below owns the atomic
invalid-fact/cursor publication, rather than calling journal cleanup and fact
publication separately.

The selector opens/reads pending J and receipts before exposing selection:

- Pending J yields RecoveryRequired. Continue the same pinned attempt only.
- A terminal receipt yields AcknowledgeRequired. Verify the observed stable tuple,
  then atomically persist the invalid-root fact and propagation cursor when
  required, reconcile candidate membership/counters, and remove that receipt.
- Receipt acknowledgement uses expected receipt identity and stable tip fencing,
  is idempotent after an ambiguous write, and never loses the failure between J
  removal and invalidity publication. A successful target receipt has no invalid
  fact; clock-driven source restoration has no deterministic invalid fact.

The coordinator must distinguish full deterministic replacement failure from
unsupported/resource/storage failures before producing such a typed receipt.
The inspected common bridge exposes Accepted/Invalid/StorageError; audit the
Invalid mapping before using it as that proof. If unsupported execution or an
operational host limit can reach Invalid, widen the result/adapter first rather
than inferring determinism from its error text or adding a consensus rejection.
Reserve room for the worst-case receipt, one invalid root and pending traversal
before disconnecting source state. Invalidity-ledger exhaustion refuses a new
attempt operationally; it does not evict facts and repeatedly retry a known bad
branch. Physical I/O failure still requires reopen and authoritative reconciliation.

If source restoration fails, keep J and its pins at the last valid checkpoint.
The selector must return RecoveryRequired/StorageError, not rank that intermediate
I tip as a new stable source. Do not start another target, drop the journal, clear
failure knowledge, invent a source state or advertise completion. Previously
accepted source-body validation failure is an operational profile/data fault, not
proof that the original source or its descendants became consensus-invalid.

Only exact restored source metadata/root/index, or exact completed target, ends
the writer fence. Body downloads/header staging may continue within independent
quotas; mining templates, stable-chain serving and unrelated state writes wait.
A post-sync error can have committed: reopen and inspect J/receipt/S/H/A/I before
repeating any step. The selector makes no multi-block atomicity or rollback promise.

## 6. Bounds, eviction, reannouncement and download integration

Configure counts/bytes for resident candidates, durable side headers, candidate
metadata, invalid roots/cursors, staged bodies, downloads and pinned attempts.
Also bound reads/iterator steps/path lengths and work per poll. All values are
explicit local arguments, not new consensus limits. Creation/retention caps and
bounded LevelDB value access are needed in addition to application copy limits;
trusted engine block creation bounds are distinct from arbitrary hostile database
rewrite. Full UTXO or full-header enumeration per poll is prohibited.

Candidate metadata and speculative side-header retention have bounded windows.
Historical active H/A/undo growth still requires an explicit disk quota and later
reviewed pruning policy; this plan does not claim infinite history in finite disk.
Capacity refusal preserves the current valid chain and reports a synchronization
availability limitation rather than permanently rejecting a valid object.

At window pressure, evict only an unconnected, nonactive, unpinned side leaf with
no retained children; update H/candidate/child rows and counters atomically. Choose
lower-work expendable leaves before a stronger incoming candidate. Never remove
an active ancestor, pending recovery/receipt dependency, invalid-root fact or
parent still required by a retained descendant. If no safe leaf exists, return
CapacityRefused before admitting the new header. Do not silently leave H accepted
but unranked. Eviction is forgetting speculative data, not invalidation.

Older ever-connected side records below stable active work may leave the ranked
window while remaining historical H/body/undo records: successful stable work
never decreases, and any newly admitted descendant re-enters as a candidate.
Explain this archival distinction in diagnostics. A retained eligible header
above stable active work must remain enumerable or be explicitly evicted under
the permitted speculative-data rule; there is no hidden top-K heap approximation.

Reannouncement of an evicted valid header can re-admit it when space permits,
including parent-first header reacquisition. Bounded rescan/reannouncement and
body-arrival notifications wake deferred candidates. Within a finite stable
retained workload, fair polling, advancing eligibility time and eventually
available bodies must lead to attempting the greatest eligible work and retaining
the greatest fully validated completed tip. No finite-window implementation can
promise discovery of a forgotten branch that is never announced again; quota
saturation and adversarial churn must be visible, not a hidden liveness claim.

For missing replacement bodies, return bounded `(BlockID, header)` needs to the
existing DownloadManager. That owner chooses full/compact, tracks peers, leases
and retries, and returns complete bytes to bounded durable staging. Body staging
checks exact header binding/framing/TxRoot; contextual validity remains pending.
A body-ready notification does not promote H to Connected. Preparation pins all
replacement and source-restoration bytes before active mutation.

On candidate eviction, obsolete download work may be canceled, but its peer/BlockID
lifetime guard remains until disconnect. Reannouncement uses another peer or a
new connection when the old lifecycle is retired; it must not clear the download
guard. Source-restoration body unavailability is a recovery preparation blocker,
not a reason to disconnect the source speculatively. Existing NODE_NETWORK service
promises still require independently verified retained-history availability.

## 7. Minimal implementation packets and tests

Implement this as three bounded packets, not a new general networking framework:

1. **Persistent inventory and receipt hooks:** extend `disk_state.{h,cpp}` and the
   contextual `header_admission.{h,cpp}` path with atomic candidate rows/counters,
   bounded paged queries, child traversal and invalidation acknowledgement. Add
   recovery receipt hooks in `reorg_recovery.{h,cpp}` through the recovery owner.
   Use an explicit new local indexed-home schema; refuse old homes without reset
   or automatic full-scan migration. Preserve generic raw-store modes and existing
   worktrees. A separate validated replay into a new home remains possible.
2. **Selector:** new `src/lotus_v2/candidate_selection.{h,cpp}`,
   `test_candidate_selection.cpp` and `candidate_selection_test/{CMakeLists.txt,
   README.md}`. Keep storage-facing record/budget types in its header with a
   forward declaration of DiskStateStore; shared build registration remains root
   owned. No socket, profile loader, consensus math change or arbitrary callback
   can publish an active tip.
3. **Existing coordinator/download adapter:** feed bounded selector picks into
   existing Prepare/Step recovery, acknowledge its receipt, and turn missing-body
   needs into existing DownloadManager requests. Add one offline competing-chain
   scenario using existing explicit fixtures and the actual common validator.

Proposed narrow public surface, with all limits explicit:

```cpp
enum class CandidateResult {
    Ready, NeedBodies, Deferred, RetainActive, Progress, CapacityRefused,
    Stale, RecoveryRequired, AcknowledgeRequired, Unsupported, StorageError
};
CandidateResult PollCandidates(const Hash &expected_stable_tip,
    uint64_t now, uint64_t future_window, const CandidateLimits &,
    CandidateScanCursor &, CandidateChoices &, DiskStateStore &, std::string &);
CandidateResult AcknowledgeCandidateReceipt(const Hash &expected_receipt,
    const Hash &expected_stable_tip, const CandidateLimits &,
    DiskStateStore &, std::string &);
CandidateResult StepInvalidDescendants(const CandidateLimits &,
    DiskStateStore &, std::string &);
```

Choices carry expected source/index epoch, best eligible header and best ready
attempt separately, bounded fork/body needs, and scan-completeness status. No
Ready result is emitted until every higher-work competing retained row has been
classified under the same fenced view (or excluded by the ordered-prefix proof). The recovery owner adds
bounded receipt read/ack batch plumbing; the selector does not reinterpret raw
journal diagnostics. Exact type layout is implementation review work, not a new
wire allocation.

Required acceptance tests:

- Multiple competing retained branches where the latest announcement, greatest
  height and greatest work differ; choose work and retain exact active-work ties.
  Intermediate candidate recovery after an invalid/unavailable child is included.
- Greater-work unknown bodies versus a lower ready branch; bounded fetch/retry,
  valid body arrival, full/compact identical bytes and eventual best valid target.
- Future ancestor with an earlier-time descendant; clock advance/rollback,
  ineligible active diagnostics, restart and overflow-safe all-ancestor checks.
- Deterministic bad-signature/state/monetary replacement with commitment-matching
  full bytes; exact source restoration, durable failed-root exclusion and bounded
  descendant propagation, including a newly announced child during propagation.
- Malformed supplied/compact bytes, unsupported VM/profile, resource/read limits,
  storage errors and ambiguous writes never publish deterministic invalid facts.
- Crash after J removal but before selector execution, during receipt acknowledgement
  and propagation batches; reopen resumes the exact receipt/cursor without losing
  invalidity or confusing an intermediate recovery checkpoint with a stable tip.
- Missing/corrupt source undo/body, restore validation disagreement and failed sync
  keep recovery fenced; a healthy source is never silently abandoned.
- Exact resident/disk-row/byte/query limits, pre-read reservation and batched progress;
  safe leaf eviction, parent protection, reannouncement, pinned-data refusal,
  invalid-ledger saturation and a finite-window fairness/liveness scenario.
- Header admission and active connect/disconnect crash tests show H/C/child/counters
  remain consistent with S/H/A/I. New schemas fail closed on old homes.

Use actual native store/recovery/validator fixtures for final activation and faults;
mocked ranking alone cannot satisfy this gate. Signed mature spends and the existing
compiler pilot must retain their intended acceptance/negative behavior. Report
module/source tests separately from network synchronization. This document records
source inspection and a proposed implementation plan only; it runs no selector,
recovery, socket or testnet and does not freeze production parameters.
