# Lotus V2 & eCash High-Throughput Architecture: How We Reached 102,815 TPS (84-Patch Handoff Guide)

## 1. Repository & Two-Layer Patch Stack Overview

- **Canonical Patch Repository:** `/Users/shammah/repos/lotus-v2-optimizations` (`HEAD = c4e63b24`)
- **Upstream Base Commit:** Bitcoin ABC `1fb7db17c176cdea8a2c60d887891589382ee4e3`
- **Active Build Workspace:** `/Users/shammah/repos/lotus-v2-optimizations/daemon/workspace-v2`
- **Total Patch Count:** **84 strictly atomic, zero-fuzz patches** split across two layers:
  1. **Layer 1 (`SERIES=ecash` — `daemon/patches/ecash/001` through `052`):**
     - **100% consensus-compatible** with eCash / Bitcoin ABC (80-byte headers, `CSHA256` txids/merkle roots, legacy transaction format).
     - Contains all consensus-neutral storage, mempool, P2P set reconciliation, parallel validation, RCU RPC, Avalanche batching, and Chronik threading optimizations.
  2. **Layer 2 (`SERIES=v2` — `daemon/patches/v2/001` through `032`):**
     - Includes `@include ../ecash/series` and layers Lotus V2 consensus and V2-specific optimizations on top:
       - **BLAKE3** SIMD tree/tagged hashing (`v2/005`–`006`),
       - **134-byte V2 headers** with committed `state_root` (Sparse Merkle Tree root of UTXO set), `outputs_root`, ASERT difficulty, and monetary state (`v2/007`–`008`, `013`),
       - **v7 transaction wire format** with 3-branch outputs and native BIP340 Schnorr witnesses (`v2/009`–`010`, `014`),
       - **`DiskStateStore` (`libmdbx` + flat `blk`/`rev` segments + 4-level 16-ary Jellyfish Merkle Tree subtree packing)** (`v2/011`, `027`, `029`, `032`),
       - **C17a deterministic fee-backed UTXO expiry** (`v2/030`) and **built-in decentralized share-pool coordinator** (`v2/031`).

---

## 2. Benchmark Progression to 102,815 TPS

All numbers below were measured on the 18-thread Apple Silicon test host via `test_bitcoin --run_test=lotus_v2_tests`, `bench_bitcoin`, and the 3-node loopback stress harness:

| Milestone / Optimization Stage | `DISK_STATE_COMMIT_FINALIZED_OVERLAY_TPS` | `CREATE_AND_CONNECT_BLOCK_2000TX_TPS` | Time per 2,000-Tx Block | Key Bottleneck Eliminated |
| :--- | :---: | :---: | :---: | :--- |
| **1. Initial V2 + LevelDB / Early MDBX Baseline** | `3,366 TPS` | `~14,500 TPS` | `~137.9 ms` | Per-node LevelDB/MDBX B+Tree writes & eager per-level BLAKE3 hashing on every coin insert/erase |
| **2. Rounds 1–5 (`ecash/001`–`037`, `v2/001`–`026`)** *(libmdbx + Merklix overlay + RCU snapshots + 16-shard TLS sigcache + MonadDB 16-shard SMT)* | `~18,400 TPS` | `~52,000 TPS` | `~38.5 ms` | $O(N \log N)$ `BlockAssembler` heap copies, global `cs_main` RPC stalls, serial Schnorr sig checks |
| **3. Rounds 6–9 (`ecash/038`–`042`, `v2/027`–`031`)** *(Lazy DiskStateStore digests, `ParseNodeFast`, 1-wave batch mempool accept, Firedancer pre-`cs_main` parallel tx hashing)* | `30,652` – `35,655 TPS` | `59,489` – `70,384 TPS` | `28.42` – `33.62 ms` | Intermediate SMT branch rehashing, multi-wave parent-child mempool stalls, under-lock SHA256/BLAKE3 |
| **4. Round 10: `v2/032` Alone** *(4-Level 16-ary Jellyfish Merkle Tree Subtree Packing in `DiskStateStore`)* | **`68,952.1 TPS`** *(~2.1x)* | **`92,087.9 TPS`** | `21.72 ms` | 4x reduction in MDBX `dbi_smt_nodes` keys/writes + zero-alloc L1 4-level subtree pack cache |
| **5. Round 10 Full Stack (`ecash/043`–`052` + `v2/032`)** *(Slab allocator + `CCoinsViewCache::Reserve` + fused 1-lookup `SpendCoins` + overlay `SequenceLocks` skip + 4-level JMT packing)* | **`65,579` – `67,565 TPS`** | **`92,035` – `102,815 TPS`** | **`19.45` – `21.73 ms`** | Eliminated 13 `CCoinsViewCache` rehashes/block, cut UTXO lookups in `ConnectBlock` by 3x, skipped redundant `SequenceLocks` |

