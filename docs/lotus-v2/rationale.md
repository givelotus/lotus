# Design rationale and claim boundaries

Status: explanatory, not normative. [Consensus](consensus.md) owns rules; [decisions](decisions.md) owns alternatives.

## Authorization and assets

Alternative paths express OR; the required branches within one path express AND. Branch MASTs select methods within a role. Asset accounting is a separate obligation: conserving token units does not prove the owner approved, and owner approval does not authorize additional supply. Program-derived token identity supports continuing mint authority; outpoint-derived identity offers a different genesis model. D05 must close that tradeoff, including which historical code is reusable.

A branch tree needs membership, while a transaction tree needs order and a state map needs key position and nonmembership. Calling all three “Merklix” obscured their different contracts. The proposed branch proof uses sorted children; it must not be silently reused to authenticate transaction order.

Leaf/interior tags follow the principle illustrated in [RFC 6962 §2.1](https://www.rfc-editor.org/rfc/rfc6962#section-2.1). Their inputs are distinct by construction, while security of their outputs still relies on cryptographic assumptions. BLAKE3's internal compression flags do not tag the application's scripts and tree nodes automatically. Duplicate-leaf ambiguity and leaf/interior ambiguity are separate concerns; the old draft conflated them. Adding a second leaf normally changes a root even when the first leaf's encoding is unchanged.

## What belongs to the daemon

Memory layout, RAM trie representation, RocksDB/LevelDB selection, write-behind, mempool indexes, block-template algorithms, RPCs and transport may evolve if they preserve accepted blocks and required state. The authenticated-state root algorithm is consensus even when its physical storage is replaceable. Snapshot discovery/streaming can evolve; snapshot trust cannot be inferred from transport success.

A matching state root detects a mismatch; it does not reconstruct lost state. Crash recovery needs a durable atomic boundary linking block index, coins, undo and monetary state, plus a replay policy. Likewise, fixed-width fields do not automatically align a packed wire record. Two-minute spacing does not eliminate stale blocks. Removal of ancestor bookkeeping does not make parsing, signatures or dependency processing O(1).

The scope of post-genesis improvements must be reviewed. New wallet languages and optimized validation can preserve semantics. New accepted opcodes, different hashes, changed resource ceilings, transaction versions or monetary parameters change consensus unless their behavior was already completely defined at genesis. No advisory voting layer can authorize such changes within the zero-hardfork objective.

## Monetary research

Research source: English version 1.2 of `adaptive-pow-monetary-policy/main.tex` in the separate latex repository; repository HEAD observed during this pass: `b2b42da53a008cff97cce63cd6b522f3e1d32f34`. The paper has local edits, so that commit alone does not identify version 1.2. The observed source SHA256 is `6aa301cf0069f68bf8b256ca929b1ba11dbff8e6cd1f0206783f310237c3387b`. Export that source with its dependencies before relying on it as an external review artifact. No paper change is part of this documentation pass.

The paper's height-decaying bootstrap plus stateful work-responsive tail is not identical to the former spec's direct `K sqrt(D)` shorthand. Define target T versus work W explicitly; exact per-block work convention, lag, clipping and integer rounding matter. A timestamp-based decay proposal is a separate decision.

A miner's immediate reward and its influence on future difficulty need not accrue to the same party. Evaluate complete feasible timestamp histories under the exact DAA, not arbitrary independent choices of future difficulty. Local stability under a simplified hashrate model does not prove truthful timestamps or resistance to mobile miners. D10 requires the economic objective, assumptions and falsifiable conclusions before choosing a formula.
