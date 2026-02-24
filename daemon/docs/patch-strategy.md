# Lotus Daemon — Patch Strategy & Manifest

## Purpose

Single source of truth for all patches across all series. Tracks status, ordering,
what each patch does, which series it applies to, and what work remains.

**Status legend:**
- `DONE` — applies cleanly, correct, no further work needed
- `NEEDS-REBASE` — logically correct but context lines outdated; re-express against current base
- `NEEDS-WRITE` — patch does not yet exist; write from scratch
- `NEEDS-FIX` — patch exists but has known placeholders or errors
- `NEEDS-EXTRACT` — change exists in a larger patch; pull out into its own named patch
- `SKELETON` — stub exists; implementation not started
- `NO-OP` — trivially empty against current base (upstream already applied it)
- `DEFERRED` — intentionally not yet done; blocked on a decision or another patch

---

## Shared Slot Convention

**Patches 01–03 are reserved for chain-agnostic mining improvements across all series.**
The same slot numbers are used in v1, v2, ecash, and bchn — the patch content differs
slightly per daemon API but the purpose is identical.

**Patch 04** is reserved for the issuance compatibility flag (v1 and v2 only).

**Patches 10–11** are reserved for NNG and ZeroMQ removal in ecash and bchn.

This makes it easy to see at a glance which improvements have been ported where.

---

## V2 — New Lotus Chain (primary goal)

**Base:** bitcoin-abc `252182e957120652960c1f88ec96515c448b1204`
**Goal:** Launch a new Lotus chain from genesis: Chronik indexer, NNG pub/sub, adaptive
issuance, expanded opcode set, dual-txid, Mitra transaction format, O(n log n) mining.
No UTXO snapshot — clean PoW start from genesis.

**Design principle — no future hardforks:**
V2 is designed to be published once and work forever, like Bitcoin does. All features
are active from block 0. There are no named upgrade epochs, no mandatory activation
heights, no "coming in the next fork" promises. Users and developers can count on the
protocol being stable. The v1 upgrade patches (Exodus, Ruth, Samuel, Kings, etc.) were
largely housekeeping increments with no real feature additions — that whole machinery
is dropped in v2. Everything ships complete at genesis.

**Why this bitcoin-abc base:** Chronik is production-ready here. Chronik is the indexer
we need (Electrum-compatible API, Rust-based). Without it we'd have to backport it —
a much larger effort than rebasing our existing patches.

### V2 Patch Manifest

