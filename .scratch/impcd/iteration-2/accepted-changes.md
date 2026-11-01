# Iteration 2 — applied operator instructions

Edited `.scratch/oneshot/SPEC-PROPOSED.md` and `TESTS-PROPOSED.md` in place, as finally confirmed by the operator. No relocation or duplicate proposal was made.

## Input maintenance

Appended the complete answers message verbatim under `ANSWERS TO Q1–Q12`, then appended both partial-voting messages verbatim in arrival order as separately titled final sections. Existing accepted-review and final quorum-amendment sections were preserved. Intermediate digest after the answers: `46326c7029bf0886cee068ecfdf9a7abac20a13371adb2359e89fd0fb22bef30`.

Current whole-bundle SHA256: **`b3163bd3a4e3fbfcfacf0817127844b836f5b12a48b83ea0bf3fe947c7e9753c`**. Both regenerated drafts pin it. The bundle is now included in Git with the review round. Every future operator instruction changing the specification must be appended there verbatim as a new titled final section before application, with a new digest recorded.

## Applied contract decisions

1. Plain Snowball full-sample quorum: K=min(D,ceil(D/4)), alpha=ceil(((1+beta_adv)/2)*K). Silent/late/invalid/abstaining peers never reduce alpha. Remove hypotheses, likelihood calculation, the match-rate estimator and the D-derived threshold table.
2. beta_c=Btx from the existing epsilon-derived target, equal to 12 at epsilon=1e-9 and independent of D. Nonfinal no-success rounds reset c to zero; preference/side counts change only on a success. FINAL is lifetime-immutable.
3. Gate once at round end after item updates: one pre-entry/pre-exit W mean, empty mean zero, simultaneous membership changes.
4. One M+P capture of admitted raw IDs/incarnations/candidate bits plus round-start Pending lifetimes. Post-capture items get no votes. Matching Pending admission transfers the entire state, including FINAL-out; fresh ordinary admission initializes IN with zero counts.
5. wanted is only a description for votes. The responder fetches positives through ordinary FetchBody, just as the poller fetches missing. No special host-send action or receiver token protocol. Deduplicate concurrent operations; preserve alternate-donor retry and T10.
6. REPLY is a prefix and has no mode/basis_size. Recomputed conservative headers are REPLY=100, POLL=116, DIFF=109. Reconcile the usable prefix cap with both byte limits and the existing symbol-index bound. Generator cap stays numerically 74894. Make the existing DIFF assertion's dual capture-membership/exclusion consistency explicit.
7. Freeze iff nonempty W is entirely FINAL-in, or R union Pending is empty. Empty W with nonempty raw/Pending support does not freeze. Empty-state freezing is allowed even with no peers. No root accumulator or empty-set delay is introduced.
8. Apply both later partial-vote overrides: for captured eligible items, absent/excluded=>NO; guarded zero-after-peel scheduled index>=1=>YES; otherwise abstain. NO takes precedence. The guard uses CURRENT Pending, not just capture-time Pending. The later “proven shared” wording uses the preceding precise witness definition; no instruction explicitly removes that guard. The accepted yes-lean remains a simulation measurement obligation.

The current-Pending guard can change while Ref does not. Two compact masks preserve the necessary peel outputs until round end without a second cell array or evidence-only peel: one bit per received zero cell and one per captured decoded-absent item. Their exact byte bounds are charged. This supplies the bounded representation required by the accepted partial policy without reopening it.

## Regression requirements

Regenerated the current test table for fixed quorum/constant thresholds, no-success resets, strict overtaking, immutable FINAL, captured lifetimes, transferred FINAL-out, gate simultaneity, both empty-set branches, ordinary bidirectional fetching, new wire grammar, guard/current-Pending behavior, bounded masks and one observation per peer/item. Preserve all 104 original acceptance-case inventory rows and prescribed coding/network workloads as appropriate historical coverage obligations. Remove superseded active sign-classifier/blanket-partial-abstention tests.

31 independent arithmetic/transition/document checks pass. These do not claim compiled or executed node acceptance. Production implementation and frozen artifact migration remain outside this regeneration; no hashes were rebaselined to fit an implementation.

## Still open and termination

Q1–Q12 are closed. **Q13 remains:** beta_adv=0 with an even sample permits simultaneous IN/OUT quorums. No tie resolution is invented. See `findings.md` and `minority-report.md`.

Commit this second review round and STOP. Do not start another iteration until the specification changes.
