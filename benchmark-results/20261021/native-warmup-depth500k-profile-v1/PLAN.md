# Prepared only: warmup depth profile and post-ingestion observation

Do not execute until root/N1 explicitly transfers the runtime window after the full-scope compiler drains.

One current candidate run: source82cceea3/treec2ad1f, validated preservedd24846e8 daemon/cache3c24. Same500800 unique207B fee10000 fixture,800warm/500000timed ordinary8writers/arrays50. Existing outer driver samples ONLY ownednode0 at completed50k/250k/450k,1ms/1second; actual sample lifetimes must overlap ingestion GO as in the prior profile. Timed ingestion core is unchanged.

After ingestion ends, keep the same three nodes alive and take bounded read-only observations at target0/5/15/30seconds: per-node getmempoolinfo count/usage and per-processRSS. Record actual query start/end offsets, so scheduling/RPC delays remain visible. Do not submit additional transactions, mine, force inventories or require peer convergence; this window may include natural relay work and is not guaranteed quiescence. No observed sleep/poll time is included in ingestion elapsed. Emit/persist every completed observation so a later error retains earlier evidence.

Existing getmemoryinfo RPC reports only locked-wallet-memory statistics, not jemalloc allocated/live/resident; Darwin mallocinfo is unavailable. No daemon/API changes are made to obtain allocator statistics.

Same12GiB ownedPG,free6GiB,criticalpressure4,newglobalswap4GiB,1200s guards. Existing generator remains streamed/mmap209334400B+4006400index, no huge rawJSON allocation. Preparation-only wrapper check passed without starting any daemon. New optional observation helper is tested with mock clocks/clients for absolute deadlines, read-only RPC methods, differing peer counts, and prior-row preservation on error; all27 existing/scoped ingestion tests pass in0.102s. Tooling commit49d72417; no benchmark execution or new performance claim.

Exact runnable command is in execution-plan.json and executed by run.py only after a lease. PREPARE-CHECK.json records the no-daemon source/adaptation check. The requested inspection is whether first signature work leaves rpcadmit, what serialized work remains, and whether memory tracks peer progress or persists during the bounded idle-input window.
