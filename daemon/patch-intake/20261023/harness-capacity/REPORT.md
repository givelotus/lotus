# Load-generator capacity and RPC-worker attribution

The user requested proof that the harness limited throughput, followed by an isolated blocking-versus-co_await worker-count comparison. Node source is unchanged. The worker sweep compares blocking94453bdd with async-only6e70bcae; the atomic-reader candidate is excluded. No active source pins changed.

## Completed read proof

| RPC | One process, RPC/s | Four processes, RPC/s | Ratio |
|---|---:|---:|---:|
| getmempoolinfo | 14,202 | 44,405 | 3.13× |
| getblockchaininfo | 14,046 | 43,164 | 3.07× |

Three alternating pairs, unchanged combined binaryd2e4db3226, exactly12total warmed persistent connections and5seconds per sample. Same node/datadir while reading an empty mempool. Increased client process parallelism alone yields3.1× read throughput, establishing a generator-side limitation under these conditions. This does not prove node maximum capacity or explain every historical benchmark discrepancy.

## Initial admission screening

One complete8-cell round and one extra array sample are preserved at benchmark-results/20261023/harness-capacity-matrix. At equal8submitters/12readers, splitting the generator into4processes raised loaded admissions4904→10199tx/s; individual sends10966→17192tx/s. Arrays22628→22164tx/s did not improve. These admission comparisons have only one pair; they are exploratory, unlike the repeated read result. The broader run was interrupted on user steering; the interrupted attempt is excluded. All completed samples remain preserved.

## RPC-worker sweep

Running three alternating pairs each at1,2,4,8,16,32RPC workers. Constant four generator processes,8submitters and12readers alternating getmempoolinfo/getblockchaininfo. Same150000distinct presigned fixture cardinality,16total untimed warmup transactions,≥5s measured windows. Warm all subprocess threads/connections before common GO; reject>25ms start skew, fixture exhaustion, RPC errors, or incorrect exact mempool inventory. The smaller fixture reduces untimed setup for36samples and is identical across both sides; this is a distinct workload from the initial500K-corpus screening. One-worker smoke is seeded as the first valid pair, without remeasurement.

CPU evidence uses per-process ps CPU counters for all3nodes and the sum of measured child CPU. Node counters bracket0.1s common-start lead plus final drain; they are not exact critical-path attribution. Three nodes and generators share one host. No builds/profilers run during timings. Source/binary/config/tool hashes are in each input packet. Independent process partitions use disjoint read-only corpus offsets; no signing, funding, connection creation or thread startup is timed.

Tools: daemon/bench/harness-capacity/. All source/report paths are canonical; no extra source worktree or clone created.
