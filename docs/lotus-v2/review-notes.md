# Review handoff — October 9, 2026

The design is ready to begin isolated candidate implementation. It is not ready to freeze genesis. Start with [I01 workspace routing and I02 independent reference semantics](../plans/implementation-entry.md); investigate the historical v1 sync obstruction in parallel once its evidence is available. The production v2 daemon still starts from a verified, compatible v1 release.

## Principal proposals to review

- **Recursive header groups:** preserve v1's compact partial-header rationale. P04 proposes 134 bytes, a state commitment, no epoch/lucky-block pointer, and v1's 64-bit nonce and 48-bit timestamp. Both widths are carried over from v1 unchanged. The 64-byte linkage and 82-byte work disclosures are exact candidate sizes. Field-Merkle proofs are an alternative, not the recommendation.
- **Explicit signed intent and $O(1)$ sighash preimages:** P01 defines transaction framing, core/full identities (with scripts and proofs in Core and only witness arguments excluded), hard output caps (`MAX_OUTPUT_BRANCHES = 16`, `MAX_OUTPUT_PATHS = 16`, bounding every `Output` to $\le 812\text{ B}$ and every `Coin` to $\le 867\text{ B}$), a 41-byte `SpendSelector` binding `(input_index, branch_index, Leaf(script))`, and fixed-size signing preimages across all three modes (`00`, `01`, `02`) using `OwnInputHash(i)` and `OutputsHash` / `OutputHash(i)` so every signature check hashes at most 3 BLAKE3 blocks in $O(1)$ time.
- **Typed commitments:** P02 distinguishes unordered branch membership, ordered transaction inclusion, indexed contract Merkle trees (`merkleidx`) and a compact single-leaf-collapsed sparse UTXO tree (~27 hashes per key/proof at $10^8$ coins). The state envelope also commits monetary recurrence state (D11's protocol faucet is rejected).
- **Closed VM:** P03 specifies 215 assigned opcode bytes and 41 `OP_SUCCESS_N` bytes, arithmetic, structured loops, branch continuation (`OUTPUTCONTINUESBRANCH` `0xcf`), in-contract Merkle root verification/update (`MERKLEROOT_SORTED` `0xee`, `MERKLEROOT_INDEXED` `0xef`) and signature profiles. No opcode reads block height, block time or global `UtxoRoot`, so a script's result cannot change as blocks arrive (`C22a`); input × output loops remain permitted. This is a candidate new ABI, not a claim of existing Script compatibility.
- **Conservative execution:** every required branch executes independently. Cache optimization needs context-complete equivalence; static cost never assumes a hit. P05 covers aggregate transaction/block work and memory, not just per-input loop counts.

## Production blockers that remain real

The [decision register](decisions.md) owns the complete list. The main unresolved choices are bootstrap/tail issuance and timestamp incentives (D10; protocol faucet D11 is rejected), future-time eligibility, numerical resource limits, final header/PoW parameters and launch identity. None has been silently filled with a convenient code default. Independent parser, signature, VM and state vectors must validate the proposals before acceptance.

Timestamp truthfulness is still an economic research question. P06 defines the objective and feasible-history analysis needed to compare mobile and persistent miners; square-root issuance plus decay is not presently established as a truthful-timestamp mechanism. The paper has not been changed by this planning pass.

## Evidence and limits

The [small structural model](tools/README.md) checks framing, hashing, tree proofs, header sizes and selected integer algorithms. It records its own source and six packet digests. Those results are construction checks from one model, not independent consensus review or signed-payment validation. The [validation ledger](../../daemon/docs/lotus-validation-results.md) separates these from unrun daemon, live-sync, monetary and performance gates.

No daemon build, patch replay, live-network operation or benchmark was attempted. The [faster-machine handoff](../plans/faster-machine-handoff.md) and bounded implementation contracts describe the next execution steps. No external tickets or changes have been published.
