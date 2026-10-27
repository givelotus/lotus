# Iteration 6 — evidence-weighted rounds review

Author's amendment and all subsequent rules10–15, exact Rule10 and C++style instruction are appended verbatim in order. Current input SHA256 fb140f92e8287616f0979c4c1744863d88b0b9e2e9fa85afb3b3860c2515ce5c. Two independent formal revisions: gpt-6-astra and gpt-6.1-sol, each covering the eleven technical roles plus anchor. These are model analyses, not recruited human experts. Neither saw the other's revision before submission. Root compared only after submission; a later shared EW7 counterexample was independently checked by both.

| Finding | Severity | Confidence | Weight | Disposition |
|---|---:|---:|---:|---|
| EW1: opposite infinite contributions | 10 | 10 | 100 | OPEN author arithmetic |
| EW2: FINAL side and retained preference disagree | 9 | 10 | 90 | OPEN author integration |
| EW3: immutable score can never pass signed-score gate | 9 | 9 | 81 | OPEN, conditional on signed gate reading |
| EW4: majority-answer response selection can split FINAL | 9 | 9 | 81 | OPEN safety counterexample |
| EW7: FINAL-out can reenter through negative-mean gate | 8 | 10 | 80 | REPAIRED: gate entrants must be in A |
| EW5: D1 weights always zero | 6 | 10 | 60 | Documented liveness limitation |
| EW6: two stale physical-R operands after rule12 | 6 | 10 | 60 | REPAIRED: use advertised A |

The previous one-fast-voter and n0 defects are CLOSED by explicit operator rules13–15, not counted as unresolved current defects. K crossover is intentionally OPEN for the named experiment; no number selected.

## EW1 — ordinary full-population successes have infinite weights

Section §8, S6_0718: “true H=0 gives e=+infinity ... Opposing infinite contributions are undefined pending the author decision.” This open marker exposes the amendment's mathematical gap rather than selecting arithmetic. The controlling formula is H=P[HG(D,ceil(D/2),voteCount)>=sideVoteCount].

Counterexample: D=K=16, sixteen valid IN votes gives H0,e∞. One such success sets S+∞ but cannot finalize with only one IN success. A following sixteen-vote OUT success gives S=+∞−∞. Both rounds meet answerfloor9 and80%success; the3success guard does not avoid undefined accumulation. This is the normal full-census success domain, not floating underflow. At D>=2, every full-population80%success has y>ceil(D/2) and true H0.

Smallest repair requires defining the arithmetic or changing the weight domain. No numerical evaluation trick, prose deletion or voting count can define the present signed sum. A finite cap, cancellation/reset rule or replacement distribution would be a new author choice; none is invented. Author question is pending. Keep this blocker and prohibit claiming an executable transition for it.

## EW2 — reached FINAL can permanently disagree with p

Sections §8 S6_0722–S6_0735 retain strict-count preference, reached-side FINAL and immutable state; S6_0741 retains p=in for entry.

Floor-valid finite scenario: D16,K16,floor9. Let a=ln286=5.655991810819852 from n10,y8, and b=ln1430=7.265429723253953 from n9,y8. Fresh Pending starts pOUT. Repeat13cycles [OUT(a),IN(b)]. No earlier score reaches either barrier; after12cycles S12ln5<T=ln1e9. On the13th IN, S13ln5=20.9226928616433>T, din=dout13 and ties retain pOUT. The amendment therefore declares FINAL-in while immutable preference remainsOUT. Matching admission preserves that state, and the pIN gate can never admit it. Mirroring sides from pIN gives FINAL-out/pIN. No infinity, subfloor round or Sybil is involved.

Smallest candidate integration is to make finalization's reached side govern terminal preference/membership. Whether that updates p or another gate condition must be explicit; the author question is pending. Labelling FINAL's side alone does not resolve the retained p-based rule. Do not restore the old requirement that FINAL agree with prior p, which the amendment explicitly replaces.

## EW3 — terminal signed-score overshoot creates permanent gate exclusion

Section §8 S6_0740–S6_0743 compare S with the prechange mean and explicitly mark the unconfirmed reading of “IN-side sum.” The scenario below is conditional on signed total S being that gate quantity.

Let an existing frozen W member have score3b=21.79628916976186, from three n9,y8 IN successes. A later live Pending x gets3IN(a),1OUT(b),2IN(a). Its sum first reaches the positive barrier at5a−b=21.01452933084531, with din5,dout1,pIN,FINAL-in. Every round meetsfloor9; all weights are finite. Host admission preserves the score. It remains below W's mean forever because FINAL accepts no further updates, so it cannot enter even with indefinitely many later honest YES replies.

A second node can already include x when it finalizes at the smaller score, and later admit the higher-score base. Thus terminal membership can retain different W for identical held FINAL-in items. A raw signed-sum gate, immutable terminal score and unequal overshoot need an explicit integration decision. The author has been asked whether “IN-side sum” instead means a separate positive-only sum; that interpretation is not silently added. A cap, terminal admission override or altered FINAL update would be a new choice, not a typography fix.

Root additionally checked the alternative uncapped positive-only interpretation: a base starting IN(a), then ten cycles OUT(a),IN(b), keeps pIN and first finalizes at signed sum21.75037094 with positive IN sum78.31028904. A late x finalizes after4IN(a) with positive sum22.62396724, below that mean forever. Thus merely choosing an uncapped positive-only accumulator does not generally resolve terminal gate exclusion; this additional root arithmetic is recorded separately from the reviewers' signed-gate witness. No extra positive accumulator or policy was implemented.

