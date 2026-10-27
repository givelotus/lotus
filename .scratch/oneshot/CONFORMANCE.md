# Snowstorm proposal conformance — IMPCD iteration 1

Regenerated **in place** under Shammah's latest instructions. The unchanged bundle is `.scratch/inputs/SNOWSTORM-SPEC-INPUTS.md`, SHA256 `4bb4cc4d8d0aa76c92e905002dabd051c76fca8ef114f6bdd9318a853eaeff76`; all 318 lines were read. Live operator amendments override conflicting bundled text. The existing oneshot proposal supplies the base; no alternate proposal copies were made.

## Applied controlling changes

| Rule | Final disposition | Coverage |
|---|---|---|
| DIFF reconstruction | Start from the round capture's raw R, including locally excluded IDs | §6.1; T13_diff_local_excluded_peer_included_yes |
| Partial peeling | No partial item yes/no observations; a still-undecoded reply abstains on every item. Timely valid arrival remains an observed root nonmatch, not an accumulated root vote | §§6.2,8; T13_undecoded_reply_abstains_every_item; fake-Pending and full-rescue regressions |
| DIFF-only sizing | Use exact samples and normal estimator; permit shrinking. Only no-sample MATCH/silence retains n; doubling triggers unchanged | §6.3; T7_diff_only_round_shrinks_request |
| Replacement round-count amendment | Preference, cumulative side counts, consecutive count and FINAL replace scalar item likelihood accumulation. No separate root accumulator/reset/veto remains. MATCH is compact captured item evidence; all-W FINAL-in is the freeze condition | §§7,8,10; current round-count test table |
| Threshold derivation | Exact full-K hypergeometric tails reproduce all five supplied rows. Broot only derives Btx; Btx only derives beta_round | §8; T13_beta_reference_table |
| Admission after freeze | Later gate admission changes the root and invalidates freeze; no wait-until-next-epoch latch | §8; gate/lifetime transition cases |
| Removed alternatives | Withdrawn finite-magnitude rule not applied. The temporary OPEN item-scoring instruction and earlier item-only amendment retaining root accumulation are superseded | Iteration-1 accepted-changes.md |
| Retained scope | Stateless two-way one-shot polls, 2n fallback, provisional K, raw-set dissemination, bounded rescue/Pending, host push scope, original workload counts | §§1–11; retained nonvoting obligations and full historical case inventory |

## Open decisions

Q1 gate order/empty mean; Q3 capture-time Pending and admission/incarnation lifetimes; Q4 wanted host delivery/callbacks; Q5 first donor versus retries; Q6 fallback correlation grammar; Q8 threshold endpoints and beta_round=1; Q9 actual classifier/calibration and population-rate projection; Q10 FINAL and threshold changes; Q12 empty-W freeze. Q2, Q7 and Q11 are closed. Additional structural findings: the byte cap can exceed the schedule index domain, and DIFF must reject missing IDs already in the raw capture. Host-only body-byte accounting also needs clarification.

Do not invent threshold floors, an empty-set delay, a new root confidence mechanism, a receiver token protocol, or a security theorem to close these cases. The detailed scenarios and smallest fixes are in `.scratch/impcd/iteration-1/findings.md`; high-severity statistical/adversarial concerns are preserved in `minority-report.md`.

## Verification actually performed

- PASS: 19 document/arithmetic checks, including the five reference rows using independent integer binomial sums and exact rational tail probabilities. For each row, verify the selected threshold meets the target and its predecessor does not.
- PASS: all 104 original frozen-case inventory rows retained as historical provenance. Current active policy tables replace obsolete scalar-item/root-SPRT tables; historical names do not revive old policy requirements.
- PASS: regenerated `.scratch/oneshot/normative-PROPOSED.diff` against the unique marked span in the current parent document; `git apply --check` succeeds. The parent normative document and rendered site remain unchanged.
- PASS: input bundle digest unchanged; existing source freeze-manifest digest remains `4aa896175e94e472f645c2d7ca25552a3efb079a789dd8aaca203b0e318906db`.
- No node acceptance, build, sanitizer, simulator, table generation, freeze, source migration or publication was run. New test rows are requirements in the executable-contract proposal, not compiled/executed tests. The legacy frozen source API/harness still describes its older protocol and is not claimed migrated.

## Version and termination

Spec: `ee334454711106d48f442f588f13f0da4d10df0d9042d10a7673380ad58e3078`; 86,055 bytes versus the 76,234-byte original baseline, **12.882703% growth**. Test plan: `fe01f59b74d4c04686914f7a361cd5d7019733fa90b0dd85d4f1098c72b3611b`; 55,812 bytes versus 61,492 original bytes. The 20% spec-growth stop threshold has not been reached.

Iteration 1 of at most 4. **Not converged: new blocker/major scenarios remain. STOP for the spec owner's next decisions/application**, as explicitly requested. No iteration 2, stability percentage or successful independent artifact-review/freeze verdict is claimed. Git commit of this review round is authorized; the iteration records and regenerated files are committed together.
