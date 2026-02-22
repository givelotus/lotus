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

### Indexer
- Chronik was paid for ($20K) and then pulled into eCash daemon dropping Lotus support
- Options: fork Chronik back out, extend Fulcrum, or build new indexer on bitcoinsuite
- Preference: embed indexer in logosd to reduce daemon count
- **Decision deferred:** Depends on daemon codebase analysis

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

### Daemon is Chain-Agnostic (logosd vision)
- The daemon binary is not Lotus-specific — it is a PoW chain framework
- Chain identity lives in config, not in the binary
- Lotus, eCash-compatible, and future chains (Doge-style etc.) are just chain configs
- This makes the project useful beyond Lotus and potentially upstreamable to eCash
- CMake build flags control which chain configs are compiled in:
  ```
  cmake -DLOGOSD_CHAIN=lotus     # Lotus chain
  cmake -DLOGOSD_CHAIN=ecash     # eCash-compatible (for testing)
  cmake -DLOGOSD_CHAINS=all      # all configured chains
  ```

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
Patches applied in order on top of a clean eCash tag:
```
01-rename-to-logosd.patch
02-genesis-block.patch
03-coin-issuance.patch          ← runtime -chain flag controls this
04-address-format.patch         ← runtime -chain flag controls this
05-remove-activations.patch     ← replace with per-chain config
06-block-header.patch           ← larger nonce, extended metadata field
07-txhash-txid-split.patch
08-merkle-fix.patch
09-util-intmath-log2.patch      ← Log2FixedPoint for subsidy calc (Logos Foundation)
10-opcodes-bitwise.patch        ← Tobias's variable-length AND/OR/XOR fix
11-opcodes-bitshift.patch       ← OP_RAWLEFTBITSHIFT (bidirectional via sign)
12-opcodes-new.patch            ← OP_LOG, OP_SQRT (to be written for new chain)
13-nng-interface.patch
```

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
