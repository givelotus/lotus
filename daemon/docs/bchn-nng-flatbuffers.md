# BCHN compatible NNG / FlatBuffers candidate

This is the replacement for the rejected incompatible raw-payload publisher.
It is one mailbox patch on exact BCHN pin
`abd433abe04f74780744b9eac06731f3690ce68a`, independently selectable and default OFF:
`daemon/patches/bchn/10-nng-interface.patch`.

Source commit: `f9966c8d3b53cbab640a34cff33d00558884ca3f`.
Source tree: `5d16cbdd89cdcef3bd6c34cf220194cf804d9fe8`.
Independent mailbox replay retains that tree. Root submitted the reviewed final
source as `eb7e2f4f7ae336f6f7b54b08baf6729a212e9f39` to MR2176, with
byte-identical final tree. Native enabled build, both existing consumer suites and
the complete mandatory local lint suite pass. New Linux CI remains pending;
historical raw-protocol CI does not validate this replacement.


`BUILD_BITCOIN_NNG` is OFF by default. This is a port of the maintained
Lotus/Logos NNG service and the existing public `bitcoinsuite-bitcoind-nng`
consumer contract, not a replacement for ZeroMQ. Neither Chronik nor changes to
mempool, mining selection, consensus or ZeroMQ are dependencies.

## Build and run

Install NNG development headers/library and matching FlatBuffers headers and
`flatc`. Native validation uses NNG 1.12.4 and FlatBuffers 25.12.19. CMake finds
installed dependencies; it does not download them. C++ and Python bindings are
generated from `src/nng_interface/nng_interface.fbs`; no custom deserializer is
required. A generated header checks the FlatBuffers header/compiler versions.

```
cmake -S . -B build -GNinja -DBUILD_BITCOIN_NNG=ON -DBUILD_BITCOIN_QT=OFF
ninja -C build bitcoind bitcoin-cli
build/src/bitcoind -nngrpc=ipc:///private/path/rpc.pipe \
  -nnglegacyrpc=ipc:///private/path/legacy-rpc.pipe \
  -nngpub=ipc:///private/path/pub.pipe \
  -nngpubmsg=blkconnected -nngpubmsg=blkdisconctd \
  -nngpubmsg=mempooltxadd -nngpubmsg=mempooltxrem \
  -nngpubmsg=updateblktip -nngpubmsg=chainstflush -nngpubmsg=miningwrkchg
```

Choose explicit endpoints. The service is an unauthenticated data-plane API;
restrict it to trusted processes using protected IPC paths or loopback. Multiple
`-nngpubmsg` arguments select the topics; none are enabled implicitly.

## Existing wire contract

NNG `Req0` / `Rep0` carries a FlatBuffers `RpcCall`. Replies are `RpcResult` with
`is_success`, numeric `error_code`, `error_msg` and a nested response buffer in
`data`. Requests are verified before dispatch. Existing discriminants, table
field positions, existing error numbers and 32-byte little-endian hash arrays are retained.
New failure codes append after those preserved numbers: evolved code 8 is an
invalid mining parameter and code 9 is a response resource limit; legacy code 8
is its response resource limit. They use the existing RpcResult error envelope.

NNG `Pub0` / `Sub0` carries exactly a 12-byte topic followed by its FlatBuffers
table. There is **no added sequence header or alternate raw payload format**.
The supported topics match the existing Rust consumer:

| Topic | Table |
|---|---|
| `updateblktip` | `UpdatedBlockTip` |
| `mempooltxadd` | `TransactionAddedToMempool` |
| `mempooltxrem` | `TransactionRemovedFromMempool` |
| `blkconnected` | `BlockConnected` |
| `blkdisconctd` | `BlockDisconnected` |
| `chainstflush` | `ChainStateFlushed` |
| `miningwrkchg` | `MiningWorkChanged` |

