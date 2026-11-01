# Independent formal revision B — iteration6

Reviewer: gpt-6.1-sol. The shared baseline is the current iteration6 ledger and complete SPEC/TESTS proposal, including weighted-evidence.json, settings/findings and ordered rules1–15 plus the naming instruction. Controlling input digest: `fb140f92e8287616f0979c4c1744863d88b0b9e2e9fa85afb3b3860c2515ce5c`. Prior preliminary analysis was independent; no other critic/reviser output was accessed. Only this report and revision-b.json are submitted. The latest whitespace-only ledger update does not change the exact substantive old-text matches used by the eight proposed operations.

The IMPCD skill/runtime from previous turns remains controlling. Naming convention checked against the canonical daemon developer notes: UpperCamelCase functions/methods, lowerCamelCase variables, m_members, UPPER_SNAKE_CASE constants and lower_snake_case namespaces; historical real filenames and case names remain provenance. No frozen/source/proposal edit, generated table, simulator run or implementation conformance is claimed.

**An executable, safety-complete fixed point is not available while EW1–EW4 remain unresolved.** Small wording/integration repairs do not close those findings. Mathematical or voting/timing policy choices are left to the author. The pending author answers are not inferred from elapsed time.

## EW1 — support; severity10, confidence10; concrete undefined arithmetic

S6_0718, §8 explicitly records “true H=0 gives e=+infinity” and no completion of opposing infinities. With D=K=n=16,y=16, the null population has eight successes and H=0 exactly. First IN success creates positive infinity but cannot finalize with one success. A following OUT success asks for positive infinity minus positive infinity, still before three successes. Both rounds meet floor9. The third-success guard cannot define the second transition. Preserving the OPEN marker is correct; the contract is not executable over its allowed message domain until the author selects arithmetic. No clipping, pseudo-count or restored LLR operation is proposed.

## EW2 — support; severity9, confidence10; finite terminal/preference mismatch

§8 preserves strict-count preference while FINAL is independently its reached evidence side; S6_0741 retains p=in for outsider entry. The common finite witness is valid under the new floor:

`a=ln286` comes from D16,n10,y8, H=1/286. `b=ln1430` comes from D16,n9,y8, H=1/1430. Both meet floor9 and80%. Start fresh Pending p=OUT and repeat13 cycles `[OUT(a), IN(b)]`. Each cycle adds b−a=ln5. Until cycle12, every score remains below T=ln1e9; on cycle13's IN success, S=13ln5=20.9226928616433>T. Counts are dIN=dOUT=13, so tie-retained preference is OUT, while FINAL is IN. All contributions are finite. My independently constructed longer floor-valid sequence yields the same defect, but the common shorter trace suffices.

An immutable FINAL-in with retained pOUT cannot satisfy the pIN entry gate, even after admission. The reached-side rule is explicit author intent, so restoring the old preferred-side condition would be wrong. FINAL-out now has an explicit W/A removal, which resolves that half of candidate membership; it does not resolve FINAL-in/pOUT entry. Preserve the author-choice dispute and the existing OPEN marker. No forced preference synchronization is proposed.

## EW3 — support conditional on signed-sum reading; severity9, confidence10

S6_0741/S6_0743 use the signed evidence mean and explicitly leave the interpretation open. Independently recomputed exact tails confirm the gate obstruction:

| Quantity | Value |
|---|---:|
| T=ln1e9 | 20.72326583694641 |
| a=ln286 | 5.655991810819852 |
| b=ln1430 | 7.265429723253953 |
| Frozen base score3b | 21.79628916976186 |
| Pending x final score5a−b | 21.01452933084531 |

x receives3 weak IN successes,1 strong OUT,2 weak IN. It stays nonfinal through the penultimate update, then has pIN,dIN5,dOUT1,FINAL-in. Matching admission preserves its score. With frozen W containing the base item, x's immutable score remains permanently below the mean. It cannot ever enter while that W remains. This is not EW2: here preference and FINAL already agree. On another poller where x entered before finalization, it can remain in W; terminal items can consequently agree while W differs.

