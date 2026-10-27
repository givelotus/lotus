# Snowstorm executable-contract test proposal — review round 1

The three accepted corrections and the **replacement** per-item/root Snowball round-count amendment control this regenerated plan. This file is edited in place; no frozen test, header, harness, oracle, manifest or production implementation is changed. Input bundle: `.scratch/inputs/SNOWSTORM-SPEC-INPUTS.md`, SHA256 `4bb4cc4d8d0aa76c92e905002dabd051c76fca8ef114f6bdd9318a853eaeff76`. Live operator amendments recorded in `.scratch/impcd/iteration-1/accepted-changes.md` override conflicting bundled sections. Argon owns simulator execution, with fetchable uniques and printed 1 ms host validation.

## Current replacement contract

- DIFF reconstructs peer candidates as `((captured raw R - wanted) union missing) - peer exclusions`.
- A still-undecoded non-MATCH reply abstains on every item, even decoded-negative/excluded/zero-cell cases. It is an answered nonmatch only for the next-round observed match-rate estimate. A full decode on arrival or rescue can contribute at most once per peer/item/round.
- MATCH supplies compact captured per-item observations: yes for captured W, no for the rest of captured R union Pending. It is not an algebraic full decode or separate root evidence.
- DIFF-only rounds use the normal sizing estimator on their exact samples and may shrink n. Only no-sample MATCH/silent rounds retain n; the two doubling triggers are unchanged.
- Item state is preference, two cumulative side counters, consecutive count capped at the derived beta_round, previous vote side and FINAL. The hypergeometric function determines only the sign of this round’s vote. Kx=0 leaves the whole item state unchanged.
- The root commits to W. Freeze iff all W items are FINAL-in. A later gate admission invalidates the freeze. No root-confidence accumulator, root-change scoring veto, likelihood-bit item score, clamp, or score-derived epoch eviction mark remains in the proposed contract. Broot survives only to derive Btx, which derives beta_round.
- Q2 (partial-voting memory), Q7 (item-score choice), and Q11 (MATCH inclusion) are closed. Numerical threshold edges, population transitions and other open cases are listed below. Do not freeze guessed expectations for an open case.

## Current round-count and correction cases

These are future test requirements, not claims of executed acceptance tests.

| Test | Normative coverage | Required assertion |
|---|---|---|
| T13_beta_reference_table | §8 | Independently compute exact integer hypergeometric tails, unrounded p_error, and threshold ceiling. Reproduce all five rows below, comparing p_error at displayed precision and exact K/y_star/beta_round |
| T13_first_round_zero_yes_not_final | §8 | For the reference D=32,K=8,beta_round=7 fixture, a first OUT round increments d[out] to 1, sets c=1 and does not mark FINAL. No likelihood magnitude is accumulated; preserve a reversible preference change |
| T13_final_requires_consecutive_preferred_side | §8 | For each reference beta_round>=2, fewer than beta_round repeated preferred-side votes cannot finalize; exactly beta_round can. A streak of length beta_round on a side that is not the cumulative-count preference does not finalize |
| T13_preference_overtake_and_tie | §8 | Increment one side count exactly once; switch only when its count strictly exceeds the current preference’s count. Equal counts retain preference; test both directions before FINAL |
| T13_streak_change_and_abstention | §8 | A changed observed side sets c=1; repeated side increments up to the cap. Interspersed Kx=0 leaves counts, preference, c and previous observed side unchanged |
| T13_item_vote_uses_population_and_prior_rate | §8 | Determine only the sign of L(Yx;D,M0,M1hat,Kx); positive/negative infinity are signs, zero votes IN. Never accumulate magnitude; use prior observed rate, never current or hidden truth |
| T13_gate_uses_mean_consecutive_rounds | §8 | Admitted p=in item enters only at c>=mean c of W; p=out leaves. Empty-W and simultaneous-order expectations await Q1; Pending transition awaits Q3 |
| T13_unique_final_side_agreement | §§8,9 | Fetchable unique transactions in quiescent honest fixtures end with the same FINAL side at all honest nodes. Include adversarial/partition outcomes and nontermination reporting; no simulator success is assumed |
| T13_match_equals_full_candidate_observations | §§6.1,8 | Verified MATCH and an equivalent full reconstruction give identical captured item yes/no observations, including captured raw exclusions and captured Pending, with no raw-set equality claim. Pending capture representation is Q3 |
| T13_no_one_round_freeze_reference_nonempty_W | §8 | Nonempty W, all sampled peers match, each reference beta_round>=2: after one round no candidate is FINAL and no freeze is emitted. General D=1024/empty-W requirements await Q8/Q12; do not pretend this reference test establishes them |
| T13_no_root_accumulator | §§1,8,10 | Corrected proposed API, state, Stats, transcript and implementation have no root-confidence accumulator, batch increment, or root-change reset/veto. Broot may exist only as a derivation constant. Legacy frozen API is not claimed corrected by this draft |
| T13_diff_local_excluded_peer_included_yes | §§6.1,8 | Poller captured raw R contains x but captured W excludes it; peer includes x and excludes nothing. A valid empty-list DIFF must give eligible x exactly one YES observation from captured raw R |
| T13_undecoded_reply_abstains_every_item | §§6.2,8 | Incomplete reply gives zero item observations, including partial positive, decoded absent, exclusions and scheduled zero cells; timely valid arrival still answers nonmatch for the observed match-rate estimator |
| T13_partial_fake_pending_cannot_vote | §§4,6.2,8 | A single malicious source poisons live Pending and attacks a retained honest reply’s zero-cell inference. Unless that reply fully decodes, it supplies no item observations. No Sybils, weakened decoder checks or body-admission bypass |
| T13_full_rescue_single_observation | §§6.2,8 | No partial item observations; successful full rescue before the round ends adds at most one complete observation per eligible peer/item; no duplicate scoring |
| T13_pending_state_lifetime | §§6.4,7,8 | Preserve the complete Pending state through awaiting notification, donor disconnect and suspension; loss of live support destroys it, refetch creates fresh Pending state, and tip reset clears it. Admission preference/transfer expectations await Q3 |
| T13_midround_admission_preserves_round | §§6,8 | Root-changing admission/removal preserves active round and eligible item observations; no root confidence exists to reset. Captured-incarnation and post-capture admission cases follow Q3 |
| T13_final_population_transition | §8 | Cover changed D, recomputed beta_round, preexisting c and FINAL records; exact expected transitions await Q10 |
| T13_beta_endpoints_and_calibration_scope | §8 | Preserve exact p=0/D=1 and beta_round=1/D=1024 counterexamples and small-Kx calibration issue; expected policy needs Q8/Q9. Do not clamp beta_round or invent a fallback |
| T7_diff_only_round_shrinks_request | §6.3 | With an existing oversized prefix and only small exact DIFF samples, an independent quantile fixture yields a smaller normal-estimator argmin; assert n_next equals it and shrinks. No zero-decode trigger; doubling triggers remain separately tested |

