# Snapshot holders and epoch numbering: proposed boundary

> **Status: Superseded by Snowstorm ([`../snowstorm.md`](../../archive/snowstorm.md), 2026-10-24).** This document is retained as a historical research record of earlier D11 explorations. See **[`../snowstorm.md`](../../archive/snowstorm.md)** for the normative specification of Snowstorm's multi-peer rateless $\text{GF}(2^{64})$ BCH fountain miniblocks, coupled peeling decoder, Type 1/2/3 algebraic fraud proofs, self-clocking `parent_base_root` layer promotion, two-phase anti-drip union with symmetric Phase 2 demotion, symmetric transitive conflict quarantine (`BatchId(E)` tiebreaking), and 0-RTT `SnapBlock` (`SEALEDHEADER`) propagation.


## A candidate is a held snapshot

A candidate descriptor names its domain, agreed chain anchor, epoch slot if that protocol uses one, exact predecessor/base descriptor, cumulative canonical TxId/TxHash root, and commitment-format version. Candidate content identity excludes holder identity and connection/request handles: two holders of the same exact content descriptor offer the same candidate. Counts and short-ID sketches are bounded hints; they do not replace the canonical root. A sender advertises itself as a holder only after it possesses and validates the complete immutable candidate and can serve it within the advertised retention/resource policy.

Maintain a bounded descriptor-to-source table. Direct advertisements identify the authenticated connection offering service. A forwarded signed preference identifies its original authority and preferred descriptor, but does not imply that the forwarding peer stores the candidate. A forwarded holder advertisement still needs an actual connected retrieval route or an explicit bounded referral mechanism. An unreachable origin is not a usable source merely because its signature verifies. The table may record several independently reachable holders, request budgets, failures and retention expiries; it is not an unbounded global routing index.

After selecting a concrete advertised target, pin its descriptor and the owned request context. Ask a holder for summaries/proofs of that exact view, zoom its mismatching prefixes, retrieve exact identities/bodies, and validate them. Reuse local/base tree nodes and transaction bodies as a cache; do not assume local extras belong to the target. Historical reconstruction checks the committed anchor/state and membership; admitting those bodies into today's live mempool separately checks current chain/policy validity. An old view does not become unmaterializable merely because the live chain advanced. Keep the reconstruction private until its canonical root and required state/ancestor validity match the descriptor. Only then may the node advertise itself as a holder or positively vote for that candidate. If a holder expires or withholds the view, retry another holder or cancel that reconstruction; never silently retag a response to a newer snapshot.

For AB and AC, there are initially two held candidates, not an existing ABC target. Compatible recovery can let a node construct ABC. Once complete and validated, that node becomes a holder and may advertise ABC as a third candidate. Reconstructing exactly AC using AB as a cache produces a separate AC view; it does not require forgetting B from live/pending ownership. Voting preference, retrieval priority and transaction retention remain separate.

Requests bind connection incarnation, direction, a nonreused owned request ID, exact target descriptor/root, and prefix/cursor. Reconnect creates a new ownership domain; a late response cannot attach to a successor connection's request with the same numeric handle. Epoch number alone is insufficient because one epoch can have several candidate versions. Direct arrivals while serving a pinned snapshot cannot change its responses. These semantics belong to the future owned-snapshot exchange; the existing moving-window wire does not yet implement them.

## One implementable naming baseline using existing authority

The smallest shared namespace that requires no new epoch-consensus mechanism is `EpochKey = (B, 0)`, where B is an agreed checkpoint established by the chain authority the node already runs. It may run many reconciliation attempts and create many local immutable snapshots inside that namespace. A local snapshot is separately named by its exact descriptor/root and holder-local request handle; its local sequence is not a network epoch number.

