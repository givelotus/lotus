# Snowstorm executable-contract test proposal — review round 6

Regenerated in place from the maintained input bundle, SHA256 `fb140f92e8287616f0979c4c1744863d88b0b9e2e9fa85afb3b3860c2515ce5c`. The final per-item reply-vote and partial-peel instructions control over all earlier vote wording. No frozen test/header/harness/oracle/manifest or production implementation is changed. Argon owns simulations with fetchable uniques and printed 1 ms validation.

## Current replacement contract

- Success uses voteCount valid item votes: y>=ceil(4*voteCount/5); Require voteCount>=floor(K/2)+1; below-floor/no-vote rounds contribute0 and count no success. Silent/late/invalid/undecoded abstain. Existing arrival observations, exclusions, MATCH and rescue abstention remain.
- Signed evidence S starts0; success contributes +/-e, e=-ln P[HG(D,ceil(D/2),voteCount)>=y]. No-success adds0 and resets nothing. Require at least3 IN/OUT successes respectively in addition to S reaching +/-(-ln epsilon). FINAL is immutable and is its reached side, not prior preference. H0/opposing infinities and FINAL/preference integration remain OPEN.
- Preserve cumulative-count preference updates, whole-state Pending admission and one simultaneous gate snapshot; compare signed IN-direction S to mean S over prechange W. A separate positive-only sum is not invented.
- A node never sends YES for its own Pending: its advertised candidate set excludes it. Received YES votes from admitted holders can score the poller's captured Pending. A live FINAL-in Pending item blocks freezing and keeps ordinary deduplicated donor retries active.
- FINAL-out is removed from advertised sketch view A and W, is never in exclusions and needs no further votes. Physical body/state ownership stays bounded in R. Use advertised A for all cells/setSize/captured raw-set formulas; Ref=(A union Pending) minus FINAL-out.
- At small D poll all D. The K<D crossover is OPEN for the(f,K) grid, no numeric crossover chosen; fixtures print their explicit K.
- Request-to-reply measurements include complete transfer. Normal deadline=4*captured sampled upper median of last measured peer times, imputing unmeasured peers by the measured sampled upper median, otherwise existing fallback. Below-majority-answer rounds double next duration; a majority-answer round restores formula. Majority/all-answered early endings remain.
- Probe fallback prefix length=min(cap,RequiredSymbols(estimatedProbeDifference)), using transient probe difference estimate and censor lower bound, not2*largest-index span. Prefix-request fallback doubling remains unchanged. Ordinary bidirectional FetchBody, raw advertised-A DIFF reconstruction and exact-DIFF resizing remain.
- Fixtures retain1000fixed seeds and report freeze-round distributions at a horizon long enough to finish, with nonfinishing trials visible. Hard assertions: zero false freezes and zero split freezes. No >=99%-within25 target.

## Current weighted-round correction cases

These are requirements for the future executable-contract correction, not executed node acceptance. Current mathematical OPEN cases must be resolved before freezing their expected outcomes.