| D | K | y_star | p_error (display-rounded) | beta_round |
|---|---|---|---|---|
| 16 | 4 | 3 | 0.392 | 9 |
| 32 | 8 | 6 | 0.271 | 7 |
| 64 | 16 | 12 | 0.135 | 5 |
| 128 | 32 | 23 | 0.0715 | 4 |
| 500 | 125 | 89 | 0.0020 | 2 |

## Primitive and workload preservation

Preserve field/cell/schedule/sketch/peeler oracles and all their exact workloads. Existing pure hypergeometric PMF/support/LLR vectors remain independent arithmetic evidence for the round-sign primitive, not an accumulating confidence policy. Old root/item saturation and finite SPRT DP cases are historical arithmetic evidence only, not current protocol requirements; replace their policy assertions explicitly when the executable contract is corrected. Do not retain old batch confidence or scalar item-score fixtures as active full-node acceptance criteria.

Retain 7000 T7 trials, 5/20/100-node T9, 100000 malformed inputs for each of the four new wire types, the 50-height/20-node soak, all T14 boundaries, all T15 cross-process and observation-mode checks, and the existing body-service/transport/callback assertions. Additional tests do not substitute for these workloads.

## Existing frozen cases

All 104 original frozen cases are inventoried below as provenance. Existing inventory labels refer to the earlier plan; the current amendment supersedes all scalar-item and batch-root policy assertions. Preserve applicable pure arithmetic and coding coverage, and replace obsolete policy assertions explicitly. REPLACED / ADAPTED means preserve applicable assertions/workload while replacing obsolete session/policy assumptions. T1–T16 numbering stays stable. Determinism/host-service cases retain exact names and all transport/body callback assertions; only protocol fixtures and observer plumbing change.

