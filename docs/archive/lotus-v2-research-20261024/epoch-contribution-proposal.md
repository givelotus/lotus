# Committed contributions: current §§9.4/10 review and proposed behavior vectors

> **Status: Superseded by Snowstorm ([`../snowstorm.md`](../snowstorm.md), 2026-10-24).** This document is retained as a historical research record of earlier D11 explorations. See **[`../snowstorm.md`](../snowstorm.md)** for the normative specification of Snowstorm's multi-peer rateless $\text{GF}(2^{64})$ BCH fountain miniblocks, coupled peeling decoder, Type 1/2/3 algebraic fraud proofs, self-clocking `parent_base_root` layer promotion, two-phase anti-drip union with symmetric Phase 2 demotion, symmetric transitive conflict quarantine (`BatchId(E)` tiebreaking), and 0-RTT `SnapBlock` (`SEALEDHEADER`) propagation.


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
3. **[Chancellor 2026]** Shammah Chancellor, *"Adaptive PoW Monetary Policy Without Oracles: A Constructive Mechanism for Pseudo-Stability via Work-Coupled Tail Emission and Burn"*, Lotus Network Technical Paper, 2026.
4. **[Nakamoto 2008]** Satoshi Nakamoto, *"Bitcoin: A Peer-to-Peer Electronic Cash System"*, October 2008 (`https://bitcoin.org/bitcoin.pdf`).
