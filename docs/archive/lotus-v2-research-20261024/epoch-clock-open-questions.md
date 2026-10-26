> **Latest review:** §§9.4/10 now specify stake-first total priority and committed contributions, with grinding and ACS limitations acknowledged. The current proposed behavior contract and experiment plan appear in the final “Current committed-contribution review” section. Older variant objections below are historical where superseded. No production protocol has been selected.

> **Status: Superseded by Snowstorm ([`../snowstorm.md`](../snowstorm.md), 2026-10-24).** This document is retained as a historical research record of earlier D11 explorations. See **[`../snowstorm.md`](../snowstorm.md)** for the normative specification of Snowstorm's multi-peer rateless $\text{GF}(2^{64})$ BCH fountain miniblocks, coupled peeling decoder, Type 1/2/3 algebraic fraud proofs, self-clocking `parent_base_root` layer promotion, two-phase anti-drip union with symmetric Phase 2 demotion, symmetric transitive conflict quarantine (`BatchId(E)` tiebreaking), and 0-RTT `SnapBlock` (`SEALEDHEADER`) propagation.

# Epoch clocks: authored heartbeat DAG, progress vector, or accepted parent chain



**Scope update — current §9 variant:** The supplied proposal now explicitly removes per-transaction finality. The finalized-only objections below apply to the earlier base design, not §9. The current review is appended as “Section 9 update”; keep the variants separate. No option has been selected.

## Recommendation

For the reconciliation repair, use the exact accepted parent-BatchId chain as the authoritative epoch order, with the exclusive per-slot candidate/finalization lifecycle already specified. This is a scalar causal chain, **not a vector clock**, and must be described honestly. A bounded peer-progress vector can help locate lagging peers, but should not become a finality certificate. Introduce an authored heartbeat DAG only if authenticated concurrent causal history and independent clock progress are themselves requirements worth a new consensus subsystem.

The AB|D→ABC|DE requirement does not require a vector clock. It requires exact proposal membership, an owned epoch target through admission, candidate/top reassignment, immutable proposal versions and fresh root-bound votes. A clock cannot supply that ownership mapping or replace proof that C belongs to the candidate being reconstructed. Conversely, if the requirement is specifically an authenticated vector clock that defines cuts, neither a renamed counter nor a decorative observer clock meets it.

## What the primary sources actually establish

