| Change | Workload | Before | After | Change | Adoption |
|---|---|---:|---:|---:|---|
| Atomic readers | Individual sends, tx/s | 11,797 | 11,672 | -1.1% | Candidate |
| Atomic readers | Arrays of 50, tx/s | 22,976 | 23,035 | +0.3% | Candidate |
| Atomic readers | Sends + readers, tx/s | 5,141 | 5,067 | -1.4% | Candidate |
| Atomic readers | Concurrent reads, RPC/s | 7,945 | 7,919 | -0.3% | Candidate |
| Async admission | Individual sends, tx/s | 12,146 | 11,943 | -1.7% | Candidate |
| Async admission | Arrays of 50, tx/s | 23,785 | 23,216 | -2.4% | Candidate |
| Async admission | Sends + readers, tx/s | 5,217 | 5,221 | +0.1% | Candidate |
| Async admission | Concurrent reads, RPC/s | 8,073 | 8,132 | +0.7% | Candidate |
| Combined | Individual sends, tx/s | 12,012 | 12,054 | +0.3% | Candidate |
| Combined | Arrays of 50, tx/s | 23,310 | 22,405 | -3.9% | Candidate |
| Combined | Sends + readers, tx/s | 5,187 | 5,220 | +0.6% | Candidate |
| Combined | Concurrent reads, RPC/s | 8,034 | 8,154 | +1.5% | Candidate |

Medians of three alternating pairs per comparison; each measured window ≥5 seconds. Same queue-only control and negotiated peer behavior. Each comparison uses its own matched control runs; do not add the percentages. Eight submitters, 16 RPC workers; loaded cases add 12 clients alternating getmempoolinfo/getblockchaininfo. Shared ABC/eCash, wallet/Chronik/H2/WT/jemalloc OFF. RPC acceptance, not block confirmation or all-peer completion. Exact ranges, source and binary hashes are linked through MEASUREMENTS.json and the three result packets. Profiles are excluded.