| Existing file | Exact case | Disposition |
|---|---|---|
| adversarial_tests.cpp | T11_wire_goldens_and_every_truncation | REPLACED / ADAPTED |
| adversarial_tests.cpp | T11_100000_malformed_messages_per_wire_type | REPLACED / ADAPTED |
| adversarial_tests.cpp | T12_admission_capacity_is_atomic_and_removal_releases_space | REPLACED / ADAPTED |
| adversarial_tests.cpp | T12_connection_capacity_and_fixed_floor | REPLACED / ADAPTED |
| adversarial_tests.cpp | T11_inconsistent_raw_cells_terminate_without_iteration_cap | REPLACED / ADAPTED |
| adversarial_tests.cpp | T12_fifty_heights_twenty_nodes_allocated_byte_soak | REPLACED / ADAPTED |
| adversarial_tests.cpp | T12_height_failure_tables_exhaust_without_eviction_or_refetch | REPLACED / ADAPTED |
| adversarial_tests.cpp | T12_wire_vector_limit_boundaries | REPLACED / ADAPTED |
| adversarial_tests.cpp | T12_own_churn_expires_bounded_reference_before_authoritative_change | REPLACED / ADAPTED |
| adversarial_tests.cpp | T12_derived_capacity_envelopes_follow_live_components | REPLACED / ADAPTED |
| adversarial_tests.cpp | T12_pending_and_fetch_union_capacity | REPLACED / ADAPTED |
| adversarial_tests.cpp | T12_session_symbol_budget_exact_and_duplicate_free | REPLACED / ADAPTED |
| adversarial_tests.cpp | T12_eight_simultaneous_donors_and_ninth_replacement | REPLACED / ADAPTED |
| adversarial_tests.cpp | T12_minus_capacity_rejects_sixty_ninth_distinct_claim | REPLACED / ADAPTED |
| adversarial_tests.cpp | T11_literal_valid_version_malformed_fields | REPLACED / ADAPTED |
| adversarial_tests.cpp | T11_normal_response_order_identity_and_snapshot_binding | REPLACED / ADAPTED |
| adversarial_tests.cpp | T12_suspension_preserves_awaiting_admission_and_existing_confidence | REPLACED / ADAPTED |
| cell_tests.cpp | T2_exhaustive_small_sign_reference_cells | UNCHANGED |
| cell_tests.cpp | T2_reject_million_scale_high_degree_and_random_cells | UNCHANGED |
| cell_tests.cpp | T2_schedule_integrity_overflow_and_wire | UNCHANGED |
| determinism_tests.cpp | T15_same_process_full_transcript | REPLACED / ADAPTED |
| determinism_tests.cpp | T15_transcript_process | REPLACED / ADAPTED |
| determinism_tests.cpp | Host_observation_mode_preserves_actual_actions_and_truth | REPLACED / ADAPTED |
| determinism_tests.cpp | Host_fixed_transport_policy_preserves_default_delivery | REPLACED / ADAPTED |
| determinism_tests.cpp | Host_transport_policy_directed_byte_queue_and_reverse_reply_loss | REPLACED / ADAPTED |
| determinism_tests.cpp | Host_transport_rejects_negative_and_overflow_delays_in_both_directions | REPLACED / ADAPTED |
| determinism_tests.cpp | Host_default_seeded_nonzero_jitter_and_loss_matches_independent_draws | REPLACED / ADAPTED |
| determinism_tests.cpp | Host_reverse_queue_reserves_in_service_ready_order | REPLACED / ADAPTED |
| determinism_tests.cpp | Host_body_service_phase_loss_deadline_tie_and_late_once | REPLACED / ADAPTED |
| determinism_tests.cpp | Host_body_cancellation_preserves_physical_arrivals_and_terminal_once | REPLACED / ADAPTED |
| determinism_tests.cpp | Host_body_observer_noninterference_and_full_light_equivalence | REPLACED / ADAPTED |
| determinism_tests.cpp | Host_body_and_reconciliation_share_service_ready_directed_queue | REPLACED / ADAPTED |
| determinism_tests.cpp | Host_body_callback_guards_and_policy_install_boundaries | REPLACED / ADAPTED |
| determinism_tests.cpp | Host_body_payload_and_time_boundaries | REPLACED / ADAPTED |
| determinism_tests.cpp | Host_body_terminal_does_not_release_late_phase_policy_ownership | REPLACED / ADAPTED |
| determinism_tests.cpp | Host_body_admitted_notification_survives_disconnect_but_not_tip | REPLACED / ADAPTED |
| determinism_tests.cpp | Host_scheduled_reconciliation_disconnect_counts_both_honest_directions | REPLACED / ADAPTED |
| determinism_tests.cpp | Host_scheduled_reconciliation_wire_disconnect_counts_outbound_and_reply | REPLACED / ADAPTED |
| determinism_tests.cpp | Host_body_request_and_serve_callbacks_reject_mutation | REPLACED / ADAPTED |
| determinism_tests.cpp | Host_body_inventory_is_looked_up_at_request_arrival | REPLACED / ADAPTED |
| determinism_tests.cpp | Host_removal_flushes_token_associated_admission_once_before_removal | REPLACED / ADAPTED |
| field_tests.cpp | T1_field_million_pairs_and_inverses | UNCHANGED |
| field_tests.cpp | T1_runtime_backend_conformance | UNCHANGED |
| field_tests.cpp | T1_batch_inverse | UNCHANGED |
| field_tests.cpp | T1_million_distinct_pair_solves | UNCHANGED |
| field_tests.cpp | T1_million_each_trace_class | UNCHANGED |
| peeler_tests.cpp | T5_exact_signed_differences | UNCHANGED |
| peeler_tests.cpp | T5_ten_thousand_uniform_full_domain_residuals | UNCHANGED |
| peeler_tests.cpp | T5_ten_thousand_focused_small_count_residuals | UNCHANGED |
| peeler_tests.cpp | T5_invalid_count_rejects_entire_append_batch_atomically | UNCHANGED |
| peeler_tests.cpp | T5_contradictory_singleton_zero_has_no_cycle | UNCHANGED |
| peeler_tests.cpp | T5_singleton_before_pair_rechecks_stale_pair_source | UNCHANGED |
| pooling_tests.cpp | T9_full_mesh_5_20_100_nodes_with_always_on_pooling | REPLACED / ADAPTED |
| pooling_tests.cpp | T9_three_node_pending_reference_holder_and_absent_peer | REPLACED / ADAPTED |
| pooling_tests.cpp | T10_fake_failures_cleanup_all_references_and_repeated_sources | REPLACED / ADAPTED |
| pooling_tests.cpp | T10_done_honest_donor_survives_false_not_found | REPLACED / ADAPTED |
| pooling_tests.cpp | T10_failed_donor_slots_released_for_honest_ninth | REPLACED / ADAPTED |
| pooling_tests.cpp | T10_wrong_body_is_peer_local_and_policy_rejection_is_not_fraud | REPLACED / ADAPTED |
| pooling_tests.cpp | T10_late_failed_token_cannot_poison_reconnected_honest_admission | REPLACED / ADAPTED |
| pooling_tests.cpp | T10_matching_invalid_collision_rejects_late_valid_body_explicitly | REPLACED / ADAPTED |
| schedule_tests.cpp | T3_ten_thousand_schedules_exact_first_256_indices | UNCHANGED |
| schedule_tests.cpp | T3_million_item_inclusion_frequencies | UNCHANGED |
| schedule_tests.cpp | T3_exact_integer_boundaries_and_exhaustion | UNCHANGED |
| session_tests.cpp | T8_node_constructor_rejects_invalid_local_config_domains | REPLACED / ADAPTED |
| session_tests.cpp | T8_live_body_result_validation_and_stale_precedence | REPLACED / ADAPTED |
| session_tests.cpp | T8_body_result_ignored_hash_fields_do_not_become_contract_errors | REPLACED / ADAPTED |
| session_tests.cpp | T7_static_reconciliation_7000_fresh_trials | REPLACED / ADAPTED |
| session_tests.cpp | T8_ten_sessions_with_all_removal_reasons_and_live_churn | REPLACED / ADAPTED |
| session_tests.cpp | T8_awaiting_admission_survives_timer_and_transfers_score | REPLACED / ADAPTED |
| session_tests.cpp | T8_tip_reset_cancels_awaiting_old_body_callback | REPLACED / ADAPTED |
| session_tests.cpp | T7_honest_root_match_with_excluded_raw_extra | REPLACED / ADAPTED |
| session_tests.cpp | T7_echoed_root_never_authenticates_fake_raw_body | REPLACED / ADAPTED |
| session_tests.cpp | T8_real_collision_body_removal_updates_root_and_tip_rekeys | REPLACED / ADAPTED |
| session_tests.cpp | T8_same_peer_positive_after_negative_and_removed_readmitted_id | REPLACED / ADAPTED |
| session_tests.cpp | T8_disconnect_cancels_inflight_token_before_payload_validation | REPLACED / ADAPTED |
| session_tests.cpp | T8_disconnect_retries_known_alternate_without_waiting_old_result | REPLACED / ADAPTED |
| session_tests.cpp | T8_awaiting_admission_survives_donor_disconnect_until_callback_or_tip | REPLACED / ADAPTED |
| session_tests.cpp | T8_same_session_negative_then_positive_reachability_trace | REPLACED / ADAPTED |
| session_tests.cpp | T8_pending_depends_on_current_fetch_or_live_decode_provenance | REPLACED / ADAPTED |
| setstore_tests.cpp | T6_interleaved_logs_and_pinned_snapshots | REPLACED / ADAPTED |
| setstore_tests.cpp | T6_log_cap_expires_oldest_pin_without_retargeting | REPLACED / ADAPTED |
| setstore_tests.cpp | T6_real_short_id_vector_and_collision_bucket_snapshots | REPLACED / ADAPTED |
| sketch_tests.cpp | T4_ten_thousand_random_incremental_sequences | UNCHANGED |
| sketch_tests.cpp | T4_duplicate_capacity_and_clear_are_atomic | UNCHANGED |
| timing_tests.cpp | T16_no_peers_positive_rtt_and_monotonic_time | REPLACED / ADAPTED |
| timing_tests.cpp | T16_terminal_status_correlation_and_no_immediate_reopen | REPLACED / ADAPTED |
| timing_tests.cpp | T16_loss_and_rtt_jump_eventual_exact_reconciliation | REPLACED / ADAPTED |
| timing_tests.cpp | T16_late_timer_uses_captured_deadline_without_catchup | REPLACED / ADAPTED |
| timing_tests.cpp | T16_forced_lost_continuations_and_live_edit | REPLACED / ADAPTED |
| timing_tests.cpp | T16_open_retry_keeps_logical_identity_across_own_edit | REPLACED / ADAPTED |
| voting_tests.cpp | T13_voting_math_exact_thresholds_and_hand_vectors | UNCHANGED |
| voting_tests.cpp | T13_exhaustive_small_supports_and_unanimous_populations | UNCHANGED |
| voting_tests.cpp | T13_explicit_infinities_saturation_and_stable_epsilon | UNCHANGED |
| voting_tests.cpp | T13_predictable_prior_wave_estimator | UNCHANGED |
| voting_tests.cpp | T13_rootmatched_candidate_yes_and_abstainers_are_not_no_votes | REPLACED / ADAPTED |
| voting_tests.cpp | T13_unfinished_mismatch_abstains_until_done | REPLACED / ADAPTED |
| voting_tests.cpp | T13_rootmatched_excluded_item_is_no_while_candidate_is_yes | REPLACED / ADAPTED |
| voting_tests.cpp | T13_pending_lambda_survives_result_timer_and_transfers_on_admission | REPLACED / ADAPTED |
| voting_tests.cpp | T13_frozen_requires_both_confidence_barriers_and_emits_once | REPLACED / ADAPTED |
| voting_tests.cpp | T13_colliding_body_changes_reset_root_confidence_without_id_change | REPLACED / ADAPTED |
| voting_tests.cpp | T13_unsampled_late_done_is_not_extra_item_evidence | REPLACED / ADAPTED |
| voting_tests.cpp | T13_admission_after_completion_invalidates_captured_root_and_evidence | REPLACED / ADAPTED |
| voting_tests.cpp | T13_node_estimator_uses_only_completed_previous_wave | REPLACED / ADAPTED |
| voting_tests.cpp | T13_node_fresh_uniform_distinct_samples_seeded_observations | REPLACED / ADAPTED |