| Test | Coverage | Required assertion |
|---|---|---|
| T13HypergeometricTailWeightVectors | §8 | Independently compute exact rational tails, natural-log e and implied same-side rounds for D16,32,64,128,500, all K answering and half K answering; print fixture K and actual y. Include unanimous and minimum80%-success counts; K=D benchmark rows do not select the production crossover |
| T13AtLeastThreeSuccesses | §8 | One or two huge-weight successes cannot finalize even if the threshold is exceeded; third same-side success can, subject to signed sum. Include H0 as an explicit unresolved-domain witness until its arithmetic is decided |
| T13NoSuccessPreservesEvidence | §8 | Silence/no-success contributes0 and preserves S and counters; no c, streak or reset remains; below-floor/no-vote rounds count no success |
| T13OUTSubtractsEvidence | §8 | A finite OUT success subtracts exactly e; alternating finite successes do not reset accumulated evidence |
| T13FinalSideIndependentOfPreference | §8 | Threshold side decides FINAL even if cumulative-count preference disagrees; do not silently retain the prior preferred-side finality condition. Integration with gate preference remains OPEN |
| T13PreferenceOvertakeAndTie | §8 | Increment d[successSide] once; strict overtake changes preference, tie retains it before FINAL; no count is replaced by weight |
| T13FinalLifetimeImmutable | §8 | FINAL side and terminal state accept no more updates; loss of lifetime or tip reset starts fresh |
| T13GateSimultaneousPrechangeMean | §8 | Compare IN-direction evidence sums with one pre-entry/pre-exit W mean, empty mean0, simultaneous entries/exits and exact snapshot timing; no prior-success/c mask remains |
| T13PendingAdmissionPreservesWholeState | §§6–8 | Transfer S, both success counts, preference and FINAL intact; no admission-forced IN or reset; captured lifetime eligibility preserved |
| T13PendingNotLocallyYesButRemotelyScored | §§6–8 | Own Pending never in W/proof/own advertised cells or YES; a peer that admitted x can send YES for the poller's Pending lifetime and permit FINAL-in before body arrival |
| T13FinalInPendingBlocksFreeze | §§6–8 | Even with every W item FINAL-in, a live FINAL-in Pending x blocks Frozen; ordinary alternate yes-voting donors/retries remain deduplicated; admission preserves evidence and applies the gate |
| T13FinalOutNotSketchedOrExcluded | §§5–8 | FINAL-out ID disappears exactly once from A, cached cells and eligible Ref, is never an exclusion and receives no more votes; body/state capacity still counts it in R until removal/tip reset. A retained FINAL-out outsider cannot enter W even with p=in and S>=a negative prechange W mean: use outsider S=-13*ln(5),p=in,FINAL-out and sole candidate mean2*ln(286)-2*ln(35357670),p=in,not FINAL with two successes per side; entry must use advertised A |
| T13CapturePendingAndPostcaptureAbstention | §§6,8 | Shared capture<=M+P, no post-capture item vote, incarnation/lifetime filters and whole-state Pending transfer |
| T13MatchEqualsFullCandidateObservations | §§6.1,8 | MATCH/full reconstruction produce identical eligible item observations; no body-possession assertion |
| T13DiffLocalExcludedPeerIncludedYes | §§6.1,8 | Locally excluded nonfinal x remains in captured advertised A; peer includes x; valid DIFF votes yes |
| T13PartialExplicitPreferenceObservations | §§6.2,8 | Arrival-decoded present/nonexcluded YES, decoded absent/excluded NO, other captured items abstain with residual; rescue-only discoveries never upgrade votes |
| T13FinalRequiresThreeNotOne | §8 | No nonempty initially nonfinal W freezes in one/two successes even when e>T; genuinely empty state and other established freeze branches remain |
| T16OneFastYesFifteenSlowNo | §§6.6,8 | D16,K16,one YES reply1ms,fifteen NO replies250ms: below-item-floor rounds add0; below-peer-answer-floor rounds double duration until NO replies count; no FINAL-in, eventual FINAL-out. Check voteCount<=answeredPeers and no new weighted success below the sample majority |
| T13UniqueFinalSideAgreement | §§8,9 | Required honest quiescent fixtures and adversarial schedules retain hard zero false/split assertions; record counterexamples rather than weaken oracle. Include the fixed D16,K16 population with eight YES/eight NO, nine timely answers biased8:1, remaining seven delayed250ms, and mirrored timing at a second poller; check exact tail1/1430, three-success threshold and opposite-final/root outcomes with explicit initial candidate/body states. Preserve zero false/split assertions and report a counterexample as a failure, not an accepted split |
| T16TransferMeasuredDeadlineAndImputation | §6.6 | Use most recent complete POLL-to-reply duration including transfer, no averaging; sampled upper-median imputation, all-unmeasured existing fallback, captured inputs, unchanged2*tmaj/all-answered early ending |
| T16AnswerFloorDoublesDeadlineMajorityResets | §6.6 | Repeated rounds below floor(K/2)+1 answering peers double next duration with checked arithmetic; a round meeting this floor returns to the4*captured-median formula |
| T7ProbeFallbackDifferenceEstimate | §6.1 | Probe fallback uses transient difference estimate through S/cap, not2*(largest index+1); censor supplies lower bound, no inbound sizing-bank sample or retained poll |
| T7DiffOnlyRoundShrinksRequest | §6.3 | Exact DIFF samples still choose normal estimator argmin and may shrink; original conditional prefix growth unchanged |

## Evidence-weight arithmetic vectors

K=D rows exercise the full-population branch; quarter-D rows are declared comparison fixtures, not a crossover choice. Half-answer rows never meet the new sample-majority floor, so their applied contribution is0 and they cannot finalize; raw e is diagnostic. Same-side implied rounds include the minimum3guard and do not resolve opposite-infinity arithmetic. Exact rational tails and80digit weights are recorded in [weighted-evidence.json](../impcd/iteration-6/weighted-evidence.json).

