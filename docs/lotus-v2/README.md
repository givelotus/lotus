# Lotus V2: Programmable Digital Cash Built for Planetary Scale

Status: **specification & reference implementation suite**.

---

## 1. Why Lotus Exists

<div class="lens-grid">
<div class="lens-card lens-consumer">

### In Practice

Digital money shouldn't force a tradeoff between **speed**, **safety**, and **programmability**:
- **Bitcoin** proved that scarce, self-custodied digital cash works—but stalled at ~7 transactions per second, with brittle scripts and fees that price out everyday payments.
- **Account-based smart-contract chains (Ethereum, Solana)** added tokens and applications—but funneled every user into shared global state where one congested NFT mint spikes everyone's fees, front-runners sandwich trades, and a single bad token approval can drain a wallet.

**Lotus V2 is built so anyone can send, save, and program sound digital cash instantly—with sub-second finality, 100,000 to 1,000,000+ transactions per second, self-custodied safety, and a monetary supply that automatically burns fees as network usage grows.**

</div>
<div class="lens-card lens-engineer">

### Under the Hood

Legacy UTXO protocols inherited 2009 serialization bugs, unindexed linear Merkle trees, single-threaded mempool locks (`cs_main`), and block-dependent script opcodes that break mempool monotonicity. Account-model VMs traded away independent input parallelism for shared global storage maps ($O(\log N)$ random I/O per `SSTORE` on a single serialization bottleneck).

**Lotus V2 is a clean-slate UTXO protocol and lock-free C++20 node architecture (`lotusd`) built around one invariant: every transaction, state commitment, and VM invocation partitions horizontally across CPU cores without cross-shard coordination, while freezing a complete validity function at Genesis so disruptive hard forks are unnecessary.**

</div>
</div>

---

## 2. How Lotus Works: Six Core Ideas

### 2.1 Composable Multi-Path Coins & Native Tokens

<div class="lens-grid">
<div class="lens-card lens-consumer">

#### In Practice
- **Smart Vaults & Social Recovery Built In:** A single coin can hold multiple independent rules (*branches*) and spending options (*paths*). For example: *"Spend instantly if both my phone and hardware key sign, OR spend with my phone alone up to \$100/day, OR recover after 90 days with 2-of-3 family keys."*
- **True Native Tokens:** Tokens live directly inside coin outputs alongside native XPI—no ERC-20 wrapper contracts to get hacked, no "infinite approve" phishing traps, and every token transfer is enforced directly by consensus.

</div>
<div class="lens-card lens-engineer">

#### Under the Hood
- **Multi-Branch AND/OR Matrix ([`consensus.md` C05/C09](consensus.md), [`P01`](decisions/encoding-and-signatures.md)):** Each output commits `1..16` distinct 32-byte MAST roots (`branches`) and `1..16` spending `paths` (each a subset of branch indices representable as a single `uint16_t` bitmask). Spending via `path_index` requires satisfying **every** branch in `paths[path_index]`, giving native compositional covenants (e.g. `OwnerAuth ∧ VaultStateInvariant`) without script duplication.
- **Separate Mint-Root Token Identity (`C15`):** A token's 32-byte `token_id` is the MAST root of its minting scripts. Positive token deltas require a dedicated `mint` input (`flags = 0x03`); transfers require zero mint inputs and conserve sums purely via `I_a >= O_a`.

</div>
</div>

---

### 2.2 Monotone Validity & Lock-Free Parallelism

<div class="lens-grid">
<div class="lens-card lens-consumer">

#### In Practice
- **Once Valid, Always Valid:** When you broadcast a transaction and a node accepts it, the arrival of new blocks will **never** invalidate your transaction's scripts or force nodes to re-check your signatures. Unless you double-spend the coin yourself, your payment stays valid until confirmed.
- **Scale With Hardware:** Because independent transactions don't contend on shared global variables, adding more CPU cores scales validation and mempool throughput linearly.

</div>
<div class="lens-card lens-engineer">

