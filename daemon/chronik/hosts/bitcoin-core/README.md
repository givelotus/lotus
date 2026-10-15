# Bitcoin Core Chronik codec foundation

For the optional real host adapter and its separate runtime evidence, see [HOST.md](HOST.md). This document describes mailbox 0001 by itself.

This optional mailbox adds a tested Bitcoin witness transaction codec. It does **not** implement or enable a Bitcoin Core Chronik bridge, indexer, provider profile or HTTP server. Provider gates, default series, public schemas and releases remain unchanged.

Exact sources are Bitcoin Core [`f13ae519de94394314cd63a27924b0998ac65d45`](https://github.com/bitcoin/bitcoin/tree/f13ae519de94394314cd63a27924b0998ac65d45) and ABC Chronik [`1fb7db17c176cdea8a2c60d887891589382ee4e3`](https://github.com/Bitcoin-ABC/bitcoin-abc/tree/1fb7db17c176cdea8a2c60d887891589382ee4e3/chronik). Chronik tree: `84b19eab61f15c7887f12d1139026f3323d57de6`. Verified export manifest SHA256: `a0ecb702d30ef408c552e1b081928476ac59f92ebb69fa225777bffb6528d8ed`. Apply with `git am` to a private copy of the verified export; the patch paths begin with `chronik/`. Never modify the trusted original export.

## Codec and verification

`BitcoinTx` keeps full bytes and per-input witness separately from the existing stripped `Tx`. BTC txid explicitly hashes stripped bytes with SHA256d; wtxid hashes full bytes. It never invokes chain-dependent `TxId::from_tx`, which Lotus changes to a Merkleized identifier. Existing TxMut and ABC/Lotus/Doged serializers remain untouched. There is no implicit serializer/dereference that could discard witness.

Parsing enforces canonical CompactSize, Core's default size limit, counts bounded by remaining bytes before allocation, witness flags, rejection of superfluous witness/unknown flags, and full consumption. It does not validate consensus, Script execution or admission policy. Weight-based vsize excludes Core's possible sigop adjustment.

The oracle links actual native Core serializers/hashes/weight/block serialization. Build the exact native source with CMake, then:

```sh
c++ -std=c++20 -I"$CORE/src" -I"$CORE/build/src" \
  daemon/chronik/hosts/bitcoin-core/tests/wire_oracle.cpp \
  "$CORE/build/lib/libbitcoin_consensus.a" \
  "$CORE/build/lib/libbitcoin_crypto.a" \
  "$CORE/build/lib/libbitcoin_util.a" -o /tmp/lotus-core-wire-oracle
python3 daemon/chronik/hosts/bitcoin-core/tests/generate-codec-fixtures.py \
  --core-source "$CORE" --oracle /tmp/lotus-core-wire-oracle \
  --output "$STAGED/chronik/bitcoinsuite-core/tests/fixtures/bitcoin_core_wire.json"
cd "$STAGED"
cargo +1.87.0 test --locked -p bitcoinsuite-core
cargo +1.87.0 clippy --locked -p bitcoinsuite-core \
  --lib --test bitcoin_codec -- -D warnings
```

CORE is the native source/build; STAGED is the private patched export. The generator rejects tracked edits and checks that src matches the exact Core pin. The local oracle build has build-label changes outside src, rather than an unchanged whole-source tree.

161 native comparisons pass: 20 accepted and 141 rejected. Cases cover legacy/SegWit, witness mutations retaining txid, multiple inputs, empty witness items, coinbase witness, P2WPKH/P2WSH/P2TR, CompactSize boundaries, large witness items, malformed flags/counts, trailing bytes and truncations. Accepted cases compare full/stripped bytes, txid/wtxid, sizes/weight and native first/second transaction offsets. Synthetic block offsets do not prove consensus validity or XOR disk reads. Regeneration is byte-identical.

All 48 existing unit tests, three integration tests and 58 doc tests pass. Focused strict Clippy passes. All-target strict Clippy fails an inherited warning at script/compress.rs:93 (needless_borrows_for_generic_args), also reproduced on the pristine export; it remains unsuppressed. [Evidence](../../../docs/evidence/bitcoin-core-chronik-codec-20261014.json) records identities and logs.

## Remaining integration

The [36-function CXX inventory](../../../docs/evidence/bitcoin-core-chronik-host-api-20261014.json) identifies every bridge function. None is implemented by the codec.

| Boundary | Required implementation and validation |
|---|---|
| Native values | Map typed Txid/Wtxid, COutPoint and Coin fields, int64 CAmount and native compression/undo wrappers; preserve Core's optional GetCoin API. |
| Chain selection | Use ValidatedChainstate and cs_main. Core ChainstateRole has validated/historical booleans, unlike ABC's enum. Follow native bootstrap/handoff ordering. |
| Storage | Use BlockManager XOR-aware readers. OpenUndoFile is private and ABC per-tx disk helpers are absent. Preserve undo coins and absolute XOR phase/offset. |
| Rust queries | Retain witness/full bytes through FFI, mempool, raw queries and broadcast. Current shared Tx bridge lacks witness; ser_len and legacy broadcast parsing are insufficient. |
| Mempool | NewMempoolTransactionInfo lacks Chronik's spent coins and insertion time. Capture acceptance-time data or prove reconstruction; queued lookup can race removal. Process grouped mined removals once. |
| Lifecycle/reorg | Register NodeContext-owned shared subscriber, reconcile locked bootstrap, respect validated-role transitions, drain outside cs_main, close DB before owners die; test disconnect/reconnect. |
| Durability | Reconcile cursor with native flushed locator after crash/restart. Callback delivery is not fsync. Require retained block/undo data initially and explicit missing-data errors. |
| Fees/broadcast | Preserve absolute max_fee and native policy virtual size; full byte size is not fee denominator. |
| Build | Link actual shared component to Core bitcoin_node with native lifecycle/options, not ABC server. Do not bypass host-provider gates. |

[Core storage](https://github.com/bitcoin/bitcoin/blob/f13ae519de94394314cd63a27924b0998ac65d45/src/node/blockstorage.cpp) owns XOR-aware readers. nDataPos starts at the header after storage framing. First transaction offset is 80 plus CompactSize count; subsequent offsets advance by full witness serialization, not stripped size/vsize. Plain FILE reads can return ciphertext; resetting XOR phase at a transaction is incorrect.

[Validation signals](https://github.com/bitcoin/bitcoin/blob/f13ae519de94394314cd63a27924b0998ac65d45/src/validationinterface.h) and [BaseIndex](https://github.com/bitcoin/bitcoin/blob/f13ae519de94394314cd63a27924b0998ac65d45/src/index/base.cpp) establish native ordering. Raw unregister during concurrent requests is insufficient; use shared subscriber lifetime management and native queue boundaries.

Public txid must remain the stripped identifier and raw responses must include witness. No public wtxid/witness schema extension is necessary for that initial contract. Existing other/full-script indexing roundtrips witness programs; tests cover P2WPKH/P2WSH/P2TR. Named witness aliases/Bech32 helpers are unimplemented. Do not reuse Lotus Taproot encoding for BTC.

Core has no Avalanche finality: report absent capability/false rather than substituting confirmations. NNG, mining policy, chain-limit removal, RTT, MinerFund and Avalanche consensus are independent. No Core Chronik compilation, HTTP runtime, synchronization, reorg or crash-recovery success is claimed here.
