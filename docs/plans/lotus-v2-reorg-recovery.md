# Resumable development-chain switching and recovery

Status: implementation proposal for review, 2026-10-15. No source change,
network activation, launch parameter, automatic selection policy or new consensus
rule is established by this document.

## Inspected implementation and remaining boundary

This proposal was written in a new monorepo worktree created from `8914db51` and
merged forward to `00abefa6`. It inspects the development native implementations
in `/private/tmp/lotus-v2-chain-index-native-20261015` and the root integration
worktree. The index and admission work was still being integrated when inspected;
these paths identify the design checkpoint, not an immutable release approval.

`DiskStateStore` commits each accepted block's coins, authenticated UTXO root,
header/monetary/history/body metadata (`S`), immutable undo (`U`), connected header
record (`H`), active height (`A`) and active summary (`I`) in one synchronous
LevelDB batch. Disconnect checks the restored inverse view and the enclosing
metadata callback before publishing a batch; it retains `U` and the header's
`Connected` stage. `Connected` means ever connected. It does not imply current
active membership. Indexed genesis cannot be disconnected.

`PlanHeaderFork` compares one supplied candidate with one expected active tip. It
requires strictly greater cumulative u320 work, checks the candidate's maximum
ancestor timestamp against explicit `now` and `future_window`, and returns bounded
source-to-fork disconnect IDs and fork-to-target connect IDs. It does not enumerate
all candidates, choose a global best tip, establish body availability or execute
transactions. Exact ties retain the current tip. Header admission validates
canonical target, PoW, parent/height/version, ASERT and median time, but accepts
roots and size as untrusted commitments. Neither a `HeaderChecked` record nor a
fork plan establishes complete-block validity.

`ReadRetainedBlockBody` checks framing, transaction root, identity/PoW and stored
monetary/root agreement. Its response quota currently limits the subsequent copy
and decode, not the backend's allocation of the entire immutable undo row.
`ConnectStoredDiskBlock` executes full bodies against the active state, derives
height/MTP from stored ancestry and publishes one block. `ConnectEligibleDiskBlock`
adds explicit external-clock eligibility for its candidate header. A reorg caller
must additionally enforce the plan's all-ancestor eligibility. Per-block atomicity
and these helpers do not yet make a multi-block switch recoverable.

## Required invariants

There is one writer and at most one pending switch per indexed chainstate home.
Ordinary connects, disconnects, another switch, pruning and profile changes are
refused while the journal is pending. Header/body arrivals may continue only
through bounded append-only staging that cannot change the active state or the
pending plan's pinned bytes. No caller may bypass the coordinator to publish an
active block during recovery.

Every durable checkpoint is a complete valid state tuple with matching `S/H/A/I`,
coins, root, monetary record and recent history. A multi-block switch exposes
intermediate checkpoints internally; they must be labelled as recovery in progress,
not advertised as a completed new active chain. No whole-reorg atomicity is claimed.
After a successful switch, the completed tip is the selected target. After a
replacement body fails deterministic validation, the completed tip is the exact
original source. An operational failure can leave a pending journal at a valid
intermediate checkpoint until storage or resources become usable again.

Only full contextual execution may promote a replacement from `HeaderChecked` to
`Connected`. Previously connected blocks are also replayed through full validation
when reconnecting, rather than treating a historical stage or retained body as a
UTXO delta that can be blindly applied. Restoration must reproduce the original
source metadata/root/index exactly. A disagreement is a storage/profile failure,
not permission to fabricate an alternative source state or change consensus.

## Journal and pinned data

Add a local storage schema version for journal-aware indexed homes. Reject older
homes without reset or implicit migration. A separately reviewed replay into a new
home remains possible. The journal is a dedicated `J` record outside `S` and outside
per-block `U` records, so reconnecting a block does not change its immutable undo
bytes merely because journal phase/cursors differ.

The versioned, canonical journal contains:

- ChainID, exact genesis ID, validator storage fingerprint and journal schema.
- A unique local attempt ID, revision and immutable plan digest. The digest covers
  all plan fields with explicit framing under a local storage-only domain.
