# patches/ecash/ — Clean eCash Upstream Candidates

These patches contain no Lotus-specific code. They are intended as upstream PR candidates
for https://github.com/Bitcoin-ABC/bitcoin-abc (eCash).

## Target Base

bitcoin-abc `252182e957120652960c1f88ec96515c448b1204` (confirmed clean apply).

Patches were ported from the old v0.24.11 target to the current bitcoin-abc HEAD API:
- `src/miner.cpp` → `src/node/miner.cpp`
- `addPackageTxs(int&, int&)` → `addTxs(const CTxMemPool &mempool)`
- `sigOpCount` → `sigChecks`
- `insertion_order` tag replaced by existing `entry_id` topological index
- `AddToBlock` takes `CTxMemPoolEntryRef` not `txiter`

## Patches

| Patch | Description |
|---|---|
| `29-nlogn-block-construction.patch` | O(n log n) block construction replacing the upstream `addTxs`. Uses `entry_id` topological index for snapshot; `CBlockTemplateEntry` gains package-stat fields; legacy O(n²) renamed `accuratelyAddTxs`. Step 1 of 3. |
| `30-remove-chaintx-limit.patch` | Adds regression test `long_chain_accepted`. The ancestor/descendant chain-length limits were already removed in upstream bitcoin-abc before 252182e9; this patch just documents that. Step 2 of 3. |
| `31-mempool-cleanup.patch` | **NO-OP** against 252182e9. All `CTxMemPoolEntry` accounting fields and O(n²) maintenance were already removed upstream. File is a header comment only. Step 3 of 3. |

## Submitting Upstream

Only patch 29 has new content to submit. Patches 30 and 31 are pre-applied in
bitcoin-abc as of 252182e9.

Apply order: 29 → 30 → 31
Verify: `git apply --check patches/ecash/29-nlogn-block-construction.patch`

Patches have been verified clean of Lotus-specific identifiers (XPI, XAddress, OP_LOG,
nTailSubsidy, lotusd, etc.).

## See Also

- `patches/v2/` — same patches as part of the full Lotus v2 series (v2/29-31 still target old API; refresh pending)
- `patches/bchn/` — same patches ported to Bitcoin Cash Node
