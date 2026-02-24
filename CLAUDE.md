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

Four patch series are maintained. Each uses a different upstream base:

| SERIES | Base | Version file | Workspace | Purpose |
|--------|------|-------------|-----------|---------|
| `v2` (default) | bitcoin-abc `252182e9` | `bitcoin-abc-version` | `workspace/` | New Lotus chain (adaptive issuance, OP_LOG/SQRT, Mitra) |
| `v1` | eCash v0.24.11 `fa7a44f73` | `ecash-version` | `workspace-v1/` | Lotus mainnet compatibility (42 patches → lotusd v10.4.10) |
| `doged` | direct clone of doged-io/doged | `doged-version` | `workspace-doged/` | Dogecoin ABC (Tobias Ruck; Mitra author; reference) |
| `bchn` | BCHN v28.0.0 | `bchn-version` | `workspace-bchn/` | Bitcoin Cash Node upstream PR candidates |

Workspaces are **not tracked** in this repo (listed in `daemon/.gitignore`). Recreate with `make setup`.

### Quick start

```bash
cd daemon/
make setup               # v2 (new chain) — bitcoin-abc 252182e9 + v2 patch series
make setup SERIES=v1     # Lotus mainnet — eCash v0.24.11 + 42 patches
make setup SERIES=doged  # direct clone of doged-io/doged
make setup SERIES=bchn   # BCHN v28.0.0 + patches 29-31
make build               # cmake + ninja → lotusd + lotus-cli
```

### Patch workflow

```bash
# Edit files in daemon/workspace/, then save as a patch:
make mkpatch NAME=25-my-feature        # saves to patches/v2/25-my-feature.patch
# Add the name to patches/v2/series (in order), then commit.

# Rebase v2 onto a newer bitcoin-abc commit:
make refresh SERIES=v2 COMMIT=<hash> DESC="bitcoin-abc 2026-03-01"

# Add a newer lotusd release to the v1 series:
make refresh SERIES=v1 COMMIT=v10.4.11 DESC="lotusd v10.4.11"

# Advance doged to a newer release:
make refresh SERIES=doged COMMIT=v0.5.0 DESC="doged v0.5.0"
```

### Key files

- `daemon/bitcoin-abc-version` — pinned bitcoin-abc commit for v2 (`252182e9`)
- `daemon/ecash-version` — pinned eCash v0.24.11 base for v1 (`fa7a44f73`, static)
- `daemon/doged-version` — doged branch/tag (`master`, ~Oct 2025 / v0.4.0)
- `daemon/bchn-version` — BCHN tag (`v28.0.0` / `0bc23ac4`)
- `daemon/lotusd-version` — current lotusd release tracked in v1 (`v10.4.10`)
- `daemon/patches/v2/series` — ordered patch list for new chain (patches 01–31 active; 01–28 need rebase to 252182e9)
- `daemon/patches/v1/series` — 42 patches, all apply cleanly to eCash v0.24.11
- `daemon/patches/ecash/` — ecash-specific versions of patches 29-31 (same base as v2)
- `daemon/patches/bchn/` — BCHN-adapted patches 29-31

### v2 patch status

- **Patches 01–28**: written against eCash v0.24.11 — still need rebase onto bitcoin-abc 252182e9
- **Patches 29–31**: ported to bitcoin-abc 252182e9 API (`src/node/miner.cpp`, `addTxs(const CTxMemPool&)`)

### macOS build dependencies

```bash
brew install berkeley-db boost cmake flatbuffers jemalloc libevent nng ninja openssl protobuf
```

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
