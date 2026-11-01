# Snowstorm executable-contract test proposal — review round 27 (strict null upper-median confidence gate)

Regenerated in place from the maintained input bundle, SHA256 `a8d6f14d49f30a2fb75dafe6dd4925b25ae400bf1ff9c1b79133d8bc97795019`. The final per-item reply-vote and partial-peel instructions control over all earlier vote wording. No frozen test/header/harness/oracle/manifest or production implementation is changed. Argon owns simulations with fetchable uniques and printed 1 ms validation.

## Current replacement contract

Snowstorm requires K>=3. A node unable to sample at least3 peers uses ordinary block relay; no below-K3 calibration or test is specified. All complete-node polling fixtures supply at least3 compatible peers per tested node. Pure codec/field/oracle fixtures are not below-minimum Snowstorm runs.

- Preference: increment d[side] when sideVoteCount>K/2; p follows the larger counter and retains ties. Confidence: success iff sideVoteCount>=successThreshold,where successThreshold=min{y:P[Bin(K,p0)>=y]<1/2}, with finite e=-ln P[Bin(K,(1+maximumAdversaryFraction)/2)>=sideVoteCount]. No e/n, answer normalization, hypergeometric, latest-vote-per-peer cache or sample top-up.
- Confidence stores only the current consecutive side/run: no success resets0; opposite success resets then adds the current e as run1. FINAL needs run length r>=3 and evidence>=T_r^item(K) calibrated from the exact null score distribution, and its terminal side is the reached side. FINAL-out is omitted from advertised A/exclusions; FINAL-in never leaves through a tally update.
- W is held nonarchived bodies whose active item preference is pIN; held nonarchived items at epoch start start IN, fresh admissions without live Pending start OUT, and Pending admission preserves state. No entry gate or mean is retained. Before FINAL, majority d counters alone move p; admitted FINAL-in is in W only when §8.1 FINAL/frozen effective-OUT constraints do not block it; FINAL-out never is. Host removal, epoch rollover and tip resets end active tally lifetimes; immutable archive membership survives to tip reset.
- Root evidence separately counts eligible current-commitment MATCH replies with the same strict-null-upper-median/binomial rule and3consecutive-success floor. No root success or any W/commitment change resets it. Freeze depends on root evidence and no FINAL-in Pending item, not per-item FINAL. An empty R union Pending uses ordinary calibrated root voting.
- Policy refusal votesNO while unadmitted, preserves bounded policyWaiting evidence/capture and can reach FINAL-in. FetchBody CONSENSUS_ONLY then bypasses policy subject to consensus validation; invalid bodies never enter R and FINAL-in invalidity emits ProtocolAnomaly. A verified held-transaction conflict also permits CONSENSUS_ONLY replacement when the existing majority preference becomes IN before FINAL; §8.1 freezes no new priority rule. Frozen winners exclude later conflicts until the next block. Reservations remain withinP and admissions withinM.
- Deadline:4*captured successThreshold-th smallest latest measured complete request/reply time with stated imputation/bootstrap; no root success AND eligible MATCH count+unansweredCount>=successThreshold doubles next duration; otherwise nextDuration=max(normalFormula,currentDuration). The duration never shrinks within a tip lifetime, including epoch rollovers; only a new tip resets to formula. Only the all-answered early-ending branch remains.
- No-empty reply censor floor=max(L,InverseHalfCDF(m)), inverse of the strictF(Delta,m)<.5 stepCDF; probe fallback uses RequiredSymbols(first empty residual probe index), or RequiredSymbols(largest sent index) if none, with the existing cap. No point estimate or2*span operand.
- C++ UpperCamelCase functions/methods, lowerCamelCase variables, m_members, UPPER_SNAKE_CASE constants, lower_snake_case namespaces; exact historical references remain literal. All prescribed workload counts and zero-false assertions remain; zero-split applies to random graphs meeting the representative-peer sampling assumption. Clique-bridge splits are reported as a limitation, not failures. Report freeze-round distributions; no99%-within25target. Argon's rateless-stream simulator remains active.

- Every timely verified MATCH contributes one uncensored zero sizing observation to the same banks/resize as DIFF; no raw-set equality or peel is inferred. Only a round with no usable samples retains its previous prefix by default.

## Current tally, root, policy and sizing cases

These are future executable-contract requirements; the review arithmetic/event models do not execute a new SnowstormNode implementation.