#### Under the Hood
- **Strict Monotone Validity ([`consensus.md` C22a](consensus.md), [`rationale.md`](rationale.md)):** No VM opcode reads current block height, time, or header hashes (`OP_BLOCKHEIGHT` and `OP_UTXOPROOFVERIFY` are excluded; time constraints use monotonic transaction/input locks). Consequently, `removeForBlock` never re-executes mempool scripts on block arrival.
- **Prefix-Sharded Trees & Lock-Free Mempool ([`P02`](decisions/commitments-and-state.md)):** Both the block transaction tree (`Subtree A`, keyed by `TxID`) and the UTXO tree (`UtxoRoot`, keyed by `OutpointKey = txid[0..28] || (txid[28..32] ^ vout)`) partition by the exact same 256-bit `TxID` prefix, enabling $2^k$ independent validation shards and $O(1)$ `getblocktemplate` assembly (`H_txroot(0x03 || CoinbaseLeaf || SubtreeA)`).

</div>
</div>

---

### 2.3 Authenticated State & Header History Merkle Tree

<div class="lens-grid">
<div class="lens-card lens-consumer">

#### In Practice
- **Instant Light Wallets & Bridges:** Mobile and browser wallets never have to trust a server blindly. Every 134-byte block header seals a cryptographic commitment to:
  1. **Every unspent coin (`UtxoRoot`)**,
  2. **The chain's exact monetary supply and fee state (`MonetaryState`)**, and
  3. **Every prior block header since Genesis (`history_root`)**.
- With a ~1 KB cryptographic receipt, any device can verify a coin balance or a 5-year-old block in under a millisecond.

</div>
<div class="lens-card lens-engineer">

#### Under the Hood
- **Single-Leaf-Collapsed Sparse UTXO Tree ([`P02`](decisions/commitments-and-state.md)):** Collapsing single-leaf subtrees reduces UTXO Merkle depth from 256 levels to $\sim \log_2(|U|) \approx 27$ levels at $10^8$ coins (~9.5× fewer BLAKE3 hashes per update/proof), while `IS_BURN` (`flags & 0x02`) outputs are pruned immediately (`C17`).
- **Binary Carry-Chain Header History Tree ([`header-history-tree.md`](header-history-tree.md)):** `HeaderHistoryFrontier` maintains 64 level peaks (`peaks[k]` for each set bit of `count = H`) updated in $O(\text{ctz}(H))$ tagged hashes per block and folded into `MonetaryState::history_root`, providing $O(\log H)$ inclusion proofs via `getheaderhistoryproof` / `verifyheaderhistoryproof`.

</div>
</div>

---

### 2.4 Bounded Expressive VM (`int128` to 8,192-Bit Math)

<div class="lens-grid">
<div class="lens-card lens-consumer">

#### In Practice
- **Rich Financial & Cryptographic Contracts:** Native big-integer math (up to 8,192 bits), structured loops, and signature/data verification let developers build automated market makers (AMMs), order books, vaults, and zero-knowledge / post-quantum verifiers directly in Lotus Script.
- **No "Out of Gas" Fee Losses:** Every script's maximum cost is calculated statically *before* it runs. You never lose fees to a transaction that executes halfway and reverts.

</div>
<div class="lens-card lens-engineer">

#### Under the Hood
- **Linear-Time Static Cost & Size Pass ([`P03`](decisions/vm-semantics.md), [`P05`](decisions/resources-and-parameters.md), [`C22`–`C24`](consensus.md)):** Only bounded enumeration loops (`depth <= 2`, `0..256` or `input_count`/`output_count`) exist; dynamic jumps and recursion are forbidden. A single AST pass computes a deterministic upper bound in unified **Cost Units (`cu`)** before VM execution.
- **Two-Phase Deferred Feasibility (`C12a`, [`deferred-checks.md`](deferred-checks.md)):** Input scripts run in parallel and emit declarative output constraints (`ENFORCEOUTPUT`); a post-invocation solver verifies joint conservation and claim feasibility across the transaction.
- **Forward-Compatible `OP_SUCCESS_N` (`C02`):** Unassigned opcodes succeed during consensus instruction-boundary scans (while policy declines to relay them until assigned), allowing soft-fork opcode upgrades without hard forks.

</div>
</div>

---

### 2.5 Smooth Issuance, Work-Responsive Tail & 50% Fee Burn

<div class="lens-grid">
<div class="lens-card lens-consumer">

#### In Practice
- **No Abrupt Halving Cliffs:** Instead of jarring 4-year supply shocks, Lotus V2 releases its bootstrap reserve smoothly block-by-block alongside a work-responsive tail subsidy that scales with real mining security.
- **Automatic Fee Burn:** At least **50% of every transaction's base fee** (plus 100% of token-creation burn floors and congestion surcharges) is permanently burned, making XPI deflationary under high usage.

