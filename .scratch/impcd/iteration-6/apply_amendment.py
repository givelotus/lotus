"""Author-amended draft ledger; explicitly retain unresolved mathematical cases."""
import copy,difflib,hashlib,json,re,sys
sys.dont_write_bytecode=True
from pathlib import Path
here=Path(__file__).resolve().parent;repo=here.parents[2]
base=json.loads((here.parent/'iteration-5/ledger-final.json').read_text())
author=json.loads((here/'author-amendment.json').read_text());digest=author['current_input_sha256']
spec=''.join(c['text'] for c in base[0]['claims']);tests=''.join(c['text'] for c in base[1]['claims'])
spec=spec.replace('fb84e15abe521460cd55f65f693835b8047be070075191729fe07df0128e9d96',digest)
tests=tests.replace('fb84e15abe521460cd55f65f693835b8047be070075191729fe07df0128e9d96',digest)
spec=re.sub(r'REVIEW ROUND 5:.*?No freeze or implementation\.', 'REVIEW ROUND 6: evidence-weighted author amendment applied for IMPCD; open cases are explicit. No freeze or implementation.',spec,count=1)
section8='''## §8 EVIDENCE-WEIGHTED ITEM ROUNDS AND ROOT SETTLEMENT

D is the compatible connected peer population captured at round start. At small D, sample all D peers. The population at which K first drops below D is OPEN for the (f,K) grid; no crossover or replacement K formula is selected here. Experiments declare K explicitly, with 1<=K<=D. Select distinct peers uniformly from the canonical connected list using the seeded RNG. D=0 opens no round. beta_max remains the host's adversary-fraction assumption, not the new per-item success threshold.

Each nonfinal captured item receives at most one eligible observation per selected peer. Capture advertised raw A with incarnation/candidate bits and live Pending identities at round start, at most M+P records; post-capture items get no votes. Matching Pending admission preserves its lifetime and whole state; removal/readmission or loss of support invalidates prior-lifetime observations. Inbound polls never vote. FINAL items need no further votes.

Votes express the responder's candidate preference. MATCH gives yes for captured W and no for other captured eligible IDs. At arrival, decoded-present and nonexcluded gives yes; decoded-absent or excluded gives no. An incomplete arrival gives no other sharing inference: remaining captured items abstain. A complete arrival classifies other eligible captured reference items as shared unless excluded. DIFF reconstructs the peer's advertised raw set from captured raw A, then applies exclusions; captured Pending absent from that assertion is absent. No takes precedence over presence. Rescue-only discoveries abstain that round, including a later complete rescue. Silent, late, invalid or discarded contradictory replies abstain.

A node never casts a yes for its own Pending item: Pending is absent from its W, root, proof, advertised cells, set_size and exclusions. This does not prohibit receiving a yes from another node that has admitted the item. Such received votes score the poller's captured Pending lifetime and permit the expressly required FINAL-in Pending state. MATCH votes remain as before.

For item x, n_x=yes_x+no_x is the number of sampled peers casting valid votes on x. A side s succeeds when y_s>=ceil(4*n_x/5), where y_s is that side's actual vote count. The denominator is n_x, not K. OPEN EW-ZERO: at n_x=0 the literal inequality admits both sides; the required zero-contribution silence case needs an explicit no-success convention. For n_x>0, at most one side can succeed. A no-success round adds zero and resets nothing.

For a success, let m=ceil(D/2), let X have the hypergeometric law with population D, m peers on side s and n_x draws without replacement, and H=P[X>=y_s]. The round weight is e=-ln(H). Update the signed per-item evidence sum S by +e for IN, -e for OUT. Start S=0. Use natural logarithms. For a positive tail compute log H stably by log-sum-exp of log binomial terms over [max(y_s,n_x-(D-m),0),min(n_x,m)], without first underflowing H to zero. H=1 gives e=0. OPEN EW-INFINITY: true H=0 gives e=+infinity; no saturation, signed-infinity cancellation, replacement cap or other completion of the accumulator is invented. Opposing infinite contributions are undefined pending the author decision. These are per-round tail weights, not a restored root SPRT or match-rate estimator.

Retain the existing cumulative success counters d[in],d[out] and preference p, with d initially zero. Epoch-held IDs and fresh ordinary admissions initialize p=in; fresh Pending initializes p=out. On success for s increment d[s] once, and switch p only when d[s]>d[p]; a tie keeps p. Matching Pending admission preserves every field; it does not force preference in. No-success leaves p,d,S unchanged. Remove c, beta_c, previous-success streak state and all streak/reset logic. Item state remains bounded by M+P records. Counter overflow is an atomic local error as before.

Set T=-ln(epsilon), evaluated stably for the full valid epsilon domain. FINAL-in occurs when S>=T and d[in]>=3. FINAL-out occurs when S<=-T and d[out]>=3. FINAL is the side reached by the evidence threshold, independently of the prior preference; it is immutable and accepts no more item updates. A single huge or infinite contribution cannot finalize before three same-side successes. OPEN EW-PREFERENCE: the author has not yet specified how an immutable FINAL side different from cumulative-count preference affects that preference and the existing p-based gate; do not silently force agreement or preserve an executable contradiction.

At epoch start W is the held IDs. Evaluate the gate once at round end after item updates, using W_before before any entries/exits, with host removals authoritative. Interpret the amendment's IN-side sum as the signed evidence S in the IN direction: mu=sum(S[x] for x in W_before)/|W_before|, or0 if empty. Simultaneously remove members whose preference is out or whose FINAL side is out, and admit held outsiders with p=in and S>=mu. This replaces the previous-success/c gate value. OPEN EW-GATE: confirm this signed-sum interpretation if a separate positive-only accumulator was intended; no such extra accumulator has been added. Infinite sums/means remain subject to EW-INFINITY. Preserve one snapshot and simultaneous updates; admission alone does not bypass the gate.

Freeze iff ((W is nonempty and every W item is FINAL-in) OR (R union Pending is empty)) AND there is no live FINAL-in Pending item. Emit Frozen{root over W,sorted unique txids} once per frozen transition as before. FINAL-in Pending blocks freeze while the body is still unadmitted; continue the ordinary deduplicated fetch lifecycle with alternate yes-voting donors and retry after failure. Existing binding, host validation, one-operation-per-ID reservation and awaiting-admission obligations remain. A donor cannot bypass admission by a yes vote. Admission preserves the weighted state and applies the ordinary end-round gate. Body-failure lifetime cleanup is unchanged. Candidate-body or W changes invalidate an earlier freeze; no independent root score exists.

FINAL-out removes an ID from the advertised sketch view A and from W; it is never an exclusion during that lifetime and receives no more votes. Retain its host-admitted body bucket and terminal item state within existing M bounds until host removal or tip reset; do not create unbounded evicted-ID history. A is a derived view, not a second retained body set. Tip reset starts surviving admitted IDs afresh as before. K crossover remains intentionally OPEN; EW-INFINITY/EW-PREFERENCE and concrete review findings must be resolved before executable freeze.

'''
start=spec.index('## §8 ');end=spec.index('## §9 ',start);spec=spec[:start]+section8+spec[end:]
# Rule12: distinguish authoritative held bodies from their advertised raw-ID view.
anchor='## §5 SET STORE\n\n'
overlay='''R continues to own all host-admitted body buckets and their bounded item lifetimes. Define advertised raw A={id in R_ID whose state is not FINAL-out}. Encode A in every own POLL/REPLY and set_size=|A|; exclusions are A minus candidate IDs. FINAL-out IDs occur in neither cells nor exclusions. The decode reference is Ref=(A union Pending) minus FINAL-out IDs. Inbound POLLs decode against A alone. A is a derived membership filter over existing state, with no second body store. A gain/loss, including a FINAL-out transition, updates caches and retained invariant residuals exactly once by net reference membership. Message formulas below use advertised A wherever they name sent/peer raw IDs; host admission/removal capacity still counts all R bodies/IDs, including terminal ones.\n\n'''
spec=spec.replace(anchor,anchor+overlay)
# Update wire/reference identities consistently; keep physical host store R intact.
repls=[
('Ref=own R_ID union Pending','Ref=(own A union Pending) minus FINAL-out IDs'),('Ref=R union Pending','Ref=(A union Pending) minus FINAL-out IDs'),
("responder raw R_ID","responder raw A"),("own R_ID, distinct from the R_ID union Pending","own A, distinct from the (A union Pending) minus FINAL-out"),
("inbound POLL signed claims<=2*M (own R versus sent raw set)","inbound POLL signed claims<=2*M (own A versus sent advertised set)"),
("round capture raw R","round capture raw A"),("captured raw R","captured raw A"),("current R|","current A|"),
("own raw R so normal Pending","own raw A so normal Pending"),("Inbound decoding uses raw R","Inbound decoding uses raw A"),
("against the responder's own R (not Pending)","against the responder's own A (not Pending)"),
("set_size is own distinct admitted |R|","set_size is own distinct advertised |A|"),("own R encoding","own A encoding"),
("full exclusions=R_ID minus candidate IDs","full exclusions=A minus candidate IDs"),
("admitted raw IDs with admission incarnation and candidate bit","advertised admitted IDs with admission incarnation and candidate bit"),
("captured raw-set","captured advertised-raw-set"),("wanted intersect current R","wanted intersect current A"),
("R/Pending transitions that leave membership unchanged","A/Pending transitions that leave membership unchanged"),
("Pending-to-R or R-to-Pending transitions preserving membership","Pending-to-A or A-to-Pending transitions preserving membership"),
("Live Pending initializes preference out, cumulative counts d[in]=d[out]=0, c=0, no previous vote, and not FINAL.","Live Pending initializes preference out, cumulative success counts d[in]=d[out]=0, signed evidence S=0, and not FINAL."),
("Pending is outside W and does not block freezing.","Pending is outside W; a FINAL-in Pending lifetime blocks freezing, while other Pending does not."),
("zero counters, consecutive count zero, and no previous vote or FINAL status","zero success counters, evidence S=0 and no FINAL status"),
("both cumulative side counters zero, consecutive count zero, and no previous vote or FINAL status","both cumulative success counters zero, evidence S=0 and no FINAL status"),
("preference, counters, previous success and FINAL","preference, success counters, evidence sum and FINAL"),
("preference/side counters/consecutive count/previous side/FINAL","preference/success counters/evidence sum/FINAL"),
("both side counters and c zero, no previous vote, and not FINAL","both success counters and evidence sum zero, and not FINAL"),
("per-item Snowball state","per-item weighted-round state"),("§8 Snowball item state","§8 weighted-round item state"),
("whole Snowball state","whole weighted-round state"),("complete live Pending state","complete live Pending state"),
("no per-item scalar likelihood score or confidence-derived epoch eviction history is retained","the bounded per-item signed evidence sum is retained, but no unbounded eviction history or root likelihood accumulator is retained"),
]
for old,new in repls:spec=spec.replace(old,new)
# Probe fallback uses the inbound difference estimate and existing responder S floor.
old='For a probe,let h be the largest probe index actually sent;fallback REPLY is prefix[0,m),m=min(max_symbols_per_reply,max(2*(h+1),S(abs(set_size_r−set_size_q)))).'
new='For a probe, compute a transient difference estimate Delta_probe from its pre-peel residual against responder A using the existing approximate estimator and boundary/censor rules in §6.3; fallback REPLY is prefix[0,m),m=min(max_symbols_per_reply,S(Delta_probe)). A censored estimate supplies its lower bound. This estimate sizes this response only: no inbound sizing-bank sample or retained poll state is created. There is no largest-probe-index doubling operand. Discarded contradictory claims are not counted in the estimator lower bound.'
assert old in spec;spec=spec.replace(old,new)
# Rule10 keeps majority/all-answer ending, changes captured deadline inputs and backoff.
a=spec.index('Round end is earliest of strict-majority answered');b=spec.index('\n\n## §7',a)
spec=spec[:a]+'''Round end is earliest of strict-majority answered at elapsed t_maj followed by elapsed>=2*t_maj, all selected peers answered, or the captured fallback duration. The normal fallback duration is4 times the upper median, over the K sampled peers, of each peer's request-to-reply estimate captured at round start. A measured estimate is that peer's most recent time from sending POLL until receipt of the complete correlated reply, including transfer; use no averaging. A sampled peer without a measurement uses the upper median of the measured sampled peers; if none are measured, use the existing captured PeerCaps RTT fallback. Preserve the at-least1microsecond upper-median convention. A round with zero answers makes the next fallback duration twice this round's duration; after a round with answers the next returns to the normal captured formula. Use checked time arithmetic; no new constant. Strict-majority and all-answered early-ending conditions remain. Each correlated complete current reply supplies one measurement; late/stale replies remain discarded with no retained past-round slot. Measurement state is one bounded value per connected peer, within its fixed record budget. Factors2 and4 remain operational params.h constants.

D=0 idles without timer/round and resumes on connect; empty-state freeze follows §8 independently of peers. Host processes events by Time with peer-id tie order; replies precede timers at equal Time. Late timers evaluate once at actual Time without catch-up. Zero-answer fallback ends the round and starts another using the doubled duration. No early-freeze evaluation before round-end scoring. Correlated invalid-proof or malformed reply arrivals count for timing but not item votes; uncorrelatable bytes cannot satisfy a slot. Captured fallback time does not move with later measurements.\n'''+spec[b:]
# Replace old full-K limitations and obsolete confidence rationale.
a=spec.index('Silent peers abstain, but the sampled population for quorum');b=spec.index('\n\n',a)
spec=spec[:a]+'''Silent/late/invalid/undecoded observations reduce n_x under the new success rule, while D remains the full captured peer population in the hypergeometric tail. Answering and decoding may depend on adversarial identity and vote side; tail weights are not a proved sequential error bound under this selection. Report actual n_x, side counts and adversarial response shares. Fixed-population response selection and measured-deadline starvation are concrete review obligations; zero false/split freezes remain hard test assertions, not results established here.'''+spec[b:]
spec=spec.replace('The replacement confidence rationale is that one round is one projection of a correlated peer neighbourhood; likelihood magnitude from one projection is not accumulated as sequential confidence. Repeated round votes are required by the fixed consecutive-success threshold.', 'The author-selected confidence rule accumulates hypergeometric-tail evidence over successful rounds and requires at least three same-side successes before FINAL.')
spec=spec.replace('K=min(D,ceil(D/4))','K with an OPEN full-population-to-subsample crossover').replace('K in{ceil(ln D),ceil(D/8),ceil(D/4)}','K in{ceil(ln D),ceil(D/8),ceil(D/4),D}').replace('K in{5,16,32}','K in{5,16,32,128}').replace('K in{7,63,125}','K in{7,63,125,500}')
# Current questions: explicit unresolved cases, not invented arithmetic completion.
a=spec.index('## Remaining contract questions');b=spec.index('### Candidate-proof arithmetic vectors',a)
questions='''## Remaining contract questions

OPEN K-CROSSOVER: at small D poll all D; where K drops below D is left to the (f,K) grid, with no number chosen. OPEN EW-INFINITY: H=0 and opposite infinite weights; OPEN EW-PREFERENCE: FINAL versus prior preference; OPEN EW-ZERO: literal n=0 success ambiguity; OPEN EW-GATE: signed IN-direction sum interpretation if a separate positive-only sum was intended. Review also tests a one-fast-voter fixed-population attack and D=1 nontermination. Rule10's deadline calculation is author-specified and is not open. These draft markers expose unresolved semantics; no executable freeze or convergence is claimed.

Review records are in `.scratch/impcd/iteration-6/`. Implementation, table generation, simulator and network validation remain future evidence obligations.\n\n'''
spec=spec[:a]+questions+spec[b:]
# Rewrite active voting test requirements, keep the104 historical inventory verbatim.
a=tests.index('## Current replacement contract');b=tests.index('## Primitive and workload preservation')
newtests='''## Current replacement contract

- Success uses n_x valid item votes: y>=ceil(4*n_x/5); n=0 handling is explicitly OPEN pending review. Silent/late/invalid/undecoded abstain. Existing arrival observations, exclusions, MATCH and rescue abstention remain.
- Signed evidence S starts0; success contributes +/-e, e=-ln P[HG(D,ceil(D/2),n_x)>=y]. No-success adds0 and resets nothing. Require at least3 IN/OUT successes respectively in addition to S reaching +/-(-ln epsilon). FINAL is immutable and is its reached side, not prior preference. H0/opposing infinities and FINAL/preference integration remain OPEN.
- Preserve cumulative-count preference updates, whole-state Pending admission and one simultaneous gate snapshot; compare signed IN-direction S to mean S over prechange W. A separate positive-only sum is not invented.
- A node never sends YES for its own Pending: its advertised candidate set excludes it. Received YES votes from admitted holders can score the poller's captured Pending. A live FINAL-in Pending item blocks freezing and keeps ordinary deduplicated donor retries active.
- FINAL-out is removed from advertised sketch view A and W, is never in exclusions and needs no further votes. Physical body/state ownership stays bounded in R. Use advertised A for all cells/set_size/captured raw-set formulas; Ref=(A union Pending) minus FINAL-out.
- At small D poll all D. The K<D crossover is OPEN for the(f,K) grid, no numeric crossover chosen; fixtures print their explicit K.
- Request-to-reply measurements include complete transfer. Normal deadline=4*captured sampled upper median of last measured peer times, imputing unmeasured peers by the measured sampled upper median, otherwise existing fallback. Zero-answer rounds double next duration; an answering round restores formula. Majority/all-answered early endings remain.
- Probe fallback prefix length=min(cap,S(Delta_probe)), using transient probe difference estimate and censor lower bound, not2*largest-index span. Prefix-request fallback doubling remains unchanged. Ordinary bidirectional FetchBody, raw advertised-A DIFF reconstruction and exact-DIFF resizing remain.
- Fixtures retain1000fixed seeds and report freeze-round distributions at a horizon long enough to finish, with nonfinishing trials visible. Hard assertions: zero false freezes and zero split freezes. No >=99%-within25 target.

## Current weighted-round correction cases

These are requirements for the future executable-contract correction, not executed node acceptance. Current mathematical OPEN cases must be resolved before freezing their expected outcomes.

| Test | Coverage | Required assertion |
|---|---|---|
| T13_hypergeometric_tail_weight_vectors | §8 | Independently compute exact rational tails, natural-log e and implied same-side rounds for D16,32,64,128,500, all K answering and half K answering; print fixture K and actual y. Include unanimous and minimum80%-success counts; K=D benchmark rows do not select the production crossover |
| T13_at_least_three_successes | §8 | One or two huge-weight successes cannot finalize even if the threshold is exceeded; third same-side success can, subject to signed sum. Include H0 as an explicit unresolved-domain witness until its arithmetic is decided |
| T13_no_success_preserves_evidence | §8 | Silence/no-success contributes0 and preserves S and counters; no c, streak or reset remains; n0 ambiguity must be resolved explicitly |
| T13_OUT_subtracts_evidence | §8 | A finite OUT success subtracts exactly e; alternating finite successes do not reset accumulated evidence |
| T13_final_side_independent_of_preference | §8 | Threshold side decides FINAL even if cumulative-count preference disagrees; do not silently retain the prior preferred-side finality condition. Integration with gate preference remains OPEN |
| T13_preference_overtake_and_tie | §8 | Increment d[success_side] once; strict overtake changes preference, tie retains it before FINAL; no count is replaced by weight |
| T13_final_lifetime_immutable | §8 | FINAL side and terminal state accept no more updates; loss of lifetime or tip reset starts fresh |
| T13_gate_simultaneous_prechange_mean | §8 | Compare IN-direction evidence sums with one pre-entry/pre-exit W mean, empty mean0, simultaneous entries/exits and exact snapshot timing; no prior-success/c mask remains |
| T13_pending_admission_preserves_whole_state | §§6–8 | Transfer S, both success counts, preference and FINAL intact; no admission-forced IN or reset; captured lifetime eligibility preserved |
| T13_pending_not_locally_yes_but_remotely_scored | §§6–8 | Own Pending never in W/proof/own advertised cells or YES; a peer that admitted x can send YES for the poller's Pending lifetime and permit FINAL-in before body arrival |
| T13_final_in_pending_blocks_freeze | §§6–8 | Even with every W item FINAL-in, a live FINAL-in Pending x blocks Frozen; ordinary alternate yes-voting donors/retries remain deduplicated; admission preserves evidence and applies the gate |
| T13_final_out_not_sketched_or_excluded | §§5–8 | FINAL-out ID disappears exactly once from A, cached cells and eligible Ref, is never an exclusion and receives no more votes; body/state capacity still counts it in R until removal/tip reset |
| T13_capture_pending_and_postcapture_abstention | §§6,8 | Shared capture<=M+P, no post-capture item vote, incarnation/lifetime filters and whole-state Pending transfer |
| T13_match_equals_full_candidate_observations | §§6.1,8 | MATCH/full reconstruction produce identical eligible item observations; no body-possession assertion |
| T13_diff_local_excluded_peer_included_yes | §§6.1,8 | Locally excluded nonfinal x remains in captured advertised A; peer includes x; valid DIFF votes yes |
| T13_partial_explicit_preference_observations | §§6.2,8 | Arrival-decoded present/nonexcluded YES, decoded absent/excluded NO, other captured items abstain with residual; rescue-only discoveries never upgrade votes |
| T13_final_requires_three_not_one | §8 | No nonempty initially nonfinal W freezes in one/two successes even when e>T; genuinely empty state and other established freeze branches remain |
| T13_unique_final_side_agreement | §§8,9 | Required honest quiescent fixtures and adversarial schedules retain hard zero false/split assertions; record counterexamples rather than weaken oracle |
| T16_transfer_measured_deadline_and_imputation | §6.6 | Use most recent complete POLL-to-reply duration including transfer, no averaging; sampled upper-median imputation, all-unmeasured existing fallback, captured inputs, unchanged2*tmaj/all-answered early ending |
| T16_zero_answer_doubles_answer_resets | §6.6 | Repeated zero-answer rounds double next duration with checked arithmetic; a round with answers returns to the4*captured-median formula |
| T7_probe_fallback_difference_estimate | §6.1 | Probe fallback uses transient difference estimate through S/cap, not2*(largest index+1); censor supplies lower bound, no inbound sizing-bank sample or retained poll |
| T7_diff_only_round_shrinks_request | §6.3 | Exact DIFF samples still choose normal estimator argmin and may shrink; original conditional prefix growth unchanged |

'''
tests=tests[:a]+newtests+tests[b:]
tests=tests.replace('no likelihood primitive or match-rate estimator remains in the proposed protocol','the new hypergeometric upper-tail primitive replaces old LLR/root policy; no adaptive match-rate estimator remains')
tests=tests.replace('## Remaining contract questions'+tests.split('## Remaining contract questions')[-1],questions)
# Adapt non-historical obligations mechanically; retain historical case rows unchanged.
for text_name in ('spec','tests'):
    text=locals()[text_name]
    # Protect the historical inventory from new-rule vocabulary normalization.
    if text_name=='tests':
        i=text.index('## Existing frozen cases');j=text.index('## Other retained case obligations');protected=text[i:j];text=text[:i]+'__HISTORICAL_INVENTORY__'+text[j:]
    text=text.replace('full-K quorum successes','80%-of-valid-votes successes').replace('full-sampled-K quorum tests','valid-vote weighted-round tests').replace('full-K quorum','valid-vote success threshold').replace('reduce alpha to a quorum of answerers instead of full K','replace n_x by K in the success threshold').replace('item-round state','weighted item-round state').replace('round-count gate','evidence-sum gate').replace('raw R','raw A').replace('sent raw R','sent raw A')
    text=text.replace('cumulative side counters','cumulative success counters')
    if text_name=='tests':text=text.replace('__HISTORICAL_INVENTORY__',protected)
    locals()[text_name]=text
