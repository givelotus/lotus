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
8. [Post-Genesis Evolution: Zero-Hardfork Enhancements](#8-post-genesis-evolution-zero-hardfork-enhancements)
   - [8.1. QUIC P2P Transport Layer](#81-quic-p2p-transport-layer-rfc-9000--http3-over-udp)
   - [8.2. Stateless Snap-Sync RPCs & P2P Merklix Chunk Streaming](#82-stateless-snap-sync-rpcs--p2p-merklix-chunk-streaming)
   - [8.3. Chronik Indexer API Adaptations & Real-Time WebSockets](#83-chronik-indexer-api-adaptations--real-time-websockets)
   - [8.4. Partially Signed Lotus Transactions (PSLT / BIP-0370)](#84-partially-signed-lotus-transactions-pslt--bip-0370-standard)
   - [8.5. Architectural Exclusion of Double-Spend Proofs (BUIP135)](#85-architectural-exclusion-of-double-spend-proofs-buip135)

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

### 3.3. Zero-Copy Wire Format, Inline Witnesses & Multi-Branch Structured Outputs

Variable-length integers (`CompactSize` / `varint`) are eliminated from transaction headers and fixed records. Crucially, the BIP-141 soft-fork hack of a decoupled, trailing `witness` vector is completely discarded. In Lotus v2, **witnesses map 1-to-1 directly inside `vin` and `vout`**.

```cpp
// Transaction Wire Header (16 Bytes)
struct LotusTxHeader {
    int32_t  nVersion;       // 4 bytes: Tx format version
    uint32_t nLockTime;      // 4 bytes: Locktime
    uint32_t nInputCount;    // 4 bytes: Fixed 32-bit integer
    uint32_t nOutputCount;   // 4 bytes: Fixed 32-bit integer
};

// Branch Witness (Carried inside each input, one per active branch)
struct BranchWitness {
    std::vector<uint8_t> script;              // Script preimage / covenant bytecode
    std::vector<std::vector<uint8_t>> stack;  // Unlocking parameters / signatures
};

// Input Record (Inline Branch Witnesses)
struct LotusInput {
    COutPoint prevout;                         // 32B txid + 4B index
    uint32_t  nSequence;                       // 4 bytes
    uint16_t  n_branch_witnesses;              // 2 bytes: Number of branch witnesses
    std::vector<BranchWitness> witnesses;      // Inline 1-to-1 branch witnesses
};

// Output Record (Inline Creation Witness & Optional Token Amount)
struct LotusOutput {
    uint64_t  amount;                          // 8 bytes: Native XPI satoshis (carrier gas)
    uint16_t  flags;                           // 2 bytes: Bitflags (FLAG_HAS_TOKEN, etc.)
    uint16_t  n_branches;                      // 2 bytes: Count of branch hashes (typically 1 or 2)
    uint128_t token_amount;                    // 16 bytes: ONLY serialized if (flags & FLAG_HAS_TOKEN)
    std::vector<uint256> branches;             // Array of 32B branch hashes [Owner, Covenant, ...]
    
    // Creation Witness: 0 bytes for standard transfers, populated ONLY when minting tokens
    std::vector<uint8_t> creation_script;
    std::vector<std::vector<uint8_t>> creation_args;
};
```

#### Wire Layout & Cache-Line Efficiency:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ PURE XPI STANDARD OUTPUT (44 Bytes - Fits in a SINGLE 64-Byte CPU Cache Line!)         │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ [00..07] uint64_t amount              (8B: Native XPI satoshis)                        │
│ [08..09] uint16_t flags               (2B: FLAG_HAS_TOKEN = 0)                         │
│ [10..11] uint16_t n_branches          (2B: 0x0001 = 1 branch)                          │
│ [12..43] uint256  branch[0]           (32B: Owner PubKeyHash / Destination)            │
└────────────────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────────────────┐
│ TOKEN / COVENANT OUTPUT (92 Bytes - Explicit Owner, Token Amount & Covenant)           │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ [00..07] uint64_t  amount             (8B: Native XPI carrier fuel)                    │
│ [08..09] uint16_t  flags              (2B: FLAG_HAS_TOKEN = 1)                         │
│ [10..11] uint16_t  n_branches         (2B: 0x0002 = 2 branches)                        │
│ [12..27] uint128_t token_amount       (16B: Native 128-bit token balance)              │
│ [28..59] uint256   branch[0]          (32B: Owner PubKeyHash)                          │
│ [60..91] uint256   branch[1]          (32B: Token Covenant / Policy Hash)              │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

#### Why Optional `token_amount` via Bitflag Beats Varints:
1. **Zero Bytes for Pure XPI**:
   For $>95\%$ of transactions (pure native XPI), `FLAG_HAS_TOKEN` is unset. `token_amount` is **omitted entirely from the wire (0 bytes)**. Standard outputs shrink to **44 bytes**, fitting inside a single 64-byte L1 CPU cache line.
2. **Zero-Cycle CPU Cost**:
   Instead of variable-length parsing branches, serialization uses a single bit-test:
   ```cpp
   if (__builtin_expect(flags & FLAG_HAS_TOKEN, 0)) {
       stream >> token_amount;
   } else {
       token_amount = 0;
   }
   ```
   The CPU branch predictor predicts pure XPI with $>99.9\%$ accuracy, executing in 0 clock cycles without CPU stalls. When tokens are present, 128-bit amounts load via a single 1-cycle SIMD instruction (`vmovdqu` / `ldr q0`).
3. **Malleability Immunity by Construction**:
   The **TXID** is defined as $\mathbf{BLAKE3}(\text{nVersion} \parallel \text{nLockTime} \parallel \text{inputs without witnesses} \parallel \text{outputs without creation\_witness})$. Third parties can never malleate the TXID.

---

### 3.4. Native Layer-1 Assets, Token Identity & Key Rotation

#### 3.4.1. The Immutable Identity Invariant
To prevent configuration changes from altering the token identity, `TokenID` is **never** the hash of mutable admin keys or reserve addresses. `TokenID` is permanently anchored to the Genesis Outpoint:
$$\mathbf{TokenID} = \mathbf{BLAKE3}(\text{tx.vin}[0].\text{prevout})$$

Because every outpoint `(txid:vout)` can only be spent once in the history of the ledger, `TokenID` is mathematically unique and immutable forever.

#### 3.4.2. Key Rotation Without TokenID Mutation
In production, reserve addresses change, keys are compromised, and corporate officers rotate. Lotus v2 decouples immutable `TokenID` from mutable configuration:
1. **The Admin Baton (On-Chain Governance Coin)**:
   The token creator maintains an Admin Baton UTXO governed by an $m$-of-$n$ corporate multisig (e.g. 3-of-5).
   - **Key Rotation**: When an employee leaves, the remaining officers spend the Admin Baton to a new Baton UTXO containing the updated key set and new reserve address. `TokenID` never changes.
   - **Contention-Free Ingestion**: Depositors include the Admin Baton as a **Read-Only Reference Input** (like Cardano CIP-31). Because depositors only *read* the baton rather than spending it, **10,000 users can read the Admin Baton simultaneously in the same block with zero double-spend collisions**.
2. **Epoch Delegation Certificates (`OP_CHECKDATASIG`)**:
   Alternatively, the $m$-of-$n$ admin keys sign an off-chain delegation certificate committing to the authorized reserve address for epoch $[H..H+\Delta]$. The depositor attaches this certificate to their witness, and the token script validates it via `OP_CHECKDATASIG`. Zero on-chain state contention.

#### 3.4.3. The Parallel Deposit Invariant (Zero State-UTXO Collisions)
To deposit into a token or staking contract (e.g. USDC $\rightarrow$ sUSDC), users **never spend a shared contract coin**. The deposit is an atomic local transaction invariant:
- **Inputs**: Alice's 500 USDC.
- **Outputs**:
  - `Vout[0]`: 500 USDC sent to `sUSDC_Reserve_Address`.
  - `Vout[1]`: 480 sUSDC minted to `Alice_Address` (with `creation_witness` proving the deposit).
- **Zero Lock Contention**: Alice only spends her own coins. 10,000 users can deposit in parallel across the exact same block with zero lock contention. Reserves are held in chunked UTXOs, enabling parallel withdrawals.

---

### 3.5. Multi-Branch Architecture & Elimination of Opaque Roots

#### 3.5.1. Why Opaque Merkle Roots Were Abandoned
Early covenant proposals (including Taproot MAST and single-root `P2MNOR`) hashed all spend conditions and recipient public keys into a single 32-byte opaque Merkle root. This created severe operational failures:
1. **The Blind Indexer Problem**: Chronik could not identify what token or contract an output belonged to until the coin was spent.
2. **The Blind Light-Wallet Problem**: Because the recipient's public key was hashed together with the covenant, Bob's address was blinded. Bob's wallet could not find his own coins without out-of-band communication or exhaustive witness graph tracing.

#### 3.5.2. Multi-Branch Direct Hashes
Lotus v2 replaces single opaque roots with an **explicit array of branch hashes** in the output struct:
$$\text{branches} = [ \mathbf{hash}_0, \mathbf{hash}_1, \dots \mathbf{hash}_{n-1} ]$$

- **`hash_0` (Owner)**: `BLAKE3(Bob_PubKey)`. Bob's wallet and Chronik index the recipient in $O(1)$ directly from the unspent output.
- **`hash_1` (Covenant / Token Policy)**: `BLAKE3(TokenCovenantScript)`. Chronik indexes the asset type and rules in $O(1)$ directly from the unspent output.
- **`hash_2` (Optional Guardrail / Emergency Recovery)**: E.g., timelock or recovery key.

#### 3.5.3. Multi-Branch Execution & The NOR-Tree
When spending an output with $n$ branches, the input provides an array of branch witnesses: `vin[i].witnesses[k]`.
Consensus verifies:
1. $\mathbf{BLAKE3}(\text{witnesses}[k].\text{script}) == \text{branches}[k]$ for all active branches.
2. Executes each branch script in an **isolated evaluation stack frame** (executed in parallel across CPU cores).
3. Evaluates branch results across a deterministic **NOR-Tree**:
   $$\text{Root} = (n_0 \bar{\lor} n_1) \;\bar{\lor}\; (n_2 \bar{\lor} n_3)$$
   Using static scripts (`OP_TRUE` / `OP_FALSE`) in branch slots, arbitrary boolean logic like $(\text{Owner} \land \text{Covenant}) \lor \text{Recovery}$ is expressed directly on the wire with zero hidden Merkle trees.

#### 3.5.4. Composable Asset Invariants
Covenants must never hardcode output indices (e.g. "Output 0 must be my change"). Instead, composable covenants enforce **Asset Invariants**:
- The `USDC_Covenant` only asserts that the subset of inputs carrying USDC balances equals the subset of outputs carrying USDC balances ($\sum \text{in}[USDC] == \sum \text{out}[USDC]$), and all USDC outputs preserve `USDC_Covenant`.
- It ignores unrelated inputs and outputs (such as XPI or sUSDC), allowing multiple covenants, AMMs, and staking vaults to compose seamlessly in the exact same transaction.

---

### 3.6. The 128-Bit Forth Stack Machine (`int128_t`)

All numerical values on the evaluation stack are **native 128-bit signed two's-complement integers (`int128_t` / `__int128_t`, 16 bytes)**:
* **Elimination of `CScriptNum`**:
  * Legacy Bitcoin stored integers as variable-length sign-magnitude byte arrays (1 to 4 bytes, later expanded to 8 bytes with quirky rules). This introduced sign-magnitude ambiguity, negative-zero (`0x80`) malleability bugs, and endianness mismatch.
  * In Lotus v2, numbers on the stack are fixed 16-byte signed two's-complement integers. Zero sign-magnitude quirks, zero negative-zero bugs, zero variable-byte allocations.
* **Direct Hardware Instruction Mapping**:
  * On modern 64-bit architectures (x86-64 and ARM64), operations on `int128_t` map directly to pairs of native CPU instructions using carry/overflow flags (`adcq`, `sbbq`, `mulq`, `umulh`).
  * `OP_ADD`, `OP_SUB`, `OP_MUL`, `OP_DIV`, `OP_MOD`, `OP_NEGATE`, `OP_ABS` execute in nanoseconds without arbitrary-precision heap overhead.
* **High-Precision Financial Math & Scale**:
  * 128-bit signed integers support values up to $\pm 1.7 \times 10^{38}$ ($\pm 2^{127}-1$).
  * Fully accommodates multi-asset automated market makers (AMMs), constant-product formulas ($x \cdot y = k$), loan collateralization ratios, and high-frequency compound interest without intermediate truncation or integer overflow.

---

### 3.7. Multi-Precision Math & Cryptographic Primitives

To empower smart contracts to compute arbitrary zero-knowledge proofs and cryptographic curves without requiring network hardforks:

#### 3.7.1. Integer & Curve Arithmetic Opcodes
* `OP_MUL` (`0x95`): 128-bit signed multiplication with explicit overflow checking.
* `OP_RAWLEFTBITSHIFT` (`0x98`): Raw bitshift on byte vectors. A positive shift count shifts left; a negative shift count shifts right!
* `OP_MULPOW2` (`0x99`): Computes arithmetic power-of-two scaling ($x \cdot 2^k$ for $k > 0$, or $x / 2^{|k|}$ for $k < 0$).
* `OP_ADDCARRY` (`0xb4`): Multi-precision add with carry. Pops $(a, b, c_{in})$, pushes $(sum, c_{out})$ where $c_{out} \in \{0, 1\}$.
* `OP_SUBCARRY` (`0xb5`): Multi-precision subtract with borrow. Pops $(a, b, b_{in})$, pushes $(diff, b_{out})$ where $b_{out} \in \{0, 1\}$.
* `OP_MUL128_WIDE` (`0xb6`): Full 128-bit $\times$ 128-bit $\to$ 256-bit unsigned wide multiply. Pops $(a, b)$, pushes $(prod_{high}, prod_{low})$.
* `OP_LOG` (`0xbd`): Fixed-point base-2 logarithm using the Turner algorithm.
* `OP_SQRT` (`0xbe`): Integer square root ($\lfloor\sqrt{x}\rfloor$).

By chaining `OP_ADDCARRY`, `OP_SUBCARRY`, and `OP_MUL128_WIDE`, user-space contracts can implement 256-bit (secp256k1, secp256r1, Ed25519) and 384-bit (BLS12-381) field arithmetic directly in Script.

#### 3.7.2. Cryptographic Hashing & Signature Verification
* `OP_BLAKE3` (`0xcd`): Single-pass BLAKE3 hash ($\approx 12\text{ ns}$).
* `OP_SHA256` (`0xa8`): Single SHA-256 hash.
* `OP_HASH256` (`0xaa` / `OP_SHA256D`): Double SHA-256 for Bitcoin cross-chain header verification.
* `OP_CHECKSIG` (`0xac`): Evaluates 64-byte Schnorr signatures (BIP340) by default, or 64-byte compact Low-S ECDSA.
* `OP_CHECKDATASIG` (`0xba`): Verifies an arbitrary message hash against a public key.
  - **Multi-Curve Algorithm Parameter**: Evaluates a curve parameter byte on stack:
    - `0x00`: **secp256k1** (standard Bitcoin/Lotus curve)
    - `0x01`: **secp256r1 (NIST P-256)** — Native support for **Apple Secure Enclave (FaceID / TouchID)**, **Google Titan M**, and **WebAuthn / FIDO2 Passkeys**! Allows non-custodial mobile spending without seed phrases.
    - `0x02`: **Ed25519** — Fast Edwards-curve signatures for cross-ecosystem attestation.
* `OP_MERKLEVERIFY` (`0xbb`): Verifies Merklix branch inclusion/exclusion proofs on stack against a state root.

---

### 3.8. Native Introspection Opcodes (`0xc0–0xd2`) — BCH Ecosystem Aligned

To maximize tooling interoperability with CashScript, Libauth, and existing smart contract compilers, Lotus v2 aligns its native introspection opcodes directly with the **Bitcoin Cash (BCH) May 2022 specification**, while augmenting them with Lotus v2's 80-byte POD metadata and bounded loop primitives:

| Opcode | Hex | Stack In $\to$ Out | Alignment | Description |
| :--- | :--- | :--- | :--- | :--- |
| `OP_INPUTINDEX` | `0xc0` | `-> index` | **BCH Identical** | Pushes the 32-bit index of the executing input. |
| `OP_ACTIVEBYTECODE`| `0xc1` | `-> bytecode` | **BCH Identical** | Pushes currently executing script bytecode. |
| `OP_TXVERSION` | `0xc2` | `-> ver` | **BCH Identical** | Pushes the 32-bit transaction version. |
| `OP_TXINPUTCOUNT` | `0xc3` | `-> count` | **BCH Identical** | Pushes the total number of inputs. |
| `OP_TXOUTPUTCOUNT`| `0xc4` | `-> count` | **BCH Identical** | Pushes the total number of outputs. |
| `OP_TXLOCKTIME` | `0xc5` | `-> locktime` | **BCH Identical** | Pushes the 32-bit transaction locktime. |
| `OP_UTXOVALUE` | `0xc6` | `i -> amount` | **BCH Identical** | Pops input index $i$, pushes 128-bit satoshi amount. |
| `OP_UTXOBYTECODE` | `0xc7` | `i -> dest` | **BCH Identical** | Pops input index $i$, pushes 32-byte destination (pubkey hash or Merkle root). |
| `OP_OUTPOINTTXHASH`|`0xc8` | `i -> txid` | **BCH Identical** | Pops input index $i$, pushes 32-byte spent outpoint TXID. |
| `OP_OUTPOINTINDEX` | `0xc9` | `i -> vout` | **BCH Identical** | Pops input index $i$, pushes 32-bit spent outpoint index. |
| `OP_UTXOMETADATA` | `0xca` | `i -> metadata`| **Lotus v2 Native** | Pops input index $i$, pushes 32-byte metadata (Token/Covenant state). |
| `OP_UTXOTYPE` | `0xcb` | `i -> type` | **Lotus v2 Native** | Pops input index $i$, pushes 1-byte output type (`0x01`–`0x04`). |
| `OP_OUTPUTVALUE` | `0xcc` | `j -> amount` | **BCH Identical** | Pops output index $j$, pushes 128-bit satoshi amount. |
| `OP_OUTPUTBYTECODE`|`0xcd` | `j -> dest` | **BCH Identical** | Pops output index $j$, pushes 32-byte destination (pubkey hash or Merkle root). |
| `OP_OUTPUTMETADATA`|`0xce` | `j -> metadata`| **Lotus v2 Native** | Pops output index $j$, pushes 32-byte metadata (Token/Covenant state). |
| `OP_OUTPUTTYPE` | `0xcf` | `j -> type` | **Lotus v2 Native** | Pops output index $j$, pushes 1-byte output type (`0x01`–`0x04`). |
| `OP_TXID` | `0xd0` | `-> txid` | **Lotus v2 Native** | Pushes the 32-byte Single-BLAKE3 Merklix TXID of current transaction. |
| `OP_FOREACH_INPUT` | `0xd1` | `... OP_ENDFOR` | **Lotus v2 Native** | Starts an enumerable bounded loop over all inputs (depth $\le 2$). |
| `OP_FOREACH_OUTPUT`| `0xd2` | `... OP_ENDFOR` | **Lotus v2 Native** | Starts an enumerable bounded loop over all outputs (depth $\le 2$). |

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

---

## 8. Post-Genesis Evolution: Zero-Hardfork Enhancements

Because all consensus invariants (Header format, 80B POD Outputs, BLAKE3, 128-bit VM, Introspection, P2MNOR, Tail Subsidy) are permanently locked at Block 0, future protocol optimizations remain **strictly internal node implementations and network transport upgrades** that require **ZERO hardforks**:

### 8.1. QUIC P2P Transport Layer (RFC 9000 / HTTP/3 over UDP)
* **Deep Packet Inspection (DPI) Invisibility**: Transports P2P messages inside standard TLS 1.3 encrypted UDP datagrams. To ISPs, enterprise firewalls, and state censors, Lotus P2P traffic looks indistinguishable from standard HTTP/3 web browsing (Cloudflare, Google, YouTube).
* **Elimination of Head-of-Line Blocking**: In TCP, a dropped packet on a 32 MB block stalls all concurrent transaction relay. In QUIC, independent streams (blocks, mempool transactions, peer discovery, heartbeats) multiplex over a single connection without blocking.
* **Connection Migration for Mobile Nodes**: QUIC connections bind to 64-bit Connection IDs rather than `IP:Port` tuples. Mobile wallets and node operators can transition seamlessly from Wi-Fi to 5G cellular without dropping peer connections or restarting handshakes.
* **Zero-Hardfork Rollout**: Introduced via standard P2P feature negotiation (`NODE_QUIC` service bit) in `src/net`. Nodes that support QUIC upgrade immediately; older or constrained nodes remain on TCP.

### 8.2. Stateless Snap-Sync RPCs & P2P Merklix Chunk Streaming
* Rapid node synchronization utilizing authenticated Crit-Bit Radix Trie snapshots.
* New nodes sync to the tip in $< 3 \text{ minutes}$ by streaming the Radix Trie leaves validated against the header's `hashUtxoMerklixRoot`.

### 8.3. Chronik Indexer API Adaptations & Real-Time WebSockets
* Native streaming of L1 token balances (`uint128_t amount || uint128_t token_id`), XAddress (`xpi` prefix), and 32-byte output metadata.
* Enables Web3 applications and mobile wallets to query balances and state channels in $O(1)$ time without running an L1 script evaluator.

### 8.4. Partially Signed Lotus Transactions (PSLT / BIP-0370 Standard)
* Standardized binary exchange format for air-gapped hardware wallets, multisig coordinators, and mobile signers.
* Incorporates native fields for 80-byte POD outputs, 32-byte metadata, and Merklix proofs.

### 8.5. Architectural Exclusion of Double-Spend Proofs (BUIP135)
* **The Asymmetric DoS Vulnerability**: Double-Spend Proofs (DSPs) introduce an un-fee'd signature verification cascade. An attacker splitting 1 XPI into 100,000 dust outputs can broadcast 100,000 conflicting transactions, forcing every full node on the network to perform 200,000 cryptographic signature checks and gossip the proofs across the P2P topology without paying a single satoshi in fees.
* **Script & Covenant Incompatibility**: DSPs break down on stateful smart contracts and `P2MNOR` guardrails, requiring complex whitelist heuristics that compromise protocol simplicity.
* **The Sound Alternative**: Lotus v2 adheres to pure Nakamoto first-seen policy: conflicting mempool spends are rejected in a single $O(1)$ hash table check ($<5\text{ ns}$ CPU cost, zero bandwidth, zero state bloat).
