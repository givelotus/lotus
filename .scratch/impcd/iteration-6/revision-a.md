# Independent revision A — formal iteration 6

**Seven exact stable-ID operations proposed. Coherent/executable convergence is not possible yet: EW1–EW4 remain unresolved high-severity findings.** The operations correct two projection remnants and document demonstrated limitations/counterexamples; they do not select any author policy. Exact old/new bytes are in `revision-a.json`, checked against the latest ledger after its EOF-whitespace adjustment.

Reviewed the complete current spec/test renderings, common settings/findings, weighted-evidence.json, current ledger and ordered final input amendments1–15/style instruction. I retained the installed IMPCD v3 method and anchor plus eleven technical perspectives. No other reviewer's critique/revision was read. Only this formal revision pair was written. No source/frozen artifact edits, simulations, node acceptance, deployment or generated sizing table occurred.

## Finding dispositions

| Finding | Disposition | Severity | Confidence | Smallest authorized action |
|---|---|---:|---:|---|
| EW1 | Support | 10 | 10 | Preserve explicit unresolved arithmetic; author decision required |
| EW2 | Support | 9 | 10 | Preserve explicit FINAL/preference question; author decision required |
| EW3 | Support for provisional signed gate | 9 | 10 for trace | Preserve gate question and new overshoot consequence; no invented repair |
| EW4 | Support local opposite-FINAL counterexample; conditional root construction below | 9 | 10 local, 9 root preconditions | Record concrete case and keep hard failing safety oracle |
| EW5 | Support as documented liveness limit | 6 | 10 | Document D1 zero-weight consequence; no invented minimum D |
| EW6 | New mechanical advertised-A mismatch | 7 | 10 | Replace two leftover host-R operands with advertised A |

## EW1: support-zero evidence remains undefined

§8 S6_0718: “true H=0 gives e=+infinity”; S6_0719: “Opposing infinite contributions are undefined pending the author decision.” S6_0735 retains the three-success guard.

D16,K16,n16,y16 meets floor9 and the80% success threshold, but H0 because the null has only8 supporting peers. One IN round gives +infinity without FINAL; a subsequent OUT round requires +infinity−infinity before either side has3 successes. This is a valid-input transition, not a numerical-underflow corner. Exact rational tails in the common evidence agree with independent calculation. No cap, saturation, cancellation convention, skipped success or new null is authorized. The draft correctly leaves this open; no operation can repair its semantics without author input.

## EW2: FINAL/preference disagreement remains reachable with finite floor-valid votes

§8 S6_0724: “switch p only when d[s]>d[p]; a tie keeps p.” S6_0734 makes threshold-side FINAL immutable independently of prior preference. S6_0736 explicitly leaves their integration open.

Let a=ln286 from D16,n10,y8 and b=ln1430 from D16,n9,y8. Both meet floor9. Repeat [OUT of weight a, IN of weight b]13 times. Preference becomes/remainsOUT; each IN only ties the cumulative counts. After12 cycles S=12ln5<T, and intermediate OUT steps never reach−T. The thirteenth IN produces S=13ln5=20.9226928616433>T=20.7232658369464 with counts13/13 and pOUT. Thus FINAL-in can be permanently unable to pass a pIN gate. The mirrored trace produces FINAL-out/pIN. This independently verifies the common evidence without using withdrawn n1/n8 counting rounds. Aligning preference, changing the gate to read FINAL side, or another repair requires author choice.

## EW3: immutable overshoot and the gate

§8 S6_0740 provisionally interprets the gate using signed S; S6_0741 admits outsiders only with pIN and S>=mu. S6_0743 explicitly requests confirmation of that quantity. S6_0734 stops all evidence updates after FINAL.

Using a,b above, base z finalizes after3b=21.7962891697619. A later Pending x receives3 weak IN,1 strong OUT,2 weak IN. It remains pIN with counts5/1 and finalizes at5a−b=21.0145293308453>T but below base mean. It cannot enter on admission and cannot raise its immutable score afterward. Every round meets floor9; no infinity is involved. On a second node x can be in W from the beginning and finalize at that smaller score; z with the larger score can subsequently enter. Thus equal final sides do not alone force equal W under different admission histories. This is an additional consequence requiring disposition, not merely the signed-versus-positive-sum naming question.

The rendering wisely no longer asserts that every postfreeze entrant is FINAL-in. That old implication would also fail: after a base mean21.7963, change D=K to32; two IN successes with n17,y16 each have e=ln35357670=17.3810. The outsider can pass the gate with score34.7621 while still below the minimum3-success count. Existing freeze checks correctly prevent refreezing while that entrant is nonfinal. No claim correction is needed for this second behavior because the false old implication has been removed.