| Slot | File | Status | What it does |
|------|------|--------|--------------|
| 01 | `01-nlogn-block-construction.patch` | DONE | O(n log n) `addTxs`: snapshot → package-stat accumulation → sort → DFS |
| 02 | `02-remove-chaintx-limit.patch` | DONE | Drop ancestor/descendant chain-tx limits from mempool |
| 03 | `03-mempool-cleanup.patch` | NO-OP | CTxMemPoolEntry accounting fields already removed upstream in 252182e9 |
| 04 | `04-issuance-compat.patch` | NEEDS-WRITE | Runtime `-issuance=ecash` flag; Lotus issuance is default; eCash/Bitcoin halving when flag set; allows eCash test suite to run unmodified without changing coinbase amount checks |
| 05 | `05-chain-identity.patch` | NEEDS-REBASE | Binary names (lotusd/lotus-cli), version strings, CMake project name |
| 06 | `06-currency-unit.patch` | NEEDS-REBASE | XPI denomination; 1 XPI = 10^4 satoshis; amount formatting throughout |
| 07 | `07-xaddress.patch` | NEEDS-REBASE | XAddress encoding/decoding; replaces CashAddr; v2 prefix = `xpi` (v1 used `lotus`) |
| 08 | `08-daa-cleanup.patch` | NEEDS-REBASE | Remove Grasberg/EDA; keep only aserti3-2d DAA |
| 08b | `08b-decouple-avalanche.patch` | NEEDS-WRITE | Decouple Avalanche from block consensus: remove chain-tip finalization hooks in `src/net_processing.cpp`, remove Avalanche from block validity checks. **Do NOT remove the Avalanche code itself.** It stays in the codebase for soft parameter voting (fee preferences, mempool policy, network parameter governance). Avalanche as a finalization layer is incompatible with the σₜ security model; as a gossip/voting layer it's fine. |
| 08c | `08c-blocktime.patch` | NEEDS-EXTRACT | Set `nPowTargetSpacing = 2 * 60` (2 minutes). **The commit already exists in the v1 lotusd repo — extract it.** Find the commit with `git log --all --oneline -- src/chainparams.cpp` in workspace-v1 and isolate the `nPowTargetSpacing` change. V2 uses the same value; apply the same extracted patch. **Downstream effects:** (1) boot subsidy step heights in patch 26 must be 5× larger to hit the same wall-clock half-life (720 blocks/day at 2 min vs 144 at 10 min). |
| 09 | `09-merkle.patch` | NEEDS-REBASE | IGUANA interleaved merkle tree; fixes the CVE-2012-2459 variant merkle tree vulnerability; implements MerklixHash (bitwise trie + SHA256 overlay) per the 2018 Vermorel/Séchet/Chancellor/Cox paper |
| 10 | `10-nng-interface.patch` | NEEDS-REBASE | NNG pub/sub replacing ZeroMQ; adds `src/nng_interface/`; Chronik stays separate |
| 11 | `11-remove-zeromq.patch` | NEEDS-WRITE | Delete `src/zmq/`, ZeroMQ CMake option, ZeroMQ functional + unit tests; was never removed |
| 12 | `12-issuance-OLD.patch` | DEFERRED | Old log2 issuance curve — **superseded by 26+27; remove from series once those confirmed stable** |
| 13 | *(minerfund — not applied)* | N/A | Archived for reference only |
| 14 | `14-script-opcodes.patch` | NEEDS-REBASE | OP_MULPOW2 (0xb2), OP_RAWLEFTBITSHIFT (0xb3) and related new opcodes |
| 15 | `15-taproot.patch` | NEEDS-REBASE | Taproot — **open question: does v2 want taproot? review before rebasing** |
| 16 | `16-chain-params.patch` | NEEDS-FIX | Network magic, ports, primitives; genesis nNonce=0 placeholder; epoch times need updating |
| 17 | `17-genesis.patch` | NEEDS-FIX | Assume-valid constants — placeholder with v1 mainnet values; replace after genesis is mined |
| 18 | `18-checkpoints.patch` | NEEDS-FIX | Checkpoints — currently has v1 values; must be cleared for new chain |
| 19 | `19-fixed-seeds.patch` | NEEDS-WRITE | Seed node IPs for new chain (v1 IPs currently; need new seed nodes) |
| 20 | `20-seeder.patch` | NEEDS-REBASE | DNS seeder tool |
| 21 | `21-consensus-activation.patch` | NEEDS-REVIEW | V1 named upgrade epochs (Exodus through 1st Kings). **V2 activates everything at block 0 — no epoch infrastructure needed.** This patch likely should be dropped from v2 entirely or replaced with a single "all features active at genesis" config. Keep in v1 series only. |
| 22 | `22-src-build.patch` | NEEDS-REBASE | src/CMakeLists.txt and sub-build-systems |
| 23 | `23-misc.patch` | NEEDS-REBASE+EXTRACT | RPC, wallet, net, tests, util, policy, primitives. **Contains several things that need their own patches — see below** |
| 24 | `24-qt-gui.patch` | NEEDS-REBASE | Qt GUI (BUILD_BITCOIN_QT=OFF by default) |
| 25 | `25-build-compat.patch` | NEEDS-REBASE | CMake 4.x + Boost 1.90 fixes for macOS arm64 |
| 26 | `26-boot-subsidy.patch` | NEEDS-REBASE | Boot subsidy: height-based step-halvings (10M XPI → 260 XPI floor, ~73-day half-life) |
| 27 | `27-tail-subsidy.patch` | NEEDS-REBASE | Tail emission: sqrt-adaptive stateful emission via nTailSubsidy consensus variable |
| 28 | `28-ifp-removal.patch` | NEEDS-REBASE | Disable IFP: enableMinerFund=false, coinbasePayoutAddresses cleared |
| 29 | `29-op-log-op-sqrt.patch` | NEEDS-REBASE | OP_LOG (0xbd) and OP_SQRT (0xbe) with full test suite |
| 30 | `30-op-mul.patch` | NEEDS-REBASE | OP_MUL (0x95) re-enabled; 63-bit signed multiply with overflow detection |
| 31 | `31-bigint-ops.patch` | NEEDS-REBASE | Big-integer opcodes (0xbf–0xc4): BIGADD/BIGSUB/BIGMUL/BIGMOD/BIGDIVMOD/BIGMULMOD |
| 32 | `32-chronik-adapt.patch` | NEEDS-WRITE | Adapt Chronik API output to XAddress (xpi prefix) + XPI denomination |
| 33 | `33-mitra-tx.patch` | SKELETON | Mitra tx format; see `daemon/docs/mitra-spec.md`; blocked on opcode slot resolution |

