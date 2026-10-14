# Lotus Monorepo — Agent & Developer Guide (`AGENTS.md`)

> `CLAUDE.md` is a symlink to `AGENTS.md` so Claude Code, Cursor, Codex, Antigravity, and other agent harnesses share a single source of truth.

## What is Lotus?

Lotus (`XPI`) is a trust-minimized peer-to-peer Proof-of-Work monetary protocol originally forked from eCash (Bitcoin ABC). It features:
- A $\log_2(\text{difficulty})$ issuance curve (`GetBlockSubsidy` in `src/validation.cpp`)
- Base-burn fee splitting (`GetBlockValue` burns 50% of transaction fees; miners and coinbase outputs split the remaining 50% + subsidy)
- Merkleized transaction IDs (`GetId()` / `TxId`) alongside raw-serialization `GetHash()` (`TxHash`)
- 160-byte block headers (`CBlockHeader`) and block-level `vMetadata`
- Taproot (`P2TR` with optional 32-byte state parameter) and `SIGHASH_LOTUS`
- XAddress format (`lotus_` prefix on V1 mainnet; `xpi_` planned for V2)
- Both an **in-process Rust/C++ Chronik indexer** (`-chronik=1`, HTTP/WS on port `8331`) and an **NNG pub/sub interface** (`src/nng_interface/`)

**Phase 1 (Complete & Live):** Rebase Lotus V1 mainnet (`v11.6.0`) onto modern `bitcoin-abc` (`252182e957120652960c1f88ec96515c448b1204`) with in-process Chronik enabled and verified against the live mainnet tip (`1,400,645+`).
**Phase 2 (Specified in `docs/lotus-v2/`):** Lotus V2 protocol featuring stripped-witness `CoreTxId` commitments, deterministic UTXO state tree, v1/v2 Script ABI (`OP_SUCCESS_N` upgrade hooks, big-integer arithmetic), and optional Avalanche soft coordination.

Trademark: "Lotus" is owned by Shammah Chancellor. All repos under `givelotus/` use it with permission.

---

## Repository Layout

```
lotus/
├── daemon/              # lotusd build system & patch series (v1 mainnet, v2 new chain, ecash, bchn, doged)
│   ├── bitcoin-abc-version
│   ├── Makefile
│   ├── scripts/         # setup.sh, build.sh, run.sh, mkpatch.sh, refresh.sh
│   ├── patches/v1/      # 153 verified patches (000–247) for Lotus V1 mainnet (v11.6.0)
│   ├── patches/v2/      # Lotus V2 new-chain patches
│   └── docs/            # patch-strategy.md, impcpd-methodology.md, lotus-validation-results.md
├── sdk/
│   ├── dart/            # Dart SDK (extracted from wallets/vase)
│   └── rust/            # Standalone Rust bitcoinsuite / chronik-client crates (see Issue #8)
├── wallets/
│   └── vase/            # Flutter mobile wallet (vase-client Dart) + Go vase-server
├── miner/               # GPU miner (OpenCL)
├── docs/                # Lotus V2 specification (docs/lotus-v2/), architecture decisions, and guides
└── .github/workflows/   # CI/CD: release-daemon.yml builds & publishes lotusd + Chronik binaries on v* tags
```

*(Note: The TypeScript SDK `@frank/nakamoto`, `cashweb`, and the modern multi-coin web/desktop wallet live in `~/repos/frank`. Legacy `sdk/typescript/`, `wallets/stamp/`, `indexer/`, and `cashweb/` were removed from this repo.)*

---

## Daemon Build & Patch Workflow (`daemon/`)

Workspaces (`daemon/workspace-*`) are **gitignored** local clones created by `make -C daemon setup`. Never commit workspace directories.

