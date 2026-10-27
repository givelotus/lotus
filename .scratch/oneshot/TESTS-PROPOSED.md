# Snowstorm executable-contract test proposal — review round 5

Regenerated in place from the maintained input bundle, SHA256 `fb84e15abe521460cd55f65f693835b8047be070075191729fe07df0128e9d96`. The final per-item reply-vote and partial-peel instructions control over all earlier vote wording. No frozen test/header/harness/oracle/manifest or production implementation is changed. Argon owns simulations with fetchable uniques and printed 1 ms validation.

## Current replacement contract

- Sample K=min(D,ceil(D/4)); capture alpha=floor(((1+beta_adv)/2)*K)+1. Only yes>=alpha or no>=alpha succeeds. Abstention never shrinks the quorum.
- beta_c=Btx=ceil(ceil(log2(25/epsilon))/3), independent of D, equals 12 at epsilon=1e-9. No likelihood, hypothesis, adaptive match-rate estimator or root accumulator remains.
- Preference changes only on strict cumulative-success-count overtaking. Same-side successive successes advance c; a changed side starts at one. Every no-success round resets nonfinal c to zero, including zero usable replies. FINAL accepts no further updates.
- Capture raw admitted IDs with incarnation/candidate bit plus Pending lifetimes present at round start, at most M+P records. No post-capture item votes. Matching Pending admission preserves all state, including preference and FINAL-out.
- DIFF reconstructs from captured raw R. MATCH supplies captured preference observations. At arrival, decoded-present/nonexcluded=>YES, decoded-absent or excluded=>NO. With residual, other captured items abstain; without residual, other eligible captured reference items are shared and vote yes unless excluded. Rescue-only discoveries abstain that round. No inferred-sharing partial votes or per-reply evidence buffers remain.
- Evaluate the gate once at round end after item updates: gate_value=c only when previous success side is IN, otherwise zero. Use one pre-entry/pre-exit W snapshot and mean gate_value (empty mean zero); apply all entries/exits simultaneously.
- Fixtures run to a horizon long enough to finish and report freeze-round distributions; hard assertions remain zero false freezes and zero split freezes.
- Freeze iff (W nonempty and all W is FINAL-in) or (R union Pending empty). Later gate entry invalidates the root freeze; no empty-W vacuity shortcut.
- Body traffic in both directions uses ordinary FetchBody. wanted is only a description for votes; it is not a body request and triggers no host body-send action.
- Fallback REPLY is a dense prefix with no mode or basis_size. Headers: REPLY 100, POLL 116, DIFF 109 bytes conservatively. Shared cell cap includes max_symbol_index+1 as well as both message byte limits.
- DIFF samples use normal next-request sizing and may shrink n; no-sample MATCH/silence retains n. Doubling triggers are unchanged.

## Current quorum, state and correction cases

These are test requirements for a future executable-contract correction, not claims of executed node acceptance.

