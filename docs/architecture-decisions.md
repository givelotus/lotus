# Lotus Mainnet Architecture

This repository contains the Lotus mainnet implementation and its supporting libraries and applications. See the [daemon guide](../daemon/README.md) for the validated node build and run instructions.

| Component | Location | Role |
|---|---|---|
| Node daemon | `daemon/` | Bitcoin ABC base plus the ordered Lotus mainnet patch series; builds `lotusd` and `lotus-cli` |
| Chronik | In the patched daemon workspace | In-process Rust/C++ transaction indexer with HTTP protobuf and WebSocket APIs |
| NNG | In the patched daemon workspace | Block and transaction pub/sub notifications |
| Dart SDK | `sdk/dart/` | Libraries used by the Flutter wallet |
| Rust SDK | `sdk/rust/` | Standalone bitcoinsuite and Chronik client crates |
| Vase wallet | `wallets/vase/` | Flutter client and Go server |
| GPU miner | `miner/` | OpenCL mining software |

The node source is reconstructed from `daemon/bitcoin-abc-v1-version` and `daemon/patches/v1/series`. Generated `daemon/workspace-*` directories are local build workspaces and are not committed. Each mainnet patch has a corresponding commit; exporting and replaying the series must reproduce the source tree.

Lotus mainnet uses a difficulty-based log2 issuance curve, burns half of transaction fees, and distinguishes merkleized transaction IDs from hashes of raw serialization. Its headers are 160 bytes and blocks include serialized metadata. Chronik adapts its header, disk-offset, transaction-ID, and Taproot indexing behavior to these rules.

Avalanche and parking-policy code remains available, but eCash miner-fund and staking parking policies do not govern Lotus blocks. The Lotus miner fund is enforced by its own consensus checks.

The TypeScript SDK, cashweb, and modern web/desktop wallet are maintained in the separate Frank repository. Their former directories are not part of this checkout.

The [mainnet validation report](../daemon/docs/v1-8c67fe1e85-validation.md) records daemon builds, tests, replay, and sampled Chronik comparisons. Those checks do not establish validation of the inherited wallet, SDK, or miner components.
