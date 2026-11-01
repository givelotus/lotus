# Preliminary independent critique B — evidence-weighted amendment

## Update after owner rules13–15 — current findings supersede the historical discussion below

I read the appended answer-floor/deadline-backoff section in full. Item updates now require `n >= floor(K/2)+1`, and fewer than that many total answering peers double the next deadline. No new source or ledger edit is made here. The old D16 n1 and n8 witnesses below do **not** count under these new rules. In particular, B2's zero-vote ambiguity and B4's one-fast-voter accumulation attack are closed operationally by the positive item floor. The author's precise question has a direct answer: with the floor applied before evidence, success-counter or finality mutation, **no item can newly reach FINAL from a below-floor round**. Item-specific valid votes and total timing answers remain separate counts.

### Current B3 replacement — immutable FINAL-in score below the frozen gate mean

**Severity8, confidence10; finite floor-valid witness; rules3–5,13.** At D16,K16 the item floor is9. A weak success with n10,y8 meets80% and has exact H=1/286, weight a=ln286=5.655991810819852. A strong success with n9,y8 meets ceil(.8*9)=8 and has exact H=1/1430, weight b=ln1430=7.265429723253953. Both denominators meet the item floor; no infinities are involved.

Let existing candidate w become FINAL-in after three strong IN successes. Its immutable sum is3b=21.79628916976186, above T=ln1e9=20.72326583694641. W={w} is nonempty and frozen when no FINAL-in Pending blocker exists.

An outsider x can remain live Pending while receiving three weak IN successes (sum3a=16.967975432459557<T), one strong OUT success (sum3a−b=9.702545709205605), and two more weak IN successes. Its final sum is5a−b=21.01452933084531>T, with dIN5,dOUT1,pIN and FINAL-in. At the penultimate state4a−b=15.358537520025457<T, so it did not finalize earlier. Admission preserves this lifetime and full state.

The frozen W mean remains21.79628916976186, strictly above x's immutable21.01452933084531. Therefore x can never pass the unchanged score gate while W is retained; future evidence cannot help an immutable item. While x is Pending it blocks a new freeze under rule5; after admission it is permanently outside W. This establishes a terminal-score/gate integration failure relative to the intended FINAL-in admission behavior. The exact gate itself is being followed, so repair needs an explicit author choice rather than silently clipping the final score or bypassing the mean. The parent-provided numerical witness was independently recomputed from exact rational hypergeometric tails.

### Current B4 replacement — response-conditioned evidence with a majority answering

**Severity9, confidence10 for majority-opposed FINAL-in; rules2–4,10,13–14.** At D16,K16, make exactly nine peers reply at1ms: eight YES for x and one NO. The remaining seven peers give honest NO replies only after250ms. One of the eight fast YES peers is Byzantine; the other seven YES peers and all eight NO peers are honest. The identities are fixed, so there is one Byzantine among sixteen and the honest majority is OUT.

Each completed round has n9,yYES8 and thus meets both the item answer floor9 and the80% success threshold8. Its weight is the finite b=ln1430 above. After three rounds x reaches3b>T with three IN successes and becomes FINAL-in. With nine answers at1ms, the retained strict-majority answered timer may close at2ms; even using the4ms fallback, all three rounds finish long before250ms. Total-answer backoff never triggers because nine answers meet its floor. Unmeasured slow peers may still impute the1ms measured-peer median, but the majority-answer timer alone is sufficient for this short trace.

This attack does **not** reach FINAL with fewer than a majority answering. It shows that a majority answering does not make the selected answer set an unconditioned without-replacement sample from D. Eight YES peers are exactly the D16 null count; the conditional responder set contains all eight every time, making a nominal1/1430 tail event deterministic under this schedule. Repeated conditioning then yields terminal evidence against the honest-majority preference. No Sybil identity, packet loss, infinite arithmetic or subfloor item vote is used.