### Additional Microbenchmark Highlights (`HEAD = c4e63b24`)
- **BLAKE3 Multi-Core Hashing (`BLAKE3_250B_TX_MC_HPS`):** `56.89M tx/sec` (`34.09 GB/s`)
- **Merklix Arena Insert (`TX_OVERLAY_ARENA_INSERT_TPS`):** `653,689` – `697,711 TPS`
- **Merklix Overlay Manager AddTx (`MERKLIX_OVERLAY_MGR_ADD_TX_TPS`):** `400,055` – `486,205 TPS`
- **Merklix Epoch Freeze (`MERKLIX_FREEZE_EPOCH_US`):** `21.9 ms` (`21,929.8 µs`)
- **$\text{GF}(2^{64})$ Syndrome Accumulation (`GF64_SYNDROME_ACCUM_MC_TPS`):** `745.6M tx/sec`
- **$\text{GF}(2^{64})$ Degree-2 BCH Root Solver (`GF64_BCH_DEG2_SOLVE_MC_ROOTS_PS`):** `41.34M roots/sec`
- **Multi-Core Script + Schnorr Verification (`VERIFY_SCRIPT_SIG_MC_TPS`):** `578,676` – `598,878 TPS`

---

## 3. Core Architectural Choices & Why They Work

### A. Storage Engine: `libmdbx` + 4-Level (16-ary) Jellyfish Merkle Tree Subtree Packing
1. **Why We Replaced LevelDB with `libmdbx` (`ecash/003`–`004`, `v2/011`):**
   - LevelDB's LSM-tree compaction causes unpredictable latency spikes and read amplification on random 32-byte UTXO/SMT keys.
   - `libmdbx` (`MDBX_WRITEMAP | MDBX_LIFORECLAIM | MDBX_UTTERLY_NOSYNC`) maps the B+Tree directly into virtual memory, giving zero-copy `std::string_view` reads (`RawGetView`) and deterministic single-writer MVCC transactions without reader locks.
   - Block bodies (`blk*.dat`) and undo data (`rev*.dat`) are stored in append-only flat segment files via `pread`/`pwrite`, keeping the `libmdbx` B+Tree compact and in RAM.
2. **Bit-Reversed Prefix Key Layout (`v2/011`, `v2/027`):**
   - In `DiskStateStore` (`src/lotus_v2/disk_state.cpp`), SMT node keys are stored as `'N' || ReverseByte(prefix[0..31]) || uint16_le(depth)` so tree bit `depth % 8 == 0` sits at MSB `0x80`. Deep SMT ancestors that share a logical bit prefix also share a lexicographic byte prefix inside 4 KB `libmdbx` B+Tree pages.
3. **Lazy In-Transaction Node Cache (`v2/027`) & `EraseAt` Sibling Read Elimination (`v2/029`):**
   - During a block commit (`CommitFinalizedOverlay`), `InsertAt` and `EraseAt` mutate an in-memory `unordered_map<Path, CachedNode, PathHash> node_cache` with `SetBranchLazy` (marking `digest_dirty = true` without calling BLAKE3 `UtxoNode` on every coin mutation).
   - `EnsureBranchDigests()` computes each modified internal branch's BLAKE3 digest **once** bottom-up right before `FlushNodes()`.
