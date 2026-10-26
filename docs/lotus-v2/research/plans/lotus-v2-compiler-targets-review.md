# Compiler target semantics and entrypoint review

Research checkpoint: 2026-10-15, monorepo `cf5c473c`, on a new worktree created from `8914db5177d7b97fa7aa7d04172f71ead633775c` and fast-forward merged with `lotus-v2`. This file proposes compiler architecture; it does not implement a backend or change consensus. Latest user direction prioritizes Lotus V2 with eCash exercised alongside it. Subsequent implementation is authorized separately from this review.

The verified ticket is [#21, Research multi-chain script targets and non-function leaves](https://github.com/givelotus/lotus/issues/21), read through `gh issue view` on this date. This supersedes the earlier [research note](lotus-v2-issue21-research.md)'s statement that the issue body was unavailable. That ticket names limited Bitcoin tapscript as its first future external contract profile, BCH single-function scripts, and a distinct eCash profile. The present Lotus/eCash machinery slice does not claim to complete the entire ticket, nor silently replace its Bitcoin/BCH deliverables.

## Recommendation and current evidence

Use semantic operations, then explicit target validation and lowering. An opcode dictionary alone is unsafe. The same spelling can have different value encodings, authentication contexts, failure behavior and resource limits. Preserve the existing Lotus path while introducing a small, demonstrably portable byte/hash subset. Keep loops, reflection, integer arithmetic and transaction signatures target-specific until a mapping proves their meaning.

Current [generic.ts](../../../../tools/lotus-v2-compiler/src/generic.ts) hardcodes the P01–P03 artifact target, int128 types and Lotus opcode constants. [optimizer.ts](../../../../tools/lotus-v2-compiler/src/optimizer.ts) consumes already encoded instructions; it is a Lotus optimizer, not a portable IR optimizer. [transaction-runtime.ts](../../../../tools/lotus-v2-compiler/src/transaction-runtime.ts) is explicitly an offline P01 planner and labels signature/invocation/context/block stages unavailable. A bytecode artifact and a complete validated transaction are different deliverables.

CABI07 package resolution and CABI08 local libraries already exist. Pure helpers inline, recursion rejects, nesting is bounded, linked policy roots remain explicit. Reuse those mechanisms; do not redo them or add runtime calls. This compiler must never lower a construct to `OP_DEFINE` or `OP_INVOKE`. Do not confuse that prohibition with blindly scanning push payloads for byte values; instruction meaning belongs to the selected registry.

## Target descriptor and semantic IR

Proposed API, not current exports:

```text
resolveTarget(id, revision, activationProfile, policyProfile) -> TargetDescriptor
specialize(program, target, compileTimeBindings) -> SelectedProgram
checkCapabilities(SelectedProgram, TargetDescriptor) -> CheckedProgram | Diagnostics
lower(CheckedProgram, TargetDescriptor) -> ScriptArtifact | Diagnostics
prepareInvocation(ScriptArtifact, resolvedContext) -> InvocationPlan | Diagnostics
finalize(InvocationPlan, signatures, validationContext) -> TransactionResult | Diagnostics
```

A descriptor seals: chain/VM and exact implementation revision; consensus activation and script flags; optional relay-policy flags; opcode registry digest; typed operation rules and unavailable capabilities; entrypoint forms; push/number/Boolean codecs; stack completion; signature algorithms, key/operand encodings and sighash rules; transaction codec/identity; resource counters and limits; success/disabled-instruction behavior. Unknown revisions fail closed. Consensus-valid and standard-for-relay are distinct results. A revision containing an opcode enum is insufficient evidence that the instruction executes.

For eCash the researched implementation is exactly ABC `1fb7db17c176cdea8a2c60d887891589382ee4e3`, also the selected V2 upstream base. Do not call this a verified current network tip or use an implicit `latest`. The initial execution profile is the exact pinned `STANDARD_SCRIPT_VERIFY_FLAGS` plus explicitly added `SCRIPT_VERIFY_MINIMALIF`, with the resolved names/mask recorded by the native harness. The added flag is a compiler verification restriction, not a claim about the network default. The initial envelope is a direct locking script; P2SH wrapping is deferred. Lotus additionally seals the V2 patch-series/profile identity; the upstream commit alone does not identify its VM.

IR values carry semantic types: bounded byte strings, canonical Boolean, `LotusInt128`, target-specific ScriptNum, target-specific public key/signature, native amount with unit, target-specific transaction identity. Never alias all integers to `Int`, all keys to bytes, or all transaction IDs to interchangeable hashes. First portable nodes: byte literal, argument, SHA256, HASH256, byte equality, require, and Boolean conditional. Every node retains source span, argument bounds, failure preconditions and effect requirements. Conditional inputs derived from canonical comparisons need no arbitrary-byte truthiness conversion; caller Booleans require explicit canonical validation. Ordinary argument bytes are not implicitly Boolean or integer.

Target nodes include `LotusEnumerateOutputs`, `LotusBranchContinues`, `LotusCheckSigP01`, `EcashCheckSigForkId`, and later `BtcCheckSigTaproot`/`BchUntil`. Capability outcomes are `exact`, `bounded-emulation` (named recipe and preconditions), or `reject` with reason. There is no “supported” flag that forgets which case applies. Emulation requires explicit source/profile selection, a proved bound, correct malformed-input handling and target resource analysis. Specialization discards unselected target bodies before capability checking, but malformed syntax and unresolved package identities still reject. Selected helpers are checked transitively. Never choose a fallback body after a compile error.

Compile-time inputs include target/body, constructor values, loop maximum/encoding, dispatch method set, parent-transaction requirement, tree shape and leaf-splitting policy. Runtime values include actual arguments, method selector, parent bytes, signatures and transaction context. Artifact/cache identity includes all compile-time choices plus exact dependency digests. No runtime chain-ID branch substitutes for specialization.

## Opcode and feature matrix

Numbers below are hexadecimal instruction bytes, not portable bytecode. `—` means no direct lowering. Lotus assignments and stack types come from [P03](../../decisions/vm-semantics.md); eCash assignments/limits from its pinned [script.h](https://github.com/Bitcoin-ABC/bitcoin-abc/blob/1fb7db17c176cdea8a2c60d887891589382ee4e3/src/script/script.h). Bitcoin rules are [BIP342](https://github.com/bitcoin/bips/blob/master/bip-0342.mediawiki). BCH is a separately researched upgrade family, not an implemented target.

| Operation / stack contract | Lotus V2 | eCash pin | BTC tapscript | BCH profile |
| --- | --- | --- | --- | --- |
| SHA256: bytes → bytes32 | b8 | a8 | a8 | a8 |
| HASH256: bytes → bytes32 | b9 | aa | aa | aa |
| Byte equality: bytes,bytes → Bool | 91; N(0/1) | 87; empty/01 | 87; empty/01 | 87; empty/01 |
| Require: Bool → empty | 65 | 69 | 69 | 69 |
| IF / ELSE / ENDIF | 61/63/64; int128 Bool | 63/67/68; Script truthiness | 63/67/68; minimal IF operand | 63/67/68; profile Boolean rules |
| DROP / DUP / PICK | 79/7a/7d; int128 index | 75/76/79; ScriptNum index | 75/76/79; ScriptNum index | 75/76/79; ScriptNum index |
| True / false literals | 4e/00; sixteen bytes | 51/00; 01/empty | 51/00; 01/empty | 51/00; 01/empty |
| Transaction checksig: sig,key → Bool | bb; P01, x-only | ac; eCash encoding/message | ac; BIP340/BIP341 message | ac; BCH encoding/message |
| Checked Lotus int128 addition | 9e | — | — | — |
| Lotus input/output `for` | 67/68 … 6a | — | — | —; BCH BEGIN 65 / UNTIL 66 is a different loop |
| BLAKE3 / branch continuation / mint delta | Lotus capabilities | — | — | — |

The `0x65` collision is material: Lotus VERIFY, BCH BEGIN, and eCash VERIF. Opcode substitution would change control flow or reject. Push framing also differs: Lotus `4e` is ONE; legacy Script uses it as PUSHDATA4. A backend owns instruction decoding and pushes, not just named opcode values.

| Feature | Lotus existing path | eCash proposed scope | Classification and condition |
| --- | --- | --- | --- |
| Bounded bytes, hashes, equality, require | Implemented | First backend slice | Exact logical operations, target ABI adapters and item limits |
| Inlined pure helpers | Implemented | Reuse after checking selected body | Exact within expansion/resource bounds |
| Canonical Bool conditional | Implemented | First or immediate second slice | Exact for typed values; reject arbitrary-byte truthiness |
| Transaction authorization | P01 implementation | Deferred from hashlock slice | Separate algorithm/key/sighash types; no shared raw signature |
| Lotus Int and Amount arithmetic | Implemented subset | Reject | Narrowing changes accepted inputs and overflow behavior |
| Lotus reflected input/output loop | Implemented | Reject | No authenticated count/read equivalent demonstrated |
| Explicit bounded repetition over ABI data | Not an automatic rewrite | Later opt-in unrolling | Bounded emulation; checked count and bounds |
| Multi-method policy | Method leaves | Later dispatcher or separate outputs | Explicit ABI/policy change, not a leaf backend |
| Lotus tokens/branch requirements | Implemented subset | Reject | Application token conventions are not consensus equivalents |
| Parent transaction introspection | Separate possible operation | Reject initially | Authentication machinery is missing, not just parsing |

ABC's pinned [interpreter](https://github.com/Bitcoin-ABC/bitcoin-abc/blob/1fb7db17c176cdea8a2c60d887891589382ee4e3/src/script/interpreter.cpp) disables MUL despite its enum entry and counts non-push instructions in skipped branches. Its numeric width is eight bytes; Lotus is fixed-width int128. eCash has no BCH native introspection, CashTokens, or loop instructions at this pin. The proposed backend must enforce 520-byte elements, 10,000-byte scripts, 201 non-push operations and 1,000 stack items, with invocation-specific signature limits evaluated later. These are not Lotus's compiler caps.

BCH [May 2022](https://upgradespecs.bitcoincashnode.org/2022-05-15-upgrade/) introspection, [May 2023](https://upgradespecs.bitcoincashnode.org/2023-05-15-upgrade/) CashTokens, and [May 2026](https://upgradespecs.bitcoincashnode.org/2026-05-15-upgrade/) loop/function changes are separate upgrades. The [loop specification](https://github.com/bitjson/bch-loops) defines BEGIN/UNTIL, not Lotus counted enumeration. No exact BCH interpreter pin, executable flags profile or BCH validation was established here; BCH backend support remains unimplemented.

## Entrypoint, main and transaction ABI

`main` is a selected entrypoint name, not a consensus opcode or automatically runnable host function. Diagnose missing or ambiguous entrypoints. For initial eCash choose exactly one function, explicit argument names/types/order and a locking-script form; multiple public methods reject unless a named dispatcher profile is selected. Do not run the Lotus leaf/root builder and attach an eCash label. A bare locking-script artifact makes no claim that standard relay policy accepts it. A P2SH envelope is a separate artifact commitment and constrains the revealed redeem-script element size.

A script artifact contains target/profile digests, specialization, semantic feature outcomes, entrypoint identity, ordered ABI codecs and initial-stack layout, exact bytecode, final-stack requirements, source map and static resources. Encoders push arguments in a specified order; generated runtime and script access agree which is top. Scripts themselves validate security-relevant argument shape: caller bindings cannot enforce consensus. Clean success is one target-encoded true value with empty alternate stack. Extra arguments cannot remain silently accepted in a declared clean-stack profile.

Illustrative portable source intent (not new grammar): `main(preimage: Bytes32) { require(sha256(preimage) == expectedDigest); }`. Constructor digest is compile-time. Both targets can enforce the same 32-byte preimage predicate; Lotus and eCash push/stack/Boolean encodings differ. The eCash backend must check length in script, rather than trust its ABI client. Bad length, wrong digest and extra argument fail under the chosen entrypoint profile. This is a hashlock, not signer authorization.

A payment `require(checksig(sig, owner))` cannot be carried over by copying the same key/signature bytes. Lotus P01 and eCash signature verification commit different messages and accept different key/operand encodings. Explicit target bodies may express the same *intent* of owner-authorized payment, but require independent signature requests and target-specific rejection tests. A program depending on a raw P01 digest must reject on eCash. Likewise, `for output in tx.outputs` checking a successor branch rejects on eCash; deleting that check is not a translation.

Complete transaction construction requires resolved UTXOs and outpoints, chosen inputs/outputs and amounts, fees/change rules, version/sequence/locks, script envelopes, signing modes and network/activation context. Output script compilation alone supplies none of those. Expose prepare → inspect signing requests → attach signatures → finalize; never obtain secrets or sign during compile. Recompute after every committed-field mutation. eCash must use its transaction serialization and ordinary transaction ID; Lotus's stripped-core/full identity pair is not transferable. Final results report independent framing, signature, VM, accounting, contextual and relay checks as passed/failed/unavailable, never unconditional validity from compilation.

## Reflection and transformations

Candidate shared reads are version, input/output count, previous outpoint, native coin value, output value and locks. Lotus/BCH can describe some analogous reads, but width, native/token distinction, authentication and lock semantics differ. eCash provides no direct general reflection partner at the researched pin. Conclusion for the first Lotus/eCash profile: keep reflection target-specific; there is no useful shared transaction-loop syntax demonstrated.

A parent transaction supplies historical fields only after its hash is bound to an authenticated spending outpoint and the correct output index. A witness-provided hash equals another witness-provided hash proves nothing about the input. BCH native outpoint reflection can provide the anchor, subject to exact parsing and size limits. eCash would need a separately proven authenticated sighash-preimage construction or another mechanism; it is not an available general escape hatch. Parent bytes cannot reveal the spending transaction's output count, Lotus branch semantics or mint delta on a chain that has none. Restrict such a future recipe to fields actually present in the parent, reject malformed/oversized serialization and validate full hash and index binding. This is opt-in and currently rejected.

| Transform | Soundness requirement | Size / ABI consequence |
| --- | --- | --- |
| Conditional → two leaves | Each leaf rechecks its arm predicate; retain failure/evaluation semantics | Two committed leaves, separate identity/source span; opt-in |
| `require(a || b)` → alternatives | Preserve eager/short-circuit and error semantics; no dropping a failing evaluated operand | May reject transform even when Boolean truth tables agree |
| Threshold → satisfying-set leaves | Complete authorization-set analysis; malformed signature behavior preserved | Up to binomial(n,k) leaves; compare tapscript CHECKSIGADD separately |
| Length-specific leaves | Leaf k authenticates actual sequence length=k and pastes k bodies | Sum of pasted sizes is quadratic in maximum M; proofs/tree also grow |
| One script with skipped tail | Enforce 0≤count≤M, check authenticated sequence count where claimed | M pasted bodies plus guards; eCash skipped instructions still count |
| Method-name dispatcher | Exact accepted names; unknown name rejects; each arm checks its own policy | One script containing every arm; witness name is not a leaf commitment |
| Parent transaction argument | Authenticated outpoint, canonical parse and output index | Full parent plus parse code; target item/script limits can reject |

M+1 always rejects; truncating leaves elements unchecked. Include length zero only under an explicit source policy (recommended default: support empty sequences if source semantics permits them, otherwise reject zero). A nested pair or branch split multiplies leaf counts. ABI selectors map source method plus specialization to a distinct leaf ID and enforce its predicate on-chain; wallet choice alone is not enforcement. Store per-leaf target body/span, predicate, witness schema, commitment/proof and length-to-leaf mapping. No automatic splitting changes existing Lotus roots.

For future Bitcoin tapscript, [BIP341](https://github.com/bitcoin/bips/blob/master/bip-0341.mediawiki) makes internal-key/key-path authorization part of the output policy. Require an explicit decision: an authorized key-path spender or a reviewed construction intended to make it unavailable. Merely supplying an internal key does not enforce script-only spending. For BCH/eCash “one address with methods” means an explicitly selected single-script dispatcher/envelope, never an invented script Merkle tree. Preserve issue #21's limited tapscript-contract goal and BCH single-function counterpart as later profiles; neither backend exists from this research.

## Failure, cost and diagnostics

Logical output equality alone is insufficient. Preserve accepted argument domains, evaluation order, deterministic failure, signature messages and identity semantics. Costs are target-indexed: Lotus accounting/enforcement CU, eCash operation/stack/sigcheck limits, Bitcoin witness budgets and BCH density rules cannot be equated numerically. A valid bounded translation can have a different declared target cost; it must preserve the source's logical meaning and satisfy that target's limits. Reject explicit source requirements about a foreign cost model. Within one Lotus profile optimizations must preserve its accounting/enforcement semantics.

Proposed diagnostic codes (reserve before implementation):

- `T001 unknown-target-profile`: missing revision or unrecognized flags/activation.
- `T010 unsupported-capability`: operation and target, source span and helper expansion trace; e.g. Lotus output enumeration on eCash.
- `T011 incompatible-value-semantics`: int128 or signature message cannot be represented exactly; suggest an explicit target body, never silent narrowing.
- `T012 missing-authentication`: parent supplied without an authenticated outpoint.
- `T020 invalid-entrypoint`: missing/ambiguous main, unsupported method family or envelope.
- `T030 resource-bound`: named counter, bound, limit and source expansion responsible.
- `T040 missing-transaction-context`: list missing coins/outputs/flags for requested finalization; script compilation may still succeed independently.

Diagnostics and capability reports should be deterministic machine-readable objects with human-readable summaries. No bytecode returned as successful output after a capability error. Distinguish unsupported from unimplemented: a sound potential recipe is still unimplemented until executed against the target interpreter.

## Incremental implementation and ownership

The dispatched shared interface uses `TargetId = 'lotus-v2' | 'ecash'`, `resolveTarget(id)` and `checkCapabilities(descriptor, requirements)` from `targets.ts`. Requirements carry capability plus optional source span; diagnostics carry code/message/span/capability. Unknown target IDs throw before selection. The capabilities for the first portable slice are `bytes`, `bool`, `sha256`, `hash256`, `byte-equality`, `require`, and `if`. Chain-specific requirements have explicit keys and reject on the eCash slice.

`semantic-ir.ts` exports `SemanticProgram` (schema `lotus/semantic-ir/1`, selected entrypoint, ordered typed arguments, body and span), and `validateSemanticProgram(unknown)` returning `{ok: true, program, requirements}` or `{ok: false, diagnostics}`. Byte types have an exact `length` in this first slice; Bool is a separate type. Expression discriminants are `bytes` (hex), `bool` (value), `arg` (name), `sha256`/`hash256` (value expression), and `equal` (left/right). Statements are `require` (condition) and `if` (condition/then/otherwise). All nodes retain `{start, end, file?}` spans. Runtime validation checks imported objects, types, bounds, cycles and nesting before backend use.

`ecash.ts` exports `compileEcash(unknown)` returning `{ok: true, artifact}` or `{ok: false, diagnostics}`. The artifact uses `ecash/script-artifact/1`, target/revision/profile, entrypoint, ordered arguments, scriptHex, sourceMap and staticResources. Arguments are ordered bottom-to-top. `main` is conventional, not forced if a different function was explicitly selected. These interfaces were sent to the implementation workers; the root integrator owns adaptation of existing source syntax. Resource checks include both conditional arms for eCash opcode counts and the maximum path stack usage.

All paths below are relative to `tools/lotus-v2-compiler/`. These are proposed disjoint work packets for root integration, not implementation claims.

| Packet | Exclusive source/test ownership | Deliverable and dependency |
| --- | --- | --- |
| A: descriptors | `src/targets.ts`, `test/targets.test.mjs` | Versioned descriptors, operation classification, precise diagnostics; first |
| B: semantic boundary | `src/semantic-ir.ts`, `test/semantic-ir.test.mjs` | Byte/hash/Bool IR and explicit unsupported target nodes; agree A interface first |
| C: eCash backend | `src/ecash.ts`, `test/ecash.test.mjs` | Single-function hashlock subset, script ABI/shape enforcement, canonical pushes, limits; consumes A/B |
| D: integration, one owner | `src/generic.ts`, `src/generic-cli.ts`, `src/packages.ts`, `src/call-runtime.ts`, `package.json`, `test/target-integration.test.mjs` | Explicit selection/reporting, default Lotus preservation, distinct eCash artifact; after A/B/C |
| E: independent execution | `test/ecash-native/` (harness and fixtures) | Hand-encoded positive/negative vectors and pinned ABC interpreter results; no compiler source edits |

This review owns only this document. Existing unrelated files and compiler tests remain their current owners' responsibility. If the integrator discovers a shared edit requirement, reassign before editing. Do not broaden into transaction signing, generic arithmetic, loops, dispatchers or parent parsing while claiming to have completed C. No consensus/mailbox changes belong in these packets.

Minimum usable new eCash backend is a real one-function script artifact, not a target name attached to Lotus bytes. It can demonstrate SHA256/HASH256 preimage conditions and byte comparisons, typed conditionals if included, with inlined checked helpers. It rejects checksig, integers, reflection, loops, tokens and multiple methods until separately implemented. Existing Lotus compilation remains the primary path and must stay byte-for-byte stable, including package/link roots and optimization results.

Required acceptance: build/typecheck; descriptor rejection tests; same predicate against Lotus and pinned ABC for valid preimage, wrong digest, bad length, extra stack argument and both conditional arms; independent expected opcodes/push boundaries; limit failures including skipped branches; unchanged existing Lotus fixtures; selected-body tests proving no wrong-target operations leak. An interpreter availability failure must be reported as an unperformed gate. A small JavaScript evaluator that duplicates the emitter is not independent consensus validation. No live node, chain data, release, publication or target mainnet parameters are needed.

Next slices after this gate: target-specific signed eCash payment and transaction envelope with exact sighash vectors; then proven bounded ABI-data repetition; then issue #21's tapscript/BCH profiles and authenticated reflection research. Do not claim the hashlock slice already emits complete signed transactions or closes issue #21.