The hard zero-false/split assertions remain intact. A complete split-freeze regression needs a declared cross-node topology, body/candidate lifetimes and metric estimand; I do not claim an executed network result. The concrete trace should remain a high-severity finding and test obligation. Repair would change author-owned weighting, response assumptions or timing policy and must not be guessed by the reviewer.

### Other current dispositions

B1's opposing-infinity case still uses n16 and meets the floor; it remains open. B5's D1 case has floor1, n1, H1 and zero evidence forever; it remains a real liveness boundary. B6's host-versus-sketched-set integration obligation and B7's probe-fallback sizing precision remain regeneration obligations. The former finite preference-mismatch sequence in historical B3 uses n1/n8 and is superseded; it must not be cited as floor-valid. The newly proved permanent gate obstruction above is independent of that old witness.

The **FINAL/preference mismatch itself also survives the floor**, with a different finite sequence. Using the same valid a,b weights, repeat ten cycles `[IN(a), OUT(b), IN(a), OUT(b), IN(a), OUT(b), IN(a)]`. Every intermediate score stays strictly between the barriers; the end state is S=8.276780735175514,dIN40,dOUT30,pIN. Then apply four strong OUT successes: scores1.011351011921561,−6.254078711332392,−13.519508434586346,−20.784938157840298. The last crosses the negative barrier, with OUT-success count34 and FINAL-out, while unchanged cumulative preference remains IN because dIN40>dOUT34. Reversing the sides gives FINAL-in with preference OUT. All observations use n9 or n10 and y8; no infinity or subfloor success appears. I executed a scalar replay and asserted no earlier FINAL crossing. Severity8/confidence10: the terminal-side versus preference/gate integration choice remains necessary under the floor.

---

The following section preserves the preliminary pre-floor critique as provenance. Its n1/n8 D16 examples are historical and are not current executable counterexamples under rules13–15.

Read all final weighted-round sections in full: rules1–9, rules10–12, and the exact rule10 replacement. This is preliminary critique of the operator amendment before a common revised ledger is available. I have not read another reviser's output and have not edited a proposal, source, input bundle or ledger. Claim references below are the operator's numbered rules, since stable revised claim IDs are not yet assigned. No simulator or implementation conformance result is claimed.

## B1 — opposing infinite evidence is reachable and undefined

**Severity9, confidence10; mathematical counterexample; rules3–4.** Rule3 defines `e=-ln H` for a hypergeometric tail with `ceil(D/2)` successes in population D. With D16,n16,y16, H=0 exactly: sixteen votes cannot be drawn from eight successes under the null. Thus a unanimous success adds infinite evidence. One such IN round cannot finalize because the three-success minimum has not been reached. A following unanimous OUT round then requests `+infinity - infinity` before either side has three successes. IEEE arithmetic yields NaN; extended-real arithmetic also leaves this expression undefined. The cumulative counters and immutable FINAL rule do not resolve it.

This does not require an adversary to exceed the population bound: honest peer preferences may change, and the message contract imposes no monotonic preference requirement. More fundamentally, the state transition must handle admissible serialized votes without assuming the input sequence cannot occur.

The smallest repair requires an author decision about zero-tail evidence and opposing infinities. Do not silently clamp, smooth H, invent a finite proxy, or delete the three-success requirement. Preserve the finding if the choice remains open. H=0 should have an explicit deterministic representation and combination rule before implementation.

## B2 — zero votes satisfy both success predicates

**Severity8, confidence10; mathematical counterexample; rules1–3.** For n_x=0, `ceil(.8*n_x)=0`, while both YES and NO counts are zero. Consequently both sides satisfy the stated success predicate. Their tails are H=P[X>=0]=1 and weights zero, but the ambiguity still matters to side-success counters, previous-success fields and the minimum-three rule. If zero-vote rounds count as successes, they can prefill the minimum-success counters before one informative round.

