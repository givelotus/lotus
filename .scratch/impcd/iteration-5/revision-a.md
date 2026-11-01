# Independent revision A — iteration 5

**Proposed substantive operations: zero. New concrete findings: zero. Unresolved severity >=8 findings from this independent review: zero.** This conclusion concerns this bounded document review, not protocol correctness established by execution.

I reviewed the complete current spec and test proposal against the maintained input bundle, including its final F5 and F1 messages, the iteration5 settings/critique brief and the stable-ID ledger. The earlier input sections and source-contract inspection remain the common historical context from my independent iteration4 review. I verified that concatenating all911 spec claims and406 test claims reproduces the current documents exactly. I did not read any revision-B output. Only this iteration's `revision-a.md` and `revision-a.json` were written; no source/proposal/frozen artifact was changed.

The IMPCD v3 rule against unmotivated changes applies: no concrete counterexample below warrants a new claim operation. A zero-operation revision does not itself fabricate another accepted iteration or lock any claim.

## Revised gate and restored implication

Relevant exact claims:

- §8 S0718: “Define gate_value[x]=c[x] if the previous success side is IN, and 0 otherwise (including no previous success). Compute mu=sum(gate_value[x] for x in W_before)/|W_before|, or 0 if empty.”
- §8 S0731: “Immutable FINAL-in members retain c=beta_c and previous success side IN, so a nonempty frozen W has mean gate value beta_c. A later gate entrant must have previous success side IN, c=beta_c and p=in; it is therefore FINAL-in.”
- T0052 tests the conditional value on both the prechange mean and entry side, including simultaneous exits, equality and empty-W mean zero.
- T0067 explicitly retains the original F1 witness, now requires rejection of its attempted entry, then requires twelve subsequent IN successes and FINAL-in entry.

**Disposition: support; confidence10 for the local state implication. No severity assigned because there is no defect.**

Independent trace, using IN=0 and OUT=1 in a small standalone arithmetic checker:

| Point | d[in] | d[out] | p | c | Previous | FINAL | gate_value |
|---|---:|---:|---|---:|---|---|---:|
| Pending after11 IN,1 OUT,11 IN,12 OUT | 22 | 13 | in | 12 | out | false | 0 |
| Matching admission, then one further OUT | 22 | 14 | in | 12 | out | false | 0 |
| Then11 consecutive IN | 33 | 14 | in | 11 | in | false | 11 |
| Then twelfth consecutive IN | 34 | 14 | in | 12 | in | true | 12 |

A still-nonempty frozen W has mean12 at the reference parameters. The first two rows fail entry; the third also fails. The fourth enters and changes the root as prescribed. Admission preserves state, so it does not create a bypass. Once FINAL-in, both an OUT round and a no-success round leave the entire state unchanged.

General argument: every FINAL-in W member has c=beta_c and previous=IN. Its gate value is beta_c; a nonempty collection has that same mean. An entering outsider has p=in and gate_value>=beta_c. Since c is capped at beta_c, entry forces c=beta_c and previous=IN. On the transition that produced those fields the unchanged FINAL predicate would have finalized it. It cannot subsequently lose FINAL without losing that lifetime. Therefore the implication holds. A prior success IN followed by no success does not bypass the gate: no success resets c=0. Cumulative-count overtake after an already capped nonpreferred IN streak also sets FINAL on the very overtake transition.

The scope matters: after a host removes every member of frozen W, that commitment has already been invalidated and the empty-W mean is0. The implication above does not impose a new FINAL-only gate on such an empty set. Likewise, with mean0 an outsider whose gate_value is0 can enter if p=in; this is the selected rule, not a counterexample. Nonempty R/Pending with empty W still does not freeze.

A bounded exhaustive scratch check enumerated reachable states for beta_c2 and3 from both initial preferences through14 steps over IN/OUT/no-success. It checked310 and570 distinct states respectively; every reachable p=in,previous=IN,c=beta_c state was FINAL. This is arithmetic corroboration of the local proof, not a node simulator, comprehensive model check or executed acceptance test.

## F5 resolution and measurement boundary

Relevant claims: §9 S0795's added acceptance paragraph and T0264 `T16_silent_slow_matching_freeze_round_distribution`. They preserve1000 fixed seeds and the23fast/6silent/3slow fixture, remove the obsolete99%-within25 target, require the freeze-round distribution and explicit nonfinishing outcomes, and retain zero false freezes and zero split freezes as hard assertions.

