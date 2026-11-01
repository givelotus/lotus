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


==================================================================
## F5 — EVIDENCE-WEIGHTED ROUNDS
==================================================================

AMENDMENT: F5 — EVIDENCE-WEIGHTED ROUNDS (from Shammah). Replaces the β_c streak, c, and the reset rule in §8. Closes F1 and F5.

1. Votes. Per item x per round, n_x = the number of sampled peers that cast a valid vote on x. Silent, late, invalid and undecoded peers abstain. A partial peel votes only on the items it decoded (decoded present = yes, decoded absent or excluded = no, rest abstain). A MATCH votes as before.
2. Success. A round is a success for side s if at least ⌈0.8·n_x⌉ of the n_x votes are for s.
3. Weight. A success adds e = −ln H, where H = P(X ≥ y) for X hypergeometric: n_x draws without replacement from D peers, ⌈D/2⌉ of them on side s, and y = the actual number of votes for s. Add +e for an IN success and −e for an OUT success. A round with no success adds 0. Nothing resets.
4. FINAL. x is FINAL-in when the sum reaches +ln(1/ε) and x has at least 3 IN successes. It is FINAL-out when the sum reaches −ln(1/ε) and x has at least 3 OUT successes. FINAL is immutable. FINAL is the side reached, not the prior preference (this fixes F1).
5. Preference, the gate and the freeze predicate stay as they are, with the gate comparing an item's IN-side sum to the mean sum over W. Add: a node does not freeze while it holds a FINAL-in Pending item; it keeps fetching from other yes-voting donors.
6. We never vote yes for a Pending item. Confirm that the spec says so.
7. K: at small D, poll all D peers. The point where K drops below D is left for the (f, K) grid. Flag it as open; do not pick a number.
8. F5: remove the ≥99%-within-25-rounds target. Report the freeze-round distribution; zero false or split freezes is required.
9. Tests: e and the implied rounds for D ∈ {16, 32, 64, 128, 500} with all K answering, and with half answering; no FINAL with fewer than 3 successes even when one round's e exceeds ln(1/ε); silence adds 0 and does not reset; an OUT success subtracts; a FINAL-in Pending item blocks the freeze.

Run IMPCD on this change until it converges (cap 8 iterations). Append this amendment to SNOWSTORM-SPEC-INPUTS.md, report the new SHA, regenerate, list anything still open, STOP.


==================================================================
## EVIDENCE-WEIGHTED ROUNDS — RULES 10–12
==================================================================

10. Round deadline. The deadline uses measured request-to-reply times (including transfer), not propagation RTT. A round with zero answers doubles the deadline for the next round; a round with answers resets it to the measured value.
11. Probe fallback. A fallback reply to a probe is sized from the probe's difference estimate, not from 2 × (largest probe index + 1).
12. FINAL-out items leave the sketched set and are never listed as exclusions again. They need no further votes.


==================================================================
## RULE 10 — EXACT DEADLINE INPUTS AND RESET
==================================================================

Rule 10, exact: the deadline is unchanged in form, 4 × the upper median, over the K sampled peers, of each peer's RTT estimate captured at round start. The only change is the input: a peer's RTT estimate is its most recent measured request-to-reply time (send of POLL to receipt of the complete reply, transfer included), not propagation RTT. No averaging and no new constant. A sampled peer with no measurement yet uses the upper median of the measured peers; if none are measured, the existing fallback applies. Zero-answer doubling stays as written: after a round with zero answers the next deadline is twice the previous one; a round with answers returns to the formula above. Not open.


==================================================================
## EVIDENCE-WEIGHTED ROUNDS — ANSWER FLOOR AND DEADLINE BACKOFF
==================================================================

Answer to the one-fast-voter blocker. Add to the amendment:

13. Answer floor. A round counts for item x only if n_x ≥ ⌊K/2⌋ + 1 (a majority of the sampled peers cast a valid vote on x). A round below the floor adds 0 to x's sum and is not a success.
14. Deadline. A round in which fewer than ⌊K/2⌋ + 1 sampled peers answered at all doubles the deadline for the next round (this generalizes the zero-answer rule). A round meeting the floor returns to the measured formula in rule 10.
15. Test: D = 16, all 16 sampled, one peer replies YES in 1 ms, fifteen reply NO in 250 ms. x must not reach FINAL-in; the deadline must grow until the NO replies are counted; x ends FINAL-out.

