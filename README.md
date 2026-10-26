# Lotus

Lotus is a trust-minimized peer-to-peer monetary protocol. Monetary policy is governed by proof-of-work mining difficulty as a live, adversarially-revealed signal — no committees, no oracles, no central bank.

This monorepo contains the Lotus V1 node daemon, patch series, historical specifications, mining software, and SDKs.

Release validation covers the V1 daemon and its in-process Chronik indexer. The SDKs, Vase wallet, and miner have separate protocol/build checks and documented platform limits in their component READMEs. See the [daemon validation report](daemon/docs/v1-8c67fe1e85-validation.md) and [target support audit](daemon/docs/support-matrix.md) for exact evidence.

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

[Release `v11.6.1`](https://github.com/givelotus/lotus/releases/tag/v11.6.1)
provides Chronik-enabled Linux x86_64 and macOS arm64 binaries on ABC `8c67fe1e85`,
including the corrected custom block assembler. Historical `v11.6.0` assets remain
unchanged on the earlier `252182e957` base. [Component release preparation](daemon/docs/component-releases.md)
produces complete review candidates for future component-prefixed releases.

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

## Building from the pinned daemon submodules

```sh
make -C daemon setup SERIES=all
make -C daemon source-verify
make -C daemon build SERIES=v1
```

Select `v2`, `ecash`, `doged`, `bitcoin`, or `bchn` for other daemon sources.
Private submodules require authenticated Git access. See the
[daemon guide](daemon/README.md) for paths, configuration and source maintenance.

## Research

The theoretical foundation for Lotus is published at [givelotus.github.io](https://givelotus.github.io). Three preprints cover proof-of-work as monetary signal, adaptive monetary policy via feedback control, and spam prevention via burn-to-speak messaging.

## Support

Lotus is funded by its community. If you believe mathematics should govern money instead of committees, consider supporting development at [patreon.com/c/givelotus](https://www.patreon.com/c/givelotus).

## Licenses

Components retain their existing licenses and attribution. See the [component license map](LICENSES.md).