RPC methods are `GetBlock`, `GetBlockRange`, `GetBlockSlice`, `GetUndoSlice`,
`GetMempool`, `GetMiningTemplate` and `GetMiningStatus`. Blocks include complete
transactions, input spent coins, absolute transaction/undo offsets and file
numbers. Mempool records include admission times and coins captured at admission,
including outputs of unconfirmed parents. Capturing before the async callback
prevents a later block/reorg from erasing that information.

BCHN reports block conflicts separately. This adapter emits `mempooltxrem` for
those conflicts before `blkconnected`, as maintained evolved clients expect;
transactions included in the block do not also receive removal notifications.
Disconnect events contain the complete disconnected block and undo data.
`ChainStateFlushed` reports durable chain state. `MiningWorkChanged` also reports
pure invalidation rollbacks that BCHN does not send through `UpdatedBlockTip`.

The schema and consumer are maintained at public
[bitcoinsuite revision d425f277](https://github.com/LotusiaStewardship/bitcoinsuite/tree/d425f277debbddfb0b9ebdc7e737c1c0c56c6dac/bitcoinsuite-bitcoind-nng).
Only the final empty line is normalized in the schema import. These are BCH
representations: 80-byte headers, SHA256d transaction IDs, no Lotus block metadata,
ordinary Bitcoin Merkle branches, and four-byte `nTime`. Spent output `script`
bytes include the serialized CashTokens prefix/data where present. The adapter
preserves these bytes; it does not add a token indexing engine.

The earlier Tobias 2021 BCHN `PluginInterface` schema is a different existing
protocol, with different hash/table layouts and conflicting union discriminants.
It is **not** wire compatible with the maintained evolved `NngInterface` schema.
Use the optional **separate** `-nnglegacyrpc=<address>` endpoint for that unchanged
2021 RPC schema (one inherited trailing space is removed). It supports all seven original methods:

| Endpoint | Existing schema | RPC methods |
|---|---|---|
| `-nngrpc` | Maintained `NngInterface` | GetBlock, GetBlockRange, GetBlockSlice, GetUndoSlice, GetMempool, GetMiningTemplate, GetMiningStatus |
| `-nnglegacyrpc` | Tobias 2021 `PluginInterface` | GetBlock, GetBlockRange, GetBlockUndoData, GetMempool, GetBlockchainInfo, SubmitBlock, SubmitTx |

`SubmitBlock` delegates to BCHN's existing submitblock handler and synchronized
state catcher; `SubmitTx` delegates to its existing BroadcastTransaction path.
This keeps current consensus and submission policy authoritative. Both retain the
original FlatBuffers success/rejection envelopes. The test reconstructs and
solves an evolved NNG mining template, then submits it through the legacy NNG RPC
endpoint. Existing JSON-RPC submission remains available.

Legacy RPC is OFF unless its explicit endpoint is configured. The earlier 2021
pub/sub dialect is not published by this port; `-nngpub` provides the maintained
evolved dialect described above. Original legacy RPC test methods and schema
are preserved as fixtures from Tobias's commit
`11b5e3c46b1e0520ed849af458ed4f38e88eb02f`. The test harness corrects the old
fixture's eleven-versus-twelve inclusive block-range count, without changing the
reference fixture or the wire protocol. Do not claim compatibility with earlier
2021 pub/sub, a runtime plugin ABI, or a complete standalone Chronik port.

## Bounds and lifecycle

Evolved requests are limited to 1 MiB; the legacy submission endpoint accepts
at most 256 MiB to accommodate serialized blocks. Slice reads are limited to 32 MiB and validate
file numbers before allocating. A range returns an ascending contiguous prefix
of at most 100 blocks and approximately 64 MiB; a single unusually large valid
block is allowed so synchronization still makes progress. Negative or out-of-tip
range starts return an empty vector. Counts are clamped before signed arithmetic.
Mempool snapshots above 64 MiB return an explicit existing error envelope rather
than a partial snapshot. Missing/pruned block or undo data is an error, not an
empty successful block. Errors do not kill the request worker.

RPC starts after chain loading and before outbound networking starts. The worker
stops and joins before node objects are destroyed. Publications run in validation
queue order; pending callbacks drain before publisher teardown. Bind failures
close partially initialized sockets, permitting restart.

Pub/sub is lossy, as in the original service. There is no replay log, common
watermark or atomic snapshot-plus-subscription operation in the existing schema.
Consumers must buffer subscribed events during bootstrap, reconcile the tip and
mempool on reconnect/restart, and handle reorgs. The mining epoch is process-local
and is not a general durable event sequence. This port does not invent new fields
that pretend to solve that limitation.

## Reproduce compatibility checks

The optional test probe links the **unmodified existing public Rust client** at
immutable revision `d425f277`, with a committed Cargo lockfile. Rust is only a
test dependency; the daemon does not link Rust for this feature. The public
client's checked-in bindings omit the declared mining-status extension, so only
that extra status check and the legacy submit convenience probe use standard
generated schema bindings; block,
mempool, mining-template and event checks use the unmodified public client.

```
cargo +1.93.0 build --locked --manifest-path test/nng_compat_client/Cargo.toml
python3 test/nng_compat_client/check_schema.py
python3 test/functional/interface_nng_compat.py --configfile=build/test/config.ini
```

The schema check compares the public consumer schema and verifies repeated
C++/Python generation is byte-identical with the installed `flatc`. The live
test covers bootstrap and raw/undo reads, spent coins, CashTokens, an unconfirmed
parent/child, real mining-template reconstruction/submission, conflicts, reorgs,
restart, malformed requests and resource bounds. It uses isolated regtest data.
For original Tobias RPC fixture tests, install the pinned optional Python
requirements in a virtual environment, then run:

```
python3 -m pip install -r test/nng_compat_client/python-requirements.txt
python3 test/functional/interface_nng_legacy_rpc.py --configfile=build/test/config.ini
```

When the optional probe is absent or NNG is OFF, the functional test explicitly
skips. Testing the daemon with ZeroMQ both ON and OFF remains independent.

## Review evidence and limits

[Machine-readable evidence](bchn-nng-flatbuffers-evidence.json) records the exact
base, mailbox replay, combination trees, tool versions and validation logs.
Native macOS arm64 builds pass with NNG ON / ZeroMQ OFF, both ON, and both OFF.
The unchanged daemon implementation passes 653 C++ cases (62,621,532 assertions).
The prior candidate `875318a9be` differs from implementation commit `0ad0aca89d` only
in the functional test and Rust probe: both prior enabled binaries pass those strengthened
undo-decoding tests using the unmodified public SDK codec. Original Tobias RPC
fixtures pass independently against both enabled builds. OFF builds expose no NNG
help, linked library or undefined symbol, and the functional test explicitly skips.

Patch 10 and patches 11/12 apply in either order to the same combined tree. This is
application evidence; the source-deleted combination has not been built in this
review. Linux, Windows, sustained load, pruning behavior and a standalone Chronik
indexer remain unvalidated. An additional pruning experiment did not start because
BCHN rejects ABC's `-fastprune` test option; it supplies no pruning evidence.
The original 2021 publication dialect is not implemented. See the protocol matrix
above for the evolved publication interface and separately supported legacy RPC.

The reviewed lint follow-up separates the admission-hook header to avoid a module
cycle and uses fixed format strings with BCHN's existing translation API. Its exact
final tree was rebuilt with NNG ON / ZeroMQ OFF and both existing consumer suites
passed again. Full unit and other build-mode evidence above belongs to the previous
implementation tree; this narrow follow-up does not repeat those broader claims.

The final generated-header include-style correction leaves schema/API behavior
unchanged. The complete mandatory CMake `check-lint` target passes on final tree
`5d16cbdd89cdcef3bd6c34cf220194cf804d9fe8`, with no skipped lint checks; the
recorded tool versions match the project's CI pins.
