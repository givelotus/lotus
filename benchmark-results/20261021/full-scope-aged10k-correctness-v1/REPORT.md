# Aged full-scope native recovery: PASS

The actual three-node gate **passed** on source `5fa8d38edca2c70c34d9c161817355e767cce260` / tree `c787f2c88d43b2a57379ed1060003b440a5c66f2`, preserved daemon `c6e205554c2a04c16203c01c0b116023a56638077c5a24688caa84f9209553d0`, samejemallocON/cache3c24 profile. All processes are drained (session39194 exit0; owned group15477 absent).

| Phase | Node0 | Node1 | Node2 |
|---|---:|---:|---:|
| Initial confirmed funding |0|0|0|
| First5000 accepted and propagated |5000|5000|5000|
| Isolatednode2,5000more submitted |10000|10000|5000|
| After64.003s real aging, still isolated |10000|10000|5000|
| Normal reconnect, exact recovery |10000|10000|10000|

Last-new-transaction source admission wall age was **65.161s** before reconnect, beyond the old30s live window. Exactall3sets converged **81.747s** after reconnect within the predeclared180s deadline. Final sortedTxId digest is `3c2d707f41b1628f122ce5cd8469c7f9e9a92e619d762343e74c1694330deb7f` on allthree. Every localrawbody was then fetched by read-onlyRPC and byte-compared with its prepared body:10000exactmatches pernode. Existing nativeframework identities yield matching sortedTxHash digest `9a96897cf13e17c853f984db268e6899881e441958c44d9e12776457796d28f4`. These local reads happened after convergence and did not initiate recovery traffic.

Actual receivedsendinvshort flags are11 on both current peers of each node, containingRECONbit1 andFULL_MEMPOOLbit3. Avalanche was disabled, service/proof counters checked at snapshots, realclockaging used (`-mocktime=0`), and no manualBIP35/forcedinventory/injectedP2Pbodies/proofs were used. Receivernode2's scope-specificManager events show verified remote10000-body snapshots and admissionfinished unresolved0. Log events alone were not accepted as coverage: exactIDs and bodybytes were checked independently. No rawwirecount or minimalnetwork-transfer claim is made; duplicate remote snapshots are visible in logs.

Wholecase **198.224s**, peak observed owned-groupRSS **0.883GiB**. This is a functional correctness test with debug output and repeated mempool consistency checks, **not a TPS benchmark**. Independent108B nativeOP_TRUE spends are tested; cross-prefixparent/child dependencies, mixedversions, loss/WAN,500k recovery and tipchange duringfetch are not established by this gate. The owner reports a separate focusedunit covers compatibletip-extension context.

Attempt1 (parentdirectory rawRESULT/gate.log/data stderr) stopped before daemon initialization because the derivedold scheduler test passed unsupportedtxrecontarget/margin flags. It is preserved as **harnessstartup failure, no protocolresult**. Root authorized the corrected prelaunch retry: removeonlythoseunusedflags and explicitlyenableexistingtxreconfull=1. Exactc6e205 help-debug validates all actualstartupflags. Source, binary, age/coverage/body assertions and deadlines were unchanged. ActualPASS is attempt2 only; no failed result is relabeled.

Evidence: attempt2/evidence.json; actualcommand/source/binary/config/script pins in attempt2/execution-plan.json; PGresource samples in attempt2/RESULT.json. CAPTURE-EVENTS.json retains actualcapturecount/chargedbytes/copy-lock durations, RAW-LOG-HASHES.json pins retainedrawlogs (large datadirs excluded fromGit). TxHashdigest rule is SHA256 of sortedlowercase nativeTxHashes, each followed bynewline; it is a diagnosticdigest, not a consensusroot. No further runtime was needed to seal this report.
