# SNOWSTORM SPEC INPUTS (bundle, revision 3)

All answer and amendment files, in the order they apply. Later sections override earlier ones where they conflict. SPEC-PROPOSED.md is the base. The last two sections (ACCEPTED-REVIEW-1 and SNOWBALL-ROUNDS) supersede the voting parts of SNOWBALL-VOTING and PENDING-CONFIDENCE: no SPRT, no Λ, no C, no M̂1. Voting is plain Snowball per item: quorum α of the K sampled peers, β_c consecutive successes.


==================================================================
## FILE: ASTRA-ANSWERS-P1-P5.md
==================================================================

ANSWERS TO P1–P5 (from Shammah). Apply them, regenerate the proposal and TESTS-PROPOSED.md, list anything still ambiguous, and STOP. Still no freeze or implementation; VOTING_SAMPLE stays TBD until E12.

P1 (estimator boundaries). Confirm the proposed priority: with no nonzero-index cells (probe {0} only), symbol-0 residual zero ⇒ Delta_hat = 0; otherwise censored at L. For Delta_hat_start, L = max(items decoded from this reply, |symbol-0 count difference after add-back|). Search domain is integer Delta in [L, 2·M + P]; if the maximum would lie above it, record a censored result at L (never an unbounded search). Validation statistics include censored samples at their lower bound; p90 by nearest rank over all 1000 ratios; report the censor count separately. On hostile input the estimate is only an approximation; say so, no authentication claim.

P2 (round-start add-back). Use the narrower estimator: reverse only additions to Ref made during the current round that are still present in Ref at processing time. Keep a per-round list of such IDs, bounded by P; R↔Pending transitions that leave Ref membership unchanged are not recorded; removals simply drop the ID from the list. Adding back x means adding x's encoding to the residual (undoing its subtraction). If the list would exceed P, stop computing Delta_hat_start for the rest of that round (use Delta_hat_now for the ratio sample that round); no penalty, no round abandonment. No cross-round log. Charge the P-record list in the storage envelope.

P3 (first-round sizing). Apply the same empirical argmin as other rounds to the previous height's round-1 samples, each scaled by |R|_now ÷ |R|_then (rounded up). The probe decision uses the upper median of the scaled samples; for the median ordering, a censored sample ranks above an uncensored one with equal value. If only MATCH replies followed a probe, the next round probes again. Bound the sample banks by D_max = 1024 each (do not depend on the current D).

P4 (generator cap and fixtures). Approve generation cap = floor((2 MiB − 109) / 28). Grid endpoint 4096 included, deduplicated. Generator PRNG: SplitMix64 from the stated seed; IDs drawn as successive outputs with rejection of zero and duplicates; signs from the next output's low bit. Fixture liveness: drop the DP-derived bound; assert that ≥ 99% of 1000 seeds freeze within T = 25 rounds; failing that is a test failure that is reported, never fixed by changing seeds. Any false freeze in the equivocation fixture fails the test and is reported.

P5 (CDF reconstruction). Store per grid d the 5%…95% quantiles (order statistic ceil(q·N), 1-based) plus the 100% value (maximum over trials, cap-exhausted trials counting as the cap). F_d(n) is a conservative step function: F_d(n) = the largest q whose stored quantile length ≤ n; F_d(n) = 0 below the 5% quantile; F_d(n) = 1 at or above the stored maximum. Between grid points use the next larger grid d (conservative). For d > 4096 scale every stored quantile length by d/4096 and round up, like S. Candidate n domain: the union of the stored quantile lengths (and S) of the current samples, capped at max_symbols_per_reply; this is bounded by 21·D and lets the argmin land on a better n than the medians alone.


==================================================================
## FILE: ASTRA-ANSWERS-P6.md
==================================================================

ANSWERS TO P6, PLUS TWO CORRECTIONS (from Shammah). Apply these together with ASTRA-ANSWERS-P1-P5.md (which answers P1–P5), regenerate the proposal and TESTS-PROPOSED.md, list anything still ambiguous, and STOP. Still no freeze or implementation; VOTING_SAMPLE stays TBD until E12.