The earlier uniform streak cap guaranteed identical terminal gate values; unbounded weight overshoot no longer does. Do not recreate that property by silently capping scores, using a positive-only accumulator, or bypassing the gate. The author must clarify the selected quantity and the intended terminal-entry consequence. Preserve the OPEN dispute; no policy operation is submitted.

## EW4 — support; severity9, confidence10; finite majority-answer selection

S6_0892, §11 already recognizes response selection but does not record this new floor-valid counterexample; T6_0064 requires hard zero false/split outcomes. The majority floor closes the original one-fast-voter failure. It does not make the valid-answer set uniform.

At D=K=16, eight YES peers plus eight NO peers form a fixed population. Make eight YES and one NO reply in1ms; the other seven NO replies arrive250ms later. Each round has n9, yYES8: floor9 and ceil(.8*9)=8 both hold. Its exact tail is1/1430 and weight b. Three such rounds give3b>T and three IN successes. Nine answers trigger the retained majority timing branch at2ms, so the item finalizes after6ms before any delayed NO. Deadline backoff never activates. This uses no infinity, subfloor contribution or Sybil identity.

A concrete opposing-item scenario uses two honest pollers P and Q sharing the same sixteen stable preference peers, eight including x and eight excluding x. Directed delays make P promptly receive its eight IN supporters plus one OUT peer, and Q promptly receive its eight OUT supporters plus one IN peer; each poller's other seven opposing replies are delayed250ms. These are real preference observations: all servers may have admitted x, with OUT servers listing it as an exclusion while nonfinal. Matching roots supply MATCH; different roots with decodable lists supply DIFF. The votes require neither an algebraic forgery nor pretending Pending is a YES source. Server preferences need remain unchanged only for6ms; they need not be terminal.

P starts with x held in W. Q starts with a live captured Pending x and an outstanding body operation whose completion is later than6ms. Received remote YES/NO may score that Pending lifetime. Three rounds make P FINAL-in and Q FINAL-out. Both are immutable. A common already-FINAL-in candidate z allows P to freeze {z,x}; Q may freeze {z}, because its FINAL-out Pending x is not the FINAL-in Pending blocker. The final per-item split persists even when body delivery later completes: Q's matching admission preserves FINAL-out. This is a possible legal state/event trace, not a claim that a binary or simulator executed it. The prior server preference states and baseline z can be established before the short trace; no fresh-epoch assumption forces all servers to begin with the same candidate preference.

Two minimal operations record the concrete OPEN EW-RESPONSE finding in S6_0892 and add its serialized two-poller regression to T6_0064. Hard zero false/split assertions remain unchanged; the counterexample is not averaged away or made passing through a weaker oracle. A voting/timing repair would require author authority and is not selected.

**Answer to the owner's precise below-majority question:** no newly reached FINAL can be sourced by a below-floor round under literal rule13, applied before all evidence/counter mutations. Valid per-item votes are deduplicated by selected peer and captured lifetime, so voteCount<=answeredPeers<=K. A below-floor round adds zero, increments no success counter and does not change the terminal predicate. Duplicate/stale replies and rescue cannot increase that count under the current eligibility rules. EW4 uses nine answers and is a different failure.

## EW5 — support as documented limitation; severity6, confidence10

D1,K1,n1,y1 gives null m1 and H1, hence e0. Any number of unanimous successful rounds leaves S0 and cannot finalize a nonempty initially nonfinal item for epsilon<1. The formula is defined. Proposed S6_0908/T6_0437 wording documents this exact limitation and retains nonfinishing reporting and the two-node workload. It does not invent a minimum D, new K crossover or special weight. A universal two-node eventual-freeze promise would remain false; the retained tests must report rather than hide that outcome.

## EW6-A-INTEGRATION — new mechanical misses; severity6, confidence10

Rule12 and S6_0203 define advertised A as admitted IDs excluding FINAL-out. Most regeneration correctly uses A, but S6_0307 still captures “send-time |R|”, and T6_0338 says “inbound decode uses R only”. These are internally inconsistent with the closed advertised-set rule.