## Other retained case obligations

The following nonvoting cases retain their workloads. Current replacement rules above control where older wording was superseded. No scalar item or root accumulator is introduced by an inherited case name.

| Test | File / spec | Requirement |
|---|---|---|
| T9_fetchable_unique_agreement | §§8,9 | Per-node unique bodies remain fetchable;after convergence each unique is in all honest W or no honest W;report split/nonfreeze outcomes |
| T12_confidence_bound_no_eviction_history | §§6.5,7,8 | All R plus livePending scores<=M+P;no sticky confidence epoch-mark table |
| T7_cells_raw_exclusions_candidate | §§6,8 | Cells/DIFF encodeR;nonmatching replies excludeR−W;POLL no exclusions |
| T16_fetch_validation_1ms | §9 | Unique bodies served from owners;body completion includes donorRTT,serialization and printed1ms validation |
| T6_current_set_interleaved_changes | current_store_tests.cpp | §5: 10000 seeded add/remove sequences, compare all current IDs/bodies and random cached prefixes to independent log replay after every operation; no pins/log retention |
| T6_current_collision_and_admission_sequences | current_store_tests.cpp | §§3,5: retained SipHash hand vector, multiple bodies per ID, duplicate no-op, partial/last-body removal, readmission seq and cache equality |
| T6_current_reset_rekeys_and_releases_capacity | current_store_tests.cpp | §5: tip and block-disconnect reset, surviving handles, cache extension to exact limit, no historical retention; overflow atomicity |
| T7_static_oneshot_7000_fresh_trials | poll_tests.cpp | §6: differences 0,1,2,3,10,100,1000, 1000 fresh seeds each, both sides; compare each successful decode to reply-time responder truth; no continuation; final candidate/body agreement |
| T7_small_difference_one_exchange | poll_tests.cpp | §6: honest distinct differences <=2 complete decoding with one POLL/REPLY_DIFF when inbound symbol0 decodes; equal roots use REPLY_MATCH, which does not prove raw equality |
| T7_reply_is_current_and_internally_consistent | poll_tests.cpp | §§5,6.1: interleave admissions/removals before delivery; cells/root/size/full exclusions all match a single reply-construction state; repeated polls may see changed state |
| T7_match_with_excluded_raw_extra | poll_tests.cpp | §§6,8: identical candidate root with unequal raw sets returns MATCH; assert candidate equality only |
| T7_match_assertion_does_not_authenticate_body | poll_tests.cpp | §§1,6,8: malicious echo never inserts body or authenticates raw membership |
| T7_decode_time_reference_and_partial_results | poll_tests.cpp | §6.2: own/Pending changes between send and receipt; frozen per-call Ref, independent residual checks, failed peel retains valid partial fetch opportunities but no item evidence |
| T8_constructor_and_body_result_validation | lifecycle_tests.cpp | §1: preserve invalid Config domains, live enum/hash/binding validation and stale-token precedence from three old T8 cases |
| T8_ten_rounds_all_removal_reasons | lifecycle_tests.cpp | §§5–7: 0–5 adds/removes each side before/during/between 10 rounds; every RemovalReason; no double residual update on fetched admission; exact next sufficiently-sized poll after quiescence |
| T8_pending_only_fetch_or_awaiting | lifecycle_tests.cpp | §7: six counterexamples: decode without fetch reservation, fetch-only without prior decode, result-to-admission gap, own removal without support, removal with live awaiting support, and ended support followed by repeated decode; no history/session support |
| T8_hash_bound_awaiting_preserves_pending_item_state | lifecycle_tests.cpp | §§6.4,7:preserve token/hash/generation/reservation and all item-state fields across timer,disconnect and suspension;matching admission preserves the lifetime once, subject to Q3;tip cancels |
| T8_tip_reset_cancels_old_generation | lifecycle_tests.cpp | §§1,5: stale results before payload validation; cancelled awaiting callback cannot resurrect old confidence |
| T8_collision_removal_rekey_and_readmission | lifecycle_tests.cpp | §§3,5,7: exact body/ID/root changes, rekey, positive/negative claims in different polls, all removal reasons |
| T8_disconnect_alternate_and_late_result | lifecycle_tests.cpp | §6.4: cancel inflight before payload validation; immediate known alternate; awaiting survives disconnect; reconnect gets fresh identity |
| T9_full_mesh_5_20_100_nodes | pooling_tests.cpp | §§6–8: original 5/20/100-node workloads and seeds, candidate/body agreement; every successful raw reply exact against host truth; release all retained state at round end/abandonment |
| T9_pending_holder_and_absent_peer | pooling_tests.cpp | §§6.2,7: three nodes, Pending hides a +decode from honest holder; success still discovers usable donors ; absent peer yields negative evidence without cancelling another live fetch |
| T10_fake_partial_and_successful_replies | pooling_tests.cpp | §6.4: real/fake mixed replies, each eligible fake fetched, failure removes unsupported Pending, real IDs reconcile, no fake R/Frozen insertion |
| T10_peer_local_failure_honest_alternate | pooling_tests.cpp | §6.4: not_found/wrong binding peer-local, policy rejection nonpunitive, matched invalid height-wide, honest donor after false failure; bound/collision cases preserved |
| T10_donor_slots_released_and_stale_results | pooling_tests.cpp | §6.4: eight occupied donor slots, failures free slots, honest ninth; cancelled late result cannot poison successful admission |
| T11_oneshot_wire_goldens_truncations | adversarial_tests.cpp | §6.1: exact independently written bytes for all four messages; every truncation, noncanonical CompactSize, suffix byte, count and integer overflow |
| T11_100000_malformed_per_wire_type | adversarial_tests.cpp | §§6.1,6.6: 100000 seeded malformed/oversized cases for EACH of four types; bounded allocation, no crash/assertion; concurrent honest polls continue |
| T11_single_reply_inconsistency | adversarial_tests.cpp | §6.6: false size/count, impossible count bound, inconsistent declared cell count, exclusion cardinality/duplicates/zero; report only independently provable faults |
| T11_failed_decode_is_not_misbehavior | adversarial_tests.cpp | §6.6: honest undersized replies and adversarial syntactically valid undecodable cells terminate; no penalty for peel failure alone; valid root vote still counted |
| T11_poll_identity_duplicate_old_tip_and_late | adversarial_tests.cpp | §§6,8: wrong peer/poll/context/generation, duplicate and out-of-order responses; no repeated evidence or fetch; late item evidence ignored |
| T12_global_and_message_limit_boundaries | adversarial_tests.cpp | §6.5: each approved bound -1/exact/+1, allocation before parse rejected, 2MiB total including full exclusions; accepted host state never blocked by stale peer models |
| T12_fixed_peer_state_and_reply_release | adversarial_tests.cpp | §6.5: allocated-capacity accounting after each call, fixed peer floor plus bounded current-round failed invariant-residual/index/exclusion buffers; repeated/duplicate failures cannot exceed the round workspace; nothing retained across rounds |
| T12_pending_union_and_failure_saturation | adversarial_tests.cpp | §§6.4,7: retain admitted/connection/Pending/fetch/awaiting/donor/failure-table boundaries and suspension regression; no eviction/refetch loophole |
| T12_fifty_heights_twenty_nodes | adversarial_tests.cpp | §6.5: original 50-height/20-node soak; last10 mean <=1.1*first10; height rollover uses bounded sizing records; retained global bounds and all actual transient capacities checked |
| T7_candidate_nonce_proof_vectors | poll_tests.cpp | §6.1: independently derived domain0/domain1 SipHash vectors, LE key/ID/proof bytes, empty/set XOR, order, collisions and nonce binding |
| T7_match_excluded_raw_extra_and_churn | poll_tests.cpp | §6.1: unequal raw sets with identical candidates yield valid proof; root change in flight accepts stored-proof MATCH; mismatch reports inconsistent_reply |
| T7_approximate_prepeel_likelihood | sizing_tests.cpp | §6.3: maximize independent likelihood over[L,2M+P],smaller tie,above-domain censor at L;{0} zero=>0 else censored;hostile input never authenticated |
| T7_probe_indices_and_round_censoring | sizing_tests.cpp | §6.3: approved sparse mode/basis, lowest-index clipping, zero-R{0}, round-median censor decision, no per-peer probe state |
| T7_empirical_request_argmin | sizing_tests.cpp | §6.3:quantile-mean CDF/cost ties;median censor independently doubles;zero-decode requires fallback cells and no successful decode/DIFF;only MATCH/silence with no samples keeps n; DIFF samples use the normal estimator and may shrink n |
| T7_diff_only_round_shrinks_request | sizing_tests.cpp | Start from an existing oversized prefix; all timely replies are valid REPLY_DIFF with small exact differences. With an independent synthetic quantile fixture whose normal cost argmin is smaller than the prior prefix, assert n_next equals that argmin and shrinks. DIFF is a decode success; no zero-decode trigger. Retain separate censored-median and zero-decode doubling tests unchanged |
| T7_first_height_and_height_rollover | sizing_tests.cpp | §6.3: scaled individual previous-round1 samples rounded up,empirical argmin,zero previousR fallback,consumed bank overwrite;two1024-record banks independent of currentD |
| T7_frozen_table_generator_and_interpolation | sizing_tests.cpp | §6.3:2000 trials,SplitMix64 ID rejection then next-output sign,cap=floor((2MiB−109)/28),grid endpoint4096;20 stored quantiles,step CDF,next-larger-d and scaled tails;S=rank1000,linear median interpolation;CDF next-larger-grid |
| T7_responder_formula_and_full_exclusions | sizing_tests.cpp | §6.1: own raw sizes, exact prefix m formula and probe alternative, full exclusions, header byte accounting and2MiB at M boundary |
| T11_proof_wire_identity_and_invalid_abstention | adversarial_tests.cpp | §§6.1,8: all truncations, old wire version, unknown/duplicate nonce/poll, wrong proof is reported but never root/item evidence |
| T11_stateless_responder_host_rate_limit_boundary | adversarial_tests.cpp | §6.6: every well-formed poll answered with current data, no retained per-peer flood/reputation state, no core poll_flood; host drops separately observed |
| T12_sizing_and_item_state_capacity | adversarial_tests.cpp | §6.5: current/round1 banks, M+P bounded Snowball item-state records and current-round observations; no confidence-derived epoch marks, transient start-estimator ledger, sparse protocol buffers charged;growable test audit separately owned/reported; no history after ID removal |
| T16_silent_slow_matching_twentyfive_rounds | timing_tests.cpp | §8:controlled victim+32 peers,23fast1ms/6silent/3slow100ms,beta.2,epsilon1e−9,fixture K=8 at D32;>=99% of1000 fixed seeds freeze within25 rounds;report all failures;no DP-derived bound |
| T16_majority_all_answer_and_fallback | timing_tests.cpp | §§6.6,8: first strict-majority time,2*t_maj grace,all answered,4*captured PeerCaps median; earliest wins; zero answers still advance |
| T16_ten_percent_loss_two_and_five_nodes | timing_tests.cpp | §8:10% seeded loss each directed link, eventual candidate agreement in honest fixtures; fallback advances rounds without continuations |
| T16_time_order_ties_late_timer_no_catchup | timing_tests.cpp | §§1,6.6: Time order/peer-id ties, replies before timers, upper RTT median>=1us; malformed/invalid-proof arrivals count timing but not evidence; late timer evaluates once at actual time |
| T16_late_reply_discard_all_effects | timing_tests.cpp | §§6,8: expired-round REPLY/MATCH discarded without decode/fetch/sizing/votes, no retained past-round slots; stale context ignored |
| T16_no_peers_connect_disconnect | timing_tests.cpp | §§1,8:initialD0 idles;connect starts next eligible round;during round disconnect abstains without discarding captured item observations or changing captured sample;fallback progresses even if all disconnect |
| T7_approximate_estimator_calibration | sizing_tests.cpp | §6.3:Delta10/50/150/500,1000 trials each,prefixS;include censored lower bounds;mean[.9,1.1],nearest-rankp90[.7,1.4],report censor counts,no retuning |
| T7_now_vs_round_start_estimate | sizing_tests.cpp | §6.3:undo only currently-present round additions,remove departed IDs,unchangedR/Pending transition not logged;P-list overflow disables start estimate for round and uses now without penalty/abandonment |
| T12_id_churn_releases_item_state | adversarial_tests.cpp | §§5,8: more than M distinct IDs across repeated remove/admit while live R<=M; no historical item-state growth; readmission starts a fresh admitted lifetime |
| T7_failed_reply_rescued_by_other_peer | poll_tests.cpp | Peer A fails alone; peer B's decoded items enter Ref via legitimate live fetch support; peer A then succeeds, with the same reconstructed candidate set and item evidence as fresh decoding C against its rescue-time Ref; no insertion into R |
| T7_retained_residual_every_ref_transition | poll_tests.cpp | §6.2:harness retains independent wire bytes;core retains one invariant residual,never raw copy;private peel copy discarded;each netRef delta once;negative claims never directly mutate invariant; partial peels supply no item observations |
| T7_cascade_poll_order_and_single_observation | poll_tests.cpp | §6.2:smallest dirty poll repeatedly,earlier rescue from later poll;success releases,failure retained clean;no item observations before full completion; no duplicate observations/sizing/fetch;<=K*(1+RefChanges) attempts and no dirty reply at return |
| T12_retained_reply_workspace_and_release | adversarial_tests.cpp | §6.5:<=K residual arrays,indices,exclusions<=K*M,one transient work buffer;no second raw copy;growable observation audit excluded from protocol reservations;allocation failure fails test;release all at boundary |
| T15_same_seed_rescue_transcript | determinism_tests.cpp | Same seed produces identical Ref deltas,rescue order,actions and evidence within one process and across processes |
| T16_round_end_or_tip_cancels_rescues | timing_tests.cpp | No cross-round retention; late replies discarded; root-changing admission preserves eligible item observations; only round end/tip releases retained replies; no root-confidence reset or veto |
| T7_rescue_original_sizing_sample_only | sizing_tests.cpp | Both sizing estimates captured once before first peel; repeated rescue attempts never add/rewrite samples; sample bank bounds unchanged |
| T7_quantile_table_all_levels | sizing_tests.cpp | §6.3:20 levels(5%..95% and100%),rankceil(q*N),repeated quantile values,maximum/cap;median S is stored50%,rank1000 |
| T7_probability_mean_of_distributions | sizing_tests.cpp | Hand distributions where mean F_d(n) differs from threshold-counting S(d)<=n; verify mean, cost argmin and smaller-n tie; responder still uses median floor |
| T7_cdf_grid_tail_and_large_difference | sizing_tests.cpp | §6.3:largest qualifyingq stepCDF,below5%=0,atmaximum=1;next-larger d between grid points;ceil-scaled each quantile beyond4096 |
| T11_peel_failure_not_attributable_to_reply_peer | adversarial_tests.cpp | Poison Ref via another peer's fabricated Pending ID; contradiction/repeated claim/bound failure on first/rescue peel discards without PeerMisbehaved; separately prove structural/proof faults still report |
| T12_cascade_attempt_and_aggregate_audit_bounds | adversarial_tests.cpp | No ID re-entersPending in one call;attempts<=K*(1+RefChanges),no dirty remainder;complete growable observation audit;first peel counts once,delta event per(item,reply);audit allocation failure is test failure,never protocol ResourceLimit |
| T7_median_rank1000_and_distinct_CDF_interpolation | sizing_tests.cpp |2000 sorted trial outcomes with distinct1000/1001: S uses1000; S linear interpolation and F next-larger-grid remain distinct |
| T7_stalled_retained_contradiction_discarded | poll_tests.cpp |Ordinary undecodable/stalled cells stay rescue-eligible;explicit repeated/sign/bound contradiction discards with no peer penalty;structural faults checked before peel only |
| T15_full_audit_observation_noninterference | determinism_tests.cpp |Full/simulation/production modes: identical calls,Actions,transcripts,RNG and host truth;only observation recording differs |
| T12_observation_allocation_failure_is_test_failure | adversarial_tests.cpp |Inject failure in observation-owned audit allocation: fail test recording,never emit protocol ResourceLimit or report truncated audit as success;separate protocol-byte accounting |
| T7_attempt_and_delta_audit_units | poll_tests.cpp |Count initial peel once,each rescue once;one delta record per(item,reply) regardless touched cells;verify attempt bound and no dirty reply at call end |
| T7_zero_decode_prefix_doubles_to_cap | sizing_tests.cpp | Scripted structurally valid cell replies never decode;positive prefix n strictly grows each censored/zero-decode round by at least2x until capped;never returns to probe;estimator cannot lower floor,checked arithmetic,no continuation |
| T7_successful_rescue_suppresses_zero_decode_floor | poll_tests.cpp | Every arrival initially stalls but one reply is rescued before round end;do not apply zero-decode floor;another round with no success does apply it |
| T7_zero_decode_gate_no_cells_and_cap | sizing_tests.cpp | §6.3:only MATCH/silence with no samples keeps n; DIFF samples use the normal estimator and may shrink n;successfulDIFF suppresses zero-decode trigger;censored median independently doubles;probe transition=max_sent_index+1 clipped to cap;no return to probe |
| T7_poll_success_reply_diff_bidirectional_fetch | poll_tests.cpp | Successful inbound decode gives exact missing/wanted signed raw-set difference; poller fetches missing, host sends wanted without getdata; receiver callback/reservation assertions await Q4. No inbound votes or sizing samples |
| T7_poll_state_consistent_prefix_and_probe | poll_tests.cpp | POLL root/raw set_size/cells from same state,exact prefix or clipped probe indices;later changes do not alter sent bytes |
| T7_poll_matching_root_skips_decode | poll_tests.cpp | Structurally valid matching root yields proof,no peel attempt/fetch/sizing sample;poll-cell bytes still counted |
| T11_poll_cell_structural_faults_reported | adversarial_tests.cpp | Raw symbol0/size mismatch,impossible counts,index/length/grammar/overflow reported before peel,including matching-root path |
| T11_poll_peel_contradiction_still_replies | adversarial_tests.cpp | §6.6:contradictory inbound attempt discards ALL its effects silently before fallback;ordinary incomplete positives may fetch;structural faults still reported |
| T12_poll_decode_transient_P_bound | adversarial_tests.cpp | One transient working buffer and<=2M inbound claims against ownR only;no POLL retention/rescue;fetch union<=P;both116-byte poll and109-byte reply/full-exclusion limits fit2MiB |
| T7_poll_pending_updates_outbound_invariant | poll_tests.cpp | §6.2:inbound Pending updates all retained invariants exactly once and triggers normal ordered rescue;no inbound retention,no new sizing sample |
| T15_poll_cell_byte_accounting | determinism_tests.cpp | Exact28*m sent/received poll-cell bytes,framing separately counted,identical mode transcripts;MATCH proof16/full application58 bytes |
| T7_poll_decode_reference_excludes_pending | poll_tests.cpp | Responder Pending differs from R;inbound decode uses R only,missing/wanted reflect two raw sets,not speculative Pending |
| T7_poll_incomplete_falls_back_to_cells | poll_tests.cpp | §6.1:ordinary incomplete inbound peel may fetch partial positives then replies with cells;contradiction discards all attempt effects then replies with cells;no inbound retention |
| T11_reply_diff_goldens_and_100000_malformed | adversarial_tests.cpp | Kind3 independent byte goldens,every truncation,100000 seeded malformed cases,ordering/zero/duplicates/overlap/count overflow/size relation/exclusion bounds;no partial effects |
| T11_reply_diff_wanted_sent_membership | adversarial_tests.cpp | §6.1:wanted validated against one round raw capture,including excluded IDs;post-send removal does not falsely penalize;missing ID or signed size mismatch reports inconsistent_reply |
| T12_reply_diff_full_payload_bound | adversarial_tests.cpp | §6.5:complete DIFF over message limit falls back to cellREPLY;no truncation/fragmentation;check both exact boundary and full list bytes before effects |
| T10_reply_diff_fake_ids_require_bodies | pooling_tests.cpp | Structurally valid missing assertions may be fake;FetchBody/host validation unchanged,no direct R/Frozen insertion,existing failure/probation behavior |
| T15_poll_match_wasted_cell_bytes | determinism_tests.cpp | Matched-exchange poll cells charged separately once;DIFF ID bytes and fallback cell bytes separated;all counts reproduce exact wire sizes |
| T16_fetch_RTT_serialization_validation_midround | timing_tests.cpp | Host body service=donorRTT+body serialization+configured validation delay;callback at actual completion including mid-round,never batch to round end |
| T10_latency_metrics_bounded_lifetimes | lifecycle_tests.cpp | §10:first-decode timestamp in live fetch/awaiting record survives donor retries;host admission without prior decode has no sample;P-bound and no historical decode table |
| T7_censored_prefix_never_returns_to_probe | sizing_tests.cpp | Scripted true difference always above request;each censored/zero-decode prefix strictly grows until success/cap;estimator cannot reduce floor or switch to probe |
| T12_one_round_capture_shared_by_all_slots | adversarial_tests.cpp | One shared admitted raw-ID/incarnation/candidate-bit capture, never K copies; MATCH also needs capture-time Pending lifetimes. Exact Pending capture representation/bound is Q3; test actual capacity and release at round end/tip |
| T7_deferred_poll_never_creates_second_capture | poll_tests.cpp | Later send shares capture only ifR unchanged;otherwise defer to next round,no new capture or mixed-state cells/root |
| T7_diff_now_start_exact_list_counts | sizing_tests.cpp | missing already inPending/R,wanted removed since send,post-capture admissions;exact specified now/start formulas at reply entry before fetch effects |
| T7_probe_span_then_monotone_prefix | sizing_tests.cpp | Unusable/censored probe=>max index sent+1 capped,otherwise estimator;once prefix exists never probe again,including all-MATCH/silent rounds |
| T7_pending_absent_from_root_proof_size_cells | poll_tests.cpp | Pending affects decodeRef only;never candidate root,expected proof,raw set_size,own encoded cells or exclusions until validated admission |
| T7_fallback_double_prefix | §6.1 | Failed prefixPOLL produces prefix length min(cap,max(2n,S(size difference)));test floor-dominant,doubling-dominant,cap and overflow inputs |
| T7_probe_fallback_dense_prefix | §6.1 | Failed sparse probe yields dense prefix sized from twice largest actually sent index+1,with floor and cap;never echoes sparse reply cells |
| T7_fallback_no_partial_wire_payload | §6.1 | Fallback contains own raw cells and exclusions only;no partial IDs,residuals or bitmaps |
| T7_diff_missing_wanted_true_difference | §6.1 | missing is responder-only,wanted is poller-only;strict order,disjointness,exact capture-based count relation and raw-set truth |
| T11_diff_wanted_capture_validation | §6.1 | wanted must belong to sent raw capture;currentR/Pending cannot substitute;reject before any body-send/fetch/evidence effect |
| T8_missing_first_donor_dedup | §§6.1,7 | First valid reply names donor;concurrent duplicates do not duplicate fetch;failure/alternate-donor behavior awaitsQ5 |
| T8_wanted_immediate_host_send | §§1,6.1 | Valid DIFF triggers host body-send immediately,no separate getdata,no reply-body embedding;binding/reservations awaitQ4 |
| T8_wanted_removed_body_and_loss | §§1,6.1 | Cover sent-capture removal,late/duplicate DIFF,invalid body,loss and callback cleanup;Q4 fixes exact expected outcomes |
| T7_fallback_no_back_propagation | §6.1 | Decoding fallback never emits body-send of poller-only IDs;responder's later own poll may discover them |
| T12_wanted_reservation_bounds | §§6.5,7 | Wanted-driven body delivery stays withinP and action/message bounds;no unsupported Pending or unbounded awaiting records;Q4 |

