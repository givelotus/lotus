# Independent revision A — IMPCD iteration 4

I independently read the settings, initial findings, ledger/renderings, complete ordered input bundle, conformance report, IMPCD skill and v3 runtime. I inspected the current source contract, acceptance timing/fixture/pooling cases, schedule/cell oracles, relevant host transport/API boundaries, and frozen inventory/registration tooling. I did not read revision B. No production, header, harness, oracle, manifest or authoritative parent specification was edited. `revision-a.json` contains exact old/new text for 13 stable claim replacements; this report explains their evidence. No simulator, node acceptance, sizing-table generation or network experiment was run.

## Decisions

| Finding | Disposition | Severity | Confidence | Evidence |
|---|---|---:|---:|---|
| F1 | Support counterexample and smallest rule-preserving correction | 8 | 10 | Exact reachable item-state trace |
| F2 | Support removal of obsolete root-vote assertion | 6 | 10 | Direct contradiction with selected item-only rule |
| F3 | Support correction to captured-K and response-assumption language | 6 | 10 | Concrete quorum counterexample |
| F4 | Support explicit zero-denominator cost convention and regression | 7 | 9 | Valid cap/CDF domain boundary |
| F5 | Support serious acceptance-target conflict; reject unilateral oracle replacement | 8 | 10 for math, 8 for unexecuted fixture outcome | Exact conditional probability; author-owned target |

## F1 — c at its cap does not imply FINAL-in

Claims: §8 S0731, “Since immutable FINAL-in members retain c=beta_c, a nonempty frozen W has mean beta_c, and a later gate entrant is itself FINAL-in.” T0067 requires the same implication in `T13_later_final_in_gate_entry_invalidates_freeze`. The authoritative SNOWBALL-ROUNDS item 6 contains the same inference, but its explicit state transition, simultaneous gate and FINAL predicate determine the counterexample. Removing the incorrect inference preserves those selected rules.

At beta_c=12, keep x in a continuously live Pending lifetime with a fetch/awaiting result delayed by the host. Starting at p=out,d=(0,0),c=0:

| Success sequence completed | d[in] | d[out] | p | c | Previous | FINAL |
|---|---:|---:|---|---:|---|---|
| 11 IN | 11 | 0 | in | 11 | in | false |
| then 1 OUT | 11 | 1 | in | 1 | out | false |
| then 11 IN | 22 | 1 | in | 11 | in | false |
| then 12 OUT | 22 | 13 | in | 12 | out | false |

No preferred IN streak reaches12. OUT never overtakes22, so its12-run cannot finalize. Existing W can independently consist of FINAL-in members. Admit x preserving the live Pending state. One additional OUT success yields d[out]=14,p=in,c=12,previous=out,FINAL=false. The gate sees mu=12 and must admit x. Its new root invalidates the old freeze, and the existing freeze predicate forbids refreezing while x is nonfinal.

This requires no Sybil, counter overflow, malformed wire, changed threshold or new policy. Eligible per-item observations can differ for x and existing W. The state remains reachable with a long host fetch delay because no core timeout cancels an awaiting item.

Smallest fix: S0731 states the actual implication and renewed freeze check; T0067 preserves the ordinary FINAL-in entry coverage and adds the exact legal nonfinal entry. Do not add a FINAL requirement to the gate, reinterpret c as a preferred-side streak, or reset state on admission.

## F2 — an incomplete reply has no independent root vote

Claim: T0246, `T11_failed_decode_is_not_misbehavior`, ends “valid root vote still counted.” §8 explicitly removes root-confidence state, and the final ordered voting instructions allow only captured item observations.

Scenario: an honest structurally valid fallback REPLY is incomplete at arrival and leaves captured x unclaimed. Its root_vote can equal the poller's root, but this does not turn x into a yes observation or create root confidence. A nonpunitive peel failure remains nonpunitive; explicitly decoded-present/nonexcluded items may still vote yes, decoded-absent/excluded items no, others abstain. An actual separately received valid MATCH retains its prescribed semantics.

Smallest fix: replace only the obsolete clause with permitted arrival observations and the no-root-accumulator rule. Do not discard valid partial item observations or treat raw root comparison as MATCH proof verification.

## F3 — sample size cannot become the number of answerers

