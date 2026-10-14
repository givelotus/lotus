# Lotus Monorepo — Agent & Developer Guide (`AGENTS.md`)

> `CLAUDE.md` is a symlink to `AGENTS.md` so Claude Code, Cursor, Codex, Antigravity, and other agent harnesses share a single source of truth.

## What is Lotus?

Lotus (`XPI`) is a trust-minimized peer-to-peer Proof-of-Work monetary protocol originally forked from eCash (Bitcoin ABC). It features:
- A $\log_2(\text{difficulty})$ issuance curve (`GetBlockSubsidy` in `src/validation.cpp`)
- Base-burn fee splitting (`GetBlockValue` burns 50% of transaction fees; miners and coinbase outputs split the remaining 50% + subsidy)
- Merkleized transaction IDs (`GetId()` / `TxId`) alongside raw-serialization `GetHash()` (`TxHash`)
- 160-byte block headers (`CBlockHeader`) and block-level `vMetadata`
- Taproot (`P2TR` with optional 32-byte state parameter) and `SIGHASH_LOTUS`
- XAddress format (`lotus_` prefix on mainnet)
- Both an **in-process Rust/C++ Chronik indexer** (`-chronik=1`, HTTP/WS on port `8331`) and an **NNG pub/sub interface** (`src/nng_interface/`)

**Mainnet validation:** Current candidate source rebases `v11.6.0` onto `bitcoin-abc` `8c67fe1e85a602204a2ce65aa3b643469c2c3a1d`. All 153 patches replay cleanly. After the mining repair, C++/Rust checks pass and the isolated Chronik node validates mainnet at height 1,400,955. Production and published assets retain the previous `252182e957` build until a separate release/deployment is undertaken.

Trademark: "Lotus" is owned by Shammah Chancellor. All repos under `givelotus/` use it with permission.

---

## Repository Layout

```
lotus/
├── daemon/              # lotusd build system & patch series (mainnet, ecash, bchn, doged)
│   ├── bitcoin-abc-v1-version
│   ├── Makefile
│   ├── scripts/         # setup.sh, build.sh, run.sh, mkpatch.sh, refresh.sh
│   ├── patches/v1/      # 153 verified patches (000–247) for Lotus V1 mainnet (v11.6.0)
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

## Daemon Build & Patch Workflow (`daemon/`)

Workspaces (`daemon/workspace-*`) are **gitignored** local clones created by `make -C daemon setup`. Never commit workspace directories.

| SERIES | Base | Version file | Workspace | Purpose |
|--------|------|-------------|-----------|---------|
| `v1` | `bitcoin-abc` `8c67fe1e85` | `bitcoin-abc-v1-version` | `workspace-v1/` | **Lotus V1 mainnet (`v11.6.0`)** — 153 patches (`000`–`247`) + in-process Chronik (`-DBUILD_CHRONIK=ON`) |
| `ecash` | `bitcoin-abc` `252182e9` | `bitcoin-abc-version` | `workspace-ecash/` | Upstream reference patches |
| `doged` | `doged-io/doged` | `doged-version` | `workspace-doged/` | Dogecoin ABC reference |
| `bchn` | BCHN `v28.0.0` | `bchn-version` | `workspace-bchn/` | Bitcoin Cash Node upstream PR candidates |

### Commands

```bash
# 1. Clone the pinned V1 bitcoin-abc base and apply all 153 patches in order:
make -C daemon setup SERIES=v1

# 2. Compile lotusd and lotus-cli (with -DBUILD_CHRONIK=ON enabled by default for SERIES=v1):
make -C daemon build SERIES=v1