No operation selects a positive-only accumulator, clamps FINAL scores, forces entry, lowers a mean or permits updates after FINAL. EW3 remains open conditional on the current provisional signed quantity.

## EW4: majority-answer response conditioning still yields opposite FINAL

§8's counting rule and tail are exercised together with §6.6's earliest-ending timer; §11 S6_0892 currently calls fixed-population response selection a review obligation. T6_0064 retains hard zero false/split assertions.

Independent validation: D16,K16,floor9, a fixed responder population has8 YES and8 NO for x. Deliver all8 YES and1 NO at1ms, remaining7 NO at250ms. At1ms a strict majority has answered; the retained2*tMajority condition ends the round at2ms, before either the4ms fallback or slow responses. The majority answer floor resets the next fallback to the normal formula rather than doubling. Repeat three times. Each counted round has n9,y8; ceil(4*9/5)=8, H=1/1430, and e=ln1430. After three rounds (about6ms), S=21.7962891697619>T and countIN=3: FINAL-in. All nine are valid votes; there is no floor bypass and no support-zero arithmetic.

At a second poller, reverse the side-dependent delays:8 NO plus1 YES fast,7 YES slow. Three rounds give FINAL-out. The peers can be the same fixed identities and consistent in their item preference to both pollers. Thus the response subset is selected by directed timing, even though every peer was sampled and the sample-majority floor is met. No Sybil creation or Byzantine identity fraction is needed for the local counterexample.

A root-split fixture needs explicit preconditions, rather than confusing absent bodies with recorded FINAL-out. One concrete local-state construction is: both pollers have admitted x and a common base z; z is already FINAL-in and in W at both. x is a nonfinal epoch member of W at poller P, but is a recent admitted outsider below the gate at Q. Their respective advertised sets both contain x. Eight responder candidates include x and eight exclude/omit it during the three-round window. P receives the first timing schedule and reaches FINAL-in for x, keeping W={z,x}; Q receives the mirror and reaches FINAL-out, retaining W={z}. All needed x bodies at the pollers are already validated; no FINAL-in Pending veto applies. Ordinary DIFF/exclusion replies can encode the stated observations without relying on MATCH equivalence. No rescue-created vote is required. Body arrivals and responder state updates may be delayed beyond this6ms window, so fixed preferences during the window do not require fake identities. This is an explicit conditional state/timing construction; I have not executed a full-network reachability fixture from zero state or claimed a simulator result.

The eight/eight population is on the null boundary, not a strict opposing majority; call the mathematical issue rejection under the stated null/response selection, and the two-poller result opposite FINAL/root outcomes under the explicit preconditions. Do not overstate it as a demonstrated majority-absent freeze without these distinctions. The hard split oracle still requires disposition.

Operations add the concrete case to S6_0892 and T6_0064 while preserving zero false/split assertions: the adversarial fixture must report a failure, not redefine the split as success. Changing timing, quorum, null assumptions or safety thresholds remains an author decision.

**Operator's below-majority question:** under literal rule13 no new contribution/success can occur with fewer than floor(K/2)+1 valid target-item votes, and valid votes cannot exceed distinct answered slots. Therefore no first FINAL transition can be sourced by a below-majority-answer round; unchanged scores/counts cannot newly satisfy a predicate already evaluated after the earlier update. Duplicate/stale/lifetime filtering preserves the premise. EW4 uses nine valid answers, so this local invariant does not solve it.

## EW5: document the D1 limit without changing supported populations

§8 S6_0717 says “H=1 gives e=0.” At D=K=n=y=1, m1 and H1 for either side. The floor1 is met, but arbitrarily many successes leave S0. Since T>0 for every legal epsilon<1, a nonempty item cannot reach FINAL. Two-node candidate agreement can still hold; nonempty freeze liveness cannot be asserted from these formulas.

The one-operation clarification appends this exact consequence to S6_0717. It neither chooses a minimumD nor removes the two/five-node workload or weakens any hard safety assertion. D1 nontermination can remain a disclosed nonfinishing outcome; a requirement for eventual D1 nonempty freeze would require author revision.

## EW6: advertised-A regeneration missed two explicit operands

§6.1 S6_0307 still stores “send-time |R|” in each current-round slot, although §5 and wire setSize now use |A|. T6_0338 `T7PollDecodeReferenceExcludesPending` still says “inbound decode uses R only.”