4. **4-Level (16-ary) Jellyfish Merkle Tree (JMT) Subtree Value Packing (`v2/032`):**
   - **Problem:** A binary Sparse Merkle Tree has up to 256 levels. Storing every binary depth `d` as its own separate MDBX key/value in `dbi_smt_nodes` caused 4–8 separate B+Tree page lookups and writes per leaf path.
   - **Solution (`src/lotus_v2/disk_state.cpp`):** We group every **4 binary tree levels** (`anchor_depth = depth & ~3u`, relative depth `rel_depth = depth & 3u` $\in \{0, 1, 2, 3\}$) into a **16-ary Jellyfish Merkle Tree (JMT) subtree pack** containing up to $1 + 2 + 4 + 8 = 15$ binary nodes (`slot = ((1u << rel_depth) - 1u) + rel_bits` $\in [0..14]$) under a single 34-byte anchor key in `dbi_smt_nodes`:
     $$\text{Record} = \texttt{'J'} \;\|\; \texttt{uint16\_le(present\_mask)} \;\|\; \big[\texttt{uint32\_le(len)} \;\|\; \texttt{node\_bytes}\big]_{\text{slot} \in \text{present\_mask}}$$
   - **Consensus Invariance:** On-disk packing is 100% transparent to consensus—`UtxoNode(depth, left, right)` still computes the exact same binary BLAKE3 hashes, so `StateRoot` and `CoinProof` are bit-for-bit unchanged.
   - **L1 Subtree Pack Cache & Write Coalescing:** Walking 4 binary levels (`d, d+1, d+2, d+3`) performs **1 `mdbx_get`** (at `d & ~3u`) and serves the next 3 levels from `cached_jmt_views` in L1 cache with zero allocations. On commit, all dirty nodes within a 4-level subtree coalesce into a single `mdbx_put`.

---

### B. Speculative Mempool Overlay, Merklix Epochs & Set Reconciliation (`ecash/005`–`010`, `022`–`025`, `035`, `038`, `040`)
1. **How Merklix Epochs & Set Reconciliation Work Together:**
   - Rather than rebuilding a block template from scratch on `getblocktemplate` or shipping megabytes of raw txids between peers, every node maintains a **Persistent Merklix Overlay Arena** (`src/lotus_v2/mempool_overlay.cpp`) anchored at the current chain tip.
   - Incoming transactions enter a lock-free/deferred pending buffer (`ecash/038`) and are periodically frozen into a **deterministic Epoch** (`FreezeEpoch` in ~21.9 ms).
   - **$\text{GF}(2^{64})$ Algebraic Sketches (`ecash/006`, `010`, `022`, `035`):**
     - Each Merklix bucket/subtree maintains XOR/algebraic power-sum syndromes $(S_1, S_3, S_5)$ in $\text{GF}(2^{64})$ over key-salted 64-bit SipHash short IDs (`short_id`), accelerated via hardware carry-less multiplication (`_mm_clmulepi64_si128` on x86_64 / `vmull_p64` on ARM64 NEON).
     - When two peers compare an epoch root:
       1. If their root hashes match, they agree on the exact transaction set in $O(1)$.
       2. If a bucket differs by $\le 2$ transactions, the receiver solves the quadratic syndrome polynomial $x^2 + S_1 x + (S_1^2 + S_3 / S_1) = 0$ in $\text{GF}(2^{64})$ in ~25 nanoseconds (**Mysticeti 1-RTT Optimistic Fast Path**, `ecash/023`) without even descending the tree!
       3. For larger differences, $D=3$ (8-way) sub-bucket summaries (`ecash/022`) pinpoint the exact missing `short_id`s in 1–2 RTTs.
2. **$O(1)$ Block Assembly & Speculative UTXO Cut-Through (`ecash/007`–`008`, `040`, `v2/017`, `027`):**
   - `CTxMemPool` maintains a speculative `MempoolOverlayLayer` with a flat open-addressed linear-probing **Cut-Through Table** (`ecash/040`): if Tx A creates output $O_1$ and Tx B spends $O_1$ in the same block/epoch, $O_1$ is cut through in memory so `DiskStateStore` only ever touches net-erased pre-block UTXOs and net-inserted unspent outputs.
   - `BlockAssembler::CreateNewBlock` reads the pre-sorted transactions and pre-computed `StateRoot` directly from the frozen Merklix overlay in **$O(1)$** (`< 1 ms`).

---

