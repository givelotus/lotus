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
| `ecash` | `bitcoin-abc` `1fb7db17` | `bitcoin-abc-version` | `workspace-ecash/` | Upstream reference patches |
| `doged` | `doged-io/doged` | `doged-version` | `workspace-doged/` | Dogecoin ABC reference |
| `bchn` | BCHN `abd433abe0` (29.2.1) | `bchn-version` | `workspace-bchn/` | Current-tip Bitcoin Cash Node upstream candidates |

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
- Superseded temporary mistake (user revoked): isolated source commit `e21d07c27a2235667d1450a003e883b246ed5aa3` on parent `a055e77a25`, final tree `e0d4f9c0219739b6774864858c582a8144a443d9`, restores retained upstream fee-index/direct-parent selection and removes broken experimental package accounting. Same final native tests fail five assertions before repair and pass afterward, including a parent/child block with one byte spare. Full `miner_tests` and all 151 `check-bitcoin` targets pass; daemon/CLI/test builds pass with Chronik OFF for this focused C++ run. It was temporarily folded into 246; the corrected custom implementation now belongs in 001, and the reversal is removed from 246. See `daemon/docs/ecash-block-assembly-review.md` for provenance and evidence.
## Block-assembly candidate repair (2026-10-14)

- Historical temporary upstream-restoration path, explicitly superseded by the corrected custom scheduler: behavioral review identified free-descendant, strict-size and fee-delta errors. Repair `e21d07c27a2235667d1450a003e883b246ed5aa3` restores the retained upstream implementation in `src/node/miner.cpp`, removes experimental header fields, restores prioritization fixtures and adds a one-byte-spare regression. That upstream restoration was the wrong requested fix. Do not repeat it or hide custom-algorithm fixes in 246.
- Historical superseded candidate patch246 tree was `efc38f2ae92be9835f149bdc55ff1041ac53cc98`; patch247/final source tree is `e0d4f9c0219739b6774864858c582a8144a443d9`. The prior final tree was `a8d838de8fb5887170d6f32e86fed19f8e82c124`. Provenance records old trees and the separate repair commit; first151 patch payloads/trees and historical metadata remain unchanged.
- Native Chronik-OFF builds of lotusd/lotus-cli/test_lotus, miner_tests and all151 check-bitcoin targets pass. The same regression tests before repair fail five assertions. Chronik-enabled integration, new live-node validation and publication are separate; preserve production workspaces, data and releases while those checks run.

## Integrated candidate validation (2026-10-14)

- Historical superseded 153-commit V1 workspace HEAD was `6590d92300ba588325628ab7c1a166e392947cff`, source tree `e0d4f9c0219739b6774864858c582a8144a443d9`. The mining correction in 246 restores upstream fee-index/direct-parent selection, with native before/after regression evidence. Chronik-enabled daemon/CLI/test/Rust builds and all 156 C++ checks pass. The isolated node retains mainnet height 1,400,955; 11-block/15-transaction Chronik parity and verifychain level 4 over 1,000 blocks pass. Production remains untouched.
- Choose `11.6.1` only as the next review-candidate version so existing `v11.6.0` assets remain immutable. Do not tag or publish it during preparation. Generated `999-release-metadata.patch` belongs only in the prepared candidate; maintained main keeps its 153 entries. Preserve existing seeds/checkpoints unless explicit verified network inputs are supplied.
- Independent build options use `FEATURES=chronik,nng-off` (or explicit reverse choices); feature planning never silently selects mining/policy patches. Empty ecash/BCHN reference manifests require explicit base-only replay. Setup and refresh replay the Doged compatibility series and refuse destructive workspace resets.
- Restored the original backed-up `v11.6.0` tag object `4e81e5d6a98aa75ee1270a351c9fd83b30bcb329` so it again identifies the source of its preserved assets. Release CI was temporarily disabled for this restoration and immediately re-enabled; asset timestamps/checksums remained unchanged. The temporary rebase tag is retained locally under `lotus-release-candidate-backup/`. Current publication runs only for tag pushes; manual workflow dispatches are artifact-only even when their ref is a tag.

- Chronik ON with NNG OFF also builds in a fresh native build directory; version/help, Ninja commands, dynamic dependencies and undefined symbols confirm no NNG linkage. See `daemon/docs/chronik-without-nng-validation.md`. Miner artifact CI `38582597072` passes Linux, Intel macOS and arm64 macOS packaging; Vase passes 44 Flutter tests/web build and Go race tests/vet/build, with native mobile camera/packaging and PostgreSQL integration still unverified.
- Candidate CI exposed Bash 3.2 nounset behavior for an empty argument array in setup/refresh. Keep argument arrays nonempty and exercise V1 setup with `/bin/bash`; 14 patch-tool tests pass. Build defaults use current ABC/Doged CMake flag names; BCHN disables optional manpages so help2man is not required for daemon/CLI builds.

