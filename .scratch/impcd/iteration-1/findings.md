# Snowstorm IMPCD technical adaptation — iteration 1

Operator: Shammah. Review date: 2026-10-26. Execution: Codex, using eleven explicitly separated technical perspectives. No subagents or separate human expert review were used. Apply the operator's technical adaptation of IMPCD v2.1.1: weight is **severity × confidence**; correctness follows concrete scenarios, not votes. No structural premiums, moral-pattern catalog, COI adjustments or social-participation workflow is used.

## Inputs and authority

Original proposal SHA256: `cc2f7342d0df701747ad641a8fd074f8e1b7639a34d83ba1be4865cd9ab49d9b` (76,234 UTF-8 bytes, 326 lines).

Original test-plan SHA256: `8a154aaa91ab851a4f59866534254cc9d80cbabab7f4a9707fcf55534463a61d` (61,492 bytes, 458 lines).

Unchanged controlling input bundle SHA256: `4bb4cc4d8d0aa76c92e905002dabd051c76fca8ef114f6bdd9318a853eaeff76` (36,008 bytes, 318 lines). Original conformance record SHA256: `dfc545d56f8e34de968e570ff1c256aeec261e55810d5c02eaa08d8050b88f50`.

Skill: `/Users/shammah/repos/conceptual-refinement/skills/impcd/SKILL.md`, SHA256 `2e99f00dc0802fe274122c01330161e84f3572449b788dc652e2b77cdbf4a047`. Complete authoritative runtime: `methodologies/iterative-multi-perspective-debugging-v2.1.1-runtime.md`, SHA256 `d6ab45ee703f4228adf112c9d7d6e7f45c877c4218f63f877edca8b5bcf7290a`. The required template in that runtime is superseded by the operator's technical adaptation; its optional moral overlay is not loaded.

Read the four requested draft/input files, applicable repository instructions, public contract headers, deterministic harness/transcript, independent field/schedule/model oracles and self-tests, all acceptance files, supplemental voting tests and CMake freeze/separation/process tooling. Parent baseline: `4e344d273a753fba88c81bdcc30b193c79c515fe`. Source baseline: `4cb465f6ec1e24d752f2c10cf0241e0ea7e31a63`. Existing manifest SHA256: `4aa896175e94e472f645c2d7ca25552a3efb079a789dd8aaca203b0e318906db`.

The operator subsequently authorized in-place regeneration, supplied three corrections, withdrew the finite-magnitude amendment, and replaced both scalar item and root accumulation with round-count item state. `accepted-changes.md` records this precedence. Findings marked resolved refer to the reviewed original wording and its original digest; open findings refer to the regenerated proposal. Frozen source files and their manifest are unchanged.

## Eleven-perspective feedback

Scores rate each perspective's principal concern, not voting power over correctness. Stances concern readiness of the executable contract after the accepted corrections.

| Perspective | Written feedback | Severity | Confidence | Weight | Stance |
|---|---|---|---|---|---|
| Coding theorist: finite fields/BCH/decoding | A zero syndrome is not arbitrary-set membership evidence; preserve the algebraic counterexample after removing partial votes. | 8 | 10 | 80 | Supports reversion; retains fingerprint limits |
| IBLT/set-reconciliation researcher | Reconstruct DIFF from raw captured IDs; also reconcile the prefix cap with the schedule's maximum index. | 8 | 10 | 80 | Requires structural fixes |
| Distributed-consensus researcher: Snowball/Avalanche | Correct full-K tails do not calibrate adaptive smaller-Kx observations; do not inherit a Snowball theorem. | 9 | 10 | 90 | Not ready for security claims |
| Bitcoin Core/lotusd P2P developer | wanted is a request but the API lacks a complete body-send/receive binding; honest body-removal races must be specified. | 9 | 9 | 81 | Blocked on host contract |
| Red-team attacker | Exercise fixed-population equivocation, selective responses, fake Pending and near-threshold manipulation without relying on Sybils. | 9 | 10 | 90 | Requires adversarial calibration |
| Liveness/formal-methods reviewer | Empty-W and beta_round=1 contradict an unrestricted no-one-round-freeze statement. | 9 | 10 | 90 | Concrete blockers remain |
| C++ implementer | Define FINAL/streak behavior across threshold changes and preserve atomic integer boundaries and actual capacities. | 8 | 10 | 80 | Needs deterministic transitions |
| Test engineer | Consolidate active requirements; keep historical test names as provenance without reviving old root/item score policies. | 8 | 9 | 72 | Supports regenerated plan; open cases block freeze |
| Network/measurement engineer | Repeated samples of one fixed neighbourhood remain correlated; wanted bytes and one-way delivery belong in host accounting. | 8 | 9 | 72 | Requires scoped measurements |
| Minimalist/deletion reviewer | Delete partial witness state and the root accumulator rather than repair them with new mechanisms. Keep unresolved choices explicit. | 7 | 9 | 63 | Supports accepted deletions |
| Skeptical paper reviewer | Separate arithmetic verification, operational protocol rules, probabilistic assumptions and demonstrated node behavior. | 9 | 9 | 81 | Rejects unsupported guarantees |

