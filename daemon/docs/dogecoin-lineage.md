# ABC-derived Dogecoin lineage and rebase evidence

Observed on 2026-10-14. These are reference and candidate sources; this audit does not replace a running node, its data, or published Lotus assets.

## Exact sources

| Source | Revision | Evidence |
| --- | --- | --- |
| [doged-io/doged](https://github.com/doged-io/doged) master | `9690833b8b6709b7a7837bc397f0d04bf3b885d1` | `git ls-remote`; now the immutable `daemon/doged-version` |
| [Bitcoin ABC](https://github.com/Bitcoin-ABC/bitcoin-abc) master | `8c67fe1e85a602204a2ce65aa3b643469c2c3a1d` | `git ls-remote`; Lotus mainnet's existing base |
| [Dogecoin Core](https://github.com/dogecoin/dogecoin) master | `47a303a449999314abcf83bd1fc7e77dd4540fcd` | `git ls-remote`; comparison reference, not built here |
| Previous local doged checkout | `a640b3b427f03ae880720653fe9ab5f62e07ccec` | Left untouched; former version file was floating `master` |
| doged / ABC common ancestor | `5c6880edbc472db2de7f30a07e5c77c1253d1dc3` | `git merge-base`; 2024-06-11 |

The Dogecoin Core README warns that master is an unstable integration branch. An exact observed tip is not a production recommendation.

`SERIES=doged` directly checks out the doged repository. The previously empty local `series` now contains a test-only Apple arm64 compilation repair and an independent Chronik AuxPoW regression test. This is not an independently maintained Dogecoin consensus port patch series against the current ABC pin. Setup must apply that local series after checkout (see the accompanying setup changes).

## Tobias's work is present

This is the requested lineage, rather than a similarly named unrelated fork. Git authorship directly identifies Tobias / Tobias Ruck, including these original commits:

| Change | Original commit |
| --- | --- |
| Height-based coinbase maturity | `2733aed66198a30f0fbfc16b5b04814529f8bb64` |
| Disable BCH/XEC upgrades | `d8c7020d972f7041a748b1030ee614d29e2742fb` |
| Dogecoin difficulty adjustment | `a122ebc5c0d8408fecbaf19f817cb14631a5f434` |
| Dogecoin subsidy | `0627acfef5a82ad2032fa4a401d6775eafe2a4f0` |
| Legacy Script execution | `63a87c9872e453506b8b768657c2e802ffe3ed4f` |
| AuxPoW header representation | `5054d7027f17d7e57d88add031d72ccd2a5bdcf9` |
| AuxPoW commitment validation | `71f2fa8d6fb78a3dcc72610838dbc7771743fded` |
| AuxPoW proof-of-work validation | `cf5f71083c18de0dd9f95e6f523e9f6907c98d52` |
| Chronik header test adaptation | `80c638c5bc3b9d91e682348d5916720d3969650c` |
| Chronik Electrum test fix | `2fde7d8a4039f3368e1ff87912354619ff04b862` |

Source inspection finds Scrypt PoW, AuxPoW chain-ID/coinbase/Merkle checks, pre-DigiShield and DigiShield difficulty rules, historical subsidy, maturity rules and legacy Script flags. Those must travel together for Dogecoin compatibility. A branding/seed/header change alone cannot form a compatible port.

Chronik uses variable-length serialized headers (`Vec<u8>`), reads AuxPoW-bearing headers through `BlockManager`, and derives first transaction offsets from serialized header size. The source has four `dogecoin_auxpow_*` C++ suites and Dogecoin-adapted functional tests. Source presence establishes intended coverage, not test success.

## Rebase candidate, preserving metadata

At these exact tips, `git cherry ABC DOGED` identifies **3,452 equivalent commits** and **414 unmatched commits**. The unmatched set includes upstream changes not present in ABC as well as Dogecoin changes; it is not a list of 414 pure consensus adaptations. Copying all 3,866 commits since the shared ancestor would duplicate substantial upstream history.

Use the diagnostic exporter against a separate clone containing both revisions:

```sh
git clone https://github.com/doged-io/doged.git /tmp/doged-source
git -C /tmp/doged-source fetch --no-tags https://github.com/Bitcoin-ABC/bitcoin-abc.git \
  8c67fe1e85a602204a2ce65aa3b643469c2c3a1d
python3 daemon/scripts/doged-rebase-candidate.py \
  --source /tmp/doged-source --output /tmp/doged-abc-candidate --apply
```

The script refuses an existing output directory. It exports original `git format-patch` messages, bodies, authors and author dates in topological order, records every original SHA, and tries `git am --3way` only inside its new clone. A failed application exits nonzero and leaves the clone and log for review. It starts no daemon and publishes nothing. The apply invocation preserves subject prefixes and author dates, and sets each new committer date to its author date; it does not claim to retain the original committer identity or original commit hash.

The actual trial applies `381fdb486f` (seed replacement) and stops at `acfb45f8e5` (port update). Five conflicts occur in the removed Electrum Docker fixture, Electrum regtest utility, address-manager tests, network tests and functional-test utilities. This is **not a clean application, completed rebase, or buildable candidate**. Resolving these by blindly choosing either side could discard current upstream test behavior.

The next port step is to classify the unmatched list, discard superseded upstream-only changes, then rebuild separate dependency layers: Dogecoin consensus/serialization; network identity; Chronik AuxPoW integration; wallet/Script compatibility; optional coordination. Preserve each original rationale and record intentional adaptations. Chronik indexing must not acquire a dependency on enabling Avalanche or unrelated mempool policy changes.

## Avalanche claims require separate evidence

Commit `a640b3b427f03ae880720653fe9ab5f62e07ccec` changes Avalanche parameters. That proves parameter edits, not a deployed quorum, liveness, finalization, or protection on Dogecoin mainnet. Current source disables miner-fund and staking-reward consensus settings on Dogecoin mainnet/testnet; inherited parking-policy code remains. Preconsensus modes have defaults of false in `src/avalanche/avalanche.h`.

Any future claim must separately demonstrate normal Dogecoin tip acceptance with Avalanche disabled, valid proof registration and Sybil/stake rules, actual multi-peer polling/finalization, and behavior under conflicting or missing quorum. This audit claims none of those network properties.

## Validation boundary

The isolated checkout is `/tmp/lotus-doged-lineage-source`; original `daemon/workspace-doged` and all node data are untouched. CMake configuration with Chronik enabled succeeds on Apple arm64, Python 3.13 and Rust 1.93.0. The actual C++ unit-test target is `test_bitcoin`, while executables are `doged` and `doge-cli`. `ENABLE_UPNP` and `ENABLE_NATPMP` were reported unused by this source revision.

The unmodified pin builds `doged` and `doge-cli`, but C++ tests initially fail to compile on Apple arm64: two large unsuffixed decimal literals have type `long`, causing ambiguous multiplication overloads with `Amount`. The compilation patch casts those literals explicitly to `int64_t`, preserving their numeric values and all consensus source. With that patch, the daemon, CLI and C++ unit binary build successfully. Both local mailbox patches replay cleanly onto the exact doged pin with `git am`; their final tree matches the tested checkout (`03ef6997701bc25b9b6a8e9712c20870995c6d9c`).

- All **740 `test_bitcoin` cases / 34,638,071 assertions pass**, including Dogecoin subsidy, AuxPoW, header serialization and inherited chain-finalization integration tests. A printed assumeutxo failure is an intentional negative test; the process exits zero.
- Separate focused runs passed 24 Dogecoin/AuxPoW/compression cases and 11 validation/subsidy cases. AuxPoW fixtures include historical mainnet heights 700,000, 800,000, 3,000,000 and 5,462,519.
- Isolated regtest functional tests `dogecoin_auxpow.py`, `feature_legacy_script_flags.py` and `feature_legacy_script_rules.py` pass.
- **Chronik `chronik_block.py`, `chronik_block_header.py` and the new `chronik_dogecoin_auxpow.py` pass** on isolated regtest. The independent AuxPoW test reruns acceptance/rejection scenarios with Avalanche disabled, then compares full variable-length headers, transaction IDs and raw disk-read transaction bytes against decoded RPC blocks at heights 1 and 2 with different Merkle branch shapes. This verifies generated AuxPoW indexing but does not verify indexing historical mainnet AuxPoW blocks. Its functional harness needs generated `protobuf-chronik`, `PYTHONPATH=<build>/test`, Python `protobuf` matching the installed `protoc` (7.36.2 here), and `websocket-client`; these are installed only in `/tmp/lotus-doged-python-20261014`.
- **Full mainnet synchronization is not tested.** A later bounded follow-up verifies peer download and acceptance through height 100 (details below); no chain-data import or unbounded chain download occurs. These checks do not establish complete mainnet consensus compatibility.
- **Avalanche network behavior is not tested.** Passing inherited unit tests does not prove a deployed Dogecoin quorum or finalization.
- The initial automated current-ABC rebase stops at patch 2; the follow-up below advances an adapted initial segment and records the next conflict. The passing build/tests above apply to pinned doged plus the two-line compatibility patch and independent test addition, not to that incomplete rebase.

Local logs: `/tmp/lotus-doged-configure-20261014.log`, `/tmp/lotus-doged-build-20261014.log` (initial compilation failure), `/tmp/lotus-doged-build-fixed-20261014.log`, `/tmp/lotus-doged-full-unit-20261014.log`, `/tmp/lotus-doged-functional-20261014.log` (three consensus tests pass; first Chronik attempts lacked test dependencies), `/tmp/lotus-doged-chronik-verified-20261014.log`, `/tmp/lotus-doged-chronik-auxpow-20261014.log`, `/tmp/lotus-doged-all-functional-20261014.log`, `/tmp/lotus-doged-candidate-tool-20261014/report.json`. Logs and clones remain outside the repository.

Repeat the successful isolated unit and consensus functional checks after building:

```sh
ninja -C /tmp/doged-source/build -j8 doged doge-cli test_bitcoin
/tmp/doged-source/build/src/test/test_bitcoin --report_level=short
ninja -C /tmp/doged-source/build test/functional/test_runner.py protobuf-chronik
PYTHONPATH=/tmp/doged-source/build/test /path/to/isolated-python \
  /tmp/doged-source/build/test/functional/test_runner.py --jobs=2 \
  --tmpdirprefix=/tmp/doged-check \
  dogecoin_auxpow.py feature_legacy_script_flags.py feature_legacy_script_rules.py \
  chronik_block.py chronik_block_header.py chronik_dogecoin_auxpow.py
```

## Follow-up: bounded mainnet synchronization

A separate node at `/tmp/lotus-doged-bounded-mainnet-20261014` connected to one peer resolved through `seed.multidoge.org`, downloaded and accepted real Dogecoin mainnet blocks **0 through 100**, and automatically stopped at `-stopatheight=100` after **6.5 seconds**. The last live sample recorded 1,156,243 received bytes; the final saved header height was 16,000. Height 100 is `48d8b2a0ea39518a288f739d10c13fb9e4ef713198fc2b7c81d0be2646ebd8d2`.

The experiment imposed a 60-second deadline and sampled a 20-MiB receive threshold; it used isolated RPC `22604`, Chronik `28331`, no listening socket, `-avalanche=0`, `-assumevalid=0`, and **`-minimumchainwork=0` solely to permit bounded early-block synchronization**. These settings are not deployment recommendations. The node still reports `initialblockdownload=true`; this establishes early-chain peer interoperability and local block acceptance, not synchronization to the present mainnet tip or validation across every consensus era.

An offline restart of that same disposable datadir (`-connect=0 -dnsseed=0`) returned **`verifychain 4 0 = true`** and zero peer connections. Chronik raw headers, transaction IDs and raw transaction bytes matched independently decoded RPC blocks at heights **0, 1, 16, 50, 96 and 100**. These early blocks contain no AuxPoW; the separate generated regtest AuxPoW fixture supplies the indexer coverage for that serialization. Both disposable processes shut down cleanly. No pre-existing Doged process or default Dogecoin datadir was found, and no existing workspace or node data was changed.

Checked-in evidence: [`evidence/doged-reference-20261014.json`](evidence/doged-reference-20261014.json). Local evidence: `/tmp/lotus-doged-bounded-mainnet-20261014/report.json`, `console.log`, `offline-check.json`, and `/tmp/lotus-doged-bounded-offline-check-20261014.log`.

## Follow-up: reviewed categories and initial port

The checked-in [`doged-lineage-classification.tsv`](doged-lineage-classification.tsv) covers all 414 unmatched original commits, with paths, an initial review category, suggested disposition and exact ABC same-subject counterpart where present. Reproduce it using `daemon/scripts/doged-classify-lineage.py` and the candidate export report. Categories are deliberately a **heuristic review inventory**, not a claim of fully audited semantic equivalence and not an automatic exclusion list.

| Initial review category | Commits |
| --- | ---: |
| Dogecoin consensus / serialization | 44 |
| Chronik | 52 |
| Network / identity | 32 |
| Wallet / SDK | 24 |
| Avalanche / policy | 53 |
| Build / tests / upstream infrastructure | 169 |
| Applications / documentation | 40 |

**273** entries have exact subject matches in current ABC despite non-equivalent patch IDs. Such entries require reviewing the Dogecoin-specific delta against the counterpart already present; replaying the entire old change would often restore obsolete APIs. Exact subjects are not proof that a patch is upstream-only. Forty application/documentation changes are separated from the minimal daemon-port review. Five historical version bumps should be consolidated into the eventual Doged version. The temporary test skip `3e443c33fb` is superseded by the following fixture addition `e29a68fb43`; checkpoint-only formatting `e43f0aea5c` is superseded by the adapted checkpoint representation.

The isolated port now progresses beyond the first conflict: **23 adapted commits** are retained on local branch `lotus-doged-on-abc-initial-20261014`, HEAD `daf09a9ec28c316e25a80bec8bbd7a88cb3b82b6`, tree `bf971ab0f83cf34656bb6671e8078463099d9ee0`. The 23 mailbox patches, exact base, order and per-tree/metadata provenance are now retained in [`daemon/candidates/doged-on-current-abc-initial`](../candidates/doged-on-current-abc-initial/README.md); the original local exports remain under `/tmp/lotus-doged-current-abc-initial-20261014`. Replay on exact ABC `8c67fe1e85` reproduces every intermediate tree and the final tree. This is still an **incomplete, unbuilt port**, not the validated Doged reference above.

Resolved adaptations preserve current ABC APIs while applying the original Dogecoin intent:

- Port-number conflicts keep current pointer-based address-manager tests and `ToStringAddrPort`; the obsolete deleted Electrum Docker fixture stays deleted.
- Dogecoin checkpoints retain the original hashes while using current `BlockHash::FromHex` / `ChainType` APIs; seed lists remain Dogecoin lists.
- The old checkpoint formatting-only patch is skipped, with that decision recorded here.
- Scrypt test registration keeps current Script interpreter tests. `CBaseBlockHeader` takes over ordinary header hashing as intended; the duplicate old `CBlockHeader::GetHash` is removed.
- Python Scrypt is added without reverting current compact-size serialization. Removed eCash-only DAA algorithms lose their corresponding tests, while current retained algorithms/tests stay present.
- Height-dependent maturity keeps current benchmark transaction padding and Script test fixtures, adds `IsDigishieldEnabled`, and avoids resurrecting the removed unrelated `IsAugustoEnabled` declaration. The wallet-link repair adds only consensus activation, preserving upstream's removal of the old string-encoding translation unit.

The next conflict is original `a06e1c4c831a6f0bbd9b1e3983a0c6b8d4c4594a` (“Unbreak avalanche tests”): a 14-file proof-score-width change intersects current upstream overflow protection and changed proof/test APIs. Resolving this by choosing old code would introduce a demonstrated arithmetic error (below). The maintainable next step is to port safe numeric-width handling into its own optional coordination layer, then continue with the historical Dogecoin DAA/subsidy, legacy Script and full AuxPoW layers before compiling the complete port. Successful mailbox replay of this initial segment alone does not establish any behavioral property of the eventual port.

## Follow-up: optional Avalanche score defect

The pinned Doged source multiplies satoshis by 100 in `uint64_t` before dividing by satoshis per coin. Dogecoin's 10-billion-coin `MAX_MONEY` exceeds the safe intermediate range. A 2-billion-DOGE input scores `15532559262` rather than `200000000000`; `MAX_MONEY` scores `77662796314` rather than `1000000000000`. The existing test repeats an overflowing expected-value expression, so its passing result conceals the defect.

An independent regression using constants, sum scaling and rounding boundaries fails **all five assertions before repair**. The optional mailbox candidate in [`daemon/candidates/doged-avalanche-proof-score`](../candidates/doged-avalanche-proof-score/README.md) divides by the exact satoshis per hundredth coin, preserving clamping and rounding without overflow. It applies independently to the exact Doged pin and is **outside the default Doged series**: Chronik and ordinary synchronization do not depend on this optional proof-scoring change.

After repair, all **139 separate `test-avalanche` cases / 17,717,287 assertions pass**, including the nine proof cases. Separate **`check-pow` passes**, including the Dogecoin DAA suite. The earlier count of 740 cases refers specifically to the entire `test_bitcoin` binary; it did not cover every separately built CMake test suite. Passing these unit tests still establishes neither an operational Avalanche quorum nor Dogecoin network finalization.

Evidence: `/tmp/lotus-doged-avalanche-before-20261014.log`, `/tmp/lotus-doged-avalanche-proof-fixed-20261014.log`, `/tmp/lotus-doged-avalanche-all-fixed-20261014.log`, `/tmp/lotus-doged-pow-tests-20261014.log`.

## Completed current-ABC source candidate (2026-10-14 continuation)

The continuation resolves immutable upstream ABC `1fb7db17c176cdea8a2c60d887891589382ee4e3`, distinct from the older `8c67fe1e85` base above. The [173-patch candidate](../candidates/doged-on-current-abc/README.md) preserves the initial segment and Tobias lineage while adapting current APIs. Exact mailbox replay verifies every intermediate tree and final `b019768499700c6cca14007f211358bd2b0aed82`; integration source is `2ddac16d140df1b9637ec489bffeba287669434e`. Metadata maintenance changes commit IDs without changing source trees.

The candidate retains consensus, wallet/mining and Chronik functionality, with independent repairs for canonical AuxPoW activation, historical Script behavior, fixed block-size consensus, sequential non-CTOR UTXOs, the first DigiShield header-presync transition and aggregate fees. Original authors/dates/messages, 414-entry disposition inventory, modern adaptation provenance and new correction rationale are retained alongside the patches. The old incomplete candidate remains unchanged as historical evidence.

Application, builds, native/functional checks, Chronik parity and network synchronization are reported separately in the [current validation report](doged-current-abc-validation.md). A fresh isolated bounded download accepted **14,942** real mainnet blocks with test-only minimum work disabled; full-tip synchronization is **not** complete. Default-minimum-work observation accepted zero blocks while performing header presync. No earlier height-100 evidence is promoted to a full-sync claim.

The new `getrawunsolvedblock` RPC and explicit Dogecoin OpenCL miner support direct Scrypt mining; actual M5 Max regtest submission succeeded. NNG and merged-mining work-construction RPC remain absent and explicitly documented in the [interface audit](doged-interface-compatibility.md). Optional Avalanche remains independent/default off, with no live-quorum claim. Existing `SERIES=doged` still selects the preserved reference, not this review candidate; production and releases are untouched.

## Headers-only AuxPoW restart correction (2026-10-15)

The maintained series now has **174 patches**, integration source `3047eec50b23b9ad0ceba53e507c034b73ec4efa`, export `59b343a4dcce4259fa8eec8562ec5f0cb2cb3da2`, and final tree `2b378152efca0ea2c578433f348e71db367202b0`. The first 173 mailbox files and their intermediate trees are byte-identical to the preceding review commit.

A default-minimum-work mainnet restart with 918,000 indexed headers but only 14,942 block bodies exposed an inherited Doged flaw: `HeadersSyncState` requested a full AuxPoW header from `CBlockIndex::GetBlockHeader` for a headers-only start point, which tried to read nonexistent block position `(-1,0)`. Patch 0174 supplies only the index's 80-byte base fields to presync, the fields actually used for hash and difficulty checks. Full AuxPoW validation, serialized headers, RPC and Chronik remain on the full-header path. The isolated peer run resumed presync beyond the prior header index; accepted block height is still 14,942. See the [follow-up](doged-current-abc-fullsync-followup.md) for exact evidence and the remaining headers-only RPC limitation.
