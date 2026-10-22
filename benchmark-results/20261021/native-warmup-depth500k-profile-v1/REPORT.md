# Native warmup: depth profile and post-ingestion memory

**PASS and fully drained.** Exactcandidate source `82cceea30001e22b83fa08f6354e92e58cede2f3` / tree `c2ad1f419f3dcf0bbda2fd49044dd421ced4faf1`, daemon `d24846e8c6f043d46a555368adc3584a3055460abbd2bd0346d07ccf04e5e00b`, cache3c24jemallocON.500000 distincttimed native207B transactions accepted in **26.36793s**,800untimedwarmup, finalnode0500800. Three ownednode0 depth samples(1ms/1s) have observed lifetimes wholly inside the post-warmup GO interval. This one sampled fixed-work run is diagnostic, not a clean/max/sustainableTPS result. No new comparison pair is inferred from its elapsedtime.

## Crypto moved out of the serialized worker

| Active leaf descendants at depth |50k|250k|450k|
|---|---:|---:|---:|
| BIP340 inrpcadmit | 0 | 0 | 0 |
| BIP340 inHTTP/precomputeworkers | 255 | 331 | 273 |
| rpcadmit activecandidateleaves | 367 | 404 | 396 |
| rpcadmit Finalize | 124 | 134 | 125 |
| rpcadmit snapshotpublication | 114 | 104 | 106 |
| rpcadmit changedentrycapture | 81 | 75 | 84 |
| rpcadmit addUnchecked | 94 | 98 | 85 |
| rpcadmit noncryptoCheckInputScripts | 73 | 86 | 84 |
| Precompute mutexwaitleaves (notCPU) | 1583 | 1626 | 1656 |

Counts are sampled non-idle **active candidates**, excluding recognized waiting/idle/unresolved leaves. Ancestor rows are **nonadditive** and are not CPU percentages. Every thread's exclusive leafsum equals its root tickcount. Zero sampled BIP340 onrpcadmit in these windows is evidence of the intended placement, not a measured100%cachehit guarantee or proof that verification is absent at every instant. Sourcevalidation.cpp:3237/3266 warms the ordinaryVM/cache oncopiedcoins outsidecs_main; the worker still derives/executes authoritative checks. Source/nativecache context tests remain N1's separate correctness evidence.

The next serialized costs are concrete: Finalize plus immutable publication/capture/addUnchecked under validation.cpp:1883 pool.cs/cs_main and snapshot.cpp:1235. NoncryptoVM/script work remains. No zero-allocation-under-lock claim is justified. Full details and exclusive top20 perdepth are HOTSPOTS.md/hotspot-analysis.json; thread-specific ancestors are retained for reproduction.

A second pipeline limit is visible: validation.cpp:3275 PrecomputeMempoolAdmission first acquirescs_main, calls PrepareNativeCrypto at3205 underpool.cs, which calls PreChecks with deferredscripts. Only then does it release locks forcrypto. Authoritative admission later repeats PreChecks. This produces1583/1626/1656 recognized mutex-wait leafobservations at the precompute callsite. These are wall-thread waits, not CPU cost; background/producer waits must not be summed as utilization. It is a plausible reason moving crypto yielded only a modest matchedpair gain, not a proof of causal share.

Narrow followup ideas only: capture the minimum owned primitivecoin/rulecontext needed for advisory crypto rather than repeating fullPreChecks, or reuse alreadyknown immutable primitives under an exactcontext/lifetime check. Authoritative currentcoin/rule/fee/conflict checks must still run; no staged execution verdict or unsafepointeridentity reuse is proposed. Further source gating belongs to the existing admissionowner; no broader redesign/newexperiment was started here.

## Bounded post-ingestion observation

Allthree reportedmempoolcounts are500800 at0/5/15/30s. This run recorded **counts, not peerTxId-set equality**; it is not a fullscope/WAN/recovery proof. No newtransactions/mining/manualinventory were sent during the window, but naturalrelay/reconciliation work could continue. Read-onlyRPC/ps observation overhead is outside ingestion elapsed.

| Targetoffsets | Actualstartoffsets | Node0RSSGiB | Node1RSSGiB | Node2RSSGiB | ClientcurrentRSSMiB |
|---:|---:|---:|---:|---:|---:|
| 0 | 0.016 | 1.955 | 2.117 | 2.097 | 230.1 |
| 5 | 5.003 | 1.935 | 2.111 | 2.088 | 230.2 |
| 15 | 15.010 | 1.921 | 2.101 | 2.078 | 230.2 |
| 30 | 30.010 | 1.894 | 2.083 | 2.059 | 230.3 |

Peak monitored whole-owned-groupRSS **6.462GiB**. Node0RSS declines1.955→1.894GiB while allthreecounts stay500800. The prior unsampledaftercase's7.85GiB grouppeak and2.655GiB immediateoriginRSS were not reproduced here. This weakens a claim of an intrinsic/deterministic warmupretention penalty; it does **not** invalidate that earlier observation or isolate its cause. There is no pairedbaseline idlewindow, livejemallocallocated/resident RPC or stablelongterm leakmeasurement. Existing getmemoryinfo reportslocked-wallet-memory only andDarwinmallocinfo is unavailable; no daemon/API change was made to obtainallocatorstatistics.

First50k **2.414s**, last50k **2.788s**; profilers perturb adjacentchunks, marked incompletion-chunks.csv. No quadratic-complexity claim follows. Exactcommands/modulehashes/fixtures/resourceguard data remain inexecution-plan/results/provenance. Same8writers/JSONarrays50/native207B/fee10000 andstreamed500800fixture; funding/signing/startup/pilot excluded. Fullscope5fa was deliberately excluded from this82cc profile, and no newfeature's correctness/performance is inherited across those sources.

Both this runtime and the precedingfullscopegate are drained. No extraexperiments started. The earlier matchedunsampled500k pair remains the only source-matched warmupperformance comparison(26.78097→25.44687s,5.24%observedrate increase,onepair).
