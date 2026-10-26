# 4KiB native warmup cache: one matched500k pair

**Both PASS and fully drained.** Originalwarmup accepted500000 transactions in **26.013697s**; the4KiB candidate took **25.218769s**. That is **3.15% higher observed average rate / 3.06% less elapsed** in ONE unsampled pair, not a certifiedmaximum or repeatedstatistical gain.

| | Warmupbefore |4KiBafter |
|---|---:|---:|
| Timed accepted |500000|500000|
| Untimed warmup |800|800|
| Exact final origin mempool |500800|500800|
| Finitecase elapsed seconds |26.013697|25.218769|
| Observed accepted/s |19220.6|19826.5|
| First50k seconds |2.456|2.353|
| Last50k seconds |2.630|2.597|
| Peak whole-owned-groupRSSGiB |6.336|7.701|

Both runs used8persistentwriters, JSONarrays50 independent sendrawtransaction calls,500800 distinct207B nativeBIP340 transactions/fee10000,800warmup excluded,2048MBmempool pernode andthreeconnectedloopbacknodes. Funding/signing, connection/threadstartup and4096pilot were outsideclock. No profiler was used. The genericfixed-work adapter label/stdout mentionsCPUdiagnostic, but actualsampler arrays are empty. Timer ends on originRPCacceptance; no networkceiling or peerTxId-set equality is claimed. Count500800 was independently read on allthree at0/5/15/30s after each ingestion. Fresh-funded fixture bytes differ, but shapes/counts/fees match. The publickey42/16reusednonce fixture distribution is unchanged.

## Exactpins and gate

Before source `82cceea30001e22b83fa08f6354e92e58cede2f3` / tree `c2ad1f419f3dcf0bbda2fd49044dd421ced4faf1`, daemon `d24846e8c6f043d46a555368adc3584a3055460abbd2bd0346d07ccf04e5e00b`. After `3b22d66a51ecaa7d4532dc1b84795b226883cad6` / tree `38f4fcd70b7c1658da1c9c70656b21cc22d1693d`, daemon `a247d2f6b9be12232f4ad95f109226d2674a983d9fda20af820899abb92cab3c`. Identical CMakecache `3c24acb5287833f62f0f117498c7aa6f17050f8c05213678fbc0931235fb3e13`: jemallocON, Chronik/pluginsOFF, walletON, Release-O3/assertions, H2/WT OFF. Both include the same reviewedTLS chain-domain fix andnativewarmup. The newfullscope feature is **excluded at both ends**; this is not performance evidence for the joint526tree orfullscope525. Exactsource delta is durably captured inSOURCE-DELTA.json with hash.

N1 supplied actual4KiB normal288actionsPASS81.22s and pool/coinsFlush/reallocation/32input +sixnative/TLS checksPASS before launch. Actual preserved binaries andconfig/cache hashes were checked; source definitions remained clean. Existing authoritative validation is still performed; no stagedverdict reuse is inferred by the timing result.

## Post-ingestion memory observations

No newtx/mining/forcedinventory were sent during the bounded observation window. Naturalrelay/reconciliation work maycontinue. Actualoffsets andperprocessRSS are inCOMPARISON.json; each snapshot is outsideingestionelapsed.

| Endpoint | Targetseconds | Node0RSSGiB | Node1RSSGiB | Node2RSSGiB | ClientcurrentRSSMiB | All3counts |
|---|---:|---:|---:|---:|---:|---|
| before | 0 | 1.818 | 1.824 | 1.755 | 238.7 |500800/500800/500800|
| before | 5 | 1.819 | 1.826 | 1.757 | 238.7 |500800/500800/500800|
| before | 15 | 1.811 | 1.818 | 1.748 | 238.7 |500800/500800/500800|
| before | 30 | 1.794 | 1.803 | 1.734 | 229.8 |500800/500800/500800|
| after | 0 | 2.418 | 2.458 | 2.418 | 245.5 |500800/500800/500800|
| after | 5 | 2.419 | 2.399 | 2.362 | 245.5 |500800/500800/500800|
| after | 15 | 2.267 | 1.822 | 1.791 | 245.5 |500800/500800/500800|
| after | 30 | 2.246 | 1.711 | 1.663 | 245.5 |500800/500800/500800|

The memorytradeoff remains unresolved: the4KiBcase's grouppeak is higher and originRSS at30s is **2.246GiB** versus **1.794GiB** before. Its peers fall below thebeforecase'speerRSS by30s. This is stronger endpoint/countinformation than the earlierpeak-only comparison, but not liveallocated/residentjemallocstatistics, a long-term leaktest, or proof of a sole sourcecause. Allocatorresidency/fragmentation, phase history andsamplevariation remain confounds. The earlierwarmup7.85GiBpeak was not reproduced in itsfollowupprofile; do not extrapolate a deterministicretentionpenalty from onepeak here either. No additional experiments were run.

Hostload before/after: before `[4.3125, 5.49267578125, 5.49853515625]` / `[7.29736328125, 6.5244140625, 5.91162109375]`; after `[7.29736328125, 6.5244140625, 5.91162109375]` / `[5.9453125, 6.34326171875, 5.8974609375]`. No quiet-host claim. WholePGpeaks stayed below12GiB and existinghostguards. The one valid observation perendpoint usesfixed before→after order; source/profiles differ fromolderABC/historicalruns, so none are silently substituted as paired controls.

Session33381exit0; ownedPG28832/29902 absent. N1/root/resourcecoordinator were notified fullcompiler/runtimeboundaryrelease. No binaries orlargefixtures are included incommittedreceipts. Exactcommands/modules, actual counts,postwindowoffsets andresource samples remain ineach executionplan/results/provenance; rawsmalllogs are preserved asJSON. This modestobservedgain andunresolvedmemorydifference should be reviewed together before adoption.