- Dogecoin follow-up: bounded isolated mainnet peer synchronization accepted blocks 0–100 and stopped in 6.5 seconds, with `assumevalid=0`, Avalanche disabled and temporary `minimumchainwork=0`; this is not full synchronization. Offline `verifychain 4 0` and six Chronik/RPC samples pass. Existing nodes/data remain untouched.
- Doged has separate CMake unit suites: the original 740 count is `test_bitcoin`, not every C++ suite. Follow-up `check-pow` passes. An independent optional proof-score fix demonstrates and repairs overflow above approximately 1.84 billion DOGE; all 139 `test-avalanche` cases pass afterward. Keep that candidate outside the default Doged/Chronik series.
- A classified review inventory covers all 414 unmatched Doged commits; 273 have same-subject ABC counterparts but non-equivalent patches, which need delta review. The current-ABC candidate now retains 23 adapted commits, exact mailbox replay tree `bf971ab0f83cf34656bb6671e8078463099d9ee0`, and stops at the original 14-file Avalanche score-width change. It remains incomplete and unbuilt; do not label it a validated Dogecoin port.

- The 23 adapted initial Dogecoin/current-ABC mailbox patches are persisted under `daemon/candidates/doged-on-current-abc-initial/`, outside selectable daemon series. Its exact base, ordered series and original/adapted commit metadata are recorded; shared replay verifies every intermediate tree and final `bf971ab0f83cf34656bb6671e8078463099d9ee0`. This incomplete, unbuilt source segment is not runnable and inherits none of the validated pinned-Doged runtime claims.

- `make -C daemon help` explains isolated release preparation, preserved network parameters, exact-commit artifact validation, and separate immutable-tag publication, with links to the full release/network documentation. Keep help aligned with the script rather than adding a second publication implementation.

## Independent eCash verification (2026-10-14)

- Check each candidate independently and combinations separately. Historical 01 failed native mining assertions and historical 02 called a nonexistent `SigOpCount` helper; both are superseded by the separately validated corrections below. Current implemented 01/02/04 pass combined checks at the selected pin; files 03/10/11 still have no diff hunks and are not executable patches.
- Candidate 04 applies to declared ABC base `8c67fe1e85` and audit-start current master `1fb7db17c176cdea8a2c60d887891589382ee4e3`, but not the wrapper's older eCash pin `252182e957`. It has no dependency on mining/policy candidates or Chronik. Ordering 02 before 04 conflicts in appended test context; reversing the order applies but does not repair 02 compilation.
- Keep independent partial-diamond finalization coverage as a separate test-only mailbox fixture under `daemon/candidates/ecash-finalized-pruning-verification/`; do not silently alter the submitted 04 payload. Report application, native unit checks, isolated regtest behavior and unmeasured performance separately in `daemon/docs/ecash-independent-verification.md`. Production workspaces, data and releases remain untouched.

## Complete patch message coverage (2026-10-14)

- All tracked real patches now have git mail metadata and a nonempty explanation. The remaining four raw eCash/BCHN 01/02 diffs receive explicitly new maintenance envelopes; original per-patch metadata was unavailable. Recorded 2026 import commits and 2019 simple-mining lineage are identified without attributing adapted modern diffs to that historical commit. All four payloads are byte-identical, and independent raw-vs-mail exact-base replays retain their source trees. Experimental/broken status and unchecked-container-only semantics remain explicit.
- Thirteen subject-only current-ABC Dogecoin candidate commits append labelled maintenance explanations, preserving original subjects/authors/dates and all source payload bytes. The manifest retains old metadata digests; all 23 intermediate trees and final `bf971ab0f83cf34656bb6671e8078463099d9ee0` are unchanged. The candidate remains incomplete and unbuilt. Existing V1 metadata recovery is preserved without redoing it.
- Run `python3 daemon/scripts/check-patch-metadata.py` to audit tracked source patches, meaningful subjects/bodies, author/date envelopes, explicit non-patch placeholders and reference payload hashes. New source corrections must deliberately update the reference evidence with separate validation; metadata enrichment never implies a successful build or behavioral approval.

## Coinbase height review patches (2026-10-14)

