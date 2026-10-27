# Snowstorm technical IMPCD — iteration 2

This pass reviews the changed concept after the operator's quorum amendment, answers to Q1–Q12, and two successive partial-voting overrides. Reviewer: Codex, exercising the eleven required technical perspectives. Correctness is decided by counterexample, not a weighted vote. Weight remains severity × confidence; no structural premiums or COI weighting applies.

## Authoritative input and scope

The maintained bundle is `.scratch/inputs/SNOWSTORM-SPEC-INPUTS.md`. It already contained the accepted-review and final quorum-amendment sections when this pass appended the requested messages. Their existing text was preserved. The complete current bundle was read in order; later sections override earlier ones.

- After verbatim `ANSWERS TO Q1–Q12`: SHA256 `46326c7029bf0886cee068ecfdf9a7abac20a13371adb2359e89fd0fb22bef30`.
- After both verbatim partial-voting overrides, in order: SHA256 `b3163bd3a4e3fbfcfacf0817127844b836f5b12a48b83ea0bf3fe947c7e9753c`, 46,566 bytes / 422 lines.
- Downloaded quorum amendment: `/Users/shammah/Downloads/ASTRA-AMENDMENT-SNOWBALL-ROUNDS.md`, SHA256 `1ccd604a4adfe56ed33b6016a4e9ce05e58b58dabc3f7fac240fd4d91942c146`.
- Previous reviewed spec: `ee334454711106d48f442f588f13f0da4d10df0d9042d10a7673380ad58e3078`, committed in `dc8ef17555`.

The operator confirmed `.scratch/oneshot/SPEC-PROPOSED.md` is the spec and directed continued editing there. No files were relocated, no duplicate proposal was created, and the frozen parent marker/source contract was not changed. Future operator instructions changing the spec are appended verbatim to this same bundle before application, with a fresh whole-file digest.

## Fresh technical-perspective feedback

This is a new pass on the changed rules, not repeated votes on iteration 1. Scores concern each role's present principal concern. All applied design choices came from the operator, so no >60% design-preference ballot was needed.

| Perspective | Feedback | Severity | Confidence | Weight | Stance |
|---|---|---|---|---|---|
| Coding theorist | Retain the accepted guarded zero-cell definition exactly, including index>=1, current Pending and negative priority. | 6 | 9 | 54 | Apply settled rule |
| IBLT researcher | Dense fallback and removed fields require explicit header, byte and index-domain bounds; both must hold. | 6 | 10 | 60 | Bounds corrected |
| Consensus researcher | Fixed sample quorums remove answerer normalization; the zero-adversary half-quorum boundary still permits two successes. | 8 | 10 | 80 | Q13 remains |
| P2P developer | Ordinary FetchBody in both directions closes the invented send/receive lifecycle; retain existing binding/retry semantics. | 5 | 10 | 50 | Q4/Q5 closed |
| Red-team attacker | Preserve the accepted partial-vote policy and measurement obligation; test the actual full-K quorum without shrinking it for abstainers. | 8 | 10 | 80 | Q13 remains; no partial-policy reopening |
| Formal-methods reviewer | Simultaneous gate and nonvacuous freeze are now specified; both-side success at beta_adv=0 has no transition. | 8 | 10 | 80 | Q13 remains |
| C++ implementer | Immutable FINAL and constant beta_c remove threshold migration; bounded masks avoid a second retained cell array. | 6 | 9 | 54 | State/bounds specified |
| Test engineer | Replace old sign/streak-abstention cases with fixed-quorum and no-success-reset cases; retain the dual-success counterexample. | 8 | 10 | 80 | Q13 remains |
| Network engineer | Wanted now uses the existing modeled body service; retain the grid, balancing adversary and printed validation latency. | 5 | 9 | 45 | Measurement scope retained |
| Minimalist | Remove hypotheses, match-rate estimator, redundant reply fields and special body actions; add no substitute scoring mechanism. | 4 | 10 | 40 | Supports deletions |
| Skeptical paper reviewer | Distinguish checked constants/transitions from executed node agreement or a security theorem. | 6 | 9 | 54 | Evidence scoped |

## Findings, ordered by severity × confidence

### F2-01 — Simultaneous quorums at the allowed zero-adversary boundary

**Severity 8; confidence 10; weight 80; major; OPEN Q13.**

Exact §1 text: “Config requires finite 0<=beta_max<1/3”. Exact current §8 rule: “alpha=ceil(((1+beta_adv)/2)*K)” and “A round succeeds for IN if yes>=alpha, succeeds for OUT if no>=alpha”.

