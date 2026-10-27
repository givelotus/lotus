# Snowstorm proposal conformance — IMPCD iteration 3

Updated `.scratch/oneshot/SPEC-PROPOSED.md` and `TESTS-PROPOSED.md` in place. No relocation or duplicate proposal.

## Maintained input

Current bundle SHA256: **`e6ab26b85fe03c3c0a327b21bb5d2da7fc9c38f9a2aee178a0d584f42b1abd1d`**; 48,180 bytes / 444 lines. The prior committed 46,566-byte prefix remains byte-identical with SHA256 `b3163bd3a4e3fbfcfacf0817127844b836f5b12a48b83ea0bf3fe947c7e9753c`.

Appended both new messages verbatim in order, under `PER-ITEM REPLY VOTES — ARRIVAL EVIDENCE` and `FINAL PARTIAL-PEEL RULE AND STRICT SAMPLE QUORUM`. Intermediate SHA256 after the first append: `8cd0115c5f23fc06ef2ca101bdf74cce2f09cfe34f0d746e71db6c5806fd4e52`. The latest section overrides the earlier partial rules; the preceding instruction excluding rescue-only discoveries remains applicable. Continue appending every future spec-changing operator instruction verbatim before application and record the new whole-file digest.

## Active rules and coverage

| Rule | Current disposition | Test requirement |
|---|---|---|
| Preference | Held but excluded is NO | T13_arrival_exclusion_overrides_presence |
| MATCH | YES in captured W, NO for other captured items | T13_match_equals_full_candidate_observations |
| Arrival explicit decode | Present/nonexcluded YES, absent/excluded NO | T13_partial_explicit_preference_observations |
| Arrival residual | Other captured items abstain; no sharing inference | T13_partial_unclaimed_items_abstain |
| Complete arrival | Other eligible captured reference items are shared unless excluded; complete DIFF determines captured Pending absence from its raw assertion | T13_complete_arrival_unclaimed_shared |
| Later rescue | New discoveries/inferred sharing abstain that round; do not upgrade arrival observations, including same-call cascades | T13_rescue_only_discoveries_abstain |
| Removed machinery | No zero-cell witness, current-Pending guard, proven-shared definition, per-reply observation masks or associated resource bound | T13_arrival_evidence_lifetime_and_storage |
| Quorum | alpha=floor(((1+beta_adv)/2)*K)+1 against full sampled K; strict at beta_adv=0 too | T13_strict_quorum_zero_adversary_boundary |
| Constants | At epsilon=1e-9, beta_c=12; D/K/alpha rows: 16/4/3, 32/8/5, 64/16/10, 128/32/20, 500/125/76 | T13_quorum_and_consecutive_constants |

All other answered rules remain: fixed consecutive-success target, no-success reset for nonfinal items, immutable FINAL, captured lifetimes, whole-state Pending transfer, simultaneous gate, ordinary bidirectional fetch with retry, prefix REPLY grammar and exact freeze predicate. Existing raw-R DIFF reconstruction and exact-sample resizing are preserved.

## Verification and limits

- PASS: 25 independent quorum/classification/document checks, including the five strict-quorum rows, uniqueness over all supported populations at zero/default/near-upper adversary fractions, explicit partial observations, exclusion priority, complete-arrival sharing, MATCH, rescue-abstention rule/text, preserved input prefix and all 104 historical inventory rows.
- Current input digest is pinned in both drafts. Parent normative markers are unique and the frozen source manifest SHA256 remains `4aa896175e94e472f645c2d7ca25552a3efb079a789dd8aaca203b0e318906db`.
- PASS: regenerated `normative-PROPOSED.diff` and direct `git apply --check`; the parent document and rendered site remain unchanged.
- No production/source-header/harness/oracle/manifest change, node acceptance build, sanitizer, simulator run, generated sizing table, freeze, source pin, node-data mutation or publication. Independent rule checks are not implementation conformance evidence.

## Version and stop

Spec SHA256 `3eac40386ebb46f024e376ac49fee416791d956bec99525f692f5e41293b6eb2`; 76,725 bytes, **0.644070% growth** from the original 76,234-byte concept. Test-plan SHA256 `dc290e7a63b83bef86d838d43c08909bd4a4483ac5e1a6d2873323f8e30a2286`; 52,252 bytes.

**STOP after iteration 3 of at most 4: no new blocker/major concrete finding; Q1–Q13 are closed.** The technical no-new-major stopping condition is met; implementation/network validation is not claimed. Provisional K remains the named experiment outcome. Records are in `.scratch/impcd/iteration-3/`.
