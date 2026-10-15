# Lotus V2 language composition and EVM conversion work

Status: **review candidate, 2026-10-15**. This document scopes implementation following review; it does not freeze language or production consensus. Baseline: `9939ab0d881ce9f1791546a0dc57b1e9580cf835`. Specification: [LC-1](../lotus-v2/script-abi.md#composition-proposal-lc-1-not-implemented). Behavioral conversion corpus: [EVM porting](../lotus-v2/examples/evm-porting/README.md). Monetary policy and the absolute genesis-anchored reward formula are unchanged.

## Design decision record

1. Preserve existing schema-2 programs, CABI-07 locks/imports, CABI-08 links and explicit compiler targets. Add a new language version and companion policy artifact; do not reinterpret old source or artifacts.
2. Separate source template, bound program, complete output policy and live outpoint. Add explicit spend `entry` and token `mint`; free helpers remain inline and acyclic. Package visibility is unrelated to on-chain authorization.
3. Give branches explicit stable numeric slots and names. Give paths names and explicit AND branch lists; the path set is OR. Canonicalize numeric paths, retaining named-to-wire mappings; never derive slots, mint identity or deployment from source/import order.
4. Make state authentication, output slots, successor preservation and terminal effects explicit. The builder checks plans and scripts enforce the actual transaction. No hidden cross-branch call, implicit absorbed leaf or global mutable state.
5. Authenticate mint/supply authority with a uniquely seeded controller and explicit enrollment, breaking circular root dependencies. Distinguish lifetime issuance limits from outstanding-supply caps.
6. Implement safe Lotus behavior first. Report expiry, callbacks, proxy address/storage and TWAP differences as semantic differences, not as compiler bugs or automatic reasons to extend consensus.

## Scoped implementation tickets

Owners below are file responsibility roles for the root integrator to assign; they are not authorization to edit other agents' worktrees. Land independent changes on isolated branches with exact-base evidence, then integrate centrally.

| ID / owner | Files expected to change | Dependencies | Required acceptance evidence |
| --- | --- | --- | --- |
| LC01 frontend maintainer | `tools/lotus-v2-compiler/src/generic.ts`, parser/types/diagnostics tests | none | Preserve original `<=` failure; fix Int/Amount comparison lowering with boundary and invalid-type cases; optimizer-on/off reference execution agrees |
| LC02 language owner | parser/types and package interface/build model under compiler `src/`; source fixtures | LC01 | Version-gated `entry`/`mint`; unmarked method rejects in LC-1; legacy artifacts byte-identical; private/helper/import changes cannot add a leaf; current helper depth 16/cycles still enforced |
| LC03 policy/SDK owner | new compiler policy module/schema; TS/Python builder peers and tests | LC02 | Exact slots/names/paths, duplicate root/path/data-slot rejection, all declaration/import permutations wire-identical; named witness order matches C10; mint independent of output slots; 16-branch/path bounds |
| LC04 linker owner | `src/packages.ts`, generic instance resolver, artifact provenance and bindings | LC02–03 | Two bindings of one imported template coexist; canonical DAG detects alias cycles; incomplete/surplus bindings reject; CABI-07/08 legacy graph/artifact tests unchanged; compile has no network/deploy effect |
| LC05 state/library owner | new canonical codec/map/state libraries, lowering and generated clients | LC03–04 | Both P02 state layouts authenticate old state and exact successors; inline proof ties active method to methods subtree; separate state-slot updates preserve every other root/path; forged state and singleton counterfeit tests |
| LC06 transaction SDK owner | TS/Python transaction planner and output-role layer | LC03, LC05 | Distinct roles and injective payout allocation; checked index bounds; full/partial signing scope explicit; no reordering after signing; two-input one-payout attack rejected on chain, not only by builder |
| LC07 math/crypto library owner | typed hash/data-signature/limb bindings; standard libraries | LC02 | DIV/MOD, explicit CHECKDATASIG profiles, bytes codecs and wide math lower to assigned opcodes; uint64 product boundaries and rounding; proof resource limits; no new opcodes; eCash target rejects unsupported features |
| LC08 token/app owner | executable ERC20/NFT/allowance/permit examples and fixtures | LC04–07 | One-time seed, enrollment, cap variants, burn/remint, mixed mint+explicit burn, revocation, per-NFT uniqueness and approval reset; nonce replay and wrong-domain failures; concrete congestion/cost report |
| LC09 controls/markets owner | executable threshold/vesting/order/pool/migration examples | LC05–08 | Multi-output collisions, lock context, rounding, malicious reserves, LP issuance/burn coupling, migration invariants; documented unsupported features remain rejected |
| LC10 indexer/client owner | application metadata/indexer schema and SDK query adapters, separate from compiler | LC08–09 | Supply/owner/order/pool state reconstructed from authenticated transitions, independent replay and reorg/undo tests; transaction retrieval supplies data availability required by proofs |
| LC11 validator/evidence owner | reference/native conformance fixtures and isolated node tests | each ticket's emitted bytes | Preserve source+artifact+transaction+engine outcome for each positive/negative case; independently execute all required branches; exact-byte TS/Python parity; transaction accounting, context and connected-block stages reported separately |

LC02–04 can precede the full state library. LC07 arithmetic/crypto and policy work can be separately assigned after review. No ticket authorizes modifying economic parameters, production workspace, published assets, opcode allocation or native consensus rules. Root remains the sole integration owner.

## Artifact and language acceptance details

`policy-artifact/1` wraps explicit branch/path metadata over existing program artifacts. It must not let a program root masquerade as a full policy. New module interfaces need a versioned digest including invocation kind and effect/state ABI; changing interface hashing must not silently rewrite old CABI-07/08 digests. Parameter objects bind by name; serialization and output slots are specified, not dependent on JavaScript object order. Program instance cache keys include target/profile, compiler/optimizer, locked package identity, fully bound values and linked program roots.

Each generated call records selected path name/index, every required branch name/index/root, selected method/leaf/proof, argument order, node-pushed mint delta and signing request keys. Invalid state/proof/argument widths reject at the boundary and remain enforced in emitted code. Runtime type brands are compile-time help only; artifact loading must validate their bytes. No implicit casts from Bytes32/TokenId to code roots or policies.

Library optimizations must preserve error behavior, short-circuit guards, ordinary final-stack rules and context completeness. Unknown opcode bytes are not used as feature probes: an emitted OP_SUCCESS can authorize an invocation. Bytecodes `89`/`8a` retain SPLIT/NUM2BIN. Every supported target has an explicit capability check; source acceptance on Lotus does not imply eCash support.

## Opcode and transaction change recommendations

| Pressure from the conversions | Existing expression route | Recommendation and decision gate |
| --- | --- | --- |
| Named OR/AND paths, explicit entries, helper imports | Existing roots, paths, scripts, proofs | Frontend/ABI only; no consensus change |
| Separate state-slot continuation | Bounded branch/path comparison or exact serialized output comparison | Implement library/lowering first; measure charged cost before proposing a convenience opcode |
| Stateful caps, allowances, collections and revocation | Consumed singleton controllers, mandatory rules, Merkle maps | Library/SDK/indexer work; shared-state contention is explicit |
| Wide AMM/vesting math | MUL128_WIDE, carry/borrow, fixed-bound arithmetic algorithms | Add typed library bindings and vectors; do not guess a new math opcode from source inconvenience |
| Ethereum typed-data compatibility | Custom signature protocol works; native Keccak/address recovery absent | Not required for Lotus permit. Exact byte compatibility needs separately justified crypto work and independent vectors; no allocation proposed |
| Automatic upper expiry or block-time TWAP | No equivalent under C22a; lower locks are only lower bounds | Preserve documented semantic difference. A contrary validity rule needs explicit consensus review, not an emulation label |
| Runtime CALL/DELEGATECALL/callbacks | Atomic transaction with independent covenants and approved effects | No new call opcode. Require a concrete protocol impossible to express safely within bounded existing transactions before considering execution-model changes |
| Read-only global/shared state | Consume/recreate authority or provide authenticated signed evidence | Preserve C13. Any proposed reference input must separately address authorization, concurrency and state-root dependence |

No current conversion proves a new opcode or transaction encoding necessary for the narrower Lotus applications. This is not proof that every EVM contract is expressible. Byte-size/cost measurements and adversarial compiled protocols remain prerequisites for claiming complete coverage.

## Evidence from this design branch

All commands ran in `/private/tmp/lotus-v2-language-astra-20261015`; compiler/reference files were read-only. `npm ci --ignore-scripts` and `npm run build` succeeded. Python 3.13 with checked-in requirements succeeded; Python 3.14 coincurve installation failed on cffi LICENSE metadata, so no 3.14 result is claimed.

`LOTUS_V2_PYTHON=/private/tmp/lotus-v2-language-astra-py313-20261015/bin/python node docs/lotus-v2/examples/evm-porting/run.mjs /private/tmp/lotus-v2-language-evidence-review-20261015` reproduced [5 artifacts, 16 invocations and 5 frontend rejections](../lotus-v2/examples/evm-porting/evidence/summary.json). Nine invocations accepted and seven rejected as expected. Threshold/escrow/mint contexts come from complete transaction bytes; the AMM kernel uses supplied integers. Checked-in cases retain bytecode, arguments, full transaction bytes where used, explicit profile, engine final stack/error and exit status. Costs are illustrative, and node outpoint resolution, contextual maturity/height, complete accounting and block connection were not performed by this runner. The runner now requires a new directory and records future successful frontend probes separately, preserving these original failure artifacts.

`LOTUS_V2_PYTHON=... node --test test/linked-libraries.test.mjs test/transaction-runtime.test.mjs` from `tools/lotus-v2-compiler` passed **10/10**. Python signed Escrow/Payer/Receiver invocations accepted; signature and wrong-root mutations rejected. Native signed execution was explicitly unavailable (`LOTUS_V2_NATIVE_VM` unset), even though the test's combined title mentions native contexts. TS/Python transaction planners matched mint/transfer bytes and selectors.

The unmodified baseline compiler rejects `delta <= limit` after successful parse/inference. Its original source and `E0403` diagnostic remain in [frontend-gaps.json](../lotus-v2/examples/evm-porting/evidence/frontend-gaps.json); the working demonstration spells the same comparison `limit >= delta`. This is a compiler bug separate from the cap design. The other frontend failures are intentional unsupported syntax/features. No failure was fixed by modifying consensus, regenerating an upstream golden, or claiming skipped native/block stages passed.

## Adjacent specification corrections for the integrator

P03's opcode table and compiler assign `OUTPUTCONTINUESBRANCH` to `ea`, but two explanatory paragraphs still say `cf`; `cf` is CHAINID. Correct those prose references in `docs/lotus-v2/decisions/vm-semantics.md` separately. Existing gallery prose also says relative locks are unimplemented despite the current `check_sequence` frontend; verify its exact runtime/context scope before updating. These files are outside this design branch's ownership.

## Bootstrap review correction and parallel interface boundary

The first ERC20 sketch incorrectly bound `SupplyController<authority: TokenId>` while the authority mint committed to that controller's initial code/policy. That creates a compile-time cycle. The corrected controller omits its own authority ID, reads the consumed asset/quantity and preserves them; dependent mint/rules programs bind and verify the expected external authority. Pool controller code likewise omits its authority ID and downstream reserve/LP commitments. [Acyclic graphs and negative counterexamples](../lotus-v2/examples/evm-porting/bootstrap.md) now specify compilation and initialization order, including Unassigned/Uninitialized state and pool Ready-to-Active first funding. These are reviewed-design obligations, not additional executed protocol tests.

**LC02 and LC03 interfaces are stable for parallel implementation:** versioned `entry`/`mint`, invocation-kind guards, explicit branch slots, named OR-of-AND paths, companion `policy-artifact/1`, named witness ordering and existing schema-2/CABI-07/08 preservation do not change. This correction changes application constructor bindings and later LC05/LC08/LC09 state/bootstrap implementations. LC04 must continue rejecting all root-dependency cycles, including those routed through constructor-bound initial-state hashes. Neither root cycles nor external authority authentication may be delegated to declaration order or a client-only assertion. The original 16-case VM evidence is unchanged and does not cover bootstrap.