### Things currently buried in `23-misc.patch` that need extraction

These were originally separate patches in v1 but got merged into the misc catch-all.
Each needs to be extracted as its own named patch during the rebase:

| Future slot | What it is | Notes |
|-------------|------------|-------|
| Between 09 and 10 | **Block header format changes** | Changes to `CBlockHeader` struct; related to IGUANA; may overlap with patch 09 |
| After 07 | **Dual TXID / merklix input tree** | `txid` = new hash via merklix tree over inputs/outputs; `txhash` = legacy serialization; block merkle commits to both; enables covenants; Mitra builds on top |
| After 14 | **64-bit script fix** | 64-bit integer support in OP_DIV and other arithmetic ops; bitwise operator fixes; was a dedicated patch originally, may have been rolled into the monolithic v1 patch |

### V2 Open Decisions

| Decision | Status | Notes |
|----------|--------|-------|
| XAddress prefix | **DECIDED** — `xpi` | V1 uses `lotus`; v2 uses `xpi` to prevent address reuse across chains |
| Avalanche in v2 | **DECIDED** — decouple from consensus; keep for soft voting | See below; Avalanche stays in codebase for fee/parameter governance |
| V2 epoch activation | **DECIDED** — drop patch 21 | V2 activates everything at block 0; no epoch infrastructure needed; keep 21 in v1 only |
| Taproot in v2 | OPEN | Needs review before patch 15 is rebased; may or may not belong in v2 |
| Mine genesis nNonce | BLOCKED on launch readiness | Patches 16/17 have placeholder nNonce=0 |
| Remove patch 12 | PENDING | Remove `12-issuance-OLD.patch` once 26+27 confirmed stable |
| Mitra opcode slots | OPEN | Patch 31 uses 0xbf–0xc4; Mitra needs adjacent slots; resolve before implementing 33 |

### Avalanche — DECIDED: decouple from consensus, keep for soft voting

**The core problem with Avalanche as a consensus mechanism:**
Two consensus mechanisms with no defined tie-breaker. PoW miners can build a valid chain
that Avalanche validators reject. eCash's answer is "Avalanche wins" — which means it's
no longer a PoW chain in any meaningful sense. The σₜ security signal from the issuance
papers breaks immediately: security expenditure is now split between hashwork (visible)
and stake (opaque), and the adaptive issuance math assumes σₜ is the sole signal.

**What Avalanche is actually good for (soft coordination):**
There is a real distinction between hard consensus and soft coordination:
- **Hard consensus** — block validity, chain tip selection, finality. PoW wins unconditionally.
- **Soft coordination** — advisory signals like preferred minimum fee rates, mempool policy
  preferences, or network parameter votes. No PoW implication; nodes can ignore it and
  remain fully valid. No need to reimplement a new gossip protocol when Avalanche already
  exists in the codebase.

**Action:**
- Add `08b-decouple-avalanche.patch` after `08-daa-cleanup` in v2 series (NEEDS-WRITE)
- Remove Avalanche from: chain-tip finalization hooks in `src/net_processing.cpp`,
  block validity checks that require Avalanche quorum
