# Snapshot reset/defer rehome — complete

Selected generic reset sequence and scoped defer controls now belong to shared owner371; native snapshot adapters remain in native041. Eight selected original hunks moved through ordinary Git fixup/autosquash and native rebase; no new logical owner or fixup remains.

Current source: shared `e36552065f5a0800619cb327bb8f62fefd099daf` (376), native `5dcb81d975a654f8c36fa6e36f3605fa217fd084` (153). Complete final tree is exactly `f58bb4951d4431ab30f1b0363c7368f6969a5cb4`, matching the preserved original529 source.

Shared normal build passed375 actions; snapshot_rcu_tests7 cases/18,516 assertions and mempool_tests24 cases/2,225 assertions passed. All529 source deltas and all529 actual generated mailboxes replayed to every expected intermediate tree. Native1203/1203 full-gate evidence is reused from the identical complete f58 source tree; this is not a newly compiled native binary claim. Current build cache contains the shared endpoint.

SOURCE-HUNK-SELECTION and SOURCE-OWNER-MAPPING account for all529 owners: only shared371 and native041 change hunk placement, in txmempool.cpp/h. Native HasPendingOverlayChanges removal remains native because shared callers still need it. Original backups and prior bundles remain. The verified incremental bundle requires ancestor a95e17daf4d64c9c9c0f91028a8418ec5a23bb12, available in the previously committed source bundle.

Pool lifecycle remains deferred: its manager originates in native059 and is absent from the shared prefix; moving native134 alone would produce an invalid prefix. No benchmark data or root-owned files were changed.