When existing chain authority establishes a successor checkpoint B', switch future mutable work to `(B', 0)` under a routing fence. Retain bounded old-B descriptors/pins for exact catchup, and revalidate current live membership under the new anchor. A local unfinalized best-tip change does not independently create that shared transition. A lagging node may still serve B while another serves B'; incoming claims of B' are bounded hints until the lagging node validates the existing chain-authority decision. A mere signed peer claim is insufficient. Reorg/fault handling follows the actual existing authority; this proposal does not override an Avalanche-finalized block with arbitrary greater-work history.

This is a proposed fallback, not a silent replacement of the user's desired multiple epochs per block. It supplies common naming at the existing checkpoint cadence while allowing fast reconciliation/snapshot passes within each namespace. If no shared finalized checkpoint exists in an Avalanche-disabled deployment, permissionless reconciliation can still use validated chain anchors and connection-owned snapshots, but this note does not pretend independently observed tips are one agreed epoch.

## What an ordinal greater than zero requires

For multiple shared epochs under B, start with `(B, 0)` and an explicitly agreed base. A node may open `(B, n+1)` only after the selected shared-decision mechanism has decided one complete descriptor for `(B, n)` and the node has validated/materialized the predecessor needed to proceed. The successor candidate commits that exact predecessor/base. Competing predecessors for the same `(B, n+1)` are not silently different valid histories: they expose the missing or violated uniqueness rule. A future-slot advertisement is held within a small bounded horizon while its predecessor is recovered; it cannot force arbitrary epoch allocation or an ordinal jump.

The ordinal update rule is simple; supplying the unique predecessor decision is the unresolved part. Local three-match quietness, a peer's claimed counter, a root hash and an observed percentage of gossiped votes do not supply it. The current ABC processor's typed authenticated queries are useful plumbing, but the reviewed scheduler does not implement one exclusive root-choice decision per slot. The optional multichoice/Snowball study must specify and test that mechanism before claiming shared fast epoch progression. No confidence or completed query from another exact root/activation can be reused as evidence that this predecessor was selected.

Local checkpoints can increment their own counters without waiting for that decision, remain immutable, and place later additions/removals in successor deltas. Their counters may differ across nodes. Comparing full compatible current views can still disseminate transactions across differing local bases. Relabeling these local counters as a common finalized epoch would add an unsupported agreement claim.

## Required small traces for the future exchange

* N1 holds AB, N2 holds ABC: N1 retrieves C from the exact advertised N2 snapshot, verifies ABC, then advertises itself as a holder. Direct D received meanwhile stays in its correct staging/live ownership.
* N1 holds AB, N2 holds AC: ABC is not advertised as a target until some node actually constructs and validates it. A preference for AC alone does not erase B.
* N1 forwards N2's vote for ABC without storing ABC: N1 must not answer a holder lookup with a false local-availability claim. An unreachable N2 makes recovery unavailable, not valid by signature.
* A target expires between prefix and body requests: matching owned requests may finish only while their view remains retained; otherwise explicit cancellation/not-available leads to a new owned request or holder binding for the same descriptor if another holder can serve it. A changed target requires explicit reselection, never mixed-root completion.
* Nodes locally seal AB and ABC with local sequence 1: both local records remain immutable, but neither proves a common `(B,1)` predecessor. Their current views may still reconcile.
* With a separately reviewed unique decision for `(B,0)=ABC`, a laggard remains at0 until it validates the predecessor; future-slot hints never relabel its old requests. Without that decision mechanism this is a conditional trace, not an executed consensus test.

---

## References

1. **[Oak 2026]** Professor Oak, *"Snowball to Snowstorm: Rateless Set Reconciliation and Probabilistic Mempool Preconsensus for Proof-of-Work Blockchains"*, October 2026.
2. **[Vermorel, Séchet, Chancellor, & van der Wansem 2018]** Joannes Vermorel, Amaury Séchet, Shammah Chancellor, and Tomas van der Wansem, *"Canonical Transaction Ordering for Bitcoin"*, June 12, 2018.
3. **[Vermorel, Séchet, Chancellor, & Cox 2018]** Joannes Vermorel, Amaury Séchet, Shammah Chancellor, and Jason Cox, *"Merklix Tree for Bitcoin"*, July 2018.
4. **[Rocket et al. 2019]** Team Rocket, Maofan Yin, Kevin Sekniqi, Robbert van Renesse, and Emin Gün Sirer, *"Scalable and Probabilistic Leaderless BFT Consensus through Metastability"*, `arXiv:1906.08936`, 2019.