- The two ordered mailboxes under `daemon/candidates/coinbase-height/` are standalone review files authorized for main, outside the default V1 series. First fix the vanity-prefix early return, then upgrade parsing with GetOp/CScriptNum. Both consensus activation parameters default to the explicitly disabled INT_MAX sentinel; select a coordinated network activation separately. Preserve historical block acceptance before activation. The parser changes accepted encodings in both directions and requires consensus upgrade review.
- The earlier upstream-assembler restoration in 246 is superseded as the intended mining fix: retain and repair the custom nlogn implementation independently in Lotus 001 and eCash 01. Release candidate PR9 is on hold until the corrected Lotus series is validated; passing CI for the earlier reverted implementation does not approve the replacement.

## Corrected eCash snapshot assembler (2026-10-14)

- Preserve the new custom assembler in eCash 01; do not replace it with upstream code or a tests-only diff. The corrected implementation uses a flat direct-parent snapshot and highest-feerate ready heap, live per-transaction size/sigchecks, individual modified fees and release-on-success dependencies. Expected bound is O(n + m + n log n), not a measured speedup over modern ABC.
- Keep this eCash correction separate from Lotus's own series. Update each chain's patch independently and retain its protocol fixtures. The eCash submission is one mailbox diff including algorithm and native regression tests; the previous failure payload/tree/metadata stays in provenance history.
- Existing old-assembler failure harness is explicitly historical and reads commit `f67257e2`, with `--patch-file` for shallow clones. It must not pretend to test the corrected current assembler. See `daemon/docs/ecash01-corrected-snapshot-assembler.md` for exact before/after scope.
- Main now retains the corrected custom assembler in Lotus 001 and eCash 01 separately. Feature planning reports V1 block construction as integrated, without adding duplicate patches. Rebuild the native release candidate from this corrected series; prior candidate CI and assets do not validate the newly retained implementation.
- The user selected `1fb7db17c176cdea8a2c60d887891589382ee4e3` as the sole eCash acceptance pin. `daemon/bitcoin-abc-version` now selects it; stop spending work on older-base compatibility and retain those results only as historical evidence. Verify individual candidates and their combinations at this exact revision. Lotus keeps its independently validated V1 pin.

## Corrected custom mining scheduler (supersedes temporary upstream restoration)

- User requirement: fix and retain the custom snapshot-based algorithm separately in Lotus `001` and eCash `01`. Do not replace it with upstream's fee-index/backlog assembler or bury its correction in 246. The earlier `e21d07c27a` restoration was an explicit temporary mistake and is superseded.
- Corrected Lotus chain: `0b7939e926b8353ad09d8edc47f355ddacc30502`, source tree `73e9db8356d5f9e617f40d4d9228209e117b08f0`, exactly 153 commits. Isolated source/build: `/tmp/lotus-v1-custom-assembly`; clean series replay: `/tmp/lotus-v1-custom-series`. Original workspaces/nodes remain untouched.
- Patch 001 owns the custom flat dependency snapshot, salted TxId index, ready-node modified-fee heap, and generic native regression tests. Unique direct-parent sets deduplicate shared/repeated parents; each node is enqueued once and each edge released once, only after successful inclusion. Size, sigchecks, modified fee, and finality are checked per transaction against current block state; collected ancestor fees/deltas never subsidize descendants. Expected O(n + m + n log n) time, O(n + m) space; no measured speedup over modern upstream is claimed. CPFP policy is not added.
- Patch 077 receives only context adaptation around newly introduced tests. Patch 246 retains Chronik/RTT/upstream API/Lotus fixture adaptations and has no miner.cpp/miner.h reversal. Every intermediate source tree and envelope metadata hash is reverified with clean `git am`; authors/dates and unchanged commit messages are preserved.
- Identical final native fixtures fail eight assertions on historical broken code (test-only baseline `e6408272a2df57a47314c50f31a66d3c55709376`) and pass on the corrected custom code. Tests cover one-byte/one-sigcheck spare capacity, ten-layer diamonds, repeated-parent inputs, scarce-capacity sibling fee priority, nonfinal parents, and existing free-descendant/fee-delta behavior. Normal Chronik-enabled daemon/CLI/test builds, Rust tests/Clippy, and all 156 C++ check targets pass.
- `daemon/tests/check-ready-heap-assembly.py --source-tree <checkout>` compiles the actual corrected method with counting adapters. At approximately 10,000 nodes, chain/diamonds/fanout/repeated-parent graphs visit exactly m unique edges, check/select n transactions once, and satisfy heap comparison bounds. This is algorithm operation evidence, not a consensus test or wall-clock performance claim.
- New corrected-tree mainnet replay is isolated at `/tmp/lotus-v1-custom-assembly-mainnet-20261014`, RPC 12604, Chronik 19331, P2P listening disabled. Only APFS copy-on-write blk files were copied; no running database or production state was copied/stopped/modified. Replay reached 1,401,052 with initialblockdownload=false, accepted fresh blocks, and passed 11-height/15-transaction Chronik parity plus verifychain level 4 over 1,000 blocks. Read-only getblocktemplate succeeded at height 1,401,053 with an empty live mempool; native fixtures separately cover dependent transactions. Published assets/tags are unchanged; publication still requires the normal reviewed candidate/artifact path.

