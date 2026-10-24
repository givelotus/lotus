# Native staged-verdict reuse: paired result

| Workload | Before median | After median | After/before |
|---|---:|---:|---:|
| Native RPC admission | 48,507 TPS | 49,666 TPS | 1.024 |
| Exact three-peer completion | 21,634 TPS | 22,055 TPS | 1.019 |
| Accepted-block / Avalanche finality | Unmeasured | Unmeasured | — |

| Pair | Before timed tx | After timed tx | Before admission TPS | After admission TPS | Before peer TPS | After peer TPS |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 244,600 | 252,400 | 48,507 | 49,666 | 22,375 | 23,312 |
| 2 | 250,400 | 258,600 | 49,623 | 50,871 | 17,063 | 17,549 |
| 3 | 239,200 | 239,000 | 47,190 | 47,604 | 21,634 | 22,055 |

The observed median differences are +2.4% admission and +1.9% exact peer completion. Round-to-round peer rates vary substantially; this small comparison does not establish a large speedup. The raw producer batch RPC path is unchanged; C11 changes native staged admission at receiving peers. C5 pool consolidation is not included. The candidate remains separate pending integration and profiling.

Three alternating pairs, matching build flags,4 generator processes/8 writers/0 readers, batch200, three validating nodes on one Apple M5 Max48GiB. Each throughput window exceeded5seconds. One million distinct signed BIP340-P2PK207-byte fixtures were prepared per run; actual timed counts are listed above, not one million. Propagated3200warmup transactions are excluded. Exact-peer TPS includes count convergence and final full inventory RPC/sorted-ID digest verification. Every run's three inventories have identical counts and digests. No task-owned builds/indexing jobs or profiler ran during timing; pre-existing live nodes were left untouched and external host load varied, as recorded in the resource samples. Chronik/jemalloc/HTTP2/WebTransport were OFF in both builds.

Before: `8b55e7c8de373d2097da1ebacfcf14fd1098d046`, tree`2ac7093521dcf926c15eb9b77babb881ddff771a`.
After: `2d64521cc6f058d8be9f9bf5dfa9e8e5bd0bc8c4`, tree`38f676d4d933b2e764e6e6df1c6c6647f6ad5777`.
The after binary was built from the exact recorded dirty feature source, then committed without production source changes; generated version metadata identifies that build-time base. BUILD receipts retain the source hashes and this distinction.

Reproduction: `daemon/bench/harness-capacity/compare_native.py --network-completion --fixture-transactions 1000000 --owned-rss-limit-gib 18`, with `C11-PAIRED-BEFORE-BUILD.json` and `C11-PAIRED-AFTER-BUILD.json` in the parent directory. Full argv/tools/source/resource/progress/results evidence is in `benchmark-results/20261023/native-staged-verdict-peer-pairs/` and the compressed archive beside this report.
