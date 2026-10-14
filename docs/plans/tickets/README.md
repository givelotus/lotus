# Local planning queue

Status: unpublished drafts. No tracker deduplication, assignment, claim or dispatch has occurred. Before publication, load the repository binding and compare open/recently closed items. These drafts use the [ticket-creation workflow](../../../.agents/skills/ticket-creation/SKILL.md); they are not live issues or READY implementation packets.

| Draft / workstream | Next action | Dependency | Readiness |
| --- | --- | --- | --- |
| [V1 sync obstruction](v1-sync-obstruction.md) | Gather incident evidence and establish reproducible boundary | Access to stalled node/hotfix/reference | Investigation scoped; fix NEEDS_SPECIFICATION |
| [Workspace/provenance reconciliation](workspace-provenance.md) | Audit routing and propose deterministic isolated execution | Local source available | Draft; execution owner/base required |
| [Consensus/reference slice](consensus-reference-slice.md) | Review D01–D04/D07 and close ordinary-payment semantics | Maintainer decisions; no live sync required | NEEDS_SPECIFICATION |
| V1 historical port | Produce compatibility patches in behavioral groups | V1-00–V1-02 | Blocked on reference fixtures |
| V1 release qualification | Run full historical sync, recovery and interface gates | V1-03–V1-04 | Blocked on candidate |
| V2 production overlay | Integrate scalar payment chain then complete features | V1-06 plus accepted reference slice | Blocked on validated-v1 commit |
| Monetary/timestamp design | Define objective and analyze feasible timestamp histories | D10–D12 inputs | NEEDS_SPECIFICATION |

Maintainer owns unresolved product/chain decisions; worker/reviewer identities are not assigned here. Investigating evidence and authoring proposals can proceed without claiming the implementation is ready. Before delegation, provide accepted scope, exact base, allowed/prohibited paths, risk tier/lane, regression/proof, rollback and handoff artifact, as required by [grooming](../../../.agents/skills/backlog-grooming/SKILL.md).

The protocol and daemon plans define acceptance gates. Do not assign speculative numerical queue scores or turn local dependency prose into claims of native tracker blocked-by edges.
