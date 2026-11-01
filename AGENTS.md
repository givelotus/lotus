# Lotus — canonical repository and daemon submodules

The permanent working checkout is `/Users/shammah/repos/lotus`. Daemon source
belongs in the registered `daemon/` submodules, with exact pins in
`daemon/sources.json`. `daemon/stack-review.json` records their source ancestry.

- Use `make -C daemon setup SERIES=all`, `source-verify`, and `source-plan`.
  Setup initializes exact submodule commits; it never replays mailboxes or
  overwrites a changed checkout. Builds use `daemon/.build/<series>`.
- Shared engine changes belong in `daemon/ecashd` (`givelotus/bitcoin-abc`).
  Lotus-specific changes belong in `daemon/lotusd` (`givelotus/lotusd`). V1 uses
  the separate `daemon/lotusv1` checkout of that repository. Doged, Core and BCHN
  use `daemon/doged`, `daemon/bitcoind` and `daemon/bitcoincashd`.
- The selected Doged source is the original Doged implementation. Current-ABC
  port candidates remain explicitly separate; do not describe them as selected.
- Setup, sync, autosquash, history-bridge and upstream-extract tooling is in
  `daemon/scripts/daemon_sources.py`; use it before inventing a new workflow.
  Publish required source commits before parent gitlinks. Verify exact source
  trees and tests before promoting behavior changes.
- Temporary PR branches/worktrees have a bounded purpose. Finish by merging or
  explicitly closing the work, accounting for every retained change, and removing
  the temporary checkout. Do not use temporary worktrees as permanent project homes.
- Do not recreate `lotus-v2-optimizations` or `lotus-v2-specifications`. Their
  histories and working changes are preserved outside this repository in
  `/Users/shammah/repos/archive/`.
  Recovery artifacts are outside the tracked source tree. Historical logs may
  retain original paths; those paths are provenance, not operational entrypoints.
- Preserve source history, dirty work, production nodes/data, existing release
  tags and published assets. Source migration does not authorize deployment.
- After a Serena source edit, run `get_diagnostics_for_file` and fix all errors.

Daemon work follows `daemon/AGENTS.md`: tiers, branches, commands, commit identity and
how `-s ours` bridges work.

## What is Lotus?

Lotus (`XPI`) is a trust-minimized peer-to-peer Proof-of-Work monetary protocol originally forked from eCash (Bitcoin ABC). It features:
- A $\log_2(\text{difficulty})$ issuance curve (`GetBlockSubsidy` in `src/validation.cpp`)
- Base-burn fee splitting (`GetBlockValue` burns 50% of transaction fees; miners and coinbase outputs split the remaining 50% + subsidy)
- Merkleized transaction IDs (`GetId()` / `TxId`) alongside raw-serialization `GetHash()` (`TxHash`)
- 160-byte block headers (`CBlockHeader`) and block-level `vMetadata`
- Taproot (`P2TR` with optional 32-byte state parameter) and `SIGHASH_LOTUS`
- XAddress format (`lotus_` prefix on mainnet)
- Both an **in-process Rust/C++ Chronik indexer** (`-chronik=1`, HTTP/WS on port `8331`) and an **NNG pub/sub interface** (`src/nng_interface/`)

**Mainnet candidate:** The custom mining scheduler is corrected in patch 001, with its tests; patch 246 no longer replaces it with upstream selection. The corrected 153-patch chain on `8c67fe1e85a602204a2ce65aa3b643469c2c3a1d` passes clean replay, Chronik-enabled C++/Rust builds, and all 156 C++ checks. A fresh isolated Chronik node replayed mainnet through 1,401,052, accepted fresh blocks, passed 11-block/15-transaction RPC parity and `verifychain 4 1000`. Production and published assets remain untouched; earlier validation of the temporary upstream-restoration tree is historical evidence only.

Trademark: "Lotus" is owned by Shammah Chancellor. All repos under `givelotus/` use it with permission.

---

## Repository Layout

```
lotus/
├── daemon/              # lotusd build system & patch series (mainnet, ecash, bchn, doged)
│   ├── bitcoin-abc-v1-version
│   ├── Makefile
│   ├── scripts/         # setup.sh, build.sh, run.sh, mkpatch.sh, refresh.sh
│   ├── ecashd, lotusd, lotusv1, doged, bitcoind, bitcoincashd   # Source submodules
│   ├── patches/         # Frozen exports and review candidates; see patches/README.md
│   └── docs/            # patch-strategy.md, impcpd-methodology.md, v1-8c67fe1e85-validation.md
├── sdk/
│   ├── dart/            # Dart SDK (extracted from wallets/vase)
│   └── rust/            # Standalone Rust bitcoinsuite / chronik-client crates (see Issue #8)
├── wallets/
│   └── vase/            # Flutter mobile wallet (vase-client Dart) + Go vase-server
├── miner/               # GPU miner (OpenCL)
├── docs/                # V1 specifications, historical architecture decisions, and guides
└── .github/workflows/   # CI/CD: release-daemon.yml builds & publishes lotusd + Chronik binaries on v* tags
```

*(Note: The TypeScript SDK `@frank/nakamoto`, `cashweb`, and the modern multi-coin web/desktop wallet live in `~/repos/frank`. Legacy `sdk/typescript/`, `wallets/stamp/`, `indexer/`, and `cashweb/` were removed from this repo.)*

---

## Historical notes

Earlier findings live in `docs/archive/project-notes-2026-10.md`. They cover the Lotus V1
consensus invariants (the 160-byte header, Merkleized TxIds, Chronik porting and the
`secondKingsActivationTime` replay-protection deadline of 2026-12-21), release engineering,
and the BCHN, Doged and Vase work. Check there before re-deriving any of it.