| D | Fixture K | Answered | YES | Case | Raw e | Counted? | One-side rounds |
|---|---|---|---|---|---|---|---|
| 16 | 16 | 16 | 13 | minimum80percent | infinity | yes | 3 |
| 16 | 16 | 16 | 16 | unanimous | infinity | yes | 3 |
| 16 | 16 | 8 | 7 | minimum80percent | 5.288267031 | no | never |
| 16 | 16 | 8 | 8 | unanimous | 9.462654301 | no | never |
| 16 | 4 | 4 | 4 | minimum80percent | 3.258096538 | yes | 7 |
| 16 | 4 | 4 | 4 | unanimous | 3.258096538 | yes | 7 |
| 16 | 4 | 2 | 2 | minimum80percent | 1.455287233 | no | never |
| 16 | 4 | 2 | 2 | unanimous | 1.455287233 | no | never |
| 32 | 32 | 32 | 26 | minimum80percent | infinity | yes | 3 |
| 32 | 32 | 32 | 32 | unanimous | infinity | yes | 3 |
| 32 | 32 | 16 | 13 | minimum80percent | 7.512687127 | no | never |
| 32 | 32 | 16 | 16 | unanimous | 20.214239244 | no | never |
| 32 | 8 | 8 | 7 | minimum80percent | 3.983216506 | yes | 6 |
| 32 | 8 | 8 | 8 | unanimous | 6.705972855 | yes | 4 |
| 32 | 8 | 4 | 4 | minimum80percent | 2.983570709 | no | never |
| 32 | 8 | 4 | 4 | unanimous | 2.983570709 | no | never |
| 64 | 64 | 64 | 52 | minimum80percent | infinity | yes | 3 |
| 64 | 64 | 64 | 64 | unanimous | infinity | yes | 3 |
| 64 | 64 | 32 | 26 | minimum80percent | 14.568537235 | no | never |
| 64 | 64 | 32 | 32 | unanimous | 42.052280570 | no | never |
| 64 | 16 | 16 | 13 | minimum80percent | 5.510568363 | yes | 4 |
| 64 | 16 | 16 | 16 | unanimous | 13.608176484 | yes | 3 |
| 64 | 16 | 8 | 7 | minimum80percent | 3.622693441 | no | never |
| 64 | 16 | 8 | 8 | unanimous | 6.042172285 | no | never |
| 128 | 128 | 128 | 103 | minimum80percent | infinity | yes | 3 |
| 128 | 128 | 128 | 128 | unanimous | infinity | yes | 3 |
| 128 | 128 | 64 | 52 | minimum80percent | 28.376699160 | no | never |
| 128 | 128 | 64 | 64 | unanimous | 86.069079522 | no | never |
| 128 | 32 | 32 | 26 | minimum80percent | 10.248524774 | yes | 3 |
| 128 | 32 | 32 | 32 | unanimous | 27.415831398 | yes | 3 |
| 128 | 32 | 16 | 13 | minimum80percent | 4.960151173 | no | never |
| 128 | 32 | 16 | 16 | unanimous | 12.160397053 | no | never |
| 500 | 500 | 500 | 400 | minimum80percent | infinity | yes | 3 |
| 500 | 500 | 500 | 500 | unanimous | infinity | yes | 3 |
| 500 | 500 | 250 | 200 | minimum80percent | 98.505374180 | no | never |
| 500 | 500 | 250 | 250 | unanimous | 343.239994878 | no | never |
| 500 | 125 | 125 | 100 | minimum80percent | 33.722936012 | yes | 3 |
| 500 | 125 | 125 | 125 | unanimous | 107.678322392 | yes | 3 |
| 500 | 125 | 62 | 50 | minimum80percent | 15.941323521 | no | never |
| 500 | 125 | 62 | 62 | unanimous | 47.301797466 | no | never |

## Primitive and workload preservation

Preserve field/cell/schedule/sketch/peeler oracles and all their exact workloads. Existing hypergeometric and saturation fixtures are historical arithmetic evidence only; the new hypergeometric upper-tail primitive replaces old LLR/root policy; no adaptive match-rate estimator remains. Old root/item saturation and finite SPRT DP cases are historical arithmetic evidence only, not current protocol requirements; replace their policy assertions explicitly when the executable contract is corrected. Do not retain old batch confidence or scalar item-score fixtures as active full-node acceptance criteria.

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

The following nonvoting cases retain their workloads. Current replacement rules above control where older wording was superseded. Old root accumulators are not restored; the new signed weighted item evidence is required by the controlling amendment.

