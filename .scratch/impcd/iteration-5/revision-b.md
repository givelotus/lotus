# Independent revision B — iteration 5

Reviewer: gpt-6.1-sol, independent context. I read the current complete specification and test proposal, iteration-5 settings and critique brief, and the maintained input bundle including its two final operator resolutions. The bundle digest is `fb84e15abe521460cd55f65f693835b8047be070075191729fe07df0128e9d96`. I checked that concatenating every ledger claim reproduces the current documents exactly: SPEC 77,983 bytes / 911 claim fragments; TESTS 54,057 bytes / 406 claim fragments, all open. The IMPCD v3 runtime and skill read for iteration4 remain controlling. I did not access any revision-A output. Only this report and `revision-b.json` were written.

**No new concrete internal defect was established. The proposed operation list is empty.** No source implementation, frozen contract, proposal, input bundle or manifest was changed. There was no simulator run or implementation conformance test.

## Independent validation of the amended gate

Relevant claims are S0718–S0719, S0731, T0052 and T0067. S0718 now defines “gate_value[x]=c[x] if the previous success side is IN, and 0 otherwise”; S0719 uses this value for entry and the prechange W mean. S0731 states that an entrant into nonempty frozen W is FINAL-in. T0067 includes the former counterexample and its repaired outcome.

I independently replayed the old witness from fresh Pending preference OUT using the current state update rule:

| Newly applied successes | d[IN] | d[OUT] | Preference | c | Previous | FINAL | gate_value |
|---|---:|---:|---|---:|---|---|---:|
| IN × 11 | 11 | 0 | IN | 11 | IN | false | 11 |
| OUT | 11 | 1 | IN | 1 | OUT | false | 0 |
| IN × 11 | 22 | 1 | IN | 11 | IN | false | 11 |
| OUT × 12 | 22 | 13 | IN | 12 | OUT | false | 0 |
| Preserve state on admission, then OUT | 22 | 14 | IN | 12 | OUT | false | 0 |

The former nonfinal entrant is now blocked by a frozen nonempty W with mean twelve. Eleven subsequent IN successes yield gate eleven and remain blocked. The twelfth gives `(p=IN,dIN=34,dOUT=14,c=12,previous=IN,FINAL=true)`, passes the gate, and changes the root. This agrees exactly with T0067. Matching Pending admission neither changes preference nor invents finality.

The restored implication is sound while W remains nonempty and frozen: immutable FINAL-in members have c=beta_c and previous=IN, hence mean gate value beta_c. Every gate value is at most beta_c. An outsider passing that mean must have c=beta_c, previous=IN and p=IN. The same successful update that established this conjunction sets FINAL; no later update can remove it. Thus the entrant is FINAL-in. A host removal that empties W invalidates that nonempty freeze before the empty-mean rule applies; an entry into subsequently empty W need not be final, and the separate freeze predicate already handles this case.

No-success rounds reset nonfinal c to zero, so retaining previous=IN across the gap does not retain a positive gate value. The next success begins at one. FINAL-in ignores no-success/opposite updates and therefore keeps its gate value beta_c. Empty W has mean zero, allowing a fresh admitted IN item with zero confidence to enter; it cannot freeze until it satisfies the unchanged FINAL condition. These are selected operator semantics, not defects requiring an extra gate.

I also executed an independent bounded state exploration, starting from fresh IN and OUT lifetimes. It enumerated every reachable item state through forty rounds under IN, OUT and no-success outcomes, with beta_c=12: 16,114 states at depth40 and 555,690 transitions checked. It asserted that `(p=IN and gate_value>=12)` implies FINAL, every FINAL-in retains gate value twelve, every nonfinal no-success result has gate zero, and every FINAL update is a no-op. All assertions passed. This checks item-state arithmetic only, not network agreement or a protocol implementation.

## F5 disposition and hard safety assertions

S0795, T0028 and T0264 implement the final operator choice: retain the 1000 fixed-seed silent/slow fixture, extend its observation horizon enough to finish, report freeze-round distributions and nonfinishing trials, and retain zero false freezes and zero split freezes as hard assertions. The obsolete 99%-within25 acceptance target is explicitly removed. This closes the earlier authority dispute; no new target or seed-selection policy is proposed.