**Concrete scenario:** D=5 gives K=2. At allowed beta_adv=0, alpha=1. One eligible yes and one eligible no satisfy both success predicates. The item has one preference/counter/streak transition per round; the rule does not select a single side or define a no-success tie. For the reference beta_adv=0.2 the problem does not occur, but that does not remove the allowed boundary.

**Smallest fix:** the author must select an explicit both-quorums rule or deliberately amend the threshold/domain. No implicit IN-first priority, strict-majority replacement or prohibition of zero adversary fraction was inserted. This does not reopen the accepted partial-voting policy.

**Required test:** `T13_zero_adversary_dual_quorum_boundary`, distinct from the passing reference constant/quorum tests.

### F2-02 — Removed REPLY fields require a new conservative header and usable cap

**Severity 6; confidence 10; weight 60; corrected.**

Q6: “remove mode and basis_size from REPLY. The fallback is always a prefix [0, m); recompute the header and cap bounds.”

**Scenario:** removing one byte and one u64 reduces H_reply from 109 to 100; retaining the old shape or allowing prefix lengths past the schedule's maximum index gives incompatible wire/cap behavior. M=1 previously allowed a byte-only cap of 74894 despite maximum index 4160.

**Smallest fix applied:** H_reply=100, H_poll=116, H_diff=109. Shared usable cap is the minimum of the two byte caps and max_symbol_index+1. The no-exclusion generator cap becomes floor((2MiB−100)/28), still numerically 74894. No new tuning parameter or schedule law was added. Prefix bounds were checked at M=1,2,128 and the maximum 262112.

### F2-03 — DIFF internal consistency has a cheap dual membership check

**Severity 6; confidence 10; weight 60; corrected from iteration-1 F10.**

Current §6.1 requires “missing absence from captured raw R” and exclusions inside the reconstructed raw assertion.

**Concrete scenario preserved:** captured R={x}, missing={x}, wanted={}, declared set_size=2 passes the old count equation yet reconstructs only one ID. This is an internally impossible assertion, independently checkable from the capture.

**Smallest fix applied:** reject overlapping missing/captured-raw IDs and exclusions outside the asserted reconstructed raw set before effects. This adds no authentication claim, remote history or new state.

### F2-04 — Guarded partial evidence must survive the discarded working buffer

**Severity 6; confidence 9; weight 54; representation specified.**

Existing §6.2 requires one invariant residual, one transient peel buffer and no second raw-cell copy. The accepted partial override needs zero-after-peel and decoded-absent evidence at round end.

**Concrete scenario:** the first attempt stalls, the transient buffer is discarded, and Pending-to-R admission preserves Ref membership but changes the CURRENT Pending guard. Reusing a precomputed yes bit alone would preserve a stale guard result; retaining a second cell array would violate the storage contract.

**Smallest representation applied:** a zero-cell bitmap over received indices and decoded-absent bitmap over captured items, overwritten by each real attempt. At round end evaluate the guard using current Pending, without an extra peel. Bound/charge the two masks explicitly and release them with the reply. Full rescue replaces the classification. This records the implementation consequence of the accepted policy; its yes-lean and security rationale are not reopened.

## Disposition of earlier questions

All Q1–Q12 are closed by the operator. In particular: full-K quorum, constant beta_c, no-success reset, simultaneous prechange mean, M+P capture, no post-capture votes, whole-state Pending transfer, ordinary body fetch, concurrent deduplication with retries, immutable FINAL and the explicit nonempty/empty freeze predicate are now normative. The partial-voting overrides supersede the earlier blanket-abstention correction; the second override's “proven shared” retains the precise guard provided immediately before it.

No obsolete D-derived threshold, likelihood-sign classifier, prior match-rate estimator, special wanted delivery action or partial-vote prohibition remains active. Iteration-1 reports remain historical records rather than being rewritten to imply their original rule was different.

## Evidence and stop condition

PASS: 31 independent arithmetic, transition and document checks, including five exact quorum rows, 12-success finality, no-success reset, strict count overtaking, immutable FINAL, simultaneous gate comparison, nonvacuous freeze, wire header/cap arithmetic, capture bounds, partial guard and preservation of 104 historical acceptance inventory rows. These are checks of the proposed rules and text; no production Snowstorm acceptance binary or simulator was run.

No source/header/harness/oracle/manifest, parent normative marker, rendered site, source pin or production node was changed. Final hashes and patch check are recorded in `CONFORMANCE.md` under the existing oneshot directory.

**STOP after iteration 2:** a new major counterexample remains (Q13), so the no-new-major convergence condition is not met. The operator requests regeneration followed by STOP. This is 2 of at most 4 iterations; spec growth is below 20% and has decreased from iteration 1. No third panel is run on the unchanged draft.
