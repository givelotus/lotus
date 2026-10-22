# Native signature warmup: matched ordinary RPC500k

**Both cases PASS and fully drained.** With the same reviewed TLS chain-domain correction at both endpoints, the native warmup candidate accepted500,000 transactions in **25.44687s**, versus **26.78097s** before: **4.98% less elapsed / 5.24% higher observed average rate** in this single unsampled pair.

| | Before524+TLS | After524+TLS+nativewarmup |
|---|---:|---:|
| Timed accepted |500,000|500,000|
| Untimed warmup |800|800|
| Exact final node0 mempool |500,800|500,800|
| Elapsed seconds |26.780967|25.446871|
| Observed accepted/s over finite case |18670.0|19648.8|
| First50k seconds |2.496|2.366|
| Last50k seconds |2.737|2.623|
| Peak monitored owned-group RSS |6.521GiB|7.849GiB|

This is a modest measured improvement, not a large recovery claim or maximum sustainableTPS result. No profiler was running. Both endpoints used eight persistent writers, JSON arrays of50 independent sendrawtransaction calls,500800 distinct prepared207-byte nativeBIP340 transactions,800 untimed warmup,10,000-sat fee, and2048MB configured mempool per node. Funding/signing, connection/thread startup and the4096-row sizing pilot were excluded. Actual clock ends on node0 RPC acceptance, not peer convergence. Unique prepared fixture consumption and exact final counts were checked; the fresh-funded fixture bytes differ but shape/count/fees are matched. Public test key42 with16 reused deterministic nonce points remains fixture provenance.

## Pins and correctness

Before source `306f4dfe2b9e25890bd361fc337f8f8344f43d55` / tree `3a9227011fce3a8e853ab9f8e7e7cb30108c9425`, binary `af59798f3889fef3d2085d7eb62e0e340ccce4754429f63d5deb3ccf3747352b`. Its tree equals imported ordered524TLS head2446653f. After source `82cceea30001e22b83fa08f6354e92e58cede2f3` / tree `c2ad1f419f3dcf0bbda2fd49044dd421ced4faf1`, binary `d24846e8c6f043d46a555368adc3584a3055460abbd2bd0346d07ccf04e5e00b`. Production differences are native warmup in validation.cpp/h; two test files add/adjust regression intent. Exact source delta is warmup-only.diff (SHA `34bf30a932c8b56d953c46339e9f0b043561174928641075667e1ce2865deb89`). Both share the same reviewed thread-local chain-domain fix; the unsafe mutable-global control is not measured.

Both binary hashes and exact identical CMake cache `3c24acb5287833f62f0f117498c7aa6f17050f8c05213678fbc0931235fb3e13` were independently checked before/after: jemallocON, Chronik/pluginsOFF, walletON, Release-O3/assertions, H2/WT OFF. N1 gates before timing: TLS baseline normal+genesis/identity cases PASS; candidate normal115 and six context/cache/TLS cases PASS. Correctness/build receipts remain owned by N1 at adaptive-reconciliation-gate. No staged consensus-verdict reuse is inferred from this benchmark.

## Limits and resource accounting

ONE observation per endpoint, fixed before→after order, no randomization or repeated statistics. Host loads before/after: baseline `[8.29248046875, 6.97119140625, 7.330078125]` / `[8.5595703125, 7.23828125, 7.40673828125]`; candidate `[8.5595703125, 7.23828125, 7.40673828125]` / `[8.58447265625, 7.40966796875, 7.458984375]`. No quiet-host or isolated hardware maximum claim. Candidate peak monitored RSS increased by1.328GiB; these whole-group peaks are one observation and do not establish a persistent memory leak or its cause. Both stayed below12GiB owned-group cap,6GiB free-indicator floor, critical pressure4 and4GiB new global-swap bounds. Per10k timings are in completion-chunks.csv; modest last-depth slowdown remains, without evidence proving quadratic behavior.

All driver and workload processes are drained (session75521 exit0; process groups97259/97759 absent). FULL-DRAIN.json records checks. Exact commands, source/binary/module hashes, preparation and actual counts are retained in each execution-plan/results/provenance. Original100k and stale9518 plans were never run; HOLD-NOT-RUN.json is historical, superseded by this report/RESULT-READY.json. No extra case or repeat was executed.
