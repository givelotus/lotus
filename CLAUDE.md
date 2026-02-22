# Lotus Monorepo — Context for Claude

## What is Lotus?

Lotus is a cryptocurrency fork of eCash (Bitcoin ABC). It uses a log2-based issuance curve,
XAddress format (different from eCash/BCH), and an NNG pub/sub interface instead of ZeroMQ.
The current mainnet chain (v6.3.3) is the Phase 1 target. Phase 2 will be a new chain with
Mitra transaction format, updated issuance, and deliberate genesis allocation.

Trademark: "Lotus" is owned by Shammah Chancellor. All repos under givelotus/ use it with permission.

## Repository Layout

```
lotus/
├── daemon/              # lotusd build system (patch-based, see below)
├── sdk/
│   ├── typescript/      # xpi-ts (JS + .d.ts, needs rewrite — see issue #2)
│   ├── dart/            # Dart SDK (extracted from wallets/vase)
│   └── rust/            # Rust chronik client (from bitcoinsuite)
├── cashweb/             # cashwebd — Rust payment server (RocksDB, NNG pub/sub)
├── wallets/
│   ├── vase/            # Flutter wallet (vase-client Dart) + Go vase-server
│   └── stamp/           # Electron/Vue wallet (embeds cashweb-ts SDK)
├── miner/               # GPU miner (OpenCL)
├── indexer/             # Fulcrum (Electrum-compatible indexer, squashed history)
└── docs/                # Architecture decisions + harvested website content
```

## Daemon Build (daemon/)

The daemon is maintained as a patch series on top of an eCash (Bitcoin ABC) base commit.
The workspace (`daemon/workspace/`) is a local git clone — **not tracked in this repo**.

### Quick start

```bash
cd daemon/
make setup        # clone eCash at pinned commit, apply all patches
make build        # cmake + ninja → builds lotusd + lotus-cli
```

### Patch workflow

```bash
# Edit files in daemon/workspace/, then save changes as a patch:
make mkpatch NAME=03-my-feature

# Add the new patch name to daemon/patches/series (in order), then commit.

# To rebase onto a newer eCash commit:
make refresh COMMIT=<new-hash> DESC="eCash v0.27.0"
```

### Key files

- `daemon/ecash-version` — pinned eCash base commit (currently `fa7a44f731`, eCash v0.24.11)
- `daemon/patches/series` — ordered list of patches to apply
- `daemon/patches/01-lotus-mainnet.patch` — cumulative Lotus diff vs eCash v0.24.11 (~52K lines)
- `daemon/patches/02-cmake4-boost190-compat.patch` — fixes for CMake 4.x + Boost 1.90 on macOS

### macOS build dependencies

```bash
brew install berkeley-db boost cmake flatbuffers jemalloc libevent nng ninja openssl protobuf
```

### eCash compatibility notes

The current patch base is eCash v0.24.11. Newer eCash versions (v0.27+) added:
- **Avalanche** consensus (eCash-specific, will NOT be in Lotus)
- **Chronik** — integrated into the daemon as linked Rust code (Lotus uses NNG instead)

When rebasing to newer eCash, cherry-pick security/consensus fixes only; skip Avalanche and Chronik.

## SDK Architecture

### Current state (legacy)
- `sdk/typescript/` — bitcore-lib-xpi (JS + .d.ts, uses bn.js — cross-env polyfill issues)
- `wallets/stamp/src/cashweb/` — TypeScript cashweb SDK embedded in stamp (issue #1: extract)
- `sdk/dart/` — Dart Lotus primitives (extracted from vase-client; issue #4: complete)

### Target state
- Rewrite xpi-ts from scratch in native TypeScript, native BigInt, no bitcore-lib-xpi (issue #2)
- Extract stamp/src/cashweb/ → sdk/cashweb-ts/ as standalone npm package (issue #1)
- Mitra transaction format support deferred until after TypeScript rewrite

## Key Architecture Decisions

See `docs/architecture-decisions.md` for full details. Summary:

- **NNG pub/sub** (not ZeroMQ, not Chronik): daemon publishes flatbuffers over IPC socket
- **cashwebd**: single Rust binary, RocksDB today, ScyllaDB migration planned (issue #3)
- **New chain (Phase 2)**: Mitra-only transactions, log2 issuance, deliberate genesis allocation
- **No UTXO snapshot**: clean PoW launch from genesis; early allocation for genuine contributors only
- **vase-server** (Go): backend for Vase wallet — push notifications, faucet, address watching (issue #6)

## Open GitHub Issues

| # | Title | Priority |
|---|-------|----------|
| #1 | Extract cashweb-ts from Stamp into standalone npm package | medium |
| #2 | Rewrite xpi-ts in native TypeScript (no bitcore-lib-xpi, native BigInt) | high |
| #3 | Migrate cashwebd from RocksDB to ScyllaDB | medium |
| #5 | Restore original Vase UI (pre-Vase-2.0, baseline: commit c35df3b) | medium |
| #6 | Complete vase-server (push notifications, faucet, address watching) | medium |

## Working with this Repo

- Issue tracking: GitHub Issues at github.com/givelotus/lotus
- Architecture decisions: `docs/architecture-decisions.md`
- Developer docs: `docs/` (harvested from givelotus.github.io)
- Letters/correspondence: NOT in this repo (see ~/latex/)
