# Final527 snapshot-warmup depth profile

PASS, fully drained. One sampled diagnostic accepted500000 distinct timed native207B transactions in **21.041639s**, plus800 untimed warmup; final origin inventory500800. Exactbuilt source `e1ff963c6c913c76b11b766a5847668f8c9c7564` / tree `9a06a5a1c13780ae91390c4407ad90fefd35bbea`, daemon `46df6fde1c820c1b3207902c445600f426ca8643e389261124aef425e4705661` is tree-equivalent to imported527 `657edc0133cac8d54c5570506dad57bf10e300b5`. Original256KiB cache, jemallocON, fullscope source; samecache3c24/config024a. Eight persistent writers/ordinaryJSONarrays50, fee10000. Funding/signing/startup/pilot excluded. Sampled elapsed is diagnostic, not a clean comparison/max sustainable TPS result.

All three1ms/1s ownednode0 samplers overlap actual ingestion, proven by retained monotonic launch/exit/GO intervals. No compiler/heavyGit overlap was authorized. Fullsymbols are losslessly preserved in RAW-PROFILES.json. HOTSPOTS.md contains top20 exclusive active-candidate leaves perdepth, nonadditive application ancestors and separate waits. Recognized waits/idle/unresolved leaves are excluded from active candidates; per-thread leafsum equals root ticks. These are sample observations, not CPU percentages.

## Serialized path evidence

| Active leaf descendants / wait observations |50k|250k|450k|
|---|---:|---:|---:|
| BIP340 on rpcadmit | 0 | 0 | 0 |
| BIP340 on other precompute threads | 439 | 413 | 470 |
| rpcadmit active candidates | 525 | 546 | 526 |
| Finalize | 189 | 164 | 188 |
| snapshot publication | 149 | 154 | 141 |
| changed-entry capture | 111 | 130 | 110 |
| addUnchecked | 133 | 121 | 133 |
| noncrypto CheckInputScripts | 95 | 112 | 105 |
| Precompute mutex waits (not CPU) | 3 | 5 | 1 |

The intended advisory preparation lock is no longer prominent: Precompute mutex-wait leaves are3/5/1, versus1583/1626/1656 in the older82cc profile. Different windows/source histories make this corroboration, not a numerical causal CPU-share comparison. validation.cpp:3333 now first uses PrepareNativeCryptoFromSnapshot(:3269); only fallback acquires cs_main and performs old PrepareNativeCrypto. No hit counter was collected, so no exact fast-path percentage is asserted.

The next serialized mechanisms are authoritative admission and immutable publication: validation.cpp:1280 PreChecks, :1726 Finalize; node/transaction.cpp:51 AdmitBroadcastLocked; node/snapshot.cpp:1237 PublishMempoolSnapshot asserts mempool.cs, clones shared state, updates changed entries(:177/:1248), then publishes. Persistent radix copy/remove and RCU destruction appear in actual stacks. This is changed-entry work, not evidence of a complete mempool-copy regression. Noncrypto VM/context/input checks remain authoritative. No zero-allocation-under-lock or unnecessary-consensus-check claim follows.

Worker mutex-wait leaves100/117/124 are separate from active work. Producer condition waits reflect queue completion; sampled secp leaves remain mainly on precompute threads. Required reconciliation/commitment work is retained but is not the dominant serialized worker mechanism in these three windows. The bounded next direction is source-level review of publication frequency/RCU lifetime and authoritative per-request allocation/check costs, preserving snapshot and consensus semantics; no major CoW rewrite or new runtime is proposed here.

## Post-ingestion memory and counts

| Target seconds | Actual start | Node0 GiB | Node1 GiB | Node2 GiB | Inventories |
|---|---:|---:|---:|---:|---|
| 0 | 0.013 | 2.182 | 1.824 | 1.709 | 500800/500074/500148 |
| 5 | 5.009 | 2.151 | 1.824 | 1.709 | 500800/500800/500800 |
| 15 | 15.005 | 2.068 | 1.743 | 1.676 | 500800/500800/500800 |
| 30 | 30.010 | 2.068 | 1.743 | 1.676 | 500800/500800/500800 |

Whole-owned-group peak **6.805GiB**. Node0 RSS declines from2.182 to2.068GiB. Peers lag at0 and reach500800 by the next poll near5s; exact convergence time/TxId-set equality were not measured. Natural relay may continue; no extra transaction/mining traffic was introduced. RSS is not jemalloc live allocation/residency or a leak test. This lower peak does not erase the paired run's7.741GiB observation or resolve its cause.

First50k1.847s; last50k2.249s. Sample-overlapping chunks are marked in completion-chunks.csv. No quadratic or statistical claim. Source/binary/profile/tool/commands/fixtures/hostloads/resource guards remain in execution-plan/results/provenance. Driver68244 exited0; ownedPG57246 absent. All500k and exactorigin inventory checks pass. No additional runtime will follow without a concrete new failure or explicit task.