**Disposition: support; confidence10 that the current text implements the final operator decision.** My prior iteration4 objection was that dropping the target required author authority; that authority is now explicit. The old run-of12 calculation remains historical diagnostic evidence and is not a new performance oracle or reason to retain the superseded25-round threshold.

A horizon long enough for ordinary fixtures must not be interpreted as a safety theorem that every permitted adversarial execution eventually freezes. Existing reporting explicitly includes nonfinishing trials and uncensored outcomes, while the evaluation section requires experiment inputs and estimands to be fixed and independently reviewed before execution. No numeric horizon, seed tuning, new pass percentage or weaker safety assertion is introduced by this revision. Actual false/split and nonfinish outcomes remain unmeasured here.

## Eleven technical perspectives plus anchor

| Perspective | Review and result |
|---|---|
| Coding theorist | Rechecked signed cell/One/Two constraints, immutable source-cell audit and finite-syndrome caveat. No new algebraic contradiction identified. The gate amendment does not alter coding primitives. |
| IBLT researcher | Rechecked raw-R inbound reference, current R-union-Pending outbound reference, exactly-once residual deltas, private peeling and rescue ordering. Existing CDF zero-cost convention remains total; cap5 with scaled exact sample32768 is a valid stronger fixture than the earlier synthetic example. No new finding. |
| Distributed-consensus researcher | Verified gate implication, strict cumulative tie retention, immutable FINAL and full captured-K uniqueness. Local implication is valid; it is not global agreement proof. |
| Core/lotusd P2P developer | Rechecked correlation, captured slots, late-discard, disconnect abstention, fallback timing and body-token admission boundaries. No introduced change to timing or host ownership is hidden in F1/F5. |
| Red team | Considered fixed-population selective withholding, early valid MATCH equivocation to different pollers, fake-Pending contamination and body-delay schedules. These attacks need no Sybil identities; strict quorum prevents opposite successes in one local round, but does not prove cross-node agreement. Existing limitations and mandatory adversarial/split reporting remain, so no safety guarantee is invented. The original F1 attack trace is now blocked. |
| Liveness/formal | Checked previous-OUT gate value zero, no-success reset with retained previous history, empty-W mean0 and Pending-to-admitted transfer. F5 now asks measured distributions instead of the contradicted finite target. Empty W with nonempty all-FINAL-out R intentionally does not freeze; this settled rule is preserved. |
| C++ implementer | Checked that gate is a derived read of existing bounded fields; it adds no record, score or history. Exact cross multiplication remains sufficient; resource/error semantics and zero-denominator sizing convention are unchanged. |
| Test engineer | T0052 and T0067 cover both conditional mean and conditional entry, failed witness and successful eventual entry. T0264 keeps trials/seeds and hard safety assertions. Historical source tests implement an older contract; no execution conformance follows from this review. |
| Measurement engineer | Retains nonfinishing observations, distributions and separate body/admission latency. A long horizon is not a guarantee or permission to censor failures. Full fixture configuration and scientific estimands remain the explicit pre-evaluation obligations. |
| Minimalist | No motivated operation remains. No threshold adjustment, FINAL-only empty gate, root barrier, extra timeout, eviction mark or safety-oracle weakening proposed. |
| Skeptical paper reviewer | No new severity>=8 internal defect demonstrated; no inherited Snowball security theorem, unlimited-height epsilon theorem or empirical result inferred. The local proof is narrow and clearly distinguished from network correctness. |

Anchor: final ordered instructions control both gate operands and F5's acceptance interpretation. Strict sampled-K quorum, explicit arrival votes, rescue abstention, full-state Pending transfer, simultaneous gate, immutable FINAL and exact freeze predicate remain intact. All prescribed workloads remain; Sybil resistance stays deferred.

## Completion assessment

For this independent document review, the owner-resolved F1/F5 choices are implemented consistently, the previous concrete counterexamples have dispositions, and no new internal failure requiring a claim edit was identified. The current deterministic operational rules and planned test obligations answer the document-level criteria sufficiently for an empty-consensus stop if the other independent review agrees and the coordinator finds no unresolved major finding.

This is not a claim that every implementation detail or experiment artifact has already been produced. Artifact/header/harness/oracle correction, frozen trust-anchor review, mutation evidence, implementation acceptance/sanitizers, simulator configurations and results, the provisional(f,K) choice, and real-network validation remain expressly future work. A fixed point under this review operator is stability, not proof of correctness or stakeholder/expert approval. No simulator, implementation acceptance, deployment or source freeze occurred.
