# Architecture Decisions & Open Questions

## Target Deployment Stack

Goal: minimize operational complexity so community members can actually run nodes.

```
logosd        — chain-agnostic PoW daemon (eCash fork + Lotus patches)
cashwebd      — unified messaging daemon (registry + relay + p2p); embedded RocksDB → ScyllaDB
vase-server   — Go HTTP server: push notification registration, faucet, location (Gin + GORM)
               does NOT need Lotus primitives; addresses stored as strings; Go is fine here
```

### Language Matrix

| Component | Language | Notes |
|---|---|---|
| logosd | C++ | eCash fork + Lotus patches |
| cashwebd | Rust | bitcoinsuite-core for primitives |
| vase-server | Go | no Lotus lib needed; Gin + GORM; keep as Go |
| sdk/typescript | TypeScript | reference primitive implementation |
| sdk/dart | Dart | mobile (Flutter/Vase); port from TypeScript + shared test vectors |
| sdk/cashweb-ts | TypeScript | cashweb protocol layer (extracted from Stamp) |

With AI assistance, maintaining Dart and TypeScript SDK parity is tractable: write
clean TypeScript with comprehensive test vectors, port to Dart with AI, verify against
the same vectors. The key is good test coverage at the protocol level.

## Open Questions

### Data Layer for cashwebd
- Current: embedded RocksDB — column families: `metadata`, `pkh_by_time`, `topic_messages`,
  `message_payloads`, `topic_burn_txs`
- RocksDB is embedded so only one cashwebd instance can run against the data at a time;
  no HA, no replication, corruption = outage
- **Decision: migrate to ScyllaDB** (Cassandra-compatible, Rust driver available, built-in
  replication, wide-column maps cleanly to existing column families)
- Implement a storage trait abstraction first so the backend is swappable
- See issue #3

### cashwebd Consolidation
- **Resolved:** cashweb is already a single unified binary (`cashwebd-exe`)
- Combines: HTTP API (axum), P2P peer sync, key registry, topic messaging
- Connects to logosd via JSON-RPC for tx broadcasting
- Source: `cashweb/` in the monorepo (pulled from LotusiaStewardship/cashweb)

### Indexer (Chronik)

**History:**
- Chronik was funded by the Lotus project (~$20K) and originally built with NNG as its
  event transport — it ran as a separate service that subscribed to block/tx events from
  lotusd via the NNG pub/sub interface
- eCash subsequently paid to pull Chronik in-process into their daemon and remove the NNG
  dependency, making it eCash-specific and breaking Lotus support
- Our eCash base (v0.24.11) predates Chronik's in-process integration — there is no Chronik
  in the current V2 workspace at all
- The NNG interface (patch 06) is present in V2 and still emits block/tx events; nothing
  consumes them right now

**Current state:**
- `cashwebd` (Rust, in monorepo) connects to logosd via JSON-RPC — this is a different
  service and not a full transaction indexer
- doged has production Chronik (Tobias, EyeOfPython, worked on it) but NNG is stripped
- No patch exists to restore Chronik to V2

**Why NNG matters beyond Chronik:**
NNG was chosen because it serves as an **ecosystem event bus**, not just a Chronik
transport. cashwebd subscribes to NNG for real-time block/tx notifications. Future
services (monitoring, alerting, custom indexers) can subscribe without the daemon
knowing about them. The daemon emits once; any number of consumers listen. Pulling
Chronik in-process breaks this model by making Chronik a special citizen — but it
does NOT mean NNG should be removed. The two are not mutually exclusive.

**Target architecture for V2:**
- Daemon has in-process Chronik for fast indexed queries (single binary, no IPC for
  the hot query path)
- Daemon also emits on NNG pub/sub for all block/tx events (cashwebd, monitoring,
  future subscribers)
- Chronik internally can also publish summary events to NNG if consumers want them
- This is strictly better than the eCash approach (in-process only, NNG stripped)

**Path to get there:**
1. Study doged's Chronik: how it hooks into the daemon's block connection / tx
   acceptance path, what internal events it subscribes to
2. Our NNG patch (06) already handles the emission side; the integration point is
   wiring Chronik's indexer to the same internal events NNG uses
3. Likely requires upgrading eCash base past v0.24.11 to a version that has Chronik,
   then applying our NNG patch on top

**Decision: deferred.** Examine `workspace-doged/src/` after `make setup SERIES=doged`
to understand the Chronik ↔ daemon integration point, then write the plan.

### logosd vs logond
- Both names are viable; `logosd` feels more natural to say and type
- **Decision deferred:** Settle before renaming patch is written

