# Staged Implementation Plan: Firedancer-Style Zero-Copy `CTransaction` & `CBlockIndex` Slab Pipeline (Base `ecash/` v1 Baseline)

**Target Baseline:** `ecash-optimizations-tip` (`8ea9ea122a`, the pure `v1` eCash optimization baseline before the `v2/` patch stack, so this work runs 100% independently in its own worktree and layers cleanly alongside the `ecash/` patches).

---

## Architecture & 4-Commit Staged Sequence (Pure `ecash/` v1 Baseline)

In `ecash-optimizations-tip` (`8ea9ea122a`), `CTransaction`, `CTxIn`, and `CTxOut` are pure `v1` eCash structs:
- `CTxOut` is `{ Amount nValue; CScript scriptPubKey; }` (`CScript` is `prevector<28, uint8_t>`, so P2PKH 25B and P2SH 23B outputs already do **0 heap allocations**).
- `CTxIn` is `{ COutPoint prevout; CScript scriptSig; uint32_t nSequence; }`.
- `CTransaction` is allocated via `MakeTransactionRef` (`std::make_shared<const CTransaction>`) and shared via `CTransactionRef` across P2P $\rightarrow$ `CTxMemPool` $\rightarrow$ `BlockAssembler` $\rightarrow$ `CCheckQueue` script workers $\rightarrow$ `ConnectBlock` $\rightarrow$ `Chronik`.

We implement the zero-copy slab pipeline in **4 small, self-contained atomic commits** on top of `ecash-optimizations-tip` (`8ea9ea122a`):

1. **`blockstorage: back BlockManager::m_block_index (BlockMap) with ChunkedSlabAllocator`**
2. **`primitives: add GlobalConcurrentSlabAllocator and wire MakeTransactionRef to slab arena`**
3. **`primitives: precompute m_serialize_size and PrecomputedTransactionData on CTransaction`**
4. **`primitives: inline small_vector<3> for vin/vout in CTransaction to eliminate vector heap allocations`**

Every commit must compile cleanly (`ninja bitcoind test_bitcoin bench_bitcoin`) and pass `test_bitcoin` before moving to the next commit.

---

### Commit 1: `blockstorage: back BlockManager::m_block_index (BlockMap) with ChunkedSlabAllocator`

#### Problem
In `src/node/blockstorage.h:72`:
```cpp
using BlockMap = std::unordered_map<BlockHash, CBlockIndex, BlockHasher>;
```
Every `CBlockIndex` header in the chain is allocated via an individual `::operator new` call inside `std::unordered_map`, scattering headers across heap pages and causing L2/TLB misses whenever `pindex->pprev` or `pindex->GetAncestor()` is traversed (e.g., `GetMedianTimePast()`, DAA/ASERT anchor walks, locator construction).

#### Files to Modify
- `src/node/blockstorage.h`
- `src/test/blockmanager_tests.cpp` (or `src/test/skiplist_tests.cpp`)

#### Exact Changes
1. In `src/node/blockstorage.h`:
   - Include `<support/allocators/chunked_slab.h>`.
   - Replace `using BlockMap = ...` with:
     ```cpp
     using BlockMap = std::unordered_map<
         BlockHash, CBlockIndex, BlockHasher, std::equal_to<BlockHash>,
         ChunkedSlabAllocator<std::pair<const BlockHash, CBlockIndex>, 16384>>;
     ```
2. Why this is 100% safe:
   - `std::unordered_map` only allocates single hash nodes (`n == 1`, served from `SlabArena::AllocateSlot` in 16,384-node contiguous chunks) and bucket pointer arrays (`n > 1`, forwarded by `ChunkedSlabAllocator` to aligned `::operator new`).
   - All `m_block_index` mutations occur under `cs_main` (or single-threaded `LoadBlockIndex`), and `SlabArena` never moves allocated slots, preserving 100% `CBlockIndex*` pointer stability.
3. Verification:
   - Run `test_bitcoin --run_test=blockmanager_tests,skiplist_tests`.

---

### Commit 2: `primitives: add GlobalConcurrentSlabAllocator and wire MakeTransactionRef to slab arena`

#### Problem
Every `MakeTransactionRef(...)` (`src/primitives/transaction.h`) calls `std::make_shared<const CTransaction>(...)`, hitting the global heap allocator for every transaction received over P2P, RPC, or disk. Unlike `mapTx` or `BlockMap` (which are guarded by a single mutex), `CTransactionRef` instances are created on P2P/RPC threads and their last `shared_ptr` reference may be dropped on validation, mempool, or Chronik threads.

