# V2 decision register

Status: review draft. A recommendation is not a frozen decision. Dated changes to these states are recorded in [decision history](decisions/history.md). Every row below blocks genesis until accepted and validated or the feature is removed through an explicit design decision.

| ID | State | Recommendation or unresolved question | Evidence required for closure |
| --- | --- | --- | --- |
| D01 Encoding and limits | CANDIDATE / calibration OPEN | [P01](decisions/encoding-and-signatures.md): exact grammar, 16-byte prefix, packed lock word, flag-selected input kinds, output flags (`0x01` `HAS_TOKEN`, `0x02` `IS_BURN`, `0x04` `HAS_STATE`), `MAX_OUTPUT_BRANCHES = 16`, `MAX_OUTPUT_PATHS = 16`, canonical framing | Independent parser vectors; [P05](decisions/resources-and-parameters.md) numerical limits |
| D02 Hash domains and trees | CANDIDATE | [P02](decisions/commitments-and-state.md): sorted branch membership, bottom-up indexed binary Merkle tree (`IndexedTreeRoot` for `InputsRoot`, `FullInputsRoot`, `OutputsRoot`, `CoinsRoot`), top-level coinbase split `TxRoot = H_txroot(0x03 \|\| CoinbaseLeaf \|\| SubtreeA)` with `TxID`-keyed single-leaf-collapsed Merklix `SubtreeA` (with branch counts), compact single-leaf-collapsed sparse UTXO map with `OutpointKey = txid \|\| vout` prefix preservation and delayed coinbase UTXO insertion (`h -> h+1` for $h \ge 1$), canonical `MonetaryState` (`56B` at $h=0$, `88B` with 32B `history_root` at $h \ge 1$) in `StateRoot` | Independent vectors, measured state cost, initial genesis `MonetaryState` values |
| D03 Paths and witnesses | CANDIDATE | C09–C11/P01: nonempty sorted paths (`1..16` for spendable outputs, `0` iff `IS_BURN`), exact positional witnesses, committed branch order (`1..16` distinct entries) | Independent authorization/path vectors |
| D04 Identities and signatures | CANDIDATE | P01: ChainID-bound Merkleized `TxID` and `TxHash` (112B header+roots preimage with witnesses minus arguments in `InputsRoot`), exact FULL message (`TxID`, `CoinsRoot`) plus two own-input partial modes (`OwnInputHash(i)` and `OutputsRoot`/`OutputLeaf(i)`), input/branch-bound spend selector | Independent signing vectors; explicit acceptance of the three-mode set |
| D05 Token identity | CANDIDATE; mint-policy identity selected | [P06](decisions/issuance-and-time.md): mint-program identity and explicit unique-issuance/revocation obligations | Accepted asset lifecycle; disposition of historical outpoint-identity patches |
| D06 Reference inputs | REMOVED | No read-only input kind exists (C13): every inspected coin is consumed | Vectors showing unassigned input flags reject |
| D07 VM and crypto ABI | CANDIDATE | [P03](decisions/vm-semantics.md): 225 assigned instructions (including `EMITLOG`, `ENFORCEOUTPUT`, `STATEVERIFY`, `STATEHASH`, `ENUMERATE`, `OUTPUTCONTINUESBRANCH`, `MERKLEROOT_SORTED`, `MERKLEROOT_INDEXED`; `OP_UTXOPROOFVERIFY` rejected) plus 31 generic success bytes, exact arithmetic/control, spend/mint contexts and four crypto profiles | Independent opcode/crypto vectors, review and costs |
| D08 Resources | CANDIDATE / constant calibration OPEN | P05: unified Cost Units (`cu`, 1 wire byte = 1 `cu`), parabolic tx cost $C_{\text{tx}} = L + ((L^2) \gg S_{\text{tx\_knee}})$, rolling integer `ema_block_cost` $E_n$ (`w = 10`), parabolic block burn floor funded by fee burn and reward underclaim, plus 1000 atoms/kB minimum fees and charged coinbase/envelope work (`MAX_TX_BYTES` and `MAX_BLOCK_BYTES` removed), bounded `Coin` size ($\le 868\text{ B}$), $O(1)$ sighash preimages | Measured primitive `cu` schedule, supported hardware envelope, simulation of shift constants ($S_{\text{tx\_knee}}, w, E_{\min}, S_{\text{linear}}, S_{\text{quad}}$) |
| D09 Optimizations | CANDIDATE | C20–C21: scalar authority, context-complete equivalence, no unproven Master/Companion shortcut | Differential evidence before each optimization is enabled |
| D10 Monetary policy | CANDIDATE / constant calibration OPEN | P06: `1 XPI = 10^6 atoms` (2-decimal UI display, 4 hidden sub-cent decimals); additive block subsidy $S_n = B_n + T_n$ from Block 1; telescoping bootstrap reserve $B_n = \max(1, R_n \gg 20), R_{n+1} = R_n - B_n$ ($\sum B_n = R_0$ exact; candidate $B_0 = T_0 = 250{,}000\text{ XPI/block} = 2.5 \times 10^{11}\text{ atoms}$, $R_0 = 2^{20} B_0 = 262{,}144{,}000{,}000\text{ XPI}$); integer work-responsive tail $T_{n+1} = \min(T_{\max}, \max(T_{\min}, \text{isqrt}(\lfloor T_g^2 W_n / W_g \rfloor)))$ | Economic/integer simulation confirming $k_{\text{boot}} = 20$ and initial constants ($R_0 = M_{\text{boot}}, T_0, T_{\min}, T_{\max}, W_{-1}$) |
| D11 Avalanche payouts and Snowstorm pre-consensus | SELECTED DIRECTION; implemented & verified at >100k TPS | [P06](decisions/issuance-and-time.md) & [Snowstorm Specification](snowstorm.md): soft `ConnectTip` block-parking policies (`StakingRewardsPolicy` `~25%` via `MSG_AVA_STAKE_CONTENDER`, staker-voted `TreasuryPolicy` `~25%` via `MSG_AVA_TREASURY_CONTENDER`, leaving `~50%` to Miner) plus **Snowstorm** multi-peer rateless $\text{GF}(2^{64})$ BCH fountain miniblocks (`RatelessMiniblock`), coupled peeling decoder, Type 1/2/3 algebraic fraud proofs, self-clocking `parent_base_root` layer promotion, hypergeometric peer sampling with sequential confidence accumulation, two-phase anti-drip union + Phase 2 majority boundary filtering and minority demotion, symmetric transitive conflict quarantine (`BatchId(E)` tiebreaking + sticky winner promotion), Avalanche batch finalization (`MSG_AVA_MEMPOOL_BATCH`), and 0-RTT `SnapBlock` (`SEALEDHEADER`) propagation; no hard-consensus treasury state | Implemented on `main` (`c4b33c6d0d..98b7dcf4b5`), verified at `102,482.82 tx/s` 3-peer convergence (`29.47 ms` lag, `100%` `SnapBlock` fast-path hits) |
| D12 Header, PoW and time | CANDIDATE / eligibility and values OPEN | [P04](decisions/header-and-mining.md): 134-byte recursive header, pure tagged BLAKE3 (`H_headerbody`, `H_headerwork`, `H_blockid`) for header hashing and PoW (`BlockID`) (memory-hard/GPU-specific PoW rejected), state commitment, v1's 64-bit nonce and 48-bit timestamp, median-time-past timestamp rule, two-day ASERT half-life as working value | Independent target/ASERT vectors, time-eligibility semantics, header/mining measurements |
| D13 State and coinbase | CANDIDATE / initial values OPEN | P01/P02: parent/height coinbase identity, pipelined coinbase UTXO insertion (`h -> h+1` for $h \ge 1$), `IS_BURN` outputs pruned from `UtxoRoot`, full `StateRoot` envelope with canonical `MonetaryState` (`56B` core `bootstrap_reserve:u64 \|\| tail_subsidy:u64 \|\| prev_work:u256 \|\| ema_block_cost:u64` at $h=0$, `88B` with 32B `history_root` at $h \ge 1$) | Genesis/undo vectors, snapshot trust contract, initial `MonetaryState` values |
| D14 Genesis/network identity | PARTIAL CANDIDATE / values OPEN | P01: independently selected ChainID; P04: explicit header/genesis framing | Parameter/launch manifest, addresses, magic, ports, seeds and source/build reproduction |
| D15 Extension policy | CANDIDATE; all unassigned opcode bytes are generic success points | Every unassigned opcode is OP_SUCCESS_N and unconditionally succeeds for its script invocation; future assignments may only restrict validity while preserving frozen monetary accounting and identical state roots; CHECKDATASIG selectors are closed at 0..3; NOP is permanently a NOP; hard forks are to be made unnecessary where practical, not declared impossible | Review capacity, crypto longevity and all post-genesis claims |

