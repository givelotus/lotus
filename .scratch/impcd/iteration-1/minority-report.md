# Iteration 1 minority report

High-severity technical concerns remain visible regardless of support. The named reviewers below are technical perspectives exercised by Codex, not independently recruited people. No correctness concern was dismissed by voting.

## M1 — Small usable samples invalidate the stated threshold calibration

Lead perspectives: distributed-consensus researcher, red-team attacker, skeptical paper reviewer. Severity 9, confidence 10, weight 90. See F03 in `findings.md`.

The full-K reference table is correct. It does not bound errors for the actual item classifier with arbitrary Kx and adaptive M1hat. With D=500, M0=300, M1hat=500 and Kx=1, an IN vote under the null occurs with probability 0.6. Two such independent rounds have probability 0.36; the threshold table's approximately 0.002 per-round tail cannot be substituted. Persistent neighbourhood correlation can further defeat an independence argument. This is not a demonstrated whole-node split-freeze attack and is not presented as one.

The majority of implementation-focused feedback can reasonably accept an operational rule without a calibrated security theorem. That preference cannot turn the table into such a theorem. Preserve Q9 and the calibration limitation until the owner supplies the intended claim or changes the observation/threshold model. Do not reintroduce an SPRT or invent a new threshold as a review workaround.

## M2 — The one-round-prevention goal is not satisfied over the complete stated domain

Lead perspectives: formal-methods/liveness reviewer, C++ implementer. Severity 9, confidence 10, weight 90. See F04/F05.

At D=1024, beta_adv=0.2 and epsilon=1e-9, the prescribed formula gives beta_round=1. Nonempty W with one all-matching round can therefore finalize. Separately, if W is empty, its universal FINAL-in condition is vacuously satisfied. A first OUT vote can also remove the sole nonfinal candidate and make W empty. These are concrete conflicts with an unrestricted no-one-round-freeze requirement. No extra minimum, dummy item, timer or root counter has been added. Q8 and Q12 remain open.

## M3 — Repetition does not by itself repair a persistent graph partition

Lead perspectives: red-team attacker, network/measurement engineer, skeptical paper reviewer. Severity 8, confidence 9, weight 72.

Two stable honest neighbourhoods can repeatedly observe different holder sets. Fresh sampling inside each fixed neighbourhood does not resample the global network. A fixed population can also equivocate, choose reply timing, or withhold bodies. These concerns do not require creating Sybil identities. The revised rationale therefore treats repeated rounds as the selected confidence mechanism, not proof that graph correlation disappears or that Snowball's published analyses transfer to this protocol.

Keep the requested unique-item FINAL-side agreement test and explicit partition, equivocation, selective-response, adaptive-near-threshold, fake-Pending and body-unavailability campaigns. Report disagreement and nontermination without retuning seeds. Sybil/eclipsing identity-population construction remains the declared follow-up-paper problem; fixed-population evidence manipulation remains in scope here.

## Resolved concern retained for provenance

The coding-theory and red-team perspectives objected to zero-cell partial-vote inference. The concrete GF/schedule witness in F02 and the operator's fake-Pending attack rationale remain recorded even though partial item voting was removed. That reversion closes the partial-vote path; it does not claim an injective sketch commitment, authenticated body holdings, or elimination of every full-decode aliasing risk.
