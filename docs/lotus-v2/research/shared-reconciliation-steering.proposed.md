# Shared steering for reconciling nodes: one experimental policy

Status: proposed observational experiment; no new root-consensus, finality, parking or epoch-transition implementation is approved here. MinHash is accepted as advisory; exact roots remain separate choices. The same selector is used by stakers and nonstakers, but the same code need not produce the same answer from different evidence at every instant.

**Later accepted direction:** [aggregate then confirm](epoch-root-gossip-loop.proposed.md) keeps working membership mutable and pins only advertised versions. The fixed-candidate nomination/election experiment below is a comparison, not the chosen aggregation lifecycle. Prefix steering stays provisional; exact-root stake confirmation is separate, with best-effort peer steering in a distinct domain when stake participation is insufficient.

## Recommended precedence

Keep four separate records: (1) a validated local preference for one exact candidate; (2) fresh responses to this node's own issued samples; (3) held candidates and usable holder routes; (4) advisory similarity/cost hints. Do not combine them into an invented weighted score.

**First, preserve valid exact preference evidence.** Candidate identity binds domain, slot, predecessor/state anchor, commitment version and exact cumulative membership root. Sketch algorithm/domain/seed/base accompany the pinned descriptor but cannot disguise a changed root as the same choice. Current local similarity and immediate-neighbor popularity cannot overrule successful independently sampled evidence. Distinct roots never pool their scores because they look similar.

**Second, obtain the candidate the evidence points toward.** If a fresh owned sample indicates X while the node prefers Y, and X is not yet reconstructed, make X the desired retrieval target. Prefer an actual holder of X even if X is distant and Z is cheap/nearby. Fetch from one holder at a time, using other holders for bounded retry. Meanwhile retain the valid Y preference; do not cast a positive X vote or increment valid-candidate confidence before X is reconstructed and validated. Old hints may prioritize retrieval, but after reconstruction require fresh applicable sampled evidence for a preference update; do not retroactively treat unvalidated observations as an acceptance streak.

If X is unavailable, record UNKNOWN/unavailable for the applicable validation/decision purpose, keep bounded holder discovery and retry with backoff, and continue independent sampling/dissemination. Spare capacity may prefetch Z while X is in backoff; this is not adoption of Z, loss of the X discovery obligation or proof that X was invalid. A popular unavailable root must not own unlimited workers or block all other traffic.

**Third, use similarity only for cost among otherwise unprioritized work.** Without a supported retrieval target, compare advisory delta/prefix sketches to choose a bounded prefetch or reconstruction order. A tie can be randomized. Never restrict the security sample to nearby roots, the six connections supporting X, the current retrieval route or a MinHash cluster.

**Fourth, preserve independent exploration.** The existing count/time scheduler continues fresh configured relay fanout (currently25%, min8,max32) with its fair rotating opportunity and per-peer pacing. Do not replace that subset with nearest peers. In the experimental adapter, reserve ordinary scheduler capacity ahead of discretionary candidate prefetch; allow only one candidate reconstruction concurrently and at most one bounded new holder-discovery request per scheduled pass. These are provisional experiment limits, not tuned production constants. Discovery stays connected to all usable peers even while one target dominates fetch priority. This cannot defeat an actual eclipse or guarantee a low-conductance graph converges within a fixed time.

## Staker and nonstaker behavior

Both run candidate discovery, validation, holder lookup, the same retrieval selector and fair dissemination. A staker may additionally answer a root-choice poll positively for its fully validated local preferred candidate, under the selected exclusive-slot voting rule. Nonstakers contribute no authority weight merely by advertising, forwarding or observing. Their held data remains useful to everyone.

A nonstaker that runs an Avalanche observer can issue its own authenticated, context-owned queries to eligible discovered authorities and apply the same experimental preference adapter. It does not need to add a vote for itself. A node with Avalanche disabled, no usable sampling quorum or only forwarded advertisements cannot reconstruct trustworthy sampled confidence from those advertisements; it remains in permissionless discovery/prefetch mode. A forwarded signed poll response authenticates a statement but does not prove the forwarder's sample was unbiased, complete or applicable to this observer. It is not a transferable confidence certificate.

Source check on the repaired scheduler lineage: `Processor::isQuorumEstablished` treats local proof as optional, but requires its actual discovery, connected-node/score and other configured quorum conditions. `PeerManager::selectPeer` draws score slots from the local proof manager; `selectNode` then seeks an available eligible connection for that proof. Thus the existing facility does not require identical enumerable global rosters, and it also does not promise a globally uniform or identical sample distribution at every observer. Preserve proof/overlap validation and authenticated request ownership; measure available-proof/capability/connection selection bias rather than claiming it away.

Current `MSG_AVA_MEMPOOL_BATCH` polling returns an item's YES/NO/unknown status. It is not already an exclusive multi-root slot-choice response or the new adapter described here. The optional root-choice query/context and transition still require specification and source review. Reusing sampling/transport does not silently make the old item records implement this policy.

## Nomination and frozen evaluation