| Test | Coverage | Required assertion |
|---|---|---|
| T13BinomialEvidenceAndRounds | §8 | Print exact item T_r(K;epsilon/2) and root T_r(K;epsilon),70%,80% and100%-agreement e/round and rounds-to-FINAL for D16,32,64,128,500 with explicitK; include K=D and declared grid comparison fixtures, not a chosen crossover. Distinguish exact encoded binary Configuration inputs from explicit rational reference fixtures; derive p0 without intermediate rounding. Use exact probabilities, score ordering and comparisons; no approximate decision arithmetic or underflow |
| T13FullKThresholdAndNoTopup | §8 | Success iff y>=successThreshold=min{j:P[Bin(K,p0)>=j]<1/2}; silence/late/invalid/undecoded count neither side. One-fast1YES and nine-answer8YES/1NO atD16,K16 give no success; mirror also none. No latest-vote history or extra sampled peers |
| T13StreakResetsOnGapAndOtherSide | §8 | With nonzero evidence/count, no confidence success resets0; opposite success resets then starts its own run with currente,count1. No signed subtraction or carried evidence from a former run |
| T13AtLeastThreeConsecutive | §8 | One/two huge-weight successes cannot FINAL. A run first finalizes at r>=3 only when its score reaches its exact T_r(K). FINAL side controls terminal preference; no later updates |
| T13PersistentSixtyFortyPreference | §8 | At exact reference beta=1/5,D=K10,persistent6YES/4NO votes increment only the majority d counter;successThreshold7 gives no confidence success; p converges to the majority with tie retention; evidence stays0 and item is not falsely FINAL |
| T13IntermediateMembersRemain | §8 | With80intermediate W members and2FINAL-in members, zero/low confidence never evicts intermediates. Only a pOUT transition exits a live member; FINAL-in stays |
| T13RootSuccessAndReset | §8 | Root success uses MATCH count>=successThreshold and binomial weight; no success or any candidate commitment change resets root evidence/count. Old-root MATCH can vote captured items but not a changed current root; root metadata never mixes commitments |
| T13ItemConfidenceDoesNotGateFreeze | §8 | Freeze predicate is current overlay root run length r>=3,evidence>=T_r^root(K),no FINAL-in Pending and nonempty active W; seal once and advance; no all-items-FINAL requirement or emitted empty batch. |
| T13NinetyPercentItemsNoRootSuccess | §§8–9 |100items each absent/excluded at a different10%of sampled peers: each item can get90%YES, but distinct candidate sets give insufficient MATCH, no root success and no freeze until roots converge |
| T13FinalInPendingVeto | §§6–8 | Root already over threshold cannot freeze while FINAL-in Pending remains; deduplicated yes-donor retries preserve decision. Matching admission transfers state; admitted pIN membership changes/resets the root |
| T13PolicyRefusalCanReachFinalIn | §§1,6.4,7–8 | A bound consensus-valid policy refusal retains P reservation/state and captured eligibility; local outgoingNO, remoteYES still count. On FINAL-in, CONSENSUS_ONLY fetch/admission bypasses policy; actual admitted callback required before R/W insertion |
| T10ConsensusInvalidFinalInAnomaly | §§1,6.4 | Consensus-invalid bound body is never admitted regardless of votes; FINAL-in triggers typed ProtocolAnomaly and existing invalid-ID cleanup. Wrong-bound/unparseable bytes stay donor-local failure, not consensus-invalid anomaly |
| T13FinalOutOmitted | §§5–8 | FINAL-out removed from active A/cache/Ref and never exclusions/votes in that epoch; retained body/state count towardcapacity. At next epoch rollover, held nonarchived items restart IN with no FINAL; archived bodies never reactivate |
| T16OneFastVoterDeadlineGrowth | §§6.6,8 | D16,K16,1msYES plus15NO250ms: no early IN success, backoff threshold11 causes growth until NO counted; x eventually FINAL-out under the selected timing rule. Report any liveness counterexample rather than weaken it |
| T16MeasuredDeadlineAndBackoff | §6.6 | Latest complete POLL-to-reply transfer time, captured successThreshold-th order statistic after existing measured-peer imputation/all-unmeasured bootstrap; no root success AND eligible MATCH count+unansweredCount>=successThreshold doubles; otherwise usesmax(normalFormula,currentDuration). No within-tip shrink on peer/K/W changes,polling pause or epoch rollover; newtip resets to normalformula. Trace9fast1ms/7slow250ms honest matching responses: quorum statistic250ms gives1000ms deadline, consecutive successes and freeze; also retain one-fast case |
| T7CensoredInverseHalfCDF | §6.3 | No-empty pre-peel residual usesmax(L,min integerDelta:F(Delta,m)<.5), strict at equality, finite grid+tail inverse with possibly nonmonotone empirical rows; no physical-count-only substitution or unbounded search |
| T7ProbeFallbackUpperBracket | §6.1 | First empty residual probe index before peeling, else largest actuallysent index, becomes RequiredSymbols argument; testindex0/cap, useindex notindex+1, no point estimator, no twice-span and no retained mask/samplebank |
| T7DiffOnlyRoundShrinksRequest | §6.3 | Exact DIFF samples stillresize/shrink normalargmin when no growthtrigger; cellfallback censor usesnew inversefloor; existing cap/dedup/banks remain |
| T13CapturedVotesAndRescueAbstention | §§6–8 | Shared captured lifetimes, postcapture abstention, terminalOUT filtering, full-state Pending transfer, arrival-only votes and no rescue upgrades/double counting |
| T13TenNodeSixtyFortyMembership | §8 | Complete ten-node fixture with six epoch holders of x, four late admissions and common b; ordinary body fetching; x becomes IN in every W and roots freeze equally, even when x initially lacks confidence successes |
| T13ThirteenOfSixteenFinalEntry | §8 | Thirteen YES of sixteen give FINAL-in after the required confidence run and actual admission includes x in W regardless of the other items' evidence; no mean/state capture |
| T13NobodyHeldNewTransaction | §8 | Nobody holds x at epoch start; later fresh admissions start OUT, remain outside W without an IN-majority history and never change the root merely by admission |
| T9RandomGraphSamplingScope | §§8,11 | Seeded network-wide random peer selection; test zero false and split freezes under the stated representative-sampling assumption; record topology/configuration/seeds |
| T9CliqueBridgeLimitation | §§8,11 | Two21-node cliques joined by one edge may freeze different roots; report roots/times as an assumption-violating limitation, do not fail the zero-split assertion for this fixture; consensus validity unchanged |
| T13ExactRunLengthThresholds | §8 | Exact sub-probability distribution retains success mass; choose the least attainable score with whole inclusive upper-tail mass<=b*2^(-(r-2)), or reject-all if none. Compare exact products and ties. Cover finite R tail representation with long all-success empty-W and FINAL-in-Pending-veto runs beyond R: score storage and represented count stop growing at R, no forbidden freeze occurs, ordinary no-success/root-change/K-change/epoch/tip resets clear the descriptor, and r-specific qualification remains exact before R. Distinguish represented count/tag from test-owned actual run length and check allocation accounting and a K change resetting item/root confidence before scoring while preserving preference counters and FINAL |
| T13SixPermutationNullCalibration | §8 | K32 counts(26,28,29),all six orders: no round3 FINAL if their accepted total null mass exceeds item-side epsilon_3=epsilon/4; root allocation at r3 is epsilon/2; use exact probabilities and the full null upper tail, not only one observed rectangle |
| T13NeighbourhoodScopeAndEpochRuns | §§8,11 | Fresh samples are from fixedD; bound is neighbourhood per-potential-start epsilon and,per item and for the root,active-epoch error at mostepsilon*roundsPolled; over a tip, sum the applicable epoch/start bounds rather than claimingepsilon for every frozen overlay together. Every polled round counts,including failed first rounds; lifecycle starts on first observed success unchanged,no conditional calibration. No epsilon bound is claimed for random-neighbourhood composition or network metastability |
| T13SilenceCannotSupplyVote | §8 | All abstentions yield no success or preference-counter increment. Report an exact trace if silence itself supplies a success or moves preference; selective suppression is distinct from an affirmative vote |
| T13TwoSidedItemEpochBound | §8 | Item IN and OUT use b=epsilon/2 each; root uses b=epsilon. Reproduce beta0,D1024,512 peers each side,K16,N100 with exact without-replacement observation DP and assert either-side FINAL probability<=epsilon*N; no simulation or approximate decision comparison |
| T13EmptyNodeLearnsPeerRootBeforeFreeze | §§6–8 | Eligible empty node with at least3 peers holding {b}: no Frozen(empty), ordinary POLL/DIFF discovery and bounded FetchBody/admission learn b, Pending state transfers, majority preference includes admitted b in W, and only calibrated MATCH-root confidence emits Frozen({b}); no immediate empty-state result |

| T16FastNonmatchingRepliesCannotStarveFreeze | §6.6 | K16,D16,beta.2:10honest MATCH at1ms,3valid nonmatching replies at1ms,3honest MATCH at250ms;13honest peers agree. No-root-success with10eligible MATCH+3unanswered reaching threshold11 doubles the next duration; root success retainsmax(normalFormula,currentDuration) within the epoch; all-answered early end remains. The node must eventually freeze; retain and report any counterexample rather than weakening the assertion |

| T7MatchOnlyRoundShrinksRequest | sizing_tests.cpp | From an oversized existing prefix, timely verified MATCH replies each record one uncensored zero sample in current/round1 banks; no peeling/raw-set equality assertion. All-MATCH resize selects n=1 using the d0 table row; all-silent/no-usable-sample control retains the previous prefix; late/invalid/duplicate replies add no sample |
| T7MatchZerosMixedWithLargeDecodedDifferences | sizing_tests.cpp | Existing n in2805..3070,cap permits it;26timely valid MATCH zero samples plus6decoded uncensored current-difference samples around2242 (exact2242reference). Use the ordinary combined-sample CDF/cost estimator and unchanged applicable growth rules; assert nNext<=nPrevious. Exact reference argmin is1, because cost(1)<=32/26<2 while cost(n)>=n for every n>=2. No censor-median or zero-decode trigger applies |

