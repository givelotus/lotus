# Independent revision B — iteration 4

Reviewer: gpt-6.1-sol, independent context. I read settings, initial findings and ledger, the complete proposed specification, tests, conformance report and ordered input bundle, the IMPCD skill and authoritative v3 runtime. I did not read revision A or another reviser's analysis. I inspected the existing frozen contract, timing tests and fixtures, old voting declarations and preview tests, independent model/schedule oracles, host transport/body interfaces and delivery implementation, and freeze/include-boundary checks. No authoritative specification, source, frozen file or manifest was edited. Proposed stable-claim edits, with exact old/new bytes, are in `revision-b.json`.

The later arrival-evidence and strict-quorum instructions control. This revision preserves the selected gate, simultaneous evaluation, immutable FINAL, captured lifetimes, Pending transfer, rescue abstention, explicit partial observations, strict full-sample quorum, and all required workloads. It does not invent a replacement consensus policy. Model agreement is not external validation.

## F1 — support; severity 8, confidence 10; counterexample

Claim S0731, §8: “Since immutable FINAL-in members retain c=beta_c, a nonempty frozen W has mean beta_c, and a later gate entrant is itself FINAL-in.” T0067 repeats the implication in `T13_later_final_in_gate_entry_invalidates_freeze`.

Independently replayed the stated updates from fresh Pending state, initially preference OUT:

| Successes just applied | d[IN] | d[OUT] | Preference | c | Previous | FINAL |
|---|---:|---:|---|---:|---|---|
| IN × 11 | 11 | 0 | IN | 11 | IN | false |
| OUT × 1 | 11 | 1 | IN | 1 | OUT | false |
| IN × 11 | 22 | 1 | IN | 11 | IN | false |
| OUT × 12 | 22 | 13 | IN | 12 | OUT | false |
| Preserve state on admission, then OUT × 1 | 22 | 14 | IN | 12 | OUT | false |

Neither IN streak reaches twelve. The OUT streak reaches twelve but never overtakes the cumulative IN count. The item therefore has preference IN and capped confidence twelve without FINAL. If another candidate is already immutable FINAL-in, its frozen W has mean twelve; the specified gate admits this item at the next round end. Frozen W gains a nonfinal member, invalidating its prior freeze and preventing immediate refreezing under the existing predicate.

Smallest repair: correct the false consequence and add the regression to the existing test requirement. Do not add FINAL to the gate, reset Pending confidence, or change the streak update. Operations: S0731 and T0067. This is a correction to an asserted implication also present in the author's earlier amendment, not authorization to change that amendment's explicit operational gate.

## F2 — support; severity 6, confidence 10; counterexample

Claim T0246, retained test obligations: “valid root vote still counted”. The current §8 deliberately has no separate root vote or accumulator. `root_vote` remains a wire assertion; equality alone is not a MATCH proof or an item observation.

Reproduction: selected peer supplies a structurally valid fallback REPLY with its root equal to the poller's root, but peeling stalls and neither explicitly decodes nor excludes target captured item x. The current rule gives x abstention. Counting a root match would invent evidence. Exclusions and other permitted arrival observations still count on an ordinary incomplete reply; explicit contradictions retain their separate discard rule.

Smallest repair: replace the obsolete root-vote clause with the permitted §8 arrival item-observation rule. Operation: T0246. No new scoring mechanism.

## F3 — support; severity 6, confidence 10; conflicting contract language

Claim S0865, §11: “Silent peers abstain, so each round's effective sample is the peers that answered.” S0866–S0868 then derive an answerer-share assumption and refer to a guarantee; S0870 refers back to that assumption. T0340 separately directs replacement with “approved round-end/answerer tests”.

Reproduction: D=32, K=8, beta=.2, alpha=5, four YES and four silent peers. §8 has no success. Any interpretation that recomputes alpha against the four answerers produces success. Answerer-share measurement remains useful, but cannot define the quorum or imply an established safety guarantee.

