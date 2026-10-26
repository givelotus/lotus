# HTTP/JSON-RPC array control: no regression reproduced

Current 521's Beast/coroutine path matched the ABC libevent/synchronous path for arrays of 50 cheap `echo` calls. The array-of-transaction-submissions gap is not explained by a blanket HTTP/JSON array processing slowdown in this control.

| Eight persistent clients | ABC | Current 521 | Observed current/ABC |
|---|---:|---:|---:|
| Individual requests, calls/second | 41,862 | 48,099 | 1.149× |
| Arrays of 50, calls/second | 611,509 | 615,222 | 1.006× |
| Array workload, accepted calls | 3,058,150 | 3,076,800 | |
| Array workload, elapsed seconds | 5.000987 | 5.001123 | |

Each independent Python process used its own warmed persistent HTTP/1.1 connection and validated every result. Both endpoints returned identical-size JSON response bodies: 51 bytes per individual response, or 2,592 bytes per 50-call response. There was no transaction admission, signing, fee calculation, mempool, mining or network relay work. The method is identical existing `echo` with one string parameter. There is no shared Python GIL across the eight client processes. Total array-client CPU was about 5.88 CPU-seconds for ABC and 6.01 for current across five elapsed seconds, so clients were not saturating their eight available cores.

One one-second macOS sample ran inside each case; all four cases include the same diagnostic sampling procedure. These are single observations under uncontrolled host load, not confidence intervals. The 0.6% array difference establishes no meaningful speedup. Nor does this control establish the cost for large raw-transaction JSON bodies or transaction submission handlers. It does rule against describing all current JSON-RPC arrays as slower because of Beast.

## Scope and source distinctions

- ABC: source `1fb7db17c176cdea8a2c60d887891589382ee4e3`, binary `38ae7776e7f54be4311c4e2b4f6f30764086a235d3c9d49e30b0f5d2ffa7feb4`.
- Current 521: source `a60bba6facc924cdf43c34dc881805bb114fe373`, tree `caf6bd4ce012b2383e733b45df46753b49b2a894`; preserved benchmark binary `3e14b617d530b61c794f141e13963879f12470042a287d2ef82183fa0edd4160`. This includes jemalloc ON, whereas ABC uses the platform allocator, so this is an endpoint control rather than a transport-only source A/B.
- Release O3, assertions retained, wallet ON, Chronik/H2/WebTransport OFF in the preserved engine binaries. No TLS on the owned loopback endpoint. RPC threads 16, eight clients.
- Original finalized fast V2 `09f95c297a67de61836c495904ce9f20551bf415` used libevent HTTP plus coroutine dispatch. Current and that original both execute the array sequentially through `JSONRPCExecBatchAsync`; generic synchronous actors do not introduce a per-element `post`. ABC's synchronous dispatcher is a further difference, so an ABC/current gap alone would not have proven a Beast defect.

The historic mempool-depth-dependent slowdown was real but cannot be attributed to fixed transport overhead. The original matched 32k array diagnostic had shared latency grow from 6.609 seconds with an empty pool to 25.338 seconds with 6k already present, while ABC stayed near 2.84 seconds. Subsequent profiling identified growing reconciliation scans and repeated snapshot work; the former is repaired in 521. The actual transaction-array and dedicated-batch/three-node workload comparisons remain the separate coordinated benchmark lane.

No production patch was created: this control found no transport regression to fix. Its raw profiles remain available for investigating dispatch micro-optimizations if transaction-specific profiles identify those costs.

Both owned daemon processes exited with code 0; all eight clients per case joined with code 0. No owned data-directory process remained after the run. Source files, script hash, exact startup commands, UTC/load, per-client counts/CPU and raw samples are in `comparison.json`, `abc/` and `native521/`. Runtime data directories are ignored and are not patch deliverables.