| T16ConvergenceCannotSupplyRootQuorumKeepsDeadline | §6.6 | K16,referencebeta1/5,threshold11,1eligible MATCH,14complete nonmatching replies,1late peer: no root success and1+1<11, so nextDuration=max(normalFormula,currentDuration), not doubled. Repeat without deadline ratcheting; normal-formula increases still apply. Boundary controls:10MATCH+1unanswered doubles,10MATCH+0unanswered does not;11MATCH succeeds and retains the epoch floor. Correlated invalid replies fill timing slots but add no MATCH; duplicate/uncorrelated/late replies do not fill additional slots. A captured commitment change makes old-root MATCH ineligible under §8 |

## Successive epochs and frozen overlay cases

All full-node fixtures collect epoch-tagged Frozen outputs; single-epoch assertions inspect epoch1 explicitly. Full observation distinguishes active sets from immutable archives. Frozen outputs carry cumulative overlay transactionIDs; reference truth is independently accumulated from disjoint archived batch bodies. Merklix fixtures use the host's same non-coinbase Subtree A function and ordinary coinbase/top-level block-root combination, not a hash of epoch roots or a tip-salted stand-in.

| Test | File / spec | Requirement |
|---|---|---|
| T8FreezeAdvancesEpochAndReinitializesRemainder | lifecycle_tests.cpp,§§5,7,8 | Freeze nonempty batchA, emit epoch1 once, start2 immediately. Held nonarchived items including prior FINAL-out restart IN with fresh counters/evidence/FINAL; archivedA stays immutable and absent from active W/A/Ref/cells; if no nonarchived body remains, later MATCH rounds emit no second batch; Pending starts OUT while reservations survive |
| T13FrozenOverlayUnionAndGbt | voting_tests.cpp,§§1,8 | Before the first freeze, query the Snowstorm-backed GBT path and require no frozen overlay, including with nonempty active W; no empty epoch is fabricated. FreezeA thenB before a block; overlay roots equal host merklix(A),merklix(A union B), not merklix(rootA,rootB). Frozen and GBT expose latest cumulative overlay; unfrozenC is absent; later admissions/removals cannot invalidate archived outputs |
| T7AheadServesRequestedFrozenEpoch | poll_tests.cpp,§6.1 | Node at epoch3 receives same-prefix epoch1 and2 POLLs; use respective batch/raw/candidates,no exclusions and correct preceding/frozen overlay roots. MATCH/DIFF/fallback from one historical state; no local fetch,tally,Pending or archive mutation |
| T7BehindAndPrefixSplitAbstain | poll_tests.cpp,§§6.1,8 | Behind responder abstains. Same epoch/different frozenPrefixRoot supplies no per-item/root evidence; correlated injected split reply affects timing only,no peel/fetch/sizing. Same-prefix/different activeW follows ordinary decoded item votes; only eligible MATCH scores root confidence |
| T9LaggardHistoricalCatchup | pooling_tests.cpp,§§5,6,8 | At least4nodes,peers ahead with compatible archived prefixes; laggard polls own epoch,fetches missing historical batch,freezes matching overlay,advances and repeats. Remove a historical batch body from every ahead donor's live R before the laggard fetches it; ordinary body service must still serve the archived handle without donor readmission. No double counting of earlier batches; eventually same frozen overlay |
| T11EpochContextWireAndStaleIsolation | adversarial_tests.cpp,§6.1 | Version3 epoch/prefix framing on all4types; epoch0,truncation,overflow,mismatched tip/epoch/prefix,duplicate and late replies. Prefix mismatch is nonpunitive. Old-epoch replies cannot supply effects after rollover even though tip key is unchanged |
| T8EpochRolloverKeepsFetchBindings | lifecycle_tests.cpp,§§5,6.4,7 | Live inflight/awaiting/policy reservations and first-decode timestamp survive same-tip rollover; epoch-local state resets; matching callback transfers current state once. Old-tip callback remains stale. No duplicate fetch or saved old confidence restoration |
| T8NewTipOverlayLookupAndRemainder | lifecycle_tests.cpp,§§1,5 | Before clearingoldtip roots,match reconstructed block non-coinbase merklix subtree root to any retained frozen overlay (including an older one): snap reconstruction. Miss ordinaryrelay. In either case validate normally,drop included bodies,carry held omitted frozen/unfrozen bodies into fresh epoch1; reorg same surviving-handle rule |
| T8NoEmptyEpochLoop | lifecycle_tests.cpp,§§5,8 | Empty activeW with repeated qualifying MATCH roots never emits/appends/increments epoch; polling continues. Empty node with peers holdingb learns it and freezes nonempty overlayb through normal voting |
| T12FrozenArchiveAggregateBound | adversarial_tests.cpp,§6.5 | Across many freezes/removals,liveR union archived bodies/IDs<=M,nonempty batch records<=M; no cumulative membership copies perroot,no historical cell arrays; actual handles/index/workspace capacities charged and typed overflow atomic. Archive freed at tip |
| T8FrozenCollisionAndRemoval | lifecycle_tests.cpp,§§3,5 | Remove archived body from liveR: retained historical body/root unchanged; duplicate admission never reactivates. Distinct colliding body cannot mutate archived body view; normal collision limits and validation remain |
| T16EpochRolloverSizingAndDeadline | timing_tests.cpp,§§6.3,6.6 | Activeprefix,samples,capture,residuals/root evidence reset for next epoch; measured request/reply values and deadline floor persist to tip. Existing possible-root-success backoff/all-answered end unchanged; no later-epoch first round reuses stale active samples; preserve epoch1-round1 history in the existing second bank through two same-tip rollovers, then use it once at the next tip and overwrite it only with the new tip's epoch1-round1 observations; exactly two banks |
| T15EpochOverlayDeterminism | determinism_tests.cpp,§10 | Same calls/seed yield identical epoch boundaries,merklix roots,archives,GBT selections,snap-hit/miss paths and transcripts in same/cross-process and observation modes |

## Conflict policy and replacement cases

No conflict wire extension or separate balanced-membership rule. Existing full-K preference/MATCH/confidence rules apply; fixtures declare their exact local votes,topology,tip and epoch. Compare frozen cumulative overlays after actual body admission,not a substitute preference model. All host bodies/descriptors use independent validated input truth; peer assertions cannot install privileged conflict facts.

