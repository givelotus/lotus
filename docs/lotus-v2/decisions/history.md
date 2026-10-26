# Decision history

Dated record of decisions affecting the Lotus V2 specification. Specifications
and decision packets state rules, rationale and status only; when and why a
state changed is recorded here. Each entry gives the date, the decision ID, what
changed and a link to the governing text.

| Date | Decision | Change | Link |
| --- | --- | --- | --- |
| 2026-10-09 | P01–P06 | Decision packets P01–P06 issued as recommended candidates. | [P01](encoding-and-signatures.md), [P02](commitments-and-state.md), [P03](vm-semantics.md), [P04](header-and-mining.md), [P05](resources-and-parameters.md), [P06](issuance-and-time.md) |
| 2026-10-09 | D05 | Token identity selected: a token ID is the root of its mint scripts (program-derived). Outpoint-derived identity superseded. | [P06](issuance-and-time.md), [rationale](../rationale.md) |
| 2026-10-09 | D06 | Read-only reference inputs removed; every inspected coin is consumed (C13). | [decision register](../decisions.md), [rationale](../rationale.md) |
| 2026-10-09 | Addresses | Address encoding direction: cashaddr-style, checksum covers the prefix, no `:` separator, prefix-omitted addresses recovered by checksum. | [script ABI](../script-abi.md) |
| 2026-10-11 | D15 | Every unassigned opcode byte is a generic `OP_SUCCESS_N`, replacing the eight EXTENSION no-ops and reserved CHECKDATASIG selectors. | [P03](vm-semantics.md) |
| 2026-10-13 | D12 | P04 updated: no deployed ASIC interface preserved, lucky-block pointer dropped, recursive header kept for partial disclosure, pure tagged BLAKE3 for header hashing and PoW. | [P04](header-and-mining.md) |
| 2026-10-14 | D08, D13 | P05/P06 updated: 1,000 atoms per decimal kB, coinbase/envelope charges deducted from reward, genesis with zero native issuance, coinbase with zero or one opaque payload. | [P05](resources-and-parameters.md), [P06](issuance-and-time.md), [P01](encoding-and-signatures.md) |
| 2026-10-14 | Script ABI | TypeScript compiler (small Finch-spec-inspired typed stack pipeline) selected; Python and TypeScript are the first client targets. | [script ABI](../script-abi.md) |
| 2026-10-14 – 2026-10-16 | D11 | Avalanche-controlled coinbase payouts selected, using Bitcoin ABC soft block-parking with a ~50/25/25 miner/staker/treasury split; treasury contracts and protocol faucet state excluded. | [P06](issuance-and-time.md), [rationale](../rationale.md) |
| 2026-10-15 | D10 | Absolute genesis-anchored tail `F(work)=clip(isqrt(T_g²*work//W_g))` adopted after the arithmetic review, superseding the recurrent tail. Constants remain open. | [P06](issuance-and-time.md), [consensus C16](../consensus.md) |
| 2026-10-15 | D12 | Avalanche/PoW chain selection follows Bitcoin ABC's rules and defaults at pinned base `1fb7db17c176cdea8a2c60d887891589382ee4e3`; no separate Lotus work-override threshold. | [P04](header-and-mining.md) |
| 2026-10-15 | D14 | Peering: ABC TCP first, QUIC second, new development network magic, P2P port 10605, RPC port 10604. | [peering](../peering.md) |
| 2026-10-15 | D14 | Separate development-only profile proposed (`lotus-v2-devnet-20261015-absolute1`). | [development profile](../development-profile.md) |
| 2026-10-16 | D02, D13 | Horizontal sharding: prefix-keyed Merklix `Subtree A` transaction root, prefix-preserving `OutpointKey`, pipelined coinbase UTXO insertion (`h -> h+1`). | [P02](commitments-and-state.md) |
| 2026-10-19 | Addresses | Typed addresses: type 0 carries an explicit MAST root; provisional through testnet. | [addresses](../addresses.md) |
| 2026-10-20 | Addresses | Type 1 x-only keyhash template added as candidate. | [addresses](../addresses.md) |
| 2026-10-20 | Message signing | Compact recoverable ECDSA over a chain-bound Lotus digest selected as candidate; provisional through testnet. | [message signing](../message-signing.md) |
| 2026-10-20 | PSBT | Lotus PSBT profile `0x4c560001` adopted as candidate; provisional through testnet. | [PSBT](../psbt.md) |
| 2026-10-20 | Browser connect | `lotus-connect/1` adopted as candidate; provisional through testnet. | [browser connect](../browser-connect.md) |
| 2026-10-20 | N06a | Forward catch-up requirement adopted (“possibly never reaching genesis is reasonable, but never being able to catch up is not”); optional bounded history; filesystem-first archive. | [peering N06a](../peering.md), [decision register](../decisions.md) |
| 2026-10-20 | N06a | Historical verification policy: authenticated root-transition checks by default, full historical replay opt-in. Provisional. | [peering N06a](../peering.md) |
| 2026-10-21 | D11 | Epoch reconciliation core lifecycle approved after two independent review rounds; recovered members join the revisable epoch, superseding the older pre-voting admission cutoff. | [mempool reconciliation](../mempool-reconciliation.md) |
| 2026-10-24 | D11 | **Snowstorm** multi-peer rateless $\text{GF}(2^{64})$ BCH fountain pseudo-consensus adopted and verified at `102,482.82 tx/s`: 913-byte `RatelessMiniblock` streams (`(count, s1, s3, s5)` with multi-scale decimation $1/2^L$), coupled multi-peer peeling, Type 1/2/3 algebraic fraud proofs, self-clocking `parent_base_root` layer promotion, two-phase anti-drip union (`kMaxUnionRounds = 2`) with symmetric Phase 2 minority-support demotion, symmetric transitive conflict quarantine with topological `BatchId(E)` tiebreaking into Epoch $E+1$, Avalanche batch finalization (`MSG_AVA_MEMPOOL_BATCH`), and 0-RTT `SnapBlock` (`SEALEDHEADER`) propagation (`88.6 µs`). Supersedes earlier D11 pairwise/root-gossip/clock research proposals. | [Snowstorm](../snowstorm.md), [peering](../peering.md), [mempool reconciliation](../mempool-reconciliation.md) |

