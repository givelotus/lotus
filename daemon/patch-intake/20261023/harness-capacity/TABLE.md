# Scoped throughput tables

Medians of three alternating pairs. Blocking vs async-only; atomic reader changes excluded. **Both tables below are shared ABC/eCash with legacy transactions, not native V2.**

Fixed 8 submitters + 12 readers; four generator processes

| RPC workers | Blocking tx/s | Async tx/s | Change | Blocking read RPC/s | Async read RPC/s | Change |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 7,302 | 7,463 | +2.2% | 11,250 | 25,124 | +123.3% |
| 2 | 10,572 | 9,883 | -6.5% | 17,817 | 25,697 | +44.2% |
| 4 | 11,083 | 10,360 | -6.5% | 23,122 | 25,115 | +8.6% |
| 8 | 10,591 | 10,752 | +1.5% | 24,391 | 25,303 | +3.7% |
| 16 | 10,557 | 10,341 | -2.0% | 24,958 | 24,126 | -3.3% |
| 32 | 10,206 | 9,874 | -3.2% | 24,022 | 24,407 | +1.6% |

Fixed 16 RPC workers; equal submitters/readers; eight generator processes

| Client workers | Blocking tx/s | Async tx/s | Change | Blocking read RPC/s | Async read RPC/s | Change |
|---:|---:|---:|---:|---:|---:|---:|
| 16 | 13,775 | 13,338 | -3.2% | 31,039 | 30,715 | -1.0% |
| 32 | 14,128 | 13,823 | -2.2% | 34,874 | 35,285 | +1.2% |
| 64 | 15,736 | 12,299 | -21.8% | 27,231 | 38,744 | +42.3% |
| 128 | 16,611 | 12,211 | -26.5% | 21,390 | 37,019 | +73.1% |

Native V2 batch injection is a separate workload on the preserved native baseline:

| Measurement | Three runs | Median |
|---|---|---:|
| Validated signed batch-200 admission, tx/s | 35,782 / 36,788 / 38,769 | 36,788 |
| Echo transport only, transaction-sized items/s | 1,627,624 / 1,639,442 / 1,588,624 | 1,627,624 |

Echo performs no transaction validation. Native fixtures contain 800,000 distinct signed transactions per trial; measured windows last at least five seconds and verify exact source inventory. No confirmation or all-peer completion claim. Source identities, ranges, profile interpretation and native coroutine correctness are in REPORT.md and the evidence archive.