| Test | File / spec | Requirement |
|---|---|---|
| T9FetchableUniqueAgreement | §§8,9 | Per-node unique bodies remain fetchable;after convergence each unique is in all honest W or no honest W;report split/nonfreeze outcomes |
| T12ConfidenceBoundNoEvictionHistory | §§6.5,7,8 | All R plus livePending scores<=M+P;no sticky confidence epoch-mark table |
| T7CellsRawExclusionsCandidate | §§6,8 | Cells/DIFF encode advertised A;nonmatching replies excludeA−W;FINAL-out is in neither;POLL no exclusions |
| T16FetchValidation1ms | §9 | Unique bodies served from owners;body completion includes donorRTT,serialization and printed1ms validation |
| T6CurrentSetInterleavedChanges | current_store_tests.cpp | §5: 10000 seeded add/remove sequences, compare all current IDs/bodies and random cached prefixes to independent log replay after every operation; no pins/log retention |
| T6CurrentCollisionAndAdmissionSequences | current_store_tests.cpp | §§3,5: retained SipHash hand vector, multiple bodies per ID, duplicate no-op, partial/last-body removal, readmission seq and cache equality |
| T6CurrentResetRekeysAndReleasesCapacity | current_store_tests.cpp | §5: tip and block-disconnect reset, surviving handles, cache extension to exact limit, no historical retention; overflow atomicity |
| T7StaticOneshot7000FreshTrials | poll_tests.cpp | §6: differences 0,1,2,3,10,100,1000, 1000 fresh seeds each, both sides; compare each successful decode to reply-time responder truth; no continuation; final candidate/body agreement |
| T7SmallDifferenceOneExchange | poll_tests.cpp | §6: honest distinct differences <=2 complete decoding with one POLL/REPLY_DIFF when inbound symbol0 decodes; equal roots use REPLY_MATCH, which does not prove raw equality |
| T7ReplyIsCurrentAndInternallyConsistent | poll_tests.cpp | §§5,6.1: interleave admissions/removals before delivery; cells/root/size/full exclusions all match a single reply-construction state; repeated polls may see changed state |
| T7MatchWithExcludedRawExtra | poll_tests.cpp | §§6,8: identical candidate root with unequal raw sets returns MATCH; assert candidate equality only |
| T7MatchAssertionDoesNotAuthenticateBody | poll_tests.cpp | §§1,6,8: malicious echo never inserts body or authenticates raw membership |
| T7DecodeTimeReferenceAndPartialResults | poll_tests.cpp | §6.2: own/Pending changes between send and receipt; frozen per-call Ref, independent residual checks, failed peel retains valid partial fetch opportunities and records arrival decoded-present/decoded-absent/exclusion observations; residual unclaimed items and rescue discoveries abstain |
| T8ConstructorAndBodyResultValidation | lifecycle_tests.cpp | §1: preserve invalid Configuration domains, live enum/hash/binding validation and stale-token precedence from three old T8 cases |
| T8TenRoundsAllRemovalReasons | lifecycle_tests.cpp | §§5–7: 0–5 adds/removes each side before/during/between 10 rounds; every RemovalReason; no double residual update on fetched admission; exact next sufficiently-sized poll after quiescence |
| T8PendingOnlyFetchOrAwaiting | lifecycle_tests.cpp | §7: six counterexamples: decode without fetch reservation, fetch-only without prior decode, result-to-admission gap, own removal without support, removal with live awaiting support, and ended support followed by repeated decode; no history/session support |
| T8HashBoundAwaitingPreservesPendingItemState | lifecycle_tests.cpp | §§6.4,7:preserve token/hash/generation/reservation and all item-state fields across timer,disconnect and suspension;matching admission preserves the lifetime once, without changing preference or FINAL;tip cancels |
| T8TipResetCancelsOldGeneration | lifecycle_tests.cpp | §§1,5: stale results before payload validation; cancelled awaiting callback cannot resurrect old confidence |
| T8CollisionRemovalRekeyAndReadmission | lifecycle_tests.cpp | §§3,5,7: exact body/ID/root changes, rekey, positive/negative claims in different polls, all removal reasons |
| T8DisconnectAlternateAndLateResult | lifecycle_tests.cpp | §6.4: cancel inflight before payload validation; immediate known alternate; awaiting survives disconnect; reconnect gets fresh identity |
| T9FullMesh520100Nodes | pooling_tests.cpp | §§6–8: original 5/20/100-node workloads and seeds, candidate/body agreement; every successful raw reply exact against host truth; release all retained state at round end/abandonment |
| T9PendingHolderAndAbsentPeer | pooling_tests.cpp | §§6.2,7: three nodes, Pending hides a +decode from honest holder; success still discovers usable donors ; absent peer yields negative evidence without cancelling another live fetch |
| T10FakePartialAndSuccessfulReplies | pooling_tests.cpp | §6.4: real/fake mixed replies, each eligible fake fetched, failure removes unsupported Pending, real IDs reconcile, no fake R/Frozen insertion |
| T10PeerLocalFailureHonestAlternate | pooling_tests.cpp | §6.4: notFound/wrong binding peer-local, policy rejection nonpunitive, matched invalid height-wide, honest donor after false failure; bound/collision cases preserved |
| T10DonorSlotsReleasedAndStaleResults | pooling_tests.cpp | §6.4: eight occupied donor slots, failures free slots, honest ninth; cancelled late result cannot poison successful admission |
| T11OneshotWireGoldensTruncations | adversarial_tests.cpp | §6.1: exact independently written bytes for all four messages; every truncation, noncanonical CompactSize, suffix byte, count and integer overflow |
| T11100000MalformedPerWireType | adversarial_tests.cpp | §§6.1,6.6: 100000 seeded malformed/oversized cases for EACH of four types; bounded allocation, no crash/assertion; concurrent honest polls continue |
| T11SingleReplyInconsistency | adversarial_tests.cpp | §6.6: false size/count, impossible count bound, inconsistent declared cell count, exclusion cardinality/duplicates/zero; report only independently provable faults |
| T11FailedDecodeIsNotMisbehavior | adversarial_tests.cpp | §6.6: honest undersized replies and adversarial syntactically valid undecodable cells terminate; no penalty for peel failure alone; only permitted arrival item observations count; unclaimed items in an incomplete reply abstain, including when rootVote equals the poller root; no separate root vote or root confidence exists |
| T11PollIdentityDuplicateOldTipAndLate | adversarial_tests.cpp | §§6,8: wrong peer/poll/context/generation, duplicate and out-of-order responses; no repeated evidence or fetch; late item evidence ignored |
| T12GlobalAndMessageLimitBoundaries | adversarial_tests.cpp | §6.5: each approved bound -1/exact/+1, allocation before parse rejected, 2MiB total including full exclusions; accepted host state never blocked by stale peer models |
| T12FixedPeerStateAndReplyRelease | adversarial_tests.cpp | §6.5: allocated-capacity accounting after each call, fixed peer floor plus bounded current-round failed invariant-residual/index/exclusion buffers; repeated/duplicate failures cannot exceed the round workspace; nothing retained across rounds |
| T12PendingUnionAndFailureSaturation | adversarial_tests.cpp | §§6.4,7: retain admitted/connection/Pending/fetch/awaiting/donor/failure-table boundaries and suspension regression; no eviction/refetch loophole |
| T12FiftyHeightsTwentyNodes | adversarial_tests.cpp | §6.5: original 50-height/20-node soak; last10 mean <=1.1*first10; height rollover uses bounded sizing records; retained global bounds and all actual transient capacities checked |
| T7CandidateNonceProofVectors | poll_tests.cpp | §6.1: independently derived domain0/domain1 SipHash vectors, LE key/ID/proof bytes, empty/set XOR, order, collisions and nonce binding |
| T7MatchExcludedRawExtraAndChurn | poll_tests.cpp | §6.1: unequal raw sets with identical candidates yield valid proof; root change in flight accepts stored-proof MATCH; mismatch reports inconsistentReply |
| T7ApproximatePrepeelLikelihood | sizing_tests.cpp | §6.3: maximize independent likelihood over[L,2M+P],smaller tie,above-domain censor at L;{0} zero=>0 else censored;hostile input never authenticated |
| T7ProbeIndicesAndRoundCensoring | sizing_tests.cpp | §6.3: approved sparse mode/basis, lowest-index clipping, zero-R{0}, round-median censor decision, no per-peer probe state |
| T7EmpiricalRequestArgmin | sizing_tests.cpp | §6.3:quantile-mean CDF/cost ties; include M=262112 with cap=5 and an exact DIFF sample32768: scaling the positive4096-grid quantiles by8 makes every length at least8, greater than5, so every capped candidate has F=0: cost is +infinity, choose the smallest candidate before unchanged growth/cap rules;median censor independently doubles;zero-decode requires fallback cells and no successful decode/DIFF;only MATCH/silence with no samples keeps n; DIFF samples use the normal estimator and may shrink n |
| T7DiffOnlyRoundShrinksRequest | sizing_tests.cpp | Start from an existing oversized prefix; all timely replies are valid REPLY_DIFF with small exact differences. With an independent synthetic quantile fixture whose normal cost argmin is smaller than the prior prefix, assert nNext equals that argmin and shrinks. DIFF is a decode success; no zero-decode trigger. Retain separate censored-median and zero-decode doubling tests unchanged |
| T7FirstHeightAndHeightRollover | sizing_tests.cpp | §6.3: scaled individual previous-round1 samples rounded up,empirical argmin,zero previousR fallback,consumed bank overwrite;two1024-record banks independent of currentD |
| T7FrozenTableGeneratorAndInterpolation | sizing_tests.cpp | §6.3:2000 trials,SplitMix64 ID rejection then next-output sign,cap=floor((2MiB−100)/28),grid endpoint4096;20 stored quantiles,step CDF,next-larger-d and scaled tails;S=rank1000,linear median interpolation;CDF next-larger-grid |
| T7ResponderFormulaAndFullExclusions | sizing_tests.cpp | §6.1: own raw sizes, exact prefix m formula and probe alternative, full exclusions, header byte accounting and2MiB at M boundary |
| T11ProofWireIdentityAndInvalidAbstention | adversarial_tests.cpp | §§6.1,8: all truncations, old wire version, unknown/duplicate nonce/poll, wrong proof is reported but never root/item evidence |
| T11StatelessResponderHostRateLimitBoundary | adversarial_tests.cpp | §6.6: every well-formed poll answered with current data, no retained per-peer flood/reputation state, no core pollFlood; host drops separately observed |
| T12SizingAndItemStateCapacity | adversarial_tests.cpp | §6.5: current/round1 banks, M+P bounded Snowball item-state records and current-round observations; no confidence-derived epoch marks, transient start-estimator ledger, sparse protocol buffers charged;growable test audit separately owned/reported; no history after ID removal |
| T16SilentSlowMatchingFreezeRoundDistribution | timing_tests.cpp | §8:controlled victim+32 peers,23fast1ms/6silent/3slow100ms,beta.2,epsilon1e−9,fixture K=8 at D32;retain1000 fixed seeds;run to a horizon long enough to finish and report the freeze-round distribution and any nonfinishing trials;no >=99%-within25-rounds acceptance condition;hard assertions: zero false freezes and zero split freezes;report failures without changing seeds |
| T16MajorityAllAnswerAndFallback | timing_tests.cpp | §§6.6,8: first strict-majority time,2*majorityAnswerTime grace,all answered,4*captured measured request-to-complete-reply median with declared imputation/bootstrap; earliest wins; zero answers still advance |
| T16TenPercentLossTwoAndFiveNodes | timing_tests.cpp | §8:10% seeded loss each directed link, eventual candidate agreement in honest fixtures; fallback advances rounds without continuations |
| T16TimeOrderTiesLateTimerNoCatchup | timing_tests.cpp | §§1,6.6: Time order/peer-id ties, replies before timers, upper RTT median>=1us; malformed/invalid-proof arrivals count timing but not evidence; late timer evaluates once at actual time |
| T16LateReplyDiscardAllEffects | timing_tests.cpp | §§6,8: expired-round REPLY/MATCH discarded without decode/fetch/sizing/votes, no retained past-round slots; stale context ignored |
| T16NoPeersConnectDisconnect | timing_tests.cpp | §§1,8:initialD0 idles;connect starts next eligible round;during round disconnect abstains without discarding captured item observations or changing captured sample;fallback progresses even if all disconnect |
| T7ApproximateEstimatorCalibration | sizing_tests.cpp | §6.3:Delta10/50/150/500,1000 trials each,prefixS;include censored lower bounds;mean[.9,1.1],nearest-rankp90[.7,1.4],report censor counts,no retuning |
| T7NowVsRoundStartEstimate | sizing_tests.cpp | §6.3:undo only currently-present round additions,remove departed IDs,unchangedR/Pending transition not logged;P-list overflow disables start estimate for round and uses now without penalty/abandonment |
| T12IdChurnReleasesItemState | adversarial_tests.cpp | §§5,8: more than M distinct IDs across repeated remove/admit while live R<=M; no historical item-state growth; readmission starts a fresh admitted lifetime |
| T7FailedReplyRescuedByOtherPeer | poll_tests.cpp | Peer A fails alone; peer B's decoded items enter Ref via legitimate live support; A succeeds with the same raw/candidate reconstruction as fresh rescue-time decoding. New rescue discoveries abstain; no R insertion bypass |
| T7RetainedResidualEveryRefTransition | poll_tests.cpp | §6.2:harness retains independent wire bytes;core retains one invariant residual,never raw copy;private peel copy discarded;each netRef delta once;negative claims never directly mutate invariant; item observations use explicit arrival outcomes and captured lifetimes; rescue adds no votes |
| T7CascadePollOrderAndSingleObservation | poll_tests.cpp | Smallest dirty poll repeatedly; success releases/failure clean; <=K*(1+RefChanges) attempts and no dirty reply. Same-call or later rescue never adds/upgrades arrival observations or duplicates sizing/fetch |
| T12RetainedReplyWorkspaceAndRelease | adversarial_tests.cpp | §6.5:<=K residual arrays,indices,exclusions<=K*M,one transient work buffer;no second raw copy;growable observation audit excluded from protocol reservations;allocation failure fails test;release all at boundary |
| T15SameSeedRescueTranscript | determinism_tests.cpp | Same seed produces identical Ref deltas,rescue order,actions and evidence within one process and across processes |
| T16RoundEndOrTipCancelsRescues | timing_tests.cpp | No cross-round retention; late replies discarded; root-changing admission preserves eligible item observations; only round end/tip releases retained replies; no root-confidence reset or veto |
| T7RescueOriginalSizingSampleOnly | sizing_tests.cpp | Both sizing estimates captured once before first peel; repeated rescue attempts never add/rewrite samples; sample bank bounds unchanged |
| T7QuantileTableAllLevels | sizing_tests.cpp | §6.3:20 levels(5%..95% and100%),rankceil(q*N),repeated quantile values,maximum/cap;median S is stored50%,rank1000 |
| T7ProbabilityMeanOfDistributions | sizing_tests.cpp | Hand distributions where mean DifferenceCDF(d,n) differs from threshold-counting RequiredSymbols(d)<=n; verify mean, cost argmin and smaller-n tie; responder still uses median floor |
| T7CdfGridTailAndLargeDifference | sizing_tests.cpp | §6.3:largest qualifyingq stepCDF,below5%=0,atmaximum=1;next-larger d between grid points;ceil-scaled each quantile beyond4096 |
| T11PeelFailureNotAttributableToReplyPeer | adversarial_tests.cpp | Poison Ref via another peer's fabricated Pending ID; contradiction/repeated claim/bound failure on first/rescue peel discards without PeerMisbehaved; separately prove structural/proof faults still report |
| T12CascadeAttemptAndAggregateAuditBounds | adversarial_tests.cpp | No ID re-entersPending in one call;attempts<=K*(1+RefChanges),no dirty remainder;complete growable observation audit;first peel counts once,delta event per(item,reply);audit allocation failure is test failure,never protocol ResourceLimit |
| T7MedianRank1000AndDistinctCDFInterpolation | sizing_tests.cpp |2000 sorted trial outcomes with distinct1000/1001: S uses1000; S linear interpolation and F next-larger-grid remain distinct |
| T7StalledRetainedContradictionDiscarded | poll_tests.cpp |Ordinary undecodable/stalled cells stay rescue-eligible;explicit repeated/sign/bound contradiction discards with no peer penalty;structural faults checked before peel only |
| T15FullAuditObservationNoninterference | determinism_tests.cpp |Full/simulation/production modes: identical calls,Actions,transcripts,RNG and host truth;only observation recording differs |
| T12ObservationAllocationFailureIsTestFailure | adversarial_tests.cpp |Inject failure in observation-owned audit allocation: fail test recording,never emit protocol ResourceLimit or report truncated audit as success;separate protocol-byte accounting |
| T7AttemptAndDeltaAuditUnits | poll_tests.cpp |Count initial peel once,each rescue once;one delta record per(item,reply) regardless touched cells;verify attempt bound and no dirty reply at call end |
| T7ZeroDecodePrefixDoublesToCap | sizing_tests.cpp | Scripted structurally valid cell replies never decode;positive prefix n strictly grows each censored/zero-decode round by at least2x until capped;never returns to probe;estimator cannot lower floor,checked arithmetic,no continuation |
| T7SuccessfulRescueSuppressesZeroDecodeFloor | poll_tests.cpp | Every arrival initially stalls but one reply is rescued before round end;do not apply zero-decode floor;another round with no success does apply it |
| T7ZeroDecodeGateNoCellsAndCap | sizing_tests.cpp | §6.3:only MATCH/silence with no samples keeps n; DIFF samples use the normal estimator and may shrink n;successfulDIFF suppresses zero-decode trigger;censored median independently doubles;probe transition=maxSentIndex+1 clipped to cap;no return to probe |
| T7PollSuccessReplyDiffBidirectionalFetch | poll_tests.cpp | Inbound success produces the true missing/wanted raw-set difference and starts ordinary responder FetchBody for its positives from the poller; poller FetchBody requests missing. wanted triggers no body-send action; ordinary token binding, reservation and retries apply |
| T7PollStateConsistentPrefixAndProbe | poll_tests.cpp | POLL root/raw setSize/cells from same state,exact prefix or clipped probe indices;later changes do not alter sent bytes |
| T7PollMatchingRootSkipsDecode | poll_tests.cpp | Structurally valid matching root yields proof,no peel attempt/fetch/sizing sample;poll-cell bytes still counted |
| T11PollCellStructuralFaultsReported | adversarial_tests.cpp | Raw symbol0/size mismatch,impossible counts,index/length/grammar/overflow reported before peel,including matching-root path |
| T11PollPeelContradictionStillReplies | adversarial_tests.cpp | §6.6:contradictory inbound attempt discards ALL its effects silently before fallback;ordinary incomplete positives may fetch;structural faults still reported |
| T12PollDecodeTransientPBound | adversarial_tests.cpp | One transient working buffer and<=2M inbound claims against ownA only;no POLL retention/rescue;fetch union<=P;both116-byte POLL and100-byte REPLY/full-exclusion limits fit2MiB |
| T7PollPendingUpdatesOutboundInvariant | poll_tests.cpp | §6.2:inbound Pending updates all retained invariants exactly once and triggers normal ordered rescue;no inbound retention,no new sizing sample |
| T15PollCellByteAccounting | determinism_tests.cpp | Exact28*m sent/received poll-cell bytes,framing separately counted,identical mode transcripts;MATCH proof16/full application58 bytes |
| T7PollDecodeReferenceExcludesPending | poll_tests.cpp | Responder Pending differs from advertised A; inbound decode uses A only, missing/wanted reflect the two advertised raw sets, excluding retained FINAL-out bodies and speculative Pending |
| T7PollIncompleteFallsBackToCells | poll_tests.cpp | §6.1:ordinary incomplete inbound peel may fetch partial positives then replies with cells;contradiction discards all attempt effects then replies with cells;no inbound retention |
| T11ReplyDiffGoldensAnd100000Malformed | adversarial_tests.cpp | Kind3 independent byte goldens,every truncation,100000 seeded malformed cases,ordering/zero/duplicates/overlap/count overflow/size relation/exclusion bounds;no partial effects |
| T11ReplyDiffWantedSentMembership | adversarial_tests.cpp | §6.1:wanted validated against one round raw capture,including excluded IDs;post-send removal does not falsely penalize;missing ID or signed size mismatch reports inconsistentReply |
| T12ReplyDiffFullPayloadBound | adversarial_tests.cpp | §6.5:complete DIFF over message limit falls back to cellREPLY;no truncation/fragmentation;check both exact boundary and full list bytes before effects |
| T10ReplyDiffFakeIdsRequireBodies | pooling_tests.cpp | Structurally valid missing assertions may be fake;FetchBody/host validation unchanged,no direct R/Frozen insertion,existing failure/probation behavior |
| T15PollMatchWastedCellBytes | determinism_tests.cpp | Matched-exchange poll cells charged separately once;DIFF ID bytes and fallback cell bytes separated;all counts reproduce exact wire sizes |
| T16FetchRTTSerializationValidationMidround | timing_tests.cpp | Host body service=donorRTT+body serialization+configured validation delay;callback at actual completion including mid-round,never batch to round end |
| T10LatencyMetricsBoundedLifetimes | lifecycle_tests.cpp | §10:first-decode timestamp in live fetch/awaiting record survives donor retries;host admission without prior decode has no sample;P-bound and no historical decode table |
| T7CensoredPrefixNeverReturnsToProbe | sizing_tests.cpp | Scripted true difference always above request;each censored/zero-decode prefix strictly grows until success/cap;estimator cannot reduce floor or switch to probe |
| T12OneRoundCaptureSharedByAllSlots | adversarial_tests.cpp | One shared capture of at most M+P admitted/Pending lifetime records, no body handles or K copies, released at round end/tip; exact post-capture abstention and transfer eligibility |
| T7DeferredPollNeverCreatesSecondCapture | poll_tests.cpp | Later send shares capture only ifR unchanged;otherwise defer to next round,no new capture or mixed-state cells/root |
| T7DiffNowStartExactListCounts | sizing_tests.cpp | missing already inPending/R,wanted removed since send,post-capture admissions;exact specified now/start formulas at reply entry before fetch effects |
| T7ProbeSpanThenMonotonePrefix | sizing_tests.cpp | Unusable/censored probe=>max index sent+1 capped,otherwise estimator;once prefix exists never probe again,including all-MATCH/silent rounds |
| T7PendingAbsentFromRootProofSizeCells | poll_tests.cpp | Pending affects decodeRef only;never candidate root,expected proof,raw setSize,own encoded cells or exclusions until validated admission |
| T7FallbackDoublePrefix | §6.1 | Failed prefixPOLL produces prefix length min(cap,max(2n,RequiredSymbols(size difference)));test floor-dominant,doubling-dominant,cap and overflow inputs |
| T7ProbeFallbackDensePrefix | §6.1 | Failed sparse probe yields a dense prefix from RequiredSymbols(estimatedProbeDifference), with censor boundary and cap; never2*probe span, never echoes sparse cells |
| T7FallbackNoPartialWirePayload | §6.1 | Fallback contains own raw cells and exclusions only;no partial IDs,residuals or bitmaps |
| T7DiffMissingWantedTrueDifference | §6.1 | missing is responder-only,wanted is poller-only;strict order,disjointness,exact capture-based count relation, missing/capture disjointness, exclusion-subset consistency and raw-set truth |
| T11DiffWantedCaptureValidation | §6.1 | wanted must belong to sent raw capture;currentR/Pending cannot substitute;reject before any body-send/fetch/evidence effect |
| T8MissingFirstDonorDedup | §§1,6.1,7 | First eligible donor starts one live operation; concurrent duplicates do not refetch; notFound/disconnect retries a usable alternate. Retain all T10 honest-donor recovery obligations |
| T8WantedResponderOrdinaryFetch | §§1,6.1 | Responder positive decode starts ordinary FetchBody from poller; wanted itself triggers no request, body-send action or special receive token at the poller |
| T8WantedSourceRemovalAndLoss | §§1,6.1 | Ordinary responder fetch handles source removal, loss, notFound, invalid body, stale/duplicate callbacks and alternate-donor retry with existing token lifecycle |
| T7FallbackNoBackPropagation | §6.1 | Decoding fallback never emits body-send of poller-only IDs;responder's later own poll may discover them |
| T12BidirectionalFetchReservationBounds | §§6.5,7 | Both directions use the existing P union reservation; wanted creates no extra awaiting table, sender action, or second request |

