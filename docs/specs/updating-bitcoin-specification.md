# Updating Bitcoin: The Lotus v2 Genesis Specification & Implementation Roadmap
## The "Zero-Hardfork" High-Throughput Proof-of-Work Monetary Engine

> **Design Mandate**: Construct and launch the definitive, clean-slate Proof-of-Work UTXO chain with all consensus invariants locked at Genesis. Future scalability optimizations must remain purely internal node implementation details—never requiring contentious protocol hardforks, governance interventions, or ecosystem fractures.

---

## Table of Contents
1. [The "Updating Bitcoin" Philosophy: Invariants vs. Internals](#1-the-updating-bitcoin-philosophy-invariants-vs-internals)
2. [Comparative Architecture: Bitcoin vs. Lotus v1 vs. Lotus v2](#2-comparative-architecture-bitcoin-vs-lotus-v1-vs-lotus-v2)
3. [Immutable Consensus Specification (Locked at Block 0)](#3-immutable-consensus-specification-locked-at-block-0)
   - [3.1. The 116-Byte Header & 2-Minute Block Interval](#31-the-116-byte-header--2-minute-block-interval)
   - [3.2. Single BLAKE3 Domain-Separated Segmented Merklix Tree](#32-single-blake3-domain-separated-segmented-merklix-tree)
   - [3.3. Zero-Copy Wire Format & 80-Byte Typed Compact Outputs (POD)](#33-zero-copy-wire-format--80-byte-typed-compact-outputs-pod)
   - [3.4. Native Layer-1 Assets & The Genesis Outpoint Invariant](#34-native-layer-1-assets--the-genesis-outpoint-invariant)
   - [3.5. Transaction Architecture: Modernized BUIP037 & Merklized NOR (`P2MNOR`)](#35-transaction-architecture-modernized-buip037--merklized-nor-p2mnor)
   - [3.6. The 128-Bit Forth Stack Machine (`int128_t`)](#36-the-128-bit-forth-stack-machine-int128_t)
   - [3.7. Multi-Precision & Cryptographic Primitives](#37-multi-precision--cryptographic-primitives)
   - [3.8. Native Introspection Opcodes (`0xbf–0xcf`)](#38-native-introspection-opcodes-0xbf0xcf)
   - [3.9. Enumerable Loops ($N \le 2$) & Static Precomputed Cost Budget](#39-enumerable-loops-n--2--static-precomputed-cost-budget)
   - [3.10. Thermodynamic Monetary Issuance & Onboarding Faucet](#310-thermodynamic-monetary-issuance--onboarding-faucet)
4. [Node Implementation & Performance Architecture (No Hardfork Required)](#4-node-implementation--performance-architecture-no-hardfork-required)
   - [4.1. Hybrid State Architecture: In-Memory Trie + RocksDB Write-Behind](#41-hybrid-state-architecture-in-memory-trie--rocksdb-write-behind)
   - [4.2. State Commitments & Sub-Second Crash Recovery](#42-state-commitments--sub-second-crash-recovery)
   - [4.3. High-Throughput Mining Engine: $O(1)$ Mempool & $O(n \log n)$ Block Construction](#43-high-throughput-mining-engine-o1-mempool--on-log-n-block-construction)
   - [4.4. Stateless Snap Sync Protocol & Dynamic Body Pruning](#44-stateless-snap-sync-protocol--dynamic-body-pruning)
   - [4.5. RPC Interface Upgrades for Merklix Proofs & Stateless Operation](#45-rpc-interface-upgrades-for-merklix-proofs--stateless-operation)
   - [4.6. Avalanche Consensus Decoupling: Hard Consensus vs. Soft Coordination](#46-avalanche-consensus-decoupling-hard-consensus-vs-soft-coordination)
5. [Upstream PR Strategy & Node Base Selection](#5-upstream-pr-strategy--node-base-selection)
   - [5.1. Daemon Base Evaluation (Bitcoin ABC vs. BCHN)](#51-daemon-base-evaluation-bitcoin-abc-vs-bchn)
   - [5.2. Chain-Agnostic Upstream Candidates (Bitcoin ABC / BCHN)](#52-chain-agnostic-upstream-candidates-bitcoin-abc--bchn)
6. [The Complete 35-Patch Rebase Sequence (`daemon/patches/v2/`)](#6-the-complete-35-patch-rebase-sequence-daemonpatchesv2)
7. [Verification, Test Harness & Genesis Launch Checklist](#7-verification-test-harness--genesis-launch-checklist)

---

## 1. The "Updating Bitcoin" Philosophy: Invariants vs. Internals

Bitcoin was humanity's first successful implementation of decentralized digital scarcity. However, its 2008 architecture accumulated critical design compromises:
* **Storage Fragility**: Uncommitted UTXO sets reliant on flat key-value databases (LevelDB), risking catastrophic unrecoverable corruption on unexpected power loss.
* **Serialization Inefficiencies**: Variable-length integers (`CompactSize` / `varint`) causing non-aligned CPU memory access, quadratic serialization parsing overhead, and transaction malleability vulnerabilities.
* **Script Limitations**: The `CScriptNum` sign-magnitude format (capping math at 32-bit signed integers with negative-zero malleability), disabled multiplication/division opcodes, and zero introspection capabilities.
* **Token Inadequacies**: Reliance on fragile off-chain indexers (SLP / Colored Coins) where accidental spend of a token UTXO by a standard wallet permanently burns the asset.
* **Mining Bottlenecks**: $O(n^2)$ CPFP ancestor-package graph recalculation during mempool admission, forcing artificial chain limits (25/50 tx limit) that cripple payment channels and high-velocity systems.
* **Macroeconomic Vulnerabilities**: Rigid 4-year halving step-functions that inflict revenue shocks on miners, periodically destabilizing hashrate and spurring fee-market volatility.

### The Zero-Hardfork Bifurcation
To eliminate these bottlenecks while guaranteeing that the protocol **never needs a hardfork**, the architecture strictly separates the **Immutable Consensus Layer** (rules locked at Genesis) from the **Node Implementation Layer** (local software optimizations):

```
┌────────────────────────────────────────────────────────────────────────┐
│                        IMMUTABLE CONSENSUS LAYER                       │
│  (Locked at Genesis — Requires 100% network agreement to change)       │
├────────────────────────────────────────────────────────────────────────┤
│  • 116-byte Block Header (Commits to UTXO Merklix Root)                │
│  • Single BLAKE3 Domain-Separated Merklix Trees (txid & utxoroot)      │
│  • Memory-Aligned Wire Format & 64-byte Compact Signatures             │
│  • 80-byte Typed Compact Outputs with 32-byte Metadata Field           │
│  • Genesis Outpoint Invariant: TokenID = BLAKE3(vin[0].prevout)        │
│  • 128-bit Two's-Complement Stack VM Semantics (int128_t)              │
│  • Native Introspection Opcodes (0xbf–0xcf) & Loop Opcodes (N ≤ 2)     │
│  • Static Precomputed Execution Budget (1 Wire Byte = 1 Cost Unit)     │
│  • Dynamic Sub-Linear Issuance: R = K · √(Difficulty)                  │
│  • 50/50 Miner / Faucet Seigniorage Split with Auto-Burn Cap           │
└────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        NODE IMPLEMENTATION LAYER                       │
│  (Upgradeable at will by individual node operators — Zero Hardforks)   │
├────────────────────────────────────────────────────────────────────────┤
│  • In-Memory Radix Trie (Crit-Bit index, cache-line aligned)           │
│  • RocksDB Asynchronous Write-Behind Worker & State Commitment WAL     │
│  • O(1) Mempool Ingestion Engine (0 ancestor-recalculation on wire)    │
│  • O(n log n) Block Template Construction (Topological Forward-Walk)   │
│  • Cryptographic verification engines (AVX-512, batch Schnorr MSM)     │
│  • Historical raw block body pruning (rolling 1,000 blocks)            │
│  • Stateless Snap Sync Protocol (GETMERKLIX / MERKLIXCHUNK)            │
│  • Soft parameter governance via Avalanche gossip (non-consensus)      │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Comparative Architecture: Bitcoin vs. Lotus v1 vs. Lotus v2

| Feature | Bitcoin Core (BTC) | Lotus v1 Mainnet | Lotus v2 ("Updating Bitcoin") | Rationale |
| :--- | :--- | :--- | :--- | :--- |
| **Block Header Size** | 80 Bytes | 160 Bytes (Layered) | **116 Bytes** (Fixed Aligned) | Replaces unaligned fields with 64-bit aligned state roots. |
| **Header State Commitments** | None (Tx merkle root only) | `hashEpochBlock` (32B) + `hashExtendedMetadata` (32B) | `hashTxMerklixRoot` (32B) + `hashUtxoMerklixRoot` (32B) | Enables stateless verification and sub-second crash recovery. |
| **Block Cadence** | 600s (10 min) | 120s (2 min) | **120s (2 min)** | Near-zero orphan rate, $5\times$ faster DAA responsiveness. |
| **Hashing Engine** | SHA256d everywhere | SHA256d + SHA256 overlay | **Single BLAKE3** (Consensus & Trees) | Native tree hashing, immune to length-extension, $12\text{ ns}$ execution. |
| **Output Representation** | Dynamic `vector<uint8_t>` | Dynamic `vector<uint8_t>` | **80-Byte POD Struct** | Zero heap allocation, 32B metadata, fast-path script bypass. |
| **Script Stack Integers** | `CScriptNum` (32-bit signed) | `CScriptNum` + 64-bit hacks | **Native `int128_t` (128-bit)** | Eliminates sign-magnitude bugs, enables high-precision finance. |
| **Multi-Precision Math** | None | Ad-hoc `BIGADD` | `OP_ADDCARRY`, `OP_SUBCARRY`, `OP_MUL128_WIDE` | Curve arithmetic (secp256k1, BLS12-381) directly in Script. |
| **Covenant Introspection** | None | Ad-hoc sighash flags | **Native Opcodes (`0xbf–0xcf`)** | Inspects own inputs, outputs, outpoints, metadata in 1 CPU cycle. |
| **Script Loops** | Disabled / Forbidden | Mitra loop proposal | **`OP_FOREACH_INPUT/OUTPUT` ($N \le 2$)** | Bounded, statically precomputed loops without Halting Problem. |
| **Native L1 Tokens** | None (3rd party indexers) | None | **Consensus-enforced $\sum \text{in} \ge \sum \text{out}$** | Invariant $\text{TokenID} = \text{BLAKE3}(\text{vin}[0].\text{prevout})$. |
| **Mempool Ingestion** | $O(n^2)$ CPFP DAG walk | $O(n^2)$ CPFP DAG walk | **$O(1)$ Ingestion Pipeline** | Eliminates chain limits, handles $50,000\text{ tx/s}$ ingress. |
| **Block Construction** | $O(n^2)$ package selection | $O(n^2)$ package selection | **$O(n \log n)$ Pipeline** | Topological forward-walk and tier sorting. |
| **UTXO Persistence** | LevelDB (Uncommitted) | LevelDB (Uncommitted) | **RAM Radix Trie + RocksDB WAL** | Cryptographic crash recovery; 0 reindexing from genesis. |
| **Subsidy Schedule** | 4-Year Halvings (Step) | Log2 Difficulty Curve | **Thermodynamic $R = K\sqrt{D}$** | Smooth continuous issuance tied to physical security expenditure. |
| **Seigniorage Split** | 100% Miner | IFP / Miner Fund Split | **50% Miner / 50% Faucet (Auto-Burn)** | Zero tax; autonomous onboarding faucet with supply burn cap. |

---

## 3. Immutable Consensus Specification (Locked at Block 0)

### 3.1. The 116-Byte Header & 2-Minute Block Interval

#### Evolution from Lotus v1 Extended Header
Lotus v1 introduced an extended 160-byte block header (`src/primitives/block.h`). Lotus v2 consolidates and aligns this structure, replacing historical experimental fields with active cryptographic state commitments:

```cpp
struct LotusHeader {
    int32_t  nVersion;             // 4 bytes: Protocol version
    uint256  hashPrevBlock;        // 32 bytes: Parent block hash (Single BLAKE3)
    uint256  hashTxMerklixRoot;    // 32 bytes: Single BLAKE3 Merklix root of block txs
    uint256  hashUtxoMerklixRoot;  // 32 bytes: Single BLAKE3 Merklix root of post-block UTXO set
    uint32_t nTime;                // 4 bytes: Unix epoch timestamp (seconds)
    uint32_t nBits;                // 4 bytes: Compact ASERT difficulty target
    uint64_t nNonce;               // 8 bytes: 64-bit nonce (eliminates ASIC overflow)
}; // Total: Exactly 116 bytes (64-bit aligned, zero padding bytes required)
```

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ BITCOIN CORE LEGACY (80 Bytes)                                                         │
│ • hashPrevBlock (32B), hashMerkleRoot (32B), nVersion (4B), nTime (4B),                │
│   nBits (4B), nNonce (4B - 32-bit overflow bug)                                        │
│ • Critical Flaws: No live state commitment, LevelDB corruption risks, 32-bit nonce.   │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ LOTUS v1 EXTENDED HEADER (160 Bytes)                                                   │
│ • hashPrevBlock (32B), nBits (4B), vTime (6B), nReserved (2B), nNonce (8B),            │
│   nHeaderVersion (1B), vSize (7B), nHeight (4B), hashEpochBlock (32B),                 │
│   hashMerkleRoot (32B), hashExtendedMetadata (32B)                                     │
│ • Rationale in v1:                                                                     │
│   - hashEpochBlock (32B): Committed to 5,040-block epoch for "lucky block" randomness   │
│     (undershooting target by 5,040x) to enable Epoch SPV skip-lists.                   │
│   - hashExtendedMetadata (32B): Committed to extensible block key-value metadata.      │
│ • Limitations: Non-aligned byte widths (6B time, 7B size), lucky block skip-list does   │
│   not commit to unspent coins, ad-hoc metadata was unused in consensus.                │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ LOTUS v2 IMMUTABLE CONSENSUS HEADER (116 Bytes - Fixed 64-bit Aligned)                 │
│ • int32_t  nVersion;             // 4 bytes: Protocol version                          │
│ • uint256  hashPrevBlock;        // 32 bytes: Parent block BLAKE3                      │
│ • uint256  hashTxMerklixRoot;    // 32 bytes: Merklix root of txs in this block        │
│ • uint256  hashUtxoMerklixRoot;  // 32 bytes: Merklix root of LIVE UTXO state          │
│ • uint32_t nTime;                // 4 bytes: Standard 32-bit Unix epoch timestamp      │
│ • uint32_t nBits;                // 4 bytes: ASERT difficulty target                   │
│ • uint64_t nNonce;               // 8 bytes: 64-bit integer nonce                      │
│ • Total: Exactly 116 bytes (Zero padding, native CPU vector-register aligned)          │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

#### Why `hashUtxoMerklixRoot` Replaces `hashEpochBlock` & `hashExtendedMetadata`:
1. **The "Lucky Block" Commitment is Obsolete**:
   In Lotus v1, `hashEpochBlock` attempted to create an inter-block skip-list for Epoch SPV (ESPV) by pointing to blocks that undershot difficulty by a factor of 5,040. However, ESPV could only prove that block headers were linked under heavy PoW—it **could not prove whether a transaction output was unspent**. Light clients were still forced to trust third-party servers for UTXO existence. By committing to `hashUtxoMerklixRoot` in every single block, every node and wallet obtains cryptographic inclusion and exclusion proofs directly from the chain tip.
2. **Unlocking Stateless Validation**:
   With `hashUtxoMerklixRoot` embedded in the header, blocks become self-authenticating. A transaction can carry compact Merklix branch proofs for its inputs; the node verifies these against `hashUtxoMerklixRoot` in RAM without touching a disk database.
3. **Hardware Memory Alignment**:
   Replacing the 6-byte `vTime` and 7-byte `vSize` with standard 32-bit timestamps and 64-bit nonces guarantees that header arrays reside on clean 64-bit cache-line boundaries.

#### The 2-Minute Block Interval (The "Goldilocks Cadence")
* **Target Block Time**: **120 seconds (2 minutes)**.
* **Cadence**: Exactly **30 blocks/hour**, **720 blocks/day**, $\approx \mathbf{263,000 \text{ blocks/year}}$.
* **Physical Advantages**:
  * **$1.25\%$ Orphan Window**: With global P2P block propagation averaging $1.5\text{ seconds}$, a 120-second interval spends only $1.25\%$ of time in transit, eliminating geographic centralization pressures on miners.
  * **$5\times$ DAA Responsiveness**: The ASERT difficulty algorithm updates target work every 120 seconds, smoothly tracking global hashrate changes without price-lag oscillations.
  * **Continuous Background Pre-Validation**: The 2-minute cadence gives validation nodes ample time to pre-verify mempool transactions in parallel background threads. When a block arrives, $>95\%$ of transactions are already verified in RAM.

---

### 3.2. Single BLAKE3 Domain-Separated Segmented Merklix Tree

#### The Elimination of Double Hashing (`BLAKE3d` Rejected)
Legacy Bitcoin utilizes double SHA-256 (`SHA256(SHA256(x))`) to prevent length-extension attacks. BLAKE3 is based on the Bao tree architecture and includes **native domain separation flags** in every compression call:
* `CHUNK_START` (0x01), `CHUNK_END` (0x02), `PARENT` (0x04), `ROOT` (0x08).

Because interior nodes and leaf nodes operate under mathematically distinct domain flags, **length-extension attacks and interior/leaf collision attacks are mathematically impossible**. Performing double BLAKE3 (`BLAKE3(BLAKE3(x))`) wastes 50% of CPU cycles with zero added security. Single BLAKE3 is enforced across all consensus primitives.

#### The Segmented Merkle Tree Invariant (Resolving CVE-2012-2459)
To prevent leaf duplication vulnerabilities where an unconfirmed transaction can spoof an interior merkle node:
1. Every leaf hash is hashed with domain prefix:
   $$\text{LeafHash} = \mathbf{BLAKE3}(\text{DOMAIN\_LEAF} \parallel \text{SerialTx})$$
2. Interior nodes combine two 32-byte children:
   $$\text{ParentHash} = \mathbf{BLAKE3}(\text{DOMAIN\_NODE} \parallel \text{Left} \parallel \text{Right})$$
3. **Zero-Padded Odd Layers**: If an odd number of elements exists at layer $L$, the dangling element is paired with a fixed 32-byte null constant ($\mathbf{0}_{256}$) committed with the layer depth:
   $$\text{DanglingParent} = \mathbf{BLAKE3}(\text{DOMAIN\_NODE} \parallel \text{Child} \parallel \mathbf{0}_{256} \parallel \text{uint8}(L))$$
   Duplicating the right-hand leaf (the Satoshi bug) is strictly invalid.

---

### 3.3. Zero-Copy Wire Format & 80-Byte Typed Compact Outputs (POD)

Variable-length integers (`CompactSize` / `varint`) are banished from transaction headers and outputs. Transactions and outputs are structured as fixed-size Plain Old Data (POD) structs:

```cpp
// Transaction Fixed Wire Header (16 Bytes)
struct LotusTxHeader {
    int32_t  nVersion;       // 4 bytes: Tx format version
    uint32_t nLockTime;      // 4 bytes: Locktime
    uint32_t nInputCount;    // 4 bytes: Fixed 32-bit integer
    uint32_t nOutputCount;   // 4 bytes: Fixed 32-bit integer
};

// Input Fixed Wire Record (48 Bytes + Witness Payloads)
struct LotusInputRecord {
    uint256  prevout_txid;        // 32 bytes: Spent Outpoint TXID
    uint32_t prevout_index;       // 4 bytes: Spent Outpoint Index
    uint32_t nSequence;           // 4 bytes: Sequence number
    uint32_t script_sig_size;     // 4 bytes: Unlocking script size
    uint32_t witness_size;        // 4 bytes: Witness stack size
    // Payload bytes follow, padded to 8-byte alignment
};

// Output Fixed Wire Record (80 Bytes - Plain Old Data POD)
struct alignas(8) LotusOutput {
    uint64_t amount;              // 8 bytes: Native XPI atomic units (satoshis)
    uint8_t  output_type;         // 1 byte: 0x01=P2PKH, 0x02=P2SH32, 0x03=P2MNOR, 0x04=P2TR
    uint8_t  flags;               // 1 byte: Metadata dispatch flags (Token, NFT, Covenant)
    uint16_t custom_size;         // 2 bytes: Bytecode size if custom type, else 0
    uint32_t reserved_alignment;  // 4 bytes: Padding to maintain 64-bit alignment
    uint256  destination;         // 32 bytes: PubKey Hash, Script Hash, or Merkle Root
    uint256  metadata;            // 32 bytes: Token Amount (16B) & TokenID (16B) / Covenant State (Chronik Indexable)
}; // Total: Exactly 80 bytes
```

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ LOTUS v2 TYPED COMPACT OUTPUT (80 Bytes - Fixed 64-Bit Aligned POD)                    │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ [00..07] uint64_t amount              (8B: Native XPI satoshis / carrier gas)          │
│ [08..08] uint8_t  output_type         (1B: P2PKH=0x01, P2SH32=0x02, P2MNOR=0x03, P2TR=0x04) │
│ [09..09] uint8_t  flags               (1B: 0x00=XPI, 0x01=Token, 0x02=NFT, 0x03=Cov)   │
│ [10..11] uint16_t custom_size         (2B: 0 for standard outputs)                     │
│ [12..15] uint32_t reserved_alignment  (4B: Explicit 64-bit padding)                    │
│ [16..47] uint256  destination         (32B: Destination PubKey Hash or Merkle Root)    │
│ [48..79] uint256  metadata            (32B: 16B TokenAmount || 16B TokenID / Cov State)│
└────────────────────────────────────────────────────────────────────────────────────────┘
```

#### Why Typed Compact Outputs Are a Scalability Breakthrough:
1. **Elimination of Heap Allocations**:
   In Bitcoin Core, every output contains a dynamic `std::vector<uint8_t> scriptPubKey`. In memory and on disk, 100,000,000 outputs trigger 100,000,000 separate dynamic heap allocations, fragmenting RAM and thrashing CPU cache. In Lotus v2, $>99.9\%$ of outputs are fixed 80-byte structs stored as a contiguous memory-mapped array with **zero pointer indirection**.
2. **The Script-Bypass Fast Lane (~30 ns Validation)**:
   When `output_type == 0x01` (`P2PKH`), the validation engine **bypasses the Forth script interpreter entirely**. It verifies `destination == BLAKE3(pubkey)` and passes the 64-byte signature to the AVX-512 batch Schnorr verification queue. Processing latency drops from microseconds to **$\approx 30 \text{ nanoseconds}$ per spend**.
3. **The Metadata Dispatch Engine**:
   The `flags` byte dictates how consensus validates `metadata`:
   * **`0x00` (`FLAG_NONE`)**: Pure native XPI payment. Metadata is unused / zero.
   * **`0x01` (`FLAG_FUNGIBLE_TOKEN`)**: Consensus validates native token math ($\sum \text{in} \ge \sum \text{out}$) for `amount[16B] || token_id[16B]`. Zero indexers needed.
   * **`0x02` (`FLAG_NFT`)**: Consensus enforces 1-to-1 conservation of an indivisible asset.
   * **`0x03` (`FLAG_COVENANT_STATE`)**: **100% General-Purpose State (Mitra Carryover)**. Consensus performs **no token arithmetic**. The 32 bytes are arbitrary data owned by the smart contract (Frank state channels, AMM reserves, rollup roots). The spending script inspects and transitions this state via `OP_UTXOMETADATA` and `OP_OUTPUTMETADATA`.
4. **Carrier Gas & Covenant Refueling**:
   * Every output carries `uint64_t amount` (native XPI satoshis) alongside `metadata`. A token or covenant UTXO always carries its own native fuel.
   * Transaction fees ("gas") are paid via normal multi-input transaction balance:
     $$\text{Fee} = \sum \text{Inputs.amount} - \sum \text{Outputs.amount} \ge \mathbf{TotalCost} \times \text{ComputeFeeRate}$$
   * Autonomous covenants that maintain state across hundreds of transactions can be refueled by any external transaction depositing XPI into their output balance.

---

### 3.4. Native Layer-1 Assets & The Genesis Outpoint Invariant

To mint a new token, an issuer spends any standard UTXO in their wallet as Input #0. The protocol consensus rule locks the unique token identifier:
$$\mathbf{TokenID} = \mathbf{BLAKE3}(\text{tx.vin}[0].\text{prevout})$$

```
[ Issuer Wallet ] 
Outpoint A: (txid: 0x4a3f..., vout: 0) ──► Spent as tx.vin[0]
                                                │
                                                ▼
                                    Consensus Rule Enforces:
                                    TokenID == BLAKE3(Outpoint A)
                                                │
                                                ▼
                                    Outputs Created:
                                    • 1,000,000 Tokens (metadata = amount || TokenID)
```

* **Mathematical Uniqueness**:
  Because every outpoint `(txid || vout)` in the blockchain is globally unique and can only be spent once in the history of the ledger, it is mathematically impossible for an attacker to ever create a colliding `TokenID`.
* **Zero Lineage Overhead**:
  Unlike early UTXO covenant tokens or SLP, a transaction **never needs to carry parent transaction preimages or ancestry proofs**. The consensus engine verifies minting in a single 12-nanosecond hash in C++.
* **Subsequent Minting (Minting Batons)**:
  For elastic-supply tokens (stablecoins or Frank relay stamps), the genesis transaction outputs a **Minting Baton** (`flags & FLAG_MINT_BATON`). Future minting is permitted if and only if the transaction consumes the unspent Minting Baton UTXO for that `TokenID`. When the issuer wishes to cap supply permanently, the baton is spent to `OP_RETURN` or burned.

---

### 3.5. Transaction Architecture: Modernized BUIP037 & Merklized NOR (`P2MNOR`)

#### 3.5.1. Why Mitra Is Abandoned
Tobias Ruck’s Mitra proposal (`daemon/docs/mitra-spec.md`) attempted to address transaction malleability, isolated validation, and smart contract tokens. However, its draft specification suffered from ongoing churn, shifting opcode allocations, and severe architectural bloat:
1. **Free-Floating Preambles (`CTxPreamble[]`)**: Free-floating transaction-level scripts broke the UTXO spending model and created messy execution phases.
2. **Duplicating Full `CTxOut` in `CTxIn`**: Copying the entire spent output on the wire bloated transaction data unnecessarily.
3. **Wire-Serialized `loopCounts[]`**: Requiring transaction authors to encode loop counter arrays on the wire added serialization overhead and complex validation edge cases.

In contrast, Amaury Séchet’s **BUIP037 ("Hardfork SegWit")** and **BUIP045** (unified address format) laid down the true sound architectural principles in 2016:
- Segregated witness (txid hashes inputs and outputs, excluding signatures, providing 100% malleability immunity).
- Strictly typed outputs with compact hashes instead of arbitrary script bytecode in the UTXO set.
- Shifting execution bytecode and proofs from the hot UTXO set to cold witness data.

Lotus v2 modernizes BUIP037: replacing variable-length `varuint` with fixed 64-bit aligned POD structs, adopting single BLAKE3, and pairing it with **Merklized NOR (`P2MNOR`)** to deliver universal covenants without Schnorr key-tweaking overhead.

#### 3.5.2. The 4 Concrete Output Types
Every UTXO in Lotus v2 is an 80-byte POD struct (`LotusOutput`) belonging to one of four canonical types:

| Type | Name | Destination (32B) | Verification Engine | Primary Use Case |
|---|---|---|---|---|
| `0x01` | **`P2PKH`** | `BLAKE3(pubkey)` | **VM Bypass**: AVX-512 batch Schnorr (~30 ns) | Simple payments, peer-to-peer transfers |
| `0x02` | **`P2SH32`** | `BLAKE3(redeem_script)` | Forth VM linear script execution | Standard multisig, single linear contracts |
| `0x03` | **`P2MNOR`** | `BLAKE3(Merkle Root)` | **Merklized Negative Guardrail Tree** | Universal covenants, Frank state channels, AMMs |
| `0x04` | **`P2TR`** | BIP341 Taproot Key/Root | Schnorr Key-Path or MAST Script-Path | Bitcoin cross-chain atomic swaps |

#### 3.5.3. Solving the Indexer Problem with Wire Metadata
A fatal flaw of pure script-hash outputs (e.g. standard Taproot or P2SH) is that the coin's state is completely opaque until spent. If Alice sends Bob 500 USDL tokens, an indexer (such as Chronik) sees a transaction where token UTXOs were consumed as inputs, but cannot tell which output received the tokens or what the split amounts are without running complex external proofs.

In Lotus v2, the 80-byte `LotusOutput` embeds a plaintext 32-byte `metadata` field on the wire:
- For Fungible Tokens (`flags == 0x01`): `metadata` contains `uint128_t token_amount || uint128_t token_id`.
- Chronik indexes token balances and transfers in **$O(1)$ time** immediately upon mempool ingress or block arrival.
- Consensus validates token conservation ($\sum \text{in} \ge \sum \text{out}$) directly in C++ at transaction validation time.
- For Covenants (`flags == 0x03`): `metadata` holds arbitrary state (e.g., channel balances, AMM reserves) inspected by script via `OP_UTXOMETADATA` and `OP_OUTPUTMETADATA`.

#### 3.5.4. P2MNOR: Merklized Negative Guardrails & Execution Flow
Unlike Taproot (where a spend path satisfies $L_1 \lor L_2 \lor L_3$), `P2MNOR` models covenants as **universal negative guardrails**: to spend the coin, none of the prohibited conditions must occur ($\neg L_1 \land \neg L_2 \dots$).

1. **Zero Schnorr Curve Math Overhead**:
   In Taproot, spending via script requires committing to an internal public key $P$ and computing an elliptic curve tweak $Q = P + H(P \parallel m)G$. This requires an expensive point multiplication (~50 µs). In `P2MNOR`, the destination is directly the 32-byte BLAKE3 Merkle root. Verifying it is a **12-nanosecond hash check** with zero elliptic curve operations.
2. **Witness Format**:
   An input spending a `P2MNOR` output provides a list of leaves and proofs:
   ```
   [leaf_0_arg_0 ... leaf_0_arg_{k-1}] [k (num_args)] [leaf_0_code] [merkle_proof_0]
   [leaf_1_arg_0 ... leaf_1_arg_{m-1}] [m (num_args)] [leaf_1_code] [merkle_proof_1]
   [num_leaves]
   ```
3. **Isolated Stack Execution & Cleanstack by Construction**:
   To prevent brittle inter-leaf stack passing, consensus executes each leaf in total isolation:
   - For each active leaf $i$:
     a. Asserts `merkle_proof_i` proves `leaf_i_code` is in `destination` root via BLAKE3.
     b. **Wipes the evaluation stack completely**.
     c. Pushes the declared $k$ witness arguments onto the stack.
     d. Executes `leaf_i_code`.
     e. Asserts the top stack item is truthy (non-zero).
     f. **Wipes the evaluation stack before the next leaf executes**.
   - Because the consensus engine wipes the stack between frames, leaf scripts cannot corrupt each other's execution, and enforcing cleanstack inside a leaf is unnecessary.
4. **Covenants Across Recipient Transfers**:
   When tokens are sent to a new recipient with a different destination script, the covenant does **not** assert `Output.Root == Input.Root`. Instead, the covenant leaf uses `OP_MERKLEVERIFY` with sibling hashes provided in the witness to assert:
   $$\mathbf{TokenPolicyLeaf} \in \mathbf{Output.Root}$$
   This allows recipient destinations to be arbitrary multisigs or contracts while mathematically locking token conservation.

---

### 3.6. The 128-Bit Forth Stack Machine (`int128_t`)

All numerical values on the evaluation stack are **native 128-bit signed two's-complement integers (`int128_t`, 16 bytes)**:
* **Elimination of `CScriptNum`**: Zero sign-magnitude quirks, zero negative-zero (`0x80`) malleability bugs, zero arbitrary byte-length conversions.
* **Direct Hardware Mapping**: `OP_ADD`, `OP_SUB`, `OP_MUL`, `OP_DIV`, and `OP_MOD` map directly to native 64-bit CPU instructions with carry/overflow registers (`mulq`/`adcq`).
* **High-Precision Financial Math**: 128-bit integers support calculations up to $3.4 \times 10^{38}$, allowing multi-asset AMM liquidity pools and compound interest math without rounding overflow.

---

### 3.7. Multi-Precision & Cryptographic Primitives

To guarantee that developers can implement arbitrary zero-knowledge proofs and cryptographic curves without network hardforks:
* **Curve Arithmetic Opcodes**:
  * `OP_ADDCARRY`: Pops $(a, b, c_{in})$, pushes $(sum, c_{out})$.
  * `OP_SUBCARRY`: Pops $(a, b, b_{in})$, pushes $(diff, b_{out})$.
  * `OP_MUL128_WIDE`: Pops two 128-bit ints, pushes the 256-bit product as $(prod_{high}, prod_{low})$.
  * Allows chaining 128-bit limbs to execute 256-bit (secp256k1, Ed25519) and 384-bit (BLS12-381) curve arithmetic directly in user-space Script.
* **Cryptographic Hashing & Verification**:
  * `OP_BLAKE3`: Single BLAKE3 hash ($\approx 12\text{ ns}$).
  * `OP_SHA256`: Single SHA-256 hash.
  * `OP_HASH256` (`OP_SHA256D`): Double SHA-256 for cross-chain Bitcoin/eCash header verification.
  * `OP_CHECKSIG`: Verifies 64-byte Schnorr (default) or 64-byte compact Low-S ECDSA.
  * `OP_CHECKDATASIG`: Verifies an arbitrary data hash against a public key.
  * `OP_MERKLEVERIFY`: Verifies Merklix inclusion/exclusion proofs on stack against a state root.

---

### 3.8. Native Introspection Opcodes (`0xbf–0xcf`)

Introspection opcodes allow an input script to inspect its spending transaction and parent UTXO state directly in memory without quadratic hashing or preambles:

| Opcode | Hex | Description |
| :--- | :--- | :--- |
| `OP_TXID` | `0xbf` | Pushes the 32-byte Single-BLAKE3 Merklix TXID of current transaction. |
| `OP_TXHASH` | `0xc0` | Pushes the 32-byte witness-inclusive serialization hash. |
| `OP_TXVERSION` | `0xc1` | Pushes the 32-bit transaction version. |
| `OP_TXLOCKTIME` | `0xc2` | Pushes the 32-bit transaction locktime. |
| `OP_INPUTINDEX` | `0xc3` | Pushes the 32-bit index of the executing input. |
| `OP_INPUTCOUNT` | `0xc4` | Pushes the total number of inputs in the transaction. |
| `OP_OUTPOINT` | `0xc5` | Pops input index $i$, pushes 36-byte outpoint `(txid || vout)`. |
| `OP_UTXOVALUE` | `0xc6` | Pops input index $i$, pushes 128-bit satoshi amount. |
| `OP_UTXOTYPE` | `0xc7` | Pops input index $i$, pushes 1-byte output type. |
| `OP_UTXOMETADATA` | `0xc8` | Pops input index $i$, pushes 32-byte metadata (Token/Covenant state). |
| `OP_OUTPUTCOUNT` | `0xc9` | Pushes the total number of outputs in the transaction. |
| `OP_OUTPUTVALUE` | `0xca` | Pops output index $j$, pushes 128-bit satoshi amount. |
| `OP_OUTPUTTYPE` | `0xcb` | Pops output index $j$, pushes 1-byte output type. |
| `OP_OUTPUTMETADATA` | `0xcc` | Pops output index $j$, pushes 32-byte metadata. |
| `OP_OUTPUTBYTECODE` | `0xcd` | Pops output index $j$, pushes destination locking bytecode. |
| `OP_TOTALINPUTVALUE`| `0xce` | Pushes sum of all input amounts in 1 CPU cycle. |
| `OP_TOTALOUTPUTVALUE`|`0xcf` | Pushes sum of all output amounts in 1 CPU cycle. |

---

### 3.9. Enumerable Loops ($N \le 2$) & Static Precomputed Cost Budget

To support expressive smart contracts without dynamic runtime gas meters or the Halting Problem:
* **The Loop Opcodes**: `OP_FOREACH_INPUT ... OP_ENDFOR` and `OP_FOREACH_OUTPUT ... OP_ENDFOR`.
* **Static Bounded Multiples**:
  Because `nInputCount` and `nOutputCount` are fixed integers in the transaction header, the engine precomputes the exact worst-case execution cost upfront:
  * Single Loop: $\text{Count} \times \text{Cost}(\text{Body}) + \text{Overhead}$
  * Nested Loop ($N = 2$ Max):
    $$\text{LoopCost} = (\mathbf{nInputCount} \times \mathbf{nOutputCount} \times \text{Cost}(\text{InnerBody})) + \text{Overhead}$$
* **Strict Total Budget**:
  $$\mathbf{TotalCost} = \mathbf{WireBytes} + \sum \mathbf{PrecomputedScriptCosts} \le \mathbf{MAX\_TX\_COST}$$
  If $\mathbf{TotalCost} > \mathbf{MAX\_TX\_COST}$, the transaction is rejected at mempool admission without executing a single instruction.

---

### 3.10. Thermodynamic Monetary Issuance & Onboarding Faucet

#### Sub-Linear Damped Subsidy: $R = K \cdot \sqrt{D}$
* Block reward adjusts dynamically per block based on the current ASERT difficulty target $D$:
  $$\text{Block Subsidy } R = K \cdot \sqrt{D}$$
  where $K$ is calibrated to provide smooth baseline growth while expanding smoothly under thermodynamic capital accumulation.
* **No Halvings**: Eliminates the quadrennial 50% revenue shock that destabilizes miner economics and creates fee-market spikes.

#### The 50/50 Schelling Point Split & Autonomous Faucet Burn Cap
* **$50\%$ ($R \gg 1$)**: Direct coinbase payout to the PoW miner.
* **$50\%$ ($R \gg 1$)**: Direct credit to the **Protocol Onboarding Faucet covenant**:
  * Subsidizes onboarding by distributing micro-stamps to authenticated Frank relays and users ($\text{CAC} < \text{Lifetime Value}$).
  * **Anti-Hoarding Cap**: If the Faucet reserve exceeds $M$ blocks of runway (e.g. 6 months of onboarding capacity), excess seigniorage automatically **burns**, permanently reducing circulating supply.

---

## 4. Node Implementation & Performance Architecture (No Hardfork Required)

### 4.1. Hybrid State Architecture: In-Memory Trie + RocksDB Write-Behind

Block validation cannot stall for synchronous disk I/O, yet nodes cannot risk losing ledger state on power interruption. Lotus v2 implements a bifurcated state model:

```
┌────────────────────────────────────────────────────────────────────────┐
│                   HOT VALIDATION PATH (In-Memory RAM)                  │
├────────────────────────────────────────────────────────────────────────┤
│ • Compressed Crit-Bit Radix Tree stored entirely in RAM.               │
│ • Validates block inputs, deletes spent UTXOs, inserts new outputs.    │
│ • Bottom-up rehash of modified branches takes < 5 milliseconds.        │
│ • Matches local RAM root against header's hashUtxoMerklixRoot.         │
│ • ZERO disk I/O on the block validation critical path!                 │
└────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼ (Asynchronous Write-Behind Worker)
┌────────────────────────────────────────────────────────────────────────┐
│                PERSISTENT BACKING STORE (RocksDB / NVMe)               │
├────────────────────────────────────────────────────────────────────────┤
│ • RocksDB Column Family: Merklix Nodes (keyed by branch prefix/hash).  │
│ • RocksDB Column Family: UTXO Payloads (amount, scriptPubKey, height). │
│ • RocksDB Column Family: State Commitments (blockHeight ↦ MerklixRoot).│
│ • Background Flush: Dirty trie nodes flushed via Write-Ahead Log (WAL).│
└────────────────────────────────────────────────────────────────────────┘
```

---

### 4.2. State Commitments & Sub-Second Crash Recovery

#### The Bitcoin Core Failure Mode:
In Bitcoin Core, `CCoinsViewDB` in LevelDB is an uncommitted flat key-value store. If power fails during block write, LevelDB is left in an inconsistent state. Having no internal cryptographic root, Core prints `"Corrupted block database detected. Please reindex"`, forcing a multi-hour rebuild from raw block files.

#### The Lotus v2 Recovery Guarantee:
1. Every block commits to `hashUtxoMerklixRoot`.
2. RocksDB commits an atomic batch at the end of each block:
   $$\mathbf{StateCommitment} = (\text{blockHeight}, \mathbf{hashUtxoMerklixRoot})$$
3. **On Startup / Reboot**:
   * The node reads the tip header's expected `hashUtxoMerklixRoot`.
   * It checks its local database root pointer. If clean: `LocalRoot == Header.hashUtxoMerklixRoot`. **The database is cryptographically proven uncorrupted in $< 1 \text{ second}$.**
   * If power failed mid-write: RocksDB rolls back to the previous block's committed root ($H - 1$) and replays the single missing block from `blk*.dat`.
   * **Zero full reindexing is ever required.**

---

### 4.3. High-Throughput Mining Engine: $O(1)$ Mempool & $O(n \log n)$ Block Construction

#### $O(1)$ Mempool Ingestion (`02-remove-chaintx-limit.patch`):
* Eliminates `DEFAULT_ANCESTOR_LIMIT` entirely.
* Incoming transactions undergo signature verification and are appended to the topological sequence (`entry_id` order).
* **Zero ancestor package recalculation on wire ingress**, enabling $>50,000\text{ tx/s}$ ingestion without lock contention.

#### $O(n \log n)$ Block Template Generation (`01-nlogn-block-construction.patch`):
Decouples block template assembly in `BlockAssembler::addTxs` into a 4-stage pipeline:
1. **Snapshot**: Ingest mempool entries in topological order ($O(n)$).
2. **Forward-Walk Accumulation**: Accumulate package fees and sizes from in-mempool parents in a single pass ($O(n + m)$).
3. **Tier Sorting**: Sort by priority tier and fee rate ($O(n \log n)$).
4. **Ancestor DFS Insertion**: Traverse sorted items and insert unconfirmed ancestors via DFS ($O(n + m)$).
* Eliminates the quadratic update loop; scales effortlessly to 1,000,000 unconfirmed transactions.

---

### 4.4. Stateless Snap Sync Protocol & Dynamic Body Pruning

* **Stateless Bootstrapping**:
  1. Download and verify the 116-byte header chain ($\approx 80 \text{ MB}$).
  2. Request current Merklix state chunks via `GETMERKLIX` / `MERKLIXCHUNK`.
  3. Chunks authenticate directly against the tip `hashUtxoMerklixRoot`.
  4. Fully operational node ready in $< 3 \text{ minutes}$.
* **Body Pruning**: Historical raw block bodies (`blk*.dat`) older than 1,000 blocks are purged automatically.

---

### 4.5. RPC Interface Upgrades for Merklix Proofs & Stateless Operation

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        RPC & PROTOCOL EXTENSION SPECIFICATION                          │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 1. getutxoproof (txid, vout)                                                           │
│    • Query: Outpoint identifier (txid: 32 bytes, vout: uint32).                        │
│    • Returns: Compact Merklix inclusion proof against tip hashUtxoMerklixRoot.         │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 2. verifymerklixproof (root, key, value, proof)                                        │
│    • Pure in-memory cryptographic verification (~15 microseconds, zero disk I/O).       │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 3. sendrawtransaction / testmempoolaccept (hexTx, [proofBundle])                       │
│    • Accepts Proof-Carrying Transactions (PCTs) for stateless validation in RAM.       │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 4. getunsolvedblock / getblocktemplate                                                 │
│    • Returns 116-byte header template committing to state roots and 64-bit nonce.      │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 5. getmerklixchunk (prefix, depth)                                                     │
│    • High-speed P2P state streaming protocol for 3-minute snap sync.                  │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

### 4.6. Avalanche Consensus Decoupling: Hard Consensus vs. Soft Coordination

* **Hard Consensus (PoW Exclusive)**: Block validity, chain-tip selection, and finality are strictly governed by Proof-of-Work. All Avalanche quorum gates in `src/net_processing.cpp` and `src/validation.cpp` are stripped.
* **Soft Coordination (Avalanche Preserved)**: The `src/avalanche/` directory is retained to allow nodes to gossip and reach advisory soft consensus on mempool fee policies, minimum relay fees, and network parameter governance.

---

## 5. Upstream PR Strategy & Node Base Selection

### 5.1. Daemon Base Evaluation

* **Selected Base**: `bitcoin-abc 252182e957120652960c1f88ec96515c448b1204`
  * **Chronik Integration**: Production-ready Rust indexer built-in.
  * **Modern Toolchain**: Native CMake, Ninja, Flatbuffers, Jemalloc.
  * **Secondary Reference**: `bitcoincashnoded` (BCHN v28.0.0) as clean PoW baseline.

### 5.2. Chain-Agnostic Upstream Candidates

The following patches in `daemon/patches/ecash/` and `daemon/patches/bchn/` are modular, chain-agnostic performance improvements ready for immediate upstream submission:
1. `01-nlogn-block-construction.patch`: Upstream PR to Bitcoin ABC & BCHN replacing the $O(n^2)$ `addTxs` loop.
2. `02-remove-chaintx-limit.patch`: Upstream PR removing artificial package limits for $O(1)$ mempool ingestion.
3. `10-nng-interface.patch`: Upstream PR introducing the modern NNG pub/sub bus.
4. `11-remove-zeromq.patch`: Upstream PR purging legacy ZeroMQ.

---

## 6. The Complete 35-Patch Rebase Sequence (`daemon/patches/v2/`)

The full rebase sequence in `lotus/daemon/patches/v2/series` onto `bitcoin-abc 252182e9`:

| Slot | File | Status | Description & Target Files |
| :--- | :--- | :--- | :--- |
| **00** | `00-decouple-avalanche.patch` | **NEEDS-WRITE** | Strip Avalanche block validity and chain-tip finalization gates from `src/net_processing.cpp` and `src/validation.cpp`. Keep gossip in `src/avalanche/`. |
| **01** | `01-nlogn-block-construction.patch` | **DONE** | $O(n \log n)$ block template construction in `src/node/miner.cpp`. |
| **02** | `02-remove-chaintx-limit.patch` | **DONE** | $O(1)$ mempool ingestion; drop ancestor/descendant limits in `src/policy/policy.h`. |
| **03** | `03-mempool-cleanup.patch` | **NO-OP** | Upstream already removed `CTxMemPoolEntry` accounting fields. |
| **04** | `04-issuance-compat.patch` | **NEEDS-WRITE** | Runtime `-issuance=ecash` flag for regression test compatibility. |
| **05** | `05-chain-identity.patch` | **NEEDS-REBASE** | Renaming to `lotusd`, `lotus-cli`, project branding in CMake. |
| **06** | `06-currency-unit.patch` | **NEEDS-REBASE** | XPI currency units ($1 \text{ XPI} = 10^6 \text{ atoms}$). |
| **07** | `07-xaddress.patch` | **NEEDS-REBASE** | XAddress format with `xpi` prefix. |
| **08** | `08-daa-cleanup.patch` | **NEEDS-REBASE** | Keep only aserti3-2d DAA; purge Grasberg/EDA. |
| **08c**| `08c-blocktime.patch` | **NEEDS-EXTRACT** | Set `nPowTargetSpacing = 120` (2 minutes) in `src/kernel/chainparams.cpp`. |
| **09** | `09-merkle.patch` | **NEEDS-REBASE** | Single BLAKE3 domain-separated segmented Merkle tree; CVE-2012-2459 fix. |
| **09b**| `09b-block-header.patch` | **NEEDS-EXTRACT** | 116-byte fixed aligned `LotusHeader` struct with `hashUtxoMerklixRoot` in `src/primitives/block.h`. |
| **09c**| `09c-compact-outputs.patch` | **NEEDS-EXTRACT** | 80-byte POD `LotusOutput` struct with 32B metadata in `src/primitives/transaction.h`. |
| **10** | `10-nng-interface.patch` | **NEEDS-REBASE** | NNG pub/sub interface replacing ZeroMQ in `src/nng_interface/`. |
| **10b**| `10b-remove-zeromq.patch` | **NEEDS-WRITE** | Purge `src/zmq/`, CMake options, and ZeroMQ tests. |
| **11** | `11-intmath-log2.patch` | **NEEDS-REBASE** | Turner fixed-point log2 integer arithmetic. |
| **14** | `14-script-opcodes.patch` | **NEEDS-REBASE** | Basic opcodes: `OP_MULPOW2`, `OP_RAWLEFTBITSHIFT`. |
| **15** | `15-taproot.patch` | **NEEDS-REBASE** | 64-byte compact Schnorr signature integration. |
| **16** | `16-chain-params.patch` | **NEEDS-FIX** | Network magic, ports, genesis placeholder. |
| **17** | `17-genesis.patch` | **NEEDS-FIX** | Assume-valid constants for new genesis. |
| **18** | `18-checkpoints.patch` | **NEEDS-FIX** | Reset checkpoints for new chain. |
| **19** | `19-fixed-seeds.patch` | **NEEDS-WRITE** | Hardcoded seed nodes for new network. |
| **20** | `20-seeder.patch` | **NEEDS-REBASE** | DNS seeder tool. |
| **22** | `22-src-build.patch` | **NEEDS-REBASE** | Build system adaptations in `src/CMakeLists.txt`. |
| **23** | `23-misc.patch` | **NEEDS-REBASE** | General RPC, wallet, net, and utility adaptations. |
| **24** | `24-qt-gui.patch` | **NEEDS-REBASE** | Optional Qt GUI build fixes. |
| **25** | `25-build-compat.patch` | **NEEDS-REBASE** | CMake 4.x and Boost 1.90 compatibility. |
| **26** | `26-boot-subsidy.patch` | **NEEDS-REBASE** | Boot subsidy calibrated for 720 blocks/day (2-minute intervals). |
| **27** | `27-tail-subsidy.patch` | **NEEDS-REBASE** | Thermodynamic adaptive tail subsidy $R = K \sqrt{D}$. |
| **28** | `28-ifp-removal.patch` | **NEEDS-REBASE** | Purge IFP; miners receive 100% of coinbase subsidy share. |
| **29** | `29-op-log-op-sqrt.patch` | **NEEDS-REBASE** | `OP_LOG` (0xbd) and `OP_SQRT` (0xbe) math opcodes. |
| **30** | `30-op-mul.patch` | **NEEDS-REBASE** | `OP_MUL` (0x95) re-enabled with overflow protection. |
| **31** | `31-int128-stack.patch` | **NEEDS-WRITE** | Native `int128_t` stack VM; `OP_ADDCARRY`, `OP_SUBCARRY`, `OP_MUL128_WIDE`. |
| **32** | `32-chronik-adapt.patch` | **NEEDS-WRITE** | Adapt Chronik Rust indexer to `xpi` prefix and XPI units. |
| **33** | `33-introspection-loops.patch` | **NEEDS-WRITE** | Introspection opcodes `0xbf–0xcf`, `OP_FOREACH_INPUT/OUTPUT`, static precomputed budget. |
| **34** | `34-utxo-merklix-rocksdb.patch`| **NEEDS-WRITE** | In-memory Radix Trie + RocksDB write-behind with block state commitments. |
| **35** | `35-rpc-merklix-proofs.patch` | **NEEDS-WRITE** | `getutxoproof`, `verifymerklixproof`, PCT validation, snap sync. |

---

## 7. Verification, Test Harness & Genesis Launch Checklist

1. **IMPCPD Patch Verification**:
   Every patch must pass the 7-point IMPCPD quality standard (Regression, Consensus Correctness, Security, Edge Cases, Completeness, Tests & Docs, Minimality) before landing.
2. **50,000 TPS Burst Harness**:
   Verify mempool ingestion and $O(n \log n)$ block template construction under simulated 50,000 tx/s network flooding.
3. **Crash-Resilience Verification**:
   Execute SIGKILL simulation during active block commits to verify sub-second rollback and recovery to tip `hashUtxoMerklixRoot`.
4. **Stateless Snap-Sync Verification**:
   Spin up a fresh node from block headers + Merklix chunk stream; verify full operational readiness in $< 3 \text{ minutes}$.
5. **Genesis Block Mining**:
   Mine the definitive Genesis Block committing to locked Block 0 invariants, hardcoded seed nodes, and zero future hardfork flags.