The preceding plain-Snowball rule had an explicit no-success outcome for silence, but the weighted amendment replaces that success rule. It does not itself state a positive-vote prerequisite. Clarify with the author that n_x=0 means no success, no side-success-counter increment and zero evidence. Do not pick an ordering between simultaneous IN/OUT successes. This is separate from the nonzero-n 80% rule, under which both sides cannot succeed.

## B3 — finite evidence can finalize against the unchanged cumulative preference

**Severity8, confidence10; finite counterexample; rules3–5 and12.** This defect does not depend on any convention for H=0.

At D16, a success with n1,y1 has H=1/2 and e=ln2=.6931471805599453. A success with n8,y8 has H=1/C(16,8)=1/12870 and e=ln12870=9.462654300590172. At epsilon1e-9 the barrier is ln1e9=20.72326583694641.

Start from ordinary admitted preference IN. Apply twenty small IN successes: sum=13.862943611198906, dIN20,dOUT0,pIN; the sum has not reached the barrier. Then four large OUT successes produce sum=-23.98767359116178 and OUT-success count4. Rule4 therefore makes the item immutable FINAL-out. The unchanged preference rule still has dIN20>dOUT4, so preference remains IN. Reversing the sides gives FINAL-in while preference remains OUT after twenty small OUT and four large IN successes.

Rule4 explicitly says FINAL is the side reached rather than prior preference. That makes the side difference intentional, but rule5 also preserves the preference/gate/freeze predicate. Those interfaces need an explicit integration rule: an immutable FINAL-in item with preference OUT can never satisfy a pIN gate if preference is itself frozen; an immutable FINAL-out item with preference IN need not satisfy the old pOUT exit condition. Rule12's mandatory removal from the sketched set creates a further candidate/raw-set integration obligation in the latter case.

The author must choose how terminal side controls candidate entry/exit and freeze classification. Do not silently overwrite cumulative preference or change finalization back to preference-constrained, because both would override the supplied amendment. This is a distinct question from infinite evidence arithmetic.

## B4 — fixed-population answer-selection attack survives the exact deadline rule

**Severity9, confidence10 for premature majority-opposed FINAL-in; conditional split-freeze consequence; rules1–4 and exact10.** A robust setup avoids any dependence on whether old late replies update timing:

1. A victim has D16 fixed peers and polls all sixteen, as required at small D. Exactly one peer is Byzantine, a 1/16 fraction; identities never change. The victim already holds candidate x.
2. The Byzantine peer gives a correlated valid YES for x in a complete reply after1ms, every round. It may provide a valid MATCH proof for the victim's captured candidate IDs; this does not require body authentication.
3. The other fifteen peers are honest, do not prefer x, and would give NO. Their complete replies arrive250ms after each POLL, because of transfer/service delay. No packet is lost.
4. Initially no request-to-complete-reply measurement exists and the permitted existing fallback is4ms. Once the fast peer is measured, every other unmeasured sampled peer imputes the upper median of measured peers:1ms. The formula remains4ms.
5. Each round has one answer, so zero-answer doubling never triggers. Each x round has n1,yIN1 and a successful80%-of-answerers result, with e=ln2.
6. At thirty rounds, time120ms, the victim reaches30ln2=20.79441541679836>ln1e9 and has thirty IN successes. It finalizes x IN before the first honest NO reply arrives.

This is deterministic under the specified deliveries and uses neither Sybils nor rare random samples: K=D. The null distribution treats the sole timely answer as an unconditioned draw from D, while answer timing selected the one adversarial identity. Exact request-to-reply measurement of peers that answer cannot establish an unbiased answer set. Imputing the fast measured peer's time onto the unmeasured majority and resetting after any answer preserves that conditioning.

The requested100ms version also repeats4ms rounds to120ms if stale replies are discarded without updating timing under the retained no-effects rule. If late complete replies can update measurements, it needs additional analysis after their first arrival at100ms. The250ms construction above avoids this ambiguity and establishes the defect before any such event.