## Files and freeze/removal plan

Independent field/schedule/model oracles remain unchanged; operation-log truth is test-owned, not protocol history. Add independent sizing/proof oracles and hand-derived self-tests. Freeze generator, seed, table digest and generator self-tests. Proposed paths: test/oracle/{sizing.h,sizing.cpp,proof.h,proof.cpp}; test/generator/{sizing_table.py,README.md}; test/data/sizing_table.csv. Seed0x534E4F5753544F52; no table generation in this step. Full-audit observation storage is test-owned and growable, not a production reservation. Extend frozen inventory and extra-file detection to these new contract directories. Reference peeler for generation is independently written, not an import of production code. Table domain is fixed through4096 with approved linear extension; generation cap=floor((2MiB−109)/28).

Keep primitive math tests unchanged. Replace supplemental verify/voting_early_tests.cpp full-K/early-freeze and root-SPRT policy tests with approved round-end/answerer tests in the correction and freeze them; do not retain the superseded policy as a current acceptance requirement. Keep underlying arithmetic regressions including finite DP labelled as primitive-only evidence. The production preview helper is obsolete policy and must be adapted only after external review.

Contract edits after approval: CONTRACT.md; public include/snowstorm/{setstore,messages,types,stats,voting}.h and node.h only for approved necessary declarations; test/harness/{host.cpp,host.h,transcript.cpp,transcript.h}; test/acceptance/{fixture.cpp,fixture.h,pooling_tests.cpp,adversarial_tests.cpp,voting_tests.cpp,timing_tests.cpp,determinism_tests.cpp}; test/CMakeLists.txt; freeze checker inventory where needed; ACCEPTANCE.sha256. New acceptance files: current_store_tests.cpp,poll_tests.cpp,lifecycle_tests.cpp,sizing_tests.cpp. Existing public field/short-ID/cell/schedule/sketch/peeler declarations and primitive algorithms remain unchanged.

