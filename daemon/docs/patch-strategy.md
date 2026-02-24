# Lotus Daemon — Patch Strategy & Manifest

## Purpose

Single source of truth for all patches across all series. Tracks status, ordering,
what each patch does, which series it applies to, and what work remains.

**Status legend:**
- `DONE` — applies cleanly, correct, no further work needed
- `NEEDS-REBASE` — logically correct but context lines outdated; needs re-expressing against current base
- `NEEDS-WRITE` — patch does not yet exist; needs to be written from scratch
- `NEEDS-FIX` — patch exists but has known problems or placeholders
- `SKELETON` — stub exists; implementation not started
- `NO-OP` — patch is empty/trivial against current base (upstream already applied it)
- `DEFERRED` — intentionally not yet implemented; blocked on a decision or other patch

---

## V2 — New Lotus Chain

**Base:** bitcoin-abc `252182e957120652960c1f88ec96515c448b1204`
**Goal:** Launch a new Lotus chain from genesis with Chronik, NNG, adaptive issuance,
expanded opcode set, and O(n log n) mining. No UTXO snapshot; clean PoW start.
**Why this base:** Chronik is production-ready at this commit.

### V2 Patch Manifest

| # | File | Status | What it does |
|---|------|--------|--------------|
| 01 | `01-chain-identity.patch` | NEEDS-REBASE | Binary names (lotusd/lotus-cli), version strings, CMake project name |
| 02 | `02-currency-unit.patch` | NEEDS-REBASE | XPI denomination; 1 XPI = 10^4 satoshis; amount formatting |
| 03 | `03-xaddress.patch` | NEEDS-REBASE | XAddress encoding/decoding; replaces CashAddr; prefix needs updating from `lotus` → `xpi` (or final chosen value) |
| 04 | `04-daa-cleanup.patch` | NEEDS-REBASE | Remove Grasberg/EDA; keep only aserti3-2d DAA |
| 05 | `05-merkle.patch` | NEEDS-REBASE | IGUANA interleaved merkle tree for block structure |
| 06 | `06-nng-interface.patch` | NEEDS-REBASE | NNG pub/sub replacing ZeroMQ for block/tx notifications; adds `src/nng_interface/` |
| 06b | `06b-remove-zeromq.patch` | NEEDS-WRITE | Delete `src/zmq/`, ZeroMQ CMake option, ZeroMQ functional + unit tests; ZeroMQ was never removed |
| 07 | `07-intmath-log2.patch` | NEEDS-REBASE | Log2 fixed-point math (Turner algorithm); required by issuance patches |
| 08 | `08-issuance.patch` | DEFERRED | Old log2 issuance curve — **superseded by 22+23; remove from series when 22+23 confirmed stable** |
| 09 | `09-minerfund.patch` | N/A | Not applied; archived for reference only |
| 10 | `10-script-opcodes.patch` | NEEDS-REBASE | OP_MULPOW2 (0xb2), OP_RAWLEFTBITSHIFT (0xb3) and related new opcodes |
| 11 | `11-taproot.patch` | NEEDS-REBASE | Taproot implementation — needs review for new chain semantics |
| 12 | `12-chain-params.patch` | NEEDS-FIX | Network magic bytes, ports, primitives; genesis definition placeholder (nNonce=0); epoch activation times need updating |
| 13 | `13-genesis.patch` | NEEDS-FIX | Assume-valid constants — **placeholder; contains v1 mainnet values; replace with new chain genesis hash + chain work after mining** |
| 14 | `14-checkpoints.patch` | NEEDS-FIX | Checkpoint hashes — **currently has v1 values; must be cleared for new chain** |
| 15 | `15-fixed-seeds.patch` | NEEDS-WRITE | Hardcoded seed node IPs for new chain — v1 IPs currently; need new chain seed nodes |
| 16 | `16-seeder.patch` | NEEDS-REBASE | DNS seeder tool |
| 17 | `17-consensus-activation.patch` | NEEDS-REBASE | All named upgrade epochs (Exodus through 1st Kings) with activation times |
| 18 | `18-src-build.patch` | NEEDS-REBASE | src/CMakeLists.txt and sub-build-systems |
| 19 | `19-misc.patch` | NEEDS-REBASE | RPC, wallet, net, tests, util, policy, primitives (miscellaneous Lotus adaptations) |
| 20 | `20-qt-gui.patch` | NEEDS-REBASE | Qt GUI (BUILD_BITCOIN_QT=OFF by default) |
| 21 | `21-build-compat.patch` | NEEDS-REBASE | CMake 4.x + Boost 1.90 fixes for macOS arm64 |
| 22 | `22-boot-subsidy.patch` | NEEDS-REBASE | Boot subsidy: height-based step-halvings (10M XPI → 260 XPI floor, ~73-day half-life) |
| 23 | `23-tail-subsidy.patch` | NEEDS-REBASE | Tail emission: sqrt-adaptive stateful emission via nTailSubsidy consensus variable |
| 24 | `24-ifp-removal.patch` | NEEDS-REBASE | Disable IFP: enableMinerFund=false, coinbasePayoutAddresses cleared; mechanism preserved |
| 25-26 | `25-26-op-log-op-sqrt.patch` | NEEDS-REBASE | OP_LOG (0xbd) and OP_SQRT (0xbe) with full test suite |
| 27 | `27-op-mul.patch` | NEEDS-REBASE | OP_MUL (0x95) re-enabled; 63-bit signed multiply with overflow detection |
| 28 | `28-bigint-ops.patch` | NEEDS-REBASE | Big-integer opcodes (0xbf–0xc4): BIGADD/BIGSUB/BIGMUL/BIGMOD/BIGDIVMOD/BIGMULMOD; BIGMULMOD is the key primitive for Mitra |
| 29 | `29-nlogn-block-construction.patch` | DONE | O(n log n) `addTxs`; snapshot → package-stat accumulation → sort → DFS |
| 30 | `30-remove-chaintx-limit.patch` | DONE | Drop ancestor/descendant chain-tx limits from mempool |
| 31 | `31-mempool-cleanup.patch` | NO-OP | CTxMemPoolEntry accounting fields already removed upstream |
| — | `chronik-adapt.patch` | NEEDS-WRITE | Adapt Chronik API output to XAddress + XPI denomination; wire Lotus network constants into Chronik's Rust code |
| 32 | `32-mitra-tx.patch` | SKELETON | Mitra transaction format; see `daemon/docs/mitra-spec.md`; blocked on opcode slot resolution with patch 28 |

