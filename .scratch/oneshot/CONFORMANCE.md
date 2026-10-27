# Snowstorm proposal conformance — IMPCD iteration 4

Reviewed and updated `.scratch/oneshot/SPEC-PROPOSED.md` and `TESTS-PROPOSED.md` **in place**. Review records, claim-ledger history, two independent revisions, arithmetic witnesses and regeneration/check scripts are in `.scratch/impcd/iteration-4/`.

## Authority and input

Input bundle SHA256 remains **`e6ab26b85fe03c3c0a327b21bb5d2da7fc9c38f9a2aee178a0d584f42b1abd1d`**,48,180bytes/444lines. This request starts technical review and adds no new operator protocol amendment to append. Future spec-changing instructions continue to be appended verbatim before application. Review repairs are attributed to findings, not fabricated as operator quotations.

Installed IMPCD skill now routes to v3.0.0: stable claim ledger, two independent revisions and shared repairs. Retained the operator's eleven technical perspectives, severity×confidence, counterexample priority, settled-rule protection,20% growth guard and four-numbered-iteration cap. Independent revisers were gpt-6-astra and gpt-6.1-sol in separate contexts, neither seeing the other's revision before submission; no human domain experts were recruited.

## Accepted repairs

- F1: passing the c-based gate into frozen W does not imply FINAL-in; a nonpreferred12-success streak can have p=in,c12,FINAL=false. Corrected the assertion and gate-entry test; existing gate/state/freeze rules preserved.
- F2: removed a stale separate-root-vote test assertion.
- F3: corrected answerer-normalization language and the test-freeze instruction to captured-K quorum; retained actual answerer-share measurement.
- F4: defined sizing-cost positive n/zero estimated probability as +infinity, retaining smaller-n ties and existing growth/cap rules. Added the cap5/large exact-DIFF sample case to the test requirements.

Eleven substantive claim repairs agreed in both revisions; substantive disagreement0/11. Reporting/status fragments generated from actual findings. All claims remain open because two accepted v3 iterations have not elapsed. Both proposals are byte-for-byte renderings of ledger-accepted.json; canonical parent remains unchanged.

## Still open

**F5, severity8: P4's >=99% of1000 fixed seeds freezing within25rounds conflicts with the current completion distribution for the23fast/6silent/3slow fixture.** For a permitted accurate-RTT configuration, exact fresh-uniform-round arithmetic yields50.39205077%; even all26nonsilent peers timely gives96.97785880%. These are idealized calculations, not executed seed outcomes or a claim that every fixed seed collection fails. The frozen source has no exact proposed silent/slow case. Keep the authored target, seeds and workload unchanged; actual fixture and seed outcomes are still needed, and changing target/protocol/fixture requires author resolution. Both independent reviews rejected silently weakening this oracle.

Q1–Q13 remain closed by operator instructions. Provisional K remains the named pre-release(f,K) experiment outcome. Implementation conformance, simulator measurements, sizing-table generation, frozen-artifact migration and network validation remain future evidence obligations.

## Executed verification

PASS: independent state/arithmetic reproducer for F1,F4,F5;26 ledger/document/integrity checks; all104 historical inventory rows preserved; P4's1000/25/99 requirement unchanged; selected quorum/voting/state/gate paragraphs unchanged. Review-only normative-PROPOSED.diff regenerated and `git apply --check` passes; Markdown diff whitespace passes. Acceptance-manifest SHA256 remains `4aa896175e94e472f645c2d7ca25552a3efb079a789dd8aaca203b0e318906db`.

No production/header/harness/oracle/manifest/canonical-parent edit, compiled node acceptance, sanitizer, simulator, table generation, source freeze, source pin, node-data mutation or publication. Arithmetic witnesses and document checks are not implementation conformance evidence.

## Version and stop

SPEC SHA256 **`34ad696fe0013f1d0dddeeced1c93e03e10a6d6ff15332f7d1f4c5c919a6ff3d`**,77,517bytes. TESTS SHA256 **`47feedcb64bb1a1df72f74e98466239024b804c37c4f868bfe26fde7cda11225`**,53,380bytes. Spec growth from this round's baseline76,725bytes is1.032258%, below20%.

**STOP: original fourth-iteration cap reached, not convergence.** F5 remains an unresolved high-severity finding, so the contract is not yet finished. No no-new-major or fixed-point claim is made. See iteration-4/findings.md,minority-report.md and accepted-changes.md.
