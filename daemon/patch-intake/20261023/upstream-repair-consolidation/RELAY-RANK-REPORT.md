# Relay rank caching: validated native admission

| Workload | Before median | After median | Change | Status |
|---|---:|---:|---:|---|
| Native V2 signed batch200 RPC admission, 8 writers in4 processes |35,711 tx/s|46,904 tx/s|+31.3%|Native candidate: full1,203 C++ cases pass; shared full1,022-case gate passes after a separately owned fee-test precondition repair; final native1,203-case gate passes |

| Alternating pair | Before tx/s | After tx/s |
|---|---:|---:|
|1|32,305|45,932|
|2|35,711|52,292|
|3|36,982|46,904|

These are **validated admission**, not all-peer synchronization, confirmed-block throughput or Avalanche finality. Three loopback nodes share this machine; only node0 receives the RPC workload. Each timed run lasts at least five seconds, uses one million distinct presigned native v7 BIP340-P2PK transactions, fixed3,200-transaction untimed warmup and exact source-mempool inventory checks. The public fixture key and16 reused nonce points are intentionally insecure benchmark data; this is one script/key distribution, not coverage of arbitrary wallet or contract workloads.

The earlier800K-fixture first pair37.3K→56.3K and1.2M first pair29.6K→54.9K are exploratory. Both series stopped before three complete pairs: the former hit a pilot-supply preflight check, the latter a preparation memory guard. A subsequent1M attempt also stopped at the12GiB aggregate setup limit. Their valid partial samples are retained but **not included** in the above medians. Different fixture counts produce different confirmed UTXO state sizes; do not mix their numbers.

## What changed

Original temporary-heap comparisons recursively locked the mempool and looked up both txids to obtain admission order. Candidate4278a1fb resolves each queued admission rank once under one coherent view; the heap compares cached integers. Existing-before-stale ordering, topological admission order, known-ID filtering, relay rate caps, capability negotiation and transaction validation remain unchanged. The transaction-reference output vector reserves the tick budget rather than the whole backlog. The relay test now verifies exact ordering alongside16 announcements, negotiated pushes and known-ID exclusion.

The original full-backlog scan and temporary-heap rebuild still happen on every relay tick. This patch reduces repeated comparison work; a persistent queue is a separate algorithmic follow-up, especially for sustained backlog growth.

## Hardware, build and identities

Apple M5 Max, Mac17,6,18 CPU cores,48GiB physical RAM. Release builds disable wallet, Chronik, H2, WebTransport and jemalloc. Real native signature/script validation remains enabled; Avalanche is disabled. Commands/configuration/tool hashes and process CPU/RSS records are in the raw receipts. No build or profiler ran during the timed comparison.

Baseline compiled3cfb703183eb4134d3fbebfe862127450cd4c199, treea576cd04fc505e68069809d0bc00ec8ed96b4955, binary SHA2566ee569ee11ea97de68b5ff7b7e32b347967d3f4317ef18cd6c8dd7ac55d36866. This is the exact tracked tree of the reviewed and cohortA-consolidated native endpoint.

Candidate compiled4278a1fbb9ac0f90ef6ce9dbcdc783761010230a, tree5c43eabb1f82032549649e625cd304d0b640cb2c, binary SHA25684a6eca0eb26c4ff478186977b25c145b29019c3f00a5e1ed5b190aa981aeadd.

All1,203 native C++ cases and31,433,982 assertions passed. Focused prefix gate passed158 cases. Test receipts are separate from throughput measurements.

The three-node/generator group had an explicit18GiB cap for this final comparison, below half the physical host memory, with unchanged6GiB host-free minimum, critical-pressure,4GiB swap-growth and1,800-second limits. Observed aggregate RSS peaks ranged6.37–11.20GiB; largest sampled individual process at those group peaks was3.38GiB. These include fixture preparation and are not memory-per-TPS estimates. The earlier aborted1M setup briefly reached13.71GiB while host availability remained23.5GiB with no swap growth; the specific guard reason and per-process RSS now persist.

Raw completed comparisons: `benchmark-results/20261023/native-relay-rank-cache-pairs-1000k-18g/`. Baseline sampled stacks and corrected exclusive wall-sample classification: `benchmark-results/20261023/native-batch-profile-baseline/`. Instrumented rates are excluded. Earlier tool bytes and failed attempts are retained in the canonical evidence archive. See RELAY-SHARED-STATE.json and RELAY-COMPOSED-OWNERSHIP.json for the shared placement, unchanged tested native tree and full owner ledger. Active source pins remain unchanged.

## Shared test precondition repair

The first full shared gate passed1,021/1,022 cases: its successful first RPC updated fee policy, while a later fee-rejection case assumed the original9,000 rate still applied. V2 adapter4371511f already re-established that precondition. The repair now belongs to shared RPC owner2e735ad1 (rewritten owner recorded in RELAY-COMPOSED-OWNERSHIP.json); each rejection sets and asserts its rate. All fee-rejection, exactly-one-attempt and no-insertion assertions remain. Full shared gate now passes1,022 cases/31,167,602 assertions. The duplicate native reset is removed with an explicit adapter record; native transaction encoding and diagnostics remain intact. This is a separate test-only correctness change, not another claimed speedup. The new native tracked treef9e86468 differs from benchmarked5c43eabb only in this test file; production files are identical. Final native validation passes1,203 cases and31,480,438 assertions.