The perspectives differ in coding soundness, protocol liveness, statistical validity, implementation cost and evidence requirements. No design preference between correct alternatives was selected by vote in this iteration: the applied choices were supplied by the operator. The >60% preference threshold is therefore not invoked; correctness findings cannot be outvoted.

## Findings, sorted by severity × confidence

### F01 — Captured-candidate DIFF reconstruction prevents reversible recovery

**10 × 10 = 100; blocker; resolved in place by operator correction.** Lead: consensus/IBLT.

Original §6.1: “W_j=((round capture candidates minus wanted) union missing) minus exclusions.”

**Scenario:** poller captured raw R={x}, captured W={}, peer raw R={x}, peer W={x}, peer exclusions={}. Roots differ, but raw sets agree, so the valid DIFF has empty missing/wanted lists. The original expression yields W_j={} and votes no for x even though the peer includes x. Repeating that exchange prevents the locally excluded item from recovering through honest DIFF observations.

**Smallest fix:** substitute captured raw R for captured candidates. Add the exact excluded-local/included-peer YES regression. No new mechanism.

### F02 — Partial item voting can reverse the round and a zero cell is forgeable evidence

**9 × 10 = 90; major; resolved by deleting partial item votes.** Lead: red team/coding/consensus.

Original §8: “It votes yes for a nonexcluded item if some received index>=1 included by that item's schedule has a zero cell after peeling”. Controlling input, final voting amendment item 3: “abstentions weaken the evidence rather than inflate it.”

**Selection scenario:** D=32, M0=19, M1hat=26, eight observations with one yes and seven no give H1 mass `C(26,1)C(6,7)=0` and H0 mass `C(19,1)C(13,7)=32604`; the round sign is OUT. Hide those seven no observations in partial remainders: Kx=1,Yx=1 gives `log2(26/19)=+0.4525122046975067`, hence IN. Relative-to-D scoring does not prevent this sign reversal.

**Independent zero-cell witness:** take own Ref={576,577,578,579}, peer raw set={580,581,582,583,3,4,6}, exclusions empty, received prefix [0,2). All IDs 576..583 include schedule index 1; IDs 3,4,6 do not. In GF(2^64), the XOR of each of x, x^3 and x^5 over 576..583 is zero. Residual index 1 is exactly zero. Index 0 is `(count=3,s1=1,s3=55,s5=595)`, which is neither Zero, One nor Two; the reply remains partial. The removed criterion votes yes for own ID 576, which the peer lacks. Raw counts remain structurally compatible with the two sets. This is an algebraic chosen-ID counterexample, not a demonstrated search for prescribed transaction-hash preimages.

The operator additionally supplies the one-adversary fake-Pending corruption route as the accepted attack rationale. No end-to-end simulator trace for that route is claimed here.

**Smallest fix:** no partial yes **or no** observations; every still-undecoded reply abstains on every item. Preserve bounded partial fetching and rescue. No witness bitmap or end-round partial-vote recomputation is needed. Add incomplete/adversarial/rescue regressions. This does not authenticate full sketches or solve every fingerprint alias.

### F03 — Reference-table error does not cover the actual item classifier

**9 × 10 = 90; major; OPEN Q9.** Lead: consensus/red team/paper.

Regenerated §8: “Compute p_error=max(Pr[Y<y_star | Hypergeom(D,M1tx,K)], Pr[Y>=y_star | Hypergeom(D,M0,K)]).” The actual vote uses “L(Yx;D,M0,M1hat,Kx)>=0”.

