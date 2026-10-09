# Lotus Daemon — Patch Strategy & Manifest

## Purpose

Single source of truth for all patches across all series. Tracks status, ordering,
what each patch does, which series it applies to, and what work remains.

---

## Patch Quality Standard

**These patches run a live network. Bugs mean lost funds, forks, or downtime.**

Every patch — whether written from scratch or rebased from history — must be
reviewed before it goes into a series. Sloppy context lines, half-applied hunks,
or logic errors that happen to compile are the failure mode. The goal is not "it
applies cleanly"; the goal is "it is correct."

### IMPCPD review

Every patch must pass IMPCPD review before being marked `DONE`.
See **`daemon/docs/impcpd-methodology.md`** for the full checklist and scoring guide.

Summary of the personas applied to every patch:
- **Regression** — does it break existing behavior?
- **Consensus Correctness** — is every branch of the state machine handled?
- **Security** — does it add a new attack surface?
- **Edge Cases** — genesis, empty mempool, reorg, disabled Avalanche?
- **Completeness** — all three networks updated? series file correct? `git apply --check` passes?
- **Tests & Docs** — test that fails before and passes after?
- **Minimality** — does it do exactly one thing?

A patch that fails Minimality (does more than it claims) must be split before
the other personas are even applied.

---

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
issuance, expanded opcode set, dual-txid, Modernized BUIP037 transaction format, O(n log n) mining.
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
| 00 | `00-decouple-avalanche.patch` | NEEDS-WRITE | Decouple Avalanche from block consensus: remove chain-tip finalization hooks in `src/net_processing.cpp` and `src/validation.cpp`. Keep `src/avalanche/` for soft parameter voting. |
| 01 | `01-nlogn-block-construction.patch` | DONE | O(n log n) `addTxs`: snapshot → package-stat accumulation → sort → DFS |
| 02 | `02-remove-chaintx-limit.patch` | DONE | Drop ancestor/descendant chain-tx limits from mempool (O(1) ingestion) |
| 03 | `03-mempool-cleanup.patch` | NO-OP | CTxMemPoolEntry accounting fields already removed upstream in 252182e9 |
| 04 | `04-issuance-compat.patch` | NEEDS-WRITE | Runtime `-issuance=ecash` flag; Lotus issuance is default; eCash/Bitcoin halving when flag set. |
| 05 | `05-chain-identity.patch` | NEEDS-REBASE | Binary names (lotusd/lotus-cli), version strings, CMake project name |
| 06 | `06-currency-unit.patch` | NEEDS-REBASE | XPI denomination; 1 XPI = 10^6 atomic satoshis/atoms |
| 07 | `07-xaddress.patch` | NEEDS-REBASE | XAddress encoding/decoding; v2 prefix = `xpi` |
| 08 | `08-daa-cleanup.patch` | NEEDS-REBASE | Remove Grasberg/EDA; keep only aserti3-2d DAA |
| 08c | `08c-blocktime.patch` | NEEDS-EXTRACT | Set `nPowTargetSpacing = 2 * 60` (120s / 2 minutes) in `src/kernel/chainparams.cpp`. |
| 09 | `09-merkle.patch` | NEEDS-REBASE | Single BLAKE3 domain-separated segmented Merkle tree; CVE-2012-2459 fix. |
| 09b | `09b-block-header.patch` | NEEDS-EXTRACT | 116-byte fixed 64-bit aligned `LotusHeader` committing to `hashUtxoMerklixRoot` and `hashTxMerklixRoot`. |
| 09c | `09c-compact-outputs.patch` | NEEDS-EXTRACT | Multi-branch structured `LotusOutput` (44B standard, 92B token) with inline witnesses and optional `token_amount`. |
| 10 | `10-nng-interface.patch` | NEEDS-REBASE | NNG pub/sub replacing ZeroMQ; adds `src/nng_interface/` |
| 10b | `10b-remove-zeromq.patch` | NEEDS-WRITE | Delete `src/zmq/`, ZeroMQ CMake option, ZeroMQ tests. |
| 11 | `11-intmath-log2.patch` | NEEDS-REBASE | Turner algorithm fixed-point log2 integer math. |
| 12 | `12-issuance-OLD.patch` | DEFERRED | Old log2 issuance curve — supersede by 26+27. |
| 13 | *(minerfund — not applied)* | N/A | Archived for reference only. |
| 14 | `14-script-opcodes.patch` | NEEDS-REBASE | OP_MULPOW2 (0xb2), OP_RAWLEFTBITSHIFT (0xb3), etc. |
| 15 | `15-taproot.patch` | NEEDS-REBASE | 64-byte compact Schnorr signatures and Taproot tree evaluation. |
| 16 | `16-chain-params.patch` | NEEDS-FIX | Network magic, ports, primitives; genesis nNonce=0 placeholder. |
| 17 | `17-genesis.patch` | NEEDS-FIX | Assume-valid constants — placeholder; replace after genesis mined. |
| 18 | `18-checkpoints.patch` | NEEDS-FIX | Clear checkpoints for new chain. |
| 19 | `19-fixed-seeds.patch` | NEEDS-WRITE | Hardcoded seed node IPs for new chain. |
| 20 | `20-seeder.patch` | NEEDS-REBASE | DNS seeder tool. |
| 21 | `21-consensus-activation.patch` | DROP | V2 activates all rules at block 0 — dropped from v2 series. |
| 22 | `22-src-build.patch` | NEEDS-REBASE | src/CMakeLists.txt and sub-build-systems. |
| 23 | `23-misc.patch` | NEEDS-REBASE | RPC, wallet, net, tests, util (header, outputs, txid extracted). |
| 24 | `24-qt-gui.patch` | NEEDS-REBASE | Qt GUI (BUILD_BITCOIN_QT=OFF by default). |
| 25 | `25-build-compat.patch` | NEEDS-REBASE | CMake 4.x + Boost 1.90 fixes for macOS arm64. |
| 26 | `26-boot-subsidy.patch` | NEEDS-REBASE | Boot subsidy step-halvings calibrated for 720 blocks/day (2-minute spacing). |
| 27 | `27-tail-subsidy.patch` | NEEDS-REBASE | Tail emission: sqrt-adaptive stateful emission ($R = K \sqrt{D}$). |
| 28 | `28-ifp-removal.patch` | NEEDS-REBASE | Disable IFP: enableMinerFund=false, zero coinbase tax. |
| 29 | `29-op-log-op-sqrt.patch` | NEEDS-REBASE | OP_LOG (0xbd) and OP_SQRT (0xbe) with full test suite. |
| 30 | `30-op-mul.patch` | NEEDS-REBASE | OP_MUL (0x95) re-enabled; 63-bit signed multiply with overflow detection. |
| 31 | `31-int128-stack.patch` | NEEDS-WRITE | Native `int128_t` two's-complement stack (kills `CScriptNum`); `OP_ADDCARRY`, `OP_SUBCARRY`, `OP_MUL128_WIDE`. |
| 32 | `32-chronik-adapt.patch` | NEEDS-WRITE | Adapt Chronik API output to XAddress (`xpi` prefix) + XPI denomination. |
| 33 | `33-introspection-loops.patch` | NEEDS-WRITE | Clean introspection opcodes (`0xbf–0xcf`), `OP_FOREACH_INPUT/OUTPUT` (depth ≤ 2), static precomputed budget. |
| 34 | `34-utxo-merklix-rocksdb.patch`| NEEDS-WRITE | In-memory Crit-Bit Radix Trie + RocksDB asynchronous write-behind with block state commitments. |
| 35 | `35-rpc-merklix-proofs.patch` | NEEDS-WRITE | `getutxoproof`, `verifymerklixproof`, PCT validation, P2P stateless snap-sync (`GETMERKLIX`/`MERKLIXCHUNK`). |

