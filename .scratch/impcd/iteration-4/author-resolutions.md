# Author resolutions after iteration 4

Applied the operator's F5 and F1 messages in order, verbatim in the maintained input bundle. These are author amendments after the capped review, not independently voted repairs. Historical findings/revisions/ledgers remain unchanged. `author-resolutions.json` records the complete messages, new digest and exact stable-claim changes from ledger-accepted.json; the spec/test files are regenerated from that ledger plus these operations.

- F5: withdrawn >=99%-within25-round acceptance condition. Preserve the1000 fixed seeds and other workload counts; fixtures run to a horizon long enough to finish and report freeze-round distributions and any nonfinishing trials. Zero false freezes and zero split freezes remain hard assertions.
- F1: gate_value=c only when the item's previous success side is IN, otherwise0. Both the W snapshot mean and outsider comparison use gate_value. Other state/gate rules remain unchanged. The old nonpreferred-streak witness now contributes0 and cannot enter frozen W; after twelve IN successes it is FINAL-in and can enter. The prior fix of deleting the false implication alone is superseded.

Input prefix48,180bytes remains unchanged with SHA256 e6ab26b85fe03c3c0a327b21bb5d2da7fc9c38f9a2aee178a0d584f42b1abd1d. Intermediate digest after F5:9153f677b2680aaa309704b91828b53c3cbd0f1b20d8f0c2001b4e0b978df823. Final digest after F1:fb84e15abe521460cd55f65f693835b8047be070075191729fe07df0128e9d96.

Both iteration-4 high-severity findings are now author-resolved. The explicit request to continue authorizes resumed IMPCD iterations after the prior cap; it supersedes the earlier F5 STOP instruction. No independent convergence or implementation conformance is inferred from applying these amendments. No frozen source, harness, oracle, manifest, canonical parent specification or simulator was changed or run.