P6 (within-round residuals and work)
1. Representation: approved, simplified. Each retained reply keeps its indices, its exclusions and one invariant residual = raw cells − encoding of the current Ref at those indices. The core does not keep a second copy of the raw cells: the invariant is maintained only by Ref deltas, and raw = residual + enc(Ref) can be reconstructed for audit. The harness keeps its own copy of the wire bytes for verification.
2. Each peel attempt (first pass or re-peel) copies the invariant residual into one transient working buffer (at most max_symbols_per_reply cells, part of the existing decode workspace), peels it there and discards it. The invariant changes only through Ref deltas, each applied exactly once. A decoded item affects retained residuals only through the Ref change it causes (entering Pending), never directly.
3. Scheduling: approved. Keep a dirty set ordered by poll order. A Ref change marks every retained reply whose indices it touches. Repeatedly re-peel the smallest dirty reply until none is dirty. Success is handled as success on arrival (W_j against Ref at that moment, this round's evidence, donors, fetches) and the reply is released. Failure leaves it retained and clean.
4. Work bound: no cap and no proportionality claim. A reply is re-peeled only after a Ref change touching its indices. Within one call Ref grows only by new Pending entries, at most P, and an ID cannot re-enter Pending in the same call. So re-peel attempts per call ≤ retained replies × (1 + Ref changes in the call). Record update touches and re-peel steps separately in Stats. Tests assert this attempt bound and that no dirty reply remains at the end of a call.
5. Root-changing admission/removal: approved. Abandonment and release take precedence; there is no rescue or scoring of stale-root replies.
6. Audit bound: aggregate per call = per-reply claim bound (2M + P) × replies processed or re-peeled in the call, plus one record per residual delta. Reserve it or fail with typed ResourceLimit before mutation; never truncate.
7. Retained replies are at most K (the peers selected this round), not D. Retained storage ≤ K × maximum reply size, plus exclusions ≤ K × M.

C1 (misbehaviour reporting). Peel-derived inconsistencies are never reported, on the first pass or on re-peel. This covers inconsistent_symbols, repeated claims, Undecodable, and claims beyond the signed-difference bound. Every peel runs against R ∪ Pending, and Pending holds unverified items decoded from other peers, so a contradiction found while peeling may be caused by another peer's fabricated identifier and is not attributable to this message. Such a reply is discarded for the round with no PeerMisbehaved. inconsistent_reply is reported only for a candidate-proof mismatch against an unchanged root and for the §6.6 structural checks (symbol-0 count ≠ set_size, a count incompatible with set_size, exclusions > set_size, grammar/length/index violations, overflow).

C2 (population changes). Remove "population changes also abandon stale-population evidence and reset C". On a live network peers connect and disconnect constantly, and resetting C on every change would prevent freezing. Each round uses the D, M0, M1hat and sample captured at round start. A selected peer that disconnects abstains. A newly connected peer becomes eligible from the next round. C resets only when own root changes. This matches N2: D changes need no special rule.


==================================================================
## FILE: ASTRA-ANSWERS-R1-R3.md
==================================================================

ANSWERS TO R1–R3 (from Shammah). Apply them, regenerate the proposal and TESTS-PROPOSED.md, list anything still ambiguous, and STOP. Still no freeze or implementation; VOTING_SAMPLE stays TBD until E12.

R1 (median rank). Confirmed: the newest rule supersedes the old one. Every stored quantile, including the 50% one, uses the 1-based order statistic ceil(q·N), so S(d) is the stored 50% quantile (rank 1000 of 2000). S keeps its approved linear interpolation between grid points and its linear extension beyond 4096; F keeps the next-larger-grid rule.

R2 (incomplete peeling vs discard). Confirmed. C1's wording was wrong to include "Undecodable".
- An ordinary stalled or incomplete peel (cells that are simply not yet decodable) is retained for rescue, with no penalty.
- An explicit contradiction (a repeated claim, a sign inconsistency, or claims beyond the signed-difference bound) discards the reply for the round, also with no penalty.
- Structural checks run on the raw reply before any Ref-dependent peel and are the only reportable reply faults besides a proof mismatch. Rescue never creates a new reportable fault.

R3 (audit pre-reservation). Don't reserve a worst-case envelope; K·(1+P) attempts × (2M+P) claims is absurd for a diagnostic. The full per-call audit is an observation facility, not protocol state:
- It is recorded only in full-observation (test) mode. Storage there is growable and owned by the observation layer.
- An allocation failure while recording the audit is a test failure. It is not a protocol path, so there is no ResourceLimit for it and no failure-before-mutation requirement on audit storage.
- Simulation mode and production keep only the Stats counters (update touches, re-peel attempts, rescued replies).
- Both modes still execute identical API calls, actions and transcripts for the same seed; the audit only observes.
- Units: the first peel of a reply counts as one attempt. A residual-delta record is per (Ref item, retained reply) pair, not per touched cell.
- Keep the assertion attempts ≤ retained replies × (1 + Ref changes in the call), and the assertion that no dirty reply remains at the end of a call.
- Protocol-state reservations (slots, retained replies, working buffer, Pending, records) stay as specified.


==================================================================
## FILE: ASTRA-ANSWERS-I1-J4.md
==================================================================

ANSWERS TO I1–I4 AND J1–J4 (from Shammah). Apply them, regenerate the proposal and TESTS-PROPOSED.md, list anything still ambiguous, and STOP. Prefer the simplest rule that is exact; do not add machinery beyond what is stated here.

J1 (captures). All polls of a round are sent at round start from one state, so keep ONE capture per round, not one per slot.
- The capture holds the admitted IDs of R at that moment, each with its admission sequence (incarnation) and a candidate/excluded bit. It holds IDs only, no body handles.
- Bound: at most M records. It is released at round end or tip reset.
- Each slot keeps its 16-byte expected proof and points at the round's capture.
- Admitted-incarnation eligibility uses the captured admission sequence. A removed and readmitted ID is a new incarnation and gets no votes cast for the old one.
- If any poll is sent later than round start, it shares the capture only if R is unchanged; otherwise it is not sent until the next round. Do not add a second capture.

I1 (lack validation). Validate `lack` against the round capture (the poller's sent raw R), exactly. An ID in `lack` that is not in the capture, or the count relation set_size = sent_set_size + |have| − |lack| failing, is inconsistent_reply. This involves only the message and the poller's own captured state (no Pending), so it is attributable.

I2 (oversized REPLY_DIFF). If the complete REPLY_DIFF would exceed the message limit, send the fallback REPLY with cells instead. Never truncate or fragment the lists.

I3 (DIFF evidence and samples).
- W_j starts from the round capture's candidates: ((captured candidates − lack) ∪ have) − exclusions. Items admitted after the capture get no evidence from this reply.
- Sizing: |have| + |lack| is exact relative to the sent set, so record it as an uncensored Δ̂_start sample. For Δ̂_now, record |have − current Ref| + |lack ∩ current R|: the part of the difference still unresolved when the reply is processed. Both are exact counts.
- A valid REPLY_DIFF is a root non-match (Y counts proven MATCH only).

I4 (inbound POLL effects). Confirmed as proposed.
- Pending additions caused by an inbound poll are ordinary Ref changes: they trigger normal rescue of retained outbound replies, and the evidence is attributed only to those outbound replies.
- Partial positives from an incomplete inbound attempt follow the normal fetch rules.
- An explicit contradiction discards all effects of that inbound attempt before the fallback REPLY is built.
- Inbound cells are never retained or rescued.

J2 (growth predicate).
- Doubling on zero decodes applies only if the round received at least one fallback REPLY with cells and none of those decoded (on arrival or by rescue). A REPLY_DIFF counts as a success.
- A round with only MATCH, REPLY_DIFF or silence keeps the previous n.
- A censored upper-median sample still doubles independently.
- First prefix after a probe: if the probe's upper-median sample is censored or unusable, the first prefix is n = (largest probe index sent) + 1, the span the probe already showed to be fully occupied. The doubling rule applies from there. Otherwise use the estimator. Never probe again within the epoch.

J3 (freeze while a fetch is in flight).
- No gate. Keep: freeze iff C ≥ B_root and every remaining candidate is settled.
- A body admitted after a freeze changes the root, which invalidates the freeze (existing rule), and the node continues.
- Remove the test "cannot freeze until the body is admitted, rejected or failed": it was an overclaim in the FETCH-LATENCY amendment.
- Keep the decomposition metrics.
- State in §11 that freezing under a continuous arrival stream is not established by this specification and is measured by R10.

J4 (metrics and counters).
- The first-decode timestamp lives in the fetch/awaiting record (bounded by P) and is kept across donor retries.
- An admission with no prior decode (for example via host relay) has no latency sample.
- A root-changed round does not update M̂1 (keep the previous estimate), and its batch increment is zero.
- root_changed stays set even if the root returns to its initial value.


==================================================================
## FILE: ASTRA-AMENDMENT-PUSH-PULL.md
==================================================================

AMENDMENT: PUSH-PULL GOSSIP (from Shammah). This supersedes my earlier message about deriving K (do not apply that one). Apply this, regenerate the proposal and TESTS-PROPOSED.md, list anything still ambiguous, and STOP.

Framing (put this in the spec rationale): Snowstorm is push-pull gossip.
- Pull: polling a random subset of peers each round. Through decoding, polls spread missing items and also carry the votes.
- Push: announcing new transactions to a random subset of peers.
- In expectation, push to f peers and pull from K peers spread an item at the same rate per round. Running both converges in far fewer rounds than either alone (Karp, Schindelhauer, Shenker, Vöcking, "Randomized Rumor Spreading", FOCS 2000).
- Safety does not depend on K: batch and per-transaction confidence accumulate across rounds until they reach their barriers. K and f trade rounds against bytes.

1. Pull sample (core).
   - K = min(D, ceil(D/4)). Label it PROVISIONAL: "set jointly with the push fanout by the (f, K) grid experiment on the reference simulator before release".
   - The sample stays uniform and fresh each round, as now.
   - Remove params::VOTING_SAMPLE, every "TBD from E12" reference, and any K derivation.
2. Push is NOT part of this spec. It is the host's existing transaction relay (inv announcements), changed in lotusd to announce each transaction to a random subset of f peers instead of all peers. That change is tracked separately. Do not add announcement messages, rules or host requirements here. The core is unaffected: pushed transactions arrive through ordinary host admission (on_tx_admitted). The only mention belongs in §9: the evaluation models host relay at fanout f.
3. Censored or zero-decode rounds double the request; the probe is only used when there is no prior request (core sizing).
   - Simulation found a livelock in the current rule. A prefix round whose replies are mostly censored triggers a probe. The probe's few cells underestimate a large difference, which leads to a prefix request that is again too small and censored, which triggers a probe again. Nodes stayed stuck for 25 rounds this way.
   - Underlying cause: a censored sample enters at its lower bound L, so it understates the difference exactly when the request was too small.
   - New rule: if in a round with a prior prefix request either (a) the upper-median sample is censored or (b) no non-matching reply with cells decoded (on arrival or by rescue), the next request is a prefix of at least twice the previous prefix request, capped at max_symbols_per_reply. The estimator may choose more, never less.
   - The exponential probe is used only when no prior prefix request exists in this epoch and no usable round-1 history exists (first height, empty history, or previous |R| = 0). Remove "probe the next round iff the upper-median sample is censored".
   - Test: a scripted victim whose true difference to every peer exceeds the current request must strictly increase n every round until a decode succeeds or the cap is reached, and must never return to probe mode within the epoch.
4. Evaluation (§9). The simulator's host relays each new transaction's announcement to f uniformly random peers (f = 0 means no announcements). Replace the K sweep with one grid: f ∈ {0, ceil(ln D), ceil(D/8), ceil(D/4)} × K ∈ {ceil(ln D), ceil(D/8), ceil(D/4)}, at D = 128 and D = 500. Measure freeze time p50/p99, rounds, total bytes per node per height (announcements + polls + replies + bodies), and agreement. The provisional values are replaced by the grid's result before release.

After regenerating, VOTING_SAMPLE should no longer exist anywhere. The only open value in the spec should be the provisional K, tied to the named experiment.


==================================================================
## FILE: ASTRA-AMENDMENT-POLL-CELLS.md
==================================================================

AMENDMENT: POLLS CARRY THE POLLER'S CELLS (from Shammah). This restores the two-way exchange of the earlier session design, which was lost in the move to one-shot polls. Apply it together with ASTRA-AMENDMENT-PUSH-PULL.md, regenerate the proposal and TESTS-PROPOSED.md, list anything still ambiguous, and STOP.

Why:
- One exchange reconciles in both directions. The responder learns the poller's items from the poll itself, which saves half a round.
- If the responder decodes the poll's cells, it knows the whole difference and answers with plain IDs instead of cells. In a non-matching exchange the cells therefore move from the reply into the poll; they are not extra.
- Every node sends K polls and receives about K polls per round, so polling alone is push-pull gossip.

1. Wire.
   - POLL gains `m:CompactSize, cells[m]`: the poller's own cells at exactly the requested indices (prefix [0,n), or the probe index set), computed from the same state as the POLL's root and set_size.
   - New reply kind REPLY_DIFF (kind 3): `poll_id, root_vote[32], set_size, exclusion_count, exclusions[], have_count, have[], lack_count, lack[]`.
     - `have` = IDs the responder holds that are absent from the poller's set.
     - `lack` = IDs in the poller's set that the responder does not hold.
     - Both strictly ascending, nonzero, with checked bounds.
   - REPLY (cells) and REPLY_MATCH are unchanged.
   - Update the size bounds for POLL and REPLY_DIFF.
2. Responder (still stateless, one serialized call).
   - If the POLL root equals the responder's candidate root, answer REPLY_MATCH and do not decode the poll's cells.
   - Otherwise:
     - Decode the poll's cells against the responder's own R (not Pending) with the normal peeler: one attempt, no retention, no rescue.
     - If decoding succeeds, answer REPLY_DIFF: have = the negative decoded items (in R, absent from the poller), and lack = the positive decoded items (the poller has them, the responder doesn't).
     - Positive items enter the responder's normal fetch/Pending path with the poller as donor; this is the push.
     - If decoding fails, answer REPLY with cells exactly as now. That is the fallback.
3. Poller.
   - REPLY_DIFF is a successful decode by construction. W_j is (own candidates minus lack) plus have, minus exclusions. It gives per-transaction yes/no evidence exactly like a decoded REPLY, and `have` items enter the fetch/Pending path with the responder as donor.
   - Sizing: a REPLY_DIFF gives the exact difference |have| + |lack| as an uncensored sizing sample. A REPLY means the responder could not decode the poll's n cells, which is evidence that n was too small; the existing estimator and the zero-decode doubling rule apply to it.
   - A REPLY_DIFF whose lists are structurally invalid (ordering, bounds, an ID in both lists, `lack` containing an ID not in the poller's sent set, counts inconsistent with set_size) is reportable as inconsistent_reply. Otherwise the lists are peer assertions, exactly as decoded cells are; neither form is authenticated.
4. No votes from inbound polls.
   - A responder never uses an inbound poll as batch or per-transaction evidence, and never as a sizing sample.
   - Inbound polls are not a uniform sample: the responder did not choose who polls it, and adversaries can poll at will.
   - Inbound polls only disseminate items.
5. Misbehaviour.
   - Structural faults in a poll's cells are reportable (the §6.6 checks).
   - Peel-derived inconsistencies in a poll's cells are silent; the responder falls back to REPLY with cells.
6. Resources.
   - Decoding a poll's cells uses the transient decode workspace; nothing is retained after the call.
   - Charge the decode-claim bound for it.
   - Fetches from inbound polls stay within the existing P union reservation.
7. Tests.
   - A decodable poll yields a REPLY_DIFF whose have/lack equal the true difference; both sides fetch what they lack, the responder from the poller and the poller from the responder.
   - An undecodable poll yields a REPLY with cells.
   - A matching root yields REPLY_MATCH with no decode.
   - Structural faults in cells and in REPLY_DIFF are reported; peel inconsistencies are silent.
   - Inbound polls never change C, Λ or the sizing banks.

Cost to state in the spec rationale and measure: when roots match, the poll's cells go unused (a REPLY_MATCH alone would have sufficed). Report poll-cell bytes on matched exchanges separately in Stats and in the evaluation.


==================================================================
## FILE: ASTRA-AMENDMENT-FETCH-LATENCY.md
==================================================================

AMENDMENT: BODY-FETCH LATENCY AND ROUNDS (from Shammah). Apply together with the PUSH-PULL and POLL-CELLS amendments, regenerate the proposal and TESTS-PROPOSED.md, list anything still ambiguous, and STOP.

Problem. A decoded short ID is not a transaction. The body arrives at least one fetch round trip later, plus validation, and only then does the host admit it into R. Admission changes the candidate set and the root. Today §8 abandons the round without scoring whenever the own root changes. While bodies are still arriving, that discards every round's per-transaction evidence, and the spec never states how fetch latency shapes rounds.

1. Admissions do not abandon a round.
   - Each poll slot stores, at send time, the expected candidate proof (16 bytes, computed from the nonce and the candidate IDs at send time) and a reference to the candidate set captured at send time.
   - A REPLY_MATCH is verified against the stored expected proof, not against the current set. A mismatch is still inconsistent_reply.
   - Remove the rule that discards MATCH proofs when the own root changed after sending.
2. Scoring when the root changed during the round.
   - Per-transaction evidence is still applied at round end. A MATCH is yes for every candidate captured at send time and no for that poll's exclusions. A decoded reply (REPLY_DIFF or a decoded REPLY) gives yes/no through W_j as now.
   - Items admitted after a poll was sent get no evidence from that poll; they start at Λ = 0 as now.
   - Batch confidence: matches count toward C only if they were for the root that is current at round end. If the root changed during the round, reset C and apply no batch increment (this is the existing order-of-evaluation rule, now without abandoning the round).
3. Consequence to state in the rationale. C can only grow in rounds during which the root does not change. A node therefore cannot freeze before its last body has been admitted, and every late admission starts its own per-transaction settlement at Λ = 0. Time to freeze ≈ reconciliation rounds + time to the last admission (fetch round trip + validation) + the rounds needed to reach B_root and +B_tx on a stable root. Rounds keep running while fetches are in flight, because polls still disseminate items and gather per-transaction evidence. No waiting rule and no timeout constant are added.
4. Stats: per admission, the time from first decode to admission. Per round, whether the root changed, and how many fetches were in flight at round start.
5. Evaluation (§9).
   - Body fetch completes after one round trip on the donor link, plus serialization of the body bytes at link bandwidth, plus a host validation delay. State the validation delay in the run configuration.
   - Admission happens when the fetch completes, at any time, including mid-round, never batched at round end.
   - Report freeze time decomposed into: time to last admission, then time from last admission to freeze.
6. Tests.
   - A mid-round admission does not abandon the round, and per-transaction evidence from that round is applied.
   - C is reset when the root changed during the round.
   - A MATCH verified against the stored proof after a mid-round admission is accepted.
   - A node with a fetch in flight cannot freeze until that body is admitted, rejected or failed.


==================================================================
## FILE: ASTRA-AMENDMENT-PENDING-CONFIDENCE.md
==================================================================

AMENDMENT: PENDING ITEMS ACCUMULATE CONFIDENCE (from Shammah). This supersedes the N6 answer's "Pending carries no Λ" and "no transfer from Pending" everywhere (§6.4, §7, §8). Apply it together with ASTRA-ANSWERS-I1-J4.md, regenerate the proposal and TESTS-PROPOSED.md, list anything still ambiguous, and STOP.

Principle: what peers say about how widely x is held is valid whether or not this node has x's body yet. A node accumulates evidence for x while x's body is being fetched. It never includes x in its root, candidate proof, set_size, encoded cells or exclusions until the host has validated and admitted the body. Root and votes stay R-only. Only confidence starts early.

1. Scope. An item has a confidence record Λ_x if it is an admitted candidate (in R, not evicted) or in Pending (a live in-flight or awaiting-admission record). The Pending records stay bounded by P, as now. No other items are scored.
2. Evidence.
   - When a reply j that yields evidence is processed (REPLY_MATCH, decoded REPLY on arrival or by rescue, or REPLY_DIFF), record for every x in (the round capture's candidates ∪ Pending at processing time): yes if x ∈ W_j, otherwise no.
   - At most one observation per selected peer per item per round.
   - For a MATCH, W_j is the captured candidate set, so it is "no" for Pending items: the responder's candidate set equals the poller's, which lacks them.
   - Scoring at round end is unchanged: Λ_x = clamp(Λ_x + L_x, −B_tx, +B_tx).
3. Admission. When a Pending item is admitted, it enters the candidate set carrying its accumulated Λ_x. If Λ_x = +B_tx it enters already settled. Admission still changes the root, as now.
4. Eviction while Pending. If Λ_x reaches −B_tx while x is Pending:
   - cancel its fetch;
   - mark x evicted for the epoch;
   - never refetch it this epoch.
   If the host later admits x anyway (for example by relay), it enters R evicted, not as a candidate. Keep these epoch-evicted marks for non-admitted IDs in a bounded set of size F, following the existing exhaustion and suspension rules. Clear them on tip reset.
5. Lifetime. A Pending item that leaves Pending without admission (not_found, invalid, probation, local_rejected, all donors unavailable) loses its Λ record. If it is later decoded and refetched, it starts at 0. A removed and readmitted admitted ID is a new incarnation and starts at 0, as now.
6. Unchanged:
   - C counts proven matches only, and the root is R-only.
   - Freeze iff C ≥ B_root and every remaining candidate is settled. Pending items are not candidates and do not block freezing (J3).
   - Sizing, misbehaviour rules and inbound-poll rules (inbound polls never give evidence).
7. Tests.
   - A Pending item receiving consistent yes evidence reaches +B_tx before its body arrives and enters settled on admission, with exactly one root change.
   - A fabricated ID receiving no evidence is evicted while Pending, its fetch is cancelled, and it is not refetched in the epoch.
   - A MATCH counts as no for Pending items.
   - Λ records never exceed M + P, and epoch-evicted marks never exceed F.
   - The root, proof, set_size and cells never include a Pending item.


==================================================================
## FILE: ASTRA-AMENDMENT-REPLY-SIMPLIFY.md
==================================================================

AMENDMENT: SIMPLER REPLIES (from Shammah). Apply together with the earlier amendments and answers, regenerate the proposal and TESTS-PROPOSED.md, list anything still ambiguous, and STOP.

1. Fallback length.
   - When the responder cannot decode the POLL's cells, the fallback REPLY carries its own cells at prefix [0, m) with m = min(cap, max(2n, S(|set_size_r − set_size_q|))), where n is the poll's requested prefix length.
   - Reason: the responder failed to decode the residual at [0, n). Its own cells at those same indices give the poller the identical residual (sign-flipped) and add nothing. A longer prefix is the rateless continuation, so the fallback always adds cells the poller did not already have.
   - For a probe poll, the fallback is the prefix [0, max(2·(largest probe index + 1), S(...))), capped.
   - No partial ID lists, leftover residuals or bitmaps are sent in the fallback.
2. Rename REPLY_DIFF's lists from the poller's point of view.
   - `have` → `missing`: IDs the poller lacks; the poller fetches each body once, from the first reply naming it.
   - `lack` → `wanted`: IDs the responder lacks.
   - Validation rules are unchanged.
3. `wanted` is the body request.
   - On receiving a valid REPLY_DIFF, the poller's host sends the bodies of the `wanted` IDs to the responder immediately, with no separate getdata, as a host action.
   - The core still counts `wanted` as the responder's "no" votes, as before.
   - Bodies are never included in any reply.
4. No back-propagation. Items the poller decodes from a fallback REPLY that the responder lacks are not sent back. The responder learns them through its own polls. No new message is added.


==================================================================
## FILE: ASTRA-AMENDMENT-SNOWBALL-VOTING.md
==================================================================

AMENDMENT: VOTING FIXES (from Shammah). This REPLACES the earlier draft of this file (the Snowball-counting version); discard that draft if you received it. Keep the §8 hypergeometric scoring, batch confidence C and their thresholds. Apply this together with all earlier amendments and answers, regenerate the proposal and TESTS-PROPOSED.md, list anything still ambiguous, and STOP.

Principle: a transaction belongs in the epoch only if a majority of the network holds it. The hypergeometric test is relative to the whole peer population D, not to the peers that happened to vote, and that is what enforces the majority. It stays. Three problems found in simulation are fixed:
- sticky eviction made one early round permanent;
- partial decodes gave no votes at all;
- nothing stopped late arrivals from dripping into the set.

1. Eviction is not sticky.
   - An item at Λ_x = −B_tx is out of the candidate set W, but it keeps being scored every round, and its Λ can rise again.
   - Remove the sticky eviction marks and the "never returns this epoch" rule.
   - The ±∞ branches remain and clamp to ±B_tx, as now.
   - Reason: a node's own new transaction scores −∞ in round 1 because nobody else holds it yet, which is correct at that moment. If a majority later holds it, the node must be able to follow the majority instead of being stuck with its round-1 view.
2. Batch-certainty gate (stops the drip).
   - At epoch start, W = the items held then, all at Λ = 0.
   - Afterwards, an item not in W joins W only when Λ_x ≥ the mean Λ over the items currently in W.
   - An item in W leaves W when Λ_x ≤ −B_tx.
   - The gate is relative, not a permanent exclusion. A latecomer stays out of W until its Λ reaches the batch's mean. If it does reach the mean, it may join this epoch: that changes the root, resets C and delays freezing. A latecomer that does not reach the mean before the node freezes stays in R, keeps spreading, and is a candidate next epoch.
   - Pending items are scored too (PENDING-CONFIDENCE). On admission they join W only through this gate.
3. Votes from the peel: yes / no / abstain, per item x of the poller's R ∪ Pending, at most one per selected peer per item per round.
   - REPLY_MATCH: yes if x ∈ captured W, otherwise no.
   - A fully decoded reply (REPLY_DIFF, or a fallback REPLY decoded on arrival or by rescue):
     - yes if the peer holds x and x is not in its exclusions;
     - otherwise no.
   - A reply still partially decoded at round end:
     - no if x is decoded as absent at the peer, or x is in its exclusions;
     - yes if x is proven shared: some received cell at an index ≥ 1 that x's schedule includes is zero after peeling, so x is not in the undecoded remainder, and x is not in the exclusions;
     - abstain otherwise.
   - Silent, late and invalid-proof peers abstain on everything. Inbound polls never vote.
   - Rationale note: abstentions hide some "no" votes (the remainder's poller-side items are all "no"), so partial replies lean toward yes. The simulator measures this lean. Because the score is relative to D, abstentions weaken the evidence rather than inflate it.
4. Scoring is unchanged otherwise: Λ_x += L(Y_x; D, M0, M̂1, K_x), with Y_x = yes votes and K_x = yes + no votes, clamped to ±B_tx. C and M̂1 are unchanged.
5. Freeze: C ≥ B_root AND every item in W is at +B_tx. Items outside W do not block freezing.
6. Cells and exclusions. POLL and REPLY cells and REPLY_DIFF encode R, so items keep spreading. Non-matching replies carry exclusions R − W. POLL carries no exclusions, because inbound polls never vote.
7. Tests.
   - A node's own new transaction never ends split: either every honest node has it in W or none does.
   - An item scored −∞ in round 1 rejoins W if a majority later holds it and it passes the gate.
   - A latecomer is not in W while its Λ is below the mean Λ of W. It joins W at the first round end at which its Λ ≥ that mean. A node that freezes first excludes it from the frozen set.
   - A partial peel yields yes, no and abstain exactly as in item 3.
   - The gate uses the mean Λ over W at round end.


==================================================================
## FILE: ASTRA-ACCEPTED-REVIEW-1.md
==================================================================

ACCEPTED CHANGES FROM SPEC REVIEW ROUND 1 (from Shammah).

1. REPLY_DIFF reconstruction: W_j = ((the round capture's raw R − wanted) ∪ missing) − the peer's exclusions. Start from the captured raw R, not the captured candidates, so that an item the poller has excluded locally but the peer includes is scored yes. Test: poller excludes x, peer includes x, REPLY_DIFF gives yes for x.
2. Only full decodes vote. Remove per-item votes from partial peels. Only fully decoded replies (REPLY_DIFF, or a fallback REPLY decoded on arrival or by rescue) and REPLY_MATCH give per-item votes. A reply still undecoded at round end is a root non-match and abstains on every item. Rationale: in a partial peel, whether a vote is lost depends on the vote itself ("no" items hide in the remainder), and the zero-cell witness can be forged by a single adversary through fake Pending IDs.
3. Sizing after REPLY_DIFF. A round with REPLY_DIFF samples sizes the next request from those exact samples with the normal estimator, which may shrink n. Only a round with no samples (only MATCH, or silence) keeps the previous n. The doubling triggers are unchanged. Test: after a round of only REPLY_DIFF replies with small exact differences, the next request shrinks.
4. Withdrawn: the L_max finite-bound change. Do not apply it. It is superseded by ASTRA-AMENDMENT-SNOWBALL-ROUNDS.md.


==================================================================
## FILE: ASTRA-AMENDMENT-SNOWBALL-ROUNDS.md
==================================================================

AMENDMENT: PER-ITEM CONFIDENCE COUNTS ROUNDS, AS IN SNOWBALL (from Shammah). This closes the OPEN per-transaction scoring item in §8. It replaces per-item Λ accumulation (log-likelihood bits), the L_max idea, AND the batch confidence C over roots (also an SPRT). No sequential probability ratio test remains anywhere. Apply it with the three accepted changes (W_j from the captured raw R; only full decodes vote; REPLY_DIFF samples resize the request), regenerate, list anything still open, STOP.

Why: a single round's sample is one projection of the network graph. A node's peers are a correlated neighbourhood, so one round can look overwhelming when the network as a whole is not there. Only repeated rounds wash that out, so confidence must count rounds, not bits. Accumulating log-likelihood bits lets one round decide an item. At D=128 and K=32, a single round scores up to −45.6 or +17.3 against B_tx = 12, so a new transaction is decided by its first round, while it is still spreading. Snowball counts rounds instead, so no single round decides anything.

1. One Snowball vote per item per round, as a quorum of the K sampled peers.
   - Sample K = min(D, ⌈D/4⌉) peers as now, and set α = ⌈(1+β_adv)/2 · K⌉, a majority of the SAMPLE (not of whoever answered) that holds even if every adversary votes one way.
   - For item x, count yes and no among the full-decode and MATCH votes.
   - The round is a success for IN if yes ≥ α, a success for OUT if no ≥ α, and no success otherwise.
   - Silent, late, invalid-proof and undecoded peers count toward neither side. A round with many abstentions cannot reach α, so a few voters can never carry an item.
2. Snowball state per item (for items in R ∪ Pending, bounded by M + P, cleared on tip reset):
   - preference p_x ∈ {in, out}: in for items held at epoch start or admitted, out for Pending items;
   - counters d_x[in] and d_x[out], starting at 0;
   - a consecutive count c_x, capped at β_c.
   On a success for side s:
   - d_x[s] += 1;
   - if d_x[s] > d_x[p_x], set p_x = s;
   - if s equals the side of the previous success, c_x += 1; otherwise c_x = 1.
   On a round with no success, c_x = 0 (as in Snowball).
   x is FINAL when c_x = β_c with its success side equal to p_x. Preference can flip until then.
3. Consecutive successes: β_c = B_tx = ⌈⌈log2(25/ε)⌉ / 3⌉ (12 at ε = 1e−9), reusing the existing per-item error target; no new constant. This is conservative. The (f, K) grid and the balancing-adversary run measure freeze time; a later revision may derive a smaller β_c with binomial weighting (Mysticeti-style), which is a node-local policy change, not a consensus change.
4. Candidate set W and the gate.
   - W at epoch start = the items held then.
   - An item with p_x = in that is not in W joins W when c_x ≥ the mean c over the items in W (the batch-certainty gate, in rounds).
   - An item leaves W when p_x becomes out.
   - Nothing is sticky before FINAL.
5. The root comes for free.
   - The root is a function of the item states: it is the commitment to W.
   - A REPLY_MATCH is not separate batch evidence. It is the compact form of per-item votes: yes for every item in the captured W and no for every other item of the captured R ∪ Pending, counted as yes/no votes in item 1, exactly like a full decode.
   - Once every item in W is FINAL, the root is settled by construction.
6. Freeze: every item in W is FINAL with p = in. Emit Frozen{root over W, txids}. Items outside W do not block freezing. An item that later passes the gate (which requires c ≥ the mean c over W, i.e. β_c, once all of W is final, so it must itself be FINAL-in) changes the root and invalidates the freeze.
7. Remove:
   - per-item Λ, its clamp, the eviction-at-−B_tx rule and the L_max idea;
   - the batch confidence C, B_root as a freeze condition, M̂1's role in C, and the root_changed / C-reset rules.

   Remove M̂1 entirely (the quorum α does not use it). B_tx remains only as β_c (B_tx = ⌈B_root / 3⌉ with B_root = ⌈log2(25/ε)⌉ as before).
8. Tests.
   - α and β_c are computed exactly as stated for D ∈ {16, 32, 64, 128, 500}.
   - An item with zero yes votes in round 1 is not final after one round.
   - An item reaches FINAL only after β_c consecutive same-side successes; a round with no success resets c_x.
   - Preference flips when the opposite side's count overtakes.
   - The gate admits an item only when its c reaches the mean c of W.
   - A round with no success resets c_x, including a round in which no reply decoded.
   - A node's unique new transaction ends with the same FINAL side at all honest nodes.
   - A REPLY_MATCH contributes exactly the same per-item votes as a full decode showing an identical W.
   - No freeze occurs after a single round, even if every sampled peer matches.
   - There is no C state anywhere.


==================================================================
## ANSWERS TO Q1–Q12
==================================================================

Append this message verbatim to .scratch/inputs/SNOWSTORM-SPEC-INPUTS.md as a new final section titled “ANSWERS TO Q1–Q12”, record the new SHA256, then apply it. From now on you maintain that file: every instruction I give you that changes the spec gets appended there the same way.
Correction to §8 first. You applied an intermediate version of the round-count amendment. The final rule is plain Snowball:
Per item per round: a success for IN if yes ≥ α, a success for OUT if no ≥ α, otherwise no success. Here α = ⌈(1+β_adv)/2 · K⌉ is a quorum of the K sampled peers; silent, late, invalid-proof and undecoded peers count toward neither side.
No success resets c to 0. FINAL after β_c = B_tx = 12 consecutive successes, a constant independent of D.
Remove M̂1, M1tx, the match-rate estimator, L(·) and the derived beta_round table from §8. This closes Q8 and Q9.
Q1: evaluate the gate once per round at round end, after item updates. Use the mean c over W from before any entries or exits, and apply all exits and entries simultaneously against it. Empty W has mean 0.
Q3:
The round capture holds admitted raw IDs (with incarnation and candidate bit) plus the Pending IDs live at round start, at most M + P records. MATCH votes yes for captured W and no for every other captured ID; post-capture items get no votes that round.
On admission, a Pending item keeps its whole Snowball state and does not become p = in by admission; FINAL-out stays out.
A fresh admission with no Pending lifetime starts p = in with zero counters.
Q4: drop “wanted is the body request” and SendBodies. The responder fetches its positive items with ordinary FetchBody from the poller, as the existing fetch path already does. wanted stays only for votes.
Q5: deduplicate concurrent fetches; alternate-donor retry after failure is unchanged, and T10 stands.
Q6: remove mode and basis_size from REPLY. The fallback is always a prefix [0, m); recompute the header and cap bounds.
Q10: FINAL is immutable for the item’s lifetime and accepts no further updates. β_c is constant, and c is capped at β_c.
Q12: freeze iff (W is non-empty and every item in W is FINAL-in) or (R ∪ Pending is empty).
Q2, Q7 and Q11 stay closed. Regenerate, list anything still open, STOP.


==================================================================
## PARTIAL-PEEL VOTING OVERRIDE — GUARDED WITNESS
==================================================================

Override of ACCEPTED-REVIEW-1 item 2: partial peels DO vote. For a reply still partially decoded at round end, per item x of captured R ∪ Pending:
No if x is decoded as absent at the peer, or is in the peer’s exclusions.
Yes if some received cell at an index ≥ 1 that x’s schedule includes is zero after peeling, no current Pending ID is scheduled at that index, and x is not excluded.
Abstain otherwise.
The Pending restriction prevents the fake-Pending-ID forgery of zero cells. The yes-lean from hidden “no” votes is accepted and measured in simulation. Append this to the inputs bundle, apply it, and do not reopen it.


==================================================================
## PARTIAL-PEEL VOTING OVERRIDE — CURRENT RULE
==================================================================

Override of ACCEPTED-REVIEW-1 item 2: partial peels vote. For a reply still partially decoded at round end: yes for items proven shared by the peel, no for items decoded as absent or excluded, abstain for the rest. Append this to the inputs bundle and apply it.


==================================================================
## PER-ITEM REPLY VOTES — ARRIVAL EVIDENCE
==================================================================

Per-item votes from a reply (replaces ACCEPTED-REVIEW-1 item 2 and all earlier vote text). Votes are the peer’s preference; an item it holds but excludes is a no.
REPLY_MATCH: yes for items in captured W; no for captured items outside W.
Decoded at arrival: yes if decoded as present and not excluded; no if decoded as absent, or excluded.
Residual remains: every other item abstains.
No residual: every other captured item is shared, so it votes yes unless excluded.
Decoded later in the round by rescue: abstain that round.
The quorum α counts against the K sampled peers. Append this to the inputs bundle and apply it


==================================================================
## FINAL PARTIAL-PEEL RULE AND STRICT SAMPLE QUORUM
==================================================================

Final rule for partial peels, replacing both partial-peel overrides. A reply still partially decoded at round end votes per captured item: yes if decoded as present at the peer and not in its exclusions; no if decoded as absent at the peer, or in its exclusions; abstain otherwise. Remove the zero-cell witness, the current-Pending guard, the “proven shared” text and the per-reply observation masks (§6.2) and their resource bound.
Q13: α = ⌊((1+β_adv)/2)·K⌋ + 1, a strict majority of the sample, so IN and OUT can never both succeed. Update the α table.
Append this to the inputs bundle, apply it, STOP.


==================================================================
## F5 — FREEZE-ROUND DISTRIBUTION AND SAFETY ASSERTIONS
==================================================================

F5: drop the “≥99% of seeds freeze within 25 rounds” acceptance condition; it predates β_c = 12. Fixtures run to a horizon long enough to finish and report the freeze-round distribution. The hard assertions remain zero false freezes and zero split freezes. Append this to the inputs bundle, apply it, STOP.


==================================================================
## F1 — PREVIOUS-IN GATE VALUE
==================================================================

F1: the gate uses c only when the item’s previous success side is IN; otherwise its gate value is 0. The same applies when computing the mean over W. This replaces “remove the false implication only”. With it, a gate entrant after a freeze is FINAL-in. Append this to the inputs bundle, apply it, and continue the IMPCD iterations.