The original Snow/Avalanche paper describes repeated randomized sampling and a transaction DAG used to combine related consensus instances. That is evidence for a consensus DAG architecture, not a built-in per-validator authored-event vector clock. Its stated safety model is probabilistic and parameterized; those claims cannot simply be transferred to a different clock protocol. [Original paper](https://arxiv.org/pdf/1906.08936)

Current Avalanche documentation describes Snowman for linear chains, subsampled preference voting and confidence, with AvalancheGo-specific parameters. This is not evidence that eCash has the same parameters, validator population or certificate format. [Snowman documentation](https://build.avax.network/docs/primary-network/avalanche-consensus)

ACP-181 makes an epoch a block range sharing a fixed P-Chain height and start time, so the validator-set view needed by the next block is predictable. A timestamp-qualified block seals the epoch; the following block starts the next one. It does not introduce a heartbeat-authored vector clock, nor does it directly add epochs to the P-Chain VM. Lotus/eCash has no corresponding P-Chain registry to import. [ACP-181](https://docs.avax.network/docs/acps/181-p-chain-epoched-views)

Bitcoin ABC's public protocol document defines polls containing a round and inventory list, and responses containing round, cooldown and votes, authenticated by a Schnorr signature. Proofs identify stakes and a master key; delegations authorize other signing keys. These messages do not carry authored vertices, per-origin event vectors or threshold close certificates. [Bitcoin ABC wire/proof documentation](https://raw.githubusercontent.com/Bitcoin-ABC/bitcoin-abc/master/doc/avalanche.md)

Independent primary research also finds nontrivial safety/liveness tradeoffs in Snow-family algorithms. This is a reason to analyze the proposed new composition, not a reason to assume an arbitrary theta/R heartbeat rule inherits a theorem from the Avalanche name. [Snow-family analysis](https://arxiv.org/pdf/2401.02811)

## Actual Lotus/eCash source constraints

Inspected immutable lifecycle source `b81455fa120dcbdd86938a6ed62a5a9dbac5a95a`. Generic node-storage/publication has advanced separately; none of those changes supplies the clock described here. Source provenance must remain separate: historical `daemon/v2-version` beginning `09f` is not the current runtime selector; the original failing 500k cohort was `2b61dded451755e175681f41a57281a5c0554e32` / tree `2b4fef46071b44cc8789a49553b3d112b4fd084e`, and the ordered 522 progression uses tree `143e6ae94885cf9e1ebf2772fb918904af7ac846`. The b814 lifecycle audit is an immutable repair-source checkpoint, not a claim that a later unbuilt candidate is a tested daemon.

* `avalanche/protocol.h`: Poll is `(round, invs)` and Response is `(round, cooldown, votes)`. Signed responses attest that sender's response under its authorized key. They do not prove that a weighted global set accepted an epoch boundary.
* `processor.cpp` session setup and `net_processing.cpp` AVAHELLO: sessions are generated/delegated and handshake authentication binds connection nonces/entropy. This provides authenticated communication, not a persistent globally exclusive authored sequence.
* `peermanager.h/.cpp`: one proof can have multiple interchangeable NodeIds/sessions. Counting connections or session keys as independent validator weight would double-count one stake authority.
* `proof.cpp`: proof identity incorporates proof data; its sequence is replacement ordering, not an event counter. Stake UTXOs are live/spendable and are checked against chain state, amounts, heights, maturity and expiration. Proofs can be replaced, conflict, expire or become invalid on tip/reorg changes.
* `PeerManager::selectPeer/selectNode`: selection uses proof-score sampling and available connections. `Processor::isQuorumEstablished` uses locally known total/connected scores and other thresholds, with latching behavior. Those local discovery metrics are not a canonical globally agreed TotalStake roster.
* `VoteRecord` is sampled-response/confidence machinery. It is not a collection of stake signatures proving `theta * agreed_total_stake` on a close object. Neither a confidence increment nor a signed response should be relabeled as such a certificate.

These differences rule out importing AVAX validator counts, BLS aggregation or a two-thirds certificate assumption as implementation facts. Any such new threshold/certificate construction needs its own specified membership, authentication and safety model.

## Assessment of the proposed authored heartbeat DAG

The proposal has useful explicit structure: an authenticated author v, sequence n, self-parent, other parents and signature; incompatible vertices at `(v,n)` conflict; vector coordinate v records the highest accepted authored event in ancestry. That would give the term vector clock concrete meaning. An exclusive epoch-close object can select one cut among several eligible cuts. These are meaningful design components—but they define a new authored consensus DAG.

The following requirements remain substantive, rather than implementation details:

1. **Unique author and restart rule.** Define v by a stake authority anchored in an accepted membership snapshot, not NodeId/session alone. Multiple nodes delegated from one proof must coordinate the single sequence or have a specified equivocation outcome. Restart/key rotation cannot reset n and replay old weight. Sequence persistence, domain separation and a roster/anchor identity must be signed.
2. **Proof replacement and stake overlap.** A new ProofId can refer to overlapping UTXOs or a replaced proof. The epoch roster must prevent counting both as separate weight. Changing delegation/session keys must not create another author. Spending or expiring stake and PoW reorgs need explicit current/next-roster transition rules.
3. **Agreed denominator.** `W >= theta * TotalStake` needs a common roster, exact weights and arithmetic, and a rule for who may enter it. Local discovered proof totals cannot serve as an authoritative denominator. Selecting the next roster at an accepted boundary still requires a deterministic eligibility rule; a proposer cannot choose its preferred voting set.
4. **Accepted ancestry and equivocation closure.** A valid signature is only an authored statement. A vertex is clock-authoritative only after the new acceptance rules hold. Children of losing/equivocating self-parents must not inherit accepted progress. A component-wise maximum over mutually incompatible histories is invalid; validate ancestry/conflict compatibility before merging. Recompute round labels from valid parents instead of trusting a supplied number.
5. **Exclusive close consensus.** Several incomparable eligible cuts can satisfy the progress test. They must compete in one slot tied to the previous accepted close and fixed roster. Independently polling each as a yes/no item can accept more than one unless exclusivity/preference/finalization rules are supplied. This is the same class of issue found in AB/ABC proposal handling.
6. **No circular validator bootstrap.** Validators authorized by boundary S must decide its successor; a proposed next validator set cannot vote itself into authority. Startup, proof discovery, weak-subjectivity/history needs, checkpoint validation and roster changes need explicit rules without assuming a P-Chain.
7. **Bounded availability and storage.** Specify maximum parents, vertex bytes, author rate, unaccepted/orphan/equivocation queues, retained ancestry and catch-up proof format. Cached full vectors cost O(V) per vertex for V authors; sparse representations do not remove worst-case ancestry/merge work. Heartbeats create continuing work even when no transaction needs a new epoch. Garbage collection needs a trusted accepted checkpoint that preserves enough author/ancestry/equivocation state to validate the future.
8. **Offline/fallback behavior.** If the available accepted stake cannot satisfy theta, the proposed progress predicate stops. A local timeout cannot safely lower theta, drop validators or pick a cut unilaterally. Any fallback cut/roster transition must itself have explicit agreed rules and a stated synchrony/adversary model. “Use a timeout” is not a consensus-liveness proof.

This assessment is our inference from the proposal and the actual source architecture, not a claim that any primary source specifies this new Lotus clock.

## The theta-plus-R condition needs a precise claim

Let `W_S(x) = sum_v weight(v) * 1[VC(x)[v] > VC(S)[v]]`. This measures the weight whose authored sequence advanced **at least once** since S. Adding `round(x)-round(S) >= R` does not by itself imply that theta-weight of the same authors each advanced R times.

Counterexample to that stronger interpretation: three equal authors A/B/C, a two-of-three weighted parent condition, and R=2. The participating sets can be `{A,B}` in one round and `{A,C}` in the next. Both rounds have two-thirds participation, yet only A authored in both. The weight that advanced twice is one-third, not two-thirds. An exact round-construction rule may add constraints, but the advertised inequality alone does not establish the stronger property.

There is a second causal gap: `VC(x)[v] > VC(S)[v]` does not prove that v observed S. The additional authored vertex may have been concurrent with S, precomputed or withheld. If the purpose is stake witnessing this boundary, count only an accepted heartbeat that descends from S (or establish an equivalent precise causal theorem).

If the desired property is literally R authored advances by theta-weight, the predicate would need something like `sum_v weight(v) * 1[VC(x)[v]-VC(S)[v] >= R] >= theta*TotalStake`, plus accepted self-chain continuity. Even that does not prove elapsed wall time, transaction dissemination to every validator or R independent observation opportunities: an author can create a burst unless inter-author causal constraints say otherwise. None of these observations selects a theta or changes production thresholds.

## Three alternatives and what they actually buy

| Mechanism | Authoritative fact | New work | Limitation |
|---|---|---|---|
| Accepted parent-BatchId chain | One selected fully validated epoch proposal closes each slot; successor names that exact parent | Correct exclusive slot lifecycle, real proposal discovery, root-bound voting, cut scheduler and recovery already required | Scalar causal order; not a vector clock; no independent heartbeat progress |
| Bounded peer-progress vector | Authenticated peers report where they are on that accepted chain; local finality remains local protocol evidence | Negotiated signed progress fields, proof-authority/connection mapping, bounded map, ancestor checks and catch-up logic | Scheduling/observability, not a global transaction-cut or threshold-finality certificate |
| Authored heartbeat DAG | Accepted causal ancestry of uniquely authorized events, plus separately accepted exclusive cuts | New roster/snapshot, author sequencing, DAG validity/acceptance, cut consensus, wire/storage/catch-up and liveness analysis | Larger consensus attack surface and continuous work; still needs epoch candidate association/reconciliation |

The first option can close a nonempty epoch by finalizing its proposal itself; a separate close token need not duplicate that decision. If independent progress during an empty mempool is required, explicitly specify empty boundary proposals or a heartbeat layer—the current `MempoolBatchAnnouncement::IsValid` requires a nonzero count. No quiet-period clock progress should be invented implicitly.

For a peer-progress vector, a coordinate must carry both sequence and exact branch/BatchId, not just a number. A reported higher sequence on an unknown or incompatible parent chain cannot be merged by numeric max. Reports authenticated to several sessions of one proof are not several stakes. A received claim can trigger verification/catch-up; it cannot advance local finalized state by itself.

## Pending decision and test implications

My recommendation is the accepted parent chain for this repair, optionally with a bounded nonauthoritative progress vector once its value is demonstrated. That is a recommendation, not a selected protocol. If the user wants the new authored clock, treat it as an explicit additional architecture task with the eight contracts above before coding.

Only after selection should normative letter/fixed-ID vectors specify clock updates, epoch cuts and merge behavior. The lifecycle vectors must still include AB|D→ABC|DE, second refinement/re-voting, finalization races, delayed/already-admitted C and exact Merklix fallback under balanced sets/SID collisions. A heartbeat choice also needs equivocation, duplicate-author sessions, roster rotation, incompatible vector merges, competing close cuts and offline-threshold tests. Toy weights/thresholds must be labeled fixture parameters, never production eCash/Avalanche constants. An observation-only vector is not an acceptable substitute for the requested actual protocol.


## Additional alternative: publisher microbatch chains and skip-selected cuts

Reviewed the complete supplied `leaderless_epochs.md`, rather than treating it as the earlier heartbeat proposal. It is an alternative, not the selected protocol. It defines signed per-publisher microbatch chains, epoch-advance vectors, Avalanche-finalized exits/skips and deterministic union cuts. Unlike the heartbeat DAG, its vectors occur at publisher epoch transitions; publisher data forms self-chains. These are distinct alternatives.

The useful idea is to separate dissemination of immutable named content from agreement on a cut. Narwhal makes a related separation between reliable dissemination/storage and transaction ordering; the analogy does not establish safety for this new sampled-voting composition or replace its availability rules. [Narwhal and Tusk](https://arxiv.org/abs/2105.11827)

### Concrete gaps and counterexamples

1. **Finality dependency changes the objective.** The proposed batches admit only transactions already finalized by pre-consensus, and a receiver votes yes only after its own transaction finality. If epoch batches are meant to supply that transaction finality, this is circular: C must finalize before inclusion in the item that finalizes C. The current Processor does support separate `CTransactionRef` vote items and admission-triggered transaction polling, so circularity is not unconditional. It is coherent as an indexing/packaging layer over that retained individual-transaction finality mechanism, but the finality state/availability interface must be specified and this changes the intended batch-finality benefit. If “finalized” means merely validated, say so and explicitly resolve conflicting transactions/dependencies inside the new batch protocol; validation is not finality.
2. **Honest skips can differ.** Publisher p has finalized sequence 4 at both H1/H2. p publishes 5 and then goes offline. H1 has locally finalized 5; H2 has not yet learned/finalized it. Both local skip timers expire. The stated rules produce `Skip(p,e,5)` at H1 and `Skip(p,e,4)` at H2, with no malicious author and no conflicting finalized publisher batches. An offline publisher's immutable chain does not imply identical knowledge of its tip. The rule “honest skips never differ” is therefore false. Timers may trigger proposals; they cannot establish an agreed terminal sequence.
3. **Exit exclusivity needs a complete state machine.** All skip alternatives and next-epoch advance alternatives must select exactly one exit for `(roster,p,e)` under explicit preference and finalization rules. For example, `Skip(p,e,c)` and a next-epoch batch whose self-parent is c may encode the same cut, but the proposal does not specify whether they are compatible representations or conflicting vote items. A skip at c must also exclude any later cut c+1 and prohibit subsequent descendants from reopening the closed interval. It is insufficient to list only the conflict with later epoch-e batches. Local timeout-based rejection of otherwise valid content must not masquerade as permanent objective invalidity.
4. **Private knowledge is not a validity predicate.** A publisher cannot prove it has never seen a quorum. If vectors are present only on advances, a same-epoch batch exposes no such vector. Requiring advancement when the carried ancestry itself proves a quorum can be deterministic; requiring it whenever the author “has seen” enough is not remotely checkable. First-seen choice is likewise a local initial preference, not global objective validity, and needs eventual preference switching rather than a permanent rejection of every alternative.
5. **No-progress publishers still affect the stake clock.** If less than theta of the fixed roster can supply the required finalized epoch-e batches, progress vectors cannot authorize e+1 under the written rule. Skips can pin intervals but do not count as those authored epoch-e batches. Conversely, allowing every publisher to exit by skip closes an epoch under the stated closure rule without any theta-weight advance; specify whether this is intended and how the subsequent tag/roster state proceeds. The text's claim that skips prevent a minority from stalling needs an explicit online-honest-weight assumption, or a new rule for how skipped publishers/roster changes affect the next epoch. No bound `max(quorum_time,T_skip)+finality_latency` follows without network, discovery, preference convergence and service assumptions.
6. **The cut coordinate has an off-by-one ambiguity.** If the first e+1 batch has sequence k, the inclusive epoch-e upper bound must be its epoch-e self-parent sequence k-1, not k. The advance batch belongs to the next interval. Skips at c set that bound to c. Specify empty publications, skipped epochs, publisher entry/exit coordinate initialization and continuous sequence domains explicitly. In particular, an author offline through a skipped epoch cannot both obey no-skipped-tags and avoid extending the already closed interval without a defined empty-transition/resume rule.
7. **Version numbers are not batch identities.** A vector of highest contiguous finalized sequence identifies missing numeric ranges only when a single authenticated publisher branch is already established. It does not reveal the exact batch hashes without additional headers/hash-chain traversal. Coordinates need roster/author identity and verified exact tip hash; equivocation or replacement cannot be merged by numeric maximum. Four bytes per publisher omits identity, root/hash authentication, framing and sequence lifetime/overflow rules.
8. **Short IDs do not commit exact contents.** A publication needs exact TxId/TxHash commitment plus collision-complete retrieval and availability verification. The supplied `short_ids / delta_root` alternatives cannot be interchangeable authorities. The existing exact Merklix zoom can serve this purpose; replacing it with a live minisketch layer is an additional unselected algorithm change. “Newer than last closed epoch” does not make the live set bounded when closure or inclusion stalls. It must also not exclude old still-unfinalized transactions and recreate the original age-stranding bug; every eligible transaction needs eventual coverage regardless of arrival age.
9. **Roster agreement is foundational.** The proposal acknowledges gossiped proofs are not an agreed on-chain set. Minimum stake alone does not select an agreed roster. Snapshot height alone lacks an exact block identity; skips also lack a publisher-signed finalized-tip observation. Define the weighted-median inputs when exits are skips, deterministic proof eligibility, overlap/replacement, delegation/restarts and reorg consequences. Two-epoch lag gives time but does not prove discovery completeness or agreement. Removing an equivocator needs agreed evidence/admission rules, not each node's local evidence set.
10. **Continuous epochs do not eliminate PoW reorg handling.** An epoch lineage can avoid resetting its counter, but transaction validity, proof stakes, parent UTXO roots and block inclusion still depend on the exact PoW ancestry. Define invalidation/reanchor behavior. Garbage collection conditional on every transaction reaching an Avalanche-finalized block may retain history indefinitely when inclusion stalls; bounded storage requires an explicit retention/checkpoint/service policy. Committing the union as a block prefix also needs ordinary transaction dependency/conflict/block-validity checks.
11. **Agreement proof is conditional.** A union bound does not require independence, but it does require justified per-item failure bounds under this actual adaptive scheduling/conflict composition and a bounded item count (or specified failure budget). Per-item finality alone does not show exits are exclusive, ancestry is available, cuts are complete or membership snapshots agree. Liveness is a separate claim. No empirical double-finality trace or protocol theorem has been established by this review.

12. **Set union must preserve executable, exact identities.** Two publishers may name the same TxId with different TxHash/body witnesses; deduplicating TxId alone does not select the same committed leaf. Specify body identity and conflict resolution. Separately, individually finalized parent X and child Y can be published into different intervals with Y in e and X only in e+1. Finalized-only membership therefore does not prove that epoch e is dependency-closed or executable against the prior cut. State whether cuts may contain such descendants, how missing ancestors are assigned and how that interacts with exact epoch membership.
13. **Cached roots cannot be combined by an unspecified union.** `ComputeV2TxRootFromSubtreeA` combines one prepared noncoinbase subtree root with the coinbase commitment. It does not merge arbitrary overlapping publisher/epoch roots into a deduplicated transaction union. The implementation still needs canonical trie union/path updates, exact duplicate/witness handling, dependency checks and confirmed-transaction exclusions where applicable. Cross-epoch subtraction of `content(<e)` also requires retained exact membership/checkpoint data after old publication bodies are collected; otherwise an old transaction can reappear in a later cut.

These points do not show that publisher chains cannot be designed. They show that the supplied sketch has unresolved consensus and lifecycle contracts and that its stated absence of honest conflicts is too strong.

### Decision that matters before fixtures

Under a finalized publisher-cut definition, AB can mean an incomplete local materialization of an already fixed ABC cut, rather than a legitimate competing epoch proposal. That node must reconstruct the fixed cut before it is ready. Before cut selection, an open union/proposed cut can still change. Consequently the earlier AB→ABC proposal/re-voting state machine cannot simply be copied to this alternative without naming which of these states AB represents. This is a semantic choice, not an immutable-storage detail.

The concrete first choice is whether epochs **perform transaction pre-consensus** or **package transactions already finalized by another mechanism**. For the first goal, retain the revised AB→ABC candidate/re-voting requirement and compare the minimally corrected exclusive-slot parent chain against an explicitly designed publisher/cut consensus alternative. For the second goal, publisher chains are a plausible separate packaging design, but budget and specify the retained transaction-finality mechanism. No choice is made here.

If independent weighted causal witnessing is itself required, compare the heartbeat DAG with a simpler linear chain of boundary-bound round certificates before accepting concurrent DAG ancestry as necessary. That simpler alternative still needs the same new agreed roster, weights and authentication rules; it is not available merely by renaming existing sampled Avalanche confidence.

The current implementation defects should be repaired against the selected lifecycle, and the narrow initial-relay request-ownership repair remains independent. Existing source lacks exclusive same-slot finalization and proper readiness checks; that is a source-grounded risk, not proof that production double-finality has occurred. The duplicate AVABATCH handling and cadence effects of conflict state must also be described accurately: conflict bookkeeping is not merely a metric, but neither does it enforce exclusive final acceptance.


## Independent review disposition

Two independent source-grounded reviews of the actual publisher alternative were performed: an overlay review (source 91dbda5308) and an alternative-protocol review (source b81455fa12). Their concrete findings have been incorporated above. Both assess options only; neither selects or approves a clock protocol, transfers the earlier lifecycle review to a different epoch definition, or authorizes implementation. Normative clock/cut vectors remain pending the actual protocol choice.


---

## Section 9 update

# Section 9 variant: publisher-root voting without per-transaction finality


## What changed, and what can work

Publisher batches now commit immutable data sets, reconstructed with canonical Merklix roots and BCH hints. Their acceptance attests data availability and a specified validation predicate; it does not yet mean every contained transaction wins execution. A closed, agreed cut determines the data union. A separate deterministic execution rule then determines the executed root. These three commitments/states must be named separately.

This removes individual-transaction voting from the intended fast path. It can in principle amortize voting over batches. It also moves irrevocable transaction outcome to the point where the cut, all relevant conflict data, and execution rules are fixed. Neither `2*I + T_fin` nor approximately three seconds is established for this implementation by the supplied sketch.

A whole-epoch root is not intrinsically unvoteable. Once an exact cut is fixed, all complete replicas can derive the same root; it can be verified or voted on if useful. The original pathology is independently changing or incomplete cuts being treated as equivalent vote targets. Author-named immutable batches are one way to fix the input sets, not a theorem that a whole-epoch commitment can never work.

## Required contracts and concrete tests

### A. Availability is not execution validity (§9.3)

“Well formed and inputs exist somewhere” is insufficient to exclude invalid signatures, invalid script/VM execution, value creation, immature coinbase spends, locktime/sequence/expiry violations or incorrect contextual rules. Allowing two individually authorized spends of the same outpoint in a data set does not permit either spend to lack authorization. Specify exactly which checks run before a positive availability vote, the chain/roster anchor, and which checks necessarily wait for the selected execution state.

The stated input source `content(<e) union chain_p union chain/UTXO` omits a parent first published by another publisher in the same epoch. Conversely, a raw input's existence in historical data does not show it survives earlier conflict resolution or remains unspent. Define authenticated dependency lookup/closure and unknown behavior. A parent manifest/body must identify the exact outpoint, value and script used for validation, not merely establish that some transaction with a matching short ID exists.

Keep conflicting but authorized data separate from the current accepted mempool execution view. A body can be retained in an immutable publication without being simultaneously admitted into the ordinary mempool alongside its double spend. The existing single admitted pool is not automatically a store for every competing transaction published in this new protocol. Specify bounded quarantine/body ownership, validation caches and promotion/removal rules; do not bypass ordinary admission to force both conflicts into M.

### B. Per-input winners need a complete whole-transaction rule (§9.4)

Consider X spending inputs a and b with support 6, Y spending a with support 7, and Z spending b with support 5, all in one epoch. Per-input winners are Y for a and X for b. X cannot execute after losing a. Does Z then win b, or remain a loser? Both a one-pass `Y only` rule and a globally specified reconsideration rule can be deterministic, but the present text does not select one. “Drop descendants” does not resolve this choice because Z is a conflicting alternative, not X's descendant.

Specify a total selection/execution algorithm for overlapping input-conflict graphs, dependency ordering and failures, including whether discarded alternatives are reconsidered. A global greedy ordering is a possible design to evaluate, not an adopted rule here. All nodes must agree on the exact support/ranking input set and on execution context before deriving the root. Mark parent losers and propagate that outcome transitively to descendants without dropping unrelated valid siblings. Include child-before-parent, diamond dependencies, multi-input overlap and unavailable ancestor vectors.

Earlier epochs can have immutable **executed winners**. Earlier appearance in a raw data root must not resurrect a transaction that lost that epoch or cause the same spent input to be reconsidered in later epochs. Define whether a previously discarded transaction may be republished, how it is treated, and what historical state is retained after garbage collection. Freeze the prior executed UTXO state before resolving the next epoch.

### C. Publisher support is a new exact rule (§9.4)

Count each eligible unique stake authority at most once per exact supported transaction, regardless of repeat publication or multiple delegated sessions. Bind the roster and weights to the agreed epoch domain, and define replacement/overlapping-proof treatment. Existing score-weighted peer sampling does not supply this support tally automatically.

A publisher may include spend T at sequence 1 and conflicting spend U at sequence 2 without signing two different objects at the same `(p,seq)`. Under §9.3 both can be authorized data. This is not the already defined sequence-equivocation offense. Decide whether that publisher supports both, neither, the first, or an explicitly chosen alternative in the conflict group. Honest first-seen relay behavior is not a remotely verifiable validity rule and does not prove network-wide first arrival. Any punishment or exclusion rule would be an additional explicit protocol rule.

### D. Canonical identity and tie breaking (§9.1, §9.4)

Actual `commitment.cpp::TxLeaf` commits `TxId` **and** `TxHash`; canonical trie keys use TxId. Idempotence holds when the same exact identity is inserted again. Two different bodies/TxHashes with one TxId need a deterministic validated choice or rejection rule. “Same txid twice changes nothing” is not sufficient to determine the canonical root for those alternatives. Support, duplicate removal, dependency references and ranking must agree on the chosen identity model.

Define `root(C_e)` precisely: an authenticated cut-vector commitment, the raw data root, or the executed root are different values. Using the executed root to select the transactions that determine it is circular unless a separate fixed-point protocol is defined. Using the cut/data root avoids that particular circularity but does not establish ungrindability. A publisher can vary candidate data, ordering/packaging, withheld publications or competing exits before the cut is fixed; a malicious sender may also generate candidate transaction identities. The mere fact that the final cut is initially unknown does not prove unbiased or unpredictable entropy at the last influencing party. Treat this hash as a deterministic tie-break with a bias analysis, or specify a separately justified randomness mechanism. Do not claim grinding resistance from secrecy alone.

### E. Latest-head voting must define inherited decisions (§9.1)

The retained §2 rule requires `self_parent` already finalized before the child can receive yes. Under that rule polling only the latest unfinalized head cannot replace every intermediate finalization. If §9 intends head finality to imply ancestors, explicitly replace that precondition with verified immutable ancestry, complete required availability/validation, compatible epoch/exit/roster history and a rule for atomically committing ancestor decisions. It must not endorse an unavailable or conflicting ancestor merely because a later hash names it.

Ancestor inheritance also requires preference/exclusivity across publisher equivocations and skip exits, including delayed ancestor votes and finalized-history immutability. Existing block handling is an analogy, not an implementation of those semantics for new publisher items. Bound unfinalized chain length and reconstruction work before polling a head; unknown responses must not poison a valid branch while its data is incomplete.

### F. BCH reconstructs exact sets but does not guarantee a small difference (§9.2)

The commitment-first design and collision/overflow fallback are sound requirements: pin the exact publisher delta root and local comparison view, use BCH only as a hint, and reconstruct exact identities before yes. Do not interpret a local short-ID match as proof of the requested TxId/TxHash. Exact prefix traversal must cover all 256 TxId bits and return complete bounded pages; no fixed cap may truncate the represented set. Use the same canonical bit orientation in roots, prefix routing and terminal reconstruction.

The proposed comparison `L_p = my_pool minus (history union chain_p,e)` approximates a publisher's next delta only if that publisher includes nearly all of the same eligible residual set. If the local residual pool contains 100,000 transactions and the publisher intentionally batches 1,000, the symmetric difference can be 99,000 even with complete body dissemination. Optional home-publisher sharding or a different batch cutoff can likewise dominate the difference. Small differences need an explicit common selection predicate or measurements; otherwise correct exact zoom must tolerate O(N) difference work. Avoid rebuilding whole-pool vectors on every peer poll.

The stated XOR identity additionally requires `chain_p,e` be a subset of `my_pool minus history`, not merely a subset of my_pool. If a publisher repeats a transaction already in history, blindly XORing its contribution reintroduces that identity. Either forbid such repeated publication objectively, or subtract the exact intersection with the base set. Bodies removed/mined since a pinned publication also violate the simple live-pool subset assumption and must remain recoverable by immutable ownership.

### G. Early conflict-only voting is not automatically early finality (§9.4)

A transaction that appears conflict-free locally may have an authorized conflict withheld in another publisher's still-open interval. If the cut's eventual stake/tie rule can choose that conflict, the earlier outcome was tentative, not irrevocable. Conflict-only polls do not solve hidden-conflict knowledge.

Resolution markers need a unique conflict domain, exact participants/outpoints, selected identity, compatible predecessor state and committed decision evidence. Define precedence between markers and ordinary cut ranking, conflicting markers, marker dependencies, ordering/epoch assignment, and application to multi-input conflicts. Local confidence or a publisher assertion is not automatically a portable proof of a globally finalized marker. Earlier executed finality cannot be reversed by a marker that arrives later.

For the present batch-finality objective, target low close latency and measure it. Treat any pre-close “accepted” status as explicitly tentative unless the chosen protocol provides a separate irrevocable decision that all later cuts must honor. Add a hybrid only for a demonstrated latency need and after defining how that separate decision constrains cuts; no three-second promise follows from the optional paragraph.

### H. Cost and latency must use the actual sampler (§9.6)

Source `VoteRecord::registerVote` maintains an eight-vote window, requires more than six agreeing considered votes, filters recent duplicate peer identities, increments confidence on agreeing results and resets it on a preference switch. `AVALANCHE_FINALIZATION_SCORE=128` is not 128 fixed independent network polls, and is not a stake-threshold signature certificate. Unknown votes, peer reuse filters, loss, batching and preference changes affect observations and cost.

The protocol serializes a 36-byte inventory entry and a 36-byte vote entry, plus round/vector/cooldown fields and a 64-byte Schnorr response signature. Thus 72 bytes describes only the marginal pair of item entries in amortized multi-item frames, not a complete one-item request/response. Network framing, requests to other peers, retransmission, proofs, announcements, body recovery and Merklix work also matter. Do not multiply 130 by 72 and present it as measured per-item cost.

Instrument finalization latency distributions, useful votes/confidence increments, request/response element counts and serialized bytes, peer uniqueness, neutral/rejected replies, ancestry fetches, body bytes, CPU and memory. Compare per-transaction baseline and batch variant at the same membership/network workload only after the protocol is specified. Batch voting reduces item count in principle; root construction, support tallying, validation and dissemination remain transaction-dependent, and cost also depends on publisher count/replication.

The `2*I+T_fin` sketch excludes offline exits, skip conflicts, ancestry reconstruction and the newly required conflict execution. Retained §2 finalized-parent sequencing also changes attainable publication cadence. A committee could reduce publisher load but introduces another unselected roster/selection protocol.

## Remaining clock issues and disposition

The new variant does not resolve the earlier exact skip-cut disagreement, skip/threshold deadlock or bypass, unverifiable mandatory knowledge advancement, agreed roster/weights, session/sequence durability, PoW anchor/reorg or retention/catch-up contracts. Preserve those findings while dropping the obsolete finalized-only critique for §9.

Recommended direction for the stated bulk-finality objective: evaluate batch finality with a low-latency target, and define one exact cut/execution protocol before a hybrid. This is an engineering recommendation, not approval of the proposed clock, conflict rule, committee, salt or consensus changes. The original parent-chain/exclusive-slot alternative remains available for comparison; publisher-root voting is a different candidate requiring these contracts.

Required new small vectors include the X/Y/Z overlap above, cross-publisher dependencies, same-TxId/different-TxHash publications, a publisher supporting both conflicts at different sequences, hidden conflict arriving before close, conflicting resolution markers, head-finality/ancestor recovery and a large symmetric difference despite full body availability. Existing AB|D→ABC|DE vectors must be restated in terms of the chosen cut semantics. No normative expected protocol outcomes or production implementation should be invented before that choice.


---

## Current committed-contribution review

# Committed contributions: current §§9.4/10 review and proposed behavior vectors


## Scope and recommendation

The user's intended boundary is now explicit: freeze each publisher's contribution C_p(e) as the unconfirmed-ancestor closure of its cutoff direct admissions; later direct admissions go to its next contribution, while epoch reconstruction accepts only verified members of selected, immutable C_j(e). Required ancestors may have been received from another contribution: this is an explicit dependency-closure supplement to the direct-admission rule, not a new direct-admission event. The union is complete when every included contribution is reconstructed, not when all live mempools happen to match. A shared canonical owned tree remains reusable storage for these sets. A vector records a causal frontier; it neither certifies arbitrary transaction origin nor replaces agreement on the roster and included contributions.

The revised stake-first atomic execution direction is coherent enough to specify and compare. It resolves the old pairwise tournament and independent-per-input selection objections. Its first-seen economic/security properties remain hypotheses to test; a deterministic outcome is not proof of resistance to double spending. Prefer the bulk-finality target with measured low closure latency before adding a hybrid. This is a recommendation for study, not approval of the clock, conflict policy or deployment. All four requested areas below are written as a **proposed behavior contract** with explicit open decisions. Normative within-proposal examples are separated from alternatives and blocked cases. No actual clock or production oracle is invented.

## 1. Exact scheduler and support definition

For the proposed generation-based contract, fix the complete selected epoch contribution union, exact prior executed-state identity, epoch roster/weights, consensus validation context and normalized TxId/TxHash identities first. Do not recompute scores from later arrivals. A publisher's support is computed from its whole selected C_p(e), the set union of all its microbatches in that epoch, and its unique weight is counted at most once. Splitting rivals across microbatches or repeating the same transaction must not increase support. Multiple delegated sessions do not create new weight.

**Proposed rival definition:** direct shared-outpoint neighbors, not transitive connected components. For a transaction t, R(t) contains the other eligible normalized transactions in this fixed epoch union that consume at least one of t's input outpoints. A publisher supports t iff t is in C_p(e) and C_p(e) contains no member of R(t). Sum that publisher's epoch weight once. This is a proposed precise reading of the supplied score, not an already implemented rule. The eligible-universe decision remains material: invalid signatures/malformed records must not silently become rival votes; transactions failing ancestor/state eligibility need a specified phase before scores become normative. A remote rival alone does not zero an honest publisher's support: the disqualifying rival must also be inside that publisher's own fixed contribution. Once present there, it can zero support under the stated rule even if its body is later found ineligible unless the normalization rule excludes it.

The proposed scheduler is **fixed topological generations**, not a priority Kahn heap. For a fully resolved acyclic in-epoch dependency graph, g(t)=0 when t has no in-epoch parents; otherwise g(t)=1+max g(parent). Build generations from the fixed eligible identity graph, not from local arrival order or a graph after opportunistically deleting losers. Missing required ancestors cannot receive an invented depth0: a fully reconstructed contribution omitting them is invalid before execution. Incomplete reconstruction is unknown, not a negative validity conclusion. Every generation finishes before the next starts. Within it order by decreasing fixed support, then increasing specified hash tie key, then full canonical identity as a collision-safe final total-order key. This final key handles a hash collision without relying on unspecified container order.

Before each transaction executes, every in-epoch parent must already be accepted. Check remaining consensus/script/VM rules against the current deterministic execution state. Accept atomically only when all inputs are unspent and all required checks succeed; then update state. A failed transaction changes no state. Descendants of a failed/rejected parent cannot become ready. State/VM rules, height/MTP/expiry context, fee and resource admissibility remain consensus choices to be finalized; ordinary node-local fee policy must not determine divergent executed roots. Earlier executed decisions are immutable. A proposed generation ordering can intentionally favor a generation0 competitor over a higher-support child; this is observable protocol behavior, not an implementation optimization.

### Hand-worked scheduler vector G

All signatures/inputs are valid; base outpoints are w and u. Publisher a has weight2 and contributes {P,C}; publisher b has weight1 and contributes {P,X}. P spends w and creates P:0. C spends P:0 and u. X spends u. Direct rivals are C/X, so support(P)=3, support(C)=2, support(X)=1; no hash tie is involved.

| Step | Fixed generation scheduler, proposed contract | Priority Kahn heap, alternative only |
|---|---|---|
| Initial ready | Generation0={P,X}; generation1={C} | Heap={P,X} |
| Accept P | P accepted; remain in generation0 | P accepted; C enters heap |
| Next | X accepted and spends u | C outranks X, accepted and spends u |
| Finish | C rejected; executed set {P,X} | X rejected; executed set {P,C} |

This replaces raw numeric TxIds as a purported score example: H(seed||TxId) is not numerical TxId order. The fixture uses actual unequal support ranks and thus does not assume a hash ordering.

### Hand-worked multi-input and rival vectors

M: A spends {u,v}, B spends {u}, C spends {v}; publishers respectively contribute {A} at weight4, {B} at weight5 and {C} at weight3. All are generation0. Order B,A,C: B accepts, A atomically rejects because u is spent, C accepts v. Result {B,C}. No partial spend by A and no per-input dangling winner.

R: T spends u, R spends {u,v}, S spends v. Publisher p(weight3) contributes {T,S}; q(weight2) contributes {R}. With direct rivals, support(T)=support(S)=3 and support(R)=2, yielding {T,S}. If “conflict set” instead means the entire connected component, p's two nonconflicting transactions would exclude each other's support, yielding R. The proposed contract selects direct rivals; component exclusion is an alternative with different output, not an interchangeable optimization.

Z: publisher p(weight7) contributes both A and B, which spend the same u; q(weight3) contributes A; r(weight2) contributes B. p contributes zero support to both. A has3, B has2: A wins. The result is unchanged if p puts A/B in separate microbatches. If p is the only publisher, both scores are0 and the declared hash tie key decides; this is explicitly grindable, not stake protection. Tie-only grinding can still matter operationally if zero/tied support is common.

## 2. Cross-epoch behavior vectors and remaining choices

The proposed identity model first detects already executed exact identities before checking their already-spent inputs. An exact duplicate is a no-op, not a new double spend, fee, leaf or UTXO transition. Previous executed membership must remain queryable after publication garbage collection. A later different TxHash for the same TxId is not the same exact duplicate. Preserve the previously executed identity; it cannot rewrite the earlier leaf. Whether the new witness is a rejected data record, an ignorable equivalent witness after validation, or invalidates its containing contribution is an explicit still-open availability rule. No fixture silently chooses among these distinct consequences.

| Case | Proposed execution behavior | Unresolved boundary |
|---|---|---|
| A exact TxId+TxHash executed in e, repeated in e+1 | Exact duplicate no-op; no second charge/spend/leaf | Availability treatment of redundant data should be explicit |
| A same TxId, different TxHash in e+1 | Never rewrite executed A | Contribution validity/normalization remains open; expected status is pending in JSON |
| Complete C_p(e) contains child C but omits unconfirmed parent P | INVALID contribution at vote time, even if another publisher has P or may publish it later | Cannot enter selected valid epoch content; partial reconstruction stays UNKNOWN |
| P loses in e because its input was consumed by executed Q; child C arrives in e+1 | C cannot spend nonexistent P output; reject from execution | Merely seeing historical raw P is not an input-state proof |
| New later contribution includes P and C with complete ancestry | Revalidate this new commitment against its fixed context | Does not repair or rewrite the earlier invalid contribution |
| A/B/C overlapping-input vector M | B,C execute as above; A and descendants do not | Resource/VM failure ordering must use chosen consensus context |

A fixed raw contribution remains immutable even when some members lose execution; a complete non-closed contribution is invalid and never reaches execution. Its data root and the executed root are separate. No API may mark every transaction in an available/finalized data batch as an executed winner. A transaction's finality status must name the executed epoch/state, not merely a publisher root containing it. Bodies for valid conflicting data need bounded named-publication ownership separate from the ordinary accepted mempool.

### Ancestor-closure vote contract and q/p/r vector

Use one fixed agreed chain/state anchor for the epoch, never each validator's moving local tip. Under the user's stated rule, repeat every ancestor not confirmed on that anchor inside the same contribution, even if its body came from q or an earlier publication. A positive vote checks its own contribution's complete authenticated dependency graph, not whether the union might acquire the parent elsewhere. Confirmed-on-chain must identify exact anchor outpoints and scripts; it is not proof that any historical output is currently spendable. The prior executed state also matters when conflicts from earlier epochs have already consumed an input.

Negative H1: q directly admits P and commits {P}; p received P through reconciliation, directly admits C spending P:0, but commits only {C}. q is skipped. Once p's exact root has been fully reconstructed, p's contribution is INVALID for missing its unconfirmed ancestor, regardless of q's status. If only C's body has arrived and the advertised root might also contain P, the response is UNKNOWN pending reconstruction; do not infer non-closure from missing local bytes. r publishing P in e+1 cannot retroactively validate p's epoch-e commitment.

Positive H2: p commits ancestor-closed {P,C}. q may be skipped and r may publish P later; p's contribution remains independently dependency-valid. If no other execution conflict exists, e executes {P,C}; an exact repeated P in e+1 is a no-op. q's exclusion can still change stake support and thus conflict ranking in a different vector; closure independence is not score independence.

If P was already executed in an earlier epoch but is still unconfirmed on the agreed chain anchor, the literal latest rule requires repeating P. Normalize its exact identity as an already-executed no-op before spent-input checks, then validate C against the agreed prior executed state and process it once. Omitting P in favor of an authenticated reference to prior executed state could be a later optimization, but is **not** silently substituted for the user's repeat-all-unconfirmed-ancestors rule. Its witness/availability commitment would need a separate explicit decision. An earlier losing parent's raw body cannot create an output in that state.

Malformed cycles, incorrect outpoint indices, false parent identities, invalid scripts/value rules and excessive resource graphs must fail their specified checks. The complete validation predicate remains to be finished; ancestor closure alone is not script/VM authorization. A later complete contribution can include C with P and be considered under its own anchor; it does not revive the old invalid object.

Closure is not free merely because Merklix deduplicates. With visited identities and shared traversal, discovering a closure can be O(n+m) in distinct reachable transactions and dependency edges; repeatedly walking all ancestors of every child can become quadratic on a chain. Hash/path updates, exact identity comparison, scripts/VM work and retained body/root exposure remain real. Reuse existing bodies and immutable subtrees where available, but reserve bounded memory and work for adversarial long/wide ancestry. Measure chain/diamond/wide fan-in cases, shared ancestors across many publishers and cold caches; count distinct traversals, edges, hash work, bytes retained and wall time. A fixed target only gives monotonic reconstruction if the owned reconstruction state retains validated progress; live mempool mutation or eviction otherwise invalidates the simple “differences only shrink” claim.

These rules preserve the cutoff: direct admissions after freeze cannot enter C_p(e), while required ancestors are included before its commitment is fixed. Same-epoch alternate witnesses and eligibility of invalid/ancestor-ineligible rivals remain blocked fixture cases until exact normalization is chosen. No architecture selection follows from this behavioral draft.

## 3. Numerical security and latency experiment plan — no results claimed

Define merchant-observed honest spend h and a conflicting attacker spend a. Measure P(a becomes the executed winner in the same epoch | merchant has received/validated h, specified propagation head start, attacker stake and cut policy). Separately measure probability that any two honest nodes derive different executed roots, inclusion delay, merchant exposure time, and availability/closure failure. A late attacker win after only tentative acknowledgement is different from reversal of already committed executed finality; report both explicitly.

The baseline is **primary hash priority**, not the proposed stake-first rule. Under an ideal independent uniform hash model, after seeing an honest hash quantile q, K independently grindable attacker candidates win with probability 1-(1-q)^K. Averaged over an independent uniform honest hash, this is K/(K+1). Thus enough candidates approach win probability1. This is an analytical baseline under stated assumptions, not measured Lotus security. Apply the same calculation only to tied support in the stake-first variant; report the empirical tie/zero-support frequency separately. Stake-first inclusion cannot be ground by changing only a TxId while holding every contribution fixed, but propagation, publisher selection, withholding, double inclusion and cut timing can change its score. No “attacker cannot influence stake support” guarantee is asserted.

Planned grid (values are experimental inputs, not selected production parameters):

| Axis | Initial cells |
|---|---|
| Attacker share of agreed roster weight | 0, .05, .10, .20, .30, .40; separate concentrated vs split proof layouts with equal total stake |
| Honest-spend head start before attacker release | 0, 25, 100, 500, 1000ms; normalize by epoch cadence too |
| Contribution cadence / cutoff offset | .25, 1, 2, 5s; tx arrival at 0%, 50%, 95%, 99% of local interval |
| Delivery model | measured baseline traces; asymmetric delays; loss/retry; partition then recovery; selective body/contribution withholding |
| Topology / dissemination | production peer selection with explicit degree, preferred connections, body relay policy and non-staker routing |
| Grind budget | K=1,16,256,65536; primary-hash baseline and tie-only attacker |
| Publisher behavior | first-seen honest inclusion; malicious alternate sends; same-proof repeat/microbatch split; include both rivals; late support-changing contribution |
| Roster / cut / skip | fixed explicit roster; varying honest included weight; contribution/skip boundary races; committee variants only as separately specified models |
| Conflict graph | one input, multi-input overlaps, dependency chains/diamonds, zero support, exact TxId/TxHash collisions |

Declare stake identity/deduplication, contribution admission/eligibility, root/cut finality, availability retention, adversarial scheduling capability, honest relay and first-seen behavior, synchrony/fair-service assumptions and seeds for every run. In particular, a cut that includes little honest weight can have different conflict outcomes even at unchanged total attacker stake. Local per-contribution caps do not bound aggregate work across many publishers: add agreed global bounds or bounded execution/reconstruction accounting, and test coordinated stake identities subject to exact eligibility. Compact double-spend proof relay can improve merchant visibility; it is not a substitute for finality or a free anti-spam fee.

After algorithm selection, the model and production actors must call the **same conflict-normalization/support/scheduler implementation** with a production-state adapter. First run exact small vectors, then actual three-pool/Processor and three-daemon signed-transaction paths. Use controlled network schedules, actual sampler and measured counters; no independent Python model receives a production PASS label. Exploratory models must be labeled as models and report their deviation from production. No new consensus source code is authorized now.

For each probabilistic cell report trial count, successes/failures, confidence interval, censorship/incomplete-run handling and latency percentiles, with preregistered stopping criteria. Zero successes are not zero risk; e.g. the rough 95% upper bound 3/n for zero observed events assumes independent repeated trials and must not be applied to adversarially correlated schedules. Random simulation samples do not prove a worst-case bound. Escalate counterexample schedules to deterministic regressions.

Instrument VoteRecord's actual considered responses, recent-peer filter, confidence increments/resets, request item counts, wire bytes, proof/ancestry fetching, Merklix work, retained roots/bodies and validation time. Source ideal all-yes startup reaches score128 after134 eligible observations for initially accepted=true (135 if initially false), not a universal130 polls. A poll plus signed response for m items has payload72m+20+2*CompactSizeLen(m)+64 bytes (158 at m=1), before transport; 72 is marginal element cost only. Real neutral votes, batching, peers, loss and preference changes determine total cost. Do not use the rough10KB or ~3s/2I latency as measured acceptance criteria.

## 4. ACS-shaped composition: useful target, missing proof obligations

The current §10.1 correctly retracts automatic HoneyBadger inheritance. HoneyBadger's primary publication describes an asynchronous construction; its model and components are not supplied by Lotus's signed sampled responses. [Primary publication](https://eprint.iacr.org/2016/199). The paper landing page was accessible; direct PDF fetch was blocked during this review, so this note does not claim a fresh line-by-line proof audit. The [author's pinned ACS implementation](https://github.com/amiller/HoneyBadgerBFT/blob/78b66448a00c2ab0645d7a70a62f687e62ae27f4/core/bkr_acs.py) was retrieved and read. It explicitly coordinates a fixed set of binary instances, delivery-triggered positive inputs, initiation of remaining zero inputs, waiting for all outputs and a minimum-inclusion check. This historical code establishes that composition machinery is explicit; it is not an audited threshold theorem or a substitute for the paper.

For this proposal the concrete agreement output is a common vector selecting INCLUDE(exact contribution hash) or SKIP for every eligible publisher/epoch, with explicit conflicting author values. Reconstructing a committed root proves that node's content possession, not that all honest nodes can eventually recover it. A vector of observed/finalized contributions can justify a cutoff only under the selected acceptance and ancestry rules; it cannot enforce that a publisher froze at its first private observation of the threshold.

Required composition contracts:

1. **Common roster.** Commit exact eligible authority identities, weights, overlap/replacement policy and transition anchor from prior accepted state. Gossiped ABC proofs and finalized block height alone do not define that roster. Old membership must authorize transition; no circular bootstrap or unseen proof completeness assumption.
2. **Availability/reliable delivery.** Show that an included value remains recoverable for lagging honest nodes despite Byzantine withholding, honest pruning/restarts and sampled holder concentration. Either provide a probabilistic argument tied to actual stake sampling and retention/service assumptions, or design a separate certificate/dispersal mechanism. A sampled yes is not an all-honest reliable-broadcast guarantee or an explicit two-thirds certificate.
3. **Exclusive include/skip decisions.** One conflict domain `(epoch, publisher, roster)` must exclude incompatible roots and skip choices; local timeouts propose alternatives rather than create objective absence. Define preference changes, finalization serialization, delayed values and descendant/next-epoch effects. Independent binary vote records do not automatically compose into this exclusivity.
4. **Liveness and closure coupling.** Specify when each decision starts, what evidence permits skip inputs, how many contributions/weight must be included, and when every decision is considered complete. A timer alone proves neither a missing publisher nor termination. If eventual bounded delay/service and sufficient online stake are required, state them; do not claim fully asynchronous HoneyBadger liveness. Partial synchrony alone also does not prove Avalanche termination for these conflicts without the rest of the algorithm and assumptions.
5. **Epoch-wide safety accounting.** If each actual decision instance i has a justified failure bound ε_i under the complete adaptive composition, P(any failure) ≤ sum ε_i. Independence is unnecessary for this union bound, but the applicable conditional/marginal bounds, number of instances, equivocation/skip alternatives, roster transitions and epochs covered must be justified. Unknown per-item ε cannot be replaced by a confidence constant. Over an unbounded lifetime, a fixed per-item bound does not itself give one finite global guarantee.
6. **Deterministic output and execution.** Include/SKIP results, exact identities, complete data, dependencies and the chosen support/scheduler/context must all agree before output is complete. Missing reconstruction is unknown. Whole-epoch roots are valid commitments once these inputs are fixed; agreement on independent moving local pools remains the wrong target.

The authored cutoff-vector mechanism and these agreement contracts remain a proposed new protocol, not an existing eCash clock. The requested production clock/lifecycle vectors still need exact chosen identities, merge/cut transitions and included/skip rules. The attached small conflict vectors cover only the proposed deterministic execution layer and clearly label alternatives/pending cases. No new finality/wire implementation is authorized by this study.


## Review and verification record

Two independent reviews (overlay and protocol) and an experiment plan were recorded. The protocol reviewer reread proposal39c1ccead262 and the current study/fixtures, confirmed all four requested areas and no remaining contradiction in their stated scope; this approves the accuracy of the proposal review, not any architecture. The overlay reviewer confirmed the G/M/R/Z outputs and persisted a current H1/H2/H3, prior-loser and per-contribution closure addendum. Both independent reviews cover the latest ancestor-closed variant as a proposal, not a selected architecture. Five symbolic support/generation vectors pass arithmetic checks; no production, cryptographic, ACS or security experiment was run.


## Section 11 follow-up

The [setup and availability decision review](epoch-availability-open-decisions.md) covers the later no-trusted-setup proposal. Its four decisions remain open: common roster/stake lifetime, explicit availability attestation, include/skip agreement/liveness, and epoch/block validity. Ordinary Schnorr certificates do not automatically provide the remaining guarantees.

---

## References

1. **[Oak 2026]** Professor Oak, *"Snowball to Snowstorm: Rateless Set Reconciliation and Probabilistic Mempool Preconsensus for Proof-of-Work Blockchains"*, October 2026.
2. **[Rocket et al. 2019]** Team Rocket, Maofan Yin, Kevin Sekniqi, Robbert van Renesse, and Emin Gün Sirer, *"Scalable and Probabilistic Leaderless BFT Consensus through Metastability"*, `arXiv:1906.08936`, 2019.
3. **[Babel et al. 2023/2025]** Kushal Babel, Andrey Chursin, George Danezis, Lefteris Kokoris-Kogias, and Alberto Sonnino, *"Mysticeti: Low-Latency DAG Consensus with Fast Commit Path"*, `arXiv:2310.14821` / *NDSS*, 2025.
4. **[Nakamoto 2008]** Satoshi Nakamoto, *"Bitcoin: A Peer-to-Peer Electronic Cash System"*, October 2008 (`https://bitcoin.org/bitcoin.pdf`).