| Test | File / spec | Requirement |
|---|---|---|
| T13ConflictSeventyThirtyMajorityReplacement | voting_tests.cpp,§8.1 | Ten honest epoch-start holders:7holda,3holdb,commonunrelatedc;complete graph,K=D9,real fetchable consensus-valid doublespend bodies. First full samples give a strict majority at every node;they may now pass the lower confidence gate,but the minimum3successes prevents immediateFINAL; minority holders replaceb witha on preference IN beforeFINAL,using matchedPOLICY and CONSENSUS_ONLY path. After root convergence every honest frozen overlay containsa and notb; do not require FINAL before replacement |
| T13ConflictBalancedEpochStartThenTips | voting_tests.cpp,§8.1 | Eight honest nodes,4a/4b,connected D6 graph with each node3a/3b neighbours,K6;W includes its held epoch-start spend,no ad-hoc exclusion. Eligible MATCH3<successThreshold5 yields no root success/freeze. Add an a-holder and move to full9nodeD8 graph: b-nodes see5a/3b and flip, a-nodes4a/4b retain preference;replacement converges allWa and onlya reaches frozen overlays. No omniscient global-tie detector or new signalling |
| T13ConflictFreshMidEpochRemainsOut | voting_tests.cpp,§§7,8.1 | Fresh conflicting admission with no live Pending startsOUT and does not alter activeW; no conflict first-seen IN seeding exception. Matching live Pending admission transfers its current state unchanged |
| T8ConflictReplacementKeepsPending | lifecycle_tests.cpp,§§6.4,8.1 | Replacement with ordinary fetch in flight,POLICYwaiting,awaitingAdmission,donor failure/disconnect and duplicate/stale result;one reservation and one operation perID. Admitted-result,loser-removal,target-admission sequence preserves target preference/counters,currentconfidence,incarnation,descriptor,firstdecode timestamp and binding;netRef/cache deltas once |
| T8ConflictAdmissionAuthorizationRace | lifecycle_tests.cpp,§8.1 | CONSENSUS_ONLY target flipsOUT,changesepoch,gets opposingFINAL/frozen winner or tip reset before completion. Current read-only authorization denies stale trigger;host returnsCONTEXT with no partial replacement,no target insertion,no false peer penalty;retry only after current authorization. Wrong hash/live token HostContractError;unknown token STALE |
| T13FinalInConflictConstraintAndAnomaly | voting_tests.cpp,§8.1 | FINAL-in a constrains known b effectiveOUT without fabricated FINAL-out,rewriting terminal evidence or losing reservation. INmajority cannot override live winningFINAL. Delayed validated relation with bothFINin emits typed anomaly before suppression,preserves decisions,does not admit both and retains Pending freeze veto;Known conflict pair with two validated live Pending policy alternatives,no pre-existing FINAL/frozen blocker and structurally valid hostile replies asserting both candidates: hold admissions until their IN runs qualify in the same scoring batch. Stage/publish both terminals before derived constraints;require anomaly,retained decisions,no permission to admit both and Pending freeze veto. Reverse per-item traversal/storage order and require identical semantic outcomes. This hostile robustness trace is not claimed possible under honest disjoint confidence quorums or the representative-neighbourhood null. Retain pre-existing-FINAL and delayed-relation controls;duplicate report markers bounded;existing epsilon/null scope only |
| T8FrozenWinnerExcludesLaterConflicts | lifecycle_tests.cpp,§§5,8.1 | Archivea,then majority favorsb sharinginput. Reject replacement authorization and exclude b fromactiveW/laterbatches through unrelated epoch rollover;historical a/root/GBT/snap remainimmutable. Changing raw preference/admission of a still-blocked body does not reset the active root run;actual effectiveW/body changes do. Newblock resets/recomputes constraint;heldsurvivor rekey rules remain |
| T12ConflictDescriptorCapacityAndChurn | adversarial_tests.cpp,§§1,6.5,8.1 | At mostM+P shared immutable body/input descriptors and constant flags,no quadratic edge/history table. LocalPOLICY metadata missing/wrongbound hash is atomicHostContractError. Record/working capacity limits checked;host-owned payload separately measured;removal/rollover/tip cleanup and dense direct conflicts staybounded |
| T11UntrustedConflictCannotSuppress | adversarial_tests.cpp,§8.1 | Peer fakeIDs,shortID collisions and unvalidated conflict claims cannot create trustedinput facts,evictheld bodies,overrideconsensus or rewritearchives. Exact body/hash/currenttip binding required;wrongbody remains existing donor failure |
| T8ConflictRelationIsNotTransitive | lifecycle_tests.cpp,§8.1 | a spendsu,b spendsu+v,c spendsv. a/c can beheldtogether;authorized b replacement displaces its actual direct conflicts subjectonlyconsensus checks;no relation falselydeclares a/c conflicting. Collisionbucket removals arebody-specific |
| T15ConflictReplacementDeterminism | determinism_tests.cpp,§§1,10 | Identical event order/seed gives identical read-only authorization,status callbacks,netRef changes,anomaly markers and Frozen outputs in all observationmodes;no hiddenhost query or peertruth access |

## Strict null upper-median gate cases

Reference arithmetic uses exact beta=1/5,p0=3/5,epsilon=1/10^9 unless explicitly testing encoded binary inputs. For the requested comparison table use K=D and observedY=ceil(agreement*K) at70%,80%,100%; this does not select the OPEN production crossover. Report first item qualification with budgetepsilon/2 and root qualification with budgetepsilon separately. Exact distribution predicates include all qualifying success paths and equal-score atoms,not a fixed-log-budget/evidence shortcut. A proof by certified rational bounds may establish a displayed first-qualification count only when it certifies all earlier rejections and the first acceptance; it does not replace the normative exact startup table definition or round a decision.

| Test | File / spec | Requirement |
|---|---|---|
| T13StrictNullUpperMedianGate | voting_tests.cpp,§8 | Compute m=min{j:CDF(j)>1/2},alpha=m+1=min{y:tail(y)<1/2} from exact encoded p0;referenceK16alpha11,K32alpha20,K64alpha39,K128alpha78,K500alpha301. For beta0,K3choosealpha3 (not2 with q=1/2);allallowedK>=3have0<q<1/2,nonempty support and finiteR |
| T13AdversaryBudgetRoundSuccess | voting_tests.cpp,§8 | With all honest replies valid/timely and20%votingagainst in the binomial alternative model,K32newalpha20 gives Psuccess=925684794379590434816/931322574615478515625≈.9939464795662064> .99;report ratherthan hide the value. Missing/late honest votes remain abstentions and get no such probability claim |
| T16TenFastSixSlowMatchingPeersFreeze | timing_tests.cpp,§§6.6,8 | K16,10MATCH1ms,6MATCH250ms,referencealpha11. With bootstrap/imputed1ms estimates,deadline4ms cannot succeed on10MATCH;possiblequorum doublesuntil slow repliescount. Current complete timingmeasurements then feed11thorderstatistic,retainfloor,and all-answered earlyend. Unanimous confidence needs3successes,so nodefreezes;also test all estimates already known250ms,normalformula1000ms and all-answered250ms end |
| T13UpperMedianCalibrationRegressions | voting_tests.cpp,§8 | Recompute exact T_r from new unconditional success support and unchanged epsilon allocations/geometricspending. All six(26,28,29)permutations stillreject atK32,r3. Unanimousmaximum-scoreatom remains p0^(Kr),so unanimousfirstqualification counts areidentical tooldgate for eachK/budget. Report70/80/100item/root tables withYrounding,K and exactreferenceinputs |