## Decisions that can proceed now

“CANDIDATE” means an implementable proposed rule, not approved mainnet consensus or independent verification. The six packets provide precise proposed encodings, integer algorithms and tradeoffs. [Implementation entry contracts](../plans/implementation-entry.md) identify work that can start without guessing production constants. No decision is FROZEN.

P01–P06 can now drive a complete parameterized reference implementation and local vectors, including the 134-byte pure BLAKE3 recursive header (P04), the canonical 56-byte `MonetaryState` record (P02), the additive bootstrap recurrence + absolute tail issuance $S_n = B_n + T_n$ (P06), and the unified `cu` parabolic transaction cost and block fee-burn floor (P05). Shift parameters ($k_{\text{boot}}, S_{\text{tx\_knee}}, w, E_{\min}, S_{\text{linear}}, S_{\text{quad}}$), primitive `cu` weights, and initial monetary constants ($R_0, T_0, T_{\min}, T_{\max}, W_{-1}, E_0$) remain to be confirmed by simulation and hardware benchmarking before genesis freeze.
The monetary analysis must choose an objective before optimizing it: expected discounted miner profit, reward per hash, or total network issuance are different quantities. Evaluate fixed-share and mobile miners, changing share, discovery randomness, allowed timestamp histories, transaction fees, clipping, and rounding. A reward formula involving difficulty is not by itself a proof of timestamp honesty. Record any impossibility result or tradeoff rather than claiming a “sweet spot” without a feasible-history model.