A related observation is not independently a defect: with a high weight an outsider can pass a frozen mean after only two successes, before FINAL. The current draft makes no weighted final-only-entrant claim and the existing freeze predicate blocks immediate refreezing; do not reopen this as the old capped-streak inference.

## EW4 — nine answers meet the floor yet select the apparent majority

Section §11 S6_0892 and test T6_0064 now record this unresolved case rather than weaken the hard zero-false/split assertions.

D=K16; fixed peer population has eight IN and eight OUT preferences. Eight timely YES and one timely NO meet floor9 and ceil(.8*9)=8. Seven remaining NO replies take250ms. A complete-answer time1ms establishes tMajority1ms, so the retained2*tMajority early ending can close the round at2ms; the normal fallback is4ms. The floor is met, so no doubling occurs. Each counted success gives H1/1430,e=ln1430. Three rounds give3ln1430=21.79628917>ln1e9 and3INsuccesses before the seven NO replies arrive. Mirrored directed timing at another honest poller produces three OUT successes and immutable opposite FINAL.

Possible actual observations require no fake items or algebraic forgery: sixteen servers may have admitted x; eight prefer/include x, eight nonfinal servers exclude it. A poller P holding x in W receives matching-root proofs from its eight supporters and a valid DIFF/exclusion from one opponent. Poller Q has a live captured Pending x with body completion delayed past6ms; it receives matching-root NOs from eight OUT servers and an arrival DIFF YES from one IN server. Such received YES does not violate the local-own-Pending prohibition. A common already-FINAL-in candidate z permits P to freeze {z,x} and Q to freeze {z}; FINAL-out Pending does not veto Q. Initial candidate/body states and their public-API setup must be explicit in the required executable regression. This is a concrete local state/message-timing counterexample with root preconditions, not a claim a new binary or full network simulator executed it.

Smallest authorized action now: preserve the counterexample and add the two-poller serialized regression under the unchanged safety assertion. Making response-selected n an unconditioned hypergeometric sample requires a voting/timing change or an explicit justified response assumption. Author disposition is pending. No new rule or weaker safety oracle was chosen by model agreement.

**Requested below-majority report:** no new FINAL can be sourced by a below-answer-floor round under literal rule13. Valid deduplicated item votes<=answered sampled peers. Below floor, both evidence and success counters are unchanged; the final predicate cannot newly become true. Duplicate/stale replies, rescue and invalidated lifetimes do not add votes. EW4 has9answers, so it does not contradict this precise conclusion. The old1YES/15slowNO scenario now grows its deadline until NOs count and reaches OUT in the independent rule trace; this is not executed node acceptance.

## EW7 — terminal-out reentry is a rule12 integration defect

Section §8 S6_0741 formerly admitted any physically held outsider with pIN,S>=mu, even though rule12 omits FINAL-out from advertised A. Test T6_0057 did not cover negative mean.

Counterexample: retained outsider x has FINAL-out,pIN,S=-13ln5=-20.9226928616433 (mirrored EW2). W has one nonfinal pIN member b with din=dout2 and S=2ln286−2ln35357670=-23.45006817815525: obtain two weak IN successes at D16, change D32,K32, then two OUT successes with n17,y16 and weightln35357670. Both OUT rounds meetfloor17; count2 prevents FINAL and ties preserve pIN. The old entry predicate would admit x because its negative score exceeds the more negative mean, contradicting terminal exclusion.

Smallest fix, independently shared: restrict outsiders to advertised A. Existing A excludes FINAL-out by author rule12, so no new store, preference policy or score condition is introduced. Add this negative-mean regression. This repair is accepted and does not resolve EW2/EW3.

## EW5 — defined small-population nontermination

Section §8 S6_0717: “H=1 gives e=0.” For D=K=n=y1, m1,H1,e0. Arbitrarily many unanimous successes leave S0; epsilon<1 means T>0, so a nonempty item never finalizes. This is defined behavior, not a division error. Documented as a liveness limitation, retaining nonfinishing reporting and existing workloads. No invented minimum D, exception weight or K crossover. A future requirement of nonempty D1 eventual freeze would need author revision.

## EW6 — stale raw-store operands contradicted advertised A

Section §6.1 S6_0307 stored “send-time |R|”; T6_0338 required inbound decoding against physical R. At R={z,x},xFINAL-out, A={z}, actual POLL setSize is1. Capturing size2 would reject an honest DIFF's cardinality relation. Peeling against R would introduce a spurious−x and advertise the omitted terminal item.

Smallest shared fixes: store send-time|A| and test inbound decoding against A, excluding Pending and retained FINAL-out bodies. No extra retained set/history. Both exact replacements accepted.

## Evidence and current execution status

Exact rational tails and80digit logarithms for D16,32,64,128,500, all-K/half-K and minimum80%/unanimous cases are in weighted-evidence.json and weighted-vectors.md and included in the test proposal. Half-K responses are below the new floor: applied weight0, no success, no final; raw tails are diagnostic. Fixture K=D and quarter-D do not select a production crossover. True infinite weights are explicitly distinguished from numerical underflow.

Independent reports document all eleven roles, frozen-source boundary, Pending semantics, naming source, timing/probe/projection and actual evidence limits. Root ran the exact arithmetic/state/timing reproducer and27 integrity checks. No simulator, current-protocol node acceptance, sanitizer, generated sizing table, human expert review, source freeze, publication or deployment ran.

Seven shared substantive claim repairs accepted; EW1–EW4 remain unresolved severity>=8. Not converged, not cap-exhausted:1of8run iterations completed. Next legal scope is arithmetic EW1 once its author definition arrives. Further policy-changing revisions require the missing author decisions already requested; repeating an identical empty review cannot resolve them or justify convergence.
