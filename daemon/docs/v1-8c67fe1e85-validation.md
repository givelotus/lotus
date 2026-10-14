# Lotus V1 rebase validation — 2026-10-14

The 153-patch V1 series now targets Bitcoin ABC
`8c67fe1e85a602204a2ce65aa3b643469c2c3a1d`, pinned separately in
`daemon/bitcoin-abc-v1-version`.

The initial rebase workspace HEAD was `a055e77a25`; its tree was
`a8d838de8fb5887170d6f32e86fed19f8e82c124`. Every commit subject matches its
ordered series entry. Applying all exported patches to a temporary Git index
initialized from the new base reproduces that tree exactly.

## Current corrected custom scheduler candidate

The custom snapshot-based mining algorithm is corrected in patch **001**, with
its generic native tests. Patch 077 has context adaptation only; patch 246 keeps
Lotus fixture/API and Chronik compatibility work and no longer reverses the
custom scheduler. The prior upstream restoration in 246 was a temporary mistake
and was revoked by the user. Its tree `e0d4f9c0219739b6774864858c582a8144a443d9`
and older validation results are historical, not the current candidate.

Current source HEAD is `0b7939e926b8353ad09d8edc47f355ddacc30502`; source tree
is `73e9db8356d5f9e617f40d4d9228209e117b08f0`. Exactly 153 commits replay with
plain `git am`, and every intermediate tree and author/date/message digest
matches recorded provenance. See [the mining audit](ecash-block-assembly-review.md)
for the custom design and independent operation counts.

The same final native fixtures fail eight assertions with the historical broken
accumulator and pass with the corrected custom dependency snapshot/ready-fee
heap. Coverage includes exact byte/sigcheck boundaries, layered diamonds,
repeated-parent inputs, scarce-capacity sibling priority, nonfinal parents and
fee-delta/free-descendant policy. Normal Chronik-enabled daemon/CLI/test builds,
Rust tests/Clippy, and all 156 C++ check targets pass.

A **fresh** isolated node replayed mainnet from copied block files through
**1,401,052**, reached `initialblockdownload=false`, and accepted fresh blocks.
Chronik/RPC parity passes at 11 sampled heights and 15 coinbase/non-coinbase
transactions, checking exact 160-byte headers, merkleized TxIds, raw disk bytes
and transaction sizes. `verifychain 4 1000` returns true; `getchaintips` has only
the active tip. Read-only `getblocktemplate` succeeds at height 1,401,053 with an
empty mempool; native fixtures supply dependent-transaction behavior evidence.

Source/build is `/tmp/lotus-v1-custom-assembly`; isolated data is
`/tmp/lotus-v1-custom-assembly-mainnet-20261014` (RPC 12604, Chronik 19331,
listening disabled). Only APFS copy-on-write `blk*.dat` copies were taken.
Existing nodes, original workspaces/databases, tags and published releases were
not stopped or modified. Publication remains a separate candidate/artifact
review step; prior CI artifacts do not contain this newly corrected source.

Evidence logs:

- `/tmp/lotus-v1-custom-assembly-miner-tests-before.log`
- `/tmp/lotus-v1-custom-assembly-build-final.log`
- `/tmp/lotus-v1-custom-assembly-cpp-checks.log`
- `/tmp/lotus-v1-custom-series-verify-final.log`
- `/tmp/lotus-v1-custom-series-operations.log`
- `/tmp/lotus-v1-custom-assembly-chronik-parity.log`
- `/tmp/lotus-v1-custom-assembly-verifychain.log`

The remaining sections retain the original rebase procedure and historical
release context; source identity and current evidence are recorded above.

## Build and tests

Configuration uses Ninja, disables Qt/ZMQ/UPnP/NAT-PMP, and enables Chronik.
On this macOS host, Python 3.13 is selected explicitly because Chronik's
PyO3 0.23 bindings reject Python 3.14:

