# Iteration 6 — preliminary independent critique A, updated for rules13–15

Authority: final weighted-round rules1–15 and exact Rule10 in the maintained input bundle. Rules13–15 supersede the previous zero-answer floor and close the original one-fast-voter counterexample and n=0 ambiguity. This remains preliminary critique before the formal common-ledger brief. No proposal, ledger, source, simulator or frozen artifact was modified. No other reviewer's files were read.

All earlier D16,K16 traces using n1 or n8 as a counting round are **withdrawn under rule13**: the floor is9. Their arithmetic remains historical only. The current counterexamples below satisfy the floor.

## Current disposition

| Finding | Status under rules13–15 | Severity/confidence |
|---|---|---|
| A1 support-zero and opposite-infinity arithmetic | Remains open, floor-valid | 9/10 |
| A2 FINAL side versus cumulative preference | Remains open, new finite floor-valid witness | 9/10 |
| A3 immutable score overshoot versus relative gate | Remains open, new finite floor-valid witness | 8/10 for behavior; author intent needed |
| A4 single-fast-voter minority finalization | Closed by rules13–15 | No current defect asserted |
| A5 D1 zero evidence | Remains open | 8/10 |
| A6 n=0 success ambiguity | Closed by rule13 | No current defect asserted |

## A1 — support-zero tails and opposing infinities remain undefined

Rule3 adds signed e=−lnH. Rule4 requires at least3 corresponding successes and immutable FINAL. Rule13 requires n>=floor(K/2)+1.

D16,K16,floor9,n16,y16 gives H=P(X>=16)=0 under M=8. It is an ordinary unanimous successful observation, and n16 meets the floor. In fact any full-response success with y>=ceil(.8*16)=13 exceeds the null support8. The first IN success gives +infinity but not FINAL because countIN=1. A following OUT success, also n16, requires +infinity−infinity before either side has3 successes. Real arithmetic has no value for this expression, and NaN would leave comparisons undefined for protocol purposes.

This defect is unaffected by answer floors. Author choice is still required for H0 and opposing support-zero evidence. Stable log-tail evaluation addresses underflow for positive H, not mathematical H0. No cap, reset, selected winner or replacement null is introduced here.

## A2 — finite floor-valid FINAL-in with p=OUT

Use D16,K16,floor9 and define two permitted successful observation patterns:

- Weak side success: n10,y8, ceil(.8*n)=8. H=C(8,8)C(8,2)/C(16,10)=1/286; weight a=ln286=5.655991810819852.
- Strong side success: n9,y8, ceil(.8*n)=8. H=C(8,8)C(8,1)/C(16,9)=1/1430; weight b=ln1430=7.265429723253953.

Both n10 and n9 meet floor9. The weights were independently recomputed as exact rational hypergeometric tails before taking natural logs.

Starting at zero score, repeat [weak OUT, strong IN]13 times. After cycle j, counts are equal j/j and score is j(b−a)=j ln5. The first OUT success selects p=OUT; every subsequent OUT leads by one count and every IN only ties, so p remainsOUT. Scores never cross either barrier before the final step: the first OUT score is−a, later OUT dips are higher; after12 cycles score12ln5=19.3132549492092<ln1e9. The thirteenth IN produces score13ln5=20.922692861643306>ln1e9, with13 IN successes and p=OUT. Therefore Rule4 produces FINAL-in while the retained preference remainsOUT.

If admitted outside W, immutable FINAL plus the p=IN gate prevents entry forever in that lifetime. If Pending, FINAL-in blocks freezing until admission, but whole-state admission still preserves p=OUT. Mirroring the sequence yields FINAL-out/p=IN, requiring Rule12 to override any later candidate entry.

Author choice required: whether FINAL explicitly aligns preference, whether candidate eligibility uses the final side, or another selected rule. The old n1/n8 trace is not needed and is not current evidence.

## A3 — a lower overshoot can lock FINAL-in permanently outside frozen W

This counterexample uses only p=IN and finite weights a,b above; it is independent of A1/A2.

1. Let W={z}. Three strong IN successes give z immutable FINAL-in score3b=21.79628916976186. W freezes with this mean.
2. Keep outsider x Pending, or admitted outside W, with initial zero score.
3. Give x3 weak IN successes, then1 strong OUT success, then2 weak IN successes.
4. Its intermediate scores are a,2a,3a,3a−b,4a−b,5a−b. All before the last are below the epsilon barrier; none reaches W's mean. Preference isIN (success counts3/1 at the OUT step, then5/1).
5. The last score is5a−b=21.01452933084531>ln1e9=20.72326583694641 but below meanW=21.79628916976186. x becomes immutable FINAL-in, yet fails the gate. Admission preserves that score. Future votes cannot increase it, so x never enters W in its lifetime.

Every counting round has n9 or10>=9. No infinity, Sybil, out-of-domain sample, state reset or preference disagreement is used.

This demonstrates a new consequence of variable weighted overshoot: FINAL-in no longer ensures eventual gate eligibility after a freeze. The old capped-c construction made all FINAL-in gate values equal. Whether permanent FINAL-in exclusion is intended needs explicit disposition. Do not silently cap scores, continue scoring FINAL items, lower the mean or grant unconditional entry.

