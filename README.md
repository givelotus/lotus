# Lotus

Lotus is a trust-minimized peer-to-peer monetary protocol. Monetary policy is governed by proof-of-work mining difficulty as a live, adversarially-revealed signal — no committees, no oracles, no central bank.

This monorepo contains the Lotus V1 node daemon, patch series, historical specifications, mining software, and SDKs.

Release validation currently covers the V1 daemon and its in-process Chronik indexer. The standalone SDKs, wallet, and miner are inherited components with separate build and test requirements. See the [validation report](daemon/docs/v1-8c67fe1e85-validation.md) for the checks performed.

## Structure

```
daemon/         — Lotus node daemon (`lotusd` & `lotus-cli` built on Bitcoin ABC + Lotus patch series, with in-process Chronik & NNG)
  patches/v1/   — Lotus V1 mainnet patch series (`000`–`247`, rebased onto modern Bitcoin ABC 8c67fe1e85)
sdk/
  dart/         — Dart SDK for mobile wallet development
  rust/         — Rust libraries (bitcoinsuite / chronik-client)
wallets/
  vase/         — Mobile reference wallet (Dart/Flutter + Go vase-server)
miner/          — GPU mining software (OpenCL)
docs/           — Documentation and historical protocol specifications
```

---

## Running `lotusd` with In-Process Chronik

Prebuilt binaries for Linux (`x86_64`) and macOS (`arm64`) with the **in-process Chronik indexer** compiled in are published on the [GitHub Releases](https://github.com/givelotus/lotus/releases) page.

To start `lotusd` with Chronik enabled:

```bash
./bin/lotusd -chronik=1 -daemon
```

By default on mainnet:
- **P2P port**: `10605`
- **JSON-RPC port**: `10604`
- **Chronik HTTP / WebSocket indexer**: `127.0.0.1:8331` (override with `-chronikbind=<ip:port>`)
- **Chronik data directory**: `<datadir>/indexes/chronik/` (sync time depends on hardware, chain size, and whether blocks are already available locally)

Verify Chronik is serving live chain state:

```bash
curl -s http://127.0.0.1:8331/blockchain-info | xxd
./bin/lotus-cli getblockchaininfo
```

---

## Building `lotusd` from Source (Lotus V1 Mainnet)

Rather than maintaining a diverging fork of the entire C++/Rust tree, `daemon/` pins an upstream [`Bitcoin-ABC/bitcoin-abc`](https://github.com/Bitcoin-ABC/bitcoin-abc) commit ([`daemon/bitcoin-abc-v1-version`](daemon/bitcoin-abc-v1-version), currently `8c67fe1e85a602204a2ce65aa3b643469c2c3a1d`) and automatically applies the ordered patch series in [`daemon/patches/v1/series`](daemon/patches/v1/series).

### 1. Install Dependencies

Follow the [daemon dependency instructions](daemon/README.md#step-2-install-build-dependencies), including Python selection for Chronik. The release workflow builds on Ubuntu 24.04 and macOS arm64. Other components and platforms have separate validation requirements.

### 2. Clone `bitcoin-abc` and Apply the Lotus V1 Patch Series

From the repository root:

```bash
make -C daemon setup SERIES=v1
```

What this does automatically (`daemon/scripts/setup.sh`):
1. Clones `https://github.com/Bitcoin-ABC/bitcoin-abc.git` into `daemon/workspace-v1/`.
2. Checks out the pinned base commit from [`daemon/bitcoin-abc-v1-version`](daemon/bitcoin-abc-v1-version) (`8c67fe1e85a602204a2ce65aa3b643469c2c3a1d`) on branch `lotus-v1-work`.
3. Iterates through every patch in [`daemon/patches/v1/series`](daemon/patches/v1/series) (`000` through `247`) in order, applying and committing each patch onto `daemon/workspace-v1/`.

*(To wipe `daemon/workspace-v1/` and re-apply all patches from scratch at any time, run `make -C daemon setup SERIES=v1 RESET=1`.)*

### 3. Compile `lotusd` and `lotus-cli` (with In-Process Chronik)

```bash
# Use the Python interpreter selected in the dependency instructions:
PYO3_PYTHON="$LOTUS_BUILD_PYTHON" SERIES=v1 daemon/scripts/build.sh \
  -DPython_EXECUTABLE="$LOTUS_BUILD_PYTHON"
```

This runs CMake + Ninja inside `daemon/workspace-v1/build/` with `-DBUILD_CHRONIK=ON` enabled by default, producing:
- `daemon/workspace-v1/build/src/lotusd`
- `daemon/workspace-v1/build/src/lotus-cli`

---

## Research

The theoretical foundation for Lotus is published at [givelotus.github.io](https://givelotus.github.io). Three preprints cover proof-of-work as monetary signal, adaptive monetary policy via feedback control, and spam prevention via burn-to-speak messaging.

## Support

Lotus is funded by its community. If you believe mathematics should govern money instead of committees, consider supporting development at [patreon.com/c/givelotus](https://www.patreon.com/c/givelotus).

## Licenses

Components retain their existing licenses and attribution. See the [component license map](LICENSES.md).