- Source, target and fork IDs; their exact indexed heights, cumulative work and
  maximum ancestor timestamps; the source's complete metadata/root snapshot.
- Ordered disconnect and connect ID lists, and immutable digests/lengths for every
  pinned source body, replacement body and required source undo row.
- Admission limits accepted during preparation; the caller's observed `now` and
  explicit future window for audit only. Stored clock observations never establish
  continuing eligibility.
- Phase, completed disconnect count, completed target-connect count, completed
  replacement-rollback count, completed source-restore count, expected current tip
  and root, and any deterministic failed block ID/reason.

Counts and byte lengths are checked before allocation, and every list must exactly
match the indexed parent links and heights back to the configured genesis. Reject
unknown versions, trailing data, duplicate IDs, inconsistent cursors, overflow,
source/target/fork mismatch and profile mismatch. Journal revisions never wrap;
exhaustion is an operational refusal before mutation.

Replacement bodies need bounded durable staging because the retained-body API
only addresses locally committed records. The initial implementation embeds exact
source and replacement body bytes in the capped `J` payload, with their identities
and lengths, rather than adding a separate body store. Preparation checks header
binding, canonical framing and TxRoot; full contextual validity remains pending.
The journal retains these bytes through restoration or target completion. Do not
overload `H` stage or infer body availability from it. No pruning runs against the
attempt's source undo records.

This intentionally rewrites the capped bodies on each journal revision. Memory
budgets must include simultaneous previous/next journal payloads, storage envelopes,
decoded bodies and validation overlays; a payload cap is not an RSS measurement.
A later separate body-pin store may reduce copying, but is outside this packet.
Recovery-capable homes use an explicit new storage schema with journal/undo
creation limits. Iterator value-size checks precede application copies; LevelDB
still owns internal block decompression/allocation. These limits do not establish
an adversarial-corrupt-database engine allocation bound.

## Preparation before changing the active chain

1. Under the writer lock, verify the exact profile and source tip. Invoke the
   bounded `PlanHeaderFork` for the supplied target; reject ties/lower work without
   changing the active state. This remains a single-target plan, not selection.
2. Validate plan ordering and snapshot the exact source metadata/root/index. Locate
   every source undo row, check canonical encoding and successor/predecessor
   identities, and record its digest/length. Actual inverse coin/path validation
   still happens at disconnect against the matching active successor.
3. Obtain and pin every source restoration body and every replacement body. Check
   exact ID/framing/TxRoot and declared sizes. Missing bodies produce a resumable
   preparation result without disconnecting anything; malformed supplied bodies
   are rejected as bodies, never translated into a storage error for the existing
   source. Existing persisted corruption remains operational.
4. Check cumulative plan bytes, per-body and per-undo bytes, list lengths, available
   storage and bounded preparation reads. Authorize worst-case operations before
   performing them. Current full-undo allocation must gain a backend value-size
   bound or be explicitly limited by a storage creation/retention cap before this
   is described as a strict allocation bound.
5. Recheck source tip and all-ancestor target eligibility using fresh caller clock
   input. Atomically publish the prepared `J` and pin manifest with expected-source
   fencing. No active state changes in this batch. A crash before this point leaves
   no pending switch; unreferenced staged bytes can be cleaned with bounded work.

## State machine and atomic steps

| Phase | One durable step | Next checkpoint |
| --- | --- | --- |
| Prepared / DisconnectSource | Disconnect the next source ID with chain-aware inverse validation | Source cursor advances; expected tip becomes its predecessor |
| ConnectTarget | Execute the next pinned replacement body against the current state | Target cursor advances; `H` becomes Connected only with successful full execution |
| RollbackTarget | Disconnect the last successfully connected replacement | Replacement rollback cursor advances toward fork |
| RestoreSource | Execute original source bodies in fork-to-source order | Restore cursor advances toward exact original source |
| CompleteTarget | Verify exact target tuple/index and all-ancestor eligibility; publish terminal completion | Target is stable; cleanup is separately bounded |
| CompleteSource | Verify exact original source tuple/root/index and record failed/deferred attempt | Source is stable; cleanup is separately bounded |

