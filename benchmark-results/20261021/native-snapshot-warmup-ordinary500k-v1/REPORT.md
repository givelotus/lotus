# Snapshot-based native warmup: matched 500,000-transaction pair

Both runs passed and fully drained. Origin RPC acceptance took **25.904766s before → 20.433742s after**: **26.77% higher observed average acceptance rate**, or 21.12% less elapsed, in one unsampled pair.

| Metric | Before | After |
|---|---:|---:|
| Timed distinct accepted |500000|500000|
| Untimed warmup |800|800|
| Final origin inventory |500800|500800|
| Seconds |25.904766|20.433742|
| Observed accepted/s |19301.47|24469.33|
| First50k seconds |2.445|1.861|
| Last50k seconds |2.616|2.130|
| Peak whole-owned-group RSS GiB |6.084|7.741|

Eight persistent writers used JSON arrays of50 independent sendrawtransaction calls, native207B BIP340 transactions, fee10000 and three connected loopback nodes. Funding/signing, startup, warmup and preparation pilot were outside the clock. Fixture bytes differ between fresh funding instances; shape/count/fee and publickey42/16-reused-nonce signing distribution match. No sampling profiler was used. This is finite origin acceptance, not maximum sustainable TPS or all-peer throughput. Exact per-writer acceptance and completion chunks are retained.

## Source and validation

Before ordered definition `f0b6293e85f44786b3d96557bf4962507653cf55` / tree `dc9bf31432aaac8a7e2aeb45896dc5f4dd07600c` is byte-identical to actual compiled source `6a2782e6c7a2b3fe2fba3b14525345f0b3b1111f`; daemon SHA `3055ec18070e3a6b1c2196f2c4c7cb1c4a70cc48847a03e8ba2166ec6c0e61b4`. After actual source `e1ff963c6c913c76b11b766a5847668f8c9c7564` / tree `9a06a5a1c13780ae91390c4407ad90fefd35bbea`, daemon SHA `46df6fde1c820c1b3207902c445600f426ca8643e389261124aef425e4705661`. Candidate production matches reviewed01822776; its final test namespace repair is included. Exact source delta is in SOURCE-DELTA.json.

Both use original256KiB cache, fullscope enabled source, identical cache `3c24acb5287833f62f0f117498c7aa6f17050f8c05213678fbc0931235fb3e13`, jemallocON, Chronik/pluginsOFF, walletON, Release-O3 with assertions, H2/WT OFF. The optional4KiB experiment is excluded. Actual normal builds and meaningful snapshot/native/context/TLS checks passed before launch; BINARY-READY receipts remain at the preserved binary locations named in execution plans.

The change prepares advisory native crypto from immutable snapshot coin facts instead of repeating locked PreChecks/capture. Authoritative admission still performs current checks; no staged verdict is reused. The corpus is eligible under normal published SMT context, with fallback for missing/lagging coverage. No runtime hit counter was measured, so this report assigns no observed fast-path percentage.

## Memory and peer progress

Observations are outside ingestion timing, without extra transaction/mining traffic. Natural relay continues. Actual offsets, client RSS, per-daemon RSS and resource samples remain in COMPARISON.json and execution-results.json.

| Endpoint | Target seconds | Node0 RSS GiB | Node1 RSS GiB | Node2 RSS GiB | Actual peer inventories |
|---|---:|---:|---:|---:|---|
| before | 0 | 1.762 | 2.140 | 1.795 | 500800/500800/500800 |
| before | 5 | 1.762 | 2.140 | 1.796 | 500800/500800/500800 |
| before | 15 | 1.762 | 2.141 | 1.796 | 500800/500800/500800 |
| before | 30 | 1.702 | 2.096 | 1.751 | 500800/500800/500800 |
| after | 0 | 2.648 | 2.329 | 2.372 | 500800/499701/499708 |
| after | 5 | 2.649 | 2.295 | 2.301 | 500800/500800/500800 |
| after | 15 | 2.341 | 1.685 | 1.686 | 500800/500800/500800 |
| after | 30 | 2.341 | 1.685 | 1.686 | 500800/500800/500800 |

Before already had500800 transactions on all three nodes at the first poll. After had500800/499701/499708; all three reached500800 by the next poll near5s. This is counts-only evidence: peer TxId-set equality and exact convergence time were not measured. The26.8% origin gain must not be presented as a network throughput gain.

The candidate has a material observed RSS tradeoff: group peak rose from 6.084 to 7.741GiB; origin RSS at30s was 1.702 versus 2.341GiB. Peer progress differs at ingestion end. Allocator residency/fragmentation, phase history and variation remain unresolved; these observations prove neither a leak nor a sole intrinsic retention cause. No jemalloc live/resident API was added.

Host loads before/after each case: before `[7.2958984375, 5.8388671875, 5.74755859375]` / `[6.5009765625, 6.03515625, 5.8349609375]`; after `[6.5009765625, 6.03515625, 5.8349609375]` / `[6.52734375, 6.0830078125, 5.86376953125]`. No quiet-host or statistical confidence claim. Fixed before→after order, one observation each. No historical ABC run is substituted as a paired control.

Driver session35130 exited0. Owned process groups47532/49067 are absent. Both fully drained; no binaries or large fixtures are committed. Root approved adoption with this memory limitation explicit. A final depth-profile plan is separate and has not been executed.
