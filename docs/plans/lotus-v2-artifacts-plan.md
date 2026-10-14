# Lotus development plan

Updated October 9, 2026. Documentation/specification preparation is underway; daemon execution remains deferred to the faster machine.

Deliver a modern Lotus v1 release that syncs the running network unattended, then build an entirely new Lotus v2 chain on that verified source foundation. Maintain v1 independently and prepare chain-agnostic upstream contributions separately. The [developer entry point](../lotus-v2/README.md) links the current artifacts.

## Sequence and release gates

| Stage | Canonical plan | Gate |
| --- | --- | --- |
| Source and incident evidence | [Provenance](../../daemon/docs/feature-provenance.md), [local drafts](tickets/README.md) | Target chain/reference pinned; sync failure and patch origins understood |
| Modern v1 foundation | [V1 plan](../../daemon/docs/lotus-v1-implementation-plan.md) | Historical compatibility, integrated sync fix, clean sync and supported stalled-state recovery |
| V1 release | V1-06 | Reproducible supported release and immutable validated-v1 commit |
| V2 reference and daemon slice | [V2 plan](../../daemon/docs/lotus-v2-implementation-plan.md), V2-00–V2-02 | Exact payment bytes, reference/daemon agreement, block/root/undo |
| Complete v2 behavior | V2-03–V2-05 | Assets, VM/costs and monetary/state transitions fully specified and validated |
| Optimization and launch | V2-06–V2-07 | Independent review and reproduction; every genesis decision closed |
| Upstream contributions | [Upstream plan](../../daemon/docs/lotus-upstream-plan.md) | Independent problem/test/benchmark packets, accepted submission scope |

Spec review and the independent reference tool can proceed before v1 completes. Production v2 daemon integration depends on the validated v1 foundation. Do not wait for upstream acceptance to ship a tested local v1 improvement.

## Artifact ownership

- [Consensus](../lotus-v2/consensus.md) owns proposed validity requirements C01–C28.
- [Decisions](../lotus-v2/decisions.md) owns D01–D15 and closure evidence.
- [ABI](../lotus-v2/script-abi.md) and [examples](../lotus-v2/examples/README.md) explain wallet/compiler use; examples are currently semantic pseudocode.
- [Validation](../lotus-v2/validation.md) owns conformance obligations; [results](../../daemon/docs/lotus-validation-results.md) records executed evidence.
- [Patch inventory](../../daemon/patches/inventory.csv) records file/series provenance; application/testing remain NOT_RUN.
- [Faster-machine handoff](faster-machine-handoff.md) owns transfer and first-execution prerequisites.

The former combined spec and patch strategy are archived historical sources. Their old “locked,” “DONE,” output-layout and performance claims do not override current status. The external Master Genesis Plan artifact now points to the repository documents rather than maintaining another editable specification. V1 historical rules remain compatibility evidence; v2 proposals do not alter them.

## Current completion and remaining work

- [x] Separate protocol rules, open decisions, ABI, daemon work, upstream work and validation records.
- [x] Inventory local patch files with provenance/digests; identify tooling and source-of-truth conflicts.
- [x] Prepare the v1 incident, workspace and first-reference-slice investigation/specification drafts.
- [x] Retain input × output enumeration and specify aggregate resource obligations.
- [x] Specify candidate encoding/signatures, trees, VM, recursive header/ASERT, resource algebra and monetary alternatives in six decision packets.
- [x] Run structural models and prepare [implementation entry contracts](implementation-entry.md) for workspace tooling and an independent candidate evaluator.
- [ ] Acquire exact stalled-node and hotfix evidence; identify compatible reference chain and source.
- [ ] Assign work owners and accept/groom bounded packets before dispatch.
- [ ] Close open consensus byte formats, opcodes, trees, signatures, resource values and monetary/genesis decisions.
- [ ] Implement the reference evaluator/assembler, machine-readable vector schema and generated examples.
- [ ] Reconcile tooling and port/qualify v1 on the faster machine.
- [ ] Integrate/qualify v2 and complete independent launch review.

Use the imported [ticket-creation](../../.agents/skills/ticket-creation/SKILL.md) and [grooming](../../.agents/skills/backlog-grooming/SKILL.md) workflows for scoped drafts. [Factory provenance](../../.agents/software-factory-import.json) pins the imported tools. No external tickets, dispatch, daemon builds, live sync, benchmark runs or monetary-paper changes are part of this planning pass.