## Corrected eCash unchecked-container fixture (2026-10-14)

- eCash 02 changes tests only. Use `SigChecks`, name the fixture `unchecked_long_chain_parent_graph`, and verify 100-entry graph links, ancestor/descendant traversal and recursive removal. Never describe `addUnchecked` insertion as normal admission/relay acceptance or removal of a chain-limit policy. Preserve the historical filename with an accurate mailbox subject/body.
- Place 02 before existing finalized-container tests so independent 04 can apply before or after it. At exact current ABC `1fb7db17c176cdea8a2c60d887891589382ee4e3`, every single/pair/triple ordering of corrected 01/02 and unchanged 04 applies and all six full orderings yield the same tree. The superseded `252182e957` reference rejects 04; current eCash maintenance targets exact `1fb7db17c176cdea8a2c60d887891589382ee4e3`. Export 02 on that exact base and report current native/behavioral combination evidence.
- Retain prior 02 compilation failure/raw payload/tree/envelope digests as historical provenance, and update current hashes only with the separately reviewed test change. Files 03/10/11 remain explicit non-executable no-op/placeholders. See `daemon/docs/ecash02-container-and-combinations.md`.

## Upstream Dart crypto and exact wallet amounts (2026-10-14)

- SDK and Vase now use PointyCastle 4.0.0. Both copied ASN.1 implementations are retired; compatibility exports and a small helper adapter delegate to upstream public ASN.1 APIs. Preserve unsigned fixed-width key/compact-signature encoding separately from signed DER. Original upstream PR59 and the credited rewrite are documented in `sdk/dart/docs/crypto-audit-20261014/README.md`.
- Combined integration passes all 40 Dart SDK tests and 59 Flutter wallet tests. Independent crypto evidence includes 513 signatures accepted by OpenSSL and daemon libsecp256k1, 64 OpenSSL signatures accepted by Dart, and byte-identical valid signatures across the dependency upgrade. Exact decimal/BigInt wallet amount conversion avoids lost base units and supports six fractional digits; retain regression coverage for native and JavaScript precision. No real payment, native mobile validation, package publication or deployment is implied.
- Vase deliberately retains PostGIS for planned nearby-user discovery and communication. Keep spatial database capability when modernizing the server; pgx and standard HTTP routing are compatible with that direction. Current dependency/server work must preserve existing data/schema/API and does not authorize implementing discovery/chat or changing live database volumes.
- The Vase backend also intends to deliver notifications and occasionally distribute XPI from funds allocated out of block rewards to mobile wallet users. Funding mechanics, eligibility, amounts and scheduling are undecided. Keep these future policies separate from dependency updates and the data-access refactor; registration data is not authorization for automated payouts or signing. Existing notification delivery is not implemented merely because a PushToken is stored.

## Current BCHN work (2026-10-14)

- User selected latest BCHN tip, resolved to GitLab master `abd433abe04f74780744b9eac06731f3690ce68a` (29.2.1). Use a full immutable pin; v28 validation is historical. Isolated source/build lives under `/tmp/lotus-bchn-tip-*`; never reset the original workspace.
- Current BCHN already removed transitive mempool entry updates/chain limits in 2021 and its direct-parent-count block scheduler visits O(n + m) graph elements, with O(n log n + m) selection work including ordered mapLinks lookups, before CTOR sorting. Do not label either path quadratic without evidence. Ready-heap changes must be justified by fee selection behavior, with no unsupported speedup or CPFP claim. See `daemon/docs/bchn-current-audit.md`.

## BCHN independent NNG candidate (2026-10-14)