## Primitive and workload preservation

Preserve field/cell/schedule/sketch/peeler oracles and all their exact workloads. Existing hypergeometric and saturation fixtures are historical arithmetic evidence only; the new binomial-tail primitive and root/item runs replace old hypergeometric/LLR policy; no adaptive match-rate estimator remains. Old root/item saturation and finite SPRT DP cases are historical arithmetic evidence only, not current protocol requirements; replace their policy assertions explicitly when the executable contract is corrected. Do not retain old batch confidence or scalar item-score fixtures as active full-node acceptance criteria.

Retain 7000 T7 trials, 5/20/100-node T9, 100000 malformed inputs for each of the four current wire types, the 50-height/20-node soak, all T14 boundaries, all T15 cross-process and observation-mode checks, and the existing body-service/transport/callback assertions. Additional tests do not substitute for these workloads.

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

The following nonvoting cases retain their workloads. Current replacement rules above control where older wording was superseded. New root/item binomial run evidence is required; the old SPRT policy is not restored by the controlling amendment.

| Test | File / spec | Requirement |
|---|---|---|
| T9FetchableUniqueAgreement | §§8,9 | Per-node unique bodies remain fetchable;after quiescent catch-up compare each unique in every honest node's frozen prefix union active W, not active W alone across different epoch numbers; compare frozen overlay roots at matching epoch boundaries separately and report genuine split/nonfreeze outcomes |
| T12ConfidenceBoundNoEvictionHistory | §§6.5,7,8 | All R plus livePending scores<=M+P;no sticky confidence epoch-mark table |
| T7CellsRawExclusionsCandidate | §§6,8 | Cells/DIFF encode advertised A;nonmatching replies excludeA−W;FINAL-out is in neither;POLL no exclusions |
| T16FetchValidation1ms | §9 | Unique bodies served from owners;body completion includes donorRTT,serialization and printed1ms validation |
| T6CurrentSetInterleavedChanges | current_store_tests.cpp | §5: 10000 seeded add/remove sequences, compare all current IDs/bodies and random cached prefixes to independent log replay after every operation; only bounded frozen batch handles retained; no historical poll pins/log retention |
| T6CurrentCollisionAndAdmissionSequences | current_store_tests.cpp | §§3,5: retained SipHash hand vector, multiple bodies per ID, duplicate no-op, partial/last-body removal, readmission seq and cache equality |
| T6CurrentResetRekeysAndReleasesCapacity | current_store_tests.cpp | §5: tip and block-disconnect reset to epoch1, surviving handles including omitted frozen bodies, cache extension to exact limit, only approved immutable batch archive retention within aggregateM; tip releases it; overflow atomicity |
| T7StaticOneshot7000FreshTrials | poll_tests.cpp | §6: differences 0,1,2,3,10,100,1000, 1000 fresh seeds each, both sides; compare each successful decode to reply-time responder truth; no continuation; final candidate/body agreement |
| T7SmallDifferenceOneExchange | poll_tests.cpp | §6: honest distinct differences <=2 complete decoding with one POLL/REPLY_DIFF when inbound symbol0 decodes; equal roots use REPLY_MATCH, which does not prove raw equality |
| T7ReplyIsCurrentAndInternallyConsistent | poll_tests.cpp | §§5,6.1: interleave admissions/removals before delivery; cells/root/size/full exclusions all match a single reply-construction state; repeated polls may see changed state |
| T7MatchWithExcludedRawExtra | poll_tests.cpp | §§6,8: identical current overlay root and prefix with unequal active raw sets returns MATCH; assert candidate equality only |
| T7MatchAssertionDoesNotAuthenticateBody | poll_tests.cpp | §§1,6,8: malicious echo never inserts body or authenticates raw membership |
| T7DecodeTimeReferenceAndPartialResults | poll_tests.cpp | §6.2: own/Pending changes between send and receipt; frozen per-call Ref, independent residual checks, failed peel retains valid partial fetch opportunities and records arrival decoded-present/decoded-absent/exclusion observations; residual unclaimed items and rescue discoveries abstain |
| T8ConstructorAndBodyResultValidation | lifecycle_tests.cpp | §1: preserve invalid Configuration domains, live enum/hash/binding validation and stale-token precedence from three old T8 cases |
| T8TenRoundsAllRemovalReasons | lifecycle_tests.cpp | §§5–7: 0–5 adds/removes each side before/during/between 10 rounds; every RemovalReason; no double residual update on fetched admission; exact next sufficiently-sized poll after quiescence |
| T8PendingOnlyFetchOrAwaiting | lifecycle_tests.cpp | §7: six original counterexamples plus policyWaiting/FINAL-in-wait reservations: decode without fetch reservation, fetch-only without prior decode, result-to-admission gap, own removal without support, removal with live awaiting support, and ended support followed by repeated decode; no history/session support |
| T8HashBoundAwaitingPreservesPendingItemState | lifecycle_tests.cpp | §§6.4,7:preserve token/hash/generation/reservation and all item-state fields across timer,disconnect and suspension;matching admission preserves the lifetime once, without changing preference or FINAL;tip cancels |
| T8TipResetCancelsOldGeneration | lifecycle_tests.cpp | §§1,5: stale results before payload validation; cancelled awaiting callback cannot resurrect old confidence |
| T8CollisionRemovalRekeyAndReadmission | lifecycle_tests.cpp | §§3,5,7: exact body/ID/root changes, rekey, positive/negative claims in different polls, all removal reasons |
| T8DisconnectAlternateAndLateResult | lifecycle_tests.cpp | §6.4: cancel inflight before payload validation; immediate known alternate; awaiting survives disconnect; reconnect gets fresh identity |
| T9FullMesh520100Nodes | pooling_tests.cpp | §§6–8: original 5/20/100-node workloads and seeds, candidate/body agreement; every successful raw reply exact against host truth; release all retained state at round end/abandonment |
| T9PendingHolderAndAbsentPeer | pooling_tests.cpp | §§6.2,7: four-node fixture with three holder/absent/Pending roles plus an additional compatible peer, K>=3; Pending hides a +decode from honest holder; success still discovers usable donors ; absent peer yields negative evidence without cancelling another live fetch |
| T10FakePartialAndSuccessfulReplies | pooling_tests.cpp | §6.4: real/fake mixed replies, each eligible fake fetched, failure removes unsupported Pending, real IDs reconcile, no fake R/Frozen insertion |
| T10PeerLocalFailureHonestAlternate | pooling_tests.cpp | §6.4: notFound/wrong binding peer-local, policy rejection nonpunitive, matched invalid height-wide, honest donor after false failure; bound/collision cases preserved |
| T10DonorSlotsReleasedAndStaleResults | pooling_tests.cpp | §6.4: eight occupied donor slots, failures free slots, honest ninth; cancelled late result cannot poison successful admission |
| T11OneshotWireGoldensTruncations | adversarial_tests.cpp | §6.1: exact independently written bytes for all four messages; every truncation, noncanonical CompactSize, suffix byte, count and integer overflow |
| T11100000MalformedPerWireType | adversarial_tests.cpp | §§6.1,6.6: 100000 seeded malformed/oversized cases for EACH of four types; bounded allocation, no crash/assertion; concurrent honest polls continue |
| T11SingleReplyInconsistency | adversarial_tests.cpp | §6.6: false size/count, impossible count bound, inconsistent declared cell count, exclusion cardinality/duplicates/zero; report only independently provable faults |
| T11FailedDecodeIsNotMisbehavior | adversarial_tests.cpp | §6.6: honest undersized replies and adversarial syntactically valid undecodable cells terminate; no penalty for peel failure alone; only permitted arrival item observations count; unclaimed items in an incomplete reply abstain, including when rootVote equals the poller root; a rootVote field is not a verified MATCH; only eligible MATCH replies supply the separate root confidence |
| T11PollIdentityDuplicateOldTipAndLate | adversarial_tests.cpp | §§6,8: wrong peer/poll/context/generation, duplicate and out-of-order responses; no repeated evidence or fetch; late item/root evidence ignored |
| T12GlobalAndMessageLimitBoundaries | adversarial_tests.cpp | §6.5: each approved bound -1/exact/+1, allocation before parse rejected, 2MiB total including full exclusions; accepted host state never blocked by stale peer models |
| T12FixedPeerStateAndReplyRelease | adversarial_tests.cpp | §6.5: allocated-capacity accounting after each call, fixed peer floor plus bounded current-round failed invariant-residual/index/exclusion buffers; repeated/duplicate failures cannot exceed the round workspace; nothing retained across rounds |
| T12PendingUnionAndFailureSaturation | adversarial_tests.cpp | §§6.4,7: retain admitted/connection/Pending/fetch/awaiting/donor/failure-table boundaries and suspension regression; no eviction/refetch loophole |
| T12FiftyHeightsTwentyNodes | adversarial_tests.cpp | §6.5: original 50-height/20-node soak; last10 mean <=1.1*first10; height rollover uses bounded sizing records; retained global bounds and all actual transient capacities checked |
| T7CandidateNonceProofVectors | poll_tests.cpp | §6.1: independently derived domain0/domain1 SipHash vectors, LE key/ID/proof bytes, empty/set XOR, order, collisions and nonce binding |
| T7MatchExcludedRawExtraAndChurn | poll_tests.cpp | §6.1: unequal raw sets with identical candidates yield valid proof; root change in flight accepts stored-proof MATCH; mismatch reports inconsistentReply |
| T7ApproximatePrepeelLikelihood | sizing_tests.cpp | §6.3: maximize independent likelihood over[L,2M+P],smaller tie,above-domain branch censors at L, while no-empty branch applies the inverse-half-CDF floor;{0} zero=>0 else inverse-floor censored;hostile input never authenticated |
| T7ProbeIndicesAndRoundCensoring | sizing_tests.cpp | §6.3: approved sparse mode/basis, lowest-index clipping, zero-R{0}, round-median censor decision, no per-peer probe state |
| T7EmpiricalRequestArgmin | sizing_tests.cpp | §6.3:quantile-mean CDF/cost ties; include M=262112 with cap=4 and an exact DIFF sample32768: scaling the positive4096-grid quantiles by8 makes every length at least8, greater than4, so every capped candidate has F=0: cost is +infinity, choose the smallest candidate before unchanged growth/cap rules;median censor independently doubles;zero-decode requires fallback cells and no successful decode/MATCH/DIFF;only no usable samples retains n; MATCH contributes zero and mixes with DIFF in the normal estimator, which may shrink n |
| T7DiffOnlyRoundShrinksRequest | sizing_tests.cpp | Start from an existing oversized prefix; all timely replies are valid REPLY_DIFF with small exact differences. With an independent synthetic quantile fixture whose normal cost argmin is smaller than the prior prefix, assert nNext equals that argmin and shrinks. DIFF is a decode success; no zero-decode trigger. Retain separate censored-median and zero-decode doubling tests unchanged |
| T7FirstHeightAndHeightRollover | sizing_tests.cpp | §6.3: scaled individual previous-round1 samples rounded up,empirical argmin,zero previousR fallback,consumed bank overwrite;two1024-record banks independent of currentD |
| T7FrozenTableGeneratorAndInterpolation | sizing_tests.cpp | §6.3:2000 trials,SplitMix64 ID rejection then next-output sign,historical generation cap=floor((2MiB−100)/28),grid endpoint4096;20 stored quantiles,step CDF,next-larger-d and scaled tails;S=rank1000,linear median interpolation;CDF next-larger-grid |
| T7ResponderFormulaAndFullExclusions | sizing_tests.cpp | §6.1: own raw sizes, exact prefix m formula and probe alternative, full exclusions, header byte accounting and2MiB at M boundary |
| T11ProofWireIdentityAndInvalidAbstention | adversarial_tests.cpp | §§6.1,8: all truncations, old wire versions2and earlier, unknown/duplicate nonce/poll, wrong proof is reported but never root/item evidence |
| T11StatelessResponderHostRateLimitBoundary | adversarial_tests.cpp | §6.6: same-epoch/same-prefix polls answered with current data,ahead peers serve requested historical batch,behind or incompatible-prefix peers abstain; no retained per-peer flood/reputation state, no core pollFlood; host drops separately observed |
| T12SizingAndItemStateCapacity | adversarial_tests.cpp | §6.5: current/round1 banks, M+P bounded Snowball item-state records and current-round observations; no confidence-derived epoch marks, transient start-estimator ledger, sparse protocol buffers charged;growable test audit separately owned/reported; active item state released at removal/rollover; frozen membership remains bounded to tip |
| T16SilentSlowMatchingFreezeRoundDistribution | timing_tests.cpp | §8:controlled victim+32 peers,23fast1ms/6silent/3slow100ms,beta.2,epsilon1e−9,fixture K=8 at D32;retain1000 fixed seeds;run to a horizon long enough to finish and report the freeze-round distribution and any nonfinishing trials;no >=99%-within25-rounds acceptance condition;hard assertions: zero false freezes and zero split freezes on random graphs meeting the sampling assumption;report failures without changing seeds |
| T16AllAnswerAndFallback | timing_tests.cpp | §§6.6,8: all answered or captured deadline, whichever occurs first; no strict-majority early end; 4*captured quorum order statistic of measured request-to-complete-reply times with declared imputation/bootstrap; zero answers still advance |
| T16TenPercentLossTwoAndFiveNodes | timing_tests.cpp | §8:10% seeded loss each directed link, eventual candidate agreement in honest fixtures; fallback advances rounds without continuations |
| T16TimeOrderTiesLateTimerNoCatchup | timing_tests.cpp | §§1,6.6: Time order/peer-id ties, replies before timers, captured fallback duration>=1us; malformed/invalid-proof arrivals count timing but not evidence; late timer evaluates once at actual time |
| T16LateReplyDiscardAllEffects | timing_tests.cpp | §§6,8: expired-round REPLY/MATCH discarded without decode/fetch/sizing/votes, no retained past-round slots; stale context ignored |
| T16NoPeersConnectDisconnect | timing_tests.cpp | §§1,8:initialD0 idles;connect starts next eligible round;during round disconnect abstains without discarding captured item observations or changing captured sample;fallback progresses even if all disconnect |
| T7ApproximateEstimatorCalibration | sizing_tests.cpp | §6.3:Delta10/50/150/500,1000 trials each,prefixS;include censored lower bounds;mean[.9,1.1],nearest-rankp90[.7,1.4],report censor counts,no retuning |
| T7NowVsRoundStartEstimate | sizing_tests.cpp | §6.3:undo only currently-present round additions,remove departed IDs,unchangedR/Pending transition not logged;P-list overflow disables start estimate for round and uses now without penalty/abandonment |
| T12IdChurnReleasesItemState | adversarial_tests.cpp | §§5,8: more than M distinct IDs across repeated remove/admit while live R<=M; bounded frozen membership plus no historical active item-state growth; readmission starts a fresh active admitted lifetime (archived duplicates do not reactivate) |
| T7FailedReplyRescuedByOtherPeer | poll_tests.cpp | Peer A fails alone; peer B's decoded items enter Ref via legitimate live support; A succeeds with the same raw/candidate reconstruction as fresh rescue-time decoding. New rescue discoveries abstain; no R insertion bypass |
| T7RetainedResidualEveryRefTransition | poll_tests.cpp | §6.2:harness retains independent wire bytes;core retains one invariant residual,never raw copy;private peel copy discarded;each netRef delta once;negative claims never directly mutate invariant; item observations use explicit arrival outcomes and captured lifetimes; rescue adds no votes |
| T7CascadePollOrderAndSingleObservation | poll_tests.cpp | Smallest dirty poll repeatedly; success releases/failure clean; <=K*(1+RefChanges) attempts and no dirty reply. Same-call or later rescue never adds/upgrades arrival observations or duplicates sizing/fetch |
| T12RetainedReplyWorkspaceAndRelease | adversarial_tests.cpp | §6.5:<=K residual arrays,indices,exclusions<=K*M,one transient work buffer;no second raw copy;growable observation audit excluded from protocol reservations;allocation failure fails test;release all at boundary |
| T15SameSeedRescueTranscript | determinism_tests.cpp | Same seed produces identical Ref deltas,rescue order,actions and evidence within one process and across processes |
| T16RoundEndOrTipCancelsRescues | timing_tests.cpp | No cross-round retention; late replies discarded; root-changing admission preserves eligible item observations; round end (including the freeze/epoch-rollover boundary) or tip reset releases retained replies; required current-root reset; captured item votes remain eligible only within their original active epoch |
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
| T7ZeroDecodeGateNoCellsAndCap | sizing_tests.cpp | §6.3:only no usable samples retains n; MATCH contributes zero and mixes with DIFF in the normal estimator, which may shrink n;successfulMATCH orDIFF suppresses zero-decode trigger;censored median independently doubles;probe transition=maxSentIndex+1 clipped to cap;no return to probe |
| T7PollSuccessReplyDiffBidirectionalFetch | poll_tests.cpp | Inbound success produces the true missing/wanted raw-set difference and starts ordinary responder FetchBody for its positives from the poller; poller FetchBody requests missing. wanted triggers no body-send action; ordinary token binding, reservation and retries apply |
| T7PollStateConsistentPrefixAndProbe | poll_tests.cpp | POLL root/raw setSize/cells from same state,exact prefix or clipped probe indices;later changes do not alter sent bytes |
| T7PollMatchingRootSkipsDecode | poll_tests.cpp | Structurally valid matching root yields proof,no peel attempt/fetch/sizing sample;poll-cell bytes still counted |
| T11PollCellStructuralFaultsReported | adversarial_tests.cpp | Raw symbol0/size mismatch,impossible counts,index/length/grammar/overflow reported before peel,including matching-root path |
| T11PollPeelContradictionStillReplies | adversarial_tests.cpp | §6.6:contradictory inbound attempt discards ALL its effects silently before fallback;ordinary incomplete positives may fetch;structural faults still reported |
| T12PollDecodeTransientPBound | adversarial_tests.cpp | One transient working buffer and<=2M inbound claims against ownA only;no POLL retention/rescue;fetch union<=P;both156-byte POLL and140-byte REPLY/full-exclusion limits fit2MiB |
| T7PollPendingUpdatesOutboundInvariant | poll_tests.cpp | §6.2:inbound Pending updates all retained invariants exactly once and triggers normal ordered rescue;no inbound retention,no new sizing sample |
| T15PollCellByteAccounting | determinism_tests.cpp | Exact28*m sent/received poll-cell bytes,framing separately counted,identical mode transcripts;MATCH proof16/full application98 bytes |
| T7PollDecodeReferenceExcludesPending | poll_tests.cpp | Responder Pending differs from advertised A; inbound decode uses A only, missing/wanted reflect the two advertised raw sets, excluding retained FINAL-out bodies and speculative Pending |
| T7PollIncompleteFallsBackToCells | poll_tests.cpp | §6.1:ordinary incomplete inbound peel may fetch partial positives then replies with cells;contradiction discards all attempt effects then replies with cells;no inbound retention |
| T11ReplyDiffGoldensAnd100000Malformed | adversarial_tests.cpp | Kind3 independent byte goldens,every truncation,100000 seeded malformed cases,ordering/zero/duplicates/overlap/count overflow/size relation/exclusion bounds;no partial effects |
| T11ReplyDiffWantedSentMembership | adversarial_tests.cpp | §6.1:wanted validated against one round raw capture,including excluded IDs;post-send removal does not falsely penalize;missing ID or signed size mismatch reports inconsistentReply |
| T12ReplyDiffFullPayloadBound | adversarial_tests.cpp | §6.5:complete DIFF over message limit falls back to cellREPLY;no truncation/fragmentation;check both exact boundary and full list bytes before effects |
| T10ReplyDiffFakeIdsRequireBodies | pooling_tests.cpp | Structurally valid missing assertions may be fake;FetchBody/host validation unchanged,no direct R/Frozen insertion,existing failure/probation behavior |
| T15PollMatchWastedCellBytes | determinism_tests.cpp | Matched-exchange poll cells charged separately once;DIFF ID bytes and fallback cell bytes separated;all counts reproduce exact wire sizes |
| T16FetchRTTSerializationValidationMidround | timing_tests.cpp | Host body service=donorRTT+body serialization+configured validation delay;callback at actual completion including mid-round,never batch to round end |
| T10LatencyMetricsBoundedLifetimes | lifecycle_tests.cpp | §10:first-decode timestamp in the live reserved fetch/awaiting/policyWaiting record survives donor retries;host admission without prior decode has no sample;P-bound and no historical decode table |
| T7CensoredPrefixNeverReturnsToProbe | sizing_tests.cpp | Scripted true difference always above request;each censored/zero-decode prefix strictly grows until success/cap;estimator cannot reduce floor or switch to probe |
| T12OneRoundCaptureSharedByAllSlots | adversarial_tests.cpp | One shared capture of at most M+P admitted/Pending lifetime records, no body handles or K copies, released at round end/tip; exact post-capture abstention and transfer eligibility |
| T7DeferredPollNeverCreatesSecondCapture | poll_tests.cpp | Later send shares capture only if the captured admitted/candidate/Pending state is unchanged; otherwise defer to next round, no new capture or mixed-state cells/root |
| T7DiffNowStartExactListCounts | sizing_tests.cpp | missing already inPending/R,wanted removed since send,post-capture admissions;exact specified now/start formulas at reply entry before fetch effects |
| T7ProbeSpanThenMonotonePrefix | sizing_tests.cpp | Unusable/censored probe=>max index sent+1 capped,otherwise estimator;once prefix exists never probe again,including all-MATCH/silent rounds |
| T7PendingAbsentFromRootProofSizeCells | poll_tests.cpp | Pending affects decodeRef only;never candidate root,expected proof,raw setSize,own encoded cells or exclusions until validated admission |
| T7FallbackDoublePrefix | §6.1 | Failed prefixPOLL produces prefix length min(cap,max(2n,RequiredSymbols(size difference)));test floor-dominant,doubling-dominant,cap and overflow inputs |
| T7ProbeFallbackDensePrefix | §6.1 | Failed sparse probe yields dense prefix from RequiredSymbols(first empty probe index), else RequiredSymbols(largest sent index), cap; no point estimate or2*span |
| T7FallbackNoPartialWirePayload | §6.1 | Fallback contains own raw cells and exclusions only;no partial IDs,residuals or bitmaps |
| T7DiffMissingWantedTrueDifference | §6.1 | missing is responder-only,wanted is poller-only;strict order,disjointness,exact capture-based count relation, missing/capture disjointness, exclusion-subset consistency and raw-set truth |
| T11DiffWantedCaptureValidation | §6.1 | wanted must belong to sent raw capture;currentR/Pending cannot substitute;reject before any body-send/fetch/evidence effect |
| T8MissingFirstDonorDedup | §§1,6.1,7 | First eligible donor starts one live operation; concurrent duplicates do not refetch; notFound/disconnect retries a usable alternate. Retain all T10 honest-donor recovery obligations |
| T8WantedResponderOrdinaryFetch | §§1,6.1 | Responder positive decode starts ordinary FetchBody from poller; wanted itself triggers no request, body-send action or special receive token at the poller |
| T8WantedSourceRemovalAndLoss | §§1,6.1 | Ordinary responder fetch handles source removal, loss, notFound, invalid body, stale/duplicate callbacks and alternate-donor retry with existing token lifecycle |
| T7FallbackNoBackPropagation | §6.1 | Decoding fallback never emits body-send of poller-only IDs;responder's later own poll may discover them |
| T12BidirectionalFetchReservationBounds | §§6.5,7 | Both directions use the existing P union reservation; wanted creates no extra awaiting table, sender action, or second request |