## Files and freeze/removal plan

Independent field/schedule/model oracles remain unchanged; operation-log truth is test-owned, not protocol history. Add independent sizing/proof oracles and hand-derived self-tests. Freeze generator, seed, table digest and generator self-tests. Proposed paths: test/oracle/{sizing.h,sizing.cpp,proof.h,proof.cpp}; test/generator/{sizing_table.py,README.md}; test/data/sizing_table.csv. Seed0x534E4F5753544F52; no table generation in this step. Full-audit observation storage is test-owned and growable, not a production reservation. Extend frozen inventory and extra-file detection to these new contract directories. Reference peeler for generation is independently written, not an import of production code. Table domain is fixed through4096 with approved linear extension; generation cap=floor((2MiB−100)/28).

Keep primitive math tests unchanged. Replace supplemental verify/voting_early_tests.cpp full-K/early-freeze and root-SPRT policy tests with approved round-end/valid-vote weighted-round tests in the correction and freeze them; do not retain the superseded policy as a current acceptance requirement. Keep underlying arithmetic regressions including finite DP labelled as primitive-only evidence. The production preview helper is obsolete policy and must be adapted only after external review.

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

Mutations: T1 wrong field reduction; T2 bypass reference-sign check; T3 wrong schedule boundary; T5 omit scheduled subtraction; T7 use send-time Ref instead of decode-time Ref; T10 preserve unsupported Pending after failure; T13 replace voteCount by K in the success threshold, and separately permit a rescue-only discovery to vote that round; T16 omit fallback or substitute first-answer timer for strict-majority rule. Each mutation compiles, fails its named frozen test, restores exact source bytes, passes, and ends with both repos clean. Never edit tests to accommodate the mutant.

