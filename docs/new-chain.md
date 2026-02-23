# New Lotus Chain — Design Reference

This document synthesizes the three Lotus papers, the current daemon implementation, and
the specific goals for the new chain. It is the authoritative reference for what needs to
be built and why.

---

## Three Patchsets

Three parallel build targets are maintained in `daemon/`:

| | V1 — Mainnet | V2 — New Chain | doged |
|---|---|---|---|
| Purpose | Sync to Maff's chain | Visionary new chain; paper-correct issuance, Mitra, OP_LOG/SQRT | Tobias's Dogecoin ABC; Chronik + Avalanche reference |
| Base | LotusiaStewardship/lotusd | eCash v0.24.11 (fa7a44f731) + patches | doged-io/doged (eCash fork, version TBD) |
| Workspace | `daemon/workspace-v1/` | `daemon/workspace/` | `daemon/workspace-doged/` |
| Version pin | `daemon/lotusd-version` | `daemon/ecash-version` | `daemon/doged-version` |
| Patches | `daemon/patches/v1/` (experiments on top) | `daemon/patches/series` | `daemon/patches/doged/` (experiments on top) |
| Build | `make setup SERIES=v1 && make build SERIES=v1` | `make setup && make build` | `make setup SERIES=doged && make build SERIES=doged` |
| Chain state | ~1.2M blocks; buggy Ruth/IFP fork; Taproot active | Not launched; genesis TBD | Dogecoin mainnet |

The longer-term goal is to extract a common **logond** framework from the convergent
technical decisions across these three ABC-derived codebases. See `docs/architecture-decisions.md`
for the multi-chain framework design.

### V1 Chain State

The canonical *correct* Lotus chain stalled at block 927,381 (Dec 21, 2024) after
the Ruth epoch upgrade shipped with two consensus bugs: missing replay protection and
the Ruth IFP validation check falling through to the Judges epoch check. Maff released
a hotfix (v8.3.3-hotfix) but subsequent 9.x/10.x releases were built on top of the
diverged fork. The ~1.2M block chain is self-consistent within its own ruleset but
no correctly-validating Ruth node would accept it. V1 compatibility means compatibility
with Maff's fork, not the spec.

### doged Notes

doged is a Bitcoin ABC-derived Dogecoin node; EyeOfPython (likely Tobias Ruck, who designed
Mitra) is a contributor. The eCash base commit it was forked from is unknown — determine
by cloning and examining `git log` in `workspace-doged/`.

Key things to study:
- **Chronik implementation**: doged has production Chronik. The Lotus project funded the
  original Chronik development; eCash then paid to pull it in-process and strip NNG out.
  doged's Chronik is the most accessible production reference for re-integrating Chronik
  into V2 with NNG restored. See `architecture-decisions.md` for the three options.
- **Avalanche consensus**: reference code for a consensus layer addition
- **Opcode/interpreter history**: check `git log src/script/` for any changes Tobias made

---

## Design Goals

1. **Remove the developer reward (IFP).** The minerfund mechanism routing 50% of block
   reward to controlled addresses was the source of the network conflict and must not exist
   on the new chain. Miners keep what they mine.

2. **Implement the adaptive monetary policy from the paper.** The current daemon uses a
   simplified log2-difficulty formula. The paper specifies a two-loop mechanism (boot
   subsidy + adaptive tail). The new chain implements the full spec.

3. **No six-month hard fork schedule.** The epoch system (Genesis through 1st Kings) was
   designed to update IFP addresses on a fixed cadence. Without IFP, there is no reason
   for mandatory hard forks. Activate everything at genesis. Protocol upgrades go through
   soft fork or optional hard fork with broad consensus, not a fixed calendar.

4. **Paper-compatible from genesis.** All three Lotus papers are the specification:
   - consensus-energy: PoW security expenditure theory — already satisfied by PoW chain
   - adaptive-pow-monetary-policy: two-loop issuance — **needs implementation**
   - cashweb: burn-to-speak federated messaging — cashwebd exists, needs chain integration

