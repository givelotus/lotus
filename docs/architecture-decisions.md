# Architecture Decisions & Open Questions

## Target Deployment Stack

Goal: minimize operational complexity so community members can actually run nodes.

```
logosd      — chain-agnostic PoW daemon (eCash fork + Lotus patches); replaces lotusd
cashwebd    — unified messaging daemon (keyserver + relay + broadcast merged)
postgres    — persistent structured data
redis(?)    — ephemeral high-throughput data (message queues, routing state)
```

## Open Questions

### Data Layer for cashwebd
- Postgres handles persistent structured data (keys, metadata, accounts)
- High-throughput ephemeral data (message queues, routing state) needs a separate store
- Redis is operationally simple but not good for non-ephemeral data
- ScyllaDB and MongoDB are options but may be overkill at current scale
- **Decision deferred:** Need to inspect existing Rust daemon code to understand actual
  storage patterns before committing to a data layer

### cashwebd Consolidation
- Current state: separate keyserver, relay, and broadcast daemons (unfinished contractor work)
- Target: single `cashwebd` binary with one config, one database connection
- Shared connection pool, shared auth, shared crypto primitives across all three functions
- **Decision deferred:** Need to audit existing Rust code before merging

### Indexer
- Chronik was paid for ($20K) and then pulled into eCash daemon dropping Lotus support
- Options: fork Chronik back out, extend Fulcrum, or build new indexer on bitcoinsuite
- Preference: embed indexer in logosd to reduce daemon count
- **Decision deferred:** Depends on daemon codebase analysis

### logosd vs logond
- Both names are viable; `logosd` feels more natural to say and type
- **Decision deferred:** Settle before renaming patch is written

## Decided

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
09-intmath-opcodes.patch        ← int log (deterministic), int sqrt, POW opcodes
10-bitwise-fixes.patch          ← Tobias's fixes
11-nng-interface.patch
```

### Daemon Strategy
- Track eCash upstream via git rebase on a clean eCash tag
- Lotus-specific changes kept as clean atomic commits
- Pull upstream security fixes selectively
- Redenomination conflicts isolated to chain config layer

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
- `iguana.patch` — unknown, needs investigation (45K)
- `minerfund.patch` — miner fund addresses
- `currencyunit.patch` — denomination
- `amount.patch` — file move (Amount class preserved from original)
- `consensus.patch` — consensus constants