Other honest nodes may settle a candidate set omitting x using their faster mutual links; this can yield split frozen sets depending on the exact cross-node fixture and split-freeze estimand. I have not run or claimed that fixture. The directly demonstrated fact is that an overwhelming majority's NO votes have no influence before a minority-selected FINAL-in becomes immutable. This contradicts a majority-based interpretation of the evidence, and makes the required zero-false/split acceptance obligation a concrete test target rather than an established property.

Repair requires an author choice about response-conditioned evidence or progress/deadline semantics. Do not restore the old full-K quorum, add a minimum-answer constant, or change the new weight without authorization. Preserve this high-severity counterexample and test it with actual serialized replies and fixed peer identities once the revised executable contract exists.

## B5 — D1 honest agreement cannot accumulate any weight

**Severity7, confidence10; liveness boundary; rules3–4,7.** With one connected peer, polling all D means n1. The null population has ceil(D/2)=1 success, so a unanimous YES or NO has H=1 and e=0. Repeating successful rounds indefinitely never reaches either positive barrier for any allowed epsilon<1. A nonempty candidate therefore cannot finalize or freeze, even in a perfectly reliable, identical, two-node honest network. Three, or any number of, successes do not help.

This is a concrete consequence of the chosen null rather than an arithmetic exception. It conflicts with retaining a two-node eventual-freeze obligation. The author must either explicitly accept this small-population liveness limitation or revise the null/small-population behavior. Do not silently special-case D1 or weaken an existing workload. D0's idle/empty-state rule is separate. D2 does not share this exact zero-weight-unanimity property: a full two-peer unanimous sample has H0, bringing it under B1 instead.

## B6 — rule12 needs distinct host and sketch/candidate membership semantics

**Severity8 if left internally inconsistent, confidence9; interface consequence; rule12 plus retained host-admission contract.** “FINAL-out items leave the sketched set and are never listed as exclusions again” cannot be implemented by erasing a still-host-admitted body from the host's actual pool. Nor can the old raw `R=host-admitted distinct IDs` simply continue feeding set_size, cells and full exclusions: that would still encode the FINAL-out item or list it as an exclusion, contrary to rule12.

The revised contract needs to distinguish retained host bodies/item lifetimes from the current encoded raw set. Count/cell/list reconstruction and candidate subset relations must consistently use the encoded set; host removal, rekey and body validation must still refer to real retained bodies. Final-out terminal records cannot silently disappear and then be treated as fresh ordinary admissions under the same lifetime. No protocol-record or source edit is proposed here; this is a regeneration consistency requirement. B3 demonstrates why relying only on the old preference-based candidate exit is insufficient.

## B7 — probe-estimate fallback needs a precise existing sizing operation

**Severity6, confidence8; underspecification argument; rule11.** The author removed the twice-largest-probe-index fallback, selecting the probe's difference estimate instead. The estimate and its censor/lower-bound policy are available, but “sized from” does not explicitly say whether the responder uses S(estimate), an empirical-CDF argmin, or another already selected operation, nor which predecode reference applies on inbound POLL. The natural minimal reading is the existing median-floor operation, but a normative regeneration should make that reading explicit or record the remaining choice. Do not invent a multiplier or treat a censored lower bound as authenticated actual difference.

## Pending distinction and review limits

An own Pending item is absent from the node's admitted candidate/sketch state and must never cause that node to vote YES when answering a peer. This does not forbid the node from receiving remote YES observations about its own Pending lifetime: a remote admitted holder may prefer that item. Such received observations can make local Pending FINAL-in; the new freeze block and alternate yes-donor fetching apply to that case. The distinction must survive regeneration and testing.

This pass used mathematical arithmetic and explicit event schedules, not simulated experts or simulator evidence. Anchor/minimalist review rejects guessed repairs to the author-owned rules. Consensus/liveness/measurement/red-team perspectives identify B1–B5; P2P/C++/test perspectives identify the membership and sizing integration obligations B6–B7; coding/IBLT review preserves the existing primitive arithmetic and current-Ref discipline. Formal same-ledger revision remains pending the root's common ledger and findings, including any new author decisions.