5. **Project-controlled infrastructure.** Seed nodes, genesis block, chain identity — all
   under project control. No dependency on any external operator.

6. **Clean PoW launch.** No UTXO snapshot from old chain. Small genesis allocation for
   verifiable early contributors. PoW is the fair distributor.

---

## The Three Papers

### Paper 1: Security Expenditure, Energy, and Issuance Legibility (`consensus-energy`)

**Core thesis:** In any permissionless system with an externally valued block reward,
rational actors expend real resources proportional to expected value at risk. PoW expresses
this directly and legibly; PoS displaces it into opaque channels (MEV, governance capture,
validator infrastructure races). The key PoW quantity is `σ_t = H_t / Π_t` (expected
hashes per unit of issuance) — a protocol-visible, adversarially revealed security density
that no PoS system can produce.

**New chain implication:** The chain stays PoW. The log2-difficulty subsidy formula already
provides σ_t-coupling (higher work → higher subsidy). The adaptive tail emission extends
this with a stateful ratio-based component.

---

### Paper 2: Adaptive PoW Monetary Policy Without Oracles (`adaptive-pow-monetary-policy`)

**Core specification:**

Total coinbase subsidy per block:
```
R_n = R_n^boot + R_n^tail
```

**Boot component** (height-based, decaying):
```
R_n^boot = R_0 * exp(-λ * n)
```
Attracts early participation. Independent of work. Decays monotonically.

**Tail component** (stateful, work-coupled):
```
R_{n+1}^tail = clip(R_n^tail * (W_n / W_{n-1})^γ, R_min, R_max)
```
- `W_n` = work proxy from nBits (difficulty or expected hashes)
- `γ ∈ (0,1)` — sublinearity exponent; `γ = 1/2` recommended
- `R_min > 0` — floor: baseline mining incentive survives demand collapse
- `R_max` — ceiling: safety against rare hash-spike shocks
- `R_n^tail` is a **consensus state variable** in chainstate, updated every block

**Burn sink:**
- Fixed fee burn fraction β: `B_n^fee = β * F_n`, miners receive `(1-β) * F_n`
- Burn-to-speak: `B_n^b2s` from CashWeb message burns; sum is `B_n = B_n^fee + B_n^b2s`
- Total net issuance: `ΔS_n = R_n^boot + R_n^tail + F_n - B_n`

**Stability:** Lyapunov stability proven for φ ∈ (0, 2+2γ), where φ is price sensitivity
to supply. The sublinear exponent γ makes the stable regime wider as γ → 0.

**Implementation notes from the paper:**
- `R_n^tail` computed from `(R_{n-1}^tail, W_{n-1}, W_{n-2})` — no coinbase lookups needed
- `W_n` derived from nBits only — no full-history scan
- `(W_n/W_{n-1})^γ` for `γ=1/2` uses integer square-root — deterministic and simple
- Validation: `coinbase subsidy ≤ R_n^boot + R_n^tail`
- Fee burn fraction β = 50% already implemented in current daemon

---

### Paper 3: CashWeb (`cashweb`)

**Core specification:** Federated messaging protocol with economic spam prevention.

**Proof-of-Payment (POP):** Users burn coins (OP_RETURN outputs) to prove payment.
Relay servers verify the burn before accepting messages. No trusted intermediary needed.

**Components:**
- Keyservers: global registry of user public keys and relay server addresses
- Relay servers: store/forward encrypted messages; verify POP before accepting
- Topics: publish-subscribe broadcast channels; any user can create, any relay propagates
- Encryption: ECDH per-sender, end-to-end; relay servers see only ciphertext