- **Keep:** `src/avalanche/` directory, CMake option, init startup — Avalanche remains
  functional as a gossip/voting protocol for soft parameter coordination (fee preferences,
  mempool policy, network parameter governance)
- Avalanche votes have no authority over which block is valid or which chain tip wins

---

## V1 — Lotus Mainnet Archive

**Base:** eCash v0.24.11 `fa7a44f731a2dfe1587e572d9eb0e4bb7c73d79c` (static)
**Goal:** Build lotusd v10.4.10; sync the Lotus mainnet.

### V1 Patch Manifest

| Slot | File | Status | What it does |
|------|------|--------|--------------|
| 01 | `01-nlogn-block-construction.patch` | NEEDS-WRITE | Port mining patch to eCash v0.24.11 API (`addPackageTxs`, old `CTxMemPool::txiter`) |
| 02 | `02-remove-chaintx-limit.patch` | NEEDS-WRITE | Port to v0.24.11 API |
| 03 | `03-mempool-cleanup.patch` | NEEDS-WRITE | Port to v0.24.11 API (accounting fields still present at this base) |
| 04 | `04-issuance-compat.patch` | NEEDS-WRITE | Runtime `-issuance=ecash` flag (same concept as v2; log2 Lotus issuance is default) |
| 05+ | `05-lotus-mainnet.patch` (was 01) | DONE | Monolithic origin diff: full Bitcoin ABC → Lotus including all v1 features |
| … | `06-cmake4-boost190-compat.patch` … `46-version-10.4.10.patch` | DONE | Incremental version bumps and named upgrade epochs (Exodus through 1st Kings). **Most of these contain no new features** — they were housekeeping: version strings, activation heights, build fixes. The feature content is almost entirely in the original monolithic `05-lotus-mainnet.patch`. |
| 08c | `08c-blocktime.patch` | NEEDS-EXTRACT | 2-minute blocks. **Extract from v1 lotusd git log** — this commit exists; find it in `LotusiaStewardship/lotusd` and isolate the `nPowTargetSpacing` change. |
| 47 | `47-remove-zeromq.patch` | NEEDS-WRITE | ZeroMQ present but only disabled (BUILD_BITCOIN_ZMQ=OFF); remove `src/zmq/`, tests |
| — | `chronik-backport.patch` | DEFERRED | V1 predates Chronik; large effort; low priority — v1 is live and running, chronik backport is not needed for it to function |

*Note: v1 slot 05+ uses renumbered names to accommodate 01-04 being added at the front.*

---

## Ecash — Upstream PR Candidates

**Base:** bitcoin-abc `252182e957120652960c1f88ec96515c448b1204`

| Slot | File | Status | What it does |
|------|------|--------|--------------|
| 01 | `01-nlogn-block-construction.patch` | DONE | O(n log n) `addTxs` for `src/node/miner.cpp` |
| 02 | `02-remove-chaintx-limit.patch` | DONE | Drop chain-tx ancestor limits |
| 03 | `03-mempool-cleanup.patch` | NO-OP | Already merged upstream |
| 10 | `10-nng-interface.patch` | NEEDS-WRITE | Port NNG interface from v2; upstream PR to replace ZeroMQ in eCash |
| 11 | `11-remove-zeromq.patch` | NEEDS-WRITE | Port ZeroMQ removal from v2; pairs with 10 as a single upstream PR |

---

## BCHN — Upstream PR Candidates

**Base:** BCHN `v28.0.0` / `0bc23ac4c1365f34ed824e2b07e554ec06a5f5cd`

| Slot | File | Status | What it does |
|------|------|--------|--------------|
| 01 | `01-nlogn-block-construction.patch` | DONE | O(n log n) `addTxs` for BCHN `src/miner.cpp` (value semantics, `addTxs(int64_t)`) |
| 02 | `02-remove-chaintx-limit.patch` | DONE | Drop chain-tx ancestor limits |
| 03 | `03-mempool-cleanup.patch` | NO-OP | Already merged upstream |
| 10 | `10-nng-interface.patch` | NEEDS-WRITE | Port NNG interface to BCHN API |
| 11 | `11-remove-zeromq.patch` | NEEDS-WRITE | Port ZeroMQ removal to BCHN |