## Files and freeze/removal plan

Independent field/schedule/model oracles remain unchanged; operation-log truth is test-owned, not protocol history. Add independent sizing/proof oracles and hand-derived self-tests. Freeze generator, seed, table digest and generator self-tests. Proposed paths: test/oracle/{sizing.h,sizing.cpp,proof.h,proof.cpp}; test/generator/{sizing_table.py,README.md}; test/data/sizing_table.csv. Seed0x534E4F5753544F52; no table generation in this step. Full-audit observation storage is test-owned and growable, not a production reservation. Extend frozen inventory and extra-file detection to these new contract directories. Reference peeler for generation is independently written, not an import of production code. Table domain is fixed through4096 with approved linear extension; generation historical generation cap=floor((2MiB−100)/28).

Keep primitive math tests unchanged. Replace supplemental verify/voting_early_tests.cpp old early-freeze/root-SPRT policy tests with approved round-end/full-K binomial-streak/root tests in the correction and freeze them; do not retain the superseded policy as a current acceptance requirement. Keep underlying arithmetic regressions including finite DP labelled as primitive-only evidence. The production preview helper is obsolete policy and must be adapted only after external review.

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

Mutations: T1 wrong field reduction; T2 bypass reference-sign check; T3 wrong schedule boundary; T5 omit scheduled subtraction; T7 use send-time Ref instead of decode-time Ref; T10 preserve unsupported Pending after failure; T13 replace K by answerers in the confidence threshold, and separately permit a rescue-only discovery to vote that round; T16 omit fallback or introduce a first-answer/strict-majority early timer before the captured deadline. Each mutation compiles, fails its named frozen test, restores exact source bytes, passes, and ends with both repos clean. Never edit tests to accommodate the mutant.

