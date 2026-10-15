# Optional BCHN in-process Chronik profile

This review candidate builds the pinned Bitcoin ABC Chronik indexer directly
inside exact BCHN `abd433abe04f74780744b9eac06731f3690ce68a` (29.2.1). It uses the
existing HTTP/WebSocket protobuf API and an unmodified public Chronik client.
It requires no NNG, mining-priority, mempool-diagnostic or ZeroMQ-removal patch.
The feature and runtime service are both OFF by default.

Native macOS arm64 builds and fresh regtest behavior are validated. Mainnet
synchronization, Linux/Windows, sustained load and reproducible binaries remain
unverified. This profile is outside every default daemon patch manifest and
release workflow.

## Exact source and verification

[profile.json](profile.json) pins the ABC provider revision, BCHN revision,
native source inputs, ordered offline overlay mailbox and every changed shared
source file. Apply the [native host mailbox](node/0001-wire-chronik-lifecycle-and-native-storage.patch)
to a new BCHN checkout at the exact pin. The CMake provider first checks the
pristine export, then verifies native/overlay hashes and applies the
[shared-source mailbox](0001-port-bchn-in-process-bridge.patch) only in its own
host build directory. Reconfiguration reconstructs that directory and rechecks
all inputs; it does not patch the export or a production workspace.

The native source tree is `507c0b98b31ec2b9cb118c33b5448173fd3fd2d9`.
An independent `git am` replay reproduces it. Consensus, primitive and Script
source trees remain identical to BCHN. Removing only the guarded Chronik additions
restores byte-identical upstream `validation.cpp`, `txmempool.cpp` and `init.cpp`.
The original native acceptance, removal and mining policies are retained.

## Chain and API boundaries

BCHN supplies ordinary SHA256d transaction IDs, 80-byte headers, native block/undo
storage and validated spent coins. Complete serialized output scripts are indexed,
including arbitrary scripts and SHA256 script-hash histories/UTXOs.

**CashTokens bytes are preserved as opaque wrapped scripts, not token-aware data.**
The adapter uses native `token::WrapScriptPubKey` for outputs and spent coins, so
raw transactions and token-bearing scripts round-trip exactly. Token prefix and
locking script together form the indexed script. A token-bearing P2SH/P2PKH output
is therefore queried by its complete wrapped script/hash, rather than its bare
locking-script address group. No CashTokens balances, categories, NFT semantics
or token-aware wallet support are claimed. SLP/ALP analysis is disabled too;
`-chroniktokenindex=1` is rejected. Existing protobuf token fields retain the
upstream disabled-index defaults and do not establish absence of native tokens.

Only main, test and regtest representations are accepted; other BCHN networks
are rejected pending their own validation. Pruned operation is rejected.
Electrum, Python indexing plugins and pause controls are not enabled by this
profile. Avalanche finality always reports false; no Avalanche network behavior
or alternate BCHN finalization model is claimed.

The upstream global-only transaction WS subscription has an inherited limitation:
block-confirmed messages are suppressed when no grouped subscriptions exist.
Explicit txid subscriptions work. This adapter preserves the pinned shared
implementation rather than mixing an unrelated common-indexer fix into a host
port. Separate txid subscription streams have no cross-stream ordering guarantee;
the regression checks removal order on one global stream.

## Snapshot and lifecycle rules

Admission captures immutable validated coins and the acceptance timestamp while
native validation still owns the view. An ordered validation-queue job delivers
them after native locks are released. It never reconstructs spent coins from a
later mutable UTXO/mempool state.

Non-block removals snapshot reverse native entry-ID topology, and reorg mempool
imports snapshot the entire reverse topology before clearing it. Conflict vectors
are independently ordered by their input dependency DAG. Thus Chronik removes
descendants before parents, while native removal/event order and policy remain
unchanged. Queue-local observed-tx state filters tentative entries evicted before
successful admission; an actual rejected-child/expiry regression covers this case.
Mined entries leave that state through the connected-block callback.

Startup occurs after chain loading and before import/peer writers start. HTTP
broadcast additionally checks observer readiness, closing the small interval
between the pinned Rust listener starting and native observer registration. Shutdown
interrupts HTTP handlers before native teardown, stops native writers, drains their
callbacks, then unregisters and destroys Chronik before native coin storage is
released. Invalid/partially occupied binds, restart and dependent mempool reorgs
are exercised against fresh isolated data.