**Scenario:** D=500, M0=300, M1hat=500, Kx=1. Under the null, one yes occurs with probability 300/500=0.6 and votes IN. The accepted full-K table gives beta_round=2 from p_error≈0.0019813. Two independent IN observations under that null occur with probability 0.36, not p_error squared. The adaptive classifier and effective sample differ from the calibration. This is not itself a full-node split-freeze proof. Fixed-neighbourhood/response correlation further prevents assuming independent successive errors.

**Smallest fix:** retain the accepted operational formulas, explicitly restrict the stated tail calculation to its hypothesis/full-sample model, and require an author decision on the intended error claim. Do not silently substitute another threshold or an SPRT. Add the small-Kx counterexample and adversarial selection campaign. A calibrated guarantee needs additional analysis; changing wording cannot supply it.

### F04 — A supported population derives a one-round FINAL threshold

**9 × 10 = 90; major; OPEN Q8.** Lead: formal methods/implementer.

Regenerated §8: “beta_round=ceil(Btx/(-log2(p_error)))”. Test requirement: “No freeze occurs after a single round, even if every sampled peer matches.”

**Scenario:** D=1024, beta_adv=0.2, epsilon=1e-9 gives K=256, M0=614, M1tx=820, y_star=182, p_error≈0.000018418211347980182 and beta_round=1. For nonempty initial W, one all-MATCH round votes IN, sets c=1, and satisfies FINAL. This violates an unrestricted no-one-round requirement within the existing D<=1024 bound. D=1 also gives p_error=0 and an unspecified endpoint for the expression.

**Smallest fix:** the author must define the endpoint/population scope or amend the derived rule. Do not insert a minimum threshold or narrow D silently. Retain a failing-boundary requirement distinct from the passing five-row table test.

### F05 — Empty W bypasses every item-finality wait

**9 × 10 = 90; major; OPEN Q12.** Lead: liveness/formal methods.

Regenerated §8: “freeze iff every item in W is FINAL with preference in”; “Items outside W and live fetches do not block freezing.”

**Scenario A:** an epoch starts with W empty and peers connected. Every item in W is FINAL-in vacuously; a first matching round can freeze. **Scenario B:** start W={x}, beta_round=7, p=in, zero counters. First round votes OUT, d[out]=1>d[in]=0, p becomes out and x leaves W. W is now empty although x is not FINAL. The same universal predicate allows a first-round empty freeze.

**Smallest fix:** specify the intended empty-set behavior or qualify the no-one-round claim. A guard, delay or dummy item would be an added mechanism; none is approved or inserted here. No root accumulator is reintroduced.

### F06 — Item/capture lifetimes and admission preferences are incomplete

**9 × 9 = 81; blocker; OPEN Q3.** Lead: P2P/consensus/test.

§6.1: “A currently admitted ID is eligible only for its captured admission sequence”. New §8: MATCH votes no for “every other item in captured R union Pending”. Initialization: “fresh ordinary admissions initialize preference in”; fresh Pending initializes out.

**Scenario:** x was not in captured R, enters live Pending before reply processing, acquires counters and preference out, then is admitted before round end. The old admitted-capture test excludes x; live-Pending transfer includes it; fresh-admission preference in conflicts with preserving the prior out preference if applied indiscriminately. A different trace removes/readmits x after capture; votes for its old lifetime must not leak. MATCH also now requires capture-time Pending identity while the old capture contains only M admitted records.

**Smallest fix:** one explicit observation-eligibility/lifetime table, one fresh-versus-transferred admission rule, and a bounded capture-time Pending representation. Do not retain dead item histories, duplicate peer/item observations, or K copies of the capture. Existing fields may suffice, but their exact lifetime predicate must be stated before coding.

### F07 — wanted has no complete host effect/callback contract

**9 × 9 = 81; blocker; OPEN Q4.** Lead: P2P developer/network/implementer.

§6.1: “Proposed public output is SendBodies{peer,short_ids}”; §1 currently lists only Send, FetchBody, Frozen, PeerMisbehaved and ScheduleTimer and requires a token for body results.