</div>
<div class="lens-card lens-engineer">

#### Under the Hood
- **Exact Integer Recurrences ([`P05`](decisions/resources-and-parameters.md), [`P06`](decisions/issuance-and-time.md), [`C16`/`C25`](consensus.md)):**
  - Step $n$ subsidy is $S_n = B_n + T_n$, where $B_n = \max(1, R_n \gg 20)$ telescopes $\sum_{n=0}^{\infty} B_n = R_0$ to the exact atom, and $T_{n+1} = \text{clamp}(\text{isqrt}(\lfloor T_g^2 W_n / W_g \rfloor), T_{\min}, T_{\max})$.
  - Replaces rigid `MAX_TX_BYTES` / `MAX_BLOCK_BYTES` walls with parabolic cost curves $C_{\text{tx}} = L + (L^2 \gg S_{\text{tx\_knee}})$ and a mandatory fee-burn floor anchored to the rolling integer EMA $E_n$ (`ema_block_cost:u64` in `MonetaryState`).

</div>
</div>

---

### 2.6 134-Byte Pure BLAKE3 Headers, Avalanche Finality & Snowstorm Pseudo-Consensus

<div class="lens-grid">
<div class="lens-card lens-consumer">

#### In Practice
- **Sub-Second Finality & Instant `SnapBlock` Propagation:** **Snowstorm** rateless fountain pre-consensus crystallizes mempool epochs before a block is even mined, so newly found blocks propagate as a **compact sealed header + coinbase (`290 B` with the 134-byte V2 header, or `240 B` on legacy 84B-header benchmark frames)** in **under 0.1 milliseconds** (`>2,500×` faster than post-block recovery) while Avalanche locks in finality in under 1 second.
- **Pseudo-Consensus (Optional, Incentive-Compatible):** Nodes and miners don't *have* to run Snowstorm to follow or mine valid blocks—Proof-of-Work and Lotus V2's deterministic rules remain the sole hard consensus requirement. However, participating is strongly advantageous because Snowstorm resolves double-spends deterministically before mining and eliminates post-block propagation stalls.
- **Aligned Incentives (Soft Avalanche Coordination Policy):** While hard consensus (`C16`) places zero mandatory destination splits on the coinbase, staking nodes coordinate a soft **~50% Miner / ~25% Staker / ~25% Staker-Voted Treasury** block-parking policy (`P06`, `D11`) once Avalanche quorum is established.

</div>
<div class="lens-card lens-engineer">

#### Under the Hood
- **Single Hash Primitive Across the Stack ([`P04`](decisions/header-and-mining.md)):** The 134-byte header uses 48-bit timestamps (`time:u48`) and three domain-tagged BLAKE3 stages (`H_headerbody` $\to$ `H_headerwork` $\to$ `H_blockid`), allowing miners to grind an 18-byte work suffix (`nonce1:u64 || nonce2:u64 || extra_work:u16`) within a single 64-byte BLAKE3 compression block.
- **Snowstorm Multi-Peer Rateless $\text{GF}(2^{64})$ BCH Fountain Codes ([`snowstorm.md`](snowstorm.md), [`peering.md`](peering.md), [`mempool-reconciliation.md`](mempool-reconciliation.md)):** Nodes synchronize mempool epochs across multiple divergent peers simultaneously using 913-byte `RatelessMiniblock` streams (`32` cells $\times$ `(count, s1, s3, s5)` in $\text{GF}(2^{64})$ with geometric decimation $1/2^L$), coupled multi-peer Berlekamp-Massey/Chien peeling (~30% cell overhead), symmetric `BatchId(E)` conflict quarantine, and Type 1/2/3 algebraic fraud proofs.

</div>
</div>

---

## 3. What Lotus Specifies: Document Map

> **Interactive HTML Documentation:** Open [`site/index.html`](site/index.html) (or run `python3 docs/lotus-v2/tools/render_html.py`) for the rendered HTML book with **Full View / Overview / Under the Hood** toggling.

### Core Consensus & Decision Packets (`P01`–`P06`)