---

## Doged — Reference + Decomposed Patches

**Base:** `doged-io/doged` `master` (currently direct clone ~v0.4.0)
**Goal:** Decompose doged-specific changes into individual named patches.
**Why:** Tobias Ruck (doged author) designed Mitra. Understanding which changes he made
to adapt bitcoin-abc for Dogecoin is valuable for Lotus v2.

**Approach:** Scrape the doged git log and diff against bitcoin-abc at their fork
point (`5c6880edbc`, June 2024). Identify changes by Tobias and collaborators. Organize
as individual patches covering:
- Chain identity (Dogecoin chain params, magic bytes, ports)
- Block time (`nPowTargetSpacing`): Dogecoin uses 1-minute blocks; doged likely patches this
- Dogecoin DAA (DigiShield + ASERT hybrid)
- Auxpow / merged mining (if present)
- Avalanche parameter tuning for Dogecoin
- Chronik adaptations for DOGE addresses/denomination
- Build / misc

**Note on block time:** Doged uses `nPowTargetSpacing = 60` (1-minute blocks), confirmed
in `src/kernel/chainparams.cpp`. The commit that sets this **already exists in the doged
git log** — extract it when decomposing doged patches. It maps to a `08c-blocktime.patch`
slot in the doged series.

Until this decomposition is done, workspace-doged remains a direct clone.

---

## Work Sequencing

| Priority | Work Item | Depends on |
|----------|-----------|------------|
| 1 | Write `11-remove-zeromq.patch` for v2 (directly against 252182e9) | nothing |
| 2 | Port NNG + ZeroMQ removal to ecash (slots 10-11) | v2 patch 10+11 |
| 3 | Port NNG + ZeroMQ removal to bchn (slots 10-11) | v2 patch 10+11 |
| 4 | Write `47-remove-zeromq.patch` for v1 (against eCash v0.24.11) | nothing |
| 5 | Write `04-issuance-compat.patch` for v2 and v1 | nothing |
| 6 | Extract `08c-blocktime.patch` for v1 and v2 from v1 lotusd git log | workspace-v1 (needs fetch lotusd) |
| 7 | Extract doged blocktime patch + scrape doged git log for all patch topics | workspace-doged |
| 8 | Write `08b-decouple-avalanche.patch` for v2 | Avalanche decision (done) |
| 9 | Rebase v2 patches 05–31 onto 252182e9 | nothing blocking |
| 10 | Extract block-header, dual-txid, 64-bit fix from 23-misc during rebase | step 9 |
| 11 | Write `32-chronik-adapt.patch` for v2 | `07-xaddress` rebased, xpi prefix confirmed |
| 12 | Decompose doged patches | time / priority |
| 13 | Port mining patches 01-03 to v1 (eCash v0.24.11 API) | time |
| 14 | Mine genesis, update patches 16/17/18 | launch readiness |
| 15 | Implement Mitra (patch 33) | opcode slot decision, dual-txid patch |

---

## Key File Locations

| File | Purpose |
|------|---------|
| `daemon/bitcoin-abc-version` | Pinned base for v2 and ecash series |
| `daemon/ecash-version` | Pinned eCash v0.24.11 base for v1 (static) |
| `daemon/doged-version` | doged branch/tag |
| `daemon/bchn-version` | BCHN pinned tag |
| `daemon/lotusd-version` | Current lotusd release tracked in v1 |
| `daemon/patches/v2/series` | Ordered patch list for v2 |
| `daemon/patches/v1/series` | Ordered patch list for v1 |
| `daemon/patches/ecash/` | eCash upstream PR patches |
| `daemon/patches/bchn/` | BCHN upstream PR patches |
| `daemon/docs/mitra-spec.md` | Mitra transaction format spec |
| `daemon/docs/patch-strategy.md` | This file |