## Closure record

For each closed decision record: accepted rule and rejected alternatives; a dated acceptance entry in [decision history](decisions/history.md); spec revision and requirement IDs; exact parameter/vector digests; independent reviewer; remaining limitations; affected patches and examples. Reopening before genesis invalidates dependent vectors and measurements. After genesis, a changed validity rule is not an ordinary implementation update.

D10 tail formula: the absolute genesis-anchored tail `F(work)=clip(isqrt(T_g²*work//W_g))` is the candidate, retaining one-block lag. Immutable anchors and formula version 1 are bound to profile identity; 56-byte state caches are checked. Constant calibration and economic/runtime acceptance remain open.


## Typed addresses

[Address specification](addresses.md): type 0 carries an explicit MAST root;
type 1 is the candidate BLAKE3(x-only secp256k1 public key) program defined
there, with a full 32-byte payload and exact 37-byte native VM template.
IDs 2–30 remain reserved and 31 is an extension escape whose encoding is
still open. [Message signing](message-signing.md) specifies the candidate
compact recoverable ECDSA scheme, chain-bound Lotus digest, canonical
keyhash binding, eCash compatibility and validation gates. Native transaction
signatures remain BIP340. Both address and application-proof choices remain
provisional through testnet. Type-1/message implementation is a separate
candidate; native wallet receive/spend is a distinct dependency, not implied
by codec acceptance.


## Partially signed transactions

The [Lotus PSBT profile](psbt.md) retains BIP174's container and key/value
map conventions wherever possible. Native v7 transaction structure does not
fit Bitcoin PSBTv2 output semantics, so the candidate uses the distinct
profile version `0x4c560001` rather than claiming Bitcoin PSBTv2 compatibility.
The initial profile covers ordinary native spends; specialized invocation
construction is outside that initial scope. Its executable
[profile checks](tools/psbt_profile_checks.py) and
[conformance vectors](examples/psbt-profile-vectors.json) bind the proposed
encoding. The profile remains provisional through testnet. Specification
checks do not imply completed daemon implementation or interoperability;
implementation must preserve the specified transaction identity and witness
separation and provide matching signing/finalization tests.


## Forward catch-up and optional history