Claims: §11 S0865 says “each round's effective sample is the peers that answered”; S0866–S0868 turn response independence into an implied guarantee about answerer adversary share. T0340 still requests “round-end/answerer tests.” These conflict with the final full-K quorum rule and overstate the guarantee elsewhere explicitly withheld.

Scenario: D32,K8,beta_adv=.2,alpha5; four timely yes replies and four silent peers. The selected rule produces no success and resets nonfinal c. Normalizing to four answerers produces a conflicting majority decision. A fixed set of adversarial peers can selectively answer or withhold without acquiring any identities. The reporting obligation for actual adversarial share of answerers remains useful and remains unchanged.

Smallest fix: S0865–S0868 and S0870 distinguish captured-K quorum from response-dependent liveness/evaluation; retain S0869's actual-answerer-share metric. T0340 requests full-sampled-K tests. No security theorem, adversary-response independence guarantee or new assumption is introduced.

## F4 — valid capped candidate domain can have only zero CDF values

Claim: §6.3 S0432, “Minimize n/P_hat(n), ties to smaller n.” T0256 covers the argmin but does not cover all-zero probabilities.

Arithmetic: B=2^21=2097152; M=floor((B−256)/8)=262112. Then the exclusion-limited reply cap is floor((2097152−100−8*262112)/28)=floor(156/28)=5; the other cap operands are larger. Prefix requests remain positive.

Use an independent synthetic quantile fixture with all20 stored lengths greater than5 for the current difference samples (for example all6). Every candidate is clipped to5; the unmodified F definition gives F(5)=0 for every sample. Thus P_hat(5)=0 and the existing quotient is undefined unless its arithmetic domain is specified. This fixture tests a domain expressly admitted by the CDF and cap rules. Large positive-d table rows can also exceed this tiny runtime cap; the frozen table has not yet been generated, so I do not claim an executed generated-table witness.

Smallest fix: positive n / zero probability compares as +infinity. If all candidates have infinite cost, keep the existing smaller-n tie rule, then apply existing growth/cap rules. Add this exact cap5/quantile fixture to T0256. This defines sizing arithmetic only; it adds no likelihood confidence or replacement tuning parameter.

## F5 — preserve the target and report the conflict

Claim: T0264 requires “>=99% of1000 fixed seeds freeze within25 rounds” for a nonempty matching victim with D32,K8,alpha5,beta_c12 and23fast/6silent/3slow peers.

Authority: ordered input P4 explicitly states “assert that ≥ 99% of 1000 seeds freeze within T = 25 rounds; failing that is a test failure that is reported, never fixed by changing seeds.” Later amendments change voting but do not explicitly revoke this acceptance target. Therefore the initial suggested repair, replacing its success-rate oracle with conformance-only checks, is an author-intent change. I dispute that repair. Retaining1000 trials while dropping their success threshold would still weaken the required test.

Source inspection: current `test/acceptance/timing_tests.cpp` has six old session-era cases; none implements this proposed silent/slow1000-seed fixture. The actual old `T16_loss_and_rtt_jump_eventual_exact_reconciliation` uses two/five nodes, true RTT3000 or20000us, initial_rtt1000us, and zero/10% loss. `host.h::LinkOptions` separates actual delay from initial_rtt; `Host::connect` and `connect_wire` pass initial_rtt into PeerCaps. Thus the harness supports RTT underestimates, but it would be incorrect to say the old source supplies the exact proposed32-peer fixture or its1000 fixed seed list. Historical proposal scripts specify23 honest RTT1ms,6silent,3slowRTT100ms, but no complete per-silent-peer RTT assignment or executed outcomes.

The initial fast-only calculation is correct for a permitted fixture: advertise1ms for23fast and6silent peers and100ms for3slow peers. Among8 sampled peers, at most3 have100ms RTT, so the upper median (5th sorted RTT) is always1ms. Fallback is4ms. Slow100ms replies always miss it even with accurate slow RTT advertisements; no underestimate is necessary. A round succeeds exactly when at least5 of8 are fast:

`p23 = sum(j=5..8) C(23,j) C(9,8-j) / C(32,8) = 0.8706097943584039`.

For independent fresh uniform rounds, the exact probability of a run of12 successes by25 is `0.5039205077094632`, independently recomputed with rational arithmetic.

A stronger diagnostic avoids every RTT ambiguity: grant all26 nonsilent peers timely matching replies. The per-round success probability is at most

`p26 = sum(j=5..8) C(26,j) C(6,8-j) / C(32,8) = 0.9771659868990236`.

