# Executable paired527/528 harness — waiting only green endpoint handoff

`run-paired.py` now generates and executes the existing monitored frozen harness serially. It refuses red/unreleased endpoints, checks binary/source/tree/cache/config hashes plus effective matchedOFF/walletOFF/ChronikOFF/O3, writes input provenance beforelaunch, requires500kactualuniqueacceptance and>=5s, exactall3finalcounts+TxIddigests, then failsSTOP on any error. Existing12GiB/free6/critical4/newswap4GiB/1200scase guards and fresh canonicalignoredtempdirs remain. No sampler/compile overlap. No new framework/worktree.

AfteractualGREEN/draintheendpointowner supplies finalizedENDPOINTS.json followingENDPOINTS-TEMPLATE.json (`status=GREEN_FROZEN_ENDPOINTS_EXCLUSIVE_RUNTIME_RELEASED`,green_gate/root_runtime_lease true, finalsource/tree/binary/cache/config hashes). Do notfill pendingvalues witholdredgatedpins. Sourcedefinitions mustremainparked duringrun.

Commands fromrepo root (NOT launchedyet):

```
python3 benchmark-results/20261022/native527-528-matched-plan/run-paired.py --endpoints <actual-green-ENDPOINTS.json> --phase ordinary --ordinary-pairs 4 --output benchmark-results/20261022/native527-528-results/ordinary --total-seconds 3600
python3 benchmark-results/20261022/native527-528-matched-plan/run-paired.py --endpoints <actual-green-ENDPOINTS.json> --phase reads --output benchmark-results/20261022/native527-528-results/reads --total-seconds 1800
python3 benchmark-results/20261022/native527-528-matched-plan/run-paired.py --endpoints <actual-green-ENDPOINTS.json> --phase batch --output benchmark-results/20261022/native527-528-results/batch --total-seconds 1800
python3 benchmark-results/20261022/native527-528-matched-plan/run-paired.py --endpoints <actual-green-ENDPOINTS.json> --phase reconciliation --output benchmark-results/20261022/native527-528-results/reconciliation --total-seconds 1200
```

Ordinaryinitialpair plus3rotatedrepeatpairs:527→528,528→527,527→528,528→527; no automaticretry. Expectedactualsetup+run~60–120s/case,8cases~8–16min; honesthardbound1200s/case and60minmatrixstartbudget. Checkinitialpair resources/result beforeallowingnextcase; firstfailureSTOP. Readsphase onefresh500kperendpoint with12existinggetmempoolinfo+getblockchaininfo readers andindividualsendrawtransaction writers; dedicatedbatchphase onefresh500kperendpoint submitrawtxbatch200. Both~2–4min eachpair conditionalresources. Reconciliationphase existingexactaged10k/noAVA/FULLbit3/bodydigest script,64srealage+up-to180sreconnect,420scase/~4–8minpair. No hiddenBIP35/manualfetch. No timings fromredgate.

`matched_loopback.py` differsfromcopiedhistoricalwrapper only by explicitcurrentfullscope1/noAVA startup (alreadydeclared) and allowing theexistingloadedcase in fixedworkargumentguard. Its steadystate core is unchanged03289714; modes/builders/counts/12readerfunctions stayexisting. Allnewcodepy_compilePASS. Gate script copied exactcorrectedff918 version (removes obsolete schedulerflags,explicitfull1), notthefailedattempt1copy. Driver templates are existingownedresourceguards, no newtimingcore.

Scope: ordinaryJSONarrays50, loadedreads+individualwriters anddedicatedbatch200 aredifferentAPIs; separateallpeercompletion clocks and exactTxIddigestproof. ReconciliationbehaviorhasnotTPSlabel. Microbenchexisting207rows/3repetitions arecomponentonly andalreadyavailable; preservecoldhashregression/synchronousreleasepause, no redundantgrid. CurrentendpointbuildOFFvs historical46dfONtimings arenotpaired.
