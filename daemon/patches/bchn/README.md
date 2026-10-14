# Experimental bchn candidates

Pinned base: BCHN `v28.0.0` (`0bc23ac4c1365f34ed824e2b07e554ec06a5f5cd`). Default setup applies no patches. These are opt-in review material, not a maintained release target. See [the support audit](../../docs/support-matrix.md).

| File | Actual change | Status |
|---|---|---|
| `01-nlogn-block-construction.patch` | Replaces mining transaction selection | Applies at the pinned base; not established correct or O(n log n). Shared ancestors are counted repeatedly, DFS has no visited set, and static package statistics become stale as ancestors enter the block. No regression tests accompany this patch. |
| `02-remove-chaintx-limit.patch` | Adds a 100-entry `addUnchecked` container test | Does not remove any policy check, exercise transaction admission, or establish relay/mining acceptance. Independent of 01. |
| `03-mempool-cleanup.patch` | Comment-only historical no-op | Excluded from executable series; `git apply` rejects a file with no diff. |
| `10-nng-interface.patch` | Comment-only placeholder | Unimplemented; not selectable. |
| `11-remove-zeromq.patch` | Comment-only placeholder | Unimplemented source deletion; disabling the existing CMake feature is already possible. |

Apply/build/test results are separate evidence. Do not describe these candidates as upstream-ready until focused mining, policy, reorg, resource-limit, and performance checks pass. No candidate changes are required to enable upstream Chronik on an ABC-derived daemon.
