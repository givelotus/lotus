# Corrected527 vs528: loaded RPC reads during500k individual writes

Onefreshcaseperendpoint, no sampler; bothPASS exact500016uniqueTxIdsets onall3.800warmup doesNOTapplyhere: individualmode has16untimedwarmup plus500000timed. Twelvepersistentreaders eachalternategetmempoolinfo/getblockchaininfo; latencyunitisTWOsequentialRPCs, notindividualcall. Eightindividualsendrawtransaction writers; funding/signing/startup/pilot excluded. Onehostfullscope1/noAVA/highbandwidth/whitelist. NotmaxdaemonTPS orblockconfirmation.

| Endpoint |500k write seconds | allpeer seconds | Read RPC/s | Pair p50 ms | p95 ms | p99 ms |
|---|---:|---:|---:|---:|---:|---:|
|527|100.301159|100.438027|7952.15|2.83|5.34|6.75|
|528|100.628700|100.824688|7954.15|2.83|5.38|6.79|

Result: nearparity inthissinglepair; no statistical/certifiedgainclaim. These areloadedindividualwrites, notunloadedindividualthroughput orordinaryJSONarrays50. ClientJSON/GIL/schedulingareincluded, sodo notattributeallwalltime todaemonCPU. Wholecaseprofile exactENDPOINTS/source/binary/cache/gates arecopiedalongside; no oldredgate/sourceONtimings substituted. Fullhistograms retained inmachineRESULTS/percasemetrics, overflowcensoring preserved. Bothownedgroupsdrained beforededicatedbatchphase.
