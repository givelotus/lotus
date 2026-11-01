# IMPCD iteration 4 — technical findings

Authority and method: [settings.md](settings.md). Eleven technical perspectives plus author-intent anchor; independently revised by gpt-6-astra and gpt-6.1-sol. These are model reviews, not recruited human experts. Findings are ordered by severity × confidence. A counterexample stands without a vote. Existing source/harness/oracles/freeze tooling are historical evidence, not implementation of this proposed protocol.

| Finding | Severity | Confidence | Weight | Result |
|---|---:|---:|---:|---|
| F1: capped c does not imply FINAL-in | 8 | 10 | 80 | Corrected false implication and test; operational gate unchanged |
| F5: timing target conflicts with current completion distribution | 8 | 9 | 72 | OPEN; mandated target and workload preserved |
| F4: all candidate costs divide by zero | 7 | 10 | 70 | Defined comparison and added test requirement |
| F2: test retains separate root vote | 6 | 10 | 60 | Removed obsolete assertion |
| F3: answerer sample contradicts full-K quorum | 6 | 10 | 60 | Corrected limitations and test-freeze instruction |

## F1 — gate consequence is false

Exact section/claims: §8 S0731: “Since immutable FINAL-in members retain c=beta_c, a nonempty frozen W has mean beta_c, and a later gate entrant is itself FINAL-in.” T0067: “a later entrant must reach that mean and be FINAL-in”.

Counterexample: continuously live Pending x receives IN^11, OUT, IN^11, OUT^12. Then d[in]=22,d[out]=13,p=in,c=12,previous=out,FINAL=false. Preserve its state on admission; one further OUT gives d[out]=14,c=12,p=in,still not FINAL. An independently frozen W has mean12; the selected simultaneous gate admits x. Thus the inferred FINAL-in assertion and old test are false. The original amendment contains the same incorrect inference, but explicit state/gate/FINAL rules determine this trace.

Smallest fix: remove the false implication; state that a nonfinal entrant invalidates the prior freeze and the existing predicate must hold before refreezing. Preserve the FINAL-in entry case and add this exact nonfinal trace. No extra gate condition or mechanism; changing the gate would override the author's operational choice. Both revisers independently reproduced the state. Evidence: [counterexamples.py](counterexamples.py), [evidence.json](evidence.json).

## F5 — preserved timing criterion needs resolution

Exact section/claim: TESTS T0264, T16_silent_slow_matching_twentyfive_rounds: “23fast1ms/6silent/3slow100ms ... >=99% of1000 fixed seeds freeze within25 rounds”. Input P4: “assert that ≥ 99% of 1000 seeds freeze within T = 25 rounds; failing that is a test failure that is reported, never fixed by changing seeds.”

Scenario: one initially nonfinal common candidate; D32,K8,alpha5,beta_c12; fast/silent peers advertise1ms, slow peers advertise100ms. Every8-sample has at most3slow peers, so captured upper-median RTT is1ms and fallback4ms excludes100ms replies even with accurate slow RTTs. A round succeeds iff at least5 sampled peers are among23fast. Exact p=610489/701220≈0.8706097943584039; an independent consecutive-run DP gives probability0.5039205077094632 of a twelve-success run by25rounds. Even granting all26nonsilent peers timely responses gives only0.9697785880192303.

This is a counterexample to an implied ≥99% population completion expectation, not a measured failure or deterministic impossibility for every fixed1000-seed bank. Actual proposed fixture/seed execution is absent. The frozen timing suite has six older session-era cases and no exact proposed silent/slow case. No arbitrary seed set is manufactured.

Smallest authorized action: disclose the conflict, retain the target, all1000seeds and25round horizon, and report actual failures when executed. The initially suggested replacement with a conformance-only oracle was rejected by both independent anchors because P4 explicitly owns the target. A target, protocol or fixture change requires an author decision. This remains severity8 and blocks convergence; no new mechanism was added.

## F4 — totality of sizing cost

Exact section/claims: §6.3 S0432: “Minimize n/P_hat(n), ties to smaller n.” T0256 covers the argmin without zero denominators.

Counterexample: maximum allowed M=262112 implies shared cell cap5. A timely internally valid DIFF against captured empty raw R can assert32768 strictly sorted nonzero missing IDs, wanted0, exclusions0 and set_size32768. Its conservative payload262253bytes fits2MiB. Process this as the first usable sample, before Pending effects; Delta_hat_now=32768. Every4096-grid positive quantile is at least1; tail scaling by8 makes each at least8. All candidates clip to5, while F(5)=0, yielding5/0. This needs no empirical table values and can be sent by one scripted adversary, without Sybils. The protocol permits such unauthenticated assertions.

Smallest fix: positive n/zero probability compares as +infinity; retain smaller-n ties and unchanged growth/cap rules. Extend existing argmin test with this exact cap/DIFF/tail fixture. No probability floor, new score, threshold or mechanism. Both revisers agree on the repair; B supplied the stronger table-independent witness, independently checked by the root.

## F2 — removed root scoring survives in test text

Exact claim: TESTS T0246, T11_failed_decode_is_not_misbehavior: “valid root vote still counted”.

Scenario: structurally valid fallback REPLY has root_vote equal to the poller's root, but its arrival peel is incomplete and captured x is unclaimed. §8 requires x abstain; the test's extra root-vote instruction invents evidence absent from the selected protocol.

Smallest fix: delete that clause and require only permitted arrival item observations; no independent root vote or root confidence. Existing nonpunitive handling remains. No new mechanism.

## F3 — stale answerer-normalization language

Exact claims: §11 S0865: “each round's effective sample is the peers that answered”; S0866–S0868 derive an answerer-share assumption and implied guarantee. TESTS T0340: “approved round-end/answerer tests”.

Scenario: D32,K8,alpha5, fourYES/fourSILENT. Full-K rule has no success; recomputing quorum against four answerers would succeed. A fixed-population attacker can selectively answer/withhold without Sybils. The old effective-sample instruction conflicts with the final quorum contract.

Smallest fix: state captured-K quorum, response-dependent liveness/evaluation obligations and no independent-answering safety guarantee; retain actual adversarial answerer-share reporting. Change the test-freeze instruction to full-sampled-K quorum. No response policy, reputation or new guarantee.

## Coverage and limits

The two submitted reports separately document all eleven roles: coding/finite fields, IBLT, consensus, P2P, red team, liveness/formal, C++, tests, measurement, deletion and skeptical paper review. Fixed-population selective withholding, valid-assertion sizing attacks, equivocal MATCH proofs and fake-Pending poisoning were considered. No Sybil solution or new security theorem is claimed. Settled partial voting, rescue abstention, immutable FINAL and the simultaneous gate remain unchanged. No additional demonstrated major defect was established by either reviser.

No node acceptance, sanitizer build, simulator, sizing-table generation, human expert review or network measurement ran. Executed evidence is the small independent state/arithmetic reproducer and document/patch integrity checks. Required future workloads remain intact.
