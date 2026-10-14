# V2 implementation progress — October 14, 2026

The [implementation plan](lotus-v2-implementation-plan.md) owns the full gates. This ledger distinguishes integrated code from worker candidates. No complete V2 block has been mined and accepted.

| Slice | State and evidence |
| --- | --- |
| Output reference | Integrated `beebcbde`; independent fixed wires and rejection cases |
| Spec and launch plan | Checkpoint `4060859e`; structural checks pass, not independent full consensus validation |
| Monetary reference | Integrated `b9563366`; root reviewed and ran all12 reference tests, including coinbase burns and u128 aggregate amounts |
| ABC foundations | Integrated `b1c0bd77`:9 patches on ABC master `1fb7db17`; exact replay, six miner cases, header vectors and Debug/Release output tests. Root reran miner/header/Release checks. Source tree `2e373abb42c7989587cc8083de79a86a00efe3bf`. |
| Miner CPU/OpenCL | Isolated V2 integration `a3ea57d2`; worker executed V1 and expanded V2 GPU tests on Apple M5 Max. Root reran original V2 GPU parity. GUI unsupported-mode error handling has a worker fix awaiting root review; daemon job integration absent. |
| Transaction framing | Python `a95b9366`, native `b58c83fa`; worker reports Debug/Release and independent corpus passes; root review pending |
| Commitment primitives | Native `de5f497f`; branch/indexed/ordered trees and transaction identity wrappers, independent vectors; root review pending |
| VM reference | Integrated bounded interpreter, size-aware static charging, BIP340 and raw BLAKE3; root ran 41 reference tests, including mint context and mandatory-path introspection. Explicit profiles and unsupported-feature errors; no complete transaction validator. |
| Compiler and ABI | Integrated TypeScript templates, helper inlining, multi-method P02 proofs, typed hash references, TS/Python multi-input spend/mint runtimes and gallery with fungible-token and burn-to-upgrade sources. Bounded fixed-point literal/stack rewrites preserve tested failures. Root ran 44 package tests (no skips), rebuilt the native fixture checker, verified signed mint/transfer proofs, identities and signatures, and ran all five token invocations plus rejection cases in the reference VM. |

Active daemon lanes: native foundation integration (ordered patches 009–014 for commitments, sparse state, transaction framing and signing; combined candidate `283ded8c6`, Debug/Release and replay checks in progress) and a native VM implementation. Next gates are root review of these candidates, complete transaction validation, persistent state and monetary/block transition, then mining job integration. Workers continue in isolated worktrees; candidates are not automatically accepted because tests pass. Unfrozen cost/monetary/network parameters must remain explicit development profiles.

Review caught and requested fixes for release-disabled C++ assertions, mismatched C++ namespaces, omitted coinbase explicit burns, aggregate amount widths, and GUI panics. Fixes to the first four are reflected in integrated slices; GUI correction is pending. These are bounded correctness checks, not a claim that the whole design is audited.
