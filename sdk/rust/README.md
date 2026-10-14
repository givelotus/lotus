# Bitcoin Suite Rust SDK

Multi-network transaction primitives, signing, token protocols, node interfaces, Stratum, and Chronik clients. This standalone workspace retains its [MIT license and attribution](LICENSE).

## Source and Lotus compatibility

Imported from [LotusiaStewardship/bitcoinsuite](https://github.com/LotusiaStewardship/bitcoinsuite) default branch `master` at `d425f277debbddfb0b9ebdc7e737c1c0c56c6dac` (2026-07-08), fetched 2026-10-14. The import adds upstream Taproot primitives, Stratum support, and refreshed NNG bindings. Local corrections match the deployed Lotus V1 protocol.

The daemon's Chronik crates have a different API layout, so this workspace preserves the standalone signing and multi-network interfaces. The Rust HTTP client's protobuf comes from the validated daemon tree `a055e77a25` (Bitcoin ABC base `8c67fe1e85` plus Lotus patches), with `uint32` transaction versions and current header/broadcast messages. The inherited TypeScript client remains a separate, unvalidated implementation.

- `Tx::lotus_txid()` computes the merkleized XPI ID used by outpoints and Chronik. `Tx::hash()` and `Tx::tx_hash()` return the raw serialization hash. Signing-script changes affect the raw hash while preserving the Lotus ID.
- `LotusHeader` serializes 160 bytes. `LotusBlock` includes its metadata vector before transactions and computes Lotus block commitments and block hashes.
- `LotusAddress` uses the `lotus_` mainnet prefix. Type 0 carries a complete script, preserving P2SH and Taproot state; `from_taproot` creates the node's compact type-2 commitment address. A compact address carries no state.
- `UnsignedTxInput::sighash_preimage_with_replay_protection` exposes explicit replay-epoch selection for existing BIP143 callers; the original method keeps its pre-replay behavior.
- `lotus_sighash_preimage` supports ALL/NONE/SINGLE, ANYONECANPAY, explicit key/script execution context, and both replay epochs. Supply complete spent outputs in input order; redeem scripts are not substitutes for spent locking scripts.
- `P2TRKeyPathSignatory` signs Lotus Schnorr key-path spends, verifies the tweaked key matches the spent commitment, and emits a push of the 65-byte flagged signature. Set `merkle_root` for an output with a script tree and `replay_protection` from the node's active consensus epoch. The constructor defaults to a key-path-only tree and the current pre-replay epoch. Script-path transaction construction is not implemented by this signatory; the preimage and tree primitives are available separately.
- Rust Chronik queries use `/script/p2tr/<33-byte-commitment>`, shared by stateless and stateful outputs, and `/block-header/<height>` returns the full Lotus header. Deprecated `P2trCommitment`/`P2trState` names map to that same commitment endpoint; state is not an independent query key.

## Build and checks

Use Rust 1.93.0 (pinned in `rust-toolchain.toml`), a C/C++ compiler, CMake, pkg-config, OpenSSL development files, and `protoc`. NNG's native dependency builds through CMake; generated FlatBuffers Rust bindings are checked in.

From `sdk/rust/`:

```sh
cargo check --workspace --all-targets --locked
cargo test --workspace --lib --exclude bitcoinsuite-bitcoind --exclude bitcoinsuite-bitcoind-nng --locked
cargo test -p bitcoinsuite-core --test test_lotus_mainnet --test test_lotus_sighash --locked
cargo test -p bitcoinsuite-chronik-client --test test_lotus_protocol --locked
cargo clippy --workspace --all-targets --locked
```

The mainnet fixtures cover seven blocks and fifteen transactions, including eight non-coinbase transactions, comparing raw bytes, 160-byte headers, block hashes, Merkle roots, metadata hashes, raw TxHashes, and merkleized TxIds against RPC. Address fixtures cover P2PKH, P2SH, and stateless/stateful Taproot. Sighash tests include all 28 daemon script-path vectors, both replay epochs, derived key-path cases, odd Merkle trees, and invalid inputs. Signer tests verify Schnorr signatures for all six sighash combinations in both epochs and reject the wrong epoch or commitment.

A read-only live test runs explicitly against a local Lotus V1 node:

```sh
LOTUS_CHRONIK_URL=http://127.0.0.1:8331 cargo test -p bitcoinsuite-chronik-client --test test_lotus_protocol --locked -- --ignored
```

It checks headers, block/transaction responses, raw transaction IDs, and the Taproot UTXO endpoint. It never broadcasts. The live check passed against the running Lotus V1 node on 2026-10-14.

A plain `cargo test --workspace` also runs inherited BCH/XEC node and legacy Chronik service tests. Those require `BITCOINSUITE_BIN_DIR` and the matching external services; they fail when that environment is absent and have not been certified against this daemon. Clippy passes with inherited warnings in the Stratum API argument count and Chronik error derive.

NNG/Stratum live mining and TypeScript client integration are outside the verified coverage above. See the imported [context documentation](docs/README.md) for the remaining components.
