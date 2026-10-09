# Updated Lotus v1: unattended sync to the running network

Status: execution plan, October 9, 2026. Heavy execution deferred to the faster machine. No compatibility result is claimed. Maintainer owns target-chain decisions; implementation and review owners must be assigned before dispatch.

## Release contract

A supported release builds reproducibly on a recorded modern Bitcoin ABC base, synchronizes the intended running Lotus network from genesis without a hotfix binary or hidden manual commands, and handles the known stalled-node state through a supported recovery path. Existing users' wallets and chain data are preserved. V1 remains independently maintained after v2 launches.

This is a compatibility project. Do not change issuance, script rules, activations, historical exceptions or chain selection to match v2 preferences. Determine observed historical behavior from pinned reference implementations and block fixtures. Neither old prose describing a “correct” chain nor an unverified current tip identifies the target network sufficiently.

## Source baseline

Recorded candidate ABC base: `252182e957120652960c1f88ec96515c448b1204`. Historical extraction anchor: `fa7a44f731a2dfe1587e572d9eb0e4bb7c73d79c`. The `v10.4.10` release pin is a reference lead, not proof of compatibility. Record full commits and genesis/block identities before relying on any of them. Do not move a pin opportunistically mid-port.

[Patch inventory](../patches/inventory.csv) records file digests and source commit headers where present. Its 243 active v1 entries are not 243 proven applicable changes. Superseded history may be consolidated only after mapping its behavior and regression coverage; preserve provenance.

## Stages and gates

| ID | Deliverable and scope | Depends on | Exit evidence |
| --- | --- | --- | --- |
| V1-00 | Preserve stalled-node evidence; pin reference sources and target chain | Access to user's evidence/reference node | Binary/config identities, genesis, last accepted/first rejected hashes, logs, hotfix/manual-procedure provenance; unknowns explicit |
| V1-01 | Reconcile workspace tooling and patch provenance | Source inventory | Separate v1/v2/upstream checkouts/build/data dirs; exact pins; no implicit reset; deterministic patch application and failure reporting |
| V1-02 | Establish compatibility fixture corpus and baseline | V1-00, V1-01 | Reference build and activation-boundary blocks with expected validity, chainwork, UTXO/state summaries; failure reproduced |
| V1-03 | Port required historical semantics to modern ABC | V1-02 | Reviewable dependency-ordered patches, inherited and Lotus boundary tests, explicit supersession map |
| V1-04 | Integrate sync-obstruction fix and supported recovery | V1-02; integrate with V1-03 | Clean-boundary and stalled-database regressions pass; narrow behavior justified; no magic commands |
| V1-05 | Qualify full sync, reorg, restart and interfaces | V1-03, V1-04 | Unattended fresh validation to matched tip; fixed-height comparisons; restart/recovery/reindex; wallet/RPC/indexer results |
| V1-06 | Reproducible release and immutable v2 foundation | V1-05 | Source/patch/toolchain manifest, signed release procedure, upgrade/recovery instructions, validated-v1 commit |

V1-00 investigation can proceed alongside V1-01 tooling work in separate scopes. Diagnosis need not wait for the whole rebase. V1-04 may be developed against the reproducing baseline and then ported, with both behaviors tested. Do not hide its proof inside a giant rebase diff.

## Historical sync incident

Observed report: a nearly syncing node stops at a historical block; users need another repository's hotfix and manual operation to proceed. Exact binary, block hash, rejection reason, hotfix commit and commands are not yet supplied. [Investigation draft](../../docs/plans/tickets/v1-sync-obstruction.md) owns the intake.

Leads only: old notes mention Ruth, height 927381 and `v8.3.3-hotfix`. Patch `206-fix-broken-replay-protection-and-minerfund-outputs-8.patch` carries source commit `2e59ea5cce092df68e04ef375818482bb936d605` and changes minerfund selection/replay-protection activation. Its presence is not a diagnosis or proof that it accepts the intended live chain.

Preserve a consistent stopped-node copy or supported filesystem snapshot of the stalled data; do not copy a live database inconsistently and call it a fixture. Keep wallets/credentials outside shared artifacts. Compare release, hotfix and candidate at identical block boundaries. Determine whether the failure is validation, activation, persisted failed/parked flags, chain selection, indexes, database format or a combination. Record what each manual command actually changes.

Any historical compatibility rule must be justified by exact verified context, deterministic on all nodes, narrow, and covered by adjacent-boundary tests. A broad validation bypass, hidden checkpoint, blanket reconsideration or trust in peer consensus is not an acceptable product fix. Local metadata repair must preserve evidence, be versioned/idempotent and survive interruption. If safe automatic repair is impossible, present the limitation and ordinary supported recovery flow for explicit acceptance before declaring V1-04 complete.

## Porting boundaries

Group patches by behavior: identity/serialization/hashing; target/PoW/time; issuance/minerfund/replay protection; script/signatures and activations; chain selection; wallet/address/RPC; indexer/notifications; packaging. Map historical changes in order before consolidating superseded ones. A clean `git apply` is not semantic equivalence.

Review inherited ABC Avalanche, finalization/parking, activation defaults and transaction policy individually. Do not automatically transplant the v2 advisory-only proposal into v1. A testing switch must not let a production v1 node silently select an alternative monetary schedule. Preserve necessary production history while isolating regtest-only conveniences.

Chronik compatibility includes transaction/block identity, amounts, addresses, scripts/tokens where applicable, mempool events, block connection/disconnection and replay. “It is additive” is not evidence that only an address prefix needs changing. NNG/ZeroMQ decisions must account for existing consumers.

## Full-sync and release acceptance

Use a fresh data directory, ordinary network configuration and full historical validation with assume-valid shortcuts disabled where supported. Record exact flags and any checkpoints/shortcuts still active. Compare block hashes, cumulative work and canonical state summaries at genesis, each relevant activation, both sides of the obstruction and the same final height. Tip agreement alone does not prove equivalent validation.

Exercise interrupted sync, restart, reconnect after downtime, bounded reorg, block import/reindex and wallet/RPC smoke checks. On preserved stalled state, verify detection, repair, resumed sync and a second restart without manual operations. Define disk, memory and completion-time targets before the endurance run; report machine details and logs, not an unqualified “syncs.”

Keep the original database untouched until candidate acceptance. Record database/wallet migration compatibility and downgrade policy; rollback uses preserved data or a documented rebuild, never an unsupported older binary on a migrated wallet. Release artifacts must identify the source commit, patch digests, dependency/toolchain versions and reproducible build procedure.

The final validated-v1 commit is immutable and recorded in [results](lotus-validation-results.md). V2 forks its source, not its UTXO database. Retain these regression fixtures for every later ABC rebase and any shared daemon refactor.
