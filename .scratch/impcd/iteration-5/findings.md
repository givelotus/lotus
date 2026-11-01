# Iteration 5 — technical review findings

**No new concrete internal finding was established.** Independent revisers gpt-6-astra and gpt-6.1-sol both submitted empty operation lists, no disputes and no unresolved severity>=8 finding. Both applied all eleven technical perspectives plus an author-intent anchor. These were independent model contexts, not eleven recruited experts. Neither saw the other's revision before submission; both reviewed the same amended baseline355ea9be55 and ordered input.

## Prior major findings resolved by the author

F1, previously severity8/confidence10: §8 S0718–S0719 now use gate_value=c iff previous success IN, otherwise0, in both the prechange W mean and outsider comparison. The former witness after IN^11,OUT,IN^11,OUT^13 has dIN22,dOUT14,pIN,c12,previousOUT,FINALfalse and gate0. It cannot enter still-nonempty frozen W with mean12. After twelve IN successes it has dIN34,dOUT14,previousIN,c12,FINALtrue and can enter. T0052/T0067 cover both operands and the failed/successful traces.

Local proof: every immutable FINAL-in member has previousIN,c=beta_c, so a nonempty frozen W has mean gate beta_c. An outsider with pIN reaching that mean must have previousIN,c=beta_c. The transition establishing this conjunction sets FINAL; immutable FINAL cannot subsequently be undone. This applies while W remains nonempty/frozen; removal of its last member invalidates that premise, and the selected empty-W mean0 still applies. No-success resets nonfinal c to0, so retained previousIN history cannot bypass the gate.

Root reproduction:4,930 distinct states through24updates and13,338 checked transitions, plus the exact former witness and twelve-IN continuation. A independently replayed it and checked small-threshold states; B independently explored555,690 transitions through40rounds at beta_c12. These are bounded item-state checks and a local argument, not network agreement or SnowstormNode acceptance.

F5, previously severity8/confidence9: the author's final message explicitly withdraws the obsolete >=99%-within25-round condition. The1000fixed seeds remain. Fixtures run to a horizon long enough to finish and report freeze-round distributions and nonfinishing outcomes; zero false freezes and zero split freezes remain hard assertions. The earlier authority dispute is therefore resolved. No substitute threshold, seed selection or altered protocol is inferred.

## Technical/adversarial coverage

Both reports cover coding theory, IBLT/residual reconciliation, consensus, P2P, red team, liveness/formal state, C++ boundedness, tests, measurement, deletion and skeptical paper review. They explicitly consider fixed-population withholding/delays, equivocal valid MATCH, fake-Pending contamination and unauthenticated but internally valid DIFF input. No Sybil solution or universal safety/liveness theorem is claimed. Current limitations and hard safety test assertions remain visible; hard assertions are requirements yet to be executed.

Prior F2/F3 obsolete root-vote/answerer-normalization wording and F4 zero-probability sizing comparison remain repaired. No settled partial-vote, rescue, capture, immutable-FINAL, body-token or sample rule was reopened without a counterexample. Original workload counts and historical inventory remain intact.

## Disposition

The substantive consensus is empty, disagreement0, no severity>=8 issue open, and the document-level completion criteria are answered. Stop at the runtime fixed point and the author's no-new-major condition. This terminal zero-change step does not count as another accepted nonempty iteration or fabricate locks. No implementation, simulator, generated table, network experiment, human expert or freeze validation contributed new evidence in this round.
