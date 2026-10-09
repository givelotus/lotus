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
   - [3.3. Zero-Copy Wire Format, Inline Witnesses & Single-Asset Multi-Branch Outputs](#33-zero-copy-wire-format-inline-witnesses--single-asset-multi-branch-outputs)
   - [3.4. Universal Asset Conservation & Minting Engine](#34-universal-asset-conservation--minting-engine)
   - [3.5. Multi-Branch Architecture & Explicit Branch Witnesses](#35-multi-branch-architecture--explicit-branch-witnesses)
   - [3.6. The 128-Bit Forth Stack Machine (`int128_t`)](#36-the-128-bit-forth-stack-machine-int128_t)
   - [3.7. Multi-Precision & Cryptographic Primitives](#37-multi-precision--cryptographic-primitives)
   - [3.8. Native Introspection Opcodes (`0xc0–0xd9`) — Multi-Branch & Single-Asset Aligned](#38-native-introspection-opcodes-0xc00xd9--multi-branch--single-asset-aligned)
   - [3.9. Bounded Primitive Recursion (`OP_ENUMERATE`) & Static Precomputed Cost Budget](#39-bounded-primitive-recursion-op_enumerate--static-precomputed-cost-budget)
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
│  • Memory-Aligned Wire Format & Inline Branch Witnesses                │
│  • Single-Asset UTXO (43B Pure XPI fits in single 64B L1 Cache Line)   │
│  • Universal Asset Conservation: ∑in[asset] ≥ ∑out[asset]              │
│  • Token Identity: TokenID = BLAKE3(minting_script), Zero Batons       │
│  • 128-bit Two's-Complement Stack VM Semantics (int128_t)              │
│  • Native Introspection Opcodes (0xc0–0xde)                            │
│  • Bounded Primitive Recursion (OP_ENUMERATE, Nested Loops N ≤ 2)      │
│  • Static Precomputed Execution Budget (Zero Halting Problem)          │
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
| **Output Representation** | Dynamic `vector<uint8_t>` | Dynamic `vector<uint8_t>` | **Single-Asset Multi-Branch (45B/77B)** | 45B pure XPI fits in single 64B L1 CPU cache line; zero dust for tokens; Variadic spending paths & branch MASTs. |
| **Script Stack Integers** | `CScriptNum` (32-bit signed) | `CScriptNum` + 64-bit hacks | **Native `int128_t` (128-bit)** | Eliminates sign-magnitude bugs, enables high-precision finance. |
| **Multi-Precision Math** | None | Ad-hoc `BIGADD` | `OP_ADDCARRY`, `OP_SUBCARRY`, `OP_MUL128_WIDE` | Curve arithmetic (secp256k1, BLS12-381) directly in Script. |
| **Covenant Introspection** | None | Ad-hoc sighash flags | **Native Opcodes (`0xc0–0xde`)** | Inspects inputs, outputs, outpoints, branches, state, paths in 1 CPU cycle. |
| **Script Loops** | Disabled / Forbidden | Mitra loop proposal | **`OP_ENUMERATE` Family** | Primitive recursion bounded by inputs/outputs or $N \le 256$; zero Halting Problem. |
| **Native L1 Tokens** | None (3rd party indexers) | None | **Universal Conservation ($\sum \text{in} \ge \sum \text{out}$)** | $\text{TokenID} = \text{BLAKE3}(\text{minting\_script})$; zero consensus batons; zero dust. |
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

### 3.3. Zero-Copy Wire Format, Inline Witnesses & Single-Asset Multi-Branch Outputs

Variable-length integers (`CompactSize` / `varint`) are eliminated from transaction headers and fixed records. Crucially, the BIP-141 soft-fork hack of a decoupled, trailing `witness` vector is completely discarded. In Lotus v2, **witnesses map 1-to-1 directly inside `vin`**, and **minting proofs are structured per-asset at the transaction level**.

```cpp
// Transaction Wire Header (16 Bytes)
struct LotusTxHeader {
    int32_t  nVersion;       // 4 bytes: Tx format version
    uint32_t nLockTime;      // 4 bytes: Block height or MTP locktime
    uint32_t nInputCount;    // 4 bytes: Fixed 32-bit integer
    uint32_t nOutputCount;   // 4 bytes: Fixed 32-bit integer
    // Note: mint_count follows outputs if nVersion indicates minting/v2
};

// Branch Witness (Carried inside each input, positionally mapped to required branches)
struct BranchWitness {
    CScript script;                              // The UNHASHED leaf script bytecode (Preimage)
    std::vector<uint256> merkle_proof;           // Merklix audit path (empty if 1-leaf single script)
    std::vector<std::vector<uint8_t>> args;      // Unlocking parameters / signatures passed to script
};

// Input Record (Inline Branch Witnesses with Positional Witness Binding)
struct LotusInput {
    COutPoint prevout;                           // 32B txid + 4B index (36 bytes)
    uint32_t  nSequence;                         // 4 bytes (RBF / Relative Locktime)
    uint8_t   flags;                             // 1 byte:
                                                 //   Bit 0 (0x01): FLAG_READ_ONLY_REFERENCE
                                                 //   Bits 1-7: Reserved (must be 0)
    CompactSize path_index;                      // Index into spent coin's paths array (coin.paths[path_index])
    std::vector<BranchWitness> branch_witnesses; // Positionally maps 1-to-1 to required branches in chosen path
};

// Output Record (Single-Asset Representation with Unified nValue & Variadic Spending Paths)
struct LotusOutput {
    uint8_t  flags;                              // 1 byte:
                                                 //   Bit 0 (0x01): FLAG_HAS_TOKEN
                                                 //   Bit 1 (0x02): FLAG_HAS_STATE
                                                 //   Bits 2-7: Reserved (must be 0)
    Amount   nValue;                             // 8 bytes: Single unified amount (XPI satoshis OR Token units)
    
    // Present ONLY if (flags & FLAG_HAS_TOKEN) is set:
    uint256  token_id;                           // 32 bytes: TokenID = BLAKE3(minting_script)
    
    // Present ONLY if (flags & FLAG_HAS_STATE) is set:
    CompactSize state_len;                       // Length of state payload
    std::vector<uint8_t> state_commitment;       // Dynamic NFT / state machine data
    
    CompactSize num_branches;                    // Count of branch Merklix roots (1 to 65,535)
    std::vector<uint256> branches;               // Array of 32B Merklix Roots
    
    CompactSize num_paths;                       // Count of valid spending paths (1 to 65,535)
    std::vector<std::vector<CompactSize>> paths; // Each path is a sorted vector of branch indices required
};

// Transaction-Level Mint Witness (Present ONLY when expanding token supply: Delta > 0)
struct TokenMintWitness {
    CScript minting_script;                      // Preimage of TokenID: TokenID = BLAKE3(minting_script)
    std::vector<std::vector<uint8_t>> stack_args;// Arguments (delegated certificates, signatures, proofs)
};
```

#### Wire Layout & Cache-Line Efficiency:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ PURE XPI STANDARD OUTPUT (45 Bytes - Fits in a SINGLE 64-Byte CPU Cache Line!)         │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ [00..00] uint8_t     flags            (1B: 0x00 = Pure Native XPI)                     │
│ [01..08] uint64_t    nValue           (8B: Native XPI satoshis)                        │
│ [09..09] CompactSize num_branches     (1B: 0x01 = 1 branch root)                       │
│ [10..41] uint256     branch[0]        (32B: Merklix Root: BLAKE3(OwnerScript))         │
│ [42..42] CompactSize num_paths        (1B: 0x01 = 1 spending path)                     │
│ [43..43] CompactSize path[0].len      (1B: 0x01 = 1 required branch)                   │
│ [44..44] CompactSize path[0][0]       (1B: 0x00 = requires branch 0)                   │
└────────────────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────────────────┐
│ TOKEN / COVENANT OUTPUT (77 Bytes - Zero Dust, Pure Single-Asset UTXO)                 │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ [00..00] uint8_t     flags            (1B: 0x01 = FLAG_HAS_TOKEN)                      │
│ [01..08] uint64_t    nValue           (8B: Token units - NO native XPI dust!)          │
│ [09..40] uint256     token_id         (32B: Asset ID = BLAKE3(minting_script))         │
│ [41..41] CompactSize num_branches     (1B: 0x01 = 1 branch, or 0x02 = 2 branches)      │
│ [42..73] uint256     branch[0]        (32B: Merklix Root: BLAKE3(OwnerScript))         │
│ [74..105]uint256     branch[1] (opt)  (32B: Merklix Root: BLAKE3(CovenantScript))      │
│ [106..]  Spending Paths...            (CompactSize num_paths & required branch lists)  │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

#### Why Re-Using `nValue` Eliminates the "Dust Nightmare":
1. **Zero Dust Overhead**:
   In legacy protocols (SLP, CashTokens), token outputs were mutant hybrids: they were forced to carry 546 satoshis of native crypto just to satisfy miner dust limits. In Lotus v2, **token outputs carry 0 XPI satoshis**.
2. **Zero Accidental Burn Risk**:
   Because token outputs have no native XPI in them, an un-upgraded wallet cannot mistake a token coin for a satoshi coin and accidentally spend it as miner fees.
3. **Malleability Immunity by Construction**:
   The **TXID** is defined as:
   $$\mathbf{TxID} = \mathbf{BLAKE3}\Big(\text{nVersion} \parallel \text{nLockTime} \parallel \text{vin\_stripped} \parallel \text{vout}\Big)$$
   Where `vin_stripped` excludes all `branch_witnesses`, and `mint_witnesses` are excluded. Third parties can never malleate the TXID.

---

### 3.4. Native Layer-1 Assets & Universal Conservation

#### 3.4.1. The Universal Conservation Law
In Lotus v2, the consensus engine runs a single, universal accounting loop across all assets in a transaction:

For every unique `asset_id` (where `asset_id = 0` represents native XPI):
$$\sum_{\text{in}} \text{nValue}[\text{asset}] \ge \sum_{\text{out}} \text{nValue}[\text{asset}]$$

* **For Native XPI (`asset_id == 0`)**:
  The difference is the **Miner Fee**:
  $$\text{Miner Fee} = \sum_{\text{in}} \text{nValue}[\text{XPI}] - \sum_{\text{out}} \text{nValue}[\text{XPI}] \ge 0$$
* **For Tokens (`asset_id != 0`)**:
  The difference is an **Opt-in Burn**.
* **Sub-Microsecond Validation**:
  For 99.9% of transactions (standard peer-to-peer transfers), token validation requires **zero script interpretation**. It is a single SIMD 128-bit comparison (`sum_in >= sum_out`). Nodes validate over 100,000 token transfers per second per CPU core.

#### 3.4.2. Token Scarcity & The Minting Engine ($\Delta > 0$)
When a transaction outputs more tokens than it inputs:
$$\Delta[\text{TokenID}] = \sum_{\text{out}} \text{nValue}[\text{TokenID}] - \sum_{\text{in}} \text{nValue}[\text{TokenID}] > 0$$

Consensus strictly requires an entry in `tx.mint_witnesses` where:
$$\mathbf{TokenID} = \mathbf{BLAKE3}(\text{mint\_witness}.\text{minting\_script})$$

The node executes `minting_script` with `mint_witness.stack_args`. If the script returns `true`, the expansion of supply is approved. If missing or false, the transaction is immediately rejected as counterfeit (`bad-txns-unauthorized-mint`).

#### 3.4.3. The Three Minting & Governance Architectures (Zero Batons in Consensus)
Tracking physical "baton coins" in consensus creates massive codebase fragility (LevelDB capability flags, undo log bloat, accidental burn risks). Lotus v2 eliminates consensus batons entirely in favor of three clean architectures:

1. **Pattern 1: The Treasury Vault Pattern (Zero Minting Scripts After Genesis)**:
   * At Genesis, total authorized supply (e.g. 10 Billion USDC) is minted into a **Treasury Vault UTXO** governed by an $m$-of-$n$ multisig. Circulating market supply is $0$.
   * **Issuance**: When reserves arrive, the company spends from the Treasury UTXO: $50,000$ to the buyer, and $9,999,950,000$ change back to the Treasury.
   * **Key Rotation**: The officers spend the Treasury coin to their **new multisig address**.
   * **Consensus**: $\sum \text{in} \ge \sum \text{out}$ holds 100% of the time. The consensus engine never executes a minting script after Genesis.
2. **Pattern 2: Dynamic Delegated Minting (`OP_CHECKDATASIG`)**:
   * For elastic tokens: `MintingScript` hardcodes a **Cold Root Public Key** (`Root_PK`).
   * The cold key signs an off-chain **Delegation Certificate**:
     $$\text{Cert} = \text{Sign}_{\text{Root\_PK}}(\text{Epoch: 2}, \text{ Authorized: Frank}, \text{ Expiry: Block 600,000})$$
   * When minting, `mint_witnesses` provides `stack_args = [Frank_Sig, Cert_Bytes, Root_Sig]`.
   * `MintingScript` verifies the certificate via `OP_CHECKDATASIGVERIFY`, extracts Frank's key, and verifies Frank's transaction signature with `OP_CHECKSIG`.
   * **Key Rotation**: Cold Root signs a new certificate. `TokenID` never changes. Consensus tracks zero batons.
3. **Pattern 3: One-Time Hard-Capped Genesis (e.g. 21 Million Max Supply)**:
   * Anchored to a unique Genesis outpoint (`prevout = 0x1234...:0`):
     ```forth
     OP_0 OP_PICKINPUTOUTPOINT <0x1234...:0> OP_EQUALVERIFY
     OP_0 OP_ENUMERATE_OUTPUTS OP_PICKOUTPUTVALUE OP_ADD OP_ENDENUMERATE
     2100000000000000 OP_LESSTHANOREQUAL
     ```
   * Because `prevout` can only be spent once in blockchain history, the script can only succeed once. Double-minting is mathematically prevented by UTXO double-spend rules.

#### 3.4.4. Read-Only Reference Inputs (`FLAG_READ_ONLY_REFERENCE`)
To inspect on-chain vault or oracle state without double-spend contention:
* Set `FLAG_READ_ONLY_REFERENCE = 0x01` on `LotusInput`.
* The coin is **read, not spent**. It remains in the UTXO set.
* Enables 10,000 users to read and validate against a central vault in the exact same block with **zero lock collisions**.

---

---

### 3.5. Variadic Spending Paths, Branch Merklix Trees (MAST) & Intra-Transaction Validation Caching

#### 3.5.1. The Variadic Spending Paths Architecture (Option B Positional Witnesses)
In smart contract and transaction design, spending authorization naturally resolves into two orthogonal dimensions:
1. **Horizontal Role Composition (Branches & Paths)**: *"WHICH participants, covenants, or guardians must approve this spend?"*
2. **Vertical Specialization (The MAST within each Branch)**: *"WHICH specific method or execution path is that role running?"*

##### Elimination of Fixed-Depth Tree Bottlenecks
Early iterations evaluated spending conditions using fixed boolean topologies (such as 4-leaf NAND trees). However, fixed-depth structures introduce severe limitations:
* They artificially restrict an output to at most 4 leaves and 2 spending paths.
* They cannot express simple, common structures like $A \lor B \lor C$ (three independent alternative spenders) or $A \land B \land C$ (three co-signers) without nested inlining acrobatics.
* Forcing multi-spender and multi-method logic into a single fixed tree causes combinatorial inlining bloat: 3 co-signers and 3 contract methods would require duplicating code across $\binom{3}{2} \times 3 = 9$ separate leaves.

Lotus v2 replaces fixed wiring topologies with the **Variadic Spending Paths Architecture**:
$$\text{branches} = [ \mathbf{root}_0, \mathbf{root}_1, \dots, \mathbf{root}_{N-1} ] \quad (1 \le N \le 65,535)$$
$$\text{paths} = [ \mathbf{path}_0, \mathbf{path}_1, \dots, \mathbf{path}_{M-1} ] \quad (1 \le M \le 65,535)$$

* **Branches**: An explicit array of 32-byte Merklix Roots, each representing an autonomous role or policy (e.g. Owner, Co-Signer, Covenant, Protocol Fee Controller).
* **Paths**: A list of valid spending paths. Each path is a canonical, strictly sorted vector of branch indices required:
  $$\mathbf{path}_p = [ b_{p,0}, b_{p,1}, \dots, b_{p,k-1} ] \quad \text{where } b_{p,0} < b_{p,1} < \dots < b_{p,k-1}$$
* **Expressiveness**:
  * **Standard Single-Key / P2SH**: `branches = [A]`, `paths = [[0]]`
  * **2-of-2 Covenant (Owner + Vault)**: `branches = [Owner, Vault]`, `paths = [[0, 1]]`
  * **1-of-2 Recovery (Owner OR Backup Key)**: `branches = [Owner, Backup]`, `paths = [[0], [1]]`
  * **Quorum / Guarded Spending**: `branches = [Alice, Bob, Charlie, Vault]`, `paths = [[0, 1, 3], [0, 2, 3], [1, 2, 3]]` (Any 2 owners AND the vault).

##### Option B: Positional Witness Mapping
When spending an output, the transaction input chooses exactly which spending path to activate via `input.path_index`:
$$\mathbf{active\_path} = \text{coin.paths}[\text{input.path\_index}]$$

To eliminate all redundant wire overhead, dummy witnesses, and placeholder padding:
* The transaction input supplies an array of branch witnesses: `input.branch_witnesses`.
* **Positional Binding Invariant**: The number of witnesses provided MUST exactly equal the number of required branches in the selected path:
  $$\mathbf{input.branch\_witnesses.size}() == \mathbf{active\_path.size}()$$
* Witness element $i$ positionally binds to branch index $\mathbf{active\_path}[i]$:
  $$\mathbf{input.branch\_witnesses}[i] \iff \mathbf{coin.branches}[\mathbf{active\_path}[i]]$$
* There is **zero branch index byte** within the witness, **zero empty dummy witnesses**, and **zero unspent branch leakage**. If the spending path requires branches `[0, 2]`, `branch_witnesses` has length 2: `witness[0]` validates against `branch[0]`, and `witness[1]` validates against `branch[2]`.

---

#### 3.5.2. Every Branch is a 32-Byte Merklix Root (MAST)
Every entry in `coin.branches` is uniformly a **32-byte Merklix Root**. A branch can be either a single atomic script or an entire Merklized Alternative Script Tree (MAST):

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ 1. HORIZONTAL COMPOSITION (Branches & Paths on Output Wire)                            │
│    • Output defines: branches[0..N] and paths[0..M]                                    │
│    • e.g. Path 0: [Alice, Bob, LendingVault]                                          │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 2. VERTICAL SPECIALIZATION (MAST within each Branch Root)                              │
│    • Each branch root expands into its own Merklix tree of leaf methods                │
│    • Spender reveals ONLY the active leaf script + Merkle audit path                   │
│    • Unused methods remain completely private 32-byte hashes                           │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

##### 1-Leaf Fast Path vs Multi-Leaf Merklix Tree
When validating `input.branch_witnesses[i]` against branch root $\mathbf{R} = \text{coin.branches}[\mathbf{active\_path}[i]]$:
1. **1-Leaf Tree Fast Path (`merkle_proof.empty()`)**:
   For standard single-key payments, basic multisig, or single-method scripts, the branch root is simply the BLAKE3 hash of the leaf script:
   $$\mathbf{BLAKE3}(\text{bw.script}) == \mathbf{R}$$
   If `bw.script` is a standard public-key script (`<PubKey> OP_CHECKSIG`), the interpreter skips bytecode parsing and dispatches directly to AVX-512 batch Schnorr verification ($\approx 30\text{ ns}$).
2. **Multi-Leaf Tree (`!merkle_proof.empty()`)**:
   For smart contracts with multiple methods (e.g. `deposit`, `borrow`, `liquidate`, `repay`):
   * Each method is an unhashed leaf in a BLAKE3 domain-separated Merklix tree:
     $$\mathbf{leaf\_hash} = \mathbf{BLAKE3}(\text{DOMAIN\_LEAF} \parallel \text{bw.script})$$
   * The node verifies that `leaf_hash` is cryptographically included in $\mathbf{R}$ using `bw.merkle_proof`:
     $$\mathbf{VerifyMerklixProof}(\mathbf{leaf\_hash}, \text{bw.merkle\_proof}, \mathbf{R}) == \mathbf{true}$$
   * The spender reveals only the active method script and its Merkle path. All other methods remain cryptographically unrevealed and zero-knowledge.

---

#### 3.5.3. Wire-Level P2PKH Obsolescence: Universal Script Hashing & Address Resolution
In legacy Bitcoin (2008), the consensus protocol maintained distinct serialized wire formats for different output types (`scriptPubKey` bytecodes for P2PK, P2PKH, P2SH). This forced full nodes to inspect and branch on arbitrary, variable-length script bytecodes during UTXO database serialization and mempool validation.

##### Wire-Level Unification (All Outputs Are Branch Roots)
In Lotus v2, **the distinct wire-level "P2PKH output" is obsolete**. The consensus wire format recognizes only one unified output representation: an explicit array of 32-byte BLAKE3 branch roots evaluated through variadic spending paths:
$$\mathbf{branch}[k] = \mathbf{BLAKE3}(\mathbf{script}_k) \quad \text{or} \quad \mathbf{branch}[k] = \mathbf{MerklixRoot}(\{\mathbf{script}_{k,m}\})$$

Every output in Lotus v2 is structurally a Pay-to-Script-Hash (P2SH) / Pay-to-MAST. Consensus does not know or care whether an output is a single-key payment, an address hash, a multisig vault, or an AMM covenant—they all exist as uniform 32-byte hashes.

##### Sending to a Hashed PubKey Address (`pubkeyhash`)
When a user shares an address, they provide a compact hashed public key (`pubkeyhash`):
$$\mathbf{PubKeyHash} = \mathbf{BLAKE3}(\text{PubKey}) \quad \text{or} \quad \mathbf{RIPEMD160}(\mathbf{SHA256}(\text{PubKey}))$$

The sender only knows `PubKeyHash`—the sender **does not know the recipient's raw public key**. 

Hashing the public key inside the script is therefore essential for address-based payments:
1. **Deterministic Script Construction by Sender**:
   The sender's wallet constructs the canonical address-resolution script from `PubKeyHash`:
   $$\mathbf{script} = \mathbf{OP\_DUP} \;\; \mathbf{OP\_BLAKE3} \;\; \langle\mathbf{PubKeyHash}\rangle \;\; \mathbf{OP\_EQUALVERIFY} \;\; \mathbf{OP\_CHECKSIG}$$
2. **Commitment on the Wire**:
   The sender computes the 32-byte branch root:
   $$\mathbf{branch}[0] = \mathbf{BLAKE3}(\mathbf{script})$$
   and serializes it into the 45-byte output record with `paths = [[0]]`. The sender never needs the recipient's public key.
3. **Sub-Microsecond Wallet Indexing**:
   The recipient's wallet knows its own `PubKeyHash`. The wallet precomputes:
   $$\mathbf{expected\_branch} = \mathbf{BLAKE3}\Big(\mathbf{OP\_DUP} \parallel \mathbf{OP\_BLAKE3} \parallel \mathbf{PubKeyHash} \parallel \mathbf{OP\_EQUALVERIFY} \parallel \mathbf{OP\_CHECKSIG}\Big)$$
   The wallet registers `expected_branch` with Chronik. When a transaction is received, Chronik indexes the output by `branch[0]` in $O(1)$ time—enabling instantaneous payment discovery without scanning raw scripts.
4. **Execution at Spend Time**:
   When spending the coin, the recipient's input supplies:
   * `input.path_index = 0`
   * `input.branch_witnesses[0].script = OP_DUP OP_BLAKE3 <PubKeyHash> OP_EQUALVERIFY OP_CHECKSIG`
   * `input.branch_witnesses[0].merkle_proof = []`
   * `input.branch_witnesses[0].args = [ <64B Schnorr Sig>, <33B PubKey> ]`
   The node verifies `BLAKE3(script) == coin.branches[0]`, then executes the script: `PubKey` is duplicated, hashed with BLAKE3, verified equal to `PubKeyHash`, and the Schnorr signature is verified against `PubKey`.

##### Direct Public-Key Scripts (`<PubKey> OP_CHECKSIG`)
When the recipient's public key is known in advance (e.g. interactive payment channels, deterministic key exchanges, or Nostr/WebLN invoices), the sender skips the inner pubkey hash check:
$$\mathbf{script} = \langle\text{33-byte PubKey}\rangle \;\; \mathbf{OP\_CHECKSIG} \quad (34\text{ bytes})$$
$$\mathbf{branch}[0] = \mathbf{BLAKE3}(\text{PubKey} \parallel \text{OP\_CHECKSIG})$$
At spend time, the witness provides only `args = [ <64B Schnorr Sig> ]` (saving 33 bytes on the wire), and node validators route directly to the AVX-512 batch Schnorr fast-path ($\approx 30\text{ ns}$).

---

#### 3.5.4. Multi-Covenant Token Governance & The Linear Resource Model (Move Comparison)
In Ethereum, token balances and covenant states are stored in isolated, siloed smart contract storage tables (`mapping(address => uint256)`). This forces tokens to be manipulated through dynamic cross-contract calls (`transferFrom`), introducing reentrancy vulnerabilities and severe execution bottlenecks.

Lotus v2 adopts the **Linear Resource Model** (analogous to the Move language):
1. **Assets are Resources, Not Storage Mappings**:
   An asset is a physical UTXO record. It has an explicit asset identity (`token_id`), cannot be cloned, cannot be silently destroyed, and obeys the immutable universal conservation law:
   $$\sum_{\text{in}} \text{nValue}[\text{asset}] \ge \sum_{\text{out}} \text{nValue}[\text{asset}]$$
2. **Orthogonal Separation: Asset Type vs. Owner vs. Covenant Logic**:
   * **Asset Type (`token_id`)**: Distinguishes native XPI (miner fees) from specific tokens, enabling $O(1)$ SIMD conservation checks ($3\text{ ns}$) without executing any script.
   * **Owner (`branch[0]`)**: Authorizes the asset holder to approve transfers or reallocations.
   * **Covenant Rules (`branch[1]`, etc.)**: Governs operational rules (liquidity pools, collateral vaults, vesting locks).
3. **Decoupled Composability**:
   Because `token_id` is an explicit orthogonal field, a token can enter a lending vault, transition into an AMM pool, or be deposited into an escrow contract **without mutating its underlying asset identity**. The covenant simply occupies a branch on the coin, leaving the asset type immutable.

---

#### 3.5.5. Intra-Transaction Validation Caching & Static Purity Analysis (`OP_INPUTINDEX`)
In complex transactions (such as vault consolidations, batch withdrawals, or multi-input swaps), multiple transaction inputs often execute identical covenant branch scripts. If every input naively re-executes the same covenant script from scratch, validation time scales linearly with input count ($O(K \cdot \text{ops})$).

##### The Reflected Data Hazard: Why Naive Caching Breaks
A naive node implementation might attempt to cache script execution results across companion inputs by script hash alone: $\mathbf{CacheKey} = \mathbf{BLAKE3}(\text{TxID} \parallel \text{ScriptHash})$.
However, if a covenant uses **reflected input data**—specifically `OP_INPUTINDEX` (`0xc0`) or input-dependent introspection:
* On `vin[0]`, `OP_INPUTINDEX` pushes `0`.
* On `vin[1]`, `OP_INPUTINDEX` pushes `1`.
* If `vin[0]` executes `OP_INPUTINDEX OP_UTXOVALUE` and sees $10,000\text{ XPI}$, but `vin[1]` only provides $1\text{ XPI}$, blindly reusing `vin[0]`'s cached `TRUE` result on `vin[1]` would allow an attacker to bypass all balance checks and drain the vault!

##### Solution 1: Static Purity Analysis (Node-Level Caching)
Before executing a branch script, the node validator performs a single $O(\text{script\_size})$ scan over the script bytecode:
$$\mathbf{IsPureTxPredicate} = (\text{script does NOT contain } \mathbf{OP\_INPUTINDEX})$$

* **Pure Transaction Predicates (`IsPureTxPredicate == true`)**:
  The script only inspects global transaction invariants (`tx.outputs`, `tx.locktime`, `tx.version`, or literal inputs via `0 OP_UTXOVALUE`). The script is a mathematically pure function of the transaction:
  $$f(\text{Tx}) \to \{\mathbf{TRUE}, \mathbf{FALSE}\}$$
  Its result is 100% invariant across all inputs in the transaction. The node safely caches the result using:
  $$\mathbf{CacheKey} = \mathbf{BLAKE3}(\text{TxID} \parallel \text{ScriptHash})$$
  The script executes exactly **once** for the first companion input; all subsequent companion inputs resolve the cache in $< 5\text{ nanoseconds}$.
* **Input-Dependent Predicates (`IsPureTxPredicate == false`)**:
  The script's outcome depends on which input is currently executing. The cache key commits to the executing input index:
  $$\mathbf{CacheKey} = \mathbf{BLAKE3}(\text{TxID} \parallel \text{ScriptHash} \parallel \mathbf{input\_index})$$
  The script evaluates independently for each input, guaranteeing absolute consensus soundness.

##### Solution 2: The Master/Companion Script Pattern (Compiler-Level)
High-performance covenant compilers (such as the Lotus Contract Compiler) optimize multi-input covenants using the **Master/Companion Pattern**:
* The covenant script checks whether it is running on the primary ("master") vault input:
  $$\mathbf{is\_master} = (\mathbf{OP\_INPUTINDEX} == \mathbf{master\_input\_index})$$
* **On the Master Input**: The contract executes the comprehensive aggregation loop: iterating over all inputs, computing total vault balances, and verifying reserve constraints.
* **On Companion Inputs**: The contract executes a **3-opcode fast-path**:
  ```forth
  <master_input_index> OP_UTXOBRANCH <branch_k> OP_ACTIVEBYTECODE OP_BLAKE3 OP_EQUALVERIFY
  ```
  It simply asserts that the Master Input is present in this same transaction and executing the identical covenant.
* **Result**: In a 5-input consolidation, 1 input executes the loop, and 4 inputs execute in 3 CPU instructions. Total execution cost drops by $> 75\%$.

---

#### 3.5.6. Complete Output Authorization Validation Algorithm
```cpp
bool VerifyLotusOutputAuthorization(const LotusOutput &coin, const LotusInput &input, size_t input_index, const CTransaction &tx) {
    // 1. Path Index Bounds Check
    if (input.path_index >= coin.paths.size()) {
        return false; // SCRIPT_ERR_INVALID_PATH_INDEX
    }
    const std::vector<CompactSize> &required_branches = coin.paths[input.path_index];
    
    // 2. Option B Positional Mapping Invariant
    if (input.branch_witnesses.size() != required_branches.size()) {
        return false; // SCRIPT_ERR_WITNESS_COUNT_MISMATCH
    }
    
    // 3. Execute Required Branch Witnesses Positionally
    for (size_t i = 0; i < required_branches.size(); ++i) {
        CompactSize branch_k = required_branches[i];
        if (branch_k >= coin.branches.size()) {
            return false; // SCRIPT_ERR_BRANCH_INDEX_OUT_OF_BOUNDS
        }
        const uint256 &expected_branch_root = coin.branches[branch_k];
        const BranchWitness &bw = input.branch_witnesses[i];
        
        // 4. Branch Root Cryptographic Verification
        if (bw.merkle_proof.empty()) {
            // 1-Leaf Tree Fast-Path: Preimage check
            if (BLAKE3(bw.script) != expected_branch_root) {
                return false; // SCRIPT_ERR_SCRIPT_HASH_MISMATCH
            }
        } else {
            // Multi-Leaf Merklix Tree Proof
            uint256 leaf_hash = BLAKE3(DOMAIN_LEAF, bw.script);
            if (!VerifyMerklixProof(leaf_hash, bw.merkle_proof, expected_branch_root)) {
                return false; // SCRIPT_ERR_MERKLE_PROOF_INVALID
            }
        }
        
        // 5. Script Execution with Intra-Transaction Caching
        bool script_passed = false;
        if (bw.script.IsP2PKFastPath()) {
            // AVX-512 batch Schnorr fast-path (~30ns)
            script_passed = VerifySchnorrFastPath(bw);
        } else {
            // Static Purity Analysis & Caching
            bool is_pure = !ScriptContainsInputIndex(bw.script);
            uint256 cache_key = is_pure 
                ? BLAKE3(tx.GetId(), expected_branch_root)
                : BLAKE3(tx.GetId(), expected_branch_root, static_cast<uint32_t>(input_index));
            
            if (tx_validation_cache.Lookup(cache_key, script_passed)) {
                // Cache hit! Skip VM execution
            } else {
                script_passed = ExecuteScriptVM(bw.args, bw.script, input_index, tx);
                tx_validation_cache.Insert(cache_key, script_passed);
            }
        }
        
        if (!script_passed) {
            return false; // SCRIPT_ERR_EVAL_FALSE
        }
    }
    
    return true; // All required branches in selected path satisfied!
}
```

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
* `OP_BLAKE3` (`0xbf`): Single-pass BLAKE3 hash ($\approx 12\text{ ns}$).
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

### 3.8. Native Introspection Opcodes (`0xc0–0xde`) — Multi-Branch & Single-Asset Aligned

To maximize tooling interoperability with CashScript, Libauth, and smart contract compilers, Lotus v2 aligns its native introspection opcodes with the Bitcoin Cash (BCH) May 2022 specification while upgrading them to support Lotus v2's single-asset outputs, multi-branch architecture, state commitments, and reference inputs:

| Opcode | Hex | Stack In $\to$ Out | Description |
| :--- | :--- | :--- | :--- |
| `OP_INPUTINDEX` | `0xc0` | `-> index` | Pushes the 32-bit index of the executing input. |
| `OP_ACTIVEBYTECODE`| `0xc1` | `-> bytecode` | Pushes the currently executing branch script bytecode. |
| `OP_TXVERSION` | `0xc2` | `-> ver` | Pushes the 32-bit transaction version. |
| `OP_TXINPUTCOUNT` | `0xc3` | `-> count` | Pushes the total number of inputs. |
| `OP_TXOUTPUTCOUNT`| `0xc4` | `-> count` | Pushes the total number of outputs. |
| `OP_TXLOCKTIME` | `0xc5` | `-> locktime` | Pushes the 32-bit transaction locktime. |
| `OP_UTXOVALUE` | `0xc6` | `i -> nValue` | Pops input index $i$, pushes 128-bit integer value (XPI satoshis or token units). Alias: `OP_PICKINPUTVALUE`. |
| `OP_UTXOBRANCH` | `0xc7` | `i k -> branch_hash` | Pops input index $i$ and branch index $k$, pushes the 32-byte `branch[k]` hash of the spent coin. |
| `OP_OUTPOINTTXHASH`| `0xc8` | `i -> txid` | Pops input index $i$, pushes 32-byte spent outpoint TXID. |
| `OP_OUTPOINTINDEX` | `0xc9` | `i -> vout` | Pops input index $i$, pushes 32-bit spent outpoint index. |
| `OP_UTXOTOKENID` | `0xca` | `i -> token_id` | Pops input index $i$, pushes 32-byte `token_id` (or 32 zero bytes if native XPI). |
| `OP_UTXOSTATE` | `0xcb` | `i -> state` | Pops input index $i$, pushes state commitment byte vector (empty vector if none). |
| `OP_OUTPUTVALUE` | `0xcc` | `j -> nValue` | Pops output index $j$, pushes 128-bit integer value (XPI satoshis or token units). Alias: `OP_PICKOUTPUTVALUE`. |
| `OP_OUTPUTBRANCH`| `0xcd` | `j k -> branch_hash` | Pops output index $j$ and branch index $k$, pushes the 32-byte `branch[k]` hash. |
| `OP_OUTPUTTOKENID`| `0xce` | `j -> token_id` | Pops output index $j$, pushes 32-byte `token_id` (or 32 zero bytes if native XPI). |
| `OP_OUTPUTSTATE` | `0xcf` | `j -> state` | Pops output index $j$, pushes state commitment byte vector (empty vector if none). |
| `OP_TXID` | `0xd0` | `-> txid` | Pushes the 32-byte Single-BLAKE3 Merklix TXID of current transaction. |
| `OP_ENUMERATE_INPUTS`| `0xd1`| `... OP_ENDENUMERATE` | Bounded loop over all inputs ($0 \dots \text{nInputs}-1$). Auto-pushes current index $i$ on each iteration. |
| `OP_ENUMERATE_OUTPUTS`| `0xd2`| `... OP_ENDENUMERATE` | Bounded loop over all outputs ($0 \dots \text{nOutputs}-1$). Auto-pushes current index $j$ on each iteration. |
| `OP_ISREFERENCEINPUT`| `0xd3`| `i -> bool` | Pops input index $i$, pushes 1 if `FLAG_READ_ONLY_REFERENCE` is set, else 0. |
| `OP_TXMINTCOUNT` | `0xd4` | `-> count` | Pushes the total number of TokenMintWitness entries in the transaction. |
| `OP_INPUTSEQUENCENUMBER`| `0xd5`| `i -> nSequence` | Pops input index $i$, pushes its 32-bit sequence number. |
| `OP_INPUTFLAGS` | `0xd6` | `i -> flags` | Pops input index $i$, pushes its 1-byte flags. |
| `OP_UTXOBRANCHCOUNT`| `0xd7`| `i -> count` | Pops input index $i$, pushes the number of branches on the spent coin. |
| `OP_OUTPUTBRANCHCOUNT`| `0xd8`| `j -> count` | Pops output index $j$, pushes the number of branches on the output. |
| `OP_OUTPUTFLAGS`| `0xd9` | `j -> flags` | Pops output index $j$, pushes its 1-byte flags (`FLAG_HAS_TOKEN`, `FLAG_HAS_STATE`). |
| `OP_ENUMERATE` | `0xda` | `N ... OP_ENDENUMERATE` | Generic bounded enumeration loop ($0 \le N \le 256$). Pops $N$, auto-pushes loop counter $k \in [0, N-1]$. |
| `OP_ENDENUMERATE`| `0xdb`| `->` | Terminates loop body and steps to next iteration or exits. |
| `OP_BREAK` | `0xdc` | `depth -> ` | Pops integer `depth` ($1 \le \text{depth} \le 2$). Terminates `depth` nested active loops and jumps past target `OP_ENDENUMERATE`. |
| `OP_UTXOPATHCOUNT` | `0xdd` | `i -> count` | Pops input index $i$, pushes the number of valid spending paths (`paths.size()`) of the spent coin. |
| `OP_OUTPUTPATHCOUNT`| `0xde` | `j -> count` | Pops output index $j$, pushes the number of valid spending paths (`paths.size()`) of output $j$. |

---

### 3.9. Bounded Primitive Recursion (`OP_ENUMERATE`), Nested Loops ($N \le 2$) & Static Precomputed Cost Budget

#### 3.9.1. The DDoS Flaw in Generic `OP_LOOP`
In early smart contract designs (including Tobias Ruck's initial Mitra experiments), unbounded `OP_LOOP` or generic while-loops were explored. However, unbounded loops present a critical mempool denial-of-service vulnerability:
* An attacker crafts an invalid or low-fee transaction containing an infinite or near-infinite loop.
* Because execution length cannot be determined without running the script (the Halting Problem), nodes are forced to burn CPU cycles interpreting instructions until hitting an opcode or gas limit.
* Attackers can flood the mempool with free or low-fee transactions that exhaust node CPU resources without paying fees.

#### 3.9.2. Primitive Recursion via `OP_ENUMERATE`
Lotus v2 solves this completely by restricting control flow to **Primitive Recursion** through the `OP_ENUMERATE` opcode family:
* **Strict Physical Bounds**: Loops can only iterate over physically bound quantities:
  - `OP_ENUMERATE_INPUTS`: Strictly bounded by `tx.vin.size()`.
  - `OP_ENUMERATE_OUTPUTS`: Strictly bounded by `tx.vout.size()`.
  - `OP_ENUMERATE`: Strictly bounded by integer $N \in [0, 256]$ popped from the stack.
* **Auto-Pushing Loop Index**:
  On each iteration, the interpreter automatically pushes the current zero-based loop index ($i = 0, 1, \dots, \text{bound}-1$) onto the evaluation stack. In 95% of covenant loops, the body immediately consumes this index (e.g. `OP_OUTPUTVALUE` or `OP_UTXOVALUE`), eliminating index arithmetic overhead. If the index is not needed, the body opens with `OP_DROP` (1 byte).
* **Controlled Nesting ($N \le 2$) & Flat C++ Call Frame**:
  To enable expressive 2-dimensional algorithms (e.g., iterating across inputs and validating each against a set of outputs, or verifying an $M \times N$ matrix of signatures) while preventing combinatorial execution explosions, **loop nesting is strictly capped at depth $N = 2$ in consensus** (`SCRIPT_ERR_MAX_LOOP_DEPTH_EXCEEDED`).
  Because maximum nesting depth is fixed at 2, the worst-case iteration count across nested loops is mathematically capped at $256 \times 256 = 65,536$.
  The node interpreter maintains loop state in a fixed-size array on the C++ stack:
  ```cpp
  struct LoopFrame {
      uint32_t index;
      uint32_t bound;
      const uint8_t *pc_start;
      const uint8_t *pc_end;
  };
  LoopFrame loop_stack[2];
  uint8_t   loop_depth = 0; // Invariant: 0 <= loop_depth <= 2
  ```
  Zero dynamic heap allocations (`std::vector`), zero recursive function calls, and zero garbage collection overhead.
* **Multi-Level Early Exit (`depth OP_BREAK`)**:
  `OP_BREAK` pops a 128-bit integer `depth` from the evaluation stack ($1 \le \text{depth} \le \text{loop\_depth}$):
  - `OP_1 OP_BREAK`: Terminates the innermost loop, jumping past its corresponding `OP_ENDENUMERATE`.
  - `OP_2 OP_BREAK`: Unwinds both the inner and outer loops simultaneously in a single $O(1)$ jump past the outer `OP_ENDENUMERATE`.
  - If $\text{depth} < 1$ or $\text{depth} > \text{loop\_depth}$, script execution immediately aborts with `SCRIPT_ERR_INVALID_BREAK_DEPTH`.

#### 3.9.3. Static Precomputed Cost Budget (Zero Halting Problem)
Because every loop bound is either known from the transaction wire header (`nInputCount`, `nOutputCount`) or statically limited ($N \le 256$), the node computes the exact worst-case execution cost **statically in $O(\text{script\_size})$ before running a single opcode**:

$$\text{WorstCaseCost} = \sum_{\text{loops}} \left(\text{bound}_{\text{outer}} \times \left(\text{cost}(\text{outer\_body}) + \sum_{\text{inner}} \text{bound}_{\text{inner}} \times \text{cost}(\text{inner\_body})\right)\right) + \text{cost}(\text{linear\_code})$$

Consensus enforces the universal budget rule:
$$\mathbf{TotalCost} = \mathbf{WireBytes} + \sum_{\text{witnesses}} \mathbf{PrecomputedScriptCost} \le \mathbf{MAX\_TX\_COST}$$

If $\mathbf{TotalCost} > \mathbf{MAX\_TX\_COST}$, the transaction is discarded at the P2P network boundary without executing any script bytecode. Mempool DDoS is mathematically impossible.

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
| **09c**| `09c-compact-outputs.patch` | **NEEDS-EXTRACT** | Single-asset multi-branch outputs (42B/74B), explicit `BranchWitness` and `TokenMintWitness` in `src/primitives/transaction.h`. |
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
| **33** | `33-introspection-loops.patch` | **NEEDS-WRITE** | Introspection opcodes `0xc0–0xd9`, `OP_ENUMERATE` family, static precomputed budget. |
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

Because all consensus invariants (Header format, 45B/77B Single-Asset Multi-Branch Outputs, Variadic Spending Paths, BLAKE3, 128-bit VM, Introspection, Tail Subsidy) are permanently locked at Block 0, future protocol optimizations remain **strictly internal node implementations and network transport upgrades** that require **ZERO hardforks**:

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
* Incorporates native fields for single-asset multi-branch outputs, variadic spending paths, and Merklix proofs.

### 8.5. Architectural Exclusion of Double-Spend Proofs (BUIP135)
* **The Asymmetric DoS Vulnerability**: Double-Spend Proofs (DSPs) introduce an un-fee'd signature verification cascade. An attacker splitting 1 XPI into 100,000 dust outputs can broadcast 100,000 conflicting transactions, forcing every full node on the network to perform 200,000 cryptographic signature checks and gossip the proofs across the P2P topology without paying a single satoshi in fees.
* **Script & Covenant Incompatibility**: DSPs break down on stateful smart contracts and multi-branch guardrails, requiring complex whitelist heuristics that compromise protocol simplicity.
* **The Sound Alternative**: Lotus v2 adheres to pure Nakamoto first-seen policy: conflicting mempool spends are rejected in a single $O(1)$ hash table check ($<5\text{ ns}$ CPU cost, zero bandwidth, zero state bloat).
