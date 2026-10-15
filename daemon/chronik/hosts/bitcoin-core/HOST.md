# Optional Bitcoin Core in-process host

This adapter builds and runs Chronik inside exact Bitcoin Core `f13ae519de94394314cd63a27924b0998ac65d45` (32.99.0 development source), using the pinned ABC `1fb7db17c176cdea8a2c60d887891589382ee4e3` export. Native macOS regtest tests pass. It is not selected by default component/release profiles; stock Core artifact CI does not validate this adapter. Mainnet synchronization, Linux/Windows builds, long-running load and power-loss recovery remain untested.

`profile.json` records the native mailbox, both shared-source mailboxes, exact upstream pins, and changed-file hashes. The provider verifies the pristine export before applying the offline source overlays in a private build directory. It checks the installed native adapter files and resultant shared files before compilation, and repeats validation if inputs change. Existing ABC staging is preserved. The export manifest's historical host-status entries remain unchanged to preserve its pinned digest; optional host support is recorded separately in the reviewed profile.

## Build

Apply `node/0001-wire-chronik-lifecycle-and-native-storage.patch` using `git am` to a new exact Core checkout. Export Chronik with the existing exporter; do not apply shared-source mailboxes to that trusted export. CMake stages and applies those itself.

```sh
python3 daemon/scripts/export-chronik.py \
  --upstream /path/to/abc-containing-the-pin --output /new/verified-chronik
RUSTUP_TOOLCHAIN=1.87.0 PYO3_PYTHON=/path/to/python3.13 \
cmake -S /path/to/core -B /path/to/core/build -GNinja \
  -DBUILD_GUI=OFF -DENABLE_IPC=OFF -DWITH_ZMQ=OFF \
  -DBUILD_CHRONIK=ON -DRust_TOOLCHAIN=1.87.0 \
  -DCHRONIK_SOURCE_DIR=/new/verified-chronik \
  -DCHRONIK_PROVIDER_MODULE=/path/to/lotus/daemon/chronik/cmake/ChronikProvider.cmake
RUSTUP_TOOLCHAIN=1.87.0 PYO3_PYTHON=/path/to/python3.13 \
cmake --build /path/to/core/build --target bitcoind bitcoin-cli test_bitcoin -j8
```

For macOS set an explicit `CMAKE_OSX_DEPLOYMENT_TARGET`; it is propagated to Rust's native dependencies. The proof uses 14.0 for both sides and runs on the current host, rather than establishing runtime compatibility with macOS 14. ZeroMQ is independently configurable; the example disables it without deleting its source. NNG, mining policy, mempool limits, consensus and Avalanche are not dependencies. `BUILD_CHRONIK=OFF` builds without Rust and exposes no Chronik CLI arguments.

All source overlays are supplied locally with hashes. Cargo/Corrosion still require their pinned dependency sources/toolchain; this is not a vendored, air-gapped dependency distribution or reproducibility claim. Keep the provider module, profile and mailbox files together in any future offline component source archive.

Run with `-chronik=1 -chronikbind=127.0.0.1:8331`. Supported optional settings include `-chronikcors`, `-chronikscripthashindex`, and `-chronikreindex` (rebuild the index from retained native blocks). Pruning and an unvalidated assumed-utxo chainstate are rejected. `loadtxoutset` is explicitly unavailable while Chronik runs: native disconnect events lack a captured chainstate role, and snapshot handoff must be implemented/tested before enabling it. Electrum/plugin/token options are not advertised by this first Core host.

## Native and Rust boundaries

