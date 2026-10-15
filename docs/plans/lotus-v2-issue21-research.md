# Issue 21: multi-chain compiler target research

Research checkpoint: 2026-10-15, monorepo `8914db5177d7b97fa7aa7d04172f71ead633775c`, compiler package `@lotus/v2-payment-compiler` version `0.1.0`, artifact target `P01-P02-P03-candidate-2026-10-14`. This note records open research under the user's issue-21 instruction. An authoritative issue body was not available in the inspected repository; no issue quotation or additional requirement is inferred. No external chain documentation was consulted and no external target is claimed supported.

The current packet proposes no target implementation. Lotus lowering, emitter, opcode registry and fixtures remain unchanged. In particular, it assigns or emits neither OP_DEFINE at `0x89` nor OP_INVOKE at `0x8a`. Byte values cannot be repurposed across profiles by analogy with another VM. [C22](../lotus-v2/consensus.md) prohibits dynamic execution; the [P03 baseline](../lotus-v2/decisions/vm-semantics.md) and its assigned instructions and unconditional success scan remain authoritative for this candidate.

## Existing boundary and motivating evidence

The [compiler plan](lotus-v2-compiler-abi.md), especially “Language and lowering boundaries,” “Versioned ABI and artifact contract,” and “Spec feedback from executable contracts,” defines Lotus bytecode as the current target. TypeScript and Python client generation are binding targets, not other consensus VMs. CABI07 package resolution and CABI08 linked local contracts already exist: shared pure helpers inline; linked contracts retain explicit policy roots and ABI commitments. Multi-chain research must build on that distinction rather than treating a package dependency as a runtime code loader.

At the checkpoint, `tools/lotus-v2-compiler/src/generic.ts` sets source size 65536, script bytes 8192, opcode count 4096, helper expansions 256 and methods 16 as compiler limits. Helper chains and parser control/expression nesting are bounded at 16, and loop nesting at two. Recursion rejects. Inference rejects both an active helper cycle and a chain reaching its depth limit with E0503 (“recursive helper”); emission separately enforces expansion/depth budgets with E0703. Thus the diagnostic alone does not prove a source cycle. These are current compiler boundaries, not a portable promise about another chain's execution limits or consensus requirements.

Repeated hashing, arithmetic or signature helpers are motivating source patterns: sharing source does not necessarily share emitted code. The existing `test/generic.test.mjs` compares helper versus direct-expression bytes and tests statement-helper expansion, recursive rejection and expansion limits. `test/packages.test.mjs` compares an imported statement helper with its flattened form. Local linked-library examples under `examples/packages/linked` motivate keeping reusable policy identity distinct from helper expansion. This is evidence of current language behavior, not evidence that a new call instruction is needed.

A small compilation-only observation was reproduced using Node `v26.10.0`, `npm ci --ignore-scripts`, `npm run build`, and `compileContract(source, { contract: 'C', bindings: {}, optimize: false })` at the checkpoint. Source template:

```text
function h(x: Bytes32): Bytes32 { return sha256(x); }
contract C { function m(x: Bytes32) { BODY } }
```

`BODY` is exactly N repetitions of `require(h(x) == x);`, separated by one space. The source begins with the helper and contract separated by one space. All three compilations report maximum stack items 3 and dynamic signature checks 0:

| N | Exact script hex | Script bytes / opcode count | Helper expansions |
| --- | --- | --- | --- |
| 1 | `007db84e7d9165794e` | 9 / 9 | 1 |
| 2 | `007db84e7d9165007db84e7d9165794e` | 16 / 16 | 2 |
| 4 | `007db84e7d9165007db84e7d9165007db84e7d9165007db84e7d9165794e` | 30 / 30 | 4 |

This synthetic hash-equality contract is illustrative compiler evidence, not an application authorization example. It was not executed in a VM or accepted as a transaction. The 7-byte increase per additional repetition includes the repeated requirement and stack operations; it is not a measurement of helper-call overhead alone. No `cu`, fee, execution time or memory saving was measured. Opcode count and script size cannot substitute for P05 accounting/enforcement charges. The generic compiler suite passed 18 tests; its optional reference VM portion explicitly reported that it was not run in that invocation.

## Questions for a separately scoped target investigation

A future investigation needs an exact chain, consensus revision/activation, interpreter commit, compiler revision and resource profile before making compatibility claims. A name such as “Bitcoin-like Script” does not identify semantics. The following are research deliverables, not approved implementation changes:

| Area | Evidence required for each prospective target |
| --- | --- |
| Source semantics | Map Boolean encoding, integer width/overflow, division and remainder, byte ordering, casts, equality, hashing and failure behavior against P03. Record operations with no exact equivalent as unsupported. Separate a restricted common language from explicit target-specific features. |
| Control and helper reuse | Test inlining growth with realistic call graphs, duplication and branching. Compare bounded specialization/inlining and source-level factoring under existing instructions. Any runtime-call alternative requires a separate protocol proposal covering parsing, call frames, stack isolation, depth, recursion, termination, success scan and static charging; it is outside this packet. |
| Policy and transaction model | Compare UTXO/account state, branch/path authorization, token conservation, successor ownership and authenticated introspection. A target lacking an obligation cannot silently accept an approximation. Retain the source, both emitted artifacts and both results for a disagreement. |
| ABI and signing | Specify argument serialization/order, integer canonicalization, key/signature profiles, signing modes, chain/domain separation, transaction/core IDs, script/leaf/root commitments, proofs and final-stack requirements. Separate portable intent from each target's signing request. Never reuse a Lotus signature message or root on the strength of a shared source name. |
| Artifact identity | Bind exact target/spec/activation and cost-profile digests with source/dependency/compiler/optimizer identities. Reject an artifact imported under an incompatible profile. Determine which source constructs and generated clients can be shared without weakening target checks. |
| Resources and costs | Measure script/witness/transaction size, expansion count, stack/element limits, executed and statically charged work, signature/hash work and fees at boundaries. For Lotus retain both frozen accounting and enforcement views under P05; another target may have different limits and charging units. Report hardware/time/memory separately from consensus units. |
| Independent verification | Use target-native validators plus an independent model with positive cases and single-mutation negatives. Record unsupported separately from rejected. Compare authorization obligations and state outcomes after target-specific instantiation/signing, rather than demanding identical bytes or roots. Include optimizer and budget-boundary cases. |

Read the entire [decision register](../lotus-v2/decisions.md) alongside P01–P06: encoding/signatures, commitments/state, VM semantics, header/mining, resources/parameters and issuance/time constrain different layers. Compiler portability cannot settle open network/profile decisions D10–D14, calibrate primitive costs, or establish daemon block acceptance.

## Classification and next evidence gate

The measured repetition is a compiler expansion observation. A rejected recursive or over-depth helper is a compiler limitation under the present language. Neither is a demonstrated consensus ambiguity. A differing VM result must first be classified as a compiler bug, validator bug, ambiguous rule or incorrect example using the compiler plan's retained-reproducer requirements. Adding runtime definitions/calls or changing the success scan would be a proposed protocol change requiring separate review.

Multi-chain compilation remains open research. The next evidence gate is a separately authorized, version-pinned comparison of a small representative corpus (payment, stateful successor policy, token transfer and repeated pure helpers), with exact source/bytes/profile identities and supported-stage results. It does not authorize lowering for issue 21, a new target selector, opcode assignment, fixture regeneration, or any Lotus consensus change.