## Decided

### SDK Architecture

#### Current State (inherited, needs restructuring)

Three TypeScript/JavaScript layers currently exist, tangled across repos:

```
bitcore-lib-xpi          — JS crypto primitives (forked from Bitcore); in stamp/local_modules/
                           JavaScript + bolted-on TypeScript definitions; considered legacy
xpi-ts                   — Lotus wallet SDK (TS); wraps bitcore-lib-xpi; in sdk/typescript/
stamp/src/cashweb/       — cashweb protocol layer (your original work); embedded in the app
                           registry client, relay client, wallet, BIP70, stealth, types
```

The cashweb TypeScript module was written inline with Stamp and never extracted as a
standalone package. It is the most valuable piece and needs to be first-class.

#### Target Structure

```
sdk/typescript/          — xpi-ts: rewritten as native TypeScript from scratch
                           NO dependency on bitcore-lib-xpi
                           Covers: addresses, tx construction, signing, script, PSBT
                           Must support Mitra tx format natively

sdk/cashweb-ts/          — extracted from stamp/src/cashweb/ into its own npm package
                           Covers: registry client, relay client, wallet, BIP70, stealth,
                           signed payloads, protobuf types
                           Depends on sdk/typescript/ for Lotus primitives
                           Published independently to npm

sdk/dart/                — extracted from wallets/vase/vase-client/lib/lotus/
                           Currently embedded in Vase; same pattern as cashweb-ts in Stamp
                           Contains: BIP39, crypto, encoding, script, transaction, block
                           Referenced from Vase via pubspec path dependency (monorepo-native)
                           Evaluate pc-dart (schancel/pc-dart, PointyCastle fork) vs upstream
```

#### Decisions

- **bitcore-lib-xpi is deprecated** — JavaScript + type definitions, not native TS;
  depends on bn.js which has cross-environment bignum issues (required webpack inject
  hacks and local_modules workaround in Stamp to function in browser + Node); do not
  invest further; rewrite xpi-ts from scratch in native TypeScript using native BigInt instead
- **Mitra support is a separate milestone** — rewrite xpi-ts cleanly first; add Mitra
  tx format support after the format is finalized and format discussion is complete;
  monorepo makes the cross-library update tractable when ready
- **cashweb-ts extraction is a prerequisite for Mitra** — Mitra changes tx serialization,
  signing, and script evaluation; all three layers must be updated; easier to do with
  clean package boundaries than with cashweb embedded in Stamp
- **Publish to npm independently** — sdk/typescript/ and sdk/cashweb-ts/ should be
  separately versioned npm packages; Stamp and any other client depend on them normally
- **Mitra support must be in sdk/typescript/ first** — everything above it follows

#### Dependency Chain (target)

```
sdk/typescript/  (native TS, no legacy deps)
      ↑
sdk/cashweb-ts/  (depends on sdk/typescript/)
      ↑
wallets/stamp/   (depends on sdk/cashweb-ts/)
wallets/vase/    (depends on sdk/dart/)
```

#### Open Issues
- [ ] #1 — Extract `stamp/src/cashweb/` → `sdk/cashweb-ts/` as standalone npm package
- [ ] #2 — Rewrite `sdk/typescript/` (xpi-ts) from scratch in native TypeScript (no bitcore, no bn.js)
- [ ] #4 — Extract `wallets/vase/lib/lotus/` → `sdk/dart/` as standalone Dart package
- [ ] (future) — Add Mitra tx format to sdk/typescript/ and sdk/dart/ after format is finalized
- [ ] Update Stamp to depend on published `sdk/cashweb-ts/` package
- [ ] Update Vase to reference `sdk/dart/` via pubspec path dependency

### Monorepo
- Single `lotus` monorepo at github.com/givelotus/lotus
- All components live here: daemon, SDKs, wallets, cashweb daemons, specs, docs
- Reduces fragmentation across givelotus, StampChat, and LotusiaStewardship orgs

### Daemon is Chain-Agnostic (logond vision)

The long-term goal is a **logond** framework: a PoW chain daemon where chain identity
lives entirely in config, not in the binary. The three patchsets (V1 Lotus, V2 Lotus,
doged) are all Bitcoin ABC derivatives and share substantial infrastructure. Studying them
in parallel reveals what the common base looks like and what the per-chain layers are.

- Lotus V1 and V2 share: XAddress, NNG, IGUANA merkle, Log2FixedPoint, issuance curve logic
- doged adds: Avalanche consensus layer, production Chronik indexer, Electrum protocol
- All three share: cmake build, eCash P2P layer, script interpreter, UTXO set, mempool