## Stages and stop boundary

Stage A covers nonvoting arithmetic, current-store membership, codec/POLL/DIFF/fallback, sizing, body binding, retained-residual rescue, hostile input, bounds and deterministic host behavior. It uses test-owned candidate snapshots, not a substitute voting implementation. Q4/Q6 are resolved: ordinary FetchBody is used in both directions, REPLY has no mode/basis fields, and both cell-byte and schedule-index limits apply.

Stage B covers weighted item-round state, 80%-of-valid-votes successes, MATCH equivalence, the evidence-sum gate, FINAL, root settlement/freeze, full-node agreement, candidate/body churn and all complete-node T1–T16 workloads. It must not stub voting, retain a batch accumulator, or pass by weakening obsolete tests. The exact open-case expectations below must be resolved before freezing those cases. Argon’s simulator evidence remains distinct from executed acceptance tests; the earlier requirement for Shammah to confirm Argon’s results is retained.

No freeze, production implementation, host-relay change, table generation or simulator execution is performed by this regeneration. Git commits for the review round are explicitly authorized. Regenerate, list open issues, commit the review round, then STOP for the spec owner’s next decisions.

## Remaining contract questions

OPEN K-CROSSOVER: at small D poll all D; where K drops below D is left to the (f,K) grid, with no number chosen. OPEN EW-INFINITY: H=0 and opposite infinite weights; OPEN EW-PREFERENCE: FINAL versus prior preference; OPEN EW-GATE: signed IN-direction sum interpretation if a separate positive-only sum was intended. OPEN EW-RESPONSE: majority-answer response selection can produce opposite FINAL; hard safety assertions are preserved.
The single-fast-voter attack is guarded by the majority answer floor. D=1 zero-weight nontermination is a documented liveness limitation; no minimum D or special-case weight is invented. Rule10's deadline calculation is author-specified and is not open. These draft markers expose unresolved semantics; no executable freeze or convergence is claimed.

Review records are in `.scratch/impcd/iteration-6/`. Implementation, table generation, simulator and network validation remain future evidence obligations.
