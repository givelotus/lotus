# Full-scope recovery latency diagnosis

Existing green-gate527/528 observations recover5,000 missing native transactions to a10,000-transaction exact pool. The64-second aging period is excluded from recovery. Final proof checks exact TxId sets and fetched raw bytes/native TxHashes on all three nodes.

| Observation |527 |528 |
|---|---:|---:|
| Reconnect→exact three-node inventory |81.842s |81.391s |
| Requests per recovering peer before first full coverage |272 |272 |
| Median request interval, first recovering peer |210.855ms |209.258ms |
|528 capture, first request→last request, coverage→admission |— |4.762ms;56.842s;24.408s |

The protocol executes one request at a time with125ms exchange spacing on both sides. `CConnman::ThreadMessageHandler` sleeps up to100ms without pending receive work (`src/net.cpp:3436`). Full-scope scheduling is called from `SendMessages`; it does not signal remaining admission work. The observed~210ms request cadence is scheduling/pacing evidence, not CPU utilization. The initial suspicion that the admission tail was another heartbeat delay was subsequently disproved by per-admission logs (see correction below).

`Topological` includes all10,000 verified bodies, including5,000 already present. Admission handles only64 per Tick, then returns. This creates157 bounded work slices. The remaining admission tail is24.408s in the original528 run; its duration alone does not prove scheduler idle time.

Snapshot capture pins are counted in production but were NOT scraped by the original benchmark. `peers[].websocket.pinned` is unrelated. The old logs prove capture took milliseconds, not which capture branch ran. A metrics-enabled same-source diagnostic is running separately; original artifacts remain unchanged.

The source owner prepared useful-deadline wakeups and bounded continuation, retaining authentication, rate limits, one-request/page bounds and normal validation. Even ideal125ms scheduling leaves~34s for272 requests; further protocol throughput improvements need explicit budgeted design and correctness proof.

Reproduce retained-log extraction with `python3 benchmark-results/20261022/fullscope-recovery-latency-diagnosis/parse-timeline.py`. Raw input paths/hashes and literal events are in `retained-timeline.json`. This is diagnosis in progress, not a measured repair claim.

## Direct pin-path proof

A separate metrics-enabled run of the unchanged528 source/binary passed the same exact10k all-peer TxId and raw-body/TxHash assertions. Recovery was84.75 seconds. This preserves the original81.391-second result separately.

| Node | Captures/pins | Fallbacks | Total capture lock | Total build | Total commitment |
|---|---:|---:|---:|---:|---:|
|0 |3/3 |0 |12.629ms |7µs |4.230ms |
|1 |3/3 |0 |12.468ms |2µs |4.066ms |
|2 |2/2 |0 |4.605ms |5µs |1.518ms |

These are cumulative production counters over the whole case, not per-capture maxima. The run exited0, all owned processes drained, peak whole-group RSS0.964GiB. `before/SUMMARY.json`, `before/evidence.json` and the immutable execution plan retain source/binary/tooling details. This proves the pin branch ran; it does not imply pending-overlay flush inside `PinTxMerklixSnapshot` is always constant time.

## Measured candidate and corrected admission attribution

The source-only candidate2a36522d (treecbc28b70, frozen binary3fa8d567) passes the full1,200-case native gate. The identical metrics-enabled correctness test passed all-three exact10k TxId sets and raw-byte/TxHash checks. One observation per side:

| Phase | Before528 | Deadline candidate |
|---|---:|---:|
| Capture→first authenticated full coverage |60.695s |35.353s |
| First coverage→first admission completion |24.166s |24.694s |
| Reconnect→exact all-three inventory |84.760s |59.887s |

The candidate removes fetch heartbeat quantization. It does **not** show an admission-time gain. The initial heartbeat explanation for the24-second admission tail was wrong: both traces contain5,000 `Checking mempool` invariant scans, and almost the full interval lies inside ordinary admission (24.115s before,24.650s after, from PreChecks through acceptance). These elapsed intervals are not isolated CPU timings of the scans.

Regtest enables `checkmempool=1`; normal networks default to0. Source references: `kernel/chainparams.cpp:473`, `init.cpp:1638`, `txmempool.cpp:707`. Full invariant checking is a debug consistency scan, separate from consensus/policy validation. The separately labeled candidate checkmempool0 run passed, retaining all policy, consensus, authenticated membership, exact-body checks and DoS limits. It is not an additional source-only speedup.

The reproducible per-admission parser is `daemon/patch-intake/20261022/fullrecon-deadline-wake/admission-cost.py` (SHA2567a921d6b2f598ff507de5334f1bbc4c93537bc643faa9104a1491a1e1f3740e5). Raw timing rows are in `PHASES.json`. Source integration/replay remains pending measured handoff; active manifests were unchanged during the experiments.

## Production-profile result and remaining limit

The same candidate with explicit `-checkmempool=0` passed exact10,000 TxIds and raw-body/native-TxHash parity on all three nodes. Recovery took36.721s:35.355s capture→coverage,1.519s coverage→admission. This is a separately labeled configuration comparison. Full native source tests remained1,200/1,200 green with their original assertions.

The source-only check1 pair reduced total recovery29.35% (84.760→59.887s), with the fetch phase60.695→35.353s. The normal-setting36.721s result distinguishes the test-only invariant scan from production validation; it is not a further code speedup. No result establishes finalized or block-confirmed throughput.

The remaining~35-second bottleneck is serialized authenticated traversal:272 request cycles per peer with125ms spacing, one in-flight request. The repair preserves those bounds. Budgeted pipelining/credit is a separate design question; no blind limit increase or validation bypass was made here.

All three cases exited0 and their owned process groups drained. Whole-case peak RSS was0.964/0.949/0.902GiB (before/candidate/check0); these are group peaks, not retained daemon heap. Fresh cases use the same fixture count/shape but not identical transaction bytes/prefix distribution. `COMPARISON.json` carries exact source/binary/tool hashes, cumulative metrics, phase timestamps, exact-content proofs and resource receipts. The source owner was released for folding the tested fix into its original full-membership owner525 and replaying; no unrelated logical patch was added.