## Stages and stop boundary

Stage A covers nonvoting arithmetic, current-store membership, codec/POLL/DIFF/fallback, sizing, body binding, retained-residual rescue, hostile input, bounds and deterministic host behavior. It uses test-owned candidate snapshots, not a substitute voting implementation. Q4/Q6 are resolved: ordinary FetchBody is used in both directions, REPLY has no mode/basis fields, and both cell-byte and schedule-index limits apply.

Stage B also covers host-validated conflict inputs,pre-FINAL majority replacement,serialized current admission authorization,FINAL/frozen constraints and the required70/30,balanced-tip,lifecycle cases. Stage B also covers multi-epoch rollover,historical replies,frozen-overlay merklix/GBT/snap lookup and bounded archive lifecycle. Stage B covers majority preference and binomial confidence state, full-K strict-null-upper-median confidence successes, MATCH equivalence, admitted preference membership, FINAL, root settlement/freeze, full-node agreement, candidate/body churn and all complete-node T1–T16 workloads. It must not stub voting, retain a batch accumulator, or pass by weakening obsolete tests. The exact open-case expectations below must be resolved before freezing those cases. Argon’s simulator evidence remains distinct from executed acceptance tests; the earlier requirement for Shammah to confirm Argon’s results is retained.

No freeze, production implementation, host-relay change, table generation or simulator execution is performed by this regeneration. No commit or branch rename is authorized without the operator’s approval. Regenerate and list open issues; regenerate PLAN-SPEC.md only after actual document convergence, then STOP.

## Remaining contract questions

Round-7 dispositions close the prior deadline-cycle and membership failures by changing the deadline order statistic and removing evidence-based membership. The connected-clique split is a documented limitation outside the stated random-network-peer sampling assumption. Regression requirements cover these dispositions; prior review records remain historical evidence.

Conflict handling is closed by §8.1. OPEN K-CROSSOVER: point K<D remains for the (f,K) grid; no below-K3 operation. This remains the intentional author deferral. No unresolved major review finding remains in the selected scope. The K16 response-selection liveness attack is closed by the epoch-nondecreasing deadline rule and required must-freeze regression; earlier limitation reports remain historical. No broader protocol claim is reopened.

This regeneration uses the final bundle SHA above. PLAN-SPEC.md was synchronized after scoped upper-median-review convergence; no stage was executed. Every numbered stage ends with STOP for Shammah’s approval before the next begins. No commit or branch rename is authorized without approval. Argon's rateless-stream simulator remains in use. Scoped IMPCD records are in `.scratch/impcd/iteration-27/`; prior rounds remain historical.