Smallest repair: say explicitly that the denominator remains captured K; describe response independence as an evaluation/liveness assumption, and selective silence as potentially preventing quorum. Retain the actual adversarial answerer-share reporting requirement S0869. Correct “round-end/answerer” to “round-end/full-sample-quorum” in T0340. Operations: S0865–S0868, S0870 and T0340. The fixed-population adversary can withhold or delay without any Sybil identity; no identity-system redesign is needed to expose this distinction.

## F4 — support; severity 7, confidence 10; reachable undefined comparison

Claim S0432, §6.3: “Minimize n/P_hat(n), ties to smaller n.” Its zero denominator is reachable without knowing the generated table's empirical values.

At the largest accepted M=(2^21−256)/8=262112, the shared cap is five cells: floor((2^21−100−8M)/28)=5. Take captured raw R empty and one timely, internally valid DIFF assertion with missing_count=32768, wanted_count=0, set_size=32768, and no exclusions. Its IDs are nonzero, distinct and ordered; it fits 2 MiB, all list counts are within M, and it gives exact current sample 32768. Such unauthenticated but structurally valid peer assertions are explicitly allowed input, including from a scripted adversary.

Every stored prefix length at grid d=4096 is at least one. The prescribed d=32768 extension scales each by eight, so every quantile exceeds the runtime cap five. All candidate lengths cap to five, yet F_32768(5)=0. Therefore the cost comparison receives 5/0. This is independent of the actual table trials. Existing growth/doubling does not define the missing argmin arithmetic.

Smallest repair: define positive-n/zero-P cost as positive infinity, using the already selected smaller-n tie rule even when all costs are infinite. Add that case to the existing empirical-argmin requirement. Operations: S0432 and T0256. This does not reinterpret the CDF, insert a success floor, or change the cap or escalation.

## F5 — support the statistical concern, reject the proposed oracle replacement

Severity 8, confidence 9 for the current fixture/criterion conflict; confidence 10 that the proposed repair would override author authority.

Claim T0264: “23fast1ms/6silent/3slow100ms ... >=99% of1000 fixed seeds freeze within25 rounds”. Input P4 explicitly selected the 99%/1000/25 criterion and requires failure to be reported rather than repaired by seed changes. No later amendment withdraws that completion target. Replacing it with a purely state-transition oracle and empirical reporting would remove an author-owned acceptance condition. **No ledger operation changes T0264 or P4.**

I read the actual old `test/acceptance/timing_tests.cpp` in full. Its six cases are no-peers/time validation, terminal response correlation, two-/five-node loss and RTT-jump reconciliation, captured late deadlines, lost continuations/live edits and retry identity. It contains no `silent_slow_matching_twentyfive_rounds` case. `fixture.{h,cpp}` defines arithmetic/body helpers, not that network fixture. The old preview suite's finite null DP is a different D=5 SPRT primitive; it is not execution evidence for the proposed D=32 Snowball fixture. The exact silent/slow case is a proposal obligation, not a frozen executed test.

The old host permits physical link delay to differ from `LinkOptions.initial_rtt` (default 1000 microseconds); `set_link` can change physical delay without updating the node's captured RTT. Its WireReply adds service delay before reverse delivery. Consequently a slow response missing a 4ms captured fallback is a legal setup. More strongly, if the six silent peers have the default 1ms caps, then at most three selected peers have slow caps, so the upper median of any eight selected caps remains 1ms even when each slow peer correctly advertises 100ms. At most four fast replies cannot reach the five-answer timing majority, and fallback fires at 4ms; five fast replies yield quorum. Therefore the original .8706097943584039 per-round probability and .5039205077094632 freeze-by-25 probability are correct for this explicit permitted setup. The natural fixture need not underestimate slow RTT specifically. The proposal leaves the silent peers' captured RTT and exact wire/service split unspecified, so this is a conditional counterexample, not a claim that an already frozen fixture mandates it.

