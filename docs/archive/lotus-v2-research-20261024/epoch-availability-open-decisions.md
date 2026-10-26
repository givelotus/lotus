# Section 11: setup, availability and four remaining protocol decisions

> **Status: Superseded by Snowstorm ([`../snowstorm.md`](../snowstorm.md), 2026-10-24).** This document is retained as a historical research record of earlier D11 explorations. See **[`../snowstorm.md`](../snowstorm.md)** for the normative specification of Snowstorm's multi-peer rateless $\text{GF}(2^{64})$ BCH fountain miniblocks, coupled peeling decoder, Type 1/2/3 algebraic fraud proofs, self-clocking `parent_base_root` layer promotion, two-phase anti-drip union with symmetric Phase 2 demotion, symmetric transitive conflict quarantine (`BatchId(E)` tiebreaking), and 0-RTT `SnapBlock` (`SEALEDHEADER`) propagation.

Reviewed proposal SHA256 `163498b314d5a5074945e49325ae4e1f773dfe9558f98a70d3ca267db363554e`.


## Direct answer about trusted setup

A certificate consisting of ordinary independently generated Schnorr signatures does not require a trusted dealer or threshold-key setup. It **does** require an agreed authenticated signer roster, exact weights, authorization and signing semantics. Removing threshold encryption/common coins from this candidate removes those particular threshold-key components, not the need to solve membership, agreement, availability and liveness.

Threshold encryption or a threshold coin can use distributed key generation rather than a single trusted dealer, but that adds its own participant, adversary, robustness, key-rotation and deployment requirements. DKG is a cryptographic key-establishment protocol; it does not decide which gossiped stake proofs constitute the common roster. Stake ownership/economic alignment is likewise not a cryptographic setup assumption or an agreement proof. Do not describe local sampling plus a timeout as an implementation of HoneyBadger's common coin.

Union inclusion does not by itself prove censorship resistance: the target must actually reach at least one included, available contribution before its cutoff, and the selected execution rule must accept it. Optional threshold encryption needs a separate threat model, especially while transaction bodies are already publicly relayed.

The four decisions below are the remaining architecture boundaries. “No trusted setup” does not settle any of them.

## Decision 1 — common roster, stake lifetime and punishment authority

**Actual source fact.** In inspected Lotus source, `Proof::verifyUtxos` reads `ActiveChainstate().CoinsTip().GetCoin` under `cs_main` and rejects a missing/spent outpoint, checking other proof conditions against the active chain. `PeerManager::registerProof` calls this validation. `Processor::updatedBlockTip` calls `PeerManager::updatedBlockTip`, which revalidates registered/dangling proofs and invalidates failures. The inspected live-validation path therefore uses confirmed active-chain UTXO state, not an overlay of locally seen mempool spends. No claim is made that a merely announced spend immediately invalidates a proof through this path. Source anchor inspected: `c3089be8d2151d4c295333ae806355822864647b`; these files retain the prior Avalanche proof architecture.