- `daemon/patches/bchn/10-nng-interface.patch` now implements an independent default-OFF NNG publisher at BCHN `abd433abe04f74780744b9eac06731f3690ce68a`, outside the default manifest. It preserves ZeroMQ and has no mining/mempool-policy/Chronik dependencies. Native NNG ON/OFF and both-NNG/ZeroMQ-ON daemon/CLI builds pass; real regtest subscriber bytes, sequence, admitted transaction/mining, invalidation and failed-bind restart pass.
- This is explicitly a new BCHN raw-payload protocol, not Lotus FlatBuffers/RPC compatibility. The full legacy interface needs separate storage/spent-coin/undo/RPC-bound work; do not silently present the focused publisher as that complete port. See `daemon/docs/bchn-nng-publisher.md` for exact scope and remaining unverified behavior. Production workspaces, nodes, data and releases remain untouched.

## BCHN mempool review (2026-10-14)

- Audit BCHN on exact `abd433abe04f74780744b9eac06731f3690ce68a`. Its quadratic ancestor/descendant statistics and admission chain limits were removed in April/May 2021; do not port ABC chain-limit tests as an admission optimization or claim literal O(1) insertion.
- A separate diagnostic-only candidate uses the existing topological entry-id index in `CTxMemPool::check`, retaining direct graph/coin/accounting assertions while avoiding redundant all-ancestor walks and dependency retries. It must remain independent from mining/NNG/ZeroMQ features and from historical candidate 02. See `daemon/docs/bchn-mempool-complexity-review.md` for scope and validation.
- BCHN diagnostic mailbox `04-topological-mempool-check.patch` independently applies on the exact acceptance pin, tree `05ca138c5a926581de0006aad4b0450f5f5c5590`; native build, all 126 emitted check-bitcoin suites and focused mempool tests pass. Native temporary counters measure 130,816/32,640 old ancestor visits versus zero on 512/256-node chain checks; counters are not exported, and exact committed source was restored/rebuilt. This is a diagnostic improvement, not default admission policy or measured mining speedup.

## BCHN combined candidate validation (2026-10-14)

- Current-tip BCHN `abd433abe04f74780744b9eac06731f3690ce68a` independently selects ready-backlog fee priority (01), optional topological diagnostic checking (04), and a new default-OFF raw-payload NNG publisher (10). Historical 01/02 are retained for provenance but not selected. No candidate requires another, and default setup remains base-only.
- All 15 application combinations/orders pass; all six triple orders retain tree `bf50633c2575549a6b621cff8e70142df901b2f7`. Combined NNG/ZeroMQ-enabled daemon/CLI/test builds, all 126 C++ suites, real NNG subscriber regtest and mining-prioritization regtest pass. Mainnet synchronization and measured throughput are not claimed. See `daemon/docs/bchn-current-audit.md` and its evidence links.

## BCHN ZeroMQ disable and source removal (2026-10-14)

- User requested two separate ordered review patches: `11-disable-zeromq.patch` changes only CMake's default to OFF, retaining source and explicit ON; `12-remove-zeromq.patch` follows 11 and removes the implementation, public CLI/RPC/logging interface, build discovery/linkage, dependency recipes, docs/examples/tests and CI installation requirements. Historical release notes and opaque keys/test vectors remain intact. Neither patch changes consensus or depends on NNG/mining/mempool candidates.
- Keep upstream `zeromq-off` as the existing flag-only option; experimental `zeromq-default-off` selects 11, and `zeromq-remove` expands into ordered 11 then 12 with the explicit default-off dependency. Reject ON/OFF flags alongside source removal because that CMake option is deleted. Default BCHN setup stays base-only. See `daemon/docs/bchn-zeromq-removal.md` for exact source/tree/build/runtime evidence.

## GitLab upstream submissions (2026-10-14)

- GitLab CLI is authenticated as `schancel` using macOS Keychain. The existing local development SSH public key is registered with GitLab; the GitLab ED25519 host fingerprint was checked against official documentation before adding host trust. Never expose access tokens or private keys in logs or commits.
- Use the fork `schancel/bitcoin-cash-node` for independent upstream submissions against `bitcoin-cash-node/bitcoin-cash-node` master. Keep mining fee priority and optional mempool diagnostic improvements separate; NNG and ZeroMQ interface changes require their own review. Public BCHN submissions do not authorize changing Lotus repository visibility or publishing a release.

- Corrected custom-assembler release candidate `a4e6b837` passes native CI `38621180299` on macOS arm64/Linux x86_64. Downloaded archive hashes/licenses/manifests and byte-identical source archive pass; packaged macOS signatures/library paths and an isolated wallet/Chronik regtest smoke pass. Evidence: `daemon/docs/evidence/v1-release-native-20261014.json`. Publication is still separate; production and existing releases are untouched. Guix binary reproducibility remains pending.