- Core's typed stripped Txid, full Wtxid, COutPoint/Coin fields and integer CAmount are adapted directly. The separate witness codec computes stripped SHA256d explicitly. Native full transaction bytes travel through a private FFI field and optional immutable-Tx raw storage; existing TxMut serialization and public protobuf schemas stay unchanged. Raw responses retain witness and byte size includes it. Policy virtual size comes from native Core, including sigop adjustments for broadcast rate limits.
- Indexed transaction/undo readers use BlockManager-owned XOR-aware AutoFile handles at absolute offsets. Headers are 80 bytes; transaction positions advance by full `TX_WITH_WITNESS` serialization. Initial indexing uses native block/undo readers and checksum verification; indexed per-transaction undo reads use the same local storage positions without independently recomputing a whole block's undo checksum.
- Optional admission metadata captures input coins and acceptance time under native admission locks before temporary views are cleared. Both single and package paths preserve the snapshot through queued callbacks. No admission decision changes.
- A callback-owned transaction/dependency mirror makes Chronik removals child-first without changing native eviction policy or other subscribers' signal order. Shared descendants are deduplicated with iterative traversal. Mined parents are forgotten without evicting valid unconfirmed children. Extra memory is bounded by mirrored transactions and unique input-parent edges; the small test does not establish load scaling.
- Chronik starts before import, persisted mempool loading and networking. Its HTTP server starts during shared setup, before native observer registration; a Core-only atomic readiness gate rejects broadcasts until registration completes and again before interruption. The gate closes this startup admission gap without changing shared Rust or HTTP schemas. It uses shared subscriber lifetime management; request handlers are interrupted before native teardown, callbacks drain outside cs_main, then the subscriber/indexer closes while native owners remain alive.
- Core has no Avalanche capability. Finality stays false, and requests to await Avalanche finalization return an explicit HTTP 400 rather than synthesizing confirmations or waiting indefinitely.
- Witness scripts initially use the existing `other/<full-script>` contract. P2WPKH, P2WSH and P2TR byte programs are preserved; named witness aliases and Bech32 client helpers are not added. Lotus's Taproot format is not substituted.

## Crash ordering and performance

The first actual SIGKILL test found Chronik retaining height 104 while Core restored height 102 and did not know the indexed tip hash. The adapter now flushes native block/undo files and synchronously persists block-index metadata **before** committing that block to Chronik. All dirty files referenced by that metadata commit are flushed, including newer files behind a queued callback; small-file rollover is exercised before the crash. Core may still restore an earlier UTXO tip: retained block/index/undo data lets Chronik rewind and Core replay it. Normal startup and Chronik-only reindex use the existing resync path.

This conservative first implementation performs a native flush per connected block. It favors a recoverable index boundary; batching needs a separately tested durable checkpoint/rollback design and performance measurements. SIGKILL recovery passes, but it is not a hardware power-loss test. The pre-fix failure log is retained as historical evidence, not a validated source/release.

## Verification

[The evidence record](../../../docs/evidence/bitcoin-core-chronik-host-20261014.json) contains exact source/replay trees, hashes, reproduction commands and results. `tests/host_regtest.py` refuses an existing datadir and owns only its new processes. Generate Python protobuf bindings from the unchanged pinned `chronik.proto`; the proof uses protobuf 7.36.2 and websocket-client 1.8.0 in a private Python environment.

```sh
protoc --proto_path=/path/to/verified-chronik/chronik/chronik-proto/proto \
  --python_out=/new/python-bindings chronik.proto
python tests/host_regtest.py --node /path/to/core/build/bin/bitcoind \
  --datadir /new/private-regtest --protobuf-dir /new/python-bindings \
  --evidence /new/result.json
```

The fresh chain tests headers/genesis, witness native and Chronik broadcast, txid/wtxid and full raw bytes, spent coins/time, confirmed XOR block/undo reads, full-script UTXOs, package acceptance, reorg/resurrection, persisted mempool restart, child-first RBF WebSocket removals, unsupported finality/snapshot requests, active HTTP/WebSocket shutdown, SIGKILL restart, Chronik-only reindex and native verifychain. Resource evidence is one small process's observed RSS and bounded shutdown, not a leak/throughput benchmark.

Focused existing native suites and Rust workspace tests/strict Clippy pass as recorded. The unchanged all-target bitcoinsuite-core test warning from the codec foundation remains explicitly qualified; no lint suppression or unrelated test repair is introduced. ABC regression uses its unchanged sources with the embedded Chronik directory absent, including its full Rust checks and nine existing Chronik functional tests. Remaining obligations include assumed-valid handoff, production/mainnet replay, cross-platform CI, full-script client conveniences, batched durability performance and long-running resource/reorg testing.