Reproduction: responder retains host bodies {z,x}, with x FINAL-out. Then R={z,x}, A={z}; cells and setSize describe A. Peeling an inbound POLL against R instead of A introduces a spurious negative x and can produce incorrect DIFF lists relative to the poller's encoded set. A send-time R size of2 also disagrees with the actual sent setSize1 used for capture-based cardinality checks. Fix the two retained references to A, and explicitly include retained FINAL-out bodies in the test distinction. These are mechanical rule12 consistency operations, not an author-choice mechanism.

## Other integration checks and role coverage

Rule13 is applied before weighted success, including n0. Prefix fallback doubling remains separate from new estimate-based probe fallback. The latter uses RequiredSymbols and a transient estimator against responder A without adding inbound sizing samples. FINAL-out remains bounded body/state ownership in R while A, Ref, caches and exclusions omit it; no tombstone history is invented. Local own Pending is never advertised YES, but remote admitted holders may vote YES for the poller's Pending lifetime, enabling the explicitly required FINAL-in Pending guard.

Anchor preserves rules1–15 and pending choices. Coding/IBLT perspectives retain primitive arithmetic, invariant residuals and nonauthentication limits. Consensus/formal perspectives validate EW1–EW3 with exact finite or zero-tail arithmetic. P2P/red-team/measurement perspectives validate EW4's fixed identity set, transfer delays and conditional answer composition. C++/test perspectives identify EW6 and preserve exact workloads, three-success tests, no-reset behavior and naming. Minimalist rejects invented policy repairs; skeptical-paper review rejects interpreting the hypergeometric tail as an established sequential guarantee under selection. Perspectives are analyses, not independent recruited experts.

The eight exact replacements in revision-b.json answer EW4, EW5, EW6 and the additional EW7 below. EW1/EW2/EW3 remain explicit high-severity disputes; recording EW4 does not fix it. Therefore mathematical totality, terminal membership consistency and safety-complete document criteria are not all answered, and executable/coherent convergence cannot be declared. The intentionally deferred K crossover remains an experiment parameter; it is not the reason convergence is blocked. No freeze, acceptance, empirical security or performance result is claimed.

## Additional EW7 — FINAL-out reentry through physical held-set gate

**Severity8, confidence10; independently validated finite counterexample.** S6_0741 says to “admit held outsiders with p=in and S>=mu”. Physical R retains FINAL-out bodies, so this entry set is wider than advertised A. The simultaneous removal of FINAL-out members does not protect an outsider added in that same gate evaluation.

Use the mirrored finite EW2 construction to create a retained outsider x with Sx=−13ln5=−20.922692861643302, preference IN and immutable FINAL-out. It correctly left A and W under rule12, but remains held in R.

Let W contain only b. At D16,K16, two weak IN successes give b score2ln286 and dIN2. Change the connected population for subsequent rounds to D32,K32 and give b two OUT successes with n17,y16. Each meets the answer floor17 and80% threshold14. The exact null tail is16/C(32,17)=1/35357670, so each weight is ln35357670=17.381025899897477. b ends at Sb=2ln286−2ln35357670=−23.45006817815525, dIN=dOUT=2 and preference IN retained by the tie. It is nonfinal because it has fewer than three successes on either side. b therefore remains the sole prechange W member, with this negative mean.

Now Sx>mu and px=IN. The literal physical-held outsider condition admits x back into W despite its immutable FINAL-out state and its mandatory omission from A. No infinity, author-undefined arithmetic or subfloor update appears. This violates the already selected rule12 independently of the open question about FINAL-in/preference synchronization.

The smallest consistent repair changes S6_0741's entry domain from held outsiders to outsiders in advertised A, retaining pIN and S>=mu unchanged. It adds no terminal-score clamp or new preference policy. T6_0057 receives the negative-mean regression requiring retained FINAL-out never to reenter W. These two exact operations were appended after independently recomputing the tail and score ordering; all eight operations were revalidated against the current common ledger.
