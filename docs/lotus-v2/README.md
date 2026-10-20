# Lotus: a compatible v1 release, then a new v2 chain

Status: review draft, updated October 14, 2026. No v2 genesis specification is frozen.

Start with the [review handoff](review-notes.md) for the current recommendations, executed checks and implementation entry points.

The first deliverable is an updated Lotus v1 node that synchronizes the running network from genesis without an unofficial binary or manual intervention. Verified V1 behavior is selectively carried into a dedicated ABC-based V2 series: a separate proof-of-work chain with composable UTXO authorization, native assets, bounded covenants, and authenticated state.

V2's engineering goal is that **hard forks should not be needed after genesis**. Design the complete validity function before launch, leave named room for what cannot be foreseen (P03's extension points, limits sized for future signature schemes), and improve the implementation afterward. A hard fork remains possible; the design aims to make one unnecessary. This is a launch discipline, not a proof that cryptography, economic incentives, or software can never fail. A bug fix that changes which blocks are accepted is a consensus change regardless of what the release calls it.

## Read and build in this order

| Reader's question | Canonical artifact |
| --- | --- |
| How do we get a useful node first? | [V1 implementation plan](../../daemon/docs/lotus-v1-implementation-plan.md) |
| What did Lotus already implement? | [Feature provenance](../../daemon/docs/feature-provenance.md), [patch inventory](../../daemon/patches/inventory.csv) |
| What would a v2 validator enforce? | [Consensus draft](consensus.md) |
| How are native addresses and template IDs encoded? | [Address specification and implementation status](addresses.md) |
| How do application message signatures work? | [Message signing](message-signing.md) |
| How do wallets exchange partially signed native transactions? | [Lotus PSBT profile](psbt.md) |
| Could existing Bitcoin ASICs mine an alternative V2 envelope? | [Unselected SHA256D envelope discussion](mining-envelope-alternative.md) |
| Could burn data be pruned or referenced by contracts? | [Open burn-data and historical-receipt appendix](burn-data-open-questions.md) |
| What still needs a decision? | [Decision register](decisions.md) |
| How do wallets and contracts interact? | [Script ABI](script-abi.md), [worked examples](examples/README.md) |
| Which choices are now concrete? | [Six technical decision packets](decisions.md), [implementation entry contracts](../plans/implementation-entry.md) |
| How do we establish correctness? | [Validation contract](validation.md), [recorded results](../../daemon/docs/lotus-validation-results.md) |
| How do we implement v2, update the miner and create genesis? | [V2 implementation and launch plan](../../daemon/docs/lotus-v2-implementation-plan.md), including V1 patch reuse and V2-00–V2-07 acceptance gates |
| What can be contributed upstream? | [Upstream plan](../../daemon/docs/lotus-upstream-plan.md) |
| What is ready to investigate? | [Local work packets](../plans/tickets/README.md), [machine handoff](../plans/faster-machine-handoff.md) |
| Why these choices? | [Rationale](rationale.md) |

## The useful capabilities

A coin expresses alternative spending paths. Each path requires all of its named branches; each branch commits to one or more script methods. An owner can therefore authorize a transfer while a vault independently requires state preservation. Token identity does not have to change when custody changes. Transaction-wide input × output checks remain available within explicit resource budgets.

A header state commitment can authenticate an answer about an outpoint. It does not by itself prove that all historical transitions were valid, recover lost database pages, or establish a complete snapshot. Those are separate proof and implementation obligations.

The initial demonstration is deliberately complete: a wallet constructs a signed payment, the reference evaluator and daemon agree on its bytes and validity, a block includes it, and disconnecting that block restores the prior state. Asset, vault, and state-query demonstrations follow. No performance number is a promise until a revision-specific measurement supports it.

## Authority and status

The consensus draft owns proposed validity rules. The ABI owns developer-facing representations derived from those rules. Daemon plans own engineering order and release gates. The decision register owns unresolved choices. Patch inventories describe source evidence; test results describe executed evidence. None substitutes for another.

`DRAFT` and `CANDIDATE` mean concrete reviewable proposals, not permission to launch. `OPEN` means competing rules remain possible. `FROZEN` requires recorded acceptance, exact parameters, independent conformance evidence, and closure of all Genesis blockers. There are currently no frozen v2 rules.

The [former combined specification](../archive/updating-bitcoin-design-2026-10-08.md) and [former patch roadmap](../../daemon/docs/archive/patch-strategy-2026-10-08.md) are historical design evidence. Their performance claims, “DECIDED” labels, and code snippets are not current authority. Existing historical v1 specifications remain evidence for compatibility investigation, not v2 rules.

V1 has separate validation evidence, summarized with exact source identities in the implementation plan. V2 daemon, miner, economic-simulation and launch gates still require their own evidence; this documentation review does not claim they passed.