# Explicitly update the old probe fallback row and RTT-only timer rows when present.
tests=re.sub(r'^\| T7_probe_fallback_dense_prefix .*$', '| T7_probe_fallback_dense_prefix | §6.1 | Failed sparse probe yields a dense prefix from S(Delta_probe), with censor boundary and cap; never2*probe span, never echoes sparse cells |',tests,flags=re.M)
tests=tests.replace('no root accumulator, scalar item likelihood, match-rate estimator','no root accumulator or match-rate estimator; weighted item evidence is now required')
# Later operator rules13–15 supersede the zero-answer-only backoff and n0 ambiguity.
spec=spec.replace("A side s succeeds when y_s>=ceil(4*n_x/5), where y_s is that side's actual vote count. The denominator is n_x, not K. OPEN EW-ZERO: at n_x=0 the literal inequality admits both sides; the required zero-contribution silence case needs an explicit no-success convention.","Set answer_floor=floor(K/2)+1. A round counts for x only if n_x>=answer_floor; below this floor add0, count no success and change no item evidence/counters. For a counting round side s succeeds when y_s>=ceil(4*n_x/5), where y_s is its actual vote count. The success denominator is n_x, with the additional majority-of-K answer floor. This includes n_x=0 as no success.")
spec=spec.replace("A round with zero answers makes the next fallback duration twice this round's duration; after a round with answers the next returns to the normal captured formula.", "A round with fewer than floor(K/2)+1 sampled peers answering at all makes the next fallback duration twice this round's duration; after a round meeting that answer floor the next returns to the normal captured formula.")
spec=spec.replace('Zero-answer fallback ends the round and starts another using the doubled duration.','A below-floor-answer fallback ends the round and starts another using the doubled duration.')
spec=spec.replace('OPEN EW-ZERO: literal n=0 success ambiguity; ','')
spec=spec.replace('The sketch cache encodes current R at','The sketch cache encodes current A at').replace('every admitted ID add/remove at every cached scheduled index','every advertised A membership gain/loss at every cached scheduled index')
spec=spec.replace('A freeze can precede a delayed body admission.','A freeze can precede a delayed body admission only if no live FINAL-in Pending item blocks it.').replace('no fetch gate or hidden timeout constant is added','the explicit FINAL-in Pending freeze guard applies without an additional hidden timeout')
tests=tests.replace('n=0 handling is explicitly OPEN pending review.','Require n_x>=floor(K/2)+1; below-floor/no-vote rounds contribute0 and count no success.').replace('; n0 ambiguity must be resolved explicitly','; below-floor/no-vote rounds count no success')
tests=tests.replace('Zero-answer rounds double next duration; an answering round restores formula.','Below-majority-answer rounds double next duration; a majority-answer round restores formula.')
tests=tests.replace('Repeated zero-answer rounds double next duration with checked arithmetic; a round with answers returns to the4*captured-median formula','Repeated rounds below floor(K/2)+1 answering peers double next duration with checked arithmetic; a round meeting this floor returns to the4*captured-median formula')
tests=tests.replace('Cells/DIFF encodeR;nonmatching replies excludeR−W','Cells/DIFF encode advertised A;nonmatching replies excludeA−W;FINAL-out is in neither').replace('against ownR only','against ownA only')
tests=tests.replace('4*captured PeerCaps median','4*captured measured request-to-complete-reply median with declared imputation/bootstrap')
tests=tests.replace('No scalar item or root accumulator is introduced by an inherited case name.','Old root accumulators are not restored; the new signed weighted item evidence is required by the controlling amendment.')
tests=tests.replace('| T13_unique_final_side_agreement |','| T16_one_fast_yes_fifteen_slow_no | §§6.6,8 | D16,K16,one YES reply1ms,fifteen NO replies250ms: below-item-floor rounds add0; below-peer-answer-floor rounds double duration until NO replies count; no FINAL-in, eventual FINAL-out. Check voteCount<=answeredPeers and no new weighted success below the sample majority |\n| T13_unique_final_side_agreement |')
tests=tests.replace('OPEN EW-ZERO: literal n=0 success ambiguity; ','').replace('Review also tests a one-fast-voter fixed-population attack and D=1 nontermination.','The single-fast-voter attack is now guarded by the majority answer floor; D=1 nontermination remains under review.')
spec=spec.replace('Review also tests a one-fast-voter fixed-population attack and D=1 nontermination.','The single-fast-voter attack is now guarded by the majority answer floor; D=1 nontermination remains under review.')
tests=tests.replace('T16_zero_answer_doubles_answer_resets','T16_answer_floor_doubles_deadline_majority_resets')
# C++ illustrative interface uses Lotus braces, indentation and public access.
cppstart=spec.index('```\nclass SnowstormNode');cppend=spec.index('```',cppstart+3)
cpp=spec[cppstart:cppend]
lines=cpp.splitlines();methods=[line.strip() for line in lines if line.strip().startswith(('explicit ','Actions ','Stats '))]
cpp='```cpp\nclass SnowstormNode\n{\npublic:\n'+''.join('    '+line+'\n' for line in methods)+'};\n'
# Action alternatives remain an explicitly schematic data grammar, not invalid C++.
actiongrammar='Action alternatives: Send{peer,bytes}, FetchBody{peer,short_id,fetch_id}, Frozen{root,txids}, PeerMisbehaved{peer,reason}, ScheduleTimer{at}.\n'
spec=spec[:cppstart]+cpp+'```\n\n'+actiongrammar+spec[cppend+3:]
# Include the computed author-requested benchmark vectors without choosing a K policy.
vector=(here/'weighted-vectors.md').read_text()
vector=vector[vector.index('| D |'):]
tests=tests.replace('## Primitive and workload preservation','## Evidence-weight arithmetic vectors\n\nK=D rows exercise the full-population branch; quarter-D rows are declared comparison fixtures, not a crossover choice. Half-answer rows never meet the new sample-majority floor, so their applied contribution is0 and they cannot finalize; raw e is diagnostic. Same-side implied rounds include the minimum3guard and do not resolve opposite-infinity arithmetic. Exact rational tails and80digit weights are recorded in [weighted-evidence.json](../impcd/iteration-6/weighted-evidence.json).\n\n'+vector+'\n## Primitive and workload preservation')
# Apply the explicit source-grounded C++ naming request after semantic normalization.
from naming import Apply
spec,specnames=Apply(spec)
tests,testnames=Apply(tests,True)
(here/'naming-map.json').write_text(json.dumps({'notes_path':'/Users/shammah/repos/lotus/daemon/lotusd/doc/developer-notes.md','notes_sha256':hashlib.sha256(Path('/Users/shammah/repos/lotus/daemon/lotusd/doc/developer-notes.md').read_bytes()).hexdigest(),'methods':'UpperCamelCase','variables':'lowerCamelCase','class_members':'m_lowerCamelCase','constants':'UPPER_SNAKE_CASE','namespaces':'lower_snake_case','historical_case_references':'preserved verbatim, not proposed identifiers','mapping':dict(sorted({**specnames,**testnames}.items()))},ensure_ascii=False,indent=2)+'\n')
# Atomize this author-replaced baseline with fresh run IDs; later review IDs remain stable.
ledger=[]
for tag,path,text in [('S6','.scratch/oneshot/SPEC-PROPOSED.md',spec),('T6','.scratch/oneshot/TESTS-PROPOSED.md',tests)]:
    text=text.rstrip()+'\n'
    chunks=[];fenced=False
    for line in text.splitlines(keepends=True):
        if line.startswith('```'):fenced=not fenced
        if fenced or line.startswith(('```','|','#')) or not line.strip():chunks.append(line);continue
        parts=re.split(r'(?<=[.!?]) (?=[A-Z])',line)
        chunks.extend(s+(' ' if i<len(parts)-1 else '') for i,s in enumerate(parts))
    claims=[{'id':f'{tag}_{i:04}','status':'open','text':s} for i,s in enumerate(chunks,1)]
    assert ''.join(c['text'] for c in claims)==text
    ledger.append({'path':path,'sha256':hashlib.sha256(text.encode()).hexdigest(),'claims':claims})
    (repo/path).write_text(text)
(here/'ledger-initial.json').write_text(json.dumps(ledger,ensure_ascii=False,indent=2)+'\n')
# Parent remains untouched; write only the review patch.
old=(repo/'docs/lotus-v2/snowstorm.md').read_text();begin='<!-- snowstorm-core-normative:begin -->\n';end='<!-- snowstorm-core-normative:end -->\n'
assert old.count(begin)==old.count(end)==1
norm=spec[spec.index('# Reconciliation core: normative specification\n'):spec.index('\n---\n\n## Remaining contract questions')]
new=old[:old.index(begin)+len(begin)]+norm.rstrip()+'\n'+old[old.index(end):]
(repo/'.scratch/oneshot/normative-PROPOSED.diff').write_text(''.join(difflib.unified_diff(old.splitlines(keepends=True),new.splitlines(keepends=True),fromfile='a/docs/lotus-v2/snowstorm.md',tofile='b/docs/lotus-v2/snowstorm.md')))
print(json.dumps({d['path']:{'bytes':len((repo/d['path']).read_bytes()),'sha256':d['sha256']} for d in ledger},indent=2))
