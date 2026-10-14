# Lotus development plan

Updated October 14, 2026. The restored [V2 implementation and launch plan](../../daemon/docs/lotus-v2-implementation-plan.md) owns milestones V2-00–V2-07, V1 patch reuse, miner/pool changes, SDK/wallet/indexer integration, genesis construction and release gates.

V1 remains independently maintained. V2 is a separate chain with its own six-patch series on pinned ABC `8c67fe1e85a602204a2ce65aa3b643469c2c3a1d`; it selectively carries forward verified V1 behavior rather than applying that series over the complete V1 stack. The implementation plan records the corrected V1 reference and distinguishes reported V1 validation from unexecuted V2 gates.

## Sequence and release gates

| Stage | Milestone | Gate |
| --- | --- | --- |
| Source provenance and implementation profile | V2-00 | Exact ABC/V1/V2 references, accepted candidate requirements, explicit open parameters |
| Independent reference and daemon payment slice | V2-01–V2-02 | Parser/signature vectors, disposable development genesis, payment/block/root/undo agreement |
| Assets, VM and monetary/state behavior | V2-03–V2-05 | Complete integrated validity, resource/reward accounting and state restoration |
| Miner/pool and optimization | V2-06 | CPU/GPU tagged-BLAKE3 agreement, actual accepted development blocks and measured resource behavior |
| Ecosystem and launch qualification | V2-07 | Wallet/indexer/node agreement, all genesis decisions closed, independently reproduced final genesis and release |

Development-chain genesis construction starts at V2-02. Final mainnet genesis follows parameter freeze and independent review. Spec/reference work does not require waiting for publication of a V1 release; promoting shared daemon changes requires their recorded regression evidence.

## Artifact ownership

- [Consensus](../lotus-v2/consensus.md) owns proposed validity requirements C01–C28.
- [Decisions](../lotus-v2/decisions.md) owns D01–D15 and closure evidence.
- [ABI](../lotus-v2/script-abi.md) and [examples](../lotus-v2/examples/README.md) explain wallet/compiler use; examples are currently semantic pseudocode.
- [Validation](../lotus-v2/validation.md) owns conformance obligations; [results](../../daemon/docs/lotus-validation-results.md) records executed evidence.
- The executable [V2 series](../../daemon/patches/v2/series) selects the current six patches; the [legacy inventory](../../daemon/patches/v2/series-legacy-plan.txt) is historical only. Each new implementation requires exact replay and behavior evidence.
- [Faster-machine handoff](faster-machine-handoff.md) owns transfer and first-execution prerequisites.

The former combined spec and patch strategy are archived historical sources. Their old “locked,” “DONE,” output-layout and performance claims do not override current status. The external Master Genesis Plan artifact now points to the repository documents rather than maintaining another editable specification. V1 historical rules remain compatibility evidence; v2 proposals do not alter them.

## Current completion and remaining work

- [x] Separate consensus, decisions, ABI, validation and implementation planning.
- [x] Prepare six candidate packets, the opcode registry and structural construction checks.
- [x] Restore the missing implementation plan and its V1 reuse, miner and genesis requirements.
- [x] Specify optional opaque coinbase data and document Frank burn-demand context; calibration and full validation remain open.
- [ ] Record replay/build evidence for the actual V2 series and close its V1 provenance audit.
- [ ] Close open consensus/parameter choices and implement the independent evaluator and executable examples.
- [ ] Complete the daemon, miner and ecosystem milestones with independent conformance evidence.
- [ ] Freeze and independently reproduce final genesis; complete launch review before publication.

The older [implementation entry contracts](implementation-entry.md) remain useful bounded work descriptions; their source-routing contract is updated to match the current series. Historical incident/faster-machine drafts are not evidence that current V1 validation has not occurred. This planning update performs no daemon build, live sync, economic simulation or launch.
