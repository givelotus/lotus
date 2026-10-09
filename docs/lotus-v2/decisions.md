# V2 decision register

Status: review draft. Decision owner: project maintainer; technical reviewers and execution owners are unassigned. A recommendation is not a frozen decision. Every row below blocks genesis until accepted and validated or the feature is removed through an explicit design decision.

| ID | State | Recommendation or unresolved question | Evidence required for closure |
| --- | --- | --- | --- |
| D01 Encoding and limits | CANDIDATE / calibration OPEN | [P01](decisions/encoding-and-signatures.md): exact grammar, 22-byte prefix, explicit kinds/clocks, canonical framing | Independent parser vectors; [P05](decisions/resources-and-parameters.md) numerical limits |
| D02 Hash domains and trees | CANDIDATE | [P02](decisions/commitments-and-state.md): sorted branch membership, ordered count-bound tx tree, 256-level sparse UTXO map | Independent vectors, measured state cost, accepted MonetaryState encoding |
| D03 Paths and witnesses | CANDIDATE | C09–C11/P01: nonempty sorted paths, exact positional witnesses, committed branch order | Independent authorization/path vectors |
| D04 Identities and signatures | CANDIDATE | P01: ChainID-bound core/full identity, exact FULL message, resolved policies and selected-leaf plan | Independent signing vectors; explicit acceptance of full-only signing |
| D05 Token identity | RECOMMENDED / acceptance OPEN | [P06](decisions/issuance-and-time.md): mint-program identity and explicit unique-issuance/revocation obligations | Accepted asset lifecycle; disposition of historical outpoint-identity patches |
| D06 Reference inputs | CANDIDATE | P01: block-order visibility, no consumption/value credit, no duplicate aliases; coinbase maturity also applies to references | State/mempool/reorg vectors and maturity constant |
| D07 VM and crypto ABI | CANDIDATE | [P03](decisions/vm-semantics.md): closed byte map, exact arithmetic/control, spend/mint contexts and three crypto profiles | Independent opcode/crypto vectors, review and costs |
| D08 Resources | ALGEBRA SPECIFIED / calibration OPEN | P05: structured upper bounds, depth two including input × output, independent byte/memory/aggregate caps | Measured primitive schedule, supported hardware envelope, mainnet constants |
| D09 Optimizations | CANDIDATE | C20–C21: scalar authority, context-complete equivalence, no unproven Master/Companion shortcut | Differential evidence before each optimization is enabled |
| D10 Monetary policy | OPEN with exact tail candidate | P06: integer recurrence candidate; explicit bootstrap clock alternatives and incentive-analysis objective | Accepted mechanism/precision/initialization; economic and integer vectors |
| D11 Faucet | OPEN with implementation alternatives | P06: fixed allocation versus consensus-accounted reserve cap; explicit odd-unit and underclaim requirements | Accepted state/policy mechanism, auth assumptions and examples |
| D12 Header, PoW and time | RECOMMENDED / eligibility and values OPEN | [P04](decisions/header-and-mining.md): revised recursive header, state commitment, wide nonce; v1 48-bit precedent retained as evidence | Width/hash selection, independent target/ASERT vectors, time-eligibility semantics, header/mining measurements |
| D13 State and coinbase | CANDIDATE / monetary record OPEN | P01/P02: parent/height coinbase identity, full state envelope including coin metadata and monetary state | MonetaryState grammar, genesis/undo vectors, snapshot trust contract |
| D14 Genesis/network identity | PARTIAL CANDIDATE / values OPEN | P01: independently selected ChainID; P04: explicit header/genesis framing | Parameter/launch manifest, addresses, magic, ports, seeds and source/build reproduction |
| D15 Extension policy | CANDIDATE | Reject unknown consensus data; listed NOP is permanently a NOP; no unannounced future activation | Review capacity, crypto longevity and all post-genesis claims |

## Decisions that can proceed now

“CANDIDATE” means an implementable proposed rule, not approved mainnet consensus or independent verification. The six packets provide precise proposed encodings, algorithms and tradeoffs. [Implementation entry contracts](../plans/implementation-entry.md) identify work that can start without guessing production constants. No decision is FROZEN.

P01–P03 can drive a parameterized reference implementation and local vectors. P04 preserves v1's useful recursive-hashing rationale while proposing new fields and widths; choosing it does not settle ASERT or timestamp incentives. P05 and P06 separate empirical calibration/economic choices from work that is ready to implement as a candidate.
The monetary analysis must choose an objective before optimizing it: expected discounted miner profit, reward per hash, or total network issuance are different quantities. Evaluate fixed-share and mobile miners, changing share, discovery randomness, allowed timestamp histories, transaction fees, clipping, and rounding. A reward formula involving difficulty is not by itself a proof of timestamp honesty. Record any impossibility result or tradeoff rather than claiming a “sweet spot” without a feasible-history model.

## Closure record

For each closed decision record: accepted rule and rejected alternatives; maintainer acceptance; spec revision and requirement IDs; exact parameter/vector digests; independent reviewer; remaining limitations; affected patches and examples. Reopening before genesis invalidates dependent vectors and measurements. After genesis, a changed validity rule is not an ordinary implementation update.
