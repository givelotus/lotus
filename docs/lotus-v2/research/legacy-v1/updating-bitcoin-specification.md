# Updating Bitcoin: Lotus v2 specification and implementation plans

The current review draft is organized into separate first-class artifacts. **V2 is not frozen or launch-ready.** The zero-hardfork objective requires closing every consensus decision before genesis.

Start with the [developer overview](../../README.md) and [development sequence](../plans/lotus-v2-artifacts-plan.md).

| Former combined section | Current owner |
| --- | --- |
| Consensus, transaction format, assets, paths, MAST, VM, loops, issuance | [Consensus requirements](../../consensus.md) and [decision register](../../decisions.md) |
| Wallets, witnesses, scripting and examples | [Script ABI](../../script-abi.md) and [examples](../../examples/README.md) |
| Storage, mempool, mining, RPC, indexer and transport | [V2 daemon plan](../implementation-notes/lotus-v2-implementation-plan.md) |
| Existing network and historical compatibility | [V1 daemon plan](../../../../daemon/docs/lotus-v1-implementation-plan.md) |
| Patch sequence and upstream work | [Patch strategy](../../../../daemon/docs/patch-strategy.md) and [upstream plan](../../../../daemon/docs/lotus-upstream-plan.md) |
| Verification and genesis checklist | [Conformance contract](../../validation.md) and [results](../../../../daemon/docs/lotus-validation-results.md) |
| Design motivation and monetary research | [Rationale](../../rationale.md) |

The [previous combined draft](../updating-bitcoin-design-2026-10-08.md) is preserved for provenance. Its “locked” claims, underspecified pseudocode, performance estimates and conflicting parameter choices are historical, not current consensus authority. Do not implement its cache shortcut or raw-hash one-leaf path.
