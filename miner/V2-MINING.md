# V2 miner integration path

The maintained CLI/GUI retain the Lotus V1 and Dogecoin modes. The V2 CPU
header/job primitives and bounded OpenCL batches are available as library modules;
they are not wired into the network miner. Existing V1 and Dogecoin regression
coverage is retained.

The earlier specification branch's proposed `--protocol=v1|v2` CLI/GUI changes
are preserved outside this repository at
`~/repos/archive/evidence/earlier-integration/miner/candidates/specifications-v2-integration.diff`.
They overlapped
newer multi-chain miner fixes and remain an explicit integration candidate.
Historical test results below describe their original source revisions.

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

1. Pin a versioned P04 candidate profile and explicit development ChainID for
   integration tests. Final consensus and production ChainID freeze is a launch
   gate. Define a daemon mining-job API
   with protocol and chain identity, complete serialized block template, target,
   job/tip identity, nonce range and permitted time/template mutations. Reject
   mismatched protocol, wrong chain, stale tip, malformed length and unexpected
   RPC fields before allocating GPU work.
2. Build the canonical V2 template in the daemon, including coinbase parent ID
   and height, resource-adjusted reward, TxID/TxHash, transaction root, full
   post-state root and exact block size. Vanity/output changes require rebuilding
   all affected commitments and BodyHash; nonce-only changes reuse BodyHash.
   The GPU miner must never invent a state root.
3. Integrate the embedded tagged-BLAKE3 OpenCL kernel with versioned V2 jobs.
   BodyHash is computed once per batch from the explicit ChainID and header body;
   OpenCL computes WorkHash and BlockID for each u64 nonce. Current batches reject
   overflow and verify each target hit again on CPU. A live scheduler must
   partition nonce space without overlaps, handle cancellation and stale jobs,
   and retain V1's separate kernel and job decoding. Wire the GUI only after
   the same V2 safeguards exist.
4. Test independent header vectors, CPU/GPU parity across nonce and target
   boundaries, template mutation and stale-job behavior, V1 regressions, and
   malformed V2 job rejection. Compile and run the kernel on each supported GPU
   backend. Mine a disposable development-chain block on GPU and confirm an
   independent CPU validator and daemon both accept it. Record device, driver,
   build, test commands and measured hash rate; compilation alone is insufficient.

The bounded OpenCL parity test executed on Apple M5 Max on October 14, 2026:
independent P04 vectors, four nonce windows including byte carry, u32 carry and
the u64 end, and inclusive/lower target boundaries passed. This is GPU kernel
execution evidence, not network mining or a measured hash rate. No V2 job API
or accepted V2 block exists in this miner slice. No live network mining was
performed.

The V2-branch integration review adds a deterministic GPU corpus that changes
ChainID, parent ID, bits, time, version, size, height, transaction root and state
root independently. Batches of 1, 2, 7 and 16 nonces span u32 carry and the u64
end. Every GPU digest matches the CPU implementation, and exact/lower targets
are checked for each field variant on Apple M5 Max.

```sh
cargo test --locked -p lotus-miner-lib gpu_cpu_parity_and_target_boundaries -- --ignored --nocapture
cargo test --locked -p lotus-miner-lib gpu_diverse_header_and_batch_corpus -- --ignored --nocapture
cargo test --locked --workspace
cargo clippy --locked --workspace --all-targets -- -D warnings
```