A separate old implication also fails unless removed or repaired: entry after a freeze need not imply FINAL-in under the3-success guard. Start from the above W mean21.796289, then let D and K become32 (population change does not reset settled scores). The new floor is17. For an outsider, n17,y16 gives H=1/35357670 and e=17.381025899897477; it satisfies ceil(.8*17)=14. Two IN successes give score34.762051799794954, exceeding W's mean, while countIN=2 forbids FINAL. It passes a score/p=IN gate but is nonfinal. This trace is floor-valid and finite. If the new rendering makes no FINAL-in-entry implication, treat this as required behavior/test coverage rather than a contradiction; do not preserve the old proof unmodified.

## A4 — original minority-answer attack is closed

Rule13 permits no item update or success when n<floor(K/2)+1. At D16,K16, one valid timely YES has n1<9 and adds0; it cannot advance success counts or FINAL. Rule14 doubles when fewer than9 selected peers answer at all, so one fast answer no longer suppresses deadline growth. Rule15's1ms YES/250ms NO regression directly exercises that correction.

With an initial4ms formula deadline, the below-floor sequence doubles to8,16,32,64,128,256ms. With no earlier-termination event, the round whose deadline exceeds250ms can count the15 NO replies. The full observed n16 and15 NO meet the80% success threshold13; the intended result is OUT, subject to resolving A1's representation of its H0 weight. No replacement private simulator result is claimed.

**Answer to the operator's question:** under literal rule13 and atomic round scoring, I have no attack in which a first FINAL transition is driven by fewer than a majority of the sample casting valid votes in that round. A below-floor round changes neither score nor successes; if an earlier round had already satisfied the final predicate, it should have finalized then. This is a local eligibility invariant, not a global safety proof. Majority answering can still differ from majority valid target-item votes, but that difference cannot bypass the per-item floor. Invalid/partial responses meeting the timing floor may impede liveness, not justify scoring with too few votes.

## A5 — D1 has identically zero evidence even above the floor

For D1,K1,floor1, a valid unanimous observation has n1,y1,M=ceil(D/2)=1. H=1,e=0. Every round meets the floor and may increment successes, yet the score remains0 forever. For every legal epsilon<1 the positive barrier is strictly greater than0; no nonempty item reaches FINAL. Two honest connected nodes with matching valid sets and perfect communication therefore cannot achieve nonempty freeze through this rule.

This remains a deterministic liveness counterexample. Whether the two-node workload only checks candidate agreement or also requires eventual freeze must be reconciled explicitly. Changing the null boundary, special-casing D1, or excluding this supported topology is an author decision; no such repair is inferred here.

## A6 — zero valid votes is now unambiguous

For every live round K>=1, floor(K/2)+1>=1. Hence n0 fails rule13, is not a success and changes neither score nor success counters. The previous ceil(.8*0)=0 ambiguity is resolved by precedence of the new floor. D0 continues to open no round.

## Rule12, Pending and style boundaries

FINAL-out removal from the sketched set must remain separate from host body ownership. The common ledger must consistently project cells, set_size, round captures, DIFF cardinality/membership, exclusions, decode reference and harness truth, while retaining immutable per-item state and normal tip-reset behavior. This is an integration review obligation, not a claim that unfinished regeneration already contains a defect.

Local Pending cannot generate a local outbound YES. A remote peer that holds/prefers x may still provide an incoming YES observation for the poller's captured live Pending x. The amended freeze veto depends on preserving that distinction; no incoming-Pending-YES ban is inferred.

The requested `/Users/shammah/repos/lotus/doc/developer-notes.md` is absent; I read the canonical daemon copy at `/Users/shammah/repos/lotus/daemon/lotusd/doc/developer-notes.md`, which explicitly requires **CamelCase functions/methods, lowerCamelCase variables, m_ member prefixes, UPPER_SNAKE_CASE global constants and lower_snake_case namespaces**. Future formal revisions will follow those rules for C++ identifiers and samples; mathematical variables and literal wire/provenance paths must not be mislabeled as C++ identifiers.

## Completion and perspectives

Anchor/minimalist: preserve rules13–15 and withdraw obsolete witnesses; no selected repair or weakened workload. Formal/consensus/liveness: A1–A3/A5 remain exact current counterexamples. Red team/P2P: old timing attack blocked by two distinct floors; no new fewer-than-majority-vote FINAL attack demonstrated. Coding/IBLT: Rule12 projection and Rule11 estimator mapping remain review points. C++ implementer: support-zero score arithmetic still needs a total specified domain. Test/measurement: current traces are independent exact arithmetic, not executable-node/simulator evidence; preserve hard zero-false/split assertions. Skeptical-paper reviewer: a local answer-floor invariant is not an inherited security theorem or an executed adversarial campaign.

The contract is not yet ready for a convergence claim while A1/A2 and the new gate/small-D consequences lack explicit disposition. Formal same-ledger revision awaits the coordinator's completed common brief/settings, as requested.