### C. Why We Explicitly Dropped $\text{GF}(2^8)$ Cauchy Reed-Solomon (`Turbine`) Shredding
During Round 10 planning, we evaluated adding Solana-style $\text{GF}(2^8)$ Cauchy Reed-Solomon (`txshred` / `blkshred`) erasure coding and **explicitly dropped it**:
1. **Transport Mismatch (Reliable TCP vs. Unreliable UDP):** Solana's Turbine uses $\text{GF}(2^8)$ Reed-Solomon shreds because it streams blocks over raw **UDP** where individual 1.2 KB packets are routinely dropped. Lotus V2 and eCash run over **TCP** alongside **Merklix Set Reconciliation** + **`MinedHeader` Compact Relay** (`ecash/009`, `033`), where peers already hold >99% of transactions in their mempool overlay and only transmit a 134-byte `MinedHeader` + short-ID sketch delta.
2. **Erasure-Coding Poisoning / Computational DDoS Vector:** On a permissionless P2P network without a single slot-scheduled leader signing every shred, a Merkle root alone only proves internal consistency with whatever tree an anonymous sender constructed—not that the parity shreds are valid Reed-Solomon linear combinations of honest data shreds. Adding stake-bound originator signatures and full-tree reconstruction checks over TCP adds complexity and CPU overhead with zero throughput benefit over `MinedHeader` + Merklix set reconciliation.

---

### D. Mempool Ingestion & Memory Layout (`ecash/024`, `027`, `032`, `039`, `042`, `043`)
1. **Firedancer-Style Pre-`cs_main` Parallel Transaction Pipeline (`ecash/032`, `042`, `v2/028`):**
   - Before acquiring `cs_main`, worker threads decode raw hex transactions in parallel (`ecash/032`), warm `GetId()`/`GetHash()`, run context-free `CheckRegularTransaction`, and precompute BIP143/V2 sighash midstates (`ecash/042`), using a stack-allocated fast path (`v2/028`) that eliminates heap allocations on transactions with $\le 8$ inputs/outputs.
2. **One-Wave Chained Batch `AcceptToMemoryPool` (`ecash/039`, `v2/029`):**
   - Resolves in-batch parent-child transaction chains in a single pass using an in-batch output lookup map (`PeekCoin`) and $O(1)$ parent `txiter` linking, eliminating multi-wave retry loops on topologies with chained spends.