Each modifying step writes its new `J` revision and active tuple/index in the same
sync batch. Extend the existing storage transaction and disconnect batch builder;
do not call an existing connector, then write a separate journal file or batch.
The expected journal revision and current tip/root fence the operation. The journal
must not be included in immutable per-block undo serialization. Every step consumes
at most one block transition; callers supply a per-call step/read/byte budget.

On deterministic replacement failure, the failing block never publishes active
state. Persist a journal-only transition to `RollbackTarget`, recording the failed
ID. Undo the accepted replacement prefix to the fork, then restore all original
source bodies. If failure occurs before reaching the fork while disconnecting the
source, persist `RestoreSource` and replay only the source suffix actually detached.
All restoration lists are derived from immutable plan IDs/cursors, not caller input.

A missing pinned body, corrupt undo, callback refusal, resource exhaustion or I/O
error is operational. It does not invalidate a header or silently discard the
journal. Capacity refusal before a step leaves the durable checkpoint unchanged;
resources may be supplied and the same step resumed. Corrupt restoration data must
leave a pending recovery error at the current valid checkpoint and require repair
from authenticated local backup. Never declare source restoration successful merely
because a partial prefix was restored.

## Restart and ambiguous-write recovery

Opening a journal-aware home must inspect `J` before exposing writable chain APIs.
Reopen first after any failed synchronous write; a failed sync may have committed.
Validate the journal profile, plan/pins and current `S/H/A/I`. Because progress and
state share one batch, disk must contain either the old revision/old active tuple or
the next revision/next active tuple. Resume from that observed revision without
repeating an already committed transition. An impossible cursor/tip/root combination
is corruption; do not guess, reset the database, delete `J` or replay arbitrary undo.

Crash tests must cover these boundaries individually:

- Before/after body staging and pin publication; before/after prepared journal sync.
- Before a step's validation, after staged coin changes, before sync, ambiguous sync
  failure, after sync before returning, and between successive steps.
- Before/after recording deterministic target failure, during target rollback,
  during source restoration, and after the final active step but before completion.
- Before/after terminal journal publication and during incremental pin cleanup.

Read-only diagnostics may expose the current checkpoint and journal phase during
recovery. Serving that checkpoint as a stable fully selected chain, generating new
mining templates or accepting unrelated active-chain writes must wait for completion.
A process restart does not automatically erase the recovery lock.

## Clock changes, ancestor eligibility and ties

This is a proposed operational policy pending the open timestamp decisions. Every
forward-target step and final completion rechecks the target's authenticated maximum
ancestor timestamp using overflow-safe `maximum > now && maximum - now > window`.
Checking only the next child's timestamp is insufficient when an ancestor was dated
further ahead. `now` and `window` remain explicit arguments; no skew constant or
clock source is introduced here.

Before the first active mutation, ineligibility yields Deferred and retains the
source. After mutation has started, ineligibility or caller cancellation transitions
to restoration of the source rather than leaving an indefinite partially selected
branch waiting for time. Mandatory rollback/restoration is a recovery action and
uses deterministic validation without applying the new clock gate to original
source blocks. Otherwise clock rollback could make restoring a previously stable
source impossible. The resulting stable source may itself be temporarily ineligible
under the current clock; report this separately and defer normal forward admission.
Do not automatically detach an already stable active chain merely because the local
clock moves backward. These choices need explicit maintainer review before node
integration and do not redefine deterministic consensus.

An in-progress attempt is fenced to its original plan. Higher-work arrivals are
queued for later planning; ties never replace the stable source. Re-evaluate later
candidates after this attempt completes/restores. This coordinator and
`PlanHeaderFork` still do not enumerate or rank a global candidate set. A later
selection owner must define that bounded inventory and invalid-descendant policy.

## Proposed API and exclusive implementation ownership

The initial API uses a capped embedded-body journal as specified above; the
following API sketch records intended responsibilities, not exact C++ names.
New `src/lotus_v2/reorg_recovery.{h,cpp}` owns canonical journal parsing, preparation,
state-machine decisions and validation callbacks. Proposed public types:

```cpp
struct ReorgLimits {
    uint64_t max_disconnect, max_connect, max_steps;
    uint64_t max_reads, max_body_bytes, max_undo_bytes, max_pinned_bytes;
};
enum class ReorgResult {
    Prepared, Progress, CompleteTarget, RestoredSource, MissingBody, InvalidBody, Deferred,
    CapacityRefused, StaleTip, StorageError
};
ReorgResult PrepareDevelopmentSwitch(const Hash &expected_source,
    const Hash &target, uint64_t now, uint64_t future_window,
    const ReorgLimits &, const ValidatorProfile &, DiskStateStore &,
    const BoundedBodySource &, ReorgProgress &, std::string &error);
ReorgResult ResumeDevelopmentSwitch(uint64_t now, uint64_t future_window,
    const ReorgLimits &, const ValidatorProfile &, DiskStateStore &,
    ReorgProgress &, std::string &error);
ReorgResult RequestSourceRestoration(const Hash &attempt_id,
    const ValidatorProfile &, DiskStateStore &, ReorgProgress &, std::string &error);
```

`ValidatorProfile` is a typed bundle of the existing explicit header, ordinary,
monetary and cost profiles, not a new default parameter source. `BoundedBodySource`
returns at most one named full body per call under an authorized byte quota and
cannot mutate the active store. `ReorgProgress` reports phase, attempt/revision,
source/current/target IDs and bounded counters. Outputs change only after a durable
step or an authenticated read-only progress report; results distinguish restored
source after deterministic failure from storage failure requiring further recovery.
`InvalidBody` is available during preparation before active mutation; a contextual
replacement failure after mutation is recorded in the journal and reported with
`RestoredSource` only once restoration actually completes.

Storage owner exclusively edits `disk_state.{h,cpp}` for a typed journal record,
pinned-body/undo probes and atomic commit/disconnect progress envelopes. A storage
API must accept structured expected revision/tip plus new journal bytes validated by
the coordinator; arbitrary caller key/value writes are not exposed. Storage owns
schema checks, sync ambiguity, callback reentry guards, pin retention and size bounds.
Journal query/cleanup calls must also enforce explicit quotas.

Connector owner edits `disk_block.{h,cpp}` to expose the existing staged complete
transition with a coordinator-supplied typed progress envelope consumed by the same
commit batch. Undo owner edits `development_chain.{h,cpp}` to pass the matching
progress envelope through its predecessor validation callback and storage batch.
Neither owner may weaken block checks to make restoration succeed. Index owner
edits `chain_index.{h,cpp}` only for explicit bounded probes needed by preparation;
`PlanHeaderFork` retains its single-candidate semantics.

Independent test owner adds `test_reorg_recovery.cpp` and `reorg_recovery_test/`,
using fresh homes and actual accepted multi-block source/replacement fixtures. The
root integration owner alone changes shared CMake, patch series/export/provenance,
and later daemon callers. Networking, chain parameters, profile adoption, live homes,
mainnet data and release operations are outside this packet.

## Acceptance gates

Use at least a two-block detach and two-block replacement with divergent spends,
monetary/EMA values and exact independently expected roots. Demonstrate successful
switch and exact source restoration after invalid first/middle/final replacement
blocks. Test missing bodies, bad commitments/proofs/signatures, corrupt undo and
predecessor metadata, exhausted quotas and profile mismatch without conflating
operational failure with consensus rejection.

Fault-inject every crash boundary above, reopen, and compare `S/H/A/I`, all touched
coin/proof paths, monetary bytes, recent history, retained bodies and journal revision
with the expected checkpoint. Verify no partial batch, duplicate replay, lost pins,
reset or silent terminal success. Test clock advance/rollback/restart, a low-time tip
with a high-time ancestor, exact work ties, new arrivals while recovery is pending,
genesis protection and revision/length overflow. Measure only the bounds actually
implemented; step count alone is not a memory, I/O or CPU bound.

Module tests and mailbox replay remain separate from disposable daemon execution.
No durable multi-block recovery, global selection or peer synchronization claim is
valid until this packet and its later daemon integration pass their own gates.