## Build and reproduce

Export the exact shared source using [export-chronik.py](../../../scripts/export-chronik.py).
Keep the export unchanged; the provider requires its pinned manifest/file set.
Use CMake 3.19 or newer (tested 4.4.4), Rust 1.87.0 and Python 3.13 for PyO3.

```sh
git clone --no-hardlinks /existing/bchn /new/bchn
git -C /new/bchn checkout abd433abe04f74780744b9eac06731f3690ce68a
git -C /new/bchn am --keep-non-patch /path/to/lotus/daemon/chronik/hosts/bchn/node/0001-wire-chronik-lifecycle-and-native-storage.patch
python3 /path/to/lotus/daemon/scripts/export-chronik.py \
  --upstream /read-only/abc --output /new/shared-chronik
cmake -S /new/bchn -B /new/build -GNinja \
  -DBUILD_CHRONIK=ON -DBUILD_CHRONIK_PLUGINS=OFF \
  -DBUILD_BITCOIN_QT=OFF -DBUILD_BITCOIN_WALLET=OFF -DENABLE_MAN=OFF \
  -DRust_TOOLCHAIN=1.87.0 -DPython_EXECUTABLE=/path/to/python3.13 \
  -DCHRONIK_SOURCE_DIR=/new/shared-chronik \
  -DCHRONIK_PROVIDER_MODULE=/path/to/lotus/daemon/chronik/cmake/ChronikProvider.cmake
PYO3_PYTHON=/path/to/python3.13 RUSTUP_TOOLCHAIN=1.87.0 \
  ninja -C /new/build -j8 bitcoind bitcoin-cli test_bitcoin
mkdir -p /new/regtest-data
/new/build/src/bitcoind -regtest -datadir=/new/regtest-data \
  -chronik=1 -chronikbind=127.0.0.1:18440
```

ZeroMQ can independently remain ON or be set OFF; both build configurations were
checked. A separate Chronik-OFF build requires neither export, provider nor Rust.
The checked enabled build also succeeds with `CARGO_NET_OFFLINE=true` using cached
locked Cargo dependencies and cached pinned Corrosion source. This export does not
vendor third-party registry dependencies. Offline builds must provide those caches
and Corrosion's pinned source/archive; CMake accepts an explicit cached
`FETCHCONTENT_SOURCE_DIR_CORROSION`.

Generate Python bindings from the unchanged pinned schema and run the portable
[test](tests/host_regtest.py) with the public client from that same export:

```sh
mkdir -p /new/protobuf
protoc --proto_path=/new/shared-chronik/chronik/chronik-proto/proto \
  --python_out=/new/protobuf \
  /new/shared-chronik/chronik/chronik-proto/proto/chronik.proto
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/new/bchn/test/functional SRCDIR=/new/bchn \
  /path/to/test-python /path/to/lotus/daemon/chronik/hosts/bchn/tests/host_regtest.py \
  --configfile=/new/build/test/config.ini \
  --chronik-export=/new/shared-chronik --chronik-protobuf-dir=/new/protobuf \
  --tmpdir=/new/isolated-test-data
```

The optional test environment uses [pinned packages](tests/requirements.txt) with
protoc 36.2. Other compiler/runtime pairs must be compatible.
The test verifies the public client hash before loading it and avoids bytecode
writes into the pristine export. It exercises existing-chain bootstrap, RPC/header
and raw-byte parity, full-script histories/UTXOs, token-bearing parent/child spends,
HTTP broadcast/rejection, conflicts, reorgs, expiry including rejected admission,
WS, persisted restart, bind cleanup and `verifychain 4 0`.

[Recorded evidence](evidence/validation-20261014.json) includes native/overlay
identities, builds, 14 focused mining/mempool cases, full native lint, 16 provider
checks and exact logs. The complete BCHN C++ suite and full Rust suite were not
rerun for this host; the Core worker separately rebuilt ABC daemon/CLI/tests and passed full Rust
tests/strict Clippy plus nine existing Chronik functional tests through the
generalized provider.