**Scenario:** a responder sends DIFF wanted={x}. The poller must send x without getdata, but no current action performs that effect and the receiving core has no specified token/reservation for the arriving body. If the poller removed x after its capture, even its available body is unspecified. Ad hoc FetchBody duplicates the request; pretending a token exists violates binding; waiting forever leaks support.

**Smallest fix:** specify the single host-send action and sender lookup/race semantics, and explicitly choose either ordinary validated host admission or bounded token-backed awaiting delivery at the receiver. The former avoids new speculative receive state; the latter must justify the extra mechanism and charge it. No alternative is silently selected, and no body validation is bypassed.

### F08 — The byte-derived cell cap exceeds the schedule domain

**8 × 10 = 80; major; OPEN additional structural repair.** Lead: IBLT/C++.

§6.5: “max_symbols_per_reply=min(floor((B−H_poll)/28),floor((B−H_reply−8*M)/28))”; “max_symbol_index=min(2^39−1,64*M+4096) is unchanged.”

**Scenario:** M=1 gives max_symbols_per_reply=74894 but max_symbol_index=4160. A permitted n=4096 prefix followed by an ordinary stalled/censored hostile reply requires doubling to n=8192, within the byte cap but past the encoding domain. This conflicts with range rejection and the required growth-to-cap test. Syntactically valid undecodable cells can trigger the growth; a successful honest one-ID decode is not required for the counterexample.

**Smallest fix:** constrain the shared usable prefix cap by `max_symbol_index+1` as well as bytes, or deliberately change the schedule domain and reverify its bounds. The minimum in the cap is the smaller edit; not applied because this regeneration applies the operator's selected changes only. Cover M=1, the exact endpoint and doubling across it. No iteration budget or new sizing constant is needed.

### F09 — FINAL state is undefined when the derived cap changes

**8 × 10 = 80; major; OPEN Q10.** Lead: C++/formal methods.

§8: “consecutive count c capped at beta_round”; “The item is FINAL when c=beta_round and that vote side equals preference.”

**Scenario:** c=6 under beta_round=7, then D changes so beta_round=4. Preserve c and it exceeds its cap/equality condition; clamp it and FINAL can arise without a new vote; reset it and accumulated progress is lost. An already FINAL item whose threshold rises is another unspecified case. Post-FINAL counter/preference updates are also not fully defined.

**Smallest fix:** an explicit population-transition and post-FINAL rule, including whether FINAL is lifetime-absorbing. No separate root state is needed. Do not silently clamp, reset, grandfather or unfinalize records.

### F10 — DIFF validates wanted against capture but omits the dual missing check

**8 × 9 = 72; major; OPEN additional structural repair.** Lead: IBLT/P2P/test.

§6.1: “Validate list lengths,ascending order,nonzero IDs,disjoint missing/wanted, wanted membership in the poller's SENT raw set, and count relation set_size=sent_set_size+missing_count−wanted_count”.

**Scenario:** M>=2, captured raw R={x}, missing={x}, wanted={}, exclusions={}, claimed peer set_size=2. All enumerated tests pass: wanted membership is vacuous, the lists are disjoint, and 2=1+1. But reconstructed raw peer set remains {x}, cardinality 1: missing cannot contain something already in the sent set. Similarly an exclusion outside the fully reconstructed DIFF raw set is an internal contradiction, not an authentication issue.

**Smallest fix:** reject `missing intersect captured raw R != empty`; validate exclusions against the asserted reconstructed raw peer set when a complete DIFF provides that set. Use captured raw R, not current R/Pending. No cryptographic commitment or extra history is needed. Add exact malformed-list cases before effects.

### F11 — Gate iteration order changes which items enter

**8 × 9 = 72; major; OPEN Q1.** Lead: formal methods/minimalist.

§8: “c is at least the mean c of the items in W”; gate order and empty mean are explicitly open.

**Scenario:** after item updates W has c values {0,10}, with two outsiders of c=10 and c=5, both preference in. A single old-W mean is 5, admitting both. Sequentially admitting c=10 first raises the mean to 20/3, rejecting c=5. Starting W empty leaves the denominator undefined.

**Smallest fix:** define one ordered round-end membership transition and an empty-W value. A simultaneous snapshot mean avoids a new iterative gate, but the author must choose it. The replacement amendment already resolves post-freeze reentry; do not preserve an obsolete epoch latch.