#### Files to Modify
- `src/support/allocators/chunked_slab.h`
- `src/primitives/transaction.h`
- `src/test/mempool_tests.cpp`

#### Exact Changes
1. In `src/support/allocators/chunked_slab.h`, add `GlobalConcurrentSlabAllocator<T, std::size_t SlotsPerChunk = 16384>`:
   - Backed by a process-wide static singleton `ConcurrentSlabPool<SlotSize(), SlotAlign(), SlotsPerChunk>` constructed via placement-new in `alignas` static storage (intentionally never destroyed at process exit so static-destruction order during shutdown can never access a destroyed pool while late `CTransactionRef` globals destruct!).
   - Inside `ConcurrentSlabPool`:
     - Uses a `std::mutex m_mutex` guarding a `SlabArena m_arena{SlotSize, SlotAlign, SlotsPerChunk}`.
     - Provides `AllocateBatch(void **out, std::size_t count)` and `DeallocateBatch(void **in, std::size_t count)` under `std::lock_guard<std::mutex>`.
     - Uses a per-thread magazine (`struct ThreadMagazine { void *slots[64]; std::size_t count{0}; ~ThreadMagazine() { if (count) pool.DeallocateBatch(slots, count); } }`):
       - `allocate(1)`: if `mag.count == 0`, refill `32` slots via `pool.AllocateBatch(mag.slots, 32)`; return `mag.slots[--mag.count]`. (**Zero locks and zero atomics on the fast path!**)
       - `deallocate(p, 1)`: if `mag.count == 64`, flush `32` slots via `pool.DeallocateBatch(mag.slots + 32, 32)` and set `mag.count = 32`; store `mag.slots[mag.count++] = p`. (**Zero locks and zero atomics on the fast path!**)
       - For `n > 1`: forward to aligned `::operator new` / `::operator delete`.
   - Implement standard STL allocator traits (`value_type`, `rebind`, `is_always_equal = std::true_type`, `operator==` returning `true`).
2. In `src/primitives/transaction.h`:
   - Include `<support/allocators/chunked_slab.h>`.
   - Update `MakeTransactionRef`:
     ```cpp
     static inline CTransactionRef MakeTransactionRef() {
         return std::allocate_shared<const CTransaction>(
             GlobalConcurrentSlabAllocator<const CTransaction>{});
     }
     template <typename Tx>
     static inline CTransactionRef MakeTransactionRef(Tx &&txIn) {
         return std::allocate_shared<const CTransaction>(
             GlobalConcurrentSlabAllocator<const CTransaction>{},
             std::forward<Tx>(txIn));
     }
     ```
3. Add a multi-threaded unit test in `src/test/mempool_tests.cpp` that spawns 8 threads concurrently allocating `CTransactionRef` via `MakeTransactionRef`, passing them across queues to consumer threads that drop the `CTransactionRef`s, verifying slot reuse and zero leaks/races.

---

### Commit 3: `primitives: precompute m_serialize_size and PrecomputedTransactionData on CTransaction`

#### Problem
1. When a transaction enters the mempool (`AcceptToMemoryPool`), validation constructs `PrecomputedTransactionData txdata(tx)` (computing double-SHA256 `hashPrevouts`, `hashSequence`, `hashOutputs`). Later, when that same `CTransactionRef` is connected in a block (`ConnectBlock`) or re-checked, `PrecomputedTransactionData(tx)` is computed all over again.
2. Similarly, `GetTotalSize()` / `::GetSerializeSize(tx)` walks `vin` and `vout` with `SizeComputer` every time it is called on a `CTransaction`.

#### Files to Modify
- `src/primitives/transaction.h`
- `src/primitives/transaction.cpp`
- `src/validation.cpp`
- `src/test/transaction_tests.cpp`

