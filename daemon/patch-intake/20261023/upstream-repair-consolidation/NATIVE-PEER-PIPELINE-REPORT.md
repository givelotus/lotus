# Native peer pipeline: measurements and unmerged repairs

| Change / workload | Before | After | Status |
|---|---:|---:|---|
| Relay-rank cache; native signed batch200 RPC admission, three alternating pairs | 35,711 tx/s | 46,904 tx/s | Validated shared/native review candidates; pins unchanged |
| Same candidate; one native three-node run, admission | — | 55,675 tx/s | Single trial, not the paired median |
| Same run; exact inventory on all three nodes | — | 19,825 tx/s | Includes verification RPC time; 279,800 timed transactions |
| SHORTTX receiver queue wiring | Serial message-thread admission | Existing bounded admission worker | 1,204 native cases pass; no valid timing yet |
| Native staged signature warming | Native crypto skipped in unlocked phase | Snapshot-only signature cache warming | Initial full gate 1,204/1,205; lock repair rebuilding |

All-peer baseline: `benchmark-results/20261023/native-peer-completion-relay-rank/round-1/signed_batch200_steady-p4-w8-r0/NETWORK-COMPLETION.json`. Admission ended at 5.026s; all sorted TxID digests verified at 14.114s from ingestion start. The 3,200 warmup transactions were synchronized before timing. No block processing or staking finality measured.

Receiver profile: `benchmark-results/20261023/native-peer-catchup-profile/round-1/signed_batch200_steady-p4-w8-r0/peer1.sample.txt`. Of 3,175 message-thread wall samples, 2,735 were in compact-response synchronous admission. All 3,175 admission-worker samples were waiting for queue work. Profiled rates are excluded from throughput results.

Queue prototype: production fixup bd9ec02d9b, native fixture adapter 2d06152a39. The native test admits 768 valid transactions plus a duplicate, saturates the peer FIFO, checks callback return before admission under a pinned chain lock, and checks a following PING completes after queued verdicts. Before: fails 768 != 0. After: 1,559 assertions pass, and all 1,204 native unit cases pass. A guarded network attempt aborted on >4GiB host swap growth and yields no timing.

Staged warming prototype: 1086dc10df, repaired by 64176c73eb. Signature cache entries are advisory, not transaction validity verdicts. Native worker tasks read immutable snapshots only and never fall back to cs_main; the authoritative phase resolves current inputs and validates again. A new test rejects both an invalid signature and a spend whose coin value changes after warming. Initial full gate caught a cs_main lookup before the unlocked phase; repair supplies the live node-owned pool identity through options, with lifetime guaranteed by the caller. Existing lock-behavior assertions are retained.

Preservation: source exported as native-staged-warmup-prototype.mbox and incremental verified native-staged-warmup-prototype.bundle (prerequisite 24e17f59 is in verified fee-precondition-output.bundle). Branch perf/native-staged-warmup-lock-repair-20261023 pushed to givelotus/lotusd. No active pins changed.

Before promotion: full repaired native gate, actual end-to-end timing, retained SHORTTX decoded-body memory accounting review, shared-tier placement/gates and explicit owner folds. The compact response can retain up to one decoded response beyond primary queue accounting; a bounded primary queue alone is not a proof of a global retained-body bound. Larger consolidation inventory and logging ordering remain unfinished.

## Completed alternating comparison

Three alternating before/after pairs, each with four generator processes, eight writers, batch200, one million pre-signed native fixtures, 3,200 synchronized warmup transactions, at least five seconds admission, and three fully validating nodes on one Apple M5 Max/48GiB machine. Same frozen Release flags, no profiler or build during timing.

| Pair | Before admission tx/s | After admission tx/s | Before exact all-peer tx/s | After exact all-peer tx/s |
|---|---:|---:|---:|---:|
| 1 | 52,940 | 51,609 | 18,793 | 22,980 |
| 2 | 51,619 | 51,586 | 20,011 | 24,387 |
| 3 | 53,262 | 51,667 | 20,639 | 25,224 |
| Median | 52,940 | 51,609 | 20,011 | 24,387 |

Admission change **-2.5%**; exact all-peer completion **+21.9%**. This is the combined queue plus native-warming candidate, not attribution to either change alone. The earlier exploratory 42.8K/18.0K single trial is excluded from these medians. No block confirmation/finality measured.

Authoritative dataset: `benchmark-results/20261023/native-peer-pipeline-paired/RESULTS.json`, INPUTS.json, six CONFIG/result/NETWORK-COMPLETION/RESOURCES receipts and logs. Before source24e17f59/treef9e86468; after64176c73/tree4b78888f; exact binary/cache hashes and flags in INPUTS. All three inventories have equal counts and sorted TxID digests in every run. Group18GiB ceiling, host6GiB free/criticalpressure/swap-growth4GiB guards unchanged.

Repaired source full gate: one run failed metrics ring reuse (3 rings vs cap2), all signature-preparation tests passed; 30 isolated ring repetitions and the unchanged complete1205-case repeat passed. Preserve the intermittent failure as an unresolved metrics test interaction, not a clean two-pass claim. Initial1086 lock regression is repaired by64176; original assertion retained.

Adoption remains pending: queue retained-body accounting, proper shared placement and both boundary gates. Logical shared queue owner8ae998 (shared268) follows compact callback introductionecbefdb (shared251), so callback exists at its target. Native expected-pool adapter and signature-only warming belong in1c6f6237. Preserve native fixture ownershipf132a936. Active pins unchanged.