### Extractions from `23-misc.patch`

| Extracted Slot | File | Purpose |
|----------------|------|---------|
| Slot 09b | `09b-block-header.patch` | 116-byte fixed aligned `LotusHeader` committing to `hashUtxoMerklixRoot` and `hashTxMerklixRoot`. |
| Slot 09c | `09c-compact-outputs.patch` | Multi-branch structured `LotusOutput` (44B standard, 92B token) with inline witnesses and optional `token_amount`. |
| Slot 31 | `31-int128-stack.patch` | Native 128-bit stack replacing `CScriptNum` and ad-hoc 64-bit shims. |

### V2 Open Decisions — All Core Invariants Resolved

| Decision | Status | Notes |
|----------|--------|-------|
| XAddress prefix | **DECIDED** — `xpi` | V1 uses `lotus`; v2 uses `xpi` to prevent cross-chain address reuse. |
| Avalanche in v2 | **DECIDED** — decouple from consensus; keep for soft voting | Hard PoW block/tx consensus; Avalanche kept for advisory fee/parameter voting. |
| V2 epoch activation | **DECIDED** — drop patch 21 | All consensus rules active at block 0; zero hardfork epochs. |
| Hashing engine | **DECIDED** — Single BLAKE3 | Double hashing (`BLAKE3d`) rejected; BLAKE3 domain flags prevent length extension. |
| Output representation | **DECIDED** — Multi-Branch Structured | Explicit `branches[]` (44B standard XPI, 92B token), optional `token_amount` bitflag, inline 1-to-1 witnesses in `vin`/`vout`. |
| Native tokens | **DECIDED** — Outpoint Invariant | $\text{TokenID} = \text{BLAKE3}(\text{vin}[0].\text{prevout})$; double-spend immunity; zero lineage proofs. |
| Introspection opcodes | **DECIDED** — 128-bit VM | Native `int128_t` stack eliminates `BIGADD/SUB`, freeing `0xbf–0xcf` for clean introspection. |
| Passkey / WebAuthn | **DECIDED** — `secp256r1` in `OP_CHECKDATASIG` | Native curve support for Apple Secure Enclave & Android Titan biometric signatures. |
| Script loops | **DECIDED** — Enumerable ($N \le 2$) | Bounded over `input_count`/`output_count`; static precomputed execution budget. |
| State persistence | **DECIDED** — RAM Trie + RocksDB WAL | In-memory Crit-Bit Trie for $<5\text{ ms}$ rehash; RocksDB block state commitments for sub-second crash recovery. |
| P2P Transport (QUIC) | **DECIDED** — Post-Genesis Upgrade | RFC 9000 TLS 1.3 over UDP; looks like HTTP/3; 0 hardforks needed (`NODE_QUIC` service bit). |
| Double-Spend Proofs | **REJECTED** — Asymmetric DoS Vector | Un-fee'd signature verification cascade and covenant incompatibility; stick to clean $O(1)$ first-seen drop. |

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
- Same patch at slot `000` in v1 series (applied first, before mining patches)
- **Remove from** `src/net_processing.cpp` and `src/validation.cpp`:
  the call sites where Avalanche quorum gates block acceptance or chain-tip finalization.
  A valid PoW block is valid, full stop — Avalanche cannot veto it.
