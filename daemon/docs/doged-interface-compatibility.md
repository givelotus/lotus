# Doged optional NNG and mining interface boundary

Source audit, 2026-10-14; no daemon or consumer code changed by this audit.

## Existing Doged functionality

The complete tracked file list at Tobias Doged `9690833b8b6709b7a7837bc397f0d04bf3b885d1` contains no NNG or FlatBuffers paths. Its RPC source and initialization contain no NNG service. Therefore NNG is an unsupported additional capability, not an existing Doged interface removed by the current-ABC rebase. In-process Chronik and ordinary PoW operation must remain independent of it. No NNG-enabled Doged build or consumer compatibility has been demonstrated.

Original `src/rpc/mining.cpp` registers `getnetworkhashps`, `getmininginfo`, `prioritisetransaction`, `getblocktemplate`, `submitblock`, `submitheader`, `generatetoaddress`, `generatetodescriptor`, `generateblock`, `estimatefee`, and hidden `generate`. These existing JSON-RPC entry points must survive adaptation; successful compilation alone does not establish their response/behavior compatibility. The original source does not implement Dogecoin Core-style `getauxblock`, `createauxblock`, or `submitauxblock`. Accepting AuxPoW blocks through `submitblock` is different from offering a merged-mining work-construction RPC. This is a pre-existing interoperability gap and must be stated explicitly.

## Existing NNG consumers are not interchangeable

Historical Lotus V1 source at `0b7939e926b8353ad09d8edc47f355ddacc30502`, `src/nng_interface/nng_interface.fbs`, defines FlatBuffers request union values 1–5 for `GetBlockRequest`, `GetBlockRangeRequest`, `GetBlockSliceRequest`, `GetUndoSliceRequest`, and `GetMempoolRequest`. Its six pubsub topics are `updateblktip`, `mempooltxadd`, `mempooltxrem`, `blkconnected`, `blkdisconctd`, and `chainstflush`. Replies use `RpcResult` wrapping a serialized response with success flag, numeric error and text. Blocks expose raw headers, explicit hashes, metadata, transactions, spent coins, block-file positions and undo positions/sizes. This is not a raw-block publisher protocol.

The current standalone Rust consumer from `LotusiaStewardship/bitcoinsuite` at `d425f277debbddfb0b9ebdc7e737c1c0c56c6dac` additionally has `GetMiningTemplateRequest` union value 6 and `MiningWorkChanged`. The tracked Lotus SDK has these capabilities too. The separate in-progress BCHN FlatBuffers adaptation in `/tmp/lotus-bchn-nng-flatbuffers-20261014` additionally exposes `GetMiningStatusRequest`. Copying the historical Lotus service alone would omit the consumer's mining API; the rejected raw-payload BCHN publisher cannot substitute for either protocol. The BCHN working source is not evidence of Doged compatibility.

## Requirements for a future independent Doged host adapter

Retain exact table field indices, union discriminants, topic bytes and reply framing of the selected existing consumer protocol. Preserve block/range/raw block slice/raw undo slice/mempool services, spent-coin meanings and bootstrap/event ordering. Preserve durable-chain notifications and disconnect/reorg behavior. Validate with the unmodified pinned Rust consumer, not merely a newly written subscriber that agrees with the implementation.

Dogecoin needs the actual serialized variable-length AuxPoW header and transaction offset calculated from that actual header plus the transaction count. Historical Lotus code uses a fixed default-header serialization size and serialized `vMetadata`; neither layout can be copied into Dogecoin. Keep the schema metadata vector present and empty for a chain without Lotus metadata: the existing Rust mapper requires the field. Transaction IDs remain Dogecoin raw-transaction SHA256d, not Lotus merkleized IDs. A byte vector accepting a header does not prove that downstream Bitcoin/Lotus-specific header parsers support AuxPoW.

Adapt current node-owned validation signals and shutdown ordering, mempool spent coins, block/undo storage and locking APIs independently from Chronik. Mining templates must use actual Dogecoin block construction, Scrypt targets and AuxPoW behavior; returning a Bitcoin/Lotus template under existing field names would not establish mining compatibility. Existing merged-mining RPC gaps must not be hidden behind NNG enablement.

Any eventual service should be default OFF with separate CMake discovery/linkage and no dependency on enabling Avalanche or Chronik. Preserve ZeroMQ. Until implemented and validated, tooling must reject requested NNG rather than imply that a selectable flag enables it. This audit introduces no substitute wire format and claims no new NNG functionality.
