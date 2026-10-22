# Reconnect failure: retained evidence and separate count-one defect

Tested full union cf50cd5ef24561806eac03c665b79fc2e7edf6c7/treee0ac4536b7a1bec10ad4b244d7a699287a60f681 failed exact recovery at10000/10000/5711 after120s. The valid owner266 count-direction and window-key lifetime repairs did not complete coverage. Ordinary throughput is a separate N1 gate; no further build or network run was started by this lane.

## Retained timing evidence

Run analyze_retained.py against benchmark-results/20261021/reconciliation-combined-native-v1/reconnect. retained-analysis.json contains input hashes, counts and exact times. This is an offline audit, not another simulation or native run.

Node2's first reconnected peer appeared at05:41:57.157525Z. All4289 missing identities were admitted on source0 between05:41:25.849450 and05:41:55.743329, and on source1 between05:41:25.860109 and05:41:56.895305. At that first reconnect,346 of the eventually missing identities were already30s old on source0 and333 on source1. Isolation's5000-transaction injection itself spanned about30s. The source's recently-admitted selection therefore excluded some still-live transactions before reconnection even began.

The last receiver admission was05:42:27.217748Z,30.128416s after source1's last admission. Last inventory change was29.969s after the reconnect gate began. Bucket traffic continued until05:42:56, then summaries continued through the120s deadline without new bodies. This aligns with source-window expiration followed by receiver-window expiration. It is not proof that every missing transaction was caused by age alone;1741 missing IDs are inside the origin's lowest4096, and cap plus differing local admission times affect the represented membership.

The script also replays the three generic message types against the current32/s policy and reports thousands of predicted excess frames. These are explicitly modeled drop counts, not actual native handler counters; existing logs do not capture roots, buckets, exact requests or handler outcome counters. Any targeted instrumentation must record those details before attributing losses precisely.

## A second deterministic correctness defect

A top-level bucket count difference+1 and its single XOR syndrome do not establish a one-element symmetric difference. Two local identities versus three distinct remote identities in the same bucket produce a count+1, but the XOR can name no remote transaction. The old code requests this synthetic ID and skips bucket drilldown. Empty resolution emits no body and does not escalate the bucket. Repeated stable summaries can therefore repeat the same unresolvable hint indefinitely, even before the30s expiry.

Source-only diagnostic eec29641 originally exposed this inside the relay fixture. Final candidate fb85253b75caa99aa9190e98dfd09e02663c2604/treeff8fd446c46b7392cde40e8bc16283afbc6e1b03 extracts a standalone generic regression, root_count_one_xor_requires_bucket_proof. It proves the seeded count3-versus2 setup and that the XOR is not remotely held, then requires bucket5 recovery. One desired assertion is predicted to fail under old production; no native result is claimed yet.

The repair removes the unproven positive shortcut and uses the existing three-syndrome subbucket protocol for true singletons as well as larger differences. The existing all-scopes lifecycle fixture still resolves all three missing bodies, now deriving the genuine single ID from its subbucket. No wire/state/cap/rate change is introduced. The negative local-extra optimization still requires exact subset-root authentication from the separately validated owner266 repair.

Causal owner is global14 afb04f500a95b9d1807300d5c79bb7e54c2619bc, the original shared Merklix engine. Astra and its independent reviewer source-released this correction; final pin personally rechecked by Astra. Pure owner14 transform is idempotent across509 prefixes. Applying it before/after the owner266 transform produces identical final source across257 overlapping prefixes, exactly matching the final candidate. This is source composition proof only; N1 owns the eventual matched focused gate after the ordinary benchmark drains.

## Remaining coverage requirement

The exact tested source still selects PinAdmittedSince(now-30s,now-margin), then caps eligible membership at4096. Fixing count-one hints cannot supply historical/live transactions that are absent from all summaries. Arbitrary rotating subsets under an unchanged moving context do not provide authenticated full-set coverage. No blind cap increase, whole-pool performance claim or immutable epoch architecture is included here. A baseline repair must explicitly address old/live membership discovery and bound continuation, while preserving context ownership and the existing receive budgets.

Further source boundary: tested cf50 net_processing.cpp4136 calls PruneWindow(now-2*window), physically removing admission records after60s while current epoch identity/short-ID lookup retains live members. Merely widening the query lower bound later cannot recover records already pruned; old-body availability and membership discovery need separate treatment. The source-only age-probe.cpp component diagnostic checks selection loss while retaining actual mempool membership and explicit body resolution. It is deliberately temporary evidence, not a permanent requirement to exclude old live bodies.

## Native count-one gate result

N1 actually built control32eed: normal10 actions PASS8.60s; new standalone root case failed exactly the one desired recovery assertion, with nine setup checks passing. Candidate5c1b3e normal12 actions PASS5.66s and new case10/10 PASS. The subsequent all-scopes case stopped at four stale metric expectations, with57 functional/other assertions passing; the changed path now uses two bucket messages per scope and records no directly decoded summary IDs. The original failure is retained.

Test-only correction42df8ec80192ee2c0f72ef99c9ec6b74c579e409/tree1ab7bb6e22b088f8e7ac3a5dc09392319f2f0ae4 updates exact counters (bucket rounds8, summary histogram sum/count0, bucket histogram sum12). Metrics producers/rendering were inspected: only positive missing-ID observations are recorded, while rendering emits zero-valued histogram series. Functional checks were retained. N1 finalsource76d9/tree6fb built normal10 actions PASS7.85s; allscopes61/61, balanced35/35, GF64676 and adversarial49 assertions PASS. No extra production change was made. All owned processes drained. This validates the narrow count-one repair, not the old/live full-set recovery baseline.

The updated pure owner14 adapter verifies all509 original affected prefixes and exact final42df source. Its metric adjustment applies only once the real metric helper exists, so early prefixes do not import future APIs. Owner14/owner266 transforms remain order-independent over257 overlapping prefixes. Manifest identity is global14, stable_contract_id11, canonical_id split-11 (originalecash/010); do not confuse global position14 with stable contract14.
