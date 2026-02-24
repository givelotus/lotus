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
| 04 | `04-issuance-compat.patch` | NEEDS-WRITE | Runtime `-issuance=ecash` flag; Lotus issuance is default; eCash/Bitcoin halving when flag set; allows eCash test suite to run unmodified without changing coinbase amount checks. Placeholder exists. |
| 05 | `05-chain-identity.patch` | NEEDS-REBASE | Binary names (lotusd/lotus-cli), version strings, CMake project name |
| 06 | `06-currency-unit.patch` | NEEDS-REBASE | XPI denomination; 1 XPI = 10^4 satoshis; amount formatting throughout |
| 07 | `07-xaddress.patch` | NEEDS-REBASE | XAddress encoding/decoding; replaces CashAddr; v2 prefix = `xpi` (v1 used `lotus`) |
| 08 | `08-daa-cleanup.patch` | NEEDS-REBASE | Remove Grasberg/EDA; keep only aserti3-2d DAA |
| 08b | `08b-decouple-avalanche.patch` | NEEDS-WRITE | Decouple Avalanche from block consensus: remove chain-tip finalization hooks in `src/net_processing.cpp`, remove Avalanche from block validity checks. **Do NOT remove the Avalanche code itself.** It stays in the codebase for soft parameter voting (fee preferences, mempool policy, network parameter governance). Avalanche as a finalization layer is incompatible with the σₜ security model; as a gossip/voting layer it's fine. |
| 08c | `08c-blocktime.patch` | NEEDS-EXTRACT | Set `nPowTargetSpacing = 2 * 60` (2 minutes). **The commit already exists in the v1 lotusd repo — extract it.** Find the commit with `git log --all --oneline -- src/chainparams.cpp` in workspace-v1 and isolate the `nPowTargetSpacing` change. V2 uses the same value; apply the same extracted patch. **Downstream effects:** (1) boot subsidy step heights in patch 26 must be 5× larger to hit the same wall-clock half-life (720 blocks/day at 2 min vs 144 at 10 min). |
| 09 | `09-merkle.patch` | NEEDS-REBASE | IGUANA interleaved merkle tree; fixes the CVE-2012-2459 variant merkle tree vulnerability; implements MerklixHash (bitwise trie + SHA256 overlay) per the 2018 Vermorel/Séchet/Chancellor/Cox paper |
| 10 | `10-nng-interface.patch` | NEEDS-REBASE | NNG pub/sub replacing ZeroMQ; adds `src/nng_interface/`; Chronik stays separate |
| 10b | `10b-remove-zeromq.patch` | NEEDS-WRITE | Delete `src/zmq/`, ZeroMQ CMake option, ZeroMQ tests; was never removed. **Numbered 10b in v2 because slot 11 is occupied by intmath-log2.** In ecash/bchn this is at slot 11. Placeholder exists. |
| 12 | `12-issuance-OLD.patch` | DEFERRED | Old log2 issuance curve — **superseded by 26+27; remove from series once those confirmed stable** |
| 13 | *(minerfund — not applied)* | N/A | Archived for reference only |
| 14 | `14-script-opcodes.patch` | NEEDS-REBASE | OP_MULPOW2 (0xb2), OP_RAWLEFTBITSHIFT (0xb3) and related new opcodes |
| 15 | `15-taproot.patch` | NEEDS-REBASE | Taproot — **open question: does v2 want taproot? review before rebasing** |
| 16 | `16-chain-params.patch` | NEEDS-FIX | Network magic, ports, primitives; genesis nNonce=0 placeholder; epoch times need updating |
| 17 | `17-genesis.patch` | NEEDS-FIX | Assume-valid constants — placeholder with v1 mainnet values; replace after genesis is mined |
| 18 | `18-checkpoints.patch` | NEEDS-FIX | Checkpoints — currently has v1 values; must be cleared for new chain |
| 19 | `19-fixed-seeds.patch` | NEEDS-WRITE | Seed node IPs for new chain (v1 IPs currently; need new seed nodes) |
| 20 | `20-seeder.patch` | NEEDS-REBASE | DNS seeder tool |
| 21 | `21-consensus-activation.patch` | DROP | V1 named upgrade epochs (Exodus through 1st Kings). **V2 activates everything at block 0 — this patch is dropped from v2.** Now commented out in v2/series. Keep in v1 series only. |
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
| 32 | `32-chronik-adapt.patch` | NEEDS-WRITE | Adapt Chronik API output to XAddress (xpi prefix) + XPI denomination. Placeholder exists. |
| 33 | `33-mitra-tx.patch` | SKELETON | Mitra tx format; see `daemon/docs/mitra-spec.md`; blocked on opcode slot resolution. Placeholder exists (renamed from 32-mitra-tx.patch). |

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

## V1 — Lotus Mainnet (rebasing to latest bitcoin-abc)