All-unique roots require a nomination rule before successful exact-root samples are likely. The experimental fallback is deliberately narrow: while a node has no successful validated candidate evidence in the active evaluation attempt, a paced nomination opportunity may choose one candidate from an independently sampled authority's current preference, reconstruct it, and nominate it locally. The selection is random among applicable sampled announcements, not closest-first or most-connected-neighbor-first. Nomination is not a successful poll, adds no confidence, and can be rejected for invalid/unavailable data.

Once a successful sample exists, use the explicit experimental flat multi-choice cumulative preference rule and separate root-specific consecutive observation from the ten-actor fixture. New ordinary arrivals remain staged. Existing held candidates are immutable; recovered data creating a different root names a new candidate and cannot inherit the old root's evidence. Freeze candidate generation during an evaluation attempt; timeout/restart must be explicit, retire old owned requests and reset the appropriate attempt evidence. This prevents casual arrival-driven root churn from masquerading as progress, but does not establish a common nomination boundary across the network.

Provisional resource envelope for the next adapter experiment: at most16 descriptor records, four retained reconstructed candidate views and one active candidate fetch, all subject to an aggregate byte/node reservation. Pin the current validated preference; evict only unselected idle candidates, discard their local evidence on eviction, and require fresh activation/evidence if reintroduced. These bounds can harm liveness or fairness when different observers admit different candidates. That tradeoff must be exercised rather than hidden as a harmless cache optimization. The ten-actor fixture currently has a common frozen ten-candidate universe and does not validate this four-view eviction policy.

Every request/completion carries the local evaluation attempt/activation and exact candidate/anchor generation. Under the owner, recheck those tags before committing reconstruction, preference or confidence. Restart, eviction/reintroduction and anchor change retire old owned requests before releasing their pins; delayed completions cannot attach to the new activation.

Reserve the aggregate footprint before fetching: pinned preference, target tree, reconstruction scratch, transaction/body leases and active serving views. If the reservation cannot be made, keep the valid preference and mark the target resource-deferred with bounded retry. Descriptor/view counts and one worker are not a byte bound, and resource pressure cannot silently evict the active preference.

An active delta means exact W minus F only after validating that the named immutable F is the shared base and a subset of W. Do not subtract cumulative MinHash sketches to manufacture a delta sketch. A synthesized ABC must pass the same base/state and execution validation as any other candidate.

No authoritative seal is attached to three observations or to this nomination rule. The recommendation is to compare these transitions in an observational adapter first. The missing unique shared-epoch transition and Byzantine nomination/availability argument remain real, bounded design obligations—not work the user must research.

## Concrete scenarios and failure criteria

| Scenario | Required behavior and limitation |
|---|---|
| Ten initially unique roots | Strict threshold-only switching stalls in the executable trace. Random valid nomination is an explicit additional symmetry-breaking rule; one successful seed is no safety/liveness theorem. |
| Six X, four Y | Retrieve X from one usable X holder if own evidence prioritizes it. Y peers independently sample and may still prefer Y. Keep their connections and evidence available. |
| Two similarity clusters with a narrow bridge | MinHash may favor internal fetches, but the ordinary random/fair path and authority sample remain independent. Trace bridge utilization, latency and candidate discovery. No fixed bound is promised under arbitrary partition. |
| Unequal peer degree or aliases | Connection count does not multiply authority score. Track sampled proof/authority identity and existing overlap rules; holder redundancy affects retrieval only. |
| MinHash lies or public-seed grinding | Bound wasted retrieval. Recompute against exact held content before trusting accuracy; never alter vote validity or join different-root confidence. |
| A distant sampled preference | Fetch that target rather than override it with a closer candidate. The executable selector cases cover identical retrieval priority for stakers and nonstakers. |
| Popular unavailable or stale root | No positive vote/confidence from missing data; bounded retry/discovery, expiry ownership and independent exploration continue. A later valid view requires fresh evidence. |
| New arrivals during evaluation | Stage them; do not mutate pinned choices. Old local data is not erased when a different exact candidate is selected. |
| Large cumulative base | Prefer comparable active-delta/prefix hints only with the same validated base. Nearly identical full-set sketches cannot conceal different exact roots or decide that their active differences are harmless. |

## Executable evidence and integration seam

The ten-actor executable model (not published in this repository) reproduces all-unique strict stalling, one randomized nomination trace, one6/4 trace, candidate churn, MinHash cluster ranking, and direct retrieval-selector precedence. Its selector cases explicitly show: far sampled X outranks near Z for both a staker and nonstaker; the staker still votes for held validated Y before X is ready; an unavailable/backed-off X permits spare prefetch without changing that vote. Source routing and one-at-a-time retrieval are logical fixture actions/static limits, not transport, retention, signature or real-stake tests.

Use the already prepared production harness seams to record: exact candidate/activation ID, held-body completeness, desired retrieval target, source connection, advisory distance, issued authority sample/context, authenticated outcome, preference score, consecutive observed-root streak, pending changes, eviction and retry reason. A later C++ adapter should consume one declared transition implementation in both actors and model after selection. The current Python experiment is intentionally not implementation-equivalence or security validation. No existing chain parking/finality behavior changes.
