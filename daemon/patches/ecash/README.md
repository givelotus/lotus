# Experimental ecash candidates

Pinned base: Bitcoin ABC `252182e957120652960c1f88ec96515c448b1204`. Default setup applies no patches. These are opt-in review material, not a maintained release target. See [the support audit](../../docs/support-matrix.md).

| File | Actual change | Status |
|---|---|---|
| `01-nlogn-block-construction.patch` | Corrected custom dependency snapshot and highest-feerate ready heap, with native regressions | Single replacement diff retains the new assembler and fixes stale fees/resources and repeated DAG expansion. Expected O(n + m + n log n), no claimed speedup over modern ABC. Native pinned builds/miner/full C++ checks pass; old payload failures are historical. See [corrected evidence](../../docs/ecash01-corrected-snapshot-assembler.md). |
| `02-remove-chaintx-limit.patch` | Adds a 100-entry `addUnchecked` container test | Fails pinned-base test compilation (`SigOpCount` is not a helper method). Does not remove any policy check, exercise transaction admission, or establish relay/mining acceptance. Independent of 01. |
| `03-mempool-cleanup.patch` | Comment-only historical no-op | Excluded from executable series; `git apply` rejects a file with no diff. |
| `04-prune-finalized-mempool-ancestors.patch` | Prunes already-finalized ancestors in `CTxMemPool::setAvalancheFinalized` (`CalculateMemPoolAncestors`) and adds `setAvalancheFinalized_chained_txs` regression test | Independently verified on declared `8c67fe1e85` and current `1fb7db17c1`: daemon/CLI/native builds, full `check-bitcoin`, 64 processor cases and isolated transaction-finalization regtest pass. Does not apply to the older default `252182e957` pin. See [exact evidence](../../docs/ecash-independent-verification.md); no performance benchmark or Chronik claim. |
| `10-nng-interface.patch` | Comment-only placeholder | Unimplemented; not selectable. |
| `11-remove-zeromq.patch` | Comment-only placeholder | Unimplemented source deletion; disabling the existing CMake feature is already possible. |

Apply/build/test results are separate evidence. Do not describe these candidates as upstream-ready until focused mining, policy, reorg, resource-limit, and performance checks pass. No candidate changes are required to enable upstream Chronik on an ABC-derived daemon.