Report whether any other attack still reaches FINAL with fewer than a majority of the sample answering.


==================================================================
## CPP STYLE — LOTUS DEVELOPER NOTES
==================================================================

also:

Style: C++ samples in the spec must follow the Lotus naming conventions in ~/repos/lotus/doc/developer-notes.md, not snake_case. Read that file and apply it to every C++ sample and identifier in SPEC-PROPOSED.md and TESTS-PROPOSED.md. If the file is silent on something, match the surrounding Lotus code. Report the convention you applied in one line.


==================================================================
## F5 — FINAL VOTING RULE AND POLICY OVERRIDE
==================================================================

AMENDMENT: F5 — FINAL VOTING RULE (from Shammah). Replaces rules 2–4, 13 and 14 of the evidence-weighted amendment and the later e-over-n correction. Drop the latest-vote-per-peer and sample top-up variants; they are not adopted.

Votes are preferences. A reply votes yes for the responder's W and no for the rest of its R ∪ Pending; a responder never votes yes on an item it has not admitted. A poller's W is shaped by its own tallies, so votes carry neighbourhood information transitively. This is the Snowball metastability argument, and it is why the guarantee does not depend on D relative to network size.

1. Success. A round is a success for side s on item x iff y ≥ ⌈0.8·K⌉, where y = sampled peers voting s on x. Non-answers, late, invalid and undecoded replies count for neither side.
2. Evidence. A success adds e = −ln P(X ≥ y), X hypergeometric: K draws from D peers, ⌈D/2⌉ on side s.
3. Streak. A round with no success, or a success for the other side, resets x's evidence to 0 (only the recent consecutive run counts, as in Snowball).
4. FINAL on side s when the summed evidence reaches ln(1/ε) with at least 3 consecutive successes. FINAL is immutable and is the side reached (F1).
5. Deadline: rule 10 as written (4 × upper median of measured request-to-reply times; doubling after a round in which fewer than ⌈0.8·K⌉ sampled peers answered).
6. Tests: the one-fast-voter and nine-answer counterexamples produce no success; unanimous full rounds reach FINAL at the 3-round floor for D ≥ 64; print rounds-to-FINAL for D ∈ {16, 32, 64, 128, 500}.

Re-run the reviewers against this rule and report any remaining counterexample. STOP.

7. Policy override. A host policy rejection is not consensus invalidity. A node that rejected x on policy votes no on x. If x reaches FINAL-in at that node, the host fetches and admits x subject only to consensus validity, bypassing policy. A consensus-invalid x is never admitted regardless of votes; reaching FINAL-in on one is reported as an anomaly. Deterministic policy alignment is separate future work. Flag as OPEN: a FINAL-in x that conflicts with a held transaction (conflict resolution is out of scope per §1); do not invent a rule.


==================================================================
## F5 — FINAL VOTING, TALLY AND FREEZE
==================================================================

AMENDMENT: F5 — FINAL VOTING, TALLY AND FREEZE (from Shammah). Supersedes the β_c streak, c, the plain-Snowball freeze predicate, and the answer-floor drafts. Resolves F1, F5, the one-fast-voter and nine-answer counterexamples.

VOTES
1. Votes are preferences. A REPLY_MATCH votes yes for the poller's captured W and no for the rest of captured R ∪ Pending. A decoded REPLY_DIFF votes per item as now. A partial peel votes only on decoded items (present = yes; absent or excluded = no); the rest abstain. Silent, late, invalid and undecoded peers abstain. A node never votes yes on an item it has not admitted (Pending is never yes). Because a node's W reflects its own tallies, votes carry neighbourhood information transitively (Snowball metastability); the guarantee does not depend on D relative to network size.

