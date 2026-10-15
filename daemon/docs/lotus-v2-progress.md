# V2 implementation progress — October 14, 2026

The [implementation plan](lotus-v2-implementation-plan.md) owns the full gates.
No complete V2 block has been mined and accepted.

| Slice | State and evidence |
| --- | --- |
| Native development series | Integrated 26 patches, 000–025, on ABC `1fb7db17`. Fresh mailbox replay matches every recorded tree; final `b0c32ae8ded2cdfa520bd91cf579d991c8dfa004`. See the [review packet](../candidates/v2-native-reviewed-20261014/README.md). Modules remain isolated from daemon consensus. |
| Framing, commitments and signing | Bounded output/transaction/coinbase encoding, complete core/full identities, branch/indexed/ordered commitments, resolved-coin roots and prepared signing. Debug/Release focused tests pass; root reviewed and reran checks. |
| UTXO models | Scalar oracle plus incremental in-memory path updates/proofs. Mixed update, insertion-order and undo/reinsert comparisons pass. Worker AddressSanitizer and root Release checks pass. No persistent chainstate or block undo yet. |
| Native VM | Bounded P03 subset, authenticated witness/branch checks, signature/introspection operations, and explicit P05 charging. Root fresh Release build passes; 298 execution and 477 cost cases agree with Python. Signing preparation is reused within an invocation; transaction-wide sharing is pending. |
| Python reference | Output/monetary and bounded VM reference integrated; 44 tests pass. P05 now applies the cap to the complete composed invocation charge, preserving checked-u128 intermediate rejection. Skipped BREAK semantics are explicit. |
| Compiler and ABI | TypeScript templates, helpers, typed commitments, promise dependency scheduler, bounded recursive symbolic stack optimizer, generated TS/Python clients and spend/mint planners. Root ran 56 tests with no skips, including 256 seeded VM comparisons. The pipeline demo reduces 31 to 11 opcodes and 95 to 75 bytes. |
| Native compiler integration | Signed Payment plus all five mint/transfer invocations pass the native charged VM. Unauthorized issuer, re-signed bypass policy and mint coin-read probes reject. Full transaction/block validity is not established by these fixtures. |
| Miner CPU/OpenCL | Candidate `a3ea57d2`; worker GPU/CPU and GUI-mode checks pass. Root reran original GPU parity. Final miner patch integration and daemon job API remain separate review work. |

Active next lanes: ordinary transaction validation (conservation, mint delta,
resolved spends, fees and all selected invocations) and remaining assigned native
VM operations. Persistent state, monetary/block transitions, genesis calibration,
and end-to-end mining follow those gates. All unfrozen parameters remain explicit
development profiles; no production release or live workspace was changed.

Review corrections include the maximum-count indexed-proof overflow, witness
profile limit bypass, repeated transaction hashing per signature, incremental-tree
leaf ownership, symbolic loop aliases, and zero-bound static-cost composition.
Passing focused tests does not close the full protocol implementation plan.