| Document | Scope & Key Contents |
| :--- | :--- |
| **[Consensus Specification (`consensus.md`)](consensus.md)** | Normative validity rules **C01–C28**: encoding, MAST branches, `IndexedTreeRoot`, UTXO resolution, fee burn, VM bounds, and block transitions. |
| **[Header History Merkle Tree (`header-history-tree.md`)](header-history-tree.md)** | `HeaderHistoryFrontier`, `HeaderHistoryRoot` in `MonetaryState`, $O(\log H)$ `HeaderInclusionProof`, and RPC verification. |
| **[P01: Encoding & Signatures (`decisions/encoding-and-signatures.md`)](decisions/encoding-and-signatures.md)** | 16-byte transaction prefix, packed 64-bit lock word, input kinds (`01` spend, `02` coinbase, `03` mint), output flags (`HAS_TOKEN`, `IS_BURN`, `HAS_STATE`), and $O(1)$ Merkleized BIP340 sighash modes. |
| **[P02: Commitments & State (`decisions/commitments-and-state.md`)](decisions/commitments-and-state.md)** | BLAKE3 domain registry, Branch MAST, `IndexedTreeRoot`, prefix-sharded `TxRoot` (`Subtree A`), single-leaf-collapsed `UtxoRoot`, `MonetaryState`, `StateRoot`, and `HEADER_HISTORY`. |
| **[P03: VM Semantics (`decisions/vm-semantics.md`)](decisions/vm-semantics.md)** | Structured control flow, enumeration loops, `OP_SUCCESS_N` scan, 16..1024-byte (`128..8192`-bit) signed two's-complement arithmetic, and introspection opcodes. |
| **[P04: Header & Mining (`decisions/header-and-mining.md`)](decisions/header-and-mining.md)** | 134-byte header layout, 48-bit timestamp, two-stage BLAKE3 PoW (`H_headerbody` / `H_headerwork` / `H_blockid`), and integer ASERT difficulty adjustment. |
| **[P05: Resources & Parameters (`decisions/resources-and-parameters.md`)](decisions/resources-and-parameters.md)** | Unified Cost Units (`cu`), linear static upper-bound pass, parabolic transaction cost $C_{\text{tx}}$, rolling `ema_block_cost` $E_n$, and mandatory block fee-burn floor. |
| **[P06: Issuance & Time (`decisions/issuance-and-time.md`)](decisions/issuance-and-time.md)** | Additive subsidy $S_n = B_n + T_n$ (telescoping bootstrap reserve $R_n$ + work-responsive adaptive tail $T_n$), 50% fee burn, and Avalanche 50/25/25 reward coordination. |
| **[Deferred Checks (`deferred-checks.md`)](deferred-checks.md)** | Two-phase parallel input script execution and post-invocation `ENFORCEOUTPUT` conservation/feasibility verification (`C12a`). |
| **[Design Rationale (`rationale.md`)](rationale.md)** | Why `OP_BLOCKHEIGHT`, `OP_UTXOPROOFVERIFY`, and read-only inputs were rejected to preserve monotone mempool validity (`C22a`), and how to build auctions, timers, and shared state instead. |

### Developer, Wallet & Application Specifications

| Document | Scope & Key Contents |
| :--- | :--- |
| **[Script & Wallet ABI (`script-abi.md`)](script-abi.md)** | Stack framing, canonical 16-byte booleans, `int128`..`int8192` operand rules, and compiler calling conventions. |
| **[Native Addresses (`addresses.md`)](addresses.md)** | Typed `xpi1...` address format for explicit MAST roots and parameterized standard templates. |
| **[Message Signing (`message-signing.md`)](message-signing.md)** | Off-chain application message signatures and compact branch-membership proofs. |
| **[PSBT Profile (`psbt.md`)](psbt.md)** | Native Lotus V2 Partially Signed Transaction interchange format and hardware-wallet signing vectors. |
| **[Browser Connect (`browser-connect.md`)](browser-connect.md)** | Privacy-preserving W3C `MessageChannel` (`lotus-connect/1`) dApp-to-wallet capability protocol with zero supercookie tracking. |
| **[Worked Smart Contract Examples (`examples/README.md`)](examples/README.md)** | Executable contract gallery, EVM-to-Lotus porting guides ([ERC-20](examples/evm-porting/erc20.md), [ERC-721](examples/evm-porting/erc721.md), [AMMs & Markets](examples/evm-porting/markets.md), [Controls](examples/evm-porting/controls.md)), and test vectors. |