Dedicated STEP 3 removal paths, with each listed verbatim in commit message:

- src/snowstorm/src/session_request.cpp
- src/snowstorm/src/session_request.h
- src/snowstorm/src/session_responder.cpp
- src/snowstorm/src/session_responder.h
- src/snowstorm/src/session_model.cpp
- src/snowstorm/src/session_model.h
- src/snowstorm/test/acceptance/session_tests.cpp
- src/snowstorm/test/acceptance/setstore_tests.cpp

All still-applicable body/store tests must have approved replacements before deletion. Mixed current-store/snapshot files src/setstore.cpp,src/store_engine.h and include/snowstorm/setstore.h are edited, not blindly removed; retained shared codec byte/cursor primitives stay. Edit obsolete message sizing/range plumbing and wave/Pending policy after external review, not during contract correction. No removal of other paths without listing the proposed scope first.

STEP 2 retains old files unregistered but hashed; records both manifest states for review, compiles corrected tests against headers without stubs, commits source correction then parent spec/rendered HTML/pointer with existing tooling, runs frozen check and stops for external review. STEP 3 removal changes only approved deleted paths, associated CMake source lists and manifest entries. No new protocol implementation mixed with that commit. Then one module per source commit, immediate parent pointer commit. No push, branch/worktree creation or bypass of publication checks.

