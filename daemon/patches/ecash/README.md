# Experimental ecash candidates

Pinned base: Bitcoin ABC `252182e957120652960c1f88ec96515c448b1204`. Default setup applies no patches. These are opt-in review material, not a maintained release target. See [the support audit](../../docs/support-matrix.md).

| File | Actual change | Status |
|---|---|---|
| `01-nlogn-block-construction.patch` | Replaces mining transaction selection | Applies and builds at the pinned base, but existing miner tests fail three assertions; not established correct or O(n log n). Shared ancestors are counted repeatedly, DFS has no visited set, and static package statistics become stale as ancestors enter the block. No regression tests accompany this patch. |
| `02-remove-chaintx-limit.patch` | Adds a 100-entry `addUnchecked` container test | Fails pinned-base test compilation (`SigOpCount` is not a helper method). Does not remove any policy check, exercise transaction admission, or establish relay/mining acceptance. Independent of 01. |
| `03-mempool-cleanup.patch` | Comment-only historical no-op | Excluded from executable series; `git apply` rejects a file with no diff. |
| `04-prune-finalized-mempool-ancestors.patch` | Prunes already-finalized ancestors in `CTxMemPool::setAvalancheFinalized` (`CalculateMemPoolAncestors`) and adds `setAvalancheFinalized_chained_txs` regression test | Prepared against upstream Bitcoin ABC `8c67fe1e85a602204a2ce65aa3b643469c2c3a1d`; builds and passes `mempool_tests`, `miner_tests`, `validationinterface_tests`, and `processor_tests`. |
| `10-nng-interface.patch` | Comment-only placeholder | Unimplemented; not selectable. |
| `11-remove-zeromq.patch` | Comment-only placeholder | Unimplemented source deletion; disabling the existing CMake feature is already possible. |

Apply/build/test results are separate evidence. Do not describe these candidates as upstream-ready until focused mining, policy, reorg, resource-limit, and performance checks pass. No candidate changes are required to enable upstream Chronik on an ABC-derived daemon.