#### Exact Changes
1. In `src/primitives/transaction.h` & `src/primitives/transaction.cpp`:
   - Move `struct PrecomputedTransactionData` above `class CTransaction` (or store `PrecomputedTransactionData m_precomputed` inside `CTransaction`).
   - Add `uint32_t m_serialize_size{0};` and `PrecomputedTransactionData m_precomputed;` to `CTransaction`, and compute both **once** inside `CTransaction` construction (`InitHashes()` / `ComputeHash()`) when `!vin.empty() || !vout.empty()`!
   - Wait — can `m_precomputed` (`hashPrevouts`, `hashSequence`, `hashOutputs`) and `m_serialize_size` be computed eagerly right inside `CTransaction`'s constructor alongside `hash` (`ComputeHash()`)?
     - **YES!** Because `CTransaction` is 100% immutable after construction, computing `m_precomputed` and `m_serialize_size` right in the `CTransaction` constructor means **zero atomics, zero lazy flags, and zero data races** — every field of `CTransaction` (`hash`, `m_serialize_size`, `m_precomputed.hashPrevouts`, `m_precomputed.hashSequence`, `m_precomputed.hashOutputs`) is `const` and ready the instant `MakeTransactionRef` returns!
   - Expose `const PrecomputedTransactionData &GetPrecomputedData() const { return m_precomputed; }` on `CTransaction`.
   - In `CTransaction::Serialize(Stream &s)`: when `Stream` is `SizeComputer` and `m_serialize_size > 0`, call `s.seek(m_serialize_size); return;` in $O(1)$!
   - Add a constructor `PrecomputedTransactionData(const CTransaction &tx) : PrecomputedTransactionData(tx.GetPrecomputedData()) {}` so **every existing caller** that writes `PrecomputedTransactionData txdata(tx);` automatically copies the 3 precomputed 32-byte hashes in $O(1)$ (`memcpy` of 96 bytes) instead of running 3 double-SHA256 passes over `vin` and `vout`!
2. In `src/validation.cpp`:
   - Where `PrecomputedTransactionData` is passed by `const PrecomputedTransactionData &` to `CScriptCheck` or `VerifyScript`, bind directly to `tx.GetPrecomputedData()`.

---

### Commit 4: `primitives: inline CScriptSig capacity for 1-pass zero-malloc CTxIn construction`

#### Problem
In `src/script/script.h:425`:
```cpp
using CScriptBase = prevector<28, uint8_t>;
```
While a 28-byte inline `prevector` fits `CTxOut::scriptPubKey` (`25` bytes for P2PKH, `23` bytes for P2SH), every standard P2PKH `CTxIn::scriptSig` is `100–107` bytes (`<65B Schnorr or 72B ECDSA sig> <33B pubkey>`). As a result, **every single `CTxIn` in every transaction spills `scriptSig` to `malloc`/`free`**!
Furthermore, we must NOT increase `CScriptBase` globally from `28` to `112` because `Coin` in the UTXO cache (`CCoinsViewCache`) stores `CTxOut::scriptPubKey` (`CScript`), and we want `Coin` in the UTXO cache to stay compact.

#### Files to Modify
- `src/primitives/transaction.h`
- `src/core_memusage.h`
- `src/test/transaction_tests.cpp`

#### Exact Changes
1. Check how `CTxIn` and `CTransaction` allocate `vin` and `vout` in `src/primitives/transaction.h`:
   - Measure allocation count and `bench_bitcoin` throughput (`ChainedTx`, `MempoolCheck`, `ConnectBlock` / `AssembleBlock`) before and after reserving / pooling `vin` and `vout` inside `CTransaction`.
2. Verify all unit tests in `test_bitcoin` pass.

---

## Isolated Worktree & Benchmark Execution Plan

1. **Create Dedicated Worktree at `ecash-optimizations-tip` (`8ea9ea122a`):**
   ```bash
   git -C /Users/shammah/repos/lotus-v2-optimizations/daemon/workspace-v2 \
     worktree add -b feat/zero-copy-slab-v1 /private/tmp/wt-zero-copy-slab ecash-optimizations-tip
   ```
   - **Strict Isolation Rule:** Only touch `/private/tmp/wt-zero-copy-slab` and `/private/tmp/build-zero-copy-slab`. Never touch `daemon/workspace-v2` or any other `/private/tmp/wt-*` worktree.
2. **Build Baseline & Save Benchmark Numbers:**
   ```bash
   cmake -GNinja -B /private/tmp/build-zero-copy-slab -S /private/tmp/wt-zero-copy-slab \
     -DCMAKE_BUILD_TYPE=Release \
     -DBUILD_BITCOIN_WALLET=ON \
     -DBUILD_BITCOIN_QT=OFF \
     -DBUILD_BITCOIN_ZMQ=OFF \
     -DBUILD_CHRONIK=OFF \
     -DENABLE_UPNP=OFF \
     -DENABLE_NATPMP=OFF
   ninja -C /private/tmp/build-zero-copy-slab bitcoind test_bitcoin bench_bitcoin
   ```
3. **Export Patches:**
   ```bash
   mkdir -p /private/tmp/zero-copy-slab-v1-patches
   git -C /private/tmp/wt-zero-copy-slab format-patch -4 HEAD -o /private/tmp/zero-copy-slab-v1-patches
   ```
   (Note: The Lotus `v2/` follow-up commits — caching `m_inputs_hash` and `const lotus::v2::Transaction &ToV2Transaction()` — will be layered after GPT Astra finishes rebasing the `v1` stack.)