### V2 Open Decisions

| Decision | Status | Notes |
|----------|--------|-------|
| XAddress prefix for v2 | **DECIDED** — `xpi` (or similar) | V1 uses `lotus`; v2 prefix must differ to prevent address reuse across chains |
| Mine genesis nNonce | BLOCKED on launch readiness | Patch 12/13 have nNonce=0 placeholder |
| Remove patch 08 | PENDING | Remove once patches 22+23 confirmed stable and tested |
| Mitra opcode slots | OPEN | Patch 28 uses 0xbf–0xc4; Mitra needs adjacent slots; resolve before implementing 32 |
| Taproot in v2 | OPEN | Patch 11 imported from v1; needs review — does v2 want taproot at all? |

---

## V1 — Lotus Mainnet Archive

**Base:** eCash v0.24.11 `fa7a44f731a2dfe1587e572d9eb0e4bb7c73d79c` (static, never changes)
**Goal:** Build lotusd v10.4.10; sync the Lotus mainnet (2nd Samuel + Taproot active).
**Status:** All 42 patches apply cleanly. Chain stalled at ~927,381 since Dec 2024.

### V1 Patch Manifest

| # | File | Status | What it does |
|---|------|--------|--------------|
| 01 | `01-lotus-mainnet.patch` | DONE | Monolithic ~52K-line origin diff: full Bitcoin ABC → Lotus conversion including chain identity, XAddress, IGUANA merkle, NNG, opcodes, issuance, chain params, genesis |
| 02 | `02-cmake4-boost190-compat.patch` | DONE | CMake 4.x + Boost 1.90 build fixes |
| 03–42 | `03-judges-upgrade.patch` … `42-version-10.4.10.patch` | DONE | Incremental version bumps and upgrade epochs through v10.4.10 |
| 43 | `43-remove-zeromq.patch` | NEEDS-WRITE | ZeroMQ present but only disabled (BUILD_BITCOIN_ZMQ=OFF); needs full removal of `src/zmq/`, CMake option, and tests |
| — | `chronik-backport.patch` | DEFERRED | V1 predates Chronik; backport is large and low priority given mainnet is stalled |