- **Keep everything in** `src/avalanche/`: the gossip protocol, voting rounds, quorum
  tracking, and all the parameter-voting machinery. Nodes can still run Avalanche rounds
  to reach soft consensus on fee preferences, mempool policy knobs, and other network
  parameters. None of that touches block or transaction validity.
- Net result: Avalanche is still running and useful, just not in the consensus path.

### Post-Genesis Roadmap (Zero-Hardfork Enhancements)

Because all consensus invariants (Header format, Multi-Branch Outputs with Inline Witnesses, BLAKE3, 128-bit VM, Introspection, NOR-Tree, Tail Subsidy) are permanently locked at Block 0, future protocol optimizations remain **strictly internal node implementations and network transport upgrades** that require **ZERO hardforks**:

1. **QUIC P2P Transport Layer (RFC 9000 / HTTP/3 over UDP)**:
   - Deep Packet Inspection (DPI) resistance: Transports P2P messages inside standard TLS 1.3 encrypted UDP datagrams, indistinguishable from HTTP/3 web browsing.
   - Eliminates TCP head-of-line blocking across independent block, transaction, and heartbeat streams.
   - Seamless connection migration for mobile nodes across Wi-Fi $\leftrightarrow$ 5G handovers via 64-bit Connection IDs.
   - Rollout: Standard P2P feature negotiation via `NODE_QUIC` service bit in `src/net`.
