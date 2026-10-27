# Iteration 4 — consensus step and disposition

Applied four smallest repairs to the existing spec and test proposal **in place**, regenerating them from the accepted claim ledger. No alternate proposal paths were created. The maintained operator input remains unchanged: no new spec-changing operator message was supplied for verbatim append.

1. **F1:** correct the false assertion that passing the gate into frozen W implies FINAL-in. Preserve the selected operational gate/state/freeze predicates. Add the nonpreferred-capped-streak trace to the existing gate-entry test, retaining ordinary FINAL-in-entry coverage.
2. **F2:** remove the obsolete test requirement to count a separate root vote on incomplete decoding. Require only the selected arrival item observations.
3. **F3:** correct the stale answerer-sample wording and test-freeze instruction to captured-K quorum; retain answerer-share measurement and response-dependent liveness/proof obligations. No independent-response safety guarantee is invented.
4. **F4:** define a positive request length divided by zero estimated success probability as +infinity for the sizing-cost comparison; retain smaller-n ties and existing growth/cap rules. Extend the existing sizing test with a valid32768-ID DIFF sample at M262112/cap5.

No new scoring, gate mechanism, timer, sampling policy, eviction rule or identity scheme was introduced. Strict alpha, partial explicit observations, arrival-only evidence, rescue abstention, raw-R DIFF reconstruction, exact-sample resizing, simultaneous gate, immutable FINAL and whole-state Pending transfer remain selected.

## Independent revisions and error estimate

- A: gpt-6-astra, separate context, thirteen exact claim operations: eleven repairs and two open-question disclosure updates.
- B: gpt-6.1-sol, separate context, eleven exact repair operations; separately reports the same unresolved F5.
- Neither saw the other's proposal before submission. Both received the same initial ledger/findings/authority. Root-supplied arithmetic evidence was available to both; reviewers independently replayed it and added their own source inspections. They are model executions, not external human reviewers, and agreement is not proof.
- **Substantive consensus: eleven stable claim IDs**, S0731,T0067,T0246,S0865–S0868,S0870,T0340,S0432,T0256. Wording differs; the repairs agree in meaning. The root selected A's wording, retained both gate-entry subcases, and used B's stronger table-independent F4 fixture. `consensus-operations.json` records the final exact replacements.
- Substantive disagreement **0/11=0**, within the preselected0.50 tolerance. Raw operation-list disagreement is2/13≈0.153846: A additionally patches the two status disclosures; B records the same open issue outside its JSON. These disclosures are report metadata, not a protocol-policy disagreement. `apply_consensus.py` separately generates these disclosures, review title and record pointers in the ledger before rendering.
- Accept this nonempty consensus step. Full initial scope would widen to include the next finding after acceptance; no next step executes because the original fourth-iteration cap is reached. No claim is locked: only one accepted iteration has a v3 ledger, so the two-accepted-iteration condition is unmet. Historical iterations1–3 are preserved as amendment rounds and are not retroactively labelled independent v3 reviews.

## Disputed changes and unresolved finding

**F5 remains OPEN, severity8.** Both revisers rejected the initial suggested replacement of the >=99%/1000-seed/25-round oracle. Input P4 explicitly selects that requirement. It remains byte-identical. Idealized exact probability is approximately50.4% for an allowed timer configuration and96.98% even when all26nonsilent peers are timely. This is not an executed fixed-seed failure or a deterministic impossibility claim about every seed bank.

A new threshold, different fixture or weakened performance target would require author intent; none was inferred. The smallest authorized action is disclosure and preservation. See `minority-report.md`. Q1–Q13 remain author-closed; F5 is a newly exposed acceptance conflict, not reopening those decisions.

## Completion criteria and actual stop

| Author-owned criterion | Outcome |
|---|---|
| Finish a coherent spec and executable-contract proposal | **Incomplete:** F5 unresolved; do not claim finished/converged |
| Deterministic bounded contract | F4 comparison totality repaired; implementation/resource conformance remains future evidence |
| Preserve latest selected rules and test workloads | PASS for the reviewed amendments; all104 historical inventory rows and P4 target retained |
| Include adversarial Snowball review | Both independent reports include fixed-population withholding/delay, valid-assertion sizing, equivocation and Pending-poisoning analysis; Sybil solution remains deferred |
| Retain individual reversible review steps | This round's ledger, revisions, evidence and in-place changes are committed together, separately from prior rounds |

**STOP: original four-iteration cap reached (iteration4), not convergence.** F1/F5 are new major findings, so no-new-major does not apply. Spec grows76,725→77,517bytes,1.032258%, below20%; no state recurrence/oscillation, no cutback. There is only one accepted v3 ledger step, so a two-step runtime growth comparison is not asserted. Earlier reports and ledger initial/accepted versions retain the history.

## Checks and scope

PASS: independent F1 state witness, exact rational F5 recurrence and F4 cap/tail witness;26 document/ledger/integrity checks; review-only normative patch applies; Markdown diff whitespace passes. Input and frozen acceptance-manifest hashes remain unchanged; canonical parent and source files remain untouched. Spec/test rendering digests are in CONFORMANCE.md and ledger-accepted.json.

No compiled node acceptance, sanitizer, simulator, generated sizing table, source freeze, production change, publication or deployment. The expanded future test requirements have not been executed against a new implementation.