| Test | Coverage | Required assertion |
|---|---|---|
| T13_quorum_and_consecutive_constants | §8 | Independently compute K/alpha/beta_c exactly for the five rows below; epsilon=1e-9 gives beta_c=12 regardless of population |
| T13_full_sample_quorum_with_abstainers | §8 | alpha-1 eligible votes cannot cause success even if every usable reply agrees; silence, lateness, invalid proof and partial abstention never reduce alpha |
| T13_zero_yes_first_round_not_final | §8 | A first OUT success at the reference parameters gives c=1 and is not FINAL; absence of success gives c=0, not an imputed OUT success |
| T13_final_requires_twelve_consecutive_successes | §8 | Fewer than beta_c same-side preferred successes cannot finalize; exactly beta_c can. Opposite success restarts at one; nonpreferred streak does not finalize until preference agrees |
| T13_no_success_resets_streak | §8 | With a nonzero streak, no quorum resets c to zero but preserves preference and cumulative side counts; include no replies, partial abstentions and zero decoded replies without MATCH |
| T13_preference_overtake_and_tie | §8 | Increment one side count once; flip preference only when it strictly overtakes the preferred count; ties retain preference |
| T13_final_lifetime_immutable | §8 | After FINAL-in or FINAL-out, later opposite/no-success rounds cannot change any item state; tip reset or loss of the item lifetime releases it |
| T13_population_change_preserves_state | §8 | D changes affect next captured sample/alpha only; beta_c, existing c, cumulative counts and FINAL are unchanged |
| T13_gate_simultaneous_prechange_mean | §8 | W gate values 0,10 and outside-IN gate values 10,5 use mean 5 and admit both regardless of iteration order; include simultaneous exits, equality and empty-W mean zero. Positive gate values require previous success IN; previous OUT or absent contributes zero even when c is positive, in both the W mean and entry comparison |
| T13_gate_only_at_round_end | §§5,8 | A mid-round fresh/transferred admission changes R only; its candidate entry waits until the single end-round gate |
| T13_capture_pending_and_postcapture_abstention | §§6,8 | Capture<=M+P records includes round-start Pending; post-capture items get no votes; old admitted incarnation cannot lend votes to readmission |
| T13_pending_admission_preserves_whole_state | §§6.4,7,8 | Transfer both side counters, c, previous success, preference and FINAL intact. In particular Pending FINAL-out is still OUT after admission; fresh ordinary admission is IN with zero counters |
| T13_match_equals_full_candidate_observations | §§6.1,8 | Verified MATCH and equivalent full reconstruction produce identical captured item yes/no observations, including raw excluded and Pending IDs; no raw-set equality/body-possession claim |
| T13_diff_local_excluded_peer_included_yes | §§6.1,8 | Captured raw R contains locally excluded x; peer includes x; empty-list DIFF supplies an eligible yes for x |
| T13_complete_arrival_unclaimed_shared | §§6.1,6.2,8 | Complete arrival infers other eligible captured reference items shared and yes unless excluded; captured Pending absent from a complete DIFF raw assertion is no, not shared |
| T13_arrival_exclusion_overrides_presence | §§6.1,8 | Peer holds x but excludes it: no for complete DIFF, full arrival peel or partial explicit-present outcome; MATCH no outside captured W |
| T13_partial_explicit_preference_observations | §§6.2,8 | Incomplete arrival: explicitly decoded present and nonexcluded=>yes; decoded absent or excluded=>no; all other captured items abstain. Holding but excluding is no |
| T13_partial_unclaimed_items_abstain | §§6.2,8 | Unclaimed captured items abstain while residual remains, even if a received cell is zero or no Pending item is scheduled there. No cell/schedule-only inference |
| T13_arrival_evidence_lifetime_and_storage | §§6.2,6.5 | Arrival observations use existing bounded round-evidence records; no per-reply cell-index buffers, second cell array or evidence-only peel. Captured lifetime filters and round/tip cleanup remain |
| T13_rescue_only_discoveries_abstain | §§6.2,8 | Items first decoded or inferred shared by rescue abstain that round, including full and same-call cascade rescue. Keep valid initial arrival observations unchanged; no duplicate/upgrade |
| T13_no_one_round_nonempty_freeze | §8 | Starting nonempty W with all sampled peers matching yields c=1, not FINAL; no freeze after one round |
| T13_empty_W_nonempty_support_does_not_freeze | §8 | W empty while R or Pending nonempty never freezes, including first-round exit of the sole nonfinal candidate and admitted FINAL-out items |
| T13_truly_empty_state_freezes | §§6,8 | R union Pending empty can freeze with empty txids, including D=0; no fake timer/sample requirement or duplicate Frozen action |
| T13_later_gate_entry_invalidates_freeze | §8 | Frozen nonempty W has mean gate value beta_c. A live Pending x after 11 IN,1 OUT,11 IN,12 OUT successes has d[in]=22,d[out]=13,p=in,c=12,previous=out,not FINAL. Admission preserves state; a further OUT success leaves its gate value zero and it cannot enter frozen W. Require twelve subsequent IN successes to become FINAL-in and pass the beta_c gate; entry changes the root and invalidates the old freeze. Also test previous-IN FINAL-in entry and zero contributions from previous-OUT members when computing the W mean |
| T13_no_obsolete_confidence_state | §§1,8,10 | Corrected future API/state/Stats/transcript has no root accumulator, scalar item likelihood, match-rate estimator, hypothesis parameters or root-change scoring veto; Broot only derives Btx |
| T13_unique_final_side_agreement | §§8,9 | Fetchable unique items reach the same FINAL side at all honest nodes in the required quiescent fixtures; report adversarial disagreement/nontermination without retuning seeds |
| T13_strict_quorum_zero_adversary_boundary | §8 | D=5,K=2,beta_adv=0 gives alpha=2: yes=no=1 causes no success. Check 2*alpha>K over supported populations and valid adversary fractions; IN/OUT cannot both succeed |
| T7_diff_only_round_shrinks_request | §6.3 | Independent quantile fixture and small exact DIFF samples choose a smaller cost argmin than the old prefix; verify shrink and unchanged conditional doubling |
| T11_reply_removed_fields_and_header_bounds | §§6.1,6.5 | New independent byte golden has no REPLY mode/basis; conservative REPLY=100/POLL=116/DIFF=109 headers and both byte/domain cap boundaries; reject old layout under the canonical grammar |
| T11_diff_missing_capture_and_exclusion_consistency | §6.1 | Reject missing overlapping captured raw R or exclusions outside reconstructed peer raw set, before any body/evidence effect |