## Validation and mutation plan

Full normal acceptance, ASan+UBSan, ENABLE_SNOWSTORM=OFF configure/build and no-added-Snowstorm-input audit follow implementation, not this proposal. Keep T14 no-oracle access and T15 same-/cross-process byte-identical transcript checks. Keep all original field workload counts,7000 T7 trials,5/20/100-node T9,100000 malformed messages per NEW type,50-height20-node soak, and host-equivalence cases. Changed sizing/statistical fixtures report their actual seeds/configuration and outcomes.

Mutations: T1 wrong field reduction; T2 bypass reference-sign check; T3 wrong schedule boundary; T5 omit scheduled subtraction; T7 use send-time Ref instead of decode-time Ref; T10 preserve unsupported Pending after failure; T13 use fixed M1tx instead of prior M1hat for item-vote sign, and separately count a partial peel as an item vote; T16 omit fallback or substitute first-answer timer for strict-majority rule. Each mutation compiles, fails its named frozen test, restores exact source bytes, passes, and ends with both repos clean. Never edit tests to accommodate the mutant.

## Stages and stop boundary

Stage A covers nonvoting arithmetic, current-store membership, codec/POLL/DIFF/fallback, sizing, body binding, retained-residual rescue, hostile input, bounds and deterministic host behavior. It uses test-owned candidate snapshots, not a substitute voting implementation. Q4/Q6 and the additional resource/structural findings must be resolved where applicable.

