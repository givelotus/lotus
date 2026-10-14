# V2 implementation progress — October 14, 2026

The [implementation plan](lotus-v2-implementation-plan.md) owns the full gates. This ledger distinguishes integrated code from worker candidates. No complete V2 block has been mined and accepted.

| Slice | State and evidence |
| --- | --- |
| Output reference | Integrated `beebcbde`; independent fixed wires and rejection cases |
| Spec and launch plan | Checkpoint `4060859e`; structural checks pass, not independent full consensus validation |
| Monetary reference | Integrated `b9563366`; root reviewed and ran all12 reference tests, including coinbase burns and u128 aggregate amounts |
| ABC foundations | Integrated `b1c0bd77`:9 patches on ABC master `1fb7db17`; exact replay, six miner cases, header vectors and Debug/Release output tests. Root reran miner/header/Release checks. Source tree `2e373abb42c7989587cc8083de79a86a00efe3bf`. |
| Miner CPU/OpenCL | Isolated V2 integration `94e176f4`; worker executed V1 and expanded V2 GPU tests on Apple M5 Max. Root reran original V2 GPU parity. GUI unsupported-mode error handling remains a review blocker; daemon job integration absent. |
| Transaction framing | Python `a95b9366`, native `b58c83fa`; worker reports Debug/Release and independent corpus passes; root review pending |
| Commitment primitives | Native `de5f497f`; branch/indexed/ordered trees and transaction identity wrappers, independent vectors; root review pending |
| VM reference | Integrated bounded interpreter, size-aware static charging, BIP340 and raw BLAKE3; root ran 34 reference tests. Explicit profiles and unsupported-feature errors; no complete transaction validator. |
| Compiler and ABI | Integrated TypeScript templates, helper inlining, multi-method P02 proofs, typed hash references, TS/Python call runtimes and seven-example gallery. Root ran 27 package tests, native signed generic Payment checks and positive/negative gallery VM cases. |

Next work: review transaction/commitment interfaces, demonstrate an independently signed payment, complete VM/charging, implement sparse state and monetary/block transition, then connect mining jobs to full validation. Workers continue in isolated worktrees; candidates are not automatically accepted because tests pass. Unfrozen cost/monetary/network parameters must remain explicit development profiles.

Review caught and requested fixes for release-disabled C++ assertions, mismatched C++ namespaces, omitted coinbase explicit burns, aggregate amount widths, and GUI panics. Fixes to the first four are reflected in integrated slices; GUI correction is pending. These are bounded correctness checks, not a claim that the whole design is audited.