| D | K | alpha | beta_c |
|---|---|---|---|
| 16 | 4 | 3 | 12 |
| 32 | 8 | 5 | 12 |
| 64 | 16 | 10 | 12 |
| 128 | 32 | 20 | 12 |
| 500 | 125 | 76 | 12 |

## Primitive and workload preservation

Preserve field/cell/schedule/sketch/peeler oracles and all their exact workloads. Existing hypergeometric and saturation fixtures are historical arithmetic evidence only; no likelihood primitive or match-rate estimator remains in the proposed protocol. Old root/item saturation and finite SPRT DP cases are historical arithmetic evidence only, not current protocol requirements; replace their policy assertions explicitly when the executable contract is corrected. Do not retain old batch confidence or scalar item-score fixtures as active full-node acceptance criteria.

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
| T7_decode_time_reference_and_partial_results | poll_tests.cpp | §6.2: own/Pending changes between send and receipt; frozen per-call Ref, independent residual checks, failed peel retains valid partial fetch opportunities and records arrival decoded-present/decoded-absent/exclusion observations; residual unclaimed items and rescue discoveries abstain |
| T8_constructor_and_body_result_validation | lifecycle_tests.cpp | §1: preserve invalid Config domains, live enum/hash/binding validation and stale-token precedence from three old T8 cases |
| T8_ten_rounds_all_removal_reasons | lifecycle_tests.cpp | §§5–7: 0–5 adds/removes each side before/during/between 10 rounds; every RemovalReason; no double residual update on fetched admission; exact next sufficiently-sized poll after quiescence |
| T8_pending_only_fetch_or_awaiting | lifecycle_tests.cpp | §7: six counterexamples: decode without fetch reservation, fetch-only without prior decode, result-to-admission gap, own removal without support, removal with live awaiting support, and ended support followed by repeated decode; no history/session support |
| T8_hash_bound_awaiting_preserves_pending_item_state | lifecycle_tests.cpp | §§6.4,7:preserve token/hash/generation/reservation and all item-state fields across timer,disconnect and suspension;matching admission preserves the lifetime once, without changing preference or FINAL;tip cancels |
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
| T11_failed_decode_is_not_misbehavior | adversarial_tests.cpp | §6.6: honest undersized replies and adversarial syntactically valid undecodable cells terminate; no penalty for peel failure alone; only permitted arrival item observations count; unclaimed items in an incomplete reply abstain, including when root_vote equals the poller root; no separate root vote or root confidence exists |
| T11_poll_identity_duplicate_old_tip_and_late | adversarial_tests.cpp | §§6,8: wrong peer/poll/context/generation, duplicate and out-of-order responses; no repeated evidence or fetch; late item evidence ignored |
| T12_global_and_message_limit_boundaries | adversarial_tests.cpp | §6.5: each approved bound -1/exact/+1, allocation before parse rejected, 2MiB total including full exclusions; accepted host state never blocked by stale peer models |
| T12_fixed_peer_state_and_reply_release | adversarial_tests.cpp | §6.5: allocated-capacity accounting after each call, fixed peer floor plus bounded current-round failed invariant-residual/index/exclusion buffers; repeated/duplicate failures cannot exceed the round workspace; nothing retained across rounds |
| T12_pending_union_and_failure_saturation | adversarial_tests.cpp | §§6.4,7: retain admitted/connection/Pending/fetch/awaiting/donor/failure-table boundaries and suspension regression; no eviction/refetch loophole |
| T12_fifty_heights_twenty_nodes | adversarial_tests.cpp | §6.5: original 50-height/20-node soak; last10 mean <=1.1*first10; height rollover uses bounded sizing records; retained global bounds and all actual transient capacities checked |
| T7_candidate_nonce_proof_vectors | poll_tests.cpp | §6.1: independently derived domain0/domain1 SipHash vectors, LE key/ID/proof bytes, empty/set XOR, order, collisions and nonce binding |
| T7_match_excluded_raw_extra_and_churn | poll_tests.cpp | §6.1: unequal raw sets with identical candidates yield valid proof; root change in flight accepts stored-proof MATCH; mismatch reports inconsistent_reply |
| T7_approximate_prepeel_likelihood | sizing_tests.cpp | §6.3: maximize independent likelihood over[L,2M+P],smaller tie,above-domain censor at L;{0} zero=>0 else censored;hostile input never authenticated |
| T7_probe_indices_and_round_censoring | sizing_tests.cpp | §6.3: approved sparse mode/basis, lowest-index clipping, zero-R{0}, round-median censor decision, no per-peer probe state |
| T7_empirical_request_argmin | sizing_tests.cpp | §6.3:quantile-mean CDF/cost ties; include M=262112 with cap=5 and an exact DIFF sample32768: scaling the positive4096-grid quantiles by8 makes every length at least8, greater than5, so every capped candidate has F=0: cost is +infinity, choose the smallest candidate before unchanged growth/cap rules;median censor independently doubles;zero-decode requires fallback cells and no successful decode/DIFF;only MATCH/silence with no samples keeps n; DIFF samples use the normal estimator and may shrink n |
| T7_diff_only_round_shrinks_request | sizing_tests.cpp | Start from an existing oversized prefix; all timely replies are valid REPLY_DIFF with small exact differences. With an independent synthetic quantile fixture whose normal cost argmin is smaller than the prior prefix, assert n_next equals that argmin and shrinks. DIFF is a decode success; no zero-decode trigger. Retain separate censored-median and zero-decode doubling tests unchanged |
| T7_first_height_and_height_rollover | sizing_tests.cpp | §6.3: scaled individual previous-round1 samples rounded up,empirical argmin,zero previousR fallback,consumed bank overwrite;two1024-record banks independent of currentD |
| T7_frozen_table_generator_and_interpolation | sizing_tests.cpp | §6.3:2000 trials,SplitMix64 ID rejection then next-output sign,cap=floor((2MiB−100)/28),grid endpoint4096;20 stored quantiles,step CDF,next-larger-d and scaled tails;S=rank1000,linear median interpolation;CDF next-larger-grid |
| T7_responder_formula_and_full_exclusions | sizing_tests.cpp | §6.1: own raw sizes, exact prefix m formula and probe alternative, full exclusions, header byte accounting and2MiB at M boundary |
| T11_proof_wire_identity_and_invalid_abstention | adversarial_tests.cpp | §§6.1,8: all truncations, old wire version, unknown/duplicate nonce/poll, wrong proof is reported but never root/item evidence |
| T11_stateless_responder_host_rate_limit_boundary | adversarial_tests.cpp | §6.6: every well-formed poll answered with current data, no retained per-peer flood/reputation state, no core poll_flood; host drops separately observed |
| T12_sizing_and_item_state_capacity | adversarial_tests.cpp | §6.5: current/round1 banks, M+P bounded Snowball item-state records and current-round observations; no confidence-derived epoch marks, transient start-estimator ledger, sparse protocol buffers charged;growable test audit separately owned/reported; no history after ID removal |
| T16_silent_slow_matching_freeze_round_distribution | timing_tests.cpp | §8:controlled victim+32 peers,23fast1ms/6silent/3slow100ms,beta.2,epsilon1e−9,fixture K=8 at D32;retain1000 fixed seeds;run to a horizon long enough to finish and report the freeze-round distribution and any nonfinishing trials;no >=99%-within25-rounds acceptance condition;hard assertions: zero false freezes and zero split freezes;report failures without changing seeds |
| T16_majority_all_answer_and_fallback | timing_tests.cpp | §§6.6,8: first strict-majority time,2*t_maj grace,all answered,4*captured PeerCaps median; earliest wins; zero answers still advance |
| T16_ten_percent_loss_two_and_five_nodes | timing_tests.cpp | §8:10% seeded loss each directed link, eventual candidate agreement in honest fixtures; fallback advances rounds without continuations |
| T16_time_order_ties_late_timer_no_catchup | timing_tests.cpp | §§1,6.6: Time order/peer-id ties, replies before timers, upper RTT median>=1us; malformed/invalid-proof arrivals count timing but not evidence; late timer evaluates once at actual time |
| T16_late_reply_discard_all_effects | timing_tests.cpp | §§6,8: expired-round REPLY/MATCH discarded without decode/fetch/sizing/votes, no retained past-round slots; stale context ignored |
| T16_no_peers_connect_disconnect | timing_tests.cpp | §§1,8:initialD0 idles;connect starts next eligible round;during round disconnect abstains without discarding captured item observations or changing captured sample;fallback progresses even if all disconnect |
| T7_approximate_estimator_calibration | sizing_tests.cpp | §6.3:Delta10/50/150/500,1000 trials each,prefixS;include censored lower bounds;mean[.9,1.1],nearest-rankp90[.7,1.4],report censor counts,no retuning |
| T7_now_vs_round_start_estimate | sizing_tests.cpp | §6.3:undo only currently-present round additions,remove departed IDs,unchangedR/Pending transition not logged;P-list overflow disables start estimate for round and uses now without penalty/abandonment |
| T12_id_churn_releases_item_state | adversarial_tests.cpp | §§5,8: more than M distinct IDs across repeated remove/admit while live R<=M; no historical item-state growth; readmission starts a fresh admitted lifetime |
| T7_failed_reply_rescued_by_other_peer | poll_tests.cpp | Peer A fails alone; peer B's decoded items enter Ref via legitimate live support; A succeeds with the same raw/candidate reconstruction as fresh rescue-time decoding. New rescue discoveries abstain; no R insertion bypass |
| T7_retained_residual_every_ref_transition | poll_tests.cpp | §6.2:harness retains independent wire bytes;core retains one invariant residual,never raw copy;private peel copy discarded;each netRef delta once;negative claims never directly mutate invariant; item observations use explicit arrival outcomes and captured lifetimes; rescue adds no votes |
| T7_cascade_poll_order_and_single_observation | poll_tests.cpp | Smallest dirty poll repeatedly; success releases/failure clean; <=K*(1+RefChanges) attempts and no dirty reply. Same-call or later rescue never adds/upgrades arrival observations or duplicates sizing/fetch |
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
| T7_poll_success_reply_diff_bidirectional_fetch | poll_tests.cpp | Inbound success produces the true missing/wanted raw-set difference and starts ordinary responder FetchBody for its positives from the poller; poller FetchBody requests missing. wanted triggers no body-send action; ordinary token binding, reservation and retries apply |
| T7_poll_state_consistent_prefix_and_probe | poll_tests.cpp | POLL root/raw set_size/cells from same state,exact prefix or clipped probe indices;later changes do not alter sent bytes |
| T7_poll_matching_root_skips_decode | poll_tests.cpp | Structurally valid matching root yields proof,no peel attempt/fetch/sizing sample;poll-cell bytes still counted |
| T11_poll_cell_structural_faults_reported | adversarial_tests.cpp | Raw symbol0/size mismatch,impossible counts,index/length/grammar/overflow reported before peel,including matching-root path |
| T11_poll_peel_contradiction_still_replies | adversarial_tests.cpp | §6.6:contradictory inbound attempt discards ALL its effects silently before fallback;ordinary incomplete positives may fetch;structural faults still reported |
| T12_poll_decode_transient_P_bound | adversarial_tests.cpp | One transient working buffer and<=2M inbound claims against ownR only;no POLL retention/rescue;fetch union<=P;both116-byte POLL and100-byte REPLY/full-exclusion limits fit2MiB |
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
| T12_one_round_capture_shared_by_all_slots | adversarial_tests.cpp | One shared capture of at most M+P admitted/Pending lifetime records, no body handles or K copies, released at round end/tip; exact post-capture abstention and transfer eligibility |
| T7_deferred_poll_never_creates_second_capture | poll_tests.cpp | Later send shares capture only ifR unchanged;otherwise defer to next round,no new capture or mixed-state cells/root |
| T7_diff_now_start_exact_list_counts | sizing_tests.cpp | missing already inPending/R,wanted removed since send,post-capture admissions;exact specified now/start formulas at reply entry before fetch effects |
| T7_probe_span_then_monotone_prefix | sizing_tests.cpp | Unusable/censored probe=>max index sent+1 capped,otherwise estimator;once prefix exists never probe again,including all-MATCH/silent rounds |
| T7_pending_absent_from_root_proof_size_cells | poll_tests.cpp | Pending affects decodeRef only;never candidate root,expected proof,raw set_size,own encoded cells or exclusions until validated admission |
| T7_fallback_double_prefix | §6.1 | Failed prefixPOLL produces prefix length min(cap,max(2n,S(size difference)));test floor-dominant,doubling-dominant,cap and overflow inputs |
| T7_probe_fallback_dense_prefix | §6.1 | Failed sparse probe yields dense prefix sized from twice largest actually sent index+1,with floor and cap;never echoes sparse reply cells |
| T7_fallback_no_partial_wire_payload | §6.1 | Fallback contains own raw cells and exclusions only;no partial IDs,residuals or bitmaps |
| T7_diff_missing_wanted_true_difference | §6.1 | missing is responder-only,wanted is poller-only;strict order,disjointness,exact capture-based count relation, missing/capture disjointness, exclusion-subset consistency and raw-set truth |
| T11_diff_wanted_capture_validation | §6.1 | wanted must belong to sent raw capture;currentR/Pending cannot substitute;reject before any body-send/fetch/evidence effect |
| T8_missing_first_donor_dedup | §§1,6.1,7 | First eligible donor starts one live operation; concurrent duplicates do not refetch; not_found/disconnect retries a usable alternate. Retain all T10 honest-donor recovery obligations |
| T8_wanted_responder_ordinary_fetch | §§1,6.1 | Responder positive decode starts ordinary FetchBody from poller; wanted itself triggers no request, body-send action or special receive token at the poller |
| T8_wanted_source_removal_and_loss | §§1,6.1 | Ordinary responder fetch handles source removal, loss, not_found, invalid body, stale/duplicate callbacks and alternate-donor retry with existing token lifecycle |
| T7_fallback_no_back_propagation | §6.1 | Decoding fallback never emits body-send of poller-only IDs;responder's later own poll may discover them |
| T12_bidirectional_fetch_reservation_bounds | §§6.5,7 | Both directions use the existing P union reservation; wanted creates no extra awaiting table, sender action, or second request |