Design goal: a node may never reach genesis, but it must always be able to
catch up. [N06a](peering.md#snapshot-catch-up-and-optional-history-n06a)
requires authenticated bootstrap followed by forward validation to reach and
follow the moving live tip under explicitly supported workload, hardware,
storage, network and data-availability assumptions, with measured positive
catch-up headroom. Genesis backfill is optional, bounded and lower priority;
it may remain incomplete indefinitely without starving forward validation.
Restart/downtime recovery must preserve separate durable active and historical
progress. Historical archive retrieval is not reverse-peel state verification,
and neither permits concurrent rollback of the active forward state.

The optional archive direction is filesystem-first, separate from active
validation state; no S3 commitment is selected. Trust, finality, consensus and
monetary rules are unchanged. Closure requires moving-tip catch-up measurements,
bounded historical backlog/outage tests, same-node forward/historical isolation
and restart/downtime evidence described in N06a. This direction remains
provisional through testnet; it does not assert these operational properties
are already implemented or tested.


## Historical root verification — provisional

[N06a historical verification policy](peering.md#historical-verification-policy-root-checks-by-default-full-replay-opt-in)
records the proposed default: authenticated backwards root-transition checks,
with full historical transaction/script/signature execution on a separate
opt-in track. Neither full historical replay nor reaching genesis is required
for catch-up. Every newly connected forward block still requires the existing
full consensus validation. This is a pre-testnet/provisional synchronization
policy, not a consensus relaxation or an implemented proof protocol.

Archive commitment checks, block-derived root-transition checks and full
historical execution carry distinct assurance and durable provenance. Arbitrary
root-changing updates do not prove transaction authorization or monetary
validity; full `StateRoot` components, spent/creation proofs, block binding and
expiry-sweep completeness need a precise reviewed proof contract. Authenticated
snapshot/header/PoW and any required finalization anchors remain explicit.
Peer-count majorities are not trust proofs; Avalanche reliance is conditional
on its defined quorum/bootstrap evidence, not a generic historical-validity
claim. Root checking must never mark scripts executed. Proof encoding,
completeness, status reporting, invalid-history handling and independent tests
remain open; no new trust or activation mechanism is adopted here.

---

## References

1. **[Nakamoto 2008]** Satoshi Nakamoto, *"Bitcoin: A Peer-to-Peer Electronic Cash System"*, October 2008 (`https://bitcoin.org/bitcoin.pdf`).
2. **[Chancellor 2026]** Shammah Chancellor, *"Adaptive PoW Monetary Policy Without Oracles: A Constructive Mechanism for Pseudo-Stability via Work-Coupled Tail Emission and Burn"*, Lotus Network Technical Paper, 2026.
3. **[O'Connor, Aumasson, Neves, & Wilcox-O'Hearn 2020]** Jack O'Connor, Jean-Philippe Aumasson, Samuel Neves, and Zooko Wilcox-O'Hearn, *"BLAKE3: One Function, Fast Everywhere"*, January 2020 (`https://github.com/BLAKE3-team/BLAKE3-specs`).
4. **[Wuille, Nick, & Ruffing 2020]** Pieter Wuille, Jonas Nick, and Tim Ruffing, *"BIP 340: Schnorr Signatures for secp256k1"*, Bitcoin Improvement Proposals, January 2020.
5. **[Wuille, Nick, & Towns 2020a]** Pieter Wuille, Jonas Nick, and Anthony Towns, *"BIP 341: Taproot: SegWit version 1 spending rules"*, Bitcoin Improvement Proposals, January 2020.
6. **[Vermorel, Séchet, Chancellor, & van der Wansem 2018]** Joannes Vermorel, Amaury Séchet, Shammah Chancellor, and Tomas van der Wansem, *"Canonical Transaction Ordering for Bitcoin"*, June 12, 2018.
7. **[Vermorel, Séchet, Chancellor, & Cox 2018]** Joannes Vermorel, Amaury Séchet, Shammah Chancellor, and Jason Cox, *"Merklix Tree for Bitcoin"*, July 2018.
8. **[Lundeberg 2020]** Mark B. Lundeberg, *"ASERT (`aserti3-2d`): Absolutely Scheduled Exponentially Rising Targets"*, Bitcoin Cash Specification, July 2020.
9. **[Roughgarden 2020]** Tim Roughgarden, *"Transaction Fee Mechanism Design for the Ethereum Blockchain: An Economic Analysis of EIP-1559"*, `arXiv:2012.00854`, December 2020.
