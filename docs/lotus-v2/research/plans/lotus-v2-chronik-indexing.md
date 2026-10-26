# Private V2 testnet Chronik indexing proposal

Status: architecture proposal, with filter semantics pending user clarification.
This document authorizes no consensus change, Chronik enablement, node launch,
mainnet action, or release operation. Implementation and integration each require
independent evidence. The inspected native source is
`/private/tmp/lotus-v2-native-integration-20261015`; its file paths below are
relative to that source tree, while specification paths are relative to this
monorepo.

## Public information and indexing limits

`docs/lotus-v2/consensus.md` C05/C09 and native
`src/lotus_v2/output.h` expose each created output's complete ordered vector of
1–16 distinct branch roots and its paths. Here “branch” means an output
authorization root, not a competing blockchain fork. A branch position is its
index in that vector; it is neither an output index nor a hidden script position.

Root and positional indexing is possible at creation without consensus changes.
C11 and `src/lotus_v2/transaction.h::BranchWitness` reveal selected scripts and
membership siblings only on spending. Membership is unordered: it proves no
hidden leaf position, count, uniqueness, or covenant semantics. Do not advertise
public-key or script discovery from unrevealed roots. A separately named reveal
history could index validated spending disclosures later.

C09/C17 distinguish spendable outputs from `IS_BURN` commitments. Burn outputs
have roots/commitment words and zero paths, contribute to creation history, and
never enter UTXOs. Matching a root establishes neither ownership nor spendability.

## Proposed query semantics

These semantics are a proposal until the user's meaning of set filters is
confirmed. Support two explicit selectors rather than an ambiguous bare set:

- `any_branch: [root, ...]`: OR over roots at any branch position.
- `positions: [{position: 0, roots: [...]}, ...]`: OR within each position's root
  set, AND across specified positions, all on one output.

If both selectors are supported in one request, require both to match the same
output. Missing positions fail. Root bytes use the V2 wire hash order with an
explicitly documented API encoding. Reject malformed roots, duplicate position
clauses, positions outside 0–15, and an empty overall selector. Canonicalize root
sets and clause ordering before computing a filter digest. Never conjoin matches
from distinct outputs. Return each outpoint once with matching positions;
transaction history deduplicates transaction IDs.

Add explicit `include_burn` and confirmed/pending selection. UTXO endpoints always
exclude burns. Return complete branches, paths, flags, value and token ID so
clients can evaluate the policy they requested. History distinguishes creation
from spending; a spending transaction may match through its consumed coin.

## Storage and bounded pagination

A proposed posting key is
`chain/profile/schema || root || position || outpoint`. Any-position lookup may
use a root-only posting family or a bounded merge over positions 0–15. Keep
output records with creation/spend locations and complete public output fields.
Intersect positional postings by outpoint, then verify predicates against the
output record. Deduplicate memberships per output and transactions per history
response. Audit generic Chronik grouping support for multiple members at one
output index before reuse.

Define explicit limits before coding: request bytes, clauses, roots per clause,
total roots, posting reads, intermediate candidates, response bytes, page size,
and subscription evaluations. Limit exhaustion returns a defined continuation or
capacity result, never an incomplete response presented as complete. Avoid
unbounded total-count scans.

Use deterministic ordering and an opaque continuation containing schema/version,
chain/profile identity, anchored tip, canonical filter digest and last key.
Reorg invalidates an incompatible anchor with a defined stale-cursor result.
Bound cursor decode size and validate it before allocation. A page describes one
consistent indexed snapshot; clients can compare its anchor with node state.

## Atomic chain and pending lifecycle

The current V2 runtime is separate from legacy node-owned Chronik signals. Add a
dedicated adapter only after the integration gate. Index authoritative committed
transitions, not retained candidate bodies or validation previews. Connected
blocks atomically write output records, postings, spends, transaction history and
an index checkpoint. Disconnect atomically removes creations and restores spent
outputs and their complete memberships. Checkpoint by block hash and height;
replaying a completed transition must be idempotent.

V2 journals and receipts can represent an in-progress recovery. Keep the index
unavailable or explicitly behind during recovery, reconcile its checkpoint with
runtime authoritative state on startup, and publish a current anchor only after
reconciliation. Crash between node commit and index commit must be recoverable by
replay; independent databases must not be described as one atomic transaction.
Bound reconciliation work and persist progress without exposing partial results
as a complete tip. Notifications follow committed index batches and carry chain
anchors; reconnect requires resynchronization.