## Files and freeze/removal plan

Independent field/schedule/model oracles remain unchanged; operation-log truth is test-owned, not protocol history. Add independent sizing/proof oracles and hand-derived self-tests. Freeze generator, seed, table digest and generator self-tests. Proposed paths: test/oracle/{sizing.h,sizing.cpp,proof.h,proof.cpp}; test/generator/{sizing_table.py,README.md}; test/data/sizing_table.csv. Seed0x534E4F5753544F52; no table generation in this step. Full-audit observation storage is test-owned and growable, not a production reservation. Extend frozen inventory and extra-file detection to these new contract directories. Reference peeler for generation is independently written, not an import of production code. Table domain is fixed through4096 with approved linear extension; generation cap=floor((2MiB−100)/28).

Keep primitive math tests unchanged. Replace supplemental verify/voting_early_tests.cpp full-K/early-freeze and root-SPRT policy tests with approved round-end/full-sampled-K quorum tests in the correction and freeze them; do not retain the superseded policy as a current acceptance requirement. Keep underlying arithmetic regressions including finite DP labelled as primitive-only evidence. The production preview helper is obsolete policy and must be adapted only after external review.

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

Mutations: T1 wrong field reduction; T2 bypass reference-sign check; T3 wrong schedule boundary; T5 omit scheduled subtraction; T7 use send-time Ref instead of decode-time Ref; T10 preserve unsupported Pending after failure; T13 reduce alpha to a quorum of answerers instead of full K, and separately permit a rescue-only discovery to vote that round; T16 omit fallback or substitute first-answer timer for strict-majority rule. Each mutation compiles, fails its named frozen test, restores exact source bytes, passes, and ends with both repos clean. Never edit tests to accommodate the mutant.