### F12 — “Fetch each body once” conflicts with honest-donor recovery

**8 × 9 = 72; major; OPEN Q5.** Lead: P2P/test/liveness.

§6.1: “fetched once from the first valid reply naming them”; §6.4: “Retry known alternatives immediately.”

**Scenario:** first donor names x then returns not_found; an already known honest alternate has x. A lifetime interpretation of once prohibits retry and fails the retained T10 recovery requirement. Live-attempt deduplication permits recovery.

**Smallest fix:** say once means at most one simultaneous in-flight/awaiting operation, while preserving bounded alternate-donor retry and timestamp ownership. If lifetime-once is actually intended, explicitly acknowledge the liveness/test change rather than weakening recovery silently. No new retry protocol is proposed.

### F13 — DIFF-only sizing discards its exact samples

**7 × 9 = 63; major; resolved by operator correction.** Lead: IBLT/network/test.

Original §6.3: “A round containing only MATCH,REPLY_DIFF or silence keeps the previous request n”.

**Scenario:** a previous oversized prefix is 1024; every timely DIFF reports an exact small difference whose normal table-cost argmin is smaller. The original hold rule preserves 1024 despite available exact samples, contradicting the normal estimator path. DIFF is a success, so zero-decode doubling does not justify the hold.

**Smallest fix:** restrict hold to no-sample MATCH/silent rounds, run the normal estimator for DIFF samples, and keep both doubling predicates unchanged. Add an independent-table shrink regression; no generated sizing table was needed or produced in this review.

### F14 — The core cannot observe wanted body-byte counts

**6 × 10 = 60; moderate; OPEN host accounting clarification.** Lead: network/minimalist.

§10 requires “wanted-triggered body bytes” in core Stats. §1's opaque TxHandle exposes txid, tx_hash and short_id, not serialized body length; the wanted host action does not return actual transmitted bytes.

**Scenario:** the core emits the same ID request whether the host transmits a body, has already removed it, drops the send, or delays it. Those outcomes have different actual wire bytes but no specified core callback distinguishes them. Reporting IDs multiplied by a guessed body size invents bytes.

**Smallest fix:** core Stats counts wanted IDs/actions; actual wanted body bytes and its one-way service/delivery timing belong to the host/evaluation ledger. Do not add a new callback only for this metric. Keep modeled body traffic distinct from measured native traffic.

## Technical integrity checks and evidence boundary

- No decided architecture was reopened without a concrete internal counterexample. Retain stateless one-shot polls, raw two-way dissemination, DIFF/2n fallback, provisional quarter-population sampling, and host push scope. The operator explicitly replaced the earlier partial-vote and root/item scoring choices.
- Primary research references were consulted for attack-review context: [the original Snow protocol paper](https://arxiv.org/abs/1906.08936) and [Kniep et al., Quantifying Liveness and Safety of Avalanche's Snowball](https://arxiv.org/abs/2409.02217). Their protocol/model-specific results are not Snowstorm proofs. The latter studies adversarial liveness and safety, motivating fixed-population adaptive attacks as well as identity attacks. [Karp et al.](https://archive.cone.informatik.uni-freiburg.de/pubs/rumor.pdf) motivates dissemination analysis, not this confidence mechanism.
- Exact combinatorial and finite-field/schedule arithmetic above was executed independently in Python without production code. No full acceptance, ASan/UBSan, source build, mainnet node, simulator or statistical campaign was run. No fake success, table generation, source promotion, freeze or hash rebaseline is claimed.
- The regenerated test plan preserves prescribed counts and the complete original frozen-case inventory while deleting superseded active policy tables. Future executable-contract work must explicitly migrate the old three-kind/session API, harness and tests; old passing arithmetic does not establish conformance to this new four-kind/round-count proposal.

## Iteration termination

**STOP: iteration-1 handoff required by the operator. Not converged.** This iteration has new blocker/major counterexamples. Do not start a new panel or claim convergence until the owner has applied/decided the open fixes. This is iteration 1 of the maximum 4, not four iterations of the same unchanged draft. Final byte-growth/hash measurements and validation results are recorded in the regenerated conformance record. If specification growth exceeds 20% from the baseline above, expansion runaway is independently a stopping condition. Semantic-similarity/stability claims are not manufactured for this interrupted, substantially revised first round.
