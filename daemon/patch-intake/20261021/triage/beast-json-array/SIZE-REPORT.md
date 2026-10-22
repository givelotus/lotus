# Transaction-sized JSON control

All 16 cases passed response validation and clean shutdown. Arrays still execute sequentially. These controls exclude transaction admission and compare the same frozen ABC and 521 endpoint binaries as the first control; they do not isolate Beast source changes from coroutine/allocator/other endpoint changes.

| Hex argument | Clients | Calls/request | ABC calls/s | Frozen 521 calls/s | Ratio |
|---|---:|---:|---:|---:|---:|
| 207 bytes → 414 hex characters | 1 | 1 | 12,619 | 10,180 | 0.807× |
| 207 bytes → 414 hex characters | 1 | 50 | 122,669 | 121,554 | 0.991× |
| 207 bytes → 414 hex characters | 8 | 1 | 41,740 | 47,789 | 1.145× |
| 207 bytes → 414 hex characters | 8 | 50 | 520,941 | 509,311 | 0.978× |
| 414 bytes → 828 hex characters | 1 | 1 | 11,864 | 10,818 | 0.912× |
| 414 bytes → 828 hex characters | 1 | 50 | 89,099 | 84,223 | 0.945× |
| 414 bytes → 828 hex characters | 8 | 1 | 40,631 | 44,720 | 1.101× |
| 414 bytes → 828 hex characters | 8 | 50 | 357,074 | 372,662 | 1.044× |

The current endpoint has **no consistent large-JSON array throughput regression**: for 414-character arguments, array50 is about equal at c=1 and 2.2% lower at c=8; for 828-character arguments, it is 5.5% lower at c=1 and 4.4% higher at c=8. These one-pair differences under changing host load are not sufficient for a repeatable small regression/speedup claim.

| Single-client request p50 latency | ABC | Frozen 521 |
|---|---:|---:|
| 414 hex characters, 1 calls/request | 66.5 us | 85.5 us |
| 414 hex characters, 50 calls/request | 394.6 us | 397.7 us |
| 828 hex characters, 1 calls/request | 71.3 us | 78.0 us |
| 828 hex characters, 50 calls/request | 545.2 us | 580.3 us |

The narrower historical concern remains plausible: single-client/single-command latency can be higher even when concurrent throughput improves. This control reproduces a 19 us median single-call gap at 414 hex characters (66.5 → 85.5 us), while the equally sized array50 medians are nearly equal (394.6 → 397.7 us). Therefore it does not reproduce the old 35–40 us array50 gap as a general current behavior.

Each case lasts five seconds with ten untimed warmup requests per connection. One independent client process owns each warmed persistent HTTP/1.1 connection; no sampler ran. Complete latencies are measured on the client around HTTP request/send/response/decode/validation and then pooled for p50/p95/p99 outside timing. Exact request body bytes, response body totals, per-client CPU, counts, UTC/host load, executable/script hashes and commands are in `size-results.json` and per-case `results.json` files. The hexadecimal payload is deterministic and identical at both endpoints.

Echo intentionally returns the complete hex argument, so the response is much larger than sendrawtransaction's TxId response. This exercises JSON decoding, result construction and encoding plus both socket directions; it is not an exact raw-transaction submission simulation. Handler/parse/serialize/executor stage timings are not individually instrumented, so no specific phase is named as a demonstrated cause.

The exact introducing-source boundary is documented separately: the libevent and initial-Beast source revisions have byte-identical RPC dispatch and UniValue parser/writer files. A fresh build at that boundary is the remaining causal control if a production transport repair is pursued. No production patch was made based on these endpoint observations.

All eight owned daemons and all client processes exited cleanly. `size-DRAIN.json` records the released runtime boundary; no compiler overlapped the controls.