Framework direction:
- Chain identity (magic bytes, ports, address prefix, genesis) → per-chain config
- Protocol features (opcodes, tx format, Mitra) → CMake build flags
- Consensus rules (issuance, IFP, epoch activations) → per-chain config
- Infrastructure (Chronik, NNG, Avalanche) → optional CMake modules

```
cmake -DLOGOND_CHAIN=lotus-v2     # V2 new chain
cmake -DLOGOND_CHAIN=lotus-v1     # V1 mainnet-compatible
cmake -DLOGOND_CHAIN=dogecoin     # Dogecoin-compatible (doged-style)
cmake -DLOGOND_CHAIN=ecash        # eCash (for testing against upstream)
```

This is Phase N work — the V2 chain needs to launch first. But every patch we write
should be designed with clean separation between chain-specific and chain-agnostic code.

### Two-Tier Flag System for Testing
- **Build flags (CMake):** define what protocol features the binary has
  - New opcodes (POW operations, int log, int sqrt)
  - Block header reorganization
  - TxHash/TxID split, merkle fix, bitwise fixes
  - Always on in a Lotus build
- **Runtime flags:** control chain behavior within a single binary
  - `-chain=lotus` / `-chain=ecash` selects coin issuance, address format, denomination
  - Only valid on regtest/testnet — rejected on mainnet
  - Allows existing eCash functional tests to run against a Lotus binary unchanged

### Activation Scaffolding → Chain Config
- Historical fork activations (P2SH, etc.) move out of hardcoded heights into
  per-chain consensus config
- Lotus config: everything active from genesis block 0
- Other chains: activate features at specific heights as needed
- Makes the daemon a proper chain framework, not a Bitcoin ABC derivative

### Patchset Organization

Three parallel build targets in `daemon/`. All share the same `Makefile` and `scripts/`;
the `SERIES` variable selects which workspace and version pin to use:

```
make setup [SERIES=v2|v1|doged]   # clone + apply
make build [SERIES=v2|v1|doged]   # compile
make run   [SERIES=v2|v1|doged]   # run daemon
```

**SERIES=v2 (default) — V2 new chain**
Patches applied in order on top of eCash v0.24.11 (`daemon/patches/series`):
```
01-chain-identity        # rename, network magic, port
02-currency-unit         # XPI denomination
03-xaddress              # Lotus address encoding
04-daa-cleanup           # aserti3-2d only; remove Grasberg/EDA/DAA
05-merkle                # IGUANA interleaved merkle tree
06-nng-interface         # NNG pub/sub replacing ZeroMQ
07-intmath-log2          # Log2FixedPoint (Turner algorithm)
08-issuance              # OLD log2-difficulty formula (superseded by 22+23)
10-script-opcodes        # OP_MULPOW2, OP_RAWLEFTBITSHIFT, etc.
11-taproot               # Taproot
12-chain-params          # REPLACE: remove epoch times
13-genesis               # REPLACE: new genesis
14-checkpoints           # CLEAR
15-fixed-seeds           # REPLACE: project seeds
16-seeder                # seeder tool
17-consensus-activation  # REMOVE: epoch activation system
18-src-build             # CMakeLists
19-misc                  # rpc, wallet, net, tests
20-qt-gui                # Qt GUI (off by default)
21-build-compat          # CMake 4.x + Boost 1.90 fixes
22-boot-subsidy          # height-based step-halvings (10M→260 XPI)
23-tail-subsidy          # sqrt-adaptive stateful tail emission
24-ifp-removal           # IFP disabled; no addresses; mechanism preserved
TODO: 25-op-log, 26-op-sqrt, replace 12/13/14, XX-mitra-tx
```

**SERIES=v1 — mainnet-compatible**
Direct clone of `LotusiaStewardship/lotusd` at pinned tag.
Local experiments saved to `daemon/patches/v1/`.

**SERIES=doged — Tobias's Dogecoin ABC**
Direct clone of `doged-io/doged` at pinned commit.
Reference for Chronik improvements, Avalanche consensus code, and any
opcode/interpreter work Tobias may have added. eCash fork point unknown —
determine by inspecting `git log` in the cloned workspace.
Local experiments saved to `daemon/patches/doged/`.

**Opcode notes:**
- `OP_RAWLEFTBITSHIFT` (0x98): one opcode, positive operand = left shift, negative = right
- `OP_AND/OR/XOR`: byte-level ops on variable-length operands; longer operand modified in place
- `OP_LOG`, `OP_SQRT`: not yet implemented, needed for new chain from genesis