# 3. Run lotusd on mainnet with in-process Chronik enabled:
./daemon/workspace-v1/build/src/lotusd -chronik=1 -daemon
```

Default mainnet ports:
- **P2P**: `10605`
- **JSON-RPC**: `10604`
- **Chronik HTTP / WebSocket**: `127.0.0.1:8331` (override with `-chronikbind=<ip:port>`)

---

## Key Technical Findings & Invariants (Lotus V1 + Chronik on `252182e9`)

### 1. Decoupling Avalanche & `MinerFundPolicy` (`000-decouple-avalanche.patch`)
- **Hard Consensus vs. Soft Parking**: In `bitcoin-abc` `252182e9`, `Chainstate::ConnectTip` (`src/validation.cpp`) runs a `ParkingPolicy` loop after connecting a block when `!IsInitialBlockDownload()`.
- Upstream eCash registers `MinerFundPolicy` inside `ConnectTip`, which computes the expected miner fund from `blockFees + subsidy` (eCash's formula).
- However, Lotus burns 50% of fees (`GetBlockValue = nFees / 2 + nSubsidy`), and Lotus **already enforces its miner fund as a hard consensus rule** inside `ContextualCheckBlock` (`bad-cb-minerfund`). Leaving `MinerFundPolicy` in `ConnectTip` caused `lotusd` to falsely park valid Lotus blocks (`policy-invalid-miner-fund`) the moment `IsInitialBlockDownload()` latched to `false`!
- Therefore, `000-decouple-avalanche.patch` removes both `MinerFundPolicy` and `StakingRewardsPolicy` from `ConnectTip` while preserving the `ParkingPolicy`, `src/avalanche/`, `StakeContenderCache`, and `StakingRewardsPolicy` classes in the codebase (documented inline in `src/validation.cpp`) for optional coordination code.

### 2. Porting In-Process Chronik & RTT to Lotus V1 (`246-port-chronik-and-rtt-for-lotus.patch`)
Upstream Bitcoin ABC's in-process Chronik (`chronik/`) assumes standard 80-byte Bitcoin headers, linear `CBlockHeader + vtx` disk offsets, and double-SHA256 `txid`. Patch `246` adapts Chronik and RTT for Lotus V1 across 5 critical areas:
1. **160-Byte Block Header (`GetHeader`)**:
   - `chronik-cpp/chronik_bridge.cpp::get_block_header()` and `RawBlockHeader` in `chronik-bridge/src/ffi.rs` serialize the 160-byte Lotus `CBlockHeader` (`[u8; 160]`).
2. **`vMetadata` Disk Offset (`GetFirstBlockTxOffset`)**:
   - On disk (`blk*.dat`), Lotus's `CBlock` serializes `CBlockHeader` (160B) + `CompactSize(vMetadata.size())` + each `CBlockMetadataField` + `CompactSize(vtx.size())` before `vtx[0]` (the coinbase tx).
   - `GetFirstBlockTxOffset(const CBlock &block)` in `chronik_bridge.cpp` accounts for the exact serialized size of `block.vMetadata` so Chronik's `BlockTxs` index points to the exact byte offset of every transaction on disk.
3. **Lotus Merkleized `TxId::from_tx` in Rust (`bitcoinsuite-core/src/tx/txid.rs`)**:
   - `TxId::from_tx` matches `CTransaction::GetId`: input leaves are `SHA256d(prevout || nSequence)`; output leaves are `SHA256d(Serialize(CTxOut))`, including value, CompactSize script length, and script bytes. Odd Merkle layers are padded with zero hashes. The final preimage is `nVersion || inputs_root || inputs_height_u8 || outputs_root || outputs_height_u8 || nLockTime` (height 0 for empty trees, 1 for one leaf). It does not nest a script hash or commit a total-output-sats field; earlier prose describing those fields was incorrect.
   - `TxHash` remains the legacy double-SHA256 over raw transaction bytes.
4. **Lotus Taproot (`P2TR`) Indexing in Chronik**:
   - Adds `ScriptType::P2tr` (`PayloadPrefix::P2TR`) in `bitcoinsuite-core` and `chronik-db` to index both non-state Taproot (`OP_SCRIPTTYPE OP_1 <33-byte pubkey>`, 36 bytes) and state-carrying Taproot (`OP_SCRIPTTYPE OP_1 <33-byte pubkey> <32-byte state>`, 69 bytes) by commitment pubkey.
5. **120-Second Real-Time Target (`RTTPolicy`)**:
   - Updates `src/policy/rtt.h` and `src/test/rtt_tests.cpp` from 600s to Lotus's 120s target block spacing (`refTarget * 2.570121946e-12`).

### 3. Upcoming Mainnet Solstice Timebomb (`secondKingsActivationTime`)
- In `src/kernel/chainparams.cpp` (from `245-bump-version-to-10.4.10.patch`), `consensus.secondKingsActivationTime = 1797886200` (**2026-12-21T20:50:00Z**).
- `IsReplayProtectionEnabled` in `src/validation.cpp` defaults to activating at `secondKingsActivationTime`. Before December 21, 2026, a network upgrade patch must either advance/remove the replay-protection timebomb or coordinate the solstice upgrade with active miners.

## V1 Rebase Validation (2026-10-14)

- Mainnet uses `daemon/bitcoin-abc-v1-version`, pinned at `8c67fe1e85a602204a2ce65aa3b643469c2c3a1d`.
- `/tmp/rebase-latest-abc` contains exactly 153 commits matching `daemon/patches/v1/series`. Export patches from each commit's parent-to-commit diff; verify replay using a temporary Git index and compare the final tree with HEAD. Never run setup/reset against the live `daemon/workspace-v1` during this work.
- Fold leftover eCash activation removal and build compatibility repairs into patch 246, near the end of the series, preserving the 153-entry mapping. Lotus historical activation times and `secondKingsActivationTime` remain unchanged.
- The C++ test binary/target is `test_lotus`, not `test_bitcoin`. The upstream CMake Git reflog lookup assumes `.git` is a directory; patch 246 uses `git rev-parse --path-format=absolute --git-path logs/HEAD` to support linked worktrees.
- Original rebase HEAD is retained as `lotus-v1-before-activation-fold-20261014`; the original uncommitted cleanup is saved at `/tmp/lotus-v1-activation-cleanup-20261014.diff`.
- Do not describe the new base as validated or replace release assets until its builds and protocol checks pass. Test with a separate datadir and ports, preserving the running mainnet daemon and its chain data.

- V1 compatibility validation: `lotusd`, `lotus-cli`, `test_lotus`, and `check-crates` build successfully; all 156 `check-bitcoin` targets pass. Chronik's PyO3 0.23 bindings require Python <=3.13; configure with `-DPython_EXECUTABLE=/opt/homebrew/bin/python3.13` and run Rust checks with `PYO3_PYTHON=/opt/homebrew/bin/python3.13` locally. CI selects Python 3.13 and checks C++/Rust before packaging.
- Preserve current upstream initialization/shutdown and node-owned `ValidationSignals`; apply only Lotus settings/NNG hooks to upstream `src/init.cpp`. Restore current optional `GetCoin`, static secp256k1 context, const network-magic lookup, and mempool options APIs in patch 246.
- Mainnet/testnet eCash assumeutxo snapshots are removed; their commitments do not describe Lotus. Regtest keeps a regenerated deterministic Lotus snapshot at height 110, checked by snapshot loading/validation tests. Lotus fixtures use coinbase output 1, 160-byte headers plus serialized metadata, and block Merkle leaves committing to both TxHash and TxId. Tests must preserve V1 BIP143 out-of-range SINGLE behavior rather than importing an upstream consensus change.
- Isolated mainnet replay uses `/tmp/lotus-v1-mainnet-8c67fe1e85`, RPC 11604, P2P 11605 (listening disabled), Chronik 18331. Block files were copied with APFS copy-on-write; original live data is untouched. `daemon/scripts/check-v1-chronik.py` compares headers, TxIds, and raw transaction disk bytes with RPC. Previous release assets and tag are backed up in `/tmp/lotus-v11.6.0-before-8c67fe1e85` before republishing.

- Full isolated mainnet replay on `8c67fe1e85` reached height 1,400,898 with `initialblockdownload=false`; `verifychain 4 1000` returned true. The node accepted fresh blocks after replay. Chronik/RPC comparisons passed at 11 sampled heights (including 15 coinbase/non-coinbase transactions), with exact 160-byte headers and raw disk bytes. The original production node/workspace remains running on the previous base.
- Initial rebase patch chain HEAD before the mining audit: `a055e77a25` (153 commits), tree `a8d838de8fb5887170d6f32e86fed19f8e82c124`; the monorepo daemon rebase was introduced in `d2ef5908`. Tag `v11.6.0` also includes subsequent public-facing cleanup. Initial tag workflow `38570812943` was cancelled to add missing `COPYING` packaging; earlier dispatch run `38570352993` was cancelled to avoid duplicating release builds. Local original tag is retained as `lotus-release-backup/v11.6.0-abc252182e9-20261014`.

- Public-facing cleanup preserves imported component licenses and Git history. Generated Vase server/iOS artifacts and the localhost development `.env` are removed from the current Git index while local files remain available; use `.env.example` for development setup. No live credential or recognizable access token/private key was identified in the tracked-text audit. Historical build files remain in the subtree import; do not rewrite that history as an incidental cleanup.
- The first tag release build was cancelled after a packaging audit found missing upstream `COPYING`. Packaging now includes that file. Public README/build documentation must distinguish tested mainnet daemon behavior from inherited wallet/SDK/miner components.

- Main contains the mainnet implementation and its operational documentation only. Exploratory protocol work is kept on separate branches. Preserve those branch contents when removing unrelated plans from this checkout; do not rewrite history.

- `main` contains the V1 mainnet implementation and its supporting tools only. Exploratory protocol specifications and implementation belong on separate development branches; do not add their files, roadmap, or links to this branch.
- Release CI pins Rust 1.93.0 (`dtolnay/rust-toolchain@1.93.0`, CMake `Rust_TOOLCHAIN=1.93.0`), matching passing local checks. Floating stable selected 1.99.0 and Clippy reported `clone_on_copy` in CXX-generated bridge derives. Pinning the validated toolchain avoids changing bridge ABI/source to satisfy generated-code lint diagnostics.

## Release engineering and component review (2026-10-14)

- Preserve published releases while preparing the new release-engineering candidate. Pending tag-publishing run `38577910924` was cancelled before assets changed; artifact-only dispatch `38581523660` builds the same daemon source without publishing. Existing `v11.6.0` assets remain the earlier `252182e957` build. Do not describe candidate archives as published or overwrite existing releases during this audit.
- Standalone Rust SDK imports `LotusiaStewardship/bitcoinsuite` `d425f277`, with Lotus address/signing/Chronik corrections checked against daemon fixtures and read-only mainnet queries. External-node integration tests still need their documented services/binaries; see `sdk/rust/AGENTS.md`.
- Dart SDK has separate Chronik HTTP/protobuf and Electrum TCP/TLS libraries. DER/compact signature fixes, merkleized TxIds, and 160-byte headers pass 36 tests on isolated Dart 3.13.5; installed Dart/Flutter still use 3.13.3. Electrum validation uses mock servers; Taproot spending and SIGHASH_LOTUS remain absent. See `sdk/dart/AGENTS.md` for protocol boundaries.
- Miner packages now contain an embedded OpenCL kernel and native CLI/desktop binaries. macOS arm64 builds, tests, strict Clippy, archive extraction and ad-hoc signatures pass; other platforms await dedicated CI. Its Rust 1.99.0 toolchain is scoped to `miner/`, preserving the daemon's Rust 1.93.0.
## Daemon target and feature audit (2026-10-14)

- Only V1 has maintained release/mainnet validation. ecash/BCHN candidate 01 is experimental; exact pinned ABC builds but fails three existing mining assertions. Candidate 02 changes only unchecked test insertion and fails ABC test compilation. Keep both out of default executable manifests; opt in through `daemon/scripts/feature-plan.py` for isolated review. Comment-only no-op/placeholder files must never be applied as patches.
- Chronik and NNG are independent V1 build options. Upstream ABC/Doged Chronik needs no mining, chain-limit, ZeroMQ deletion, or Avalanche policy changes. Source removal of ZeroMQ and NNG ports for other targets remain unimplemented. The feature planner fails closed for these ports and reports application separately from build/behavior.
- Record exact upstream revisions and validation evidence in `daemon/docs/support-matrix.md`. `ecash-version` and `lotusd-version` are historical references, not executable source pins. Preserve production workspaces, chain data, and release assets during upstream candidate checks.
## Patch metadata maintenance (2026-10-14)

- V1 patch files now use git format-patch/git am metadata, preserving the153-entry mapping and original source diff bytes. Historical authors/date/message content was recovered for147 entries from givelotus/lotusd history; six newly written explanations retain recorded replay authorship/date and identify their provenance. Historical CRLF is normalized; patch191 quotes its embedded diff to protect mail parsing.
- `daemon/scripts/patch-series.py --check --provenance ... --expect-tree ...` replays in isolation and verifies every recorded intermediate tree. The initial metadata-only migration retained source tree `a8d838de8fb5887170d6f32e86fed19f8e82c124`; subsequent source repairs have separate evidence below.
- Preserve non-PATCH bracketed subjects with git am --keep-non-patch. Export committed changes with mkpatch or export-patch-series.py; require one linear commit per manifest entry and a new candidate output directory. Setup refuses destructive --reset/RESET and dirty workspaces; failures do not promote a partial patch series. See daemon/docs/patch-metadata.md.
- eCash block-construction candidate audit: `daemon/patches/ecash/01-nlogn-block-construction.patch` has no accompanying tests and must not be described as validated. `daemon/tests/check-ecash-block-assembly.py` executes its actual entry-accounting/assembly code in C++ adapters and reproduces stale size/sigcheck/fee accounting and diamond double counting. See `daemon/docs/ecash-block-assembly-review.md` for evidence and coverage limits. Its success means known failures reproduced, not patch approval; do not change published V1 payloads to repair this separate candidate.

- The eCash 01 review also identified byte-identical experimental entry accounting and `addTxs` logic in V1 rebase `a055e77a25`. Passing existing V1 tests and mainnet replay do not validate constrained mining-template resources. Treat the V1 mining correction as an explicit source change, separate from tree-preserving patch metadata work.

## Dogecoin reference audit (2026-10-14)

- `daemon/doged-version` now pins `9690833b8b6709b7a7837bc397f0d04bf3b885d1`; it was floating `master`. The original local `workspace-doged` is untouched. Its local patch series contains an Apple arm64 test-literal compatibility repair and an independent Chronik AuxPoW regression test, not a complete Dogecoin port onto current ABC.
- Isolated doged plus that patch builds with Chronik, passes all 740 C++ cases and six targeted consensus/Chronik functional tests (including generated AuxPoW indexing with Avalanche disabled). No Dogecoin mainnet synchronization or Avalanche network/quorum behavior has been demonstrated.
- `daemon/scripts/doged-rebase-candidate.py` exports unmatched original commits with mailbox metadata and optionally applies them in a new clone. At ABC `8c67fe1e85` versus doged `9690833b8b`, 3,452 equivalent commits are excluded and 414 unmatched commits remain; these are not all Dogecoin-specific. The actual attempt applies seed replacement then stops at the second commit (port-update conflicts). Never label this candidate rebased, buildable or mainnet validated. See `daemon/docs/dogecoin-lineage.md`.
- Explicit V1 mining repair: isolated source commit `e21d07c27a2235667d1450a003e883b246ed5aa3` on parent `a055e77a25`, final tree `e0d4f9c0219739b6774864858c582a8144a443d9`, restores retained upstream fee-index/direct-parent selection and removes broken experimental package accounting. Same final native tests fail five assertions before repair and pass afterward, including a parent/child block with one byte spare. Full `miner_tests` and all 151 `check-bitcoin` targets pass; daemon/CLI/test builds pass with Chronik OFF for this focused C++ run. Follow-up folds this explicit source change into 246 with metadata preserved and requires normal Chronik-enabled release validation. See `daemon/docs/ecash-block-assembly-review.md` for provenance and evidence.
## Block-assembly candidate repair (2026-10-14)

- Behavioral review identified free-descendant, strict-size and fee-delta errors in the experimental assembler. Repair `e21d07c27a2235667d1450a003e883b246ed5aa3` restores the retained upstream implementation in `src/node/miner.cpp`, removes experimental header fields, restores prioritization fixtures and adds a one-byte-spare regression. Fold it into 246, retaining all153 entries and original envelope authors/subjects/dates; do not conflate this intentional source change with metadata-only recovery.
- Candidate patch246 tree is `efc38f2ae92be9835f149bdc55ff1041ac53cc98`; patch247/final source tree is `e0d4f9c0219739b6774864858c582a8144a443d9`. The prior final tree was `a8d838de8fb5887170d6f32e86fed19f8e82c124`. Provenance records old trees and the separate repair commit; first151 patch payloads/trees and historical metadata remain unchanged.
- Native Chronik-OFF builds of lotusd/lotus-cli/test_lotus, miner_tests and all151 check-bitcoin targets pass. The same regression tests before repair fail five assertions. Chronik-enabled integration, new live-node validation and publication are separate; preserve production workspaces, data and releases while those checks run.

## Integrated candidate validation (2026-10-14)

- Current 153-commit V1 workspace HEAD is `6590d92300ba588325628ab7c1a166e392947cff`, source tree `e0d4f9c0219739b6774864858c582a8144a443d9`. The mining correction in 246 restores upstream fee-index/direct-parent selection, with native before/after regression evidence. Chronik-enabled daemon/CLI/test/Rust builds and all 156 C++ checks pass. The isolated node retains mainnet height 1,400,955; 11-block/15-transaction Chronik parity and verifychain level 4 over 1,000 blocks pass. Production remains untouched.
- Choose `11.6.1` only as the next review-candidate version so existing `v11.6.0` assets remain immutable. Do not tag or publish it during preparation. Generated `999-release-metadata.patch` belongs only in the prepared candidate; maintained main keeps its 153 entries. Preserve existing seeds/checkpoints unless explicit verified network inputs are supplied.
- Independent build options use `FEATURES=chronik,nng-off` (or explicit reverse choices); feature planning never silently selects mining/policy patches. Empty ecash/BCHN reference manifests require explicit base-only replay. Setup and refresh replay the Doged compatibility series and refuse destructive workspace resets.