```sh
cmake -S /tmp/rebase-latest-abc -B /tmp/rebase-latest-abc/build -GNinja \
  -DBUILD_BITCOIN_QT=OFF -DBUILD_BITCOIN_ZMQ=OFF \
  -DENABLE_UPNP=OFF -DENABLE_NATPMP=OFF -DBUILD_CHRONIK=ON \
  -DPython_EXECUTABLE=/opt/homebrew/bin/python3.13 -DRust_TOOLCHAIN=1.93.0
PYO3_PYTHON=/opt/homebrew/bin/python3.13 \
  ninja -C /tmp/rebase-latest-abc/build -j16 \
    lotusd lotus-cli test_lotus check-crates
ninja -C /tmp/rebase-latest-abc/build -j8 check-bitcoin
```

Both commands pass with Rust 1.93.0. Release CI pins that version; floating stable 1.99.0 raises Clippy diagnostics in generated CXX bridge code. Install the validated toolchain with `rustup toolchain install 1.93.0` when reproducing these checks. The C++ suite includes 150 test suites and 156 Ninja
targets. `test_lotus` is the correct binary/target name in the V1 series.
`check-crates` includes Rust tests, documentation tests, and Clippy checks.

Patch 246 absorbs the remaining eCash activation cleanup, upstream API
compatibility fixes, and Lotus-specific test fixture corrections. This follows
the requested 153-entry mapping. The current upstream initialization/shutdown
lifecycle is retained, with Lotus settings and NNG hooks reapplied. Lotus's
historical activations and replay-protection timestamp remain unchanged.

The eCash mainnet/testnet assumeutxo commitments are removed. The regtest
snapshot at height 110 is regenerated from Lotus's deterministic test chain,
and snapshot activation/validation tests pass with it.

## Mainnet and Chronik

The existing production node and `daemon/workspace-v1` source/build files were
left untouched. An isolated node used `/tmp/lotus-v1-mainnet-8c67fe1e85`,
RPC 11604, Chronik 18331, and disabled P2P listening. Its starting block files
were APFS copy-on-write copies of production block files; live databases were
not copied. The isolated node reindexed from genesis and connected to the
production node over local P2P for fresh blocks.

The isolated node reached height **1,400,898**, reported
`initialblockdownload=false`, and accepted fresh blocks after replay.
`verifychain 4 1000` returned `true`.

```sh
python3 daemon/scripts/check-v1-chronik.py \
  --cli /tmp/rebase-latest-abc/build/src/lotus-cli \
  --datadir /tmp/lotus-v1-mainnet-8c67fe1e85 --rpcport 11604 \
  --chronik-url http://127.0.0.1:18331 \
  --heights 0 1 143509 273561 500054 650085 663736 1000027 1400000 1400408
```

This passed for 11 sampled blocks and 15 transactions, including coinbase and
non-coinbase transactions. Checks compare Chronik's indexed tip, exact
160-byte headers, merkleized transaction IDs, raw transaction disk reads, and
transaction sizes with RPC.

Local evidence is retained in `/tmp/lotus-v1-build-final-20261014.log`,
`/tmp/lotus-v1-cpp-tests-final-20261014.log`, and
`/tmp/lotus-v1-chronik-validation-20261014.log`.

## Release

The daemon rebase was introduced in monorepo commit `d2ef5908`.
Tag `v11.6.0` also includes subsequent documentation, tracked-artifact, and
license-packaging cleanup. Earlier release runs were stopped to include upstream `COPYING` and to pin
the locally validated Rust toolchain after generated-code Clippy diagnostics
on floating stable. The final run is recorded below.
It builds Linux x86_64 and macOS arm64, checks C++ and Rust before packaging,
and publishes archives with SHA256SUMS after both builds succeed.

The previous tag is retained locally as
`lotus-release-backup/v11.6.0-abc252182e9-20261014`; previous release assets,
release metadata, and tag object ID are saved in
`/tmp/lotus-v11.6.0-before-8c67fe1e85`.

The subsequent release-engineering audit requires preserving published assets.
Tag-publishing run `38577910924` was cancelled before publication; artifact-only
dispatch `38581523660` builds the candidate without replacing a release.
The existing `v11.6.0` archives still contain the earlier `252182e957` build.
Downloaded candidate archive validation is pending completion of CI.
