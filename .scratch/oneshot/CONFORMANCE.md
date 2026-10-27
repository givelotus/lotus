# Snowstorm proposal conformance — evidence-weighted amendment, iteration 6

Updated the existing SPEC-PROPOSED.md and TESTS-PROPOSED.md in place. All operator messages were appended verbatim, in order, including the main weighted-round amendment, rules10–12, exact Rule10, rules13–15 and C++style instruction. Earlier review histories remain unchanged. No source or canonical-parent change.

## Input authority

Current bundle SHA256 **`fb140f92e8287616f0979c4c1744863d88b0b9e2e9fa85afb3b3860c2515ce5c`**,54,599bytes. The previous49,197byte prefix and its digest remain unchanged. Intermediate hashes/messages are in iteration-6/author-amendment.json. Latest input is pinned in both proposals.

## Applied amendment and naming

Weighted successes use80%of valid item votes, subject to n>=floor(K/2)+1. Add signed natural-log hypergeometric-tail evidence without resets; require at least3same-side successes for reached-side immutable FINAL. The old streakc/beta/reset policy is removed. The gate compares evidence under an explicitly unconfirmed signed-sum reading; missing mathematical choices are not invented. FINAL-in Pending vetoes freeze and retains ordinary fetch/donor/admission lifecycle. A node never advertisesYES for its own Pending, but may receive remoteYES for that lifetime.

At smallD poll allD; the crossover toK<D remains OPEN for the(f,K)grid. Exact deadline uses4*captured sampled upper median of latest complete POLL-to-reply measurements, transfer included, with specified imputation/bootstrap; below-majority answered rounds double next duration, majority-answer rounds restore formula. Probe fallback uses the existing difference estimator and RequiredSymbols, not twice the largest probe index. FINAL-out leaves derived advertisedA and W, never enters exclusions or receives further votes; physicalR retains bounded body/state ownership. Gate entries are restricted toA, including under a negative mean.

Requested root developer-notes path does not exist. Read the complete canonical `/Users/shammah/repos/lotus/daemon/lotusd/doc/developer-notes.md`; source hash/mapping recorded in iteration-6/naming-map.json. Convention: **UpperCamelCase functions/methods, lowerCamelCase variables, m_members, UPPER_SNAKE_CASE constants, lower_snake_case namespaces**. Both proposed C++ interface and active test identifiers updated; real paths/std spellings/exact historical source references retained as provenance. No frozen C++file renamed or edited.

## Independent review and actual status

Separate gpt-6-astra and gpt-6.1-sol formal revisions reviewed the same ledger/brief/input without seeing each other's output before submission. All11technical perspectives plusanchor documented, including fixed-population attacks. Both also independently validated a shared post-review terminal-reentry witness. Model consensus is not human-expert or execution evidence.

Accepted7shared claim repairs: physicalR operands→advertisedA, terminal gate filter and negative-mean regression, documented D1zero-weight nontermination, and explicit majority-answer selection counterexample/regression. Shared repair direction agrees; raw location disagreement3/9=0.333333 within tolerance0.50. Current renderings match ledger-accepted.json; metadata and substantive operations separated in decision.json. No locks added.

**Not converged;1of8permitted run iterations completed.** EW1–EW4 remain severity>=8 and require the author definitions already requested. The next scope is arithmetic EW1 once its definition arrives. Repeating unchanged missing choices cannot supply a corrective iteration or justify a fixed point; cap is not claimed exhausted. No growth/oscillation stop or cutback occurred.

## Still open

- **EW1:** full-population successes have H0,e∞; opposing successes before the3guard give undefined infinity-minus-infinity.
- **EW2:** finite floor-valid histories can reach FINAL-in with retained pOUT, or FINAL-out with pIN; terminal preference/gate integration is unspecified.
- **EW3:** gate quantity “IN-side sum” needs confirmation. With signedS, an immutable FINAL-in outsider at21.014529 can remain below frozen mean21.796289 forever.
- **EW4:** nine answers biased8:1 meet the floor; three rounds can produce opposite immutable FINAL at honest pollers with mirrored delays. Hard zero false/split assertions remain unchanged; no hidden response-independence assumption.
- **K crossover:** intentionally deferred to the named experiment, no number selected.

D1,H1,e0 implies nonempty nontermination; documented limitation rather than an invented minimumD or special weight.

**Requested fewer-than-majority attack report:** none reaches a new FINAL under literal rule13: valid per-item votes<=answered peers, and below-floor rounds update neither sum nor successes. The one1msYES/fifteen250msNO scenario now doubles deadlines until NOs count, then reachesOUT in the independent rule trace. EW4 has9answers and remains a distinct safety failure.

## Verification and limits

PASS: exact rational-tail/80digit log vectors and implied same-side rounds for D16,32,64,128,500 with allK/halfK; full-population and quarter-population K are declared arithmetic fixtures, not a chosen crossover. HalfK is below floor: contribution0/no success/no final. Verified finite preference/gate witnesses, majority-floor inequality and rule15timing trace;27ledger/input/inventory/naming/patch-integrity checks. All104historical source inventory rows and mandatory workload counts retained. Review patch regenerated/applies; Markdown/Python whitespace passes.

No current-protocol node acceptance, sanitizer, simulator, generated sizing table, frozen-artifact migration, source freeze, publication, deployment or human panel. Existing frozen sources implement an older contract. Acceptance-manifest SHA256 remains `4aa896175e94e472f645c2d7ca25552a3efb079a789dd8aaca203b0e318906db`; canonical parent remains unchanged. Exact arithmetic/local event traces are not a full-network implementation result.

SPEC SHA256 **`8ed2ff8fd3617fcef1668bd25745e492d07c9fc894c532cc9d605ccb98e784f0`**,81,190bytes. TESTS SHA256 **`f620ba544bb9290ec1644bd67a21539aa8dbb97b8281c6e1f4ed12ba9dc2efa2`**,55,535bytes. Findings, minority report, accepted changes, both revisions and ledger history are under `.scratch/impcd/iteration-6/`.