3. **TigerBeetle Portable `ChunkedSlabAllocator` (`ecash/043`):**
   - Replaces per-node `::operator new` heap allocations in `CTxMemPool::mapTx` (`boost::multi_index_container`) and `CTxMemPool::mapNextTx` (`indirectmap`) with [`src/support/allocators/chunked_slab.h`](file:///Users/shammah/repos/lotus-v2-optimizations/daemon/workspace-v2/src/support/allocators/chunked_slab.h) (`16,384` slots/chunk + $O(1)$ intrusive freelist), eliminating allocator contention and pointer-chasing L3 cache misses under high mempool churn.

---

### E. `ConnectBlock` & Signature Validation (`ecash/018`–`020`, `026`, `050`–`052`, `v2/025`–`026`)
1. **`CCoinsViewCache::Reserve` Pre-Allocation (`ecash/050`):**
   - Pre-reserves `view.Reserve(block.vtx.size() * 4)` in `ConnectBlock` and `cacheCoins.reserve(cacheCoins.size() + cursor.GetDirtyCount())` in `CCoinsViewCache::BatchWrite`, eliminating **13 full `unordered_map` bucket rehashes** per 2,000-tx block.
2. **Fused Single-Lookup `SpendCoins` + `CheckTxInputsFromSpentCoins` (`ecash/051`):**
   - Previously, `ConnectBlock` hashed and looked up every `txin.prevout` in `CCoinsViewCache` **3 separate times** (`CheckTxInputs`, `prevheights`, and `SpendCoins`).
   - Now `ConnectBlock` calls `view.SpendCoin(txin.prevout, &txundo.vprevout[j])` **once** per input, then validates input maturities/amounts/fees (`CheckTxInputsFromSpentCoins`) and reads `prevheights[j]` directly from the contiguous `txundo.vprevout` vector in L1 cache—cutting UTXO hash table lookups in `ConnectBlock` by **3x**.
3. **Anchored Speculative Overlay Hit in `ConnectBlock` (`ecash/008`, `052`, `v2/025`):**
   - When an incoming block's transactions match the speculative mempool overlay anchored at `pindex->pprev`:
     - Script/signature checks are satisfied in $O(1)$ from the pre-validated overlay (`!prevalidated_overlay_sigchecks.empty()`),
     - Redundant `prevheights` + BIP68 `SequenceLocks` re-evaluations are skipped (`ecash/052`), and
     - Redundant BIP30 disk lookups are skipped on height-committed V2 coinbases (`v2/025`).
4. **16-Shard TLS `SignatureCache` & `BatchSigCollector` (`ecash/018`–`019`):**
   - Cache misses during parallel script verification are collected into `lotus::v2::BatchSigCollector` and verified via multi-scalar Schnorr batch verification with automatic `FirstFailingIndex()` binary-search fallback on invalid signatures.

---

### F. Avalanche, P2P, Chronik & RPC Concurrency (`ecash/013`–`014`, `044`–`049`)
1. **Avalanche Batch Schnorr Verification & Lock-Free `Proof::verify` (`ecash/044`–`047`):**
   - `ecash/044`: Hoists `getStakeCommitment()` out of the per-stake verification loop in `Proof::verify`.
   - `ecash/045`: Batch-verifies all stake + master Schnorr signatures in `Proof::verify` and `Delegation::verify` via `BatchSigCollector`.
   - `ecash/046`: Runs context-free `Proof::verify` **outside** `cs_main` in `PeerManager::registerProofWithState`, holding `cs_main` only for the fast `CoinsTip()` UTXO lookup (`Proof::verifyUtxos`).
   - `ecash/047`: Coalesces incoming `NetMsgType::AVARESPONSE` bursts in `PeerManagerImpl::ProcessMessages` (`ProcessAvaResponseBatch`) and batch-verifies peer vote Schnorr signatures in a single `BatchSigCollector::VerifyAll()` call.
2. **Chronik Lock-Free `entry_time` & Dedicated Async Worker Queue (`ecash/048`–`049`):**
   - `ecash/048`: Captures `entry_time` synchronously in `ValidationSignals` and passes it directly to `ChronikValidationInterface::TransactionAddedToMempool`, eliminating 1,000 `m_node.mempool->info(txid)` `LOCK(mempool.cs)` acquisitions per batch.
   - `ecash/049`: Offloads `ChronikValidationInterface` mempool callbacks onto a dedicated background worker thread + bounded FIFO queue (`m_worker`) with a synchronization barrier (`FlushWorkerQueue`) before block/finalization events so `-chronik=1` never stalls the shared `ValidationSignals` thread.
3. **Boost.Asio Coroutine HTTP RPC + Lock-Free RCU Snapshots (`ecash/013`–`014`, `021`, `037`):**
   - Read-only RPCs (`getblockchaininfo`, `getmempoolinfo`, `getrawmempool`, `getblocktemplate`) read an atomic `std::shared_ptr<const ChainAndMempoolSnapshot>` published on tip/mempool updates with **zero `cs_main` or `mempool.cs` locks**.

---

## 4. Index of Companion Documentation Files

If a fresh agent needs deeper background on a specific subsystem, point it to:
1. **This Master Handoff Guide:**
   - `/Users/shammah/repos/lotus-v2-optimizations/daemon/docs/lotus-v2-100k-tps-architecture-and-optimizations.md`
   - `/private/tmp/lotus-v2-repo/docs/plans/lotus-v2-100k-tps-architecture-and-optimizations.md`
2. **Round 10 5-Subagent Atomic Patch Plan (`ecash/043`–`052` + `v2/032`):**
   - `/private/tmp/lotus-v2-repo/docs/plans/lotus-v2-round10-four-subagents-plan.md`
3. **Round 9 Parallel Optimization Plan (`ecash/038`–`042` + `v2/027`–`029`):**
   - `/private/tmp/lotus-v2-repo/docs/plans/lotus-v2-and-ecash-round9-parallel-plan.md`
4. **Merklix Preconsensus, Epochs & Speculative Mempool Overlays Deep Dive:**
   - `/private/tmp/lotus-v2-repo/docs/plans/lotus-v2-bulk-preconsensus-and-mempool-overlays.md`
5. **Coroutine HTTP RPC & Lock-Free RCU Snapshots Design:**
   - `/private/tmp/lotus-v2-repo/docs/plans/lotus-v2-rpc-coroutines-and-lockfree-snapshots.md`
6. **C17a Deterministic Fee-Backed UTXO Expiry & Cleaning Crew (`v2/030`):**
   - `/private/tmp/lotus-v2-repo/docs/plans/lotus-v2-utxo-expiry-and-cleaning-crew.md`
7. **Canonical Patch Series Manifests:**
   - Layer 1 (`ecash/001`–`052`): `/Users/shammah/repos/lotus-v2-optimizations/daemon/patches/ecash/series`
   - Layer 2 (`v2/001`–`032`): `/Users/shammah/repos/lotus-v2-optimizations/daemon/patches/v2/series`