- User-authorized BCHN submissions are open as upstream GitLab MR 2174 (mining ready-child fee priority) and MR 2175 (optional topological mempool diagnostic), independent single commits on `abd433abe0`. See `daemon/docs/bchn-current-audit.md` for exact source commits and submission cleanup. NNG/ZeroMQ are not included; submitted does not mean merged or upstream-CI validated.

- Initial BCHN fork pipelines fail before any jobs because GitLab reports the user is not verified. Account verification must be completed by the user before rerunning CI; do not claim upstream tests ran or bypass the verification requirement.

- User-authorized interface submissions are open as BCHN GitLab MR 2176 (independent default-OFF raw NNG publisher), MR 2177 (ZeroMQ default-OFF), and MR 2178 (complete ZeroMQ source/public API removal; depends on 2177). Submitted source trees exactly match tested exports; see `daemon/docs/evidence/bchn-interface-submissions-20261014.json`. No legacy NNG query protocol or complete Chronik port is implied.

- GitLab account verification is cleared after the user completed it. New MR pipelines were created through the MR-pipeline API: 2174→2948226388, 2175→2948226781, 2176→2948226956, 2177→2948227063, 2178→2948227193. Each now has 33 jobs; the first is running and the others queue behind shared-runner capacity. Earlier verification failures remain historical; current CI results are pending, not successful yet.

## Integrated SDK and Vase refresh (2026-10-14)

- Main now integrates canonical Dart dependency upgrades, the six-chain/16-network Nakamoto-style API, Vase dependency and safe-storage migration changes, and the net/http + pgx/PostGIS backend. Source was byte-identical to the reviewed worker trees before removing one blank line at the SQL fixture EOF. Preserve explicit unsupported API capabilities and the secure-storage v10 migration bridge; native Android/iOS builds and real existing-wallet device migration are still unvalidated.
- Combined main validation: 128 Dart SDK tests and 73 Flutter tests pass; SDK/Vase analyzers have zero errors with 398/528 inherited warning/info diagnostics. SDK JavaScript compilation and actual Node execution pass all 16 networks and exact uint64 amounts. Server Go race tests, vet, server build and migration build pass; real PostgreSQL/PostGIS legacy/fresh-schema tests were independently completed in the worker, not rerun against production. Existing wallets/databases are untouched.
- Standalone Rust SDK upstream remains current at `LotusiaStewardship/bitcoinsuite` master `d425f277`, verified with the remote on 2026-10-14. Modern ABC master is `1fb7db17`; its Chronik crates have a different API layout. Do not replace the standalone signing/NNG/Stratum workspace wholesale or imply all current ABC changes have already been imported.

## Shared Chronik source and host boundary audit (2026-10-14)

- Stock BCHN `abd433abe04f74780744b9eac06731f3690ce68a` contains no Chronik integration. Tobias's public `EyeOfPython/bitcoin-cash-node` NNG branch `11b5e3c46b1e0520ed849af458ed4f38e88eb02f` is a 2021 native node service for an external client/indexer; it is not a dlopen loader and does not cleanly apply to current BCHN. No matching upstream Chronik/NNG merge request was located; avoid claiming it was merged.
- Keep one pinned shared Chronik source/core and thin per-host adaptation as the maintenance direction. Build-time source extraction/CMake integration and runtime separation are distinct work: modern ABC Chronik remains a Rust staticlib/CXX bridge until the owned-data backend contract and standalone NNG client are implemented. Preserve existing in-process operation and NNG clients while reviewing that transition.
- The old standalone `raipay/chronik` NNG architecture is genuine precedent, but its evolved spent-coin/raw-slice protocol is not automatically compatible with the earlier BCHN schema or the new focused BCHN raw publisher. Preserve bootstrap/event ordering, reorg/durability, undo/spent coins, chain header/TxId rules and BCH CashTokens data explicitly. Chronik must not require unrelated mining, chain-limit, ZeroMQ removal or Avalanche policy changes.
- This audit adds design/evidence only, with no current-BCHN Chronik build/sync/runtime claim and no node/data/release modification. See `daemon/docs/shared-chronik-source-and-hosts.md` for exact public source links, proposed boundaries and acceptance obligations.

## Vase arithmetic restoration (2026-10-14)

