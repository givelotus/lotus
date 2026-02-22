# Lotus

Lotus is a trust-minimized peer-to-peer monetary protocol. Monetary policy is governed by proof-of-work mining difficulty as a live, adversarially-revealed signal — no committees, no oracles, no central bank.

This monorepo contains the core Lotus node daemon, patch series, specifications, mining software, and SDKs.

## Structure

```
daemon/         — Lotus node daemon (`lotusd` & `lotus-cli` built on Bitcoin ABC + Lotus patch series, with in-process Chronik & NNG)
  patches/v1/   — Lotus V1 mainnet patch series (`000`–`247`, rebased onto modern Bitcoin ABC 252182e9)
  patches/v2/   — Lotus V2 next-generation chain patch series
sdk/
  dart/         — Dart SDK for mobile wallet development
  rust/         — Rust libraries (bitcoinsuite / chronik-client)
wallets/
  vase/         — Mobile reference wallet (Dart/Flutter + Go vase-server)
miner/          — GPU mining software (OpenCL)
docs/           — Documentation, legacy specs, and Lotus V2 specification (docs/lotus-v2/)
```

---

## Running `lotusd` with In-Process Chronik

Prebuilt binaries for Linux (`x86_64`) and macOS (`arm64`) with the **in-process Chronik indexer** compiled in are published on the [GitHub Releases](https://github.com/givelotus/lotus/releases) page.

To start `lotusd` with Chronik enabled:

```bash
./lotusd -chronik=1 -daemon
```

By default on mainnet:
- **P2P port**: `10605`
- **JSON-RPC port**: `10604`
- **Chronik HTTP / WebSocket indexer**: `127.0.0.1:8331` (override with `-chronikbind=<ip:port>`)
- **Chronik data directory**: `<datadir>/indexes/chronik/` (initial index sync from genesis takes ~2–5 minutes on NVMe SSD)

Verify Chronik is serving live chain state:

```bash
curl -s http://127.0.0.1:8331/blockchain-info | xxd
./lotus-cli getblockchaininfo
```

---

## Building `lotusd` from Source (Lotus V1 Mainnet)

Rather than maintaining a diverging fork of the entire C++/Rust tree, `daemon/` pins an upstream [`Bitcoin-ABC/bitcoin-abc`](https://github.com/Bitcoin-ABC/bitcoin-abc) commit ([`daemon/bitcoin-abc-version`](daemon/bitcoin-abc-version), currently `252182e957120652960c1f88ec96515c448b1204`) and automatically applies the ordered patch series in [`daemon/patches/v1/series`](daemon/patches/v1/series).

### 1. Install Dependencies

**macOS (Homebrew):**
```bash
brew install berkeley-db@4 boost cmake flatbuffers jemalloc libevent miniupnpc libnatpmp nng ninja openssl protobuf python rocksdb rust sqlite zeroMQ
```

**Ubuntu / Debian (22.04 / 24.04):**
```bash
sudo apt-get update
sudo apt-get install -y \
  build-essential cmake ninja-build pkg-config git python3 \
  libboost-all-dev libssl-dev libevent-dev libdb++-dev \
  libsqlite3-dev libjemalloc-dev libnng-dev libflatbuffers-dev flatbuffers-compiler \
  libprotobuf-dev protobuf-compiler librocksdb-dev libclang-dev curl
# Install Rust toolchain (required for in-process Chronik):
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
```

### 2. Clone `bitcoin-abc` and Apply the Lotus V1 Patch Series

From the repository root:

```bash
make -C daemon setup SERIES=v1
```

What this does automatically (`daemon/scripts/setup.sh`):
1. Clones `https://github.com/Bitcoin-ABC/bitcoin-abc.git` into `daemon/workspace-v1/`.
2. Checks out the pinned base commit from [`daemon/bitcoin-abc-version`](daemon/bitcoin-abc-version) (`252182e957120652960c1f88ec96515c448b1204`) on branch `lotus-v1-work`.
3. Iterates through every patch in [`daemon/patches/v1/series`](daemon/patches/v1/series) (`000` through `247`) in order, applying and committing each patch onto `daemon/workspace-v1/`.

*(To wipe `daemon/workspace-v1/` and re-apply all patches from scratch at any time, run `make -C daemon setup SERIES=v1 RESET=1`.)*

### 3. Compile `lotusd` and `lotus-cli` (with In-Process Chronik)

```bash
make -C daemon build SERIES=v1
```

This runs CMake + Ninja inside `daemon/workspace-v1/build/` with `-DBUILD_CHRONIK=ON` enabled by default, producing:
- `daemon/workspace-v1/build/src/lotusd`
- `daemon/workspace-v1/build/src/lotus-cli`

---

## Research

The theoretical foundation for Lotus is published at [givelotus.github.io](https://givelotus.github.io). Three preprints cover proof-of-work as monetary signal, adaptive monetary policy via feedback control, and spam prevention via burn-to-speak messaging.

The next-generation **Lotus V2** protocol specification is located in [`docs/lotus-v2/`](docs/lotus-v2/README.md).

## Support

Lotus is funded by its community. If you believe mathematics should govern money instead of committees, consider supporting development at [patreon.com/c/givelotus](https://www.patreon.com/c/givelotus).