PER-ITEM TALLY (at round end, item x, side s, y = sampled peers voting s; non-answers count for neither side)
2. Preference: if y > K/2, the round counts toward s in x's d counters; p follows the larger counter.
3. Confidence: if y ≥ ⌈0.8·K⌉, the round is a success for s and adds e = −ln P(Bin(K, p0) ≥ y), with p0 = (1 + β_adv)/2. Binomial, not hypergeometric (claim is about the network, T → ∞ limit; no D, no infinite values). A round without a success for s, or a success for the other side, resets x's evidence to 0.
4. x is FINAL on side s when its evidence reaches ln(1/ε) over at least 3 consecutive successes. FINAL is immutable and is the side reached (F1). FINAL-out items leave the sketched set and are never listed as exclusions again.
5. W: at epoch start, the items held. An item with p = in joins W when its evidence ≥ the mean evidence over W (pre-round snapshot, simultaneous). An item leaves W when p becomes out. FINAL-in items never leave. No other exit rule.

ROOT AND FREEZE
6. The root is the commitment to W. A REPLY_MATCH is a vote for the poller's root; no new message or field. A round is a root success iff MATCH count ≥ ⌈0.8·K⌉, adding e by rule 3's formula. A round without a root success, or any change to W, resets root evidence to 0.
7. Freeze iff root evidence ≥ ln(1/ε) over at least 3 consecutive root successes, and no FINAL-in item is still Pending (keep fetching from other yes-voting donors). An empty R ∪ Pending freezes immediately. A later gate entrant changes the root and invalidates the freeze. Per-item FINAL does not gate the freeze.

POLICY
8. A host policy rejection is not consensus invalidity. A node that rejected x on policy votes no. If x reaches FINAL-in there, the host fetches and admits x subject only to consensus validity. A consensus-invalid x is never admitted; FINAL-in on one is reported as an anomaly.

TIMING AND SIZING
9. Deadline: 4 × the upper median, over the K sampled peers, of each peer's most recent measured request-to-reply time (POLL sent to complete reply received, transfer included). Unmeasured peers use the upper median of measured ones; if none, the existing fallback. A round in which fewer than ⌈0.8·K⌉ sampled peers answered doubles the next deadline; otherwise the formula applies.
10. A fallback reply to a probe is sized from the probe's difference estimate, not from 2 × (largest probe index + 1).

OPEN (do not invent rules)
11. A FINAL-in x that conflicts with a held transaction (conflict resolution is out of scope per §1).
12. K at small D: poll all D peers; the point where K drops below D comes from the (f, K) grid.
13. Network-size estimation and binomial weighting are future node-local speed-ups, not in this spec.

F5 TARGET
14. Remove the ≥99%-within-25-rounds target. Report the freeze-round distribution; zero false or split freezes remains required.

TESTS
15. Print evidence per round and rounds-to-FINAL at 80% and 100% agreement for D ∈ {16, 32, 64, 128, 500}. One-fast-voter (D = 16: one 1 ms YES, fifteen 250 ms NO): no success, deadline grows, x ends FINAL-out. Nine-answer (8 prompt YES, 1 prompt NO, 7 slow NO) and its mirror: no success either side. No FINAL with fewer than 3 successes even when one round's e exceeds ln(1/ε). A persistent 60/40 item converges to one side via preference. 80 intermediate items plus 2 FINAL do not drop intermediate items from W. 100 items each missing at a different 10% of peers: every item reaches 90% yes, no root success, no freeze until sets converge. A FINAL-in Pending item blocks the freeze. A policy-rejected item that reaches FINAL-in is admitted.

ALSO
16. C++ samples in the spec follow ~/repos/lotus/doc/developer-notes.md naming, not snake_case. Report the convention applied in one line.
17. PLAN-SPEC.md is stale (SPRT/Λ/M1tx/B_root/C/±∞/CUSUM, RECON_REQ/waves/root_vote). Do not execute it; regenerate it from the final bundle SHA after convergence. No gate replaces my STOP instructions; no branch renames or commits without my approval. Do not declare the rateless-stream simulator superseded; Argon uses it.

Append this to SNOWSTORM-SPEC-INPUTS.md, report the new SHA, regenerate, run IMPCD until it converges (cap 8 iterations), list anything still open, STOP.


==================================================================
## F5 — FINAL VOTING, TALLY AND FREEZE — ADDENDUM 18–19
==================================================================