Counterexample: host R={x,z}, x is FINAL-out, advertised A={z}. The POLL carries setSize1 and encoding{z}. An honest responder advertising{z} sends empty missing/wanted with setSize1. Recording sentSetSize2 from hostR would make the declared count check reject this valid reply. Separately, peeling the inbound POLL against hostR instead of A introduces a spurious−x difference and falsely advertises/fetches a terminal-omitted item.

Smallest rule12-consistent fix: S6_0307 stores send-time|A|. T6_0338 asserts decode against A, excluding retained FINAL-out bodies and Pending. These are mechanical operand repairs, not new stores, host removals or tombstones. Exact old/new operations provided.

## Integration, naming and scope checks

The derived A view otherwise consistently controls wire cells/setSize, raw capture, DIFF membership/cardinality, inbound decode and outbound Ref. Retained R still owns bodies/capacity and terminal state. Pending can receive remote YES but cannot generate a local outgoing YES; FINAL-in Pending veto is present. Probe fallback uses the transient existing estimator and RequiredSymbols with censor lower bound, without an inbound sample-bank mutation; the old probe-to-next-prefix transition is distinct and remains unchanged. Latest measured transfer time, sampled median/imputation, fallback, answer-floor backoff and early endings are stated. The observed EW4 uses those exact early endings, not a changed deadline.

C++ convention checked against the canonical daemon developer notes: CamelCase methods/functions, lowerCamelCase variables, m_ members, UPPER_SNAKE_CASE globals, lower_snake_case namespaces. Historical filenames, standard-library spellings and original frozen case names remain literal provenance. No style-only operation is proposed. Mathematical S versus renamed RequiredSymbols references should not be mistaken for new C++ APIs; this review does not add an API to resolve author-owned gate semantics.

Eleven-role coverage: coding theorist/IBLT researcher checked algebra/reference/projection and estimator ownership; consensus/liveness/formal checked EW1–EW5 and strict update eligibility; P2P/red team validated EW4's fixed-population timing; C++ implementer checked arithmetic totality and EW6 operands; test/measurement engineer separated exact arithmetic/local state traces from unexecuted acceptance and kept safety workloads intact; minimalist/anchor avoid unauthorized repairs; skeptical-paper reviewer rejects treating tail weights on selected responders as a proved sequential guarantee. No human panel or external experiment is implied.

## Completion assessment and minority report

EW1–EW4 survive with severity>=8 and cannot be averaged away. The draft exposes mathematical questions honestly, but exposure is not executable resolution. The seven proposed operations can improve precision and regression coverage; they cannot produce coherent/executable convergence while infinity arithmetic, FINAL/preference integration, gate interpretation/consequences and response-selected split behavior remain unresolved.

The requested K crossover remains intentionally deferred to the grid and is not itself a reason to invent a number. Implementation, frozen-artifact correction, independent oracle execution, sanitizers, simulator campaigns and network evidence remain future work. An empty or small consensus at this point must not be called convergence. Preserve the author disputes and stop/narrow according to the run settings pending concrete author answers.

## Post-submission EW7 — rule12 forbids terminal-OUT gate reentry

Independently validated the additional integration witness; severity8, confidence10. This repair implements already selected rule12 and does not resolve EW2 by choosing preference behavior.

S6_0741 currently says “admit held outsiders with p=in and S>=mu.” Physical host holding includes FINAL-out bodies, while advertised A excludes them. A FINAL-out/pIN outsider is allowed by the unresolved EW2 state rule: the mirrored13-cycle trace has S=-13ln5=-20.9226928616433. Let W contain only b, with two weak IN successes at D16,n10,y8 followed, after population changes to D=K=32, by two OUT successes with n17,y16. The latter weight is e=ln35357670=17.381025899897477. Both newer rounds meet floor17. b retains pIN on the2/2 tie and remains nonfinal because it has only2 OUT successes, although its score is2ln286-2ln35357670=-23.45006817815525.

The terminal outsider's score exceeds this negative mean, so the unqualified physical-held entry rule can put it back into W, contradicting rule12's mandatory terminal-OUT removal. Constraining entries to advertised A closes this exact route for every possible FINAL/preference integration. No scoring threshold, preference update, gate quantity or infinity semantics changes.

Added exact operations: S6_0741 “admit outsiders in advertised A”; T6_0057 retains its existing sketch/exclusion/body checks and adds the negative-mean terminal-reentry regression. This is a mechanical consistency repair under the chosen projection. EW1–EW4 remain unresolved; the overall convergence assessment is unchanged.