| SERIES | Base | Version file | Workspace | Purpose |
|--------|------|-------------|-----------|---------|
| `v1` | `bitcoin-abc` `252182e9` | `bitcoin-abc-version` | `workspace-v1/` | **Lotus V1 mainnet (`v11.6.0`)** — 153 patches (`000`–`247`) + in-process Chronik (`-DBUILD_CHRONIK=ON`) |
| `v2` (default) | `bitcoin-abc` `8c67fe1e85` | `bitcoin-abc-v2-version` | `workspace-v2/` | **Lotus V2 new chain** (see `docs/lotus-v2/`) |
| `ecash` | `bitcoin-abc` `252182e9` | `bitcoin-abc-version` | `workspace-v2/` | Upstream PR candidates for eCash ($O(n \log n)$ mining, $O(1)$ mempool, NNG) |
| `doged` | `doged-io/doged` | `doged-version` | `workspace-doged/` | Dogecoin ABC reference |
| `bchn` | BCHN `v28.0.0` | `bchn-version` | `workspace-bchn/` | Bitcoin Cash Node upstream PR candidates |

### Commands

```bash
# 1. Clone bitcoin-abc at 252182e9 and apply all 153 V1 patches in order:
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
- Therefore, `000-decouple-avalanche.patch` removes both `MinerFundPolicy` and `StakingRewardsPolicy` from `ConnectTip` while preserving the `ParkingPolicy`, `src/avalanche/`, `StakeContenderCache`, and `StakingRewardsPolicy` classes in the codebase (documented inline in `src/validation.cpp`) so they can be used for soft coordination or automated faucet/staking payouts in V2.

### 2. Porting In-Process Chronik & RTT to Lotus V1 (`246-port-chronik-and-rtt-for-lotus.patch`)
Upstream Bitcoin ABC's in-process Chronik (`chronik/`) assumes standard 80-byte Bitcoin headers, linear `CBlockHeader + vtx` disk offsets, and double-SHA256 `txid`. Patch `246` adapts Chronik and RTT for Lotus V1 across 5 critical areas:
1. **160-Byte Block Header (`GetHeader`)**:
   - `chronik-cpp/chronik_bridge.cpp::get_block_header()` and `RawBlockHeader` in `chronik-bridge/src/ffi.rs` serialize the 160-byte Lotus `CBlockHeader` (`[u8; 160]`).
2. **`vMetadata` Disk Offset (`GetFirstBlockTxOffset`)**:
   - On disk (`blk*.dat`), Lotus's `CBlock` serializes `CBlockHeader` (160B) + `CompactSize(vMetadata.size())` + each `CBlockMetadataField` + `CompactSize(vtx.size())` before `vtx[0]` (the coinbase tx).
   - `GetFirstBlockTxOffset(const CBlock &block)` in `chronik_bridge.cpp` accounts for the exact serialized size of `block.vMetadata` so Chronik's `BlockTxs` index points to the exact byte offset of every transaction on disk.
3. **Lotus Merkleized `TxId::from_tx` in Rust (`bitcoinsuite-core/src/tx/txid.rs`)**:
   - `TxId::from_tx` implements Lotus's balanced binary SHA256 Merkle tree over inputs (`SHA256d(prevout || nSequence)` hashed with `nLockTime` at height) and outputs (`SHA256d(nValue || SHA256d(scriptPubKey))` hashed with `total_output_sats` at height), combined via `SHA256d(nVersion || inputs_hash || outputs_hash)`.
   - `TxHash` remains the legacy double-SHA256 over raw transaction bytes.
4. **Lotus Taproot (`P2TR`) Indexing in Chronik**:
   - Adds `ScriptType::P2tr` (`PayloadPrefix::P2TR`) in `bitcoinsuite-core` and `chronik-db` to index both non-state Taproot (`OP_SCRIPTTYPE OP_1 <33-byte pubkey>`, 36 bytes) and state-carrying Taproot (`OP_SCRIPTTYPE OP_1 <33-byte pubkey> <32-byte state>`, 69 bytes) by commitment pubkey.
5. **120-Second Real-Time Target (`RTTPolicy`)**:
   - Updates `src/policy/rtt.h` and `src/test/rtt_tests.cpp` from 600s to Lotus's 120s target block spacing (`refTarget * 2.570121946e-12`).

### 3. Upcoming Mainnet Solstice Timebomb (`secondKingsActivationTime`)
- In `src/kernel/chainparams.cpp` (from `245-bump-version-to-10.4.10.patch`), `consensus.secondKingsActivationTime = 1797886200` (**2026-12-21T20:50:00Z**).
- `IsReplayProtectionEnabled` in `src/validation.cpp` defaults to activating at `secondKingsActivationTime`. Before December 21, 2026, a network upgrade patch must either advance/remove the replay-protection timebomb or coordinate the solstice upgrade with active miners.

### 4. Lotus V2 Specification (`docs/lotus-v2/`)
- Always run `python3 docs/lotus-v2/tools/spec_candidate_checks.py` after modifying any file under `docs/lotus-v2/`.
- **CoreTxId Witness Commitment**: `CoreTxId` (`txid`) commits to the structural witness fields (`WitnessStripped`, excluding runtime/signature `vMethodArgs`) to prevent code/branch substitution attacks while keeping `txid` non-malleable and supporting presigned transactions.
- **Avalanche Stake Weighting (`issuance-and-time.md` & `rationale.md`)**: Both reward weight $R(x)$ and voting weight $V(x)$ must remain strictly linear ($f(x_1 + x_2) = f(x_1) + f(x_2)$) with a bounded Top-$K$ active proof table (`AVALANCHE_MAX_ACTIVE_PROOFS`). Pairing superlinear $R(x)$ with sublinear $V(x) = \sqrt{x}$ is vulnerable to stock-vs.-flow 51% quorum Sybil splits and penalizes solo multi-UTXO `avalanche::Proof` construction.


## V2 implementation continuation (2026-10-14)

- The V2 implementation workspace is `daemon/workspace-v2` on base `8c67fe1e85a602204a2ce65aa3b643469c2c3a1d`. Completed patches 000–004 are preserved and exported; the active `daemon/patches/v2/series` lists implemented patches only. The former manifest is preserved in `series-legacy-plan.txt` for the remaining porting plan. Historical patch files remain available.
- Use the dedicated `daemon/bitcoin-abc-v2-version`; keep the shared V1/eCash pin unchanged. Never run setup/reset on an existing workspace as a verification step. Replay patches in a temporary Git index and compare its tree with the implementation HEAD.
- Patch 005 follows the existing chain-identity topic: Lotus daemon/CLI targets and filenames, CMake package branding, client user agent, source links, and corresponding build/test dependencies. Keep the upstream 0.34.1 development version until a V2 release number is specified. Preserve upstream copyright attribution. GUI, wallet-tool and transaction-tool renaming remain separate future work. This development series still has upstream network/genesis parameters and must not be treated as a launch-ready V2 network.
- Candidate smoke fixtures initially had stale hashes for `commitments-and-state.md` and `issuance-and-time.md`. The generator's semantic vectors and its own digest matched exactly. Regenerated only those two stored document hashes with the existing generator; the full spec candidate checker passes. Use an isolated venv with `docs/lotus-v2/tools/requirements.txt` if system Python lacks `blake3`.
- Validation for 005: `cmake -S . -B build -GNinja -DBUILD_QT=OFF -DBUILD_ZMQ=OFF -DBUILD_CHRONIK=OFF`; `ninja -C build -j4 lotusd lotus-cli test_bitcoin`; existing `util_tests/test_FormatUserAgent`; existing `interface_rpc.py` on isolated regtest ports/datadir; daemon/CLI version and help output. All pass. Six-patch temporary-index replay matches workspace HEAD exactly. Chronik and complete C++ suite are not covered by this identity-only validation.