### Networking, Pre-Consensus & Verification

| Document | Scope & Key Contents |
| :--- | :--- |
| **[Snowstorm Pseudo-Consensus (`snowstorm.md`)](snowstorm.md)** | Multi-peer rateless $\text{GF}(2^{64})$ BCH fountain miniblocks (`RatelessMiniblock`), coupled peeling decoder (~30% cell overhead), symmetric `BatchId(E)` conflict quarantine, Type 1/2/3 algebraic fraud proofs, and 0-RTT `SnapBlock` propagation. |
| **[Peering & Pre-Consensus (`peering.md`)](peering.md)** | High-throughput P2P relay, `submitminedheader`, Avalanche batch voting, and bulk template pre-consensus. |
| **[Mempool Reconciliation (`mempool-reconciliation.md`)](mempool-reconciliation.md)** | Pinned epoch snapshots and authenticated prefix-page set reconciliation. |
| **[Validation & Conformance (`validation.md`)](validation.md)** | Reference evaluator boundary, differential test obligations, and Genesis launch gates. |
| **[Decision Register (`decisions.md`)](decisions.md)** | Status of all decision packets (`D01`–`D15`) and pre-genesis calibration items. |
| **[Decision History (`decisions/history.md`)](decisions/history.md)** | Dated record of decisions: date, decision ID, change and link. |

### How these documents are organized

- **Specifications and `decisions/`** state rules, rationale and status (candidate, open, rejected).
- **[`decisions/history.md`](decisions/history.md)** holds the dated decision history.

---

## References

1. **[Nakamoto 2008]** Satoshi Nakamoto, *"Bitcoin: A Peer-to-Peer Electronic Cash System"*, October 2008 (`https://bitcoin.org/bitcoin.pdf`).
2. **[Chancellor 2026]** Shammah Chancellor, *"Adaptive PoW Monetary Policy Without Oracles: A Constructive Mechanism for Pseudo-Stability via Work-Coupled Tail Emission and Burn"*, Lotus Network Technical Paper, 2026.
3. **[Oak 2026]** Professor Oak, *"Snowball to Snowstorm: Rateless Set Reconciliation and Probabilistic Mempool Preconsensus for Proof-of-Work Blockchains"*, October 2026.
4. **[O'Connor, Aumasson, Neves, & Wilcox-O'Hearn 2020]** Jack O'Connor, Jean-Philippe Aumasson, Samuel Neves, and Zooko Wilcox-O'Hearn, *"BLAKE3: One Function, Fast Everywhere"*, January 2020 (`https://github.com/BLAKE3-team/BLAKE3-specs`).
5. **[Vermorel, Séchet, Chancellor, & van der Wansem 2018]** Joannes Vermorel, Amaury Séchet, Shammah Chancellor, and Tomas van der Wansem, *"Canonical Transaction Ordering for Bitcoin"*, June 12, 2018.
6. **[Vermorel, Séchet, Chancellor, & Cox 2018]** Joannes Vermorel, Amaury Séchet, Shammah Chancellor, and Jason Cox, *"Merklix Tree for Bitcoin"*, July 2018.
7. **[Wuille, Nick, & Ruffing 2020]** Pieter Wuille, Jonas Nick, and Tim Ruffing, *"BIP 340: Schnorr Signatures for secp256k1"*, Bitcoin Improvement Proposals, January 2020.
8. **[Wuille, Nick, & Towns 2020a]** Pieter Wuille, Jonas Nick, and Anthony Towns, *"BIP 341: Taproot: SegWit version 1 spending rules"*, Bitcoin Improvement Proposals, January 2020.
9. **[Dahlberg, Pulls, & Peeters 2016]** Rasmus Dahlberg, Tobias Pulls, and Roel Peeters, *"Efficient Sparse Merkle Trees: Caching Strategies and Secure (Non-)Membership Proofs"*, in *Proceedings of the 21st Nordic Conference on Secure IT Systems (NordSec 2016)*, LNCS vol. 10014, pp. 199–215, 2016 (`IACR ePrint 2016/683`).
10. **[Rocket et al. 2019]** Team Rocket, Maofan Yin, Kevin Sekniqi, Robbert van Renesse, and Emin Gün Sirer, *"Scalable and Probabilistic Leaderless BFT Consensus through Metastability"*, `arXiv:1906.08936`, 2019.