## Stages and stop boundary

Stage A covers nonvoting arithmetic, current-store membership, codec/POLL/DIFF/fallback, sizing, body binding, retained-residual rescue, hostile input, bounds and deterministic host behavior. It uses test-owned candidate snapshots, not a substitute voting implementation. Q4/Q6 are resolved: ordinary FetchBody is used in both directions, REPLY has no mode/basis fields, and both cell-byte and schedule-index limits apply.

Stage B covers item-round state, full-K quorum successes, MATCH equivalence, the round-count gate, FINAL, root settlement/freeze, full-node agreement, candidate/body churn and all complete-node T1–T16 workloads. It must not stub voting, retain a batch accumulator, or pass by weakening obsolete tests. The exact open-case expectations below must be resolved before freezing those cases. Argon’s simulator evidence remains distinct from executed acceptance tests; the earlier requirement for Shammah to confirm Argon’s results is retained.

No freeze, production implementation, host-relay change, table generation or simulator execution is performed by this regeneration. Git commits for the review round are explicitly authorized. Regenerate, list open issues, commit the review round, then STOP for the spec owner’s next decisions.

## Remaining contract questions

Q1–Q13 are CLOSED by the maintained input bundle. The latest instruction closes Q13 with alpha=floor(((1+beta_adv)/2)*K)+1 and replaces the earlier partial-voting definitions with explicit decoded-present/decoded-absent/exclusion observations. The preceding reply-vote instruction excludes rescue-only discoveries from this round’s item votes. F1 and F5 are CLOSED by the final operator resolutions in the maintained input bundle. The gate and its mean use c only for previous success IN, otherwise zero. Fixtures report freeze-round distributions at a horizon long enough to finish; zero false freezes and zero split freezes remain hard assertions. Iteration5 found no new concrete internal defect in either independent revision, and no unresolved contract finding remains from this document review. Implementation, acceptance execution and empirical security/performance validation remain future work.

Provisional K remains the named pre-release (f,K) experiment outcome. Simulator measurements, implementation conformance, frozen-artifact migration and network validation are future evidence obligations, not completed results. This regeneration edits the proposal/test plan in place and does not modify production or frozen source files. Review records are in `.scratch/impcd/iteration-5/`; author amendments remain recorded under iteration-4/author-resolutions.json.
