# V2 miner integration path

The current miner has an explicit `--protocol=v1|v2` setting. V1 is the default.
V2 selection exits before GPU setup or any RPC request with a clear unsupported
error. The V2 P04 CPU header hashing primitive is implemented and checked against
independent vectors, but this is not a V2 mining implementation.

## Protocol contract

P04's candidate header is 134 bytes in wire order: parent ID (32), compact bits
(4), unsigned timestamp (6, little endian), nonce (8, little endian), version
(4), exact block size (8), height (8), transaction root (32), state root (32).
`BodyHash = BLAKE3("Lotus/v2/header/body" || 00 || ChainID || body[84])`,
`WorkHash = BLAKE3("Lotus/v2/header/work" || 00 || bits || time || nonce || BodyHash)`,
and `BlockID = BLAKE3("Lotus/v2/blockid" || 00 || parentID || WorkHash)`.
The target compares BlockID as an unsigned little-endian 256-bit value,
inclusive. ChainID must come from a selected chain manifest; no mainnet value is
implied here. The P04 profile remains a candidate pending consensus freeze.

V1 has a 160-byte header and the `lotus_og` SHA-256 OpenCL kernel. Its RPC
`getrawunsolvedblock` response supplies `blockhex` and `target`; the miner
submits serialized V1 blocks through `submitblock`. Neither this job shape nor
the kernel is suitable for V2. A name-only kernel switch would leave V1 nonce,
hash, target, and block-framing behavior active.

## Next integration slices

1. Freeze P04 and the V2 chain-manifest ChainID. Define a daemon mining-job API
   with protocol and chain identity, complete serialized block template, target,
   job/tip identity, nonce range and permitted time/template mutations. Reject
   mismatched protocol, wrong chain, stale tip, malformed length and unexpected
   RPC fields before allocating GPU work.
2. Build the canonical V2 template in the daemon, including coinbase parent ID
   and height, resource-adjusted reward, TxID/TxHash, transaction root, full
   post-state root and exact block size. Vanity/output changes require rebuilding
   all affected commitments and BodyHash; nonce-only changes reuse BodyHash.
   The GPU miner must never invent a state root.
3. Add an embedded tagged-BLAKE3 OpenCL kernel accepting explicit ChainID and
   V2 header fields. Partition the u64 nonce space without overlaps or rollover,
   report candidate nonces, and verify every result on CPU against full target
   before submission. Keep V1's kernel and job decoding behind its own protocol
   dispatch. Wire the GUI only after the same V2 safeguards exist.
4. Test independent header vectors, CPU/GPU parity across nonce and target
   boundaries, template mutation and stale-job behavior, V1 regressions, and
   malformed V2 job rejection. Compile and run the kernel on each supported GPU
   backend. Mine a disposable development-chain block on GPU and confirm an
   independent CPU validator and daemon both accept it. Record device, driver,
   build, test commands and measured hash rate; compilation alone is insufficient.

No V2 job API or accepted V2 block exists in this miner slice. No live network
mining was performed.
