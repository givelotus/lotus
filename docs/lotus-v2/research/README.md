# Research (non-normative)

Documents here record investigations: analysis, reviews and explorations of
designs that are not part of the specification. They keep their review voice
and may carry dates. None of them defines a rule, wire format or vector that
the specification depends on. A research result enters the specification only
through a decision recorded in [decision history](../decisions/history.md).

Status values: **open** (investigation continuing, nothing selected),
**superseded** (kept as a record), **informs Dxx** (input to that open
decision in the [decision register](../decisions.md)).

| Document | Summary | Status |
| --- | --- | --- |
| [Optional SHA256D mining envelope](mining-envelope-alternative.md) | An 80-byte Bitcoin-shaped envelope with BLAKE3-committed extension fields for reuse of existing SHA256D ASICs, with node-built jobs and adapted Stratum construction. | open; informs D12 |
| [Prunable burn data and historical receipts](burn-data-open-questions.md) | Whether burn payloads can be pruned while keeping commitments, and whether scripts could reference historical burns as receipts. | open |
| [Burn demand, price and the work-responsive tail](burn-demand-economics.md) | Conditional economics of external burn budgets against tail issuance; the simulations needed before constants are fixed. | informs D10 |
| [Permissionless adaptive pairwise reconciliation](pairwise-reconciliation-scheduler.proposed.md) | Count/time-triggered reconciliation with random peer fanout that needs no stake, quorum or epoch clock. | open; informs D11 |
| [Epoch root gossip, reconciliation and repeated voting](epoch-root-gossip-loop.proposed.md) | Shared slot naming, aggregate-then-confirm exact roots, prefix steering and atomic sealing for epoch candidates. | open; informs D11 |
| [Snapshot holders and epoch numbering](epoch-snapshot-routing.proposed.md) | Separates a held reconstructible candidate from an opaque root, and local checkpoint counters from shared epoch ordinals. | open; informs D11 |
| [Shared steering for reconciling nodes](shared-reconciliation-steering.proposed.md) | Precedence among exact preference evidence, retrieval targets, similarity hints and independent exploration. | open; fixed-candidate election part superseded by the root-gossip study |
| [Ten roots, candidate selection and similarity hints](ten-root-candidate-study.proposed.md) | Ten-actor model showing all-distinct preferences stall without a nomination rule. | open; informs D11 |
| [Epoch clocks](epoch-clock-open-questions.md) | Compares an authored heartbeat DAG, a peer-progress vector and the accepted parent-BatchId chain as epoch clocks. | open; informs D11 |
| [Committed contributions review](epoch-contribution-proposal.md) | Review of stake-first committed-contribution epochs with fixed-generation scheduling and proposed behavior vectors. | open; informs D11 |
| [Setup, availability and remaining epoch decisions](epoch-availability-open-decisions.md) | Trusted-setup question and the four open roster, availability, conflict and block-rule decisions for epoch designs. | open; informs D11 |
| [Review handoff, October 2026](review-notes.md) | Handoff summary of the candidate packets and production blockers as of October 14, 2026. | superseded by the [decision register](../decisions.md) |

## Proposed vectors

These fixtures belong to the studies above and are not conformance vectors.

| File | Study |
| --- | --- |
| [epoch-conflict-vectors.proposed.json](epoch-conflict-vectors.proposed.json) | Committed contributions review |
| [epoch-confirmation-boundaries.proposed.json](epoch-confirmation-boundaries.proposed.json) | Epoch root gossip loop |
| [epoch-prefix-examples.proposed.json](epoch-prefix-examples.proposed.json) | Epoch root gossip loop |
| [epoch-root-gossip-vectors.proposed.json](epoch-root-gossip-vectors.proposed.json) | Epoch root gossip loop |
