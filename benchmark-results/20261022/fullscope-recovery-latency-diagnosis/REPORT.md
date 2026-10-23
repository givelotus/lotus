# Full-scope recovery latency diagnosis

Existing green-gate527/528 observations recover5,000 missing native transactions to a10,000-transaction exact pool. The64-second aging period is excluded from recovery. Final proof checks exact TxId sets and fetched raw bytes/native TxHashes on all three nodes.

| Observation |527 |528 |
|---|---:|---:|
| Reconnect→exact three-node inventory |81.842s |81.391s |
| Requests per recovering peer before first full coverage |272 |272 |
| Median request interval, first recovering peer |210.855ms |209.258ms |
|528 capture, first request→last request, coverage→admission |— |4.762ms;56.842s;24.408s |

The protocol executes one request at a time with125ms exchange spacing on both sides. `CConnman::ThreadMessageHandler` sleeps up to100ms without pending receive work (`src/net.cpp:3436`). Full-scope scheduling is called from `SendMessages`; it does not signal remaining admission work. Thus the observed~210ms request cadence and64-body-per-turn admission are scheduling/pacing evidence, not CPU utilization.

`Topological` includes all10,000 verified bodies, including5,000 already present. Admission handles only64 per Tick, then returns. This creates157 heartbeat-sized work slices. The remaining admission tail is24.408s in528.

Snapshot capture pins are counted in production but were NOT scraped by the original benchmark. `peers[].websocket.pinned` is unrelated. The old logs prove capture took milliseconds, not which capture branch ran. A metrics-enabled same-source diagnostic is running separately; original artifacts remain unchanged.

The source owner is preparing useful-deadline wakeups and bounded continuation, retaining authentication, rate limits, one-request/page bounds and normal validation. Even ideal125ms scheduling leaves~34s for272 requests; further protocol throughput improvements need explicit budgeted design and correctness proof.

Reproduce retained-log extraction with `python3 benchmark-results/20261022/fullscope-recovery-latency-diagnosis/parse-timeline.py`. Raw input paths/hashes and literal events are in `retained-timeline.json`. This is diagnosis in progress, not a measured repair claim.

## Direct pin-path proof

A separate metrics-enabled run of the unchanged528 source/binary passed the same exact10k all-peer TxId and raw-body/TxHash assertions. Recovery was84.75 seconds. This preserves the original81.391-second result separately.

| Node | Captures/pins | Fallbacks | Total capture lock | Total build | Total commitment |
|---|---:|---:|---:|---:|---:|
|0 |3/3 |0 |12.629ms |7µs |4.230ms |
|1 |3/3 |0 |12.468ms |2µs |4.066ms |
|2 |2/2 |0 |4.605ms |5µs |1.518ms |

These are cumulative production counters over the whole case, not per-capture maxima. The run exited0, all owned processes drained, peak whole-group RSS0.964GiB. `before/SUMMARY.json`, `before/evidence.json` and the immutable execution plan retain source/binary/tooling details. This proves the pin branch ran; it does not imply pending-overlay flush inside `PinTxMerklixSnapshot` is always constant time.
