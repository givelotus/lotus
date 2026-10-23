Recovery deadline wake candidate — 2026-10-22

Candidate source 2a36522dc27ba4832ccfa48264291820e960d12c
Tree cbc28b7066d27c2694ea0d9f7a1084ab174d9cf7
Parent canonical528 922eb4a7f9d8ec8af7a5e64d521454c572ece937
Earliest logical owner global525/native151 b94109e842.
This is a tested fixup candidate, not yet folded into maintained mailboxes.

Cause: request continuation waited for the message handler idle100ms
heartbeat, turning125ms pacing into roughly210ms. Admission also had no explicit continuation wake after its64-body
slice. The measured admission cost is nevertheless dominated by regtest
diagnostic invariant scans, as established below.
The existing relay scheduler now consumes a bounded atomic earliest
continuation deadline. No per-peer timers or busy polling are added.
Inflight requests schedule only their5s timeout; admission yields after
64 examined bodies and requests the next useful scheduler turn.
Exact TxHash bodies already in the pool skip redundant admission;
unknown bodies retain ProcessShortTxResponse and normal validation.

Wire delta: NONE.125ms exchange spacing,one inflight request,page64,
frame/memory limits,32msg incoming shared rate limit,authenticated
coverage,ownership checks,and transaction validation remain unchanged.
The existing272 request cycles still imply about34s of transport pacing;
this candidate does not claim to eliminate that protocol floor.

Validation: build lotusd/test_bitcoin GREEN; all txrelay_tests GREEN;
full unfiltered1200 native cases GREEN. Existing ownership/corruption/
normal admission assertions retained; new focused deadline assertions
cover inflight timeout,immediate admission continuation,and no pending
continuation after completion. Same allocatorOFF walletOFF ChronikOFF
Release profile as frozen endpoint comparison.

ENDPOINT.json pins immutable copied binary/cache/config. Old527/528
artifacts and all prior timing results are preserved. Source and binary
freeze handed directly to canonical_records_sync for identical aged10k
metrics-enabled recovery comparison. No benchmark result claimed yet.

Measured diagnostic outcome (one before/after pair, exact IDs and bodies PASS):
recovery84.7598 ->59.8871 seconds; capture-to-coverage60.695 ->35.353s.
Admission remained24.694s. This is NOT evidence of remaining heartbeat
sleep: admission-cost.py finds5000 accepted bodies and5000 full-pool
consistency scans after coverage,24.6499s cumulative PreChecks-to-accepted
of24.6898s first-to-last admission span,maximum interaccepted gap19.98ms.
Regtest defaults checkmempool=1; main/testnet defaults0. No consistency
checks have been removed or weakened. Production-profile timing with
checkmempool=0,if separately run,must be labeled a configuration result.

Canonical integration CLOSED (source delivery; no publish/push):
HEAD5286e2c35541feaa4af13d91a227ac5a7c09797b2be
Tree528cbc28b7066d27c2694ea0d9f7a1084ab174d9cf7 equals tested2a tree.
HEAD5270c84378c174a0c06fb182aee16b0533091156bb0
Tree5278840ae0990bdabfd0b902833117702f1f4e7e1c0; direct1187 gatePASS.
Earliest owner525 now07cab06bc810f305bfa0242387b4f7609496e5f2.
Only maintained mailbox151 changed;528 owners remain,feature154 unchanged.
Full528 actual mailbox/intermediate replayPASS;5281200 gate reused solely
by exact source-tree equality,not ancestry or matching test counts.
Verified integrated-source.bundle preserves final commits and tested2a.
No remote push attempted. Existing databases/builds remain accounted for.

Benchmark report: benchmark-results/20261022/fullscope-recovery-latency-diagnosis/REPORT.md
SHA256fb0d65650eee4ac87b677a33e04377f6d39f1ddcf4ad8ff4a5b68a0dcead7abd
Check1same-profile recovery84.7598->59.8871s (29.35% less time),exactall3
TxId/rawTxHashPASS. Check0production-profile36.7213s separately,not code gain.