Stage B covers item-round state, sign observations, MATCH equivalence, the round-count gate, FINAL, root settlement/freeze, full-node agreement, candidate/body churn and all complete-node T1–T16 workloads. It must not stub voting, retain a batch accumulator, or pass by weakening obsolete tests. The exact open-case expectations below must be resolved before freezing those cases. Argon’s simulator evidence remains distinct from executed acceptance tests; the earlier requirement for Shammah to confirm Argon’s results is retained.

No freeze, production implementation, host-relay change, table generation or simulator execution is performed by this regeneration. Git commits for the review round are explicitly authorized. Regenerate, list open issues, commit the review round, then STOP for the spec owner’s next decisions.

## Remaining contract questions

Q1 — Round-count gate order and boundaries. Define the empty-W mean, simultaneous preference/exits/entry order, and whether admission tests the mean immediately or only at round end. Example W counters {0,10}, outsiders c=10 and c=5: simultaneous mean 5 admits both, sequential entry can raise the mean to 20/3 and exclude the latter. Post-freeze reopening is now resolved: later gate admission invalidates the freeze; no next-epoch latch is used.

Q2 — CLOSED by the operator: no item votes from partial peels. No partial-voting metadata or end-round partial-vote recomputation is needed. Existing retained residuals and rescue/fetch behavior remain. This closes the former partial-evidence/memory question without adding a mechanism.

Q3 — Observation and admission lifetime. Resolve captured-incarnation eligibility versus current R union Pending scope, ordinary post-capture admissions and removed/readmitted IDs. MATCH now explicitly refers to captured R union Pending, while the shared capture previously bounded only M admitted records; define a bounded Pending capture/lifetime representation. Define transfer of all Snowball state on matching Pending admission: fresh admitted preference is in, but existing Pending may prefer out or be FINAL out. No dead lifetime histories or duplicated observations.

Q4 — wanted host action and callbacks. The amendment requires an immediate host send without getdata,but the existing public API has no body-send action and FetchBody results require a fetch_id. Proposed SendBodies{peer,short_ids} is explicit for review. Define how the responder reserves live Pending/awaiting state for these incoming bodies,binds results,and handles loss/timeouts/invalid bodies without a second getdata;also define sender behavior if a wanted capture ID's body was removed before the reply. Preserve host validation and exactly-once obligations. No implementation can infer these details safely.

Q5 — First donor and retry. “Fetch each body once,from the first reply naming it” may mean deduplicate concurrent fetches while retaining existing honest-alternate retry after not_found,or prohibit retries. The prior T10 recovery requirement needs retries. Clarify the lifetime and failure behavior;do not silently weaken donor recovery tests.

Q6 — Canonical fallback grammar. Fallback after a probe is now a prefix. The proposal retains REPLY's existing mode/basis fields,sets mode0 and echoes basis_size as metadata. Confirm that canonical encoding or explicitly remove the redundant fields and recompute header/cap bounds. List renaming itself changes no encoded bytes.

Q7 — CLOSED: the replacement amendment selects Snowball per-item round counts and removes separate batch root confidence. Broot remains only a derivation constant for Btx; it is not a freeze condition or retained root state. MATCH contributes compact item votes and later gate entry invalidates a freeze.

Q8 — Derived-threshold endpoints. The formula has p_error=0 at D=1 (division by infinity) and beta_round=1 at supported D=1024, beta_adv=0.2, epsilon=1e-9 (K=256, y_star=182, p_error approximately 0.0000184182). Thus the five reference rows do not establish that every supported population avoids one-round FINAL. Define endpoint handling, numerical ceiling at integer boundaries, and whether the one-round prevention claim is restricted to a stated population range. Do not insert a minimum threshold without the author’s decision.

Q9 — Calibration and estimator scope. beta_round uses full K and M1tx, whereas actual item votes may use smaller Kx and a different prior-rate M1hat. At D=500, M0=300, M1hat=500, Kx=1, one yes votes IN under the null with probability 0.6; beta_round=2 is calibrated using p_error about 0.002. Two independent IN observations occur with probability 0.36 under that null, not p_error squared. This is a local classifier/calibration counterexample, not an executed whole-node split-freeze attack. Clarify the claimed probability scope, response and round-dependence assumptions. Also specify saving the last valid observed rate and reprojecting/clamping it after D changes, rather than retaining an out-of-domain numerical M1hat. Do not silently change the accepted vote or beta formulas.

Q10 — FINAL and population transitions. Specify whether FINAL state stops accepting item updates, whether FINAL out is immutable for the lifetime, and what happens to c, its cap, and existing FINAL records when a D change recomputes beta_round. For example c=6 under beta_round=7 followed by a decrease to beta_round=4 makes “c capped at beta_round” and “FINAL when c equals beta_round” ambiguous without a transition rule. Counter overflow otherwise follows §1; no new saturation mechanism is implied.

Q11 — CLOSED by the replacement amendment: verified MATCH proofs contribute captured per-item yes/no observations and are counted in Kx and Yx. They are not full algebraic decodes and supply no independent root-confidence evidence. Captured Pending representation remains Q3.

Q12 — Empty-set freeze versus the no-one-round test. With W empty, “every item in W is FINAL-in” is vacuously true. Empty epoch-start W can therefore freeze on its first matching round. Even from W={x}, the first OUT vote can flip preference, remove nonfinal x, and leave W empty before any item reaches FINAL. Define the intended empty-set behavior or the scope of “no freeze after one round”; no extra delay, dummy item, or root-confidence gate is invented.

Q1, Q3, Q4, Q5, Q6, Q8, Q9, Q10 and Q12 remain open; Q2, Q7 and Q11 are closed. The three accepted corrections and replacement item/root round-count amendment are applied. No scalar item likelihood accumulation or separate root-confidence state remains in this proposal. The raw hypergeometric function is used only for an individual round’s sign and threshold calibration. Provisional K, raw-set dissemination, stateless polls and host-relay scope remain. Argon owns simulation with fetchable uniques and printed 1 ms validation. Frozen headers, harness, tests and production code have not been changed by this regeneration. Additional review findings are in `.scratch/impcd/iteration-1/findings.md`.