---

## Ecash — Upstream PR Candidates (bitcoin-abc / eCash)

**Base:** bitcoin-abc `252182e957120652960c1f88ec96515c448b1204`
**Goal:** Clean patches reviewable by bitcoin-abc/eCash maintainers.

### Ecash Patch Manifest

| # | File | Status | What it does |
|---|------|--------|--------------|
| 29 | `29-nlogn-block-construction.patch` | DONE | O(n log n) `addTxs` for `src/node/miner.cpp` |
| 30 | `30-remove-chaintx-limit.patch` | DONE | Drop chain-tx ancestor limits |
| 31 | `31-mempool-cleanup.patch` | NO-OP | Already merged upstream |
| — | `nng-interface.patch` | NEEDS-WRITE | Port v2 NNG patch; upstream candidate to replace ZeroMQ |
| — | `remove-zeromq.patch` | NEEDS-WRITE | Port v2 ZeroMQ removal; pairs with NNG patch as a single PR |

---

## BCHN — Upstream PR Candidates (Bitcoin Cash Node)

**Base:** BCHN `v28.0.0` / `0bc23ac4c1365f34ed824e2b07e554ec06a5f5cd`
**Goal:** Clean patches reviewable by BCHN maintainers.

### BCHN Patch Manifest

| # | File | Status | What it does |
|---|------|--------|--------------|
| 29 | `29-nlogn-block-construction.patch` | DONE | O(n log n) `addTxs` for BCHN's `src/miner.cpp` (value semantics, `addTxs(int64_t)`) |
| 30 | `30-remove-chaintx-limit.patch` | DONE | Drop chain-tx ancestor limits |
| 31 | `31-mempool-cleanup.patch` | NO-OP | Already merged upstream |
| — | `nng-interface.patch` | NEEDS-WRITE | Port v2 NNG patch to BCHN API |
| — | `remove-zeromq.patch` | NEEDS-WRITE | Port v2 ZeroMQ removal to BCHN |

---

## Doged — Reference Only

**Base:** `doged-io/doged` `master` (~v0.4.0, Oct 2025) — direct clone, no patches
**Goal:** Reference implementation. Tobias Ruck (doged author) designed the Mitra
transaction format. Study doged for: Chronik improvements, Avalanche reference,
Mitra design, and logond framework context.

---

## Work Sequencing

Roughly the right order to tackle remaining work:

1. **Write `06b-remove-zeromq.patch`** for v2 (directly against 252182e9; no rebase needed)
2. **Port NNG + ZeroMQ removal to ecash and bchn** (upstream PR value is immediate)
3. **Write `43-remove-zeromq.patch`** for v1 (same removal, different base)
4. **Rebase v2 patches 01–28** onto 252182e9 (largest effort; unlocks building v2)
5. **Write `chronik-adapt.patch`** for v2 once 03-xaddress is rebased (confirm `xpi` prefix)
6. **Write `chronik-adapt.patch`** for v1 (XAddress / `lotus` prefix) — lower priority
7. **Mine genesis, update 12/13/14** — pre-launch only
8. **Implement Mitra (patch 32)** — resolve opcode conflicts first

---

## Key File Locations

| File | Purpose |
|------|---------|
| `daemon/bitcoin-abc-version` | Pinned bitcoin-abc base for v2, ecash |
| `daemon/ecash-version` | Pinned eCash v0.24.11 base for v1 (static) |
| `daemon/doged-version` | doged branch/tag to clone |
| `daemon/bchn-version` | BCHN pinned tag |
| `daemon/lotusd-version` | Current lotusd release tracked in v1 |
| `daemon/patches/v2/series` | Ordered patch list for v2 |
| `daemon/patches/v1/series` | Ordered patch list for v1 |
| `daemon/patches/ecash/` | Ecash upstream PR patches |
| `daemon/patches/bchn/` | BCHN upstream PR patches |
| `daemon/docs/mitra-spec.md` | Mitra transaction format spec |
| `daemon/docs/patch-strategy.md` | This file |
