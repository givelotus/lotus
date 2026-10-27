# IMPCD technical review — iteration 1 accepted changes

Operator: Shammah. Reviewer: Codex using the eleven technical perspectives in `findings.md`. This is one review round, including the operator's amendments received during the round. Correctness findings stand on their counterexamples; no vote authorizes a correctness change.

## Amendment precedence and applied edits

The source bundle is unchanged. Its later sections override its earlier sections; the subsequent live operator instructions below override the bundle. The operator explicitly authorized editing the proposal files **in place** and committing this review round. No parallel proposal copies were made.

1. **Reconstruct DIFF from captured raw R.** In §6.1, use `W_j = ((captured raw R - wanted) union missing) - peer exclusions`. Include locally excluded captured IDs. Add `T13_diff_local_excluded_peer_included_yes`: captured raw R contains x, captured W excludes x, the peer includes x, and its empty-list DIFF supplies an eligible YES for x.
2. **Remove partial-peel item votes.** A reply still undecoded at round end abstains on every item, including exclusions and decoded-negative IDs. A timely valid reply still answers nonmatch for the observed match-rate estimator. A full decode on arrival or rescue supplies at most one observation per eligible peer/item. Partial positives may still start bounded body fetches; that is dissemination, not voting. Remove partial-voting witness/memory requirements. Record correlated abstention and a single adversary's fake-Pending attack on honest replies' zero-cell inference as the reason for the reversion. Sybil resistance remains follow-up-paper work.
3. **Use exact DIFF samples for next-request sizing.** A DIFF-only round uses the normal estimator and can shrink n. Only a no-sample MATCH-only/silent round retains the preceding n. Censored-median and zero-decode doubling triggers are unchanged. Add `T7_diff_only_round_shrinks_request` with an independent quantile fixture whose cost argmin is below the preceding prefix.
4. **Apply the final replacement round-count amendment.** Replace per-item likelihood accumulation with Snowball preference, cumulative in/out counts, capped consecutive count, previous observed side and FINAL. Use the hypergeometric function only to classify one round's sign. Derive the consecutive threshold from exact hypergeometric tails. Remove the separate accumulated root-confidence state and its reset/veto/freeze conditions. MATCH is compact captured item evidence, not separate root evidence. Freeze when W is entirely FINAL-in; later gate entry invalidates that freeze. Keep the preceding observed match rate solely to derive M1hat for the item vote. Keep Broot solely as an intermediate constant deriving Btx and the consecutive threshold.

The temporary finite-magnitude proposal was withdrawn before application. The intermediate instruction to leave item scoring OPEN was superseded by the round-count amendment. The first round-count amendment retained root accumulation; the final replacement explicitly removes it. The regenerated documents follow the replacement, not either superseded instruction.

## Exact round-count rule carried into §8

For an eligible item, Kx is its yes-plus-no observation count, including compact MATCH observations, and Yx is its yes count. Kx=0 leaves all state unchanged. Otherwise the round votes IN iff `L(Yx;D,M0,M1hat,Kx)>=0`; infinity determines only the sign. Zero is IN.

Fresh epoch-held/admitted items initialize preference IN; fresh Pending initializes OUT. Both cumulative counts and c start at zero, with no previous vote. Increment this round's side count once; preference changes only if that count strictly overtakes the current preference's count. Same-side observed votes increment c to its cap; a changed side sets c=1. An item is FINAL when c equals the threshold and the vote side equals preference. Pending-to-admitted transfer, post-FINAL behavior and population transitions still require the decisions listed below; these were not invented during regeneration.

For full K, derive y_star using M1tx, compute the maximum of the two exact hypothesis-tail errors, and compute `beta_round=ceil(Btx/-log2(p_error))`. Recompute on D changes at round start. Use unrounded probabilities, not the displayed table values. The symbols beta_adv and beta_round distinguish the adversary fraction from the consecutive threshold.

## Numerical verification actually performed

Independent Python integer binomial sums and exact rational probabilities reproduce:

| D | K | M0 | M1tx | y_star | Exact-calculation p_error, displayed | beta_round |
|---|---|---|---|---|---|---|
| 16 | 4 | 9 | 13 | 3 | 0.3923076923076923 | 9 |
| 32 | 8 | 19 | 26 | 6 | 0.2706637004078606 | 7 |
| 64 | 16 | 38 | 52 | 12 | 0.13463862983395827 | 5 |
| 128 | 32 | 76 | 103 | 23 | 0.07147798089809947 | 4 |
| 500 | 125 | 300 | 400 | 89 | 0.001981301487914584 | 2 |

These match the operator's five display-rounded p values and all exact integer columns. This is arithmetic verification, not a simulator run, a new oracle implementation, or executed node acceptance evidence.

## Test-plan regeneration

The current replacement table now covers the five threshold rows, first-round nonfinality in those reference configurations, consecutive runs, strict count overtaking/ties, abstention, the c-mean gate, unique-item FINAL-side agreement, MATCH/full-observation equivalence, partial-reply abstention, full rescue deduplication, lifetime transfer and removal of root accumulation. Preserve all 104 original frozen-case names as a clearly historical inventory. Consolidate the active plan instead of stacking contradictory policy tables. Legacy saturation/SPRT tests do not establish the new protocol; applicable primitive arithmetic coverage and all prescribed workloads remain required.

The frozen source contract has **not** been migrated or rehashed. Its older wire/API and state are not claimed to satisfy this proposal. No production implementation, simulator, sizing-table generation, freeze, source pin, deployment or publication was performed.

## Still open for the spec owner

| Question | Required decision |
|---|---|
| Q1 | Empty-W mean, simultaneous gate order and gate evaluation on admission versus round end. Post-freeze gate reopening is now resolved by the operator. |
| Q3 | Capture-time Pending membership and its bound; new/post-capture incarnations; state transfer versus admitted preference initialization. |
| Q4 | wanted body-send action, receiver reservation/callback binding and loss/removal races without a second getdata. |
| Q5 | Interpret first-donor/once as live deduplication versus lifetime retry prohibition; preserve honest-alternate recovery. |
| Q6 | Confirm retained fallback mode/basis correlation fields or choose a new grammar with recomputed bounds. |
| Q8 | p_error=0 at D=1; beta_round=1 at supported D=1024; numerical ceiling boundaries and the scope of the no-one-round claim. |
| Q9 | Full-K/M1tx calibration versus actual Kx/prior M1hat, persistent correlation assumptions, and rate reprojection when D changes. |
| Q10 | Updates after FINAL and changes of threshold with existing c/FINAL state. |
| Q12 | Empty-set/vacuous freeze versus the unconditional no-one-round-freeze statement. |

Q2, Q7 and Q11 are closed by the accepted amendments. Additional small, concrete repairs recommended but not applied are in F08/F10 of `findings.md`: reconcile the cell cap with the symbol-index bound and reject internally impossible DIFF lists.

## Stop

Iteration 1 produces new major findings with concrete scenarios. It does not converge. Stop after this committed regeneration for the spec owner's decisions/application; do not start iteration 2 on an unchanged concept. The 20% growth and four-iteration limits also remain in force.