2. **Stateless Snap-Sync RPCs & P2P Merklix Chunk Streaming**:
   - Fast node synchronization utilizing authenticated Crit-Bit Radix Trie snapshots.
3. **Chronik Real-Time WebSockets & Token Streaming**:
   - Native streaming of L1 token balances (`amount || token_id`) and 32B output metadata.
4. **Partially Signed Lotus Transactions (PSLT / BIP-0370)**:
   - Standardized hardware wallet multisig coordinator formats.
5. **Architectural Exclusion of Double-Spend Proofs (BUIP135)**:
   - DSPs introduce an un-fee'd signature verification cascade (100,000 dust outputs force 200,000 signature checks on every node globally).
   - Incompatible with stateful smart contracts and `P2MNOR` guardrails.
   - Lotus v2 retains pure Nakamoto first-seen policy: conflicting mempool spends are rejected in an $O(1)$ hash table check ($<5\text{ ns}$, zero bandwidth, zero state bloat).

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

### Patch ordering on the rebased 252182e9 base

**Slot 000 comes before everything else — decouple Avalanche from block/tx consensus first.**

At bitcoin-abc 252182e9, Avalanche is woven into `net_processing.cpp` and `validation.cpp`
at dozens of call sites. Specifically: chain-tip finalization hooks, quorum checks used as
block validity criteria, and tx-acceptance gates. Stripping *those specific hooks* first
means every subsequent Lotus patch that touches those files lands on cleaner context.

**What stays vs what goes in 000-decouple-avalanche:**

- **Keep:** `src/avalanche/` directory entirely. We want Avalanche for soft parameter
  voting — nodes gossip and reach quorum on things like preferred fee rates, mempool policy
  knobs, and other network parameters. None of that touches block or transaction validity.
- **Remove:** The call sites where Avalanche quorum is required to *accept a block* or
  *finalize a chain tip*. Lotus is a pure PoW chain; a valid PoW block is valid, full stop.
  Avalanche cannot veto it.
- **Leave alone:** Everything in `src/avalanche/` that handles gossip, voting rounds,
  quorum tracking — that's the part we want. Just disconnect it from the block/tx validity
  gates in `net_processing.cpp` and `validation.cpp`.

```
000-decouple-avalanche   ← remove block/tx finalization hooks; keep gossip/voting
001-nlogn-block          ← mining (uses 252182e9 API: src/node/miner.cpp + addTxs)
002-remove-chaintx       ← chain-tx limits
003-mempool-cleanup      ← no-op at this base
004 → 245                ← Lotus historical commits, conflict-resolved one at a time
```

### Process — patch-by-patch rebase

For each patch in order (000 → 245):
1. `git apply --check patches/v1/<patch>` against the workspace
2. If it fails: resolve conflicts manually, keeping Lotus-specific changes
3. `git apply --whitespace=nowarn` to apply
4. Run the relevant test suite (`make check` or the affected test file)
5. Fix any test failures
6. `make mkpatch SERIES=v1 NAME=<patch>` to re-emit the updated patch
7. Move to the next patch

Many patches (004–100) will conflict because bitcoin-abc reorganized files between
v0.24.11 and 252182e9. Key known conflicts:
- `src/miner.cpp` → `src/node/miner.cpp` (affects patches touching mining)
- `src/chainparams.cpp` → `src/kernel/chainparams.cpp` (affects every epoch patch)
- Chronik is a new subsystem (Lotus patches don't touch it; additive, low conflict)
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
| 9 | Implement Introspection & Loops (patch 33) | 0xbf–0xcf introspection, bounded loops |

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
| `daemon/docs/mitra-spec.md` | Mitra spec (Archived reference; superseded by Modernized BUIP037 + P2MNOR) |
| `daemon/docs/patch-strategy.md` | This file |