- User requested the old Venmo-like arithmetic keypad after confirming scanner restoration had left the newer decimal keypad. The restored four-column controls use persistent NumpadModel expression state and exact BigInt rational arithmetic; do not revive historical StatelessWidget mutation or build-time event listeners.
- Historical left-to-right evaluation is retained. Fractions remain exact between operations; only complete nonnegative results exactly representable in six XPI decimals can become amounts. Errors remain visible and cannot submit a previous valid amount. Draft sheets commit once on Done and discard cancellation; request amounts are independent of spendable balance and sender state. Scan/paste use atomic base-unit handoffs. Details and deliberate draft/reopen policy are in wallets/vase/AGENTS.md.
- All 99 Flutter tests, the production web build, and 19 arithmetic tests in headless Chrome pass; analyzer retains 528 inherited notices with zero errors. No native device/storage/camera or transaction broadcast is used for these checks; native deployment remains separate.

## V1 11.6.1 promotion preparation (2026-10-14)

- Regenerate release metadata from current main with `prepare-release.py --candidate`; preserve the 153 maintained patch messages/payloads and append the single generated `999-release-metadata.patch`. Promotion retains this tail on main (154 executable entries total); future preparations replace it. Maintained provenance checks the original 153-entry prefix. Do not fold release-only packaging/version changes into historical patch 247 or alter the published 11.6.0 tag/assets.
- The current-main snapshot reproduces all five PR9 release files and prepared source tree `2f67d96795f6c3e6236fbb189838bc28e420a97e` byte-for-byte, including the source archive validated by native CI `38621180299`. Seeds/checkpoints remain unchanged; no new network observations are invented. See `daemon/docs/evidence/v1-release-promotion-20261014.json`.
- Native source/artifact evidence is reusable, but the publication guard requires successful artifact-only release CI for the exact final reviewed commit on origin/main. Preparation/commit/merge alone cannot publish; after that exact run passes, the reviewed publication operation creates only new tag v11.6.1. Production deployment remains separate.
- Exact-main preflight run `38641060538` stopped before compilation because the metadata test still required six placeholders after BCHN NNG/ZeroMQ implementation reduced them to four. Use an explicit allowlist of remaining historical/unimplemented placeholders, permitting their implementation while rejecting new placeholders; this repair does not change daemon source or prepared archives.

## BCHN NNG compatibility requirement (2026-10-14)

- User rejected MR2176's newly invented raw-payload publisher: it is incompatible with both existing Lotus/Tobias NNG consumers and BCHN ZeroMQ consumers. Its tests/builds do not satisfy the requested NNG port. Do not promote that implementation or describe its successful CI as protocol acceptance.
- Replacement work must port the existing Lotus/Tobias FlatBuffers protocol and request/reply service, including its mining capabilities. Inventory actual schemas, methods, and existing consumers before implementation; verify compatibility with an unmodified existing consumer. Explicitly distinguish chain-specific transaction/header differences, and report unsupported capabilities instead of silently omitting them or inventing another interface. Preserve independent build selection and existing node/data/release state.
- The replacement is being prepared in isolation for review; MR2176 has not been withdrawn or replaced yet. No external corrective comments or MR changes are implied by this local requirement record.

## Dogecoin rebase continuation (2026-10-14)

- The continuation targets immutable Bitcoin ABC `1fb7db17c176cdea8a2c60d887891589382ee4e3`, resolved from the primary remote HEAD. This differs from the preserved initial 23-patch base `8c67fe1e85a602204a2ce65aa3b643469c2c3a1d`; do not overwrite that historical candidate or transfer pinned-Doged validation claims to the new port. Evidence: `daemon/docs/evidence/doged-current-abc-upstream-20261014.json`.
- Work is isolated in monorepo branch `doged-current-abc-complete` and source `/tmp/lotus-doged-complete-source`. Preserve original workspaces, nodes, data, releases and optional mempool diagnostic candidate `ef529501`. Each subsystem worker owns separate source changes and coordinates integration; only the primary integrator edits this monorepo branch.
- Retain Tobias's original authorship/date/message and record adaptations per patch. Keep optional Avalanche score-width/overflow corrections distinct from Dogecoin PoW consensus. Application, build, consensus/regtest, Chronik parity and real mainnet synchronization must have separate evidence; an unfinished validation requirement remains explicit.

## Dogecoin current-ABC completed source candidate (2026-10-14)