**Current base:** eCash v0.24.11 `fa7a44f731a2dfe1587e572d9eb0e4bb7c73d79c` (extraction anchor)
**Target base:** bitcoin-abc `252182e957120652960c1f88ec96515c448b1204` (same as v2)
**Goal:** Working lotusd on latest bitcoin-abc with Chronik. Lotus mainnet has been
live since June 2021. We extracted the full commit history from both source repos and
are now rebasing it onto modern bitcoin-abc so we can use Chronik and ship a supported build.

### Where We Are

We have extracted **245 individual commits** as patch files:

| Range | Source | Count | Notes |
|-------|--------|-------|-------|
| `001` | (written fresh) | 1 | O(n log n) block construction (eCash v0.24.11 API) |
| `002` | (written fresh) | 1 | Remove ancestor/descendant chain-tx limits |
| `003` | (written fresh) | 1 | Mempool cleanup (DEFERRED — no-op after rebase to 252182e9) |
| `004–199` | `givelotus/lotusd` | 196 | All non-merge commits, fork point `fa7a44f73..master` |
| `200–245` | `LotusiaStewardship/lotusd` | 46 | Commits beyond givelotus: Ruth, Samuel, Taproot, v10.4.10 |

**The patches currently target the eCash v0.24.11 base.** Many will conflict when applied
to bitcoin-abc 252182e9. The next phase is to go through each one, apply it, run tests,
fix conflicts, and move on. By the end we have a working Lotus daemon on current bitcoin-abc
with Chronik fully functional.

### Process — patch-by-patch rebase

For each patch in order (001 → 245):
1. `git apply --check patches/v1/<patch>` against a clean 252182e9 workspace
2. If it fails: resolve conflicts manually, keeping Lotus-specific changes
3. `git apply --whitespace=nowarn` to apply
4. Run the relevant test suite (`make check` or the affected test file)
5. Fix any test failures
6. `make mkpatch SERIES=v1 NAME=<patch>` to re-emit the updated patch
7. Move to the next patch

Many early patches (004–100) will conflict because bitcoin-abc reorganized files between
v0.24.11 and 252182e9. Key known conflicts:
- `src/miner.cpp` → `src/node/miner.cpp` (affects patches touching mining)
- `src/chainparams.cpp` → `src/kernel/chainparams.cpp` (affects every epoch patch)
- Avalanche machinery added throughout `src/net_processing.cpp`
- Chronik added as a new subsystem (patches touching it are additive, low conflict)
- `src/init.cpp` reorganized substantially

### Key landmark patches to watch for

| Patch | What it is | Rebase note |
|-------|------------|-------------|
| `044` | Change blocktime to 2 minutes | `nPowTargetSpacing` change; file moved to kernel/ |
| `043` | Remove ZeroMQ | Placeholder — write during rebase |
| `087` | Add log2 fixed-point math | Low conflict; likely applies cleanly |
| `095` | Log2 issuance curve | Medium conflict; touches chainparams + validation |
| `158` | Add NNG interface | Likely applies with path adjustment |
| `199` | Judges epoch activation | High conflict — epoch infrastructure differs |
| `203` | Ruth epoch | High conflict |
| `218` | 1st Samuel epoch | High conflict |
| `230` | 2nd Samuel + Taproot | High conflict |
| `240` | Taproot address RPC | Medium conflict |

### Additional patches needed on top of the historical series

These are not in the historical lotusd commits — write them after the series applies cleanly:

| Slot | File | Status | What it does |
|------|------|--------|--------------|
| A | `08b-decouple-avalanche.patch` | NEEDS-WRITE | Remove Avalanche from chain-tip finalization; keep for soft voting |
| B | `32-chronik-adapt.patch` | NEEDS-WRITE | Adapt Chronik output to `lotus` prefix + Lotus denomination |
| C | `04-issuance-compat.patch` | NEEDS-WRITE | `-issuance=ecash` flag for running eCash test suite |

### V1 Patch Manifest (summary)

The individual patches are listed in `daemon/patches/v1/series`. There are 245 of them.
Rather than repeat all 245 here, the key categories are:

- **001–003**: Mining improvements (nlogn, remove chain limits, cleanup)
- **004–046**: Core Lotus protocol changes (genesis, ASERT, blocktime, issuance, NNG, opcodes)
- **047–100**: Address format, XAddress, chain params, Chronik stubs
- **101–199**: Epoch activations (Numbers through Judges) + version bumps
- **200–245**: LotusiaStewardship additions (Ruth, Samuel epochs, Taproot, v10.4.10)

---

## Ecash — Upstream PR Candidates

**Base:** bitcoin-abc `252182e957120652960c1f88ec96515c448b1204`