A pending transaction index needs an actual accepted V2 transaction pool and its
lifecycle. Existing command `pending_validation` and journal states refer to
blocks/recovery and do not establish a mempool. Initially expose confirmed-only
capability. When a pool exists, specify admission after contextual validation,
parent dependencies, conflict removal, expiry/eviction, mining, disconnect
readmission and rejection. Keep at most one accepted variant per TxID, preserve
its TxHash, and honor the specification's rejection identity rules. Pending postings form a
separate overlay; removal restores consumed pending/confirmed availability
correctly. Test parent-child removal and reorg readmission explicitly. Do not
present pending outputs as confirmed or assume disconnected transactions are
readmitted automatically.

## Compatibility and wallet behavior

Use an explicit V2 API namespace, protocol capability and database schema. Bind
storage and responses to ChainID, genesis/profile identity and index version.
Reject mismatched databases; migration/reindex must be explicit. Preserve legacy
Chronik meanings rather than encoding V2 roots as legacy scripts or token IDs.
V2 uses unsigned values, 64-bit locks, different transaction identities, output
structure, header grammar and disk layout, so a lossless model is required.

Wallets can query their known root sets and policy positions for discovery, then
validate full output policy, token identity and authoritative coin state before
signing. Retain the `walletcontext` provider's anchored lookup/recheck behavior;
Chronik discovery does not replace it. Wallet conventions may construct hidden
trees deterministically, but indexing cannot prove their hidden contents.

## Source map and independent implementation ownership

| Slice | Files and ownership boundary |
| --- | --- |
| Specification/API contract | This plan; `docs/lotus-v2/consensus.md` C05/C09–C11/C17 and policy identity rules are reference inputs, not edit targets |
| Lossless model and bridge | New V2 modules beside `chronik/chronik-bridge/src/ffi.rs`, `chronik/chronik-cpp/chronik_bridge.cpp`, and `chronik/bitcoinsuite-core/src/tx/`; consume `src/lotus_v2/output.{h,cpp}` and `transaction.{h,cpp}` without consensus edits |
| Durable branch index | New `chronik/chronik-db/src/groups/v2_branch.rs`; `groups/mod.rs`, `db.rs`, `io/group_history.rs`, `io/group_utxos.rs`; own schema, posting deduplication and connect/disconnect batch tests |
| Query engine | New `chronik/chronik-indexer/src/query/v2_branches.rs`; `query/mod.rs`; own filter algebra, intersections, limits, snapshot cursor and reference-scan comparisons |
| Runtime integration | `src/lotus_v2/development_runtime.{h,cpp}`, `reorg_recovery.{h,cpp}`, `disk_state.{h,cpp}` and a dedicated adapter; `chronik/chronik-indexer/src/indexer.rs`; own committed-event authority, crash/recovery/reorg reconciliation; separate integration gate |
| HTTP and subscriptions | `chronik/chronik-http/src/server.rs`, `ws.rs`, `subscription_limits.rs`; `chronik/chronik-proto/proto/chronik.proto`; `chronik/chronik-indexer/src/subs.rs`, `subs_group.rs`; own request bounds, versioned encoding and notification semantics |
| Pending overlay | `chronik/chronik-db/src/mem/{mempool,group_history,group_utxos}.rs` plus future V2 accepted-pool adapter; blocked on defined V2 pool lifecycle, not simulated with block candidate state |
| Wallet consumption | `src/wallet/v2_node_provider.{h,cpp}`, `v2_wallet.{h,cpp}`; own discovery adapter and anchored verification, after API contract stabilizes |

Each slice should use an isolated candidate commit and declare shared registration
files before editing. Model fixtures precede DB/query work; API depends on a
stable query contract. Runtime integration and pending support are later gates,
not prerequisites for proving the pure filter engine. No slice implicitly owns
consensus or enables Chronik.

## Required evidence before integration

Compare indexed queries with a simple full-output reference scan for any-position
and positional OR/AND predicates, including cases where separate outputs would
otherwise falsely satisfy a conjunction. Cover burns, token outputs, all 16
positions, absent positions, duplicate memberships, spent history and pagination.
Demonstrate inverse connect/disconnect, reorg replay and crash checkpoint
reconciliation with authoritative state. Verify bounds and stale cursors. Prove
lossless V2 round trips and exact identities/header/disk offsets before exposing
raw transactions or proofs. Pending support requires separate lifecycle tests.
Legacy Chronik checks and private V2 tests must pass independently before any
combined private-node enablement is proposed.