---

## References

1. **[Nakamoto 2008]** Satoshi Nakamoto, *"Bitcoin: A Peer-to-Peer Electronic Cash System"*, October 2008 (`https://bitcoin.org/bitcoin.pdf`).
2. **[Chancellor 2026]** Shammah Chancellor, *"Adaptive PoW Monetary Policy Without Oracles: A Constructive Mechanism for Pseudo-Stability via Work-Coupled Tail Emission and Burn"*, Lotus Network Technical Paper, 2026.
3. **[Oak 2026]** Professor Oak, *"Snowball to Snowstorm: Rateless Set Reconciliation and Probabilistic Mempool Preconsensus for Proof-of-Work Blockchains"*, October 2026.
4. **[O'Connor, Aumasson, Neves, & Wilcox-O'Hearn 2020]** Jack O'Connor, Jean-Philippe Aumasson, Samuel Neves, and Zooko Wilcox-O'Hearn, *"BLAKE3: One Function, Fast Everywhere"*, January 2020 (`https://github.com/BLAKE3-team/BLAKE3-specs`).
5. **[Wuille, Nick, & Ruffing 2020]** Pieter Wuille, Jonas Nick, and Tim Ruffing, *"BIP 340: Schnorr Signatures for secp256k1"*, Bitcoin Improvement Proposals, January 2020.
6. **[Wuille, Nick, & Towns 2020a]** Pieter Wuille, Jonas Nick, and Anthony Towns, *"BIP 341: Taproot: SegWit version 1 spending rules"*, Bitcoin Improvement Proposals, January 2020.
