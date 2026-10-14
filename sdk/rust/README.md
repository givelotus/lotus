# Bitcoin Suite Rust SDK

This workspace contains inherited Rust libraries for Bitcoin-family transaction primitives, signing, token protocols, node interfaces, and Chronik clients.

The standalone SDK is separate from the Rust crates in the daemon's upstream Chronik workspace. The V1 daemon release checks validate the latter; they do not establish compatibility of every crate in this directory with the rebased Lotus daemon. Standalone SDK integration is tracked in [issue #8](https://github.com/givelotus/lotus/issues/8).

See [Cargo.toml](Cargo.toml) for workspace members and [Makefile.toml](Makefile.toml) for the existing `cargo make` tasks. Individual crates may require native dependencies or a running test node.

The SDK retains its [MIT license](LICENSE).