ADDENDUM to AMENDMENT: F5 — FINAL VOTING, TALLY AND FREEZE (from Shammah). Add as items 18–19 and fold into the same regeneration.

18. Censored sizing samples. A reply of m cells with no empty cell before peeling is censored. Its lower bound is max(the current L, the smallest Δ for which the decode table gives F(Δ, m) < ½), i.e. "more than m cells could decode", not the set-size difference. Argon's run (bundle fb140f92…) shows the old bound driving n to 2–6 cells and then 1,000–2,000.
19. Probe fallback (replaces rule 10). A fallback reply to a probe is sized from the upper end of the probe's bracket: S(the smallest probe index whose cell is empty), or S(the largest index sent) if none is empty. Not the point estimate.

Report the SHA after both are appended.


==================================================================
## ADDENDUM: §8 RATIONALE
==================================================================

ADDENDUM: §8 RATIONALE (from Shammah). Add a short "Rationale" subsection to §8 stating exactly the following, as complete sentences. No new rules.

1. Each sampled vote is a Bernoulli trial with p equal to the network's fraction for that side, treating peers as draws from the network (the T → ∞ limit). A round's count is Binomial(K, p). Rounds draw fresh samples, so they are independent and their tail probabilities multiply; summing e is multiplying them.
2. FINAL and freeze mean: the probability of this consecutive run of rounds, if the network were at or below p0 = (1 + β_adv)/2, is below ε. With at most β_adv of votes adversarial or erroneous, exceeding p0 means a strict majority of honest nodes holds that preference. β_adv is the only safety parameter.
3. Every counted round must show at least 80% agreement, so the network is near or above 80% at FINAL in practice. p0 is the worst case ruled out, not the expected state.
4. Votes are preferences shaped by each node's own tallies, so information spreads beyond a node's D peers (Snowball metastability). Once past the tipping point, the network converges with overwhelming probability. The guarantee does not depend on D relative to network size.
5. Consecutive runs, not cumulative totals: only the recent run reflects the network's current state, and one round is one projection of a correlated neighbourhood. Hence the reset and the 3-round floor.
6. Two thresholds, as in Avalanche's implementation: a simple majority moves preference so contested items resolve to a side; 80% is needed for confidence.
7. Per-item agreement does not imply set agreement (100 items each missing at a different 10% of peers each show 90% yes, yet few peers hold identical sets). The freeze therefore uses a root vote, which costs nothing on the wire because REPLY_MATCH already carries it.
8. Silence and delay count for neither side, so they can delay a decision but never push it either way.
9. Unanimous rounds carry more evidence than marginal ones, so an honest network that already agrees freezes in 3 rounds at D ≥ 64; contested items take longer or never finalize.


==================================================================
## DISPOSITIONS FOR IMPCD ROUND 7
==================================================================

DISPOSITIONS FOR IMPCD ROUND 7 (from Shammah).