### Daemon Strategy
- Track eCash upstream via git rebase on a clean eCash tag
- Lotus-specific changes kept as clean atomic commits
- Pull upstream security fixes selectively
- Redenomination conflicts isolated to chain config layer

### Future Work / Design Notes

These are not decided but should not be forgotten:

**OP_LOG opcode**
- `Log2FixedPoint` exists in `util/intmath.cpp` as a utility for subsidy calculation
- Exposing this as a script opcode (`OP_LOG`) would be useful for on-chain math
- Turner algorithm (IEEE 2010), deterministic, fixed-point
- Worth adding as a Lotus opcode from genesis

**Integer sqrt opcode (OP_SQRT)**
- Useful as a general script opcode (on-chain geometry, etc.)
- Not required for issuance — issuance uses Log2FixedPoint
- Not yet implemented — needs to be written for the new chain
- Should be deterministic integer sqrt (floor), not floating point

**Issuance curve: Log2-based (decided)**
- Subsidy calculated using `Log2FixedPoint` (Logos Foundation, Turner algorithm)
- Log2 gives diminishing early supply — large initial reward that decays quickly,
  then levels off; encourages early mining without infinite tail inflation
- This is V2 Lotus: the curve is the core economic fix vs V1
- OP_LOG exposes the same primitive to script for on-chain math
- OP_SQRT is separate and optional — not needed for the issuance formula

**Coin distribution (decided)**
- Clean PoW launch from genesis — no UTXO snapshot from old chain
- Free riders (people who received coins without contributing) do not get new coins
  automatically; they mine like everyone else
- Small deliberate early-contributor allocation in genesis block for people who
  demonstrably supported Lotus: funded development, bought and held, did real work
  (not tip-bot recipients, not zero-contribution early miners)
- Allocation recipients to be determined explicitly — not automatic
- PoW is the fair distributor; the genesis allocation is a narrow exception for
  people who are owed something concrete

**Transaction format: Mitra (chosen, exclusive)**
- Designed by Tobias Ruck; implemented as PR #273 in the givelotus.github.io repo (branch `mitra-specification`)
- Activates via `TX_VERSION_MITRA` (version flag in tx nVersion field)
- Key features:
  - **Preamble scripts**: each input has a `scriptPreamble` that runs before the main scriptSig/scriptPubKey evaluation; enables pre-computation and shared state across inputs
  - **Carryover field**: data passed between input evaluations within a single tx; enables stateful cross-input logic without touching the UTXO set
  - **Full introspection opcodes**: inputs can read tx fields (amounts, outputs, other inputs) at script level — no covenant workarounds needed
  - **Native token support**: first-class tokens in the tx format, not OP_RETURN encoding
  - **OP_LOOP / OP_ENDLOOP**: bounded iteration in script (replaces recursive covenant patterns)
- Why Mitra over plain Bitcoin tx format:
  - Bitcoin tx format is 15+ years of accumulated constraints; a new chain is the only window to fix it
  - Introspection + preamble unlock DeFi primitives (AMMs, lending, etc.) without a separate VM
  - Native tokens avoid the fragmentation of protocol-level vs OP_RETURN tokens
  - Near-impossible to change after genesis — commit at launch or not at all
- **Status: chosen; needs TS/Dart SDK work to support new format in client libraries**
- Spec branch: `mitra-specification` in givelotus/givelotus.github.io

**Coin framework (logosd vision)**
- If logosd becomes a general PoW chain framework, others could build chains on it
- Similar to how L2s work on Ethereum but at the L1 daemon level
- Chain identity lives entirely in config + CMake flags
- This has implications for how we structure chain params, opcodes, and tx format

### Archive Patches
Existing lotusd patches saved to `daemon/patches/archive/` for reference:
- `block.patch` — extended block header
- `chainparams.patch` — full Lotus chain config
- `transaction.patch` — TxHash/TxID split, richer sighash data
- `merkle.patch` — CVE fix
- `interpreter.patch` — 64-bit ints, relay=consensus (140K, needs review)
- `intmath.patch` — 64-bit script integers
- `xaddress.patch` — Lotus address format
- `addresses.patch` — address handling
- `activation.patch` — fork activation logic
- `nng-interface.patch` — NNG pub/sub interface
- `iguana.patch` — eCash-only addition (45K); not in lotusd at all, skip
- `minerfund.patch` — miner fund addresses
- `currencyunit.patch` — denomination
- `amount.patch` — file move (Amount class preserved from original)
- `consensus.patch` — consensus constants