A reporting horizon and exact false/split metric estimands still have to be fixed and printed for actual experiments, as §9 already requires before simulator evaluation. That is an acknowledged experiment-input obligation, not missing core-state semantics or permission to weaken a safety assertion. Hard zero-failure acceptance criteria do not establish that the protocol meets them before tests are run. Nonfinishing outcomes must remain visible. The old 25-round probability calculation is historical motivation only and is not reused as a current acceptance oracle.

## Whole-contract review and perspectives

The initial brief supplies no new presupposed defect. I revisited all current contract sections and retained workload rows against the ordered operator rules. No finding with severity/confidence scores is opened because no concrete contradiction survived this pass. The following coverage records the analyses rather than inventing votes or independent experts:

- **Anchor:** preserved both latest operator decisions, strict full-sample quorum, arrival-only observations, rescue abstention, captured lifetimes, simultaneous gate, immutable FINAL, Pending transfer and all required workloads. No attempted reversal of settled choices.
- **Coding theorist:** checked the field/cell/decode contract and explicit finite-syndrome limits; found no new inconsistency warranting a change.
- **IBLT researcher:** checked current-Ref residual updates, one working copy, retained rescue, sizing samples and the all-zero-CDF infinity convention. Prior F4's capped-tail input now has a defined selection and an explicit test obligation.
- **Consensus researcher:** checked the conditional gate proof above, simultaneous entry/exit snapshot, mean-zero boundary and absence of separate root confidence. None requires a policy revision.
- **Core/lotusd P2P developer:** checked captured slots/proofs, root/body churn, stale replies, timeout capture, donor retries and awaiting-admission lifecycle against the declared host boundary. Historical source contracts remain older-protocol provenance.
- **Red team:** considered a fixed peer population with withholding, delayed replies, equivocal valid MATCH proofs, fake Pending IDs and internally valid DIFF assertions. Silence cannot reduce alpha; rescue cannot upgrade votes; body validation remains required. Response selection and equivocation can threaten liveness/agreement, but §§9/11 already make these experiment/proof obligations rather than promise universal agreement. No Sybil remedy or unsupported safety theorem was added.
- **Liveness/formal reviewer:** independently replayed F1 and explored all bounded item-state transitions as described above. Empty-W/nonempty-support nonfreezing and continuous-arrival limitations are explicit selected semantics, not hidden guarantees.
- **C++ implementer:** checked integer gate comparisons, finite state bounds, capacity attribution, atomic local errors and capped streak versus unsaturated cumulative counts. No new undefined arithmetic path was established.
- **Test engineer:** checked T0052/T0067 and the retained full-K quorum, lifetime, rescue and malformed-input cases. Prior obsolete root-vote and answerer-test wording is corrected. The 7000 T7 trials, 5/20/100-node T9, four malformed-message workloads, 50-height/20-node soak and host equivalence obligations remain.
- **Measurement engineer:** checked distribution reporting, retained trials/seeds, censoring/nonfinishing disclosure, complete body/network accounting and hard zero false/split assertions. Reported probabilities, actual seeded outcomes and future simulator results remain distinct.
- **Minimalist:** an empty operation list is appropriate; no concrete defect motivates more machinery, extra policy, renamed constants or stylistic edits.
- **Skeptical paper reviewer:** the text does not claim that repeated local samples prove global independence, that candidate proofs authenticate bodies, or that this review proves security. No empirical correctness or performance result is inferred.

## Completion assessment

Within the stated **document-review** scope, the completion criteria are answered: the latest operational rules are explicit, the prior concrete gate and sizing failures have specified resolutions and regression obligations, the obsolete timing target is removed by author instruction, deterministic bounded semantics and workloads are retained, and fixed-population attack limitations and evidence obligations are visible. I identify no unresolved author choice or new severity-eight finding.

Implementation, frozen-artifact migration, generated sizing-table validation, simulator campaign outcomes, empirical zero-false/split performance, provisional K/f selection and real-node integration remain unexecuted future work. Those limitations do not constitute completed evidence. The root coordinator must compare independent revisions and apply the runtime stop rule; this report alone neither locks claims nor declares consensus or convergence.
