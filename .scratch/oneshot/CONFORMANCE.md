# Snowstorm proposal conformance — IMPCD iteration 2

Edited `.scratch/oneshot/SPEC-PROPOSED.md` and `TESTS-PROPOSED.md` **in place**. No relocation or duplicate proposal. The operator confirmed this is the intended location.

## Maintained authoritative input

Current `.scratch/inputs/SNOWSTORM-SPEC-INPUTS.md` SHA256: **`b3163bd3a4e3fbfcfacf0817127844b836f5b12a48b83ea0bf3fe947c7e9753c`**. It contains 46,566 bytes and 422 lines. The incoming bundle already included accepted-review and final quorum-amendment sections; before this pass's answers append it comprised 42,859 bytes, SHA256 `ac75af45390b84a80493d38e52ab16a3d70a9ebfba28f850a00913e6ca256506`. The earlier iteration-1 bundle digest is historical provenance, not the digest of this updated incoming prefix.

Appended the entire answers message verbatim under `ANSWERS TO Q1–Q12`; its intermediate whole-file digest was `46326c7029bf0886cee068ecfdf9a7abac20a13371adb2359e89fd0fb22bef30`. Then appended both partial-voting overrides verbatim in arrival order under separately titled final sections. Existing incoming text was preserved by append-only writes. Every future operator instruction changing the spec is appended verbatim to this bundle before application, with the new whole-file SHA256 recorded. This round versions the maintained input in Git.

## Current controlling rules

| Rule | Applied disposition | Current regression requirement |
|---|---|---|
| Sampling/success | Fixed full-sample alpha quorum; abstention never shrinks alpha | T13_full_sample_quorum_with_abstainers |
| Consecutive threshold | beta_c=Btx, constant in D, 12 at epsilon=1e-9; no hypotheses, likelihood or match-rate estimator | T13_quorum_and_consecutive_constants |
| No success and FINAL | Reset nonfinal c=0 on no success; immutable FINAL accepts no further updates | T13_no_success_resets_streak; T13_final_lifetime_immutable |
| Gate | One pre-entry/pre-exit W mean after item updates; empty mean zero; simultaneous entries/exits | T13_gate_simultaneous_prechange_mean |
| Capture/transfer | One M+P raw/Pending lifetime capture; post-capture items get no votes; Pending admission keeps its whole state, including FINAL-out | T13_capture_pending_and_postcapture_abstention; T13_pending_admission_preserves_whole_state |
| Body delivery | Ordinary FetchBody both directions; wanted is for votes, not a body request; concurrent deduplication and alternate retry | T7_poll_success_reply_diff_bidirectional_fetch; retained T10 |
| Reply grammar/bounds | Prefix REPLY has no mode/basis; conservative headers REPLY100/POLL116/DIFF109; shared byte/domain cap | T11_reply_removed_fields_and_header_bounds |
| Partial observations | Captured absent/excluded=>NO; guarded scheduled zero-index>=1=>YES; otherwise abstain. Check CURRENT Pending; NO wins | T13_partial_yes_no_abstain_guarded; T13_partial_pending_guard_current_state |
| Partial storage | Two explicitly charged compact masks; no second cell copy or evidence-only peel; rescue replaces classification | T13_partial_masks_capacity_and_lifetime |
| Freeze | Nonempty W entirely FINAL-in, or R union Pending empty; no empty-W/nonempty-support freeze | T13_empty_W_nonempty_support_does_not_freeze; T13_truly_empty_state_freezes |
| Retained accepted fixes | DIFF reconstructs from captured raw R; DIFF exact samples can shrink next request; no separate root accumulator | Excluded-local YES and DIFF-only-shrink cases |

Q1–Q12 are closed. The latest general partial-vote wording uses the precise Pending-restricted shared witness supplied immediately before it; no instruction removes that guard. Its accepted yes-lean remains a simulation measurement obligation and is not reopened.

## Still open

**Q13:** beta_adv=0 with even K permits both sides to reach alpha in one round. Example D=5,K=2,alpha=1,yes=no=1. No priority or change to Config/alpha is invented. This is independent of the accepted partial-vote policy.

Iteration-1 structural findings are also addressed: prefix cap respects max_symbol_index+1, DIFF missing IDs cannot already be in captured raw R, and exclusions must fit the reconstructed raw assertion. The removed special wanted-send path has no byte-accounting requirement left in core Stats.

## Verification and limits

- PASS: 31 independent arithmetic, transition and document checks: five exact K/alpha/beta_c rows, 12-success finality, no-success reset, strict overtake/ties, immutable FINAL, simultaneous gate, freeze predicate, conservative wire/cap bounds, captured lifetime and partial guard text, and all 104 original frozen inventory rows.
- PASS: unique final answers section, current whole-bundle digest pinned in both drafts, unique parent normative markers and unchanged source freeze-manifest digest `4aa896175e94e472f645c2d7ca25552a3efb079a789dd8aaca203b0e318906db`.
- PASS: regenerated `normative-PROPOSED.diff`; direct `git apply --check` succeeds. This is a review patch; the parent document and rendered site remain unchanged.
- No production implementation, compiled node acceptance, sanitizer, simulator, sizing-table generation, freeze, source pin, node data or publication was changed. Transition checks exercise the proposed rule independently; they do not establish implementation conformance or network agreement.

## Version and stop

Spec SHA256 `b7ee816078172b4e7230045376034930142629373e8e5fb00c23f90899d8aa86`; 77,283 bytes versus 76,234 original bytes: **1.376026% growth**, below 20% and smaller than iteration 1. Test-plan SHA256 `4145313dea1380c009f46aa2eec3ebe2fa99062c5c3c8c1b1d029087b8882884`; 52,128 bytes.

**STOP after iteration 2 of at most 4; not converged because Q13 is a new major concrete case.** No third iteration is run on the unchanged concept. Review records are in `.scratch/impcd/iteration-2/`. Commit input maintenance, in-place regeneration and review records together, as authorized.
