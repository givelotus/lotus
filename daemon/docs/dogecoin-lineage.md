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

- All **740 C++ test cases / 34,638,071 assertions pass**, including Dogecoin subsidy, AuxPoW, header serialization and inherited coordination unit tests. A printed assumeutxo failure is an intentional negative test; the process exits zero.
- Separate focused runs passed 24 Dogecoin/AuxPoW/compression cases and 11 validation/subsidy cases. AuxPoW fixtures include historical mainnet heights 700,000, 800,000, 3,000,000 and 5,462,519.
- Isolated regtest functional tests `dogecoin_auxpow.py`, `feature_legacy_script_flags.py` and `feature_legacy_script_rules.py` pass.
- **Chronik `chronik_block.py`, `chronik_block_header.py` and the new `chronik_dogecoin_auxpow.py` pass** on isolated regtest. The independent AuxPoW test reruns acceptance/rejection scenarios with Avalanche disabled, then compares full variable-length headers, transaction IDs and raw disk-read transaction bytes against decoded RPC blocks at heights 1 and 2 with different Merkle branch shapes. This verifies generated AuxPoW indexing but does not verify indexing historical mainnet AuxPoW blocks. Its functional harness needs generated `protobuf-chronik`, `PYTHONPATH=<build>/test`, Python `protobuf` matching the installed `protoc` (7.36.2 here), and `websocket-client`; these are installed only in `/tmp/lotus-doged-python-20261014`.
- **Mainnet synchronization is not tested.** No Dogecoin chain-data import or unbounded chain download occurs. Historical fixtures and regtest acceptance do not establish complete mainnet consensus compatibility.
- **Avalanche network behavior is not tested.** Passing inherited unit tests does not prove a deployed Dogecoin quorum or finalization.
- The current-ABC rebase remains blocked at patch 2; the passing build/tests above apply to pinned doged plus the two-line compatibility patch and independent test addition, not to that incomplete rebase.

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