The same exact run-state recurrence gives completion probability `0.9697785880192303` by25, still below99%. This upper bound assumes perfect decoding, no initial delay, fixed nonempty W and all honest matching preferences; actual timing can only lose eligible votes. It concerns idealized fresh uniform sampling, not a claimed theorem about an unspecified deterministic seed collection. A particular1000-seed collection could exceed its expectation; no actual seed pass/fail result is claimed here.

Reproducer (pure arithmetic, not simulator execution): start q[0]=1,q[1..11]=0. For25 steps set next[0]=(1−p)*sum(q), next[i+1]=p*q[i] for0<=i<11. Absorb q[11]*p as success; answer1−sum(q). Compute p with exact fractions of binomial coefficients.

Smallest authorized action now: retain T0264 and all workloads/seed constraints; report the conflict and missing complete fixture definition. S0887/T0401's “No unresolved contract question” must no longer hide it. `revision-a.json` proposes those disclosure corrections only. An author must choose whether to revise the target or selected protocol after reviewing evidence; this review does not select either. A future independent quorum/run-state oracle is useful additional validation but cannot silently replace P4's acceptance requirement.

## Eleven-perspective audit and minority assessment

1. Coding theorist: inspected One/Two algebra, source-cell grouping, finite-syndrome limitation and schedule equations. Existing source and independent schedule oracle already use the corrected integer quadratic law; I found no new arithmetic counterexample requiring a claim edit.
2. IBLT researcher: checked residual/reference separation, current-Ref updates, private working copies, probe/prefix growth and frozen CDF. F4 is a genuine totality defect. Honest incomplete and explicitly contradictory peeling remain distinct.
3. Distributed-consensus researcher: independently traced Snowball cumulative ties, capped streaks and lifetime transfer. F1 is conclusive. Repeated rounds do not establish an epsilon/global agreement theorem; existing §9/§11 already disclaims one.
4. P2P developer: verified captured sample/connection identity, reply lateness and current PeerCaps timer inputs. F3 and the concrete F5 median calculation are material. Fixed-peer selective withholding needs no Sybils.
5. Red-team attacker: considered fixed-population selective response, valid MATCH equivocation to different pollers, poisoned Pending references, fabricated IDs and withholding until FINAL. These can bias usable evidence or cause nontermination; the core explicitly does not authenticate honest preferences or guarantee safety under all such schedules. No extra proof is inferred from strict-majority uniqueness. F1 additionally yields a legal nonfinal gate entrant using only supported state transitions.
6. Liveness/formal reviewer: exact recurrence establishes F5's conflict. Empty W with nonempty R/Pending intentionally never freezes, including when all items become FINAL-out; I did not change that settled author rule or mislabel it as an accidental vacuity bug. Nontermination/split outcomes remain reportable.
7. C++ implementer: F4 removes an implementation-dependent divide-by-zero comparison. Capture, token, donor, residual and item-state bounds were reviewed. No source modification or claim of new implementation conformance is made.
8. Test engineer: F1/F2 show tests can encode false or removed assertions. Frozen timing sources do not contain the proposed F5 fixture. Contract/freeze tooling explicitly forbids rebaselining failures to fit implementations, supporting retention and disclosure rather than oracle weakening.
9. Measurement engineer: distinguishes empirical1000-seed outcomes from idealized DP probabilities and expectation; no simulation result is fabricated. F5 needs explicit captured RTTs, event timing and seed list. Existing metrics must keep nonfreezing trials visible.
10. Minimalist: remove false implication/root-vote/answerer phrasing; define one missing arithmetic case. No new score, root accumulator, gate condition, timeout, eviction rule or sample policy. Do not redesign known limitations absent an author decision.
11. Skeptical paper reviewer: conformance iteration3's no-new-major conclusion cannot survive F1/F5. Review agreement is not a proof. Existing source tests/oracles validate historical contracts; they do not execute this new protocol.

Anchor check: all proposed rule edits preserve the latest strict full-K quorum, arrival-only votes, rescue abstention, simultaneous gate, immutable FINAL, whole-state Pending transfer and exact freeze predicate. F5's >=99%/1000/25 target remains intact. Sybil resistance remains deferred. I found no additional independently demonstrated severity>=8 defect beyond the initial findings that warrants another protocol change in this bounded round. F5 remains an unresolved severity8 minority finding and blocks a no-new-major/converged report.