| Slot | File | Status | What it does |
|------|------|--------|--------------|
| 01 | `01-nlogn-block-construction.patch` | DONE | O(n log n) `addTxs` for `src/node/miner.cpp` |
| 02 | `02-remove-chaintx-limit.patch` | DONE | Drop chain-tx ancestor limits |
| 03 | `03-mempool-cleanup.patch` | NO-OP | Already merged upstream |
| 10 | `10-nng-interface.patch` | NEEDS-WRITE | Port NNG interface from v2. Independently reviewable. Placeholder exists. |
| 11 | `11-remove-zeromq.patch` | NEEDS-WRITE | Remove ZeroMQ. Independently reviewable; applies after slot 10. Placeholder exists. |

---

## BCHN — Upstream PR Candidates

**Base:** BCHN `v28.0.0` / `0bc23ac4c1365f34ed824e2b07e554ec06a5f5cd`

| Slot | File | Status | What it does |
|------|------|--------|--------------|
| 01 | `01-nlogn-block-construction.patch` | DONE | O(n log n) `addTxs` for BCHN `src/miner.cpp` (value semantics, `addTxs(int64_t)`) |
| 02 | `02-remove-chaintx-limit.patch` | DONE | Drop chain-tx ancestor limits |
| 03 | `03-mempool-cleanup.patch` | NO-OP | Already merged upstream |
| 10 | `10-nng-interface.patch` | NEEDS-WRITE | Port NNG interface to BCHN API. Independently reviewable. Placeholder exists. |
| 11 | `11-remove-zeromq.patch` | NEEDS-WRITE | Remove ZeroMQ from BCHN. Independently reviewable; applies after slot 10. Placeholder exists. |

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

### Primary goal (current): Rebase V1 onto bitcoin-abc 252182e9

The immediate focus is getting all 245 v1 patches applying cleanly to the latest
bitcoin-abc. Once that's done we have a working Lotus daemon with Chronik.

**Process:** For each patch in `patches/v1/series` (001 → 245):
```
git apply --check patches/v1/<patch>     # see what fails
# fix conflicts, keeping Lotus logic, accepting upstream reorganization
git apply --whitespace=nowarn patches/v1/<patch>
make check                                # or run specific test
# fix test failures
make mkpatch SERIES=v1 NAME=<patch>      # re-emit updated patch
```

| Priority | Work Item | Status |
|----------|-----------|--------|
| **1** | **Rebase v1 patches 001–245 onto bitcoin-abc 252182e9** | **IN PROGRESS** |
| 1a | Patches 001–050: core protocol, genesis, blocktime, NNG, opcodes | not started |
| 1b | Patches 051–100: XAddress, chainparams, issuance, DAA | not started |
| 1c | Patches 101–199: epoch activations (Numbers → Judges) | not started |
| 1d | Patches 200–245: Ruth → 2nd Samuel, Taproot, v10.4.10 | not started |
| 1e | Write `08b-decouple-avalanche.patch` on top of rebased series | not started |
| 1f | Write `32-chronik-adapt.patch` (lotus prefix + denomination) | not started |
| 2 | Verify Chronik works end-to-end against Lotus mainnet | after 1f |
| 3 | Rebase v2 patches 05–31 onto 252182e9 (derive from v1 rebase) | after step 1 |
| 4 | Extract block-header / dual-txid / 64-bit fix from 23-misc | during step 3 |
| 5 | Write v2-specific patches (new genesis, issuance params, xpi prefix) | after step 3 |
| 6 | Decompose doged patches | lower priority |
| 7 | Port NNG + ZeroMQ patches to ecash / bchn (slots 10-11) | lower priority |
| 8 | Mine v2 genesis, update patches 16/17/18 | launch readiness |
| 9 | Implement Mitra (patch 33) | opcode slot decision, dual-txid |

### Notes on the rebase

**File moves to expect** (bitcoin-abc moved files between v0.24.11 and 252182e9):
- `src/chainparams.cpp` → `src/kernel/chainparams.cpp`
- `src/miner.cpp` → `src/node/miner.cpp`
- Many `src/*.cpp` split into `src/node/*.cpp` and `src/kernel/*.cpp`

**Epoch activation patches (101–245)** will conflict heavily because bitcoin-abc removed
the `gArgs.GetArg("-xxxactivationtime", ...)` pattern. Strategy: accept the upstream
removal of that plumbing and keep only the Lotus-specific activation logic and addresses.

**Avalanche** is woven throughout `src/net_processing.cpp` and `src/validation.cpp` in
252182e9 in ways that didn't exist in v0.24.11. Patches touching those files will conflict.
Accept bitcoin-abc's Avalanche additions (we keep the code), just make sure Lotus's own
changes layer on top cleanly. The `08b-decouple-avalanche.patch` applied last removes the
consensus-critical Avalanche hooks.

**Chronik** is additive in 252182e9 — it's a new subsystem not present in v0.24.11.
Lotus patches don't touch Chronik, so those patches should apply cleanly. The
`32-chronik-adapt.patch` at the end adjusts Chronik output for Lotus specifics.

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