Even optimistically treating all three slow peers as timely gives a useful timing-independent ceiling: only 26 of 32 can answer, so success probability is at most P[Hypergeom(32,26,8)>=5]=.9771659868990236. A single initially nonfinal common candidate needs a twelve-success run. Exact independent fresh-round DP gives probability .9697785880192303 by round25, still below .99. Actual timing cannot improve on the all-26-timely ceiling. This is an ensemble probability, not deterministic impossibility for every possible bank of 1000 seeds; a fortunate fixed bank could exceed the target. No simulator or current-protocol acceptance binary was run, and I do not label the calculation a measured seed failure.

Required disposition: retain the author-selected target and workload, record the conflict and precise fixture assumptions, and report any actual failing seeds unchanged when the fixture is implemented. An author decision is needed before replacing the criterion, changing beta_c, changing the round/sample policy, or altering the network fixture. Do not tune the seed bank or add successful rounds beyond the prescribed horizon. An independent state-transition oracle is appropriate additional verification, not a substitute for P4.

## Reproduction of arithmetic evidence

The following standard-library calculation was executed independently; it does not execute a simulator or import production voting code:

```python
from fractions import Fraction
from math import comb

for available in (23, 26):
    p = sum(Fraction(comb(available, y)*comb(32-available, 8-y),
                     comb(32, 8))
            for y in range(5, 9)
            if y <= available and 8-y <= 32-available)
    state = [Fraction(1)] + [Fraction(0)]*11
    hits = Fraction(0)
    for _ in range(25):
        nxt = [Fraction(0)]*12
        nxt[0] = sum(state)*(1-p)
        for run in range(12):
            if run == 11:
                hits += state[run]*p
            else:
                nxt[run+1] = state[run]*p
        state = nxt
    print(available, float(p), float(hits))
```

Results: 23 → .8706097943584039 / .5039205077094632; 26 → .9771659868990236 / .9697785880192303. Absorbing success probability plus remaining state mass is one after every step. F1's trace was also replayed directly from the update rules; cap arithmetic yields M=262112 and cap=5.

## Eleven perspectives and additional findings

Coding theorist: checked field/cell assumptions and separated finite-syndrome consistency from authentication; no additional major contradiction established. IBLT researcher: verified retained-residual/current-Ref and tail-CDF reasoning; F4 is a genuine missing total-order convention. Distributed-consensus researcher: F1 invalidates a claimed gate consequence, not the selected gate itself. P2P developer: inspected old host delay/cap separation and new capture/late-reply contract; F5 is not evidence from an executed old timing fixture. Red-team attacker: fixed-population withholding, response timing, valid DIFF assertions and equivocal valid MATCH proofs do not require Sybils; F3/F4/F5 cover concrete failures, while the existing §9/§11 limitations already reject a blanket agreement theorem. Liveness/formal reviewer: independently replayed capped nonpreferred streaks and the exact run DP. C++ implementer: F4 needs explicit comparison semantics; preserve atomic errors and body-token lifetime behavior. Test engineer: remove F2's obsolete oracle and T0340's stale denominator language while retaining all original counts and host cases. Measurement engineer: retain P4 and distinguish statistical probability, actual fixed-seed outcomes and simulator measurements. Minimalist: choose deletion/correction over new gates, confidence machinery or response policies. Skeptical paper reviewer: do not present fixed correlated neighbourhoods or repeated rounds as a safety proof. Anchor: later operator instructions remain controlling; F5's replacement proposal fails that authority check.

No additional independent major defect is established by this pass. The six-claim F3 wording correction includes a related stale test-freeze instruction, not a new mechanism. Unresolved severity-eight F5 remains in the minority/disputed record until evidence and author intent resolve it. The submitted JSON changes eleven stable substantive claims, all motivated by F1–F4. No locking, consensus, convergence or freeze is claimed by this independent revision.
