# Corrected527 vs528: measured paired results

All requested core paths passed; **no active owned processes remain**. Both endpoints were rebuilt and passed full unfiltered gates before timing:5271187tests,5281200tests. The same signature-cache lifetime repair and exact-signed-transaction fixture repair are folded into both sides. Prior red-gate385b/c4 timing was never used. Canonical integration is528; evidence owner commit515550a8 supplies final frozen endpoints.

| Change/workload |527before |528after | Result / scope |
|---|---:|---:|---|
| Ordinary JSONarrays50,500k,4rotatedpairs: median origin accepts/s |22229.9|22207.2|Practical parity;8/8exact all-peer sets PASS|
| Same ordinary runs: median all-peer observed completion s |23.141|22.756|Poll upper bounds; no certified network gain|
|12loaded readers: read RPC/s during500k individual writes |7952.15|7954.15|Near parity; two sequential RPCs per measured read pair|
| Loaded writer500k seconds |100.301|100.629|Individual writes WITH12readers, not unloaded single-RPC throughput|
| Dedicated submitrawtxbatch200:500k origin seconds |25.217|23.686|One pair; about6.46% higher observed origin rate|
| Dedicated batch:500k all-peer completion seconds |65.970|66.994|No all-peer improvement; exact503200sets each|
| Aged full-scope recovery: reconnect→exact10k all3,seconds |81.842|81.391|Real64saging/noAVA; rawbody/TxHash and capability proof PASS|

The new Merklix implementation is integrated, but these endpoint observations **do not demonstrate a broad RPC or network-throughput gain**. Component gains are separate: existing three-repetition500k medians populate557.003→272.878ms; cached snapshot capture/rebuild273.759ms versus slab pin1.208us plus cached root0.166us. Cold first commitment REGRESSES17.263→24.807ms; long-lived slab snapshot release takes48.759ms. Preserve those tradeoffs; cached-root timing is not cold hashing. COMPONENT-MICROBENCH-REUSE.json proves subsequent endpoint repairs only changed signature-cache/test files, not Merklix component sources. StandaloneO2/NDEBUG component data are not daemonO3/assertions TPS.

## Meaning and limits

Eight persistent writers, native207B BIP340 transactions, fee10000, fresh confirmed funding. Ordinary batches are JSONarrays of independent sendrawtransaction requests; dedicated batch200 is a different RPC and bypasses the ordinary admission dispatcher. Unique500000 timed transactions are accepted percase;800ordinary/16individual/3200dedicated warmup transactions are excluded. Signing/funding/startup/pilot outside clock; network observer250ms adds declared overhead. Actual counts and same-endpoint all3sortedTxId digests pass independently. Fresh-funded raw fixtures differ across cases; shape/count/fees match.

All runs are one-host loopback, whitelist/highbandwidth/fullscope enabled, Avalanche disabled. Origin reply completion, all-peer mempool completion, block confirmation and Avalanche finalization are distinct. **No50k/s confirmed-block or network-wide sustained-capacity claim is established.** No actualblock confirmation stage ran here; small historical sealed-block correctness is separate. No standalone unloaded-individual500k or distributed3/3/2 injection result is inferred from loaded/single-ingress cases; those remain explicitly unmeasured in this latest matrix.

Ordinary uses initialpair plus3rotated repeats (527/528,528/527,527/528,528/527). Other paths have one observation perendpoint, not confidence-certified gains. External host work/thermal/clientJSON/GIL costs remain possible; receipts retain before/after loads and client CPU. No quiet-host/max-capacity claim. Whole-owned-group RSS/freeindicator/criticalpressure/newswap/time guards passed, no source/compiler overlap authorized. Wholecase memory includes funding/client/peer progress; do not call it live allocation or a leak test.

## Final exact endpoints

527: source`0f42fcfde6d36fd4326b8de18df17ce740b22446`, tree`a2c855dc0f6d16fa260549c40958ba37aecb03b9`, binary`7ca9d8a37f849ce5c2dadb76914cc7c7aeba4dc5bf12c695847d4d83766caa5c`, cache`279281b58582247ce194b9ace348bf3813e0311109b76f1b4d7d2b2fc37c421f`. Actual files physically in canonical ignored artifact archive; registeredsourcepeer underdaemon/worktrees. BothjemallocOFF/walletOFF/ChronikOFF/Release-O3withassertions. These differ from older46df walletON/jemallocON datasets.

528: source`922eb4a7f9d8ec8af7a5e64d521454c572ece937`, tree`1c267e0b5b115f216d5d88731074f4ac794f7a4f`, binary`3dc28247e6ebffb110da554476cbb592bdcfef420225de82ba74bd04feb667f8`, cache`22c44b3172c0044a41b421f0e6927e015c12a8894aba84edd29da5b2962ee013`. Actual files physically in canonical ignored artifact archive; registeredsourcepeer underdaemon/worktrees. BothjemallocOFF/walletOFF/ChronikOFF/Release-O3withassertions. These differ from older46df walletON/jemallocON datasets.

Perphase REPORT/RESULTS, inputENDPOINTS/toolhashes, exactcommands/adaptedworkload/provenance, resources/progress/fixturehashes and recovery evidence remain alongside. RAW-RUN-LOGS.json preserves exact small logs with original hashes. All owned groups are absent inFULL-DRAIN.json. No production nodes/data/release assets touched; no more runtime started by sealing.
