# Warmup pair: memory receipt audit (no new run)

The reported6.52→7.85GiB is the **peak sum of the whole owned process group**: three daemons, benchmark Python and any transient same-group helper. It is not per-daemon peak or an isolated retained-memory measurement.

| Endpoint | Group peakGiB | Peak relative to RPC ingestion end | Daemon sum pre-measureGiB | Daemon sum post-measureGiB |
|---|---:|---:|---:|---:|
| before | 6.521 | +0.749s | 5.828 | 6.253 |
| after | 7.849 | -0.238s | 5.841 | 7.638 |

Timing alignment is approximate: group RSS is sampled about every0.5s in driver monotonic time; ingestion GO/end comes from metric UTC boundaries. Baseline peak is near post-ingestion cleanup/relay, candidate peak just before ingestion finishes. These are different run phases and no per-process decomposition at the exact peak was stored.

| Endpoint/node | Pre-measureRSSGiB | Post-measureRSSGiB | Recorded final mempool |
|---|---:|---:|---|
| before/0 | 1.900 | 1.938 | 500800 |
| before/1 | 1.962 | 2.169 | not recorded |
| before/2 | 1.966 | 2.146 | not recorded |
| after/0 | 1.905 | 2.655 | 500800 |
| after/1 | 1.972 | 2.454 | not recorded |
| after/2 | 1.964 | 2.529 | not recorded |

The post-measure nodeRSS is captured immediately after the writer futures drain, before origin inventory RPC; peer relay can still be in flight. No stabilized idle/RSS sample or final peer inventory was taken. Node0 alone is strongly matched at500800. The Python high-water marks are about246MiB both cases; they are not current RSS at the group peak. Final driver tail drops to tens ofMiB when daemons stop; that confirms drain, not memory reclamation in a running idle daemon.

Therefore the data supports an observed whole-case peak increase of1.33GiB and higher immediate post-measure daemonRSS. It does **not** prove a persistent leak, retained warmup-object size, or sole causal attribution to warmup. Peer progress, allocator residency and phase alignment remain unresolved from existing receipts. No rerun or extra probing was performed.