The user's correction is right: spending a staked UTXO makes a proof referencing it invalid when that spend is reflected in the chain state used for verification. A proof is evidence of existing stake, not an off-chain fund lock, escrow, automatic burn or slashing bond. Bitcoin ABC's public protocol describes stake proofs and delegated signing authority, not a bond seizure mechanism. [Official wire/proof documentation](https://raw.githubusercontent.com/Bitcoin-ABC/bitcoin-abc/master/doc/avalanche.md)

**User-directed prospective rule.** An announced or mempool-only spending transaction does not invalidate Avalanche votes or change stake eligibility. Once the transaction **spending the stake UTXO confirms**, future poll sampling uses the updated proof eligibility. Already completed votes/decisions and finalized epochs are never retroactively invalidated by that spend. Already issued polls retain their captured sample and authority/weight interpretation; do not substitute a new roster or reweight their responses halfway through. This is the selected policy direction, not an optional retroactive alternative.

Current source verifies against the active confirmed-chain UTXO view and rechecks on tip updates; this matches the confirmed-spend distinction. Do not add an unstated requirement that the spending block must first be Avalanche-finalized. The exact agreed anchor for the new epoch/certificate protocol and the handling of a PoW reorg that removes/restores the spend still require explicit rules. Signature/proof checks for a newly issued request follow the applicable confirmed view; historical sampling records remain historical.

Keep three lifetimes distinct: live sampling eligibility for a new poll; the fixed contributor set and support-weight snapshot that define a committed epoch; and the certificate's named signer/retention domain. Updating live eligibility cannot quietly change which contributions belong to an already selected cut or reweight its earlier support scores. If the proposed clock instead changes contributor membership during an open epoch, specify a new cut/roster version and agreement rule rather than reinterpreting the old commitment. Any new certificate or retry must name its applicable domain; do not combine acknowledgements from incompatible roster versions.

**Remaining epoch rule.** An epoch must name an agreed exact roster/weight/chain anchor. It must define how the prospective live-eligibility policy maps to contributor-set/weight snapshots and certificate eligibility when confirmed stake spends, proof expiry/replacement or reorgs occur. A locally observed unconfirmed spend cannot cause one node to retroactively erase weight from a historical certificate while another still accepts it. Conversely, freezing old stake weights indefinitely would ignore genuine withdrawal and is not proposed. Define bounded epoch/retention lifetimes, transition checkpoints and rejection/reanchor rules explicitly. A historical signature can remain mathematically verifiable after the proof becomes ineligible; whether it remains protocol-valid evidence is a domain/lifetime rule, not a signature property.

Options:

* **On-chain registration anchored in accepted chain state:** the cleanest common enumeration baseline to evaluate. It is a new registration/consensus mechanism; specify eligibility, deposit ownership, spending/removal timing and transitions. Registration need not mean lockup unless explicitly chosen.
* **Consensus-selected off-chain membership:** possible, but requires its own finite proposal set, inclusion/absence/closure rules and bootstrap. Saying “vote on membership” moves the same agreement problem rather than eliminating it.
* **Minimum stake plus an eligibility rule:** only sufficient if the rule yields the same complete, enumerable roster from agreed data. A minimum amount applied to locally gossiped proofs does not do that.

Two signed incompatible contributions are portable equivocation evidence only if both signatures are valid for the same fixed `(network, protocol domain, roster, publisher authority, epoch)` and the protocol permits one contribution there. Separate microbatch sequence numbers or allowed revisions must not be mistaken for equivocation. Specify how evidence becomes agreed, which authority/stake it affects across replacement proofs, and when membership/reward exclusion begins. A local connection ban is not a consensus membership decision. Reward forfeiture requires an actual agreed reward entitlement/policy; automatic coin seizure does not exist here. `V_(e+2)` removal cannot be applied independently from different local evidence sets.

## Decision 2 — what an availability certificate guarantees

Let R be the fixed agreed roster, w(v) its non-overlapping integer or exactly specified rational weights, and F a justified bound on Byzantine weight in that domain. A certificate with distinct authorized signer weight `sum w(v) > F` implies at least one signer is outside the assumed Byzantine set. Write a **strict weight inequality**; `f_s+1` is meaningful only after declaring integral weight units. This threshold proves neither quorum intersection nor agreement on one contribution. It is not an automatically inherited eCash/Snowball threshold.

For a toy roster of total weight100 with an assumed Byzantine boundF=30: a certificate of weight30 can be entirely Byzantine; weight31 guarantees some honest weight under that assumption, but could contain only one honest holder of weight1. Two sessions of a weight30 authority still count as30, not60. These are arithmetic illustrations, not selected thresholds or an availability theorem.

The conclusion is useful only if honest signing has an explicit obligation. Before signing, the holder must reconstruct and verify the exact complete ancestor-closed contribution and required metadata, reserve its retention exposure, and commit to serve it under defined conditions. The conceptual signed statement must bind at least:

* protocol/network/domain version, roster identity and publisher authority;
* exact epoch/contribution identity and canonical content commitment, including exact witness identities;
* authenticated count/byte/encoding limits or the complete header hash that commits them;
* the agreed chain/prior-state validation anchor and authorized signer key domain;
* explicit retention/service horizon and renewal/checkpoint rules.

This is a signing-semantics requirement, not a finalized wire layout. Verify domain/key authorization and weight once per unique stake authority, including overlapping/replaced proofs. Merely collecting many sessions or signatures must not multiply stake.

An ordinary signed Avalanche response binds its poll response, votes and inventory identities. It does not currently carry the above storage reservation/retention promise. Repeated yes votes must not be relabeled as explicit DA acknowledgements. A new signed ACK type or an explicitly revised attestation contract is needed if the design relies on such a certificate. [Official response format](https://raw.githubusercontent.com/Bitcoin-ABC/bitcoin-abc/master/doc/avalanche.md)

The Byzantine bound must cover the relevant signing and retention model, not merely one observed instant: later corruption or loss of incentives after withdrawal cannot be silently excluded. Even an honest signer may later crash, disconnect, prune after its promised horizon or lack sufficient serving capacity. State the fault/availability model, fair-service and network-delay assumptions, minimum recoverability window, recipient catch-up deadlines and rollover/repair behavior. If the promise expires before a lagging honest node can recover, the certificate has not established permanent availability. Requiring “at least one honest signer” can place all recovery load on one small holder; quantify that service bottleneck or require redundancy under a separate availability target. Do not silently count crash failures as Byzantine only when convenient.

The certificate cannot waive local reconstruction/validation where the protocol needs actual data before a yes or before execution. It is also not a choice between INCLUDE and SKIP: two conflicting contributions could each have availability certificates. Their conflict still needs agreement. No certificate here proves elapsed time, complete dissemination to all honest nodes or immutable future stake participation.

## Decision 3 — include/skip agreement and liveness without a common coin

The proposed design is a **different protocol using sampled voting and timeout-triggered alternatives under stated timing assumptions**. It is not HoneyBadger's binary agreement with the common coin replaced by local private randomness. Private samples are not correlated common randomness, and a local timeout is not an agreed absence proof. The current §11 correctly requests a liveness argument; the stronger statement “replaces it” remains unestablished.

Define a single exclusive decision per `(roster,publisher,epoch)` over exact contribution identity or SKIP, with incompatible signed roots handled in that same conflict domain. Specify initial preferences, neutral responses, switching, eligible polls, finalization serialization, availability dependencies, and late-message handling. An honest contribution can arrive around a skip timer and conflict with SKIP without author equivocation. The known timeout/head disagreement is not resolved merely by adding a DA certificate.

State eventual network/service bounds, the online honest stake condition, peer discovery/sampling assumptions, adversarial scheduling and restart behavior. These may support a partially synchronous argument; partial synchrony itself is not a proof that this sampled conflict protocol terminates. Couple skip initiation and completion to a required included-weight or nonempty-subset condition. If all SKIPs can close an epoch, say whether that empty output is permitted and how the next cutoff advances. If only included contributions count toward theta, explain what happens when available weight cannot meet it. No hidden lowering of thresholds after timeout.

Options: complete and analyze this sampled include/skip state machine; or select an explicit reliable-broadcast/binary-agreement construction with its membership/cryptographic assumptions. Ordinary Schnorr DA signatures are compatible with either direction, but cannot supply the missing agreement theorem. A common coin/DKG should be introduced only if the chosen protocol needs it; omitting them is also a design choice requiring its own liveness analysis.

For justified per-instance failure bounds ε_i under the actual adaptive composition, an epoch/lifetime union bound is `P(any failure) <= sum ε_i`; independence is not required. The bounds, instance counts, epochs, certificate failure conditions and changing membership must be specified. The current confidence constant is not an ε estimate. No numeric safety guarantee or asymptotic-lifetime guarantee has been established for the new protocol.

## Decision 4 — executed epochs versus block validity and reorgs

“Miners must commit to closed epochs' executed roots” is consensus-critical. A block validator must be able to derive/verify the required epoch selection, exact executed membership and state from agreed data. A root alone is not proof of an epoch decision or access to its contents. Specify block commitments/references, availability/catch-up proofs or data, fork/roster/chain anchors and activation rules. A new node cannot validate a block by consulting another node's private sampled-finality status.

Decide whether epoch outcomes constrain hard block validity, Avalanche block preference/parking only, or merely mining policy. Those choices have different safety and compatibility effects and must not be merged in implementation. Define whether transactions outside epochs are allowed, whether inclusion is mandatory, and what happens to confirmed conflicting spends. A block cannot change from valid to invalid merely because a node later learns an old off-chain close claim; validity must follow the chosen deterministic available evidence rule and explicit activation/anchor semantics.

Define permitted PoW reorg behavior for the epoch lineage, prior executed state, stake validity and certificates. Continuous epoch numbering does not make those dependencies disappear. Decide whether an anchored epoch remains a historical record but loses eligibility on a new chain, must be reconstructed/revalidated, or constrains which reorgs the consensus accepts. Never rewrite an already executed epoch opportunistically to fit a new tip. The interaction between block confirmation of stake spends and the next roster must use the same agreed transition policy from Decision1.

Until these decisions are complete, it is reasonable to prepare generic storage and symbolic execution vectors, but not to enable new wire consensus, marker finality, membership punishment or mandatory epoch block commitments.

## Validation additions

Add small counterexamples before randomized experiments: certificate weight exactly F versus strictly greater; duplicate sessions/overlapping stakes; one honest signer goes offline or reaches its retention horizon; valid historical signature after confirmed withdrawal; nodes see different mempool spends but the same anchored chain; reorg removes/restores a stake UTXO; two availability-certified conflicting roots; contribution/skip race after a valid ACK; evidence known to one node before roster transition; a late node validates an epoch-committing block without original gossip; late epoch information cannot arbitrarily revise block validity.

No numerical experiment, cryptographic proof or implementation is approved by this note. “Settled” headings in the external discussion are recorded as proposed direction only; the four decisions remain open.


## Independent review

`SECTION11-PROTOCOL-REVIEW.md` independently checks the actual proposal and unchanged Lotus proof/vote architecture. Its guarantees and limitations agree with this note: possession signatures need a retention contract and do not select one value; sampled include/skip agreement needs its own liveness analysis; block commitments need independently verifiable epoch evidence. The subsequent user-directed confirmed-spend/prospective-eligibility clarification above supersedes any impression that historical votes must be retrospectively removed or that an unconfirmed spend changes eligibility; issued polls retain their captured interpretation. No implementation approval follows.

---

## References

1. **[Oak 2026]** Professor Oak, *"Snowball to Snowstorm: Rateless Set Reconciliation and Probabilistic Mempool Preconsensus for Proof-of-Work Blockchains"*, October 2026.
2. **[Rocket et al. 2019]** Team Rocket, Maofan Yin, Kevin Sekniqi, Robbert van Renesse, and Emin Gün Sirer, *"Scalable and Probabilistic Leaderless BFT Consensus through Metastability"*, `arXiv:1906.08936`, 2019.
3. **[Babel et al. 2023/2025]** Kushal Babel, Andrey Chursin, George Danezis, Lefteris Kokoris-Kogias, and Alberto Sonnino, *"Mysticeti: Low-Latency DAG Consensus with Fast Commit Path"*, `arXiv:2310.14821` / *NDSS*, 2025.
4. **[Vermorel, Séchet, Chancellor, & van der Wansem 2018]** Joannes Vermorel, Amaury Séchet, Shammah Chancellor, and Tomas van der Wansem, *"Canonical Transaction Ordering for Bitcoin"*, June 12, 2018.
5. **[Vermorel, Séchet, Chancellor, & Cox 2018]** Joannes Vermorel, Amaury Séchet, Shammah Chancellor, and Jason Cox, *"Merklix Tree for Bitcoin"*, July 2018.
