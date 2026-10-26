# Initial consolidation plan

Requested outcome: fewer complete, reviewable upstream changes; repairs, tests and build wiring belong to the feature that needs them. Keep the existing source, behavior and useful performance work.

1. Freeze the shared/native inputs and all unmerged candidates, refs, trees and dirty work. Preserve verified recovery history.
2. Inventory the 378 shared and 153 native commits. Audit all 286 commits outside the late logging tranche, starting with the 19 provisional repair candidates. Classify additions inside the logging tranche separately from call-site conversion.
3. Map every repair to the first responsible owner. Fold its tests, docs and build dependencies with it. Split mixed commits. Keep independent upstream fixes and meaningful new mechanisms separate.
4. Reorder toward small independent optimizations, logging foundation, asynchronous HTTP, Beast and coroutine completion, then larger storage/allocator/snapshot/admission/reconciliation mechanisms. Move bulk logging conversions last.
5. Execute bounded cohorts on real Git branches in the existing registered checkout. Preserve an old-to-new ownership ledger. Never edit archival patch files.
6. Require exact shared/native endpoint tree equality for pure history changes, relevant prefix builds/tests, clean replay and both tier gates. Keep source behavior repairs and new feature integrations separately identified.
7. Extract small upstream PR branches with prerequisites, tests and concise benchmark evidence. Preserve the detailed historical benchmark identities.
8. Pursue the immediate 100K native processing target using the corrected generator and actual native profiles. Track admission, propagation/convergence, block processing and finality separately; 1M TPS is the longer-term objective.

This draft is subject to the recorded review before execution.