A3/B3/A4/B4 — remove the evidence-mean entry gate entirely. W = admitted items with p = IN. Items held at epoch start start with p = IN. A fresh admission with no live Pending state starts with p = OUT (an admission that carries Pending state keeps it, as now). p moves only by the majority preference rule (y > K/2 counts toward that side's d counter). Votes follow W as before. A FINAL-in item is always in W; a FINAL-out item never is. Delete every gate rule, mean capture and gate test. Tests: the 10-node 60/40 case (six initial holders, four late admissions) converges to x IN and the root freezes; the 13/16 case finalizes and enters W; a transaction nobody held at epoch start stays OUT and does not move the root.

A5/B5 — not a protocol defect. State the sampling assumption in §8 and §11: each node's peers are chosen at random across the network (as outbound peer selection is intended to do), so samples are representative of the network. A partitioned or clique-bridged topology violates it and may freeze different roots; Snowstorm is pseudo-consensus, so this delays block reception and never affects consensus validity. Scope the zero-split requirement to topologies meeting the assumption (random graphs in tests). Keep the clique-bridge case as a documented limitation test that reports, not fails.

A1/B1 — delete the strict-majority early-end branch and its tests. Keep the all-answered early end.

A2/B2 — the deadline is 4 × the ⌈0.8·K⌉-th smallest measured request-to-reply time among the K sampled peers (the quorum order statistic), not the upper median. Doubling after a round with fewer than ⌈0.8·K⌉ answers is unchanged. Test: 9 peers at 1 ms and 7 at 250 ms produce consecutive successes and freeze.

Accept the reviewers' smallest fixes for A6, A7/B7 (m_ members, lower_snake_case namespaces per developer-notes), A8/B8 (no commit authorization; STOP), A9, A10, A11/B6 (calibrate at the recorded lowerSizingBound), A12/B9, A13.

Regenerate, continue IMPCD to convergence, report the SHA, STOP.


==================================================================
## EXACT PER-RUN-LENGTH NULL THRESHOLDS
==================================================================

Option 3. ε must bound the decision error, not describe the observed score.

Correction: for each run length r ≥ 3, threshold T_r(K) is computed exactly from the null distribution of a run's summed score under p = p0 (each round independently Binomial(K, p0), restricted to successes y ≥ ⌈0.8·K⌉, score e(y) = −ln P(Bin(K, p0) ≥ y)), such that P(sum of r scores ≥ T_r and all r rounds succeed | p0) ≤ ε·2^−(r−2). A run is FINAL (item) or freezes (root) at the first r where its sum reaches T_r. Σ_r ε·2^−(r−2) = ε. Compute the table once per K at startup; exact, no approximation. Test: the six permutations of (26, 28, 29) at K = 32 no longer fire unless their total null probability is within ε_3; print T_r and rounds-to-FINAL at 80% and 100% for D ∈ {16, 32, 64, 128, 500}.

State the bound honestly: ε applies per run; the per-epoch error is at most ε × the number of runs started.


==================================================================
## DISPOSITIONS, ITERATION 9
==================================================================

Dispositions, iteration 9 (from Shammah).

1. ε: Option 3 as sent (exact per-run-length thresholds T_r(K) from the null score distribution, spent as ε·2^−(r−2); per-epoch error ≤ ε × runs started). If not yet received, apply it now.

2. Independence. Scope the guarantee to the neighbourhood: each round samples K of the node's D fixed peers afresh, so rounds are independent conditional on the neighbourhood, and ε bounds the probability of FINAL or freeze when at most p0 of the node's D peers prefer that side. Binomial(K, p0) is a conservative bound for sampling K of D. The step from neighbourhood to network is not bounded by ε: it rests on the stated random-peer-selection assumption and Snowball metastability (votes are preferences, so information spreads beyond D). Say exactly that in §8 and §11; claim nothing more. This also settles the binomial-scope wording.

3. Conflict handling stays OPEN (out of scope, §1). K crossover stays OPEN (the (f, K) grid). Do not resolve either.

4. Silence claim: state it as "non-answers count for neither side, so silence alone cannot produce a success or move a preference; it can delay decisions." If a reviewer has a counterexample where silence produces a success or moves a preference, report that exact trace; otherwise close it.

Regenerate, continue IMPCD, report the SHA, STOP.


==================================================================
## ANSWER: PROSPECTIVE ATTEMPTS
==================================================================

Count prospective attempts, including failed first rounds


==================================================================
## PROSPECTIVE START-ROUND ACCOUNTING
==================================================================

Count prospective attempts. Every round is a potential run start; the calibrated unconditional event applies per start round, including starts whose first round fails. The lifecycle is unchanged (state still begins at the first observed success); only the accounting counts every round. State the bound as: per item (and for the root), the probability of a false FINAL or freeze in an epoch is at most ε × the number of rounds polled in that epoch. No conditional calibration.


==================================================================
## MINIMUM SAMPLE PRECONDITION — SUPERSEDED K ≥ 2
==================================================================

K = 1 is out of scope: Snowstorm requires K ≥ 2. A node that cannot sample at least 2 peers does not run Snowstorm and uses ordinary block relay. State the precondition; no K = 1 calibration or tests.


==================================================================
## MINIMUM SAMPLE PRECONDITION — K ≥ 3
==================================================================

Snowstorm requires K ≥ 3. A node that cannot sample at least 3 peers does not run Snowstorm and uses ordinary block relay. State the precondition in §8 and §11; no calibration or tests below K = 3.


==================================================================
## TWO-SIDED ITEM ALLOCATION
==================================================================

Allocate ε/2 to each item side; root keeps ε


==================================================================
## EMPTY ROOT USES ORDINARY ROOT VOTING
==================================================================

Delete the empty-state exception. An empty R ∪ Pending has an ordinary root (the commitment to the empty W) and freezes only through the root vote like any other root. Remove the sentence and its tests; add a test: an empty node whose peers hold {b} does not freeze empty, learns b, and freezes on {b}.


==================================================================
## PLAN-SPEC REVIEW — ROOT-PROGRESS DEADLINE AND STAGE APPROVALS
==================================================================

PLAN-SPEC review (from Shammah). Approved with these changes; do not execute any stage yet.

1. Limitation 4 is a liveness attack within the β_adv budget (fast non-matching replies keep the deadline below the slow MATCH quorum). Fix in §6.6: the next deadline also doubles after any round with no root success in which at least one sampled peer had not answered; a round with a root success returns to the formula. All-answered early end unchanged. Add the K = 16 trace (10 fast MATCH, 3 fast non-match, 3 slow MATCH) as a test that must freeze. Run IMPCD on this one change only, then update PLAN-SPEC.
2. Every numbered stage ends with STOP for my approval before the next begins.
3. Stage 4 includes compact-block, Graphene and Erlay-style baselines under identical load and topology, reporting the same byte categories.
4. Mark the 600 × 500 main evaluation scale as pending my confirmation.

Report the new bundle SHA, STOP.


==================================================================
## EPOCH-NONDECREASING DEADLINE — AUTHOR CORRECTION
==================================================================

Option 1, scoped to the epoch: after a root-success round, nextDeadline = max(normalFormula, currentDeadline). The deadline returns to the normal formula only at epoch start (new tip). Within an epoch it never shrinks; the all-answered early end means a larger deadline costs time only when a sampled peer is silent.


==================================================================
## SIZING AMENDMENT — MATCH ZERO-DIFFERENCE SAMPLES
==================================================================

SIZING AMENDMENT (from Shammah). Replace "a MATCH-only or silent round keeps n": each REPLY_MATCH is a sizing sample with Δ = 0, used in the same resize as REPLY_DIFF samples; only a round with no usable samples (all silent) keeps n. Evidence: Argon's trace (bundle cf2e1509…) shows n held at 2,805–3,070 cells across all-MATCH rounds after a one-round transient when FINAL-out items left the sketch, inflating rounds to ~1.4 s and freeze times to 12–30 s. Add a test: a round with 26 MATCH and 6 replies decoding Δ ≈ 2,242 does not raise n. Run IMPCD on this change only, append, report the SHA, STOP.


==================================================================
## DEADLINE AMENDMENT — POSSIBLE ROOT SUCCESS BACKOFF
==================================================================

DEADLINE AMENDMENT (from Shammah). Replace the doubling condition "no root success with any unanswered sampled peer" by: double the next deadline iff the round had no root success AND MATCH count + unanswered sampled peers ≥ the root success threshold (the unanswered peers could have produced a success). Otherwise next = max(normalFormula, currentDuration) as now; reset at new tip unchanged. Evidence: Argon's smoke shows the old condition doubling through every convergence round (root success impossible while sets differ) and ratcheting deadlines to 3.5–5.6 s, so converged rounds with one late peer take ~3.6 s. Tests: the K = 16 fast non-match trace still freezes; a convergence round with 1 MATCH and 1 late peer does not double. Run IMPCD on this change only, append, report the SHA, STOP.


==================================================================
## EPOCH QUESTION — OWNER INTENT
==================================================================

EPOCH QUESTION (from Shammah). My intent is many frozen epochs between blocks, with the block being the union of frozen epochs. First confirm whether the spec does this today (quote the relevant sections). If it does not, propose the minimal amendment for my approval, along these lines: on freeze of epoch k a node starts epoch k+1 with all held items not in a frozen epoch (starting IN); POLL carries the epoch number; a responder ahead answers from its frozen epoch, a responder behind abstains; the block is the ordered union of frozen epoch roots; at a new tip, included epochs are removed and the unfrozen remainder starts epoch 1. List every section and test it touches. Do not apply it until I approve. STOP.


==================================================================
## APPROVED EPOCH PROPOSAL CONTEXT
==================================================================

Owner-approved proposal context, quoted from the preceding assistant response. These are proposal items 1–4 and 7–9 expressly approved by the correction below; they were not originally authored by Shammah. Former items 5–6 are replaced by that correction.

1. **Separate tip lifetime from reconciliation epoch.** Each tip starts at epoch 1 and maintains an ordered archive of frozen epochs plus one active epoch.

2. **Seal and advance.** When the existing root-confidence predicate freezes a **nonempty** W, archive its immutable root and canonical transaction membership, emit `Frozen{tipContext, epochNumber, root, transactionIDs}`, and immediately start epoch k+1. Previously frozen transactions cannot enter later epochs again.

3. **Initialize the remainder.** All held transactions outside the frozen archive start the new epoch IN, with fresh preference counters, confidence and FINAL state. This includes held transactions previously OUT. Unadmitted Pending items remain OUT. Preserve same-tip fetch tokens, donor retries and host callback obligations, but reset their epoch-local tally state. Old-round replies cannot contribute to the new epoch.

4. **Scope reconciliation to the requested epoch.** POLL carries its epoch number. A responder:
   - at that epoch answers from its active state;
   - ahead answers from the immutable frozen state for the requested epoch;
   - behind abstains.

   For a historical reply, the advertised set is that frozen epoch’s membership, with no exclusions. Existing MATCH/DIFF/fallback formats and decoding rules otherwise apply.

7. **Reset on a new tip.** Remove transactions included by the accepted block, discard the old tip’s epoch archive/context, and start epoch 1 from surviving held transactions. Transactions from a locally frozen epoch that were omitted from the block return to that remainder. Reorgs use the same surviving-handle reset.

8. **Keep storage bounded.** Retain frozen membership/body references until tip reset so lagging peers can reconcile. Charge archived and active storage together against explicit bounds; do not retain historical cell arrays. Advancing only on nonempty batches prevents unlimited empty epoch records. Empty-root confidence does not append or advance an epoch.

9. **Preserve timing policy.** An epoch rollover is not a new tip: retain measured peer times and the deadline floor. Reset active-round captures, root evidence and active sizing state. The latest backoff predicate remains unchanged.


==================================================================
## EPOCH AMENDMENT — APPROVAL AND CUMULATIVE MERKLIX OVERLAYS
==================================================================

Correction to the epoch amendment, then approve (from Shammah). This was my explicit design: a new epoch starts every time the last one freezes.

- Replace items 5 and 6. The commitment for frozen epoch k is the merklix root of the overlay = union of frozen epochs 1…k since the last block, computed with the same function as the block's transaction commitment. This binds the prefix; no separate prefix commitment or ordered manifest. POLL carries the epoch number and the current overlay root; a mismatching overlay root supplies no evidence.
- GBT returns the latest frozen overlay.
- On block receipt, the host computes the block's reconstructed merklix root and looks it up among the overlay roots frozen since the last block. A match is a snap block; no match falls back to ordinary block relay.
- Items 1–4 and 7–9 as proposed.

Apply, regenerate the bundle, proposals, conformance report, normative diff and PLAN-SPEC together, run IMPCD on the epoch amendment until it converges, report the SHA, STOP.


==================================================================
## EPOCH CLARIFICATION — SAME PREFIX VERSUS PREFIX SPLIT
==================================================================

Option 3. Distinguish the two cases. (a) Same frozen-prefix overlay root (epochs 1…k−1), different active W: normal per-item votes and root confidence, unchanged. (b) Different frozen-prefix overlay root at the same epoch number: no per-item votes and no root confidence for that reply, because active sets under different prefixes are not comparable (an item frozen earlier by one node appears absent to the other). Laggards poll their own epoch number and are answered from the matching frozen epoch, so (b) applies only to genuine prefix splits; state that as the existing limitation (resolved at the next block). Add tests for both cases and for a laggard catching up through historical replies.


==================================================================
## CONFLICT HANDLING — VOTES OVERRIDE FIRST-SEEN POLICY
==================================================================

CONFLICT HANDLING (from Shammah). First-seen is host policy, and votes override policy. For transactions that spend a common input (a conflict pair): a node holds the first seen and votes yes on it, no on the other. When the majority preference rule flips a node's preference to the conflicting transaction it does not hold, the host replaces the held one with it, subject only to consensus validity (as the policy override). FINAL-in on one implies the other is OUT. Both FINAL-in at one node is reported as an anomaly (bounded by ε). A contested 50/50 pair stays out of overlays until the majority tips. Remove conflict handling from OPEN; add tests: a 70/30 double spend converges to the majority in every honest node's overlay; a 50/50 pair is excluded until it tips; a replacement keeps fetch and Pending lifecycles intact. Run IMPCD on this change only, report the SHA, STOP.


==================================================================
## CONFLICT CLARIFICATION — FROZEN WINNER UNTIL NEXT BLOCK
==================================================================

Answer to the frozen-prefix conflict question: epoch1 froze a; epoch2 learns conflicting b and majority favors b. The chosen rule is stated verbatim below.

Frozen winner excludes later conflicts until next block


==================================================================
## CONFLICT ANSWERS — EXISTING W SIGNALING AND PER-START ERROR SCOPE
==================================================================

Answers. (1) Remove the explicit 50/50 exclusion rule. A node holds one side of a conflict pair, so W never contains both; a split pair makes W differ across nodes, so no root success and no freeze until the majority preference tips and replacement converges W. Mid-epoch conflicts are fresh admissions starting OUT and do not affect active W. No new preference signalling. Test: a 50/50 pair held at epoch start delays the freeze until it tips, then the overlay contains only the winner. (2) Keep the existing per-start ε scope; a double FINAL-in implies a false FINAL-in already bounded per item; report it as an anomaly; no new guarantee. Continue IMPCD to convergence, report the SHA, STOP.


==================================================================
## LIVENESS AMENDMENT — CONFIDENCE ABOVE THE EXISTING NULL
==================================================================

LIVENESS AMENDMENT (from Shammah). Apply.

Change the confidence gate from y ≥ ⌈0.8·K⌉ to y > p0·K, where p0 = (1 + β_adv)/2 (= 0.6K at β_adv = 0.2). No new constant: the gate is tied to the existing null. Applies to item confidence (both sides) and to the root vote (MATCH count). Everything else is unchanged: evidence e = −ln P(Bin(K, p0) ≥ y), consecutive runs with reset on a non-success, minimum 3 successes, ε/2 per item side and ε for the root with the existing run-length spending. Recompute the exact T_r(K) tables for the new gate so the ε bound stays exact. Keep the majority preference rule (y > K/2) as is. Update every rule that references the old gate to the new one, including the deadline-doubling condition (MATCH + unanswered ≥ the root success threshold).

Evidence: Argon's R3/R4 at 20% adversaries froze only ~5% of honest nodes in 120 s, because per-round success at the 80% gate is ~50% at β_adv and runs never complete.

Report the new rounds-to-FINAL table at 70%, 80% and 100% agreement for D ∈ {16, 32, 64, 128, 500}. Add tests: at 20% adversaries voting against, rounds succeed with probability > 0.99 at K = 32; unanimous rounds freeze in the same number of rounds as before; the six (26, 28, 29) permutations and all existing counterexample tests still hold. Run IMPCD on this change only until it converges, report the SHA, STOP.


==================================================================
## LIVENESS DISPOSITION — STRICT NULL UPPER-MEDIAN GATE
==================================================================

Use the null upper-median gate: a confidence success (items and root) requires y > the median of Bin(K, p0), so the null success probability is below 1/2 and every all-success run eventually qualifies under the existing ε·2^−(r−2) spending (restores the finite-R proof). Recompute T_r(K); apply the same threshold in the deadline-doubling condition. Tests: K = 16 with 10 fast MATCH + 6 slow MATCH freezes; K = 32 at 20% adversaries succeeds per round with probability reported (expected > 0.99); unanimous rounds unchanged; the (26, 28, 29) permutations still reject. Report the 70%/80%/100% rounds-to-FINAL table. Continue IMPCD to convergence, report the SHA, STOP.