**Monetary role:** Burn-to-speak provides `B_n^b2s` in the adaptive issuance framework.
As network grows, burn demand grows (Metcalfe's law), strengthening the supply sink
exactly when the chain is gaining value. The burn rate rises when coin price falls
(advertisers convert more fiat to coins to maintain attention share) — natural
negative feedback without any oracle.

**Current status:** `cashwebd` (Rust, RocksDB) is implemented in the monorepo. It handles
keyserver and relay functions. It connects to lotusd via JSON-RPC. What's missing is
tight integration of the POP mechanism with the chain's issuance accounting.

---

## Current Implementation vs. Paper Spec

| Feature | Paper Specifies | Current Daemon | Gap |
|---|---|---|---|
| Boot subsidy | `R_0 * exp(-λn)` height-based decay | Step-halvings: R_0=10M XPI, half-life=52,560 blocks (~73 days), floor=260 XPI — patch 22 | Approximation of exp decay via halvings; paper uses continuous decay |
| Tail emission | Stateful `R_n^tail`, ratio update each block | Implemented: `nTailSubsidy` in CBlockIndex, sqrt-adaptive update from nBits log2 delta — patch 23 | None; matches paper spec |
| Fee burn | β fraction burned | 50% burn (β=0.5) implemented | None |
| Burn-to-speak sink | CashWeb OP_RETURN burns counted | Not integrated at daemon level | Needs chain-level burn accounting |
| Developer reward | Not specified | 50% of blockReward to IFP addresses | **Must remove** |
| Epoch activations | Not applicable (activate at genesis) | 13-epoch hard fork schedule | **Must remove** |
| OP_LOG | Useful for on-chain math | Not implemented | Needed |
| OP_SQRT | Useful for on-chain math | Not implemented | Needed |
| Mitra tx format | Protocol-layer introspection + native tokens | Not implemented | Major milestone |
| XAddress format | Lotus-specific encoding | Implemented | None |
| IGUANA merkle | CVE-safe merkle tree | Implemented | None |
| NNG pub/sub | Not paper-specified; practical need | Implemented | None |

### Issuance: Current Formula vs. Paper

**Current** (`GetBlockSubsidy` in validation.cpp):
```
subsidy = SUBSIDY_INT * LOG_MAX_TARGET - log2(nBits_target) + SUBSIDY_INT
```
- Range: 260 to ~57,460 XPI/block
- Higher difficulty → higher subsidy (work-coupled, but single-loop)
- No stateful variable; computed fresh from nBits each block
- Validates: `subsidy ≥ SUBSIDY_INT && subsidy ≤ 221 * SUBSIDY_INT`

**Paper** (two-loop mechanism):
```
R_n^boot = R_0 * exp(-λ * n)          # decays with height
R_n^tail = adaptive stateful variable  # updated from work ratio
coinbase_max = R_n^boot + R_n^tail
```

**Migration path:** The log2 formula can serve as R_n^boot with a reparameterization.
Alternatively, replace with explicit exponential decay and add R_n^tail on top. The
stateful tail variable is the critical missing piece regardless.

---

## What Needs to Change in the Daemon

### Remove

- **IFP/minerfund entirely.** `minerfund.cpp` / `minerfund.h` — delete or gut.
  `enableMinerFund` flag: hardcode to false. Remove `coinbasePayoutAddresses` from
  `Consensus::Params` (the entire `CoinbaseAddresses` struct).

- **Epoch activation system.** The 13 epoch times (`exodusActivationTime` through
  `firstKingsActivationTime`) exist solely to rotate IFP addresses. Without IFP,
  they serve no purpose. Remove from `consensus/params.h` and all callers.
  Replace the `IsXxxEnabled` activation pattern with a single "is post-genesis"
  check or remove entirely. Protocol features activate at height 0.

- **Coinbase IFP validation.** In `validation.cpp`, the `bad-cb-minerfund` check
  iterates coinbase outputs to enforce IFP payment. Remove this check.

### Modify

- **`GetBlockSubsidy`:** Replace the current formula with the paper's two-loop mechanism.
  - Implement R_n^boot as either: (a) keep the log2-difficulty formula as-is, or
    (b) implement explicit `R_0 * exp(-λn)` decay.
  - Add R_n^tail computation from chainstate.
  - Return `R_n^boot + R_n^tail`.
  - Choose initial parameters: γ=1/2, R_min, R_max, R_0^tail.

- **Chainstate:** Add `R_n^tail` as a consensus state variable.
  - Stored in chainstate/UTXO DB alongside chain work.
  - Computed during block connection: `R_{n+1}^tail = clip(R_n^tail * sqrt(W_n/W_{n-1}), R_min, R_max)`
  - Must be deterministic across all nodes (use fixed-point integer sqrt).
  - Validated on block acceptance: coinbase subsidy ≤ R_n^boot + R_n^tail.

- **Genesis block** (patch 13-genesis.patch): New genesis with clean params.
  Set `R_0^tail` to initial value from calibration. Set new chain magic, network port,
  chain name.

- **Fixed seeds** (patch 15-fixed-seeds.patch): Project-controlled seeds only.

- **Chain params** (patch 12-chain-params.patch): Remove epoch activation times.
  Keep: genesis hash, pow limit, nPowTargetSpacing, nDAAHalfLife, XAddress prefix.

### Add

- **OP_LOG opcode:** `Log2FixedPoint` already exists in `util/intmath.cpp`.
  Expose as script opcode for on-chain math. Activates at genesis.

- **OP_SQRT opcode:** Integer floor-sqrt. Useful for on-chain geometry and computations.
  Needed for γ=1/2 tail emission calculation (though that's in C++, not script).
  Activates at genesis.

- **Mitra transaction format** (larger milestone, separate patch):
  Preamble scripts, carryover field, full introspection opcodes, native tokens,
  OP_LOOP/OP_ENDLOOP. This is the biggest feature gap. Not required for chain launch
  but should be activated at genesis to avoid needing a hard fork later.

---

## Epoch System → Protocol Stability

The current mainnet fragmented because an epoch upgrade (Ruth, December 2024) shipped with
two bugs and had to be hotfixed during activation. The root cause was not just bad code —
it was that the protocol *required* a mandatory hard fork every six months to rotate IFP
addresses, creating repeated high-stakes coordination events.

Without IFP:
- No mandatory hard forks. The protocol is stable at genesis.
- Soft forks (activated by miner signaling) can add features without coordination.
- Hard forks (when needed for security) can happen on demand rather than on calendar.
- The codebase has no epoch-gated code paths that silently activate and fail.

This is the key promise to the community: build it once, correctly, and it runs.

---

## Burn-to-Speak Integration

For the adaptive monetary policy to work fully, B_n^b2s must be counted. In the current
architecture:
- cashwebd burns coins via OP_RETURN outputs included in normal transactions
- The daemon validates and mines those transactions but doesn't count burns separately
- GetBlockSubsidy doesn't see fee/burn data anyway (it only gets nBits)

For full paper compatibility, the daemon needs to:
1. Recognize CashWeb burn outputs (OP_RETURN with specific prefix/format)
2. Accumulate B_n^b2s per block
3. Feed it into net issuance tracking (informational, not coinbase validation)

This is an informational/indexing concern, not a consensus rule. The subsidy rule
validates only `coinbase ≤ R_n^boot + R_n^tail`. Burns reduce supply independently.
Phase 1 of the new chain can omit burn-counting and add it as a soft upgrade.

---

## Patch Plan (New Chain)

Starting from eCash v0.24.11 at commit `fa7a44f731`. Old mainnet patches archived in
`daemon/patches/archive/mainnet/`. Current active series in `daemon/patches/series`:

```
# ── Carried from mainnet (reviewed, keep as-is) ──────────────────────────────
01-chain-identity.patch          # binary names, version strings, cmake packaging
02-currency-unit.patch           # XPI denomination and amount formatting
03-xaddress.patch                # Lotus address encoding (XAddress, replaces CashAddr)
04-daa-cleanup.patch             # remove Grasberg/EDA/DAA; keep aserti3-2d only
05-merkle.patch                  # IGUANA interleaved merkle tree
06-nng-interface.patch           # NNG pub/sub replacing ZeroMQ
07-intmath-log2.patch            # Log2FixedPoint (Turner algorithm)
08-issuance.patch                # OLD log2-difficulty formula — superseded by 22+23
10-script-opcodes.patch          # OP_MULPOW2, OP_RAWLEFTBITSHIFT, etc.
11-taproot.patch                 # Taproot — REVIEW: may simplify or keep as-is
12-chain-params.patch            # REPLACE: remove epoch times, remove CoinbaseAddresses
13-genesis.patch                 # REPLACE: new genesis block
14-checkpoints.patch             # CLEAR for new chain
15-fixed-seeds.patch             # REPLACE: project-controlled seed nodes
16-seeder.patch                  # seeder tool
17-consensus-activation.patch    # REMOVE: epoch activation system (no IFP → no epochs)
18-src-build.patch               # src/CMakeLists.txt and sub-build-systems
19-misc.patch                    # RPC, wallet, net, tests, util, policy, primitives
20-qt-gui.patch                  # Qt GUI (BUILD_BITCOIN_QT=OFF by default)
21-build-compat.patch            # CMake 4.x + Boost 1.90 fixes (macOS arm64)

# ── New chain issuance ────────────────────────────────────────────────────────
22-boot-subsidy.patch            # DONE: step-halvings boot component (10M→260 XPI)
23-tail-subsidy.patch            # DONE: nTailSubsidy chainstate var, sqrt-adaptive tail

# ── TODO ─────────────────────────────────────────────────────────────────────
# 24-ifp-removal.patch           # gut minerfund.cpp, remove CoinbaseAddresses from params,
#                                #   remove bad-cb-minerfund validation in ConnectBlock
# 25-op-log.patch                # OP_LOG opcode (expose Log2FixedPoint as script opcode)
# 26-op-sqrt.patch               # OP_SQRT opcode (expose Sqrt64 as script opcode)
# (renumber/replace 12, 13, 14, 15, 17 for new chain identity)
# XX-mitra-tx.patch              # Mitra transaction format (large milestone)
```

Note: `09-minerfund.patch` dropped from series (left in `patches/` for reference; IFP
removed by upcoming `24-ifp-removal.patch`). `08-issuance.patch` will be dropped once
`22-boot-subsidy` and `23-tail-subsidy` are confirmed correct and `24-ifp-removal` is done.

---

## Monorepo Component Status

| Component | Path | Status | Notes |
|---|---|---|---|
| Daemon | `daemon/` | Functional (10.4.10) | Needs new-chain patches |
| TypeScript SDK | `sdk/typescript/` | Legacy | Needs full rewrite (issue #2) |
| Dart SDK | `sdk/dart/` | Partial | Extracted from Vase, incomplete |
| Rust SDK | `sdk/rust/` | Partial | Chronik client from bitcoinsuite |
| cashwebd | `cashweb/` | Functional (Rust) | RocksDB; ScyllaDB migration planned |
| Stamp wallet | `wallets/stamp/` | Functional (Electron/Vue) | cashweb SDK embedded, needs extraction |
| Vase wallet | `wallets/vase/` | Functional (Flutter) | Dart SDK embedded |
| GPU miner | `miner/` | Functional (OpenCL) | Works with current daemon |
| Indexer (Chronik) | n/a in V2 yet | Missing | Funded by Lotus project; eCash pulled it in-process and stripped NNG; needs restoration — see architecture-decisions.md |
| Indexer (Fulcrum) | `indexer/` | Functional | Electrum-compatible; fallback until Chronik is restored |

### SDK Refactor (separate from chain work)

Target SDK dependency chain:
```
sdk/typescript/    ← native TS, no bitcore-lib-xpi, native BigInt, Mitra support
      ↑
sdk/cashweb-ts/    ← extracted from stamp/src/cashweb/ (issue #1)
      ↑
wallets/stamp/     ← depends on sdk/cashweb-ts/

sdk/dart/          ← standalone Dart package (issue #4)
      ↑
wallets/vase/      ← depends on sdk/dart/
```

---

## Connection to the Community Letter

The letter to the community (`~/latex/letters/lotus/letter-draft.md`) invites people to
build together. The technical promise implicit in that invitation is:

- The new chain is built correctly from the start
- The developer reward is gone — miners and contributors, not a central address
- The protocol is complete enough to run without mandatory calendar hard forks
- The monetary policy is specified in a paper, not in a multisig wallet

This document is the spec that backs that promise.