- Review work remains isolated on `doged-current-abc-complete`, with 173 mailbox patches under `daemon/candidates/doged-on-current-abc/`. Target ABC is immutable `1fb7db17c176cdea8a2c60d887891589382ee4e3`; preserve the old 23-patch candidate/base and original Doged reference selector. Frozen integration `2ddac16d140df1b9637ec489bffeba287669434e` and metadata-maintained export `29472b1ee39663516050d5e2064cf7fee95245a5` share tree `b019768499700c6cca14007f211358bd2b0aed82`.
- Preserve every intermediate source tree, original author/date/meaningful rationale and explicit 414-entry lineage disposition inventory. Export metadata adds labelled explanations and normalizes CRLF; do not mistake rewritten commit IDs for source changes. Existing patch-series tooling checks every tree and mailbox metadata before promotion.
- New consensus corrections are separate review commits: canonical AuxPoW activation; legacy four-byte numeric operands, DER/cache modes and P2SH evaluation; unconditional 1 MB consensus/mining cap; sequential UTXO availability without CTOR; first DigiShield header-presync target; aggregate fees beyond per-transaction MAX_MONEY. Saturated optional aggregate accounting beyond int64 is documented; equivalence to Core's undefined overflow behavior is not claimed.
- Chronik remains build-selectable and preserves AuxPoW header/disk offsets, signed versions, legacy schema migrations and current APIs. Avalanche stays independent/default off; no compile-time removal or live-quorum claim. NNG and merged-mining work RPC remain explicit gaps, not substituted protocols. Direct `getrawunsolvedblock`/`submitblock` mining and an explicit Dogecoin OpenCL Scrypt backend are implemented; preserve Lotus's miner backend and CPU verification.
- Separate exact replay/build/native/functional/Chronik evidence from synchronization. Real bounded mainnet download accepted 14,942 blocks with test-only `minimumchainwork=0`; default-work run accepted zero blocks while header-presyncing. Full-tip validation remains unfinished. See `daemon/docs/doged-current-abc-validation.md` and evidence JSONs. Production nodes/data/workspaces/releases were not changed; no PR, tag or publication is authorized by this work.

- Final validation at `2ddac16d140d`: Chronik ON/OFF builds; exact 173-patch replay; 756 native cases / 32,817,013 assertions; 14 PoW cases; 17 functional tests; 144 Avalanche / 3 RTT cases; integrated Rust tests all pass. Finalized mining now explicitly topologically orders selected transactions when CTOR is disabled (the preceding combined native run exposed its real radix-order bug). Final binary passes 5-block/103-transaction mainnet parity and `verifychain 4 1000`; prior consensus-identical full downloaded-chain replay retains its exact earlier source identity. All isolated test nodes are stopped.

## Dogecoin headers-only AuxPoW restart follow-up (2026-10-15)

- The prior 173-patch completion is preserved in Git history. Current maintained candidate appends exactly one patch, `0174-Resume-Dogecoin-header-presync-from-headers-only-AuxPoW-indexes.patch`, on immutable ABC `1fb7db17c176cdea8a2c60d887891589382ee4e3`. Integration source `3047eec50b23b9ad0ceba53e507c034b73ec4efa`, metadata export `59b343a4dcce4259fa8eec8562ec5f0cb2cb3da2`, final tree `2b378152efca0ea2c578433f348e71db367202b0`. All first 173 mailbox files and intermediate trees remain byte-identical; replay verifies all 174.
- A resumed default-minimum-work peer run from an isolated datadir with 918,000 indexed headers and 14,942 downloaded blocks previously stalled on full AuxPoW header reads from nonexistent block position `(-1,0)`. Presync now uses a base header reconstructed from index fields; AuxPoW proof checking and actual wire/RPC/Chronik full-header paths remain unchanged. Native regression and real peer presync advance pass. Full-header RPC for an AuxPoW *headers-only* index still returns an error until its block body exists; record this explicit inherited interface gap.
- The current source passes Chronik ON/OFF native builds, 757/757 C++ cases, exact 174-mailbox replay, and final-binary offline Chronik/RPC/raw-disk parity over five real mainnet blocks/103 transactions at accepted height 14,942. Earlier 17 functional, 14 PoW, 144 Avalanche, 3 RTT, and Rust checks belong to the unchanged preceding source segment; do not relabel them as rerun on patch 0174. Default-work peer presync is ongoing in `/tmp/lotus-doged-current-fullsync-20261015` with a disk-space-guarded progress recorder. Continue until tip or report exact accepted height and remaining validation; never call presync height accepted blocks or full synchronization.
- A second isolated test-only historical block download runs in `/tmp/lotus-doged-activation-sync-20261015` with `minimumchainwork=0`, `assumevalid=0`, Chronik enabled and `stopatheight=371340`. Its goal is real block-body validation across DigiShield 145000 and AuxPoW 371337. These boundaries are **not yet reached** at the committed observation; inspect `activation-progress.jsonl` for current accepted height. It is distinct from default-work peer presync and never evidence of full-tip sync. Both runs have disk guards and use only copied early-chain test data.
