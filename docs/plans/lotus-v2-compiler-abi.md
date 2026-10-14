# V2 compiler, ABI generator and contract test plan

October 14, 2026. Proposed implementation scope, not an implemented compiler or frozen language. This complements [V2-01/V2-04/V2-07](../../daemon/docs/lotus-v2-implementation-plan.md), the [script ABI](../lotus-v2/script-abi.md), and the [worked contracts](../lotus-v2/examples/README.md). It is a tool for exercising the evolving protocol before genesis, not a reason to freeze the draft prematurely.

## First useful outcome

Compile an ordinary-payment contract, generate a typed call builder, construct and sign a transaction from explicit fixture coins, and run its actual bytes through independent reference and native validation. Emit a reproducible artifact containing the source-to-byte mapping, exact commitments and signing messages, result and costs. Follow with recovery, mint/transfer rules, a stateful counter, limit orders, and two-input merge contracts.

Compiler success does not establish transaction validity. The validator executes bytecode independently and enforces contextual locks, conservation, fees and state transitions. Until that validator slice exists, a test must report the narrower stage it passed: assembly, framing, signature verification or invocation execution. A daemon-accepted block and correct disconnect remain the end-to-end gate.

## Components and ownership boundaries

| Component | Responsibility | Inputs and outputs |
| --- | --- | --- |
| Assembler/disassembler | Exact P03 encodings; readable stack-level inspection | Symbolic instructions and typed literals ↔ canonical bytecode, byte offsets and diagnostics |
| Typed frontend | Source grammar, types, ownership of state transitions, bounded control flow | Source + bound template parameters → typed intermediate representation (IR) |
| Compiler backend | Stack layout, opcode lowering, script-method emission | Typed IR → scripts, source maps, static resource report and diagnostics |
| Policy/artifact builder | Method trees, branch/path layout, constructor dependencies and ABI | Scripts + explicit policy construction → versioned artifact, roots and proofs |
| ABI binding generator | Safe typed encoding and decoding; call/transaction planning | Validated artifact → TypeScript first, followed by Rust/Dart bindings |
| Execution harness | Independent verification and reproducible failures | Artifacts + scenario/parameter profile → traces, acceptance results, roots, costs and minimized regressions |

Start under `tools/lotus-v2-compiler/`, with a machine-readable schema and fixtures under that directory. Keep the existing independent evaluator in `tools/lotus-v2-reference/`. Do not generate node validation code from the compiler backend: sharing a bug must not count as independent agreement. A pinned opcode registry can be shared; implementations of encoding, execution and cost calculation need cross-checks.

Use a small Python assembler/CLI first to reach executable examples quickly and interface with the current reference. Select the typed frontend/backend implementation language in CABI-00 after a bounded prototype; the artifact and CLI contracts must not depend on Python object serialization. TypeScript bindings target the maintained Frank/Nakamoto application stack, but changes in `~/repos/frank` need a separate scoped implementation and revision record. This plan makes no changes in that repository.

## Versioned ABI and artifact contract

The first deliverable is a schema with golden valid/invalid artifacts, not only an example JSON file. Separate the reusable compiled template, a concrete deployment/policy instance, and a transaction invocation/result: compiling a template does not yet determine a TxID, signature or UTXO root.

A compiled artifact records:

- Schema version; compiler version/source revision; exact source content and dependency digests; target P01–P06/opcode-registry identities; supported feature set; optimization settings; explicit parameter/cost-profile digest where relevant.
- Constructor parameters, public methods, argument names/types/order, invocation kind and permitted signing modes. Method names are tooling identifiers: consensus selects a revealed script and proof, not a numeric method selector.
- Exact script bytes, typed constants, leaf hashes, deterministic tree construction recipe and membership proofs. Name-to-leaf mapping must remain explicit even if methods compile to identical bytes; either diagnose duplicates or define tooling alias behavior without inventing consensus-distinct leaves.
- Exact branch ordering and output path lists; token identity and mint policy kept separate from spend/rules trees. A branch root alone is insufficient to reconstruct a multi-branch output policy. State schemas describe real byte encodings or branch commitments, not a fictitious dedicated state field.
- Source maps from byte offsets to source spans and IR operations, generated instruction ownership, and diagnostics for stack/types/costs. Offsets refer to the emitted script before any visualization or annotation.
- Resource results: byte sizes and structural/static bounds, required contextual inputs, profile identity, accounting and enforcement views when applicable, and which parts remain unknown until invocation or transaction construction. Do not label a symbolic upper bound an observed execution cost.

An invocation/result artifact additionally binds resolved coins, input/branch/path selections, actual arguments and proof bytes, unsigned transaction plan, completed core/full transaction bytes, both identities, signing selectors/preimages/digests and public test signatures, resource charges, final stacks, and pre/post-state roots when that execution layer exists. Private keys never belong in published artifacts; deterministic public test keys must be visibly marked as fixtures.

Canonical JSON rules must be explicit: byte strings use lowercase even-length hex, large integers use canonical decimal strings, duplicate keys reject, and schema versions reject unsupported interpretations. Define canonical serialization for any artifact digest, exclude its own digest field, and keep tooling digests outside consensus hash domains. Reject incompatible target profiles; never reinterpret old artifacts using the newest opcode table.

ABI values distinguish signed int128, unsigned 128-bit limbs, native atom amounts, token amounts, Boolean, bytes with length bounds, hashes, x-only keys and signature operands. JavaScript bindings use `bigint` or validated decimal strings, never IEEE-754 numbers for amounts/int128. Numbers are encoded as P03's exact sixteen bytes where required; output amounts remain u64. Signature arguments follow P01's 64/65-byte mode encoding and are distinct from ordinary bytes. Mint delta is an injected context value, not an extra caller argument.

## Language and lowering boundaries

Treat existing contract examples as design input, not an already accepted grammar. CABI-02 publishes a small grammar and type rules before translating those examples.

Initial language features: compile-time template parameters, typed immutable locals, byte/numeric operations, `require`, conditionals, bounded input/output enumeration, generic bounded enumeration, helper inlining and public methods. No recursion, unbounded loops, heap model, dynamic code loading or implicit host-language arithmetic. Signed overflow, division rounding, numeric conversion and Boolean encoding follow P03 exactly; implicit Bitcoin ScriptNum conversions are forbidden. Compiler errors should identify unsupported syntax rather than emit approximately equivalent code.

Lower methods independently to script leaves, with clean main/alternate stacks on ordinary success. A stack-effect checker validates IR and emitted control structure. Emit only assigned opcodes by default. Unassigned success instructions require a conspicuous experimental target/assembly mode; normal contract compilation and generated wallets reject them because they provide no authorization protection.

Constructors are fully bound before roots exist. Compile-time references to other contracts form an acyclic dependency graph; diagnose cycles instead of searching for hash fixed points. `this.root` uses the defined runtime branch-root operation. Deterministic method-tree shape, ordering and duplicate handling are part of the tooling artifact version, while P02 owns the consensus hash/proof algorithms.

Stateful methods must explicitly declare continuation or termination. Lower continuation to checks of successor asset, value constraints, state, branches and paths; prove that every accepted successor preserves the declared policy. Pairing/merge syntax must specify input/output roles so two inputs cannot both claim an inadequately constrained successor. Do not resurrect the archived Master/Companion optimization: each required branch validates its own obligations, and another invocation's successful execution is not introspectable.

Locks compile to the supported transaction-relative/absolute lock constraints. There is no block-height/time/global-state introspection. Reject source constructs that imply expiry or automatic cancellation without spending the relevant input. Side effects must be explicit transaction outputs and burns; a compiler cannot make consensus execute a transfer hidden in an application call.

Optimization is a later gate. Initially preserve straightforward lowering and retain an unoptimized mode. Transformations must preserve acceptance/rejection, stack effects and accounting/enforcement semantics under the exact profile; equal outputs alone are insufficient. Never optimize across success-scan behavior by assuming an unassigned opcode is an ordinary no-op.

## Binding generation and signing flow

Generated APIs have separate operations to instantiate a policy, prepare a call, describe signing intent, attach signatures and finalize canonical bytes. They must not contact an RPC endpoint or sign implicitly during compilation. Wallet/key management stays outside the generator.

Call preparation requires explicit input coins, output intents, assets, locks, selected methods/paths and signing modes. It verifies local ABI shape and produces an inspectable plan. Return signature requests with ChainID, input/branch selection, script leaf, mode and exact digest. Recompute commitments after any relevant mutation; argument attachment may leave TxID unchanged while changing TxHash. CoinbaseData is an opaque, core-committed special case and must never be passed through ordinary method-argument stripping.

Partial signatures must show exactly which other inputs or outputs may change. SINGLE without a corresponding output rejects. Fee estimation must include actual argument/signature/proof bytes and coinbase/block requirements where applicable; P05 parameterized bounds are not a fee oracle. Finalization must validate the final complete bytes against the chosen profile and report unavailable contextual checks, not return a misleading unconditional `valid=true`.

The first binding target is TypeScript, with exact-atom types and fixture tests. Rust and Dart follow the same schema and wire corpus. A generated address is only available once D14's actual address/policy encoding is specified; early tools expose explicit policy descriptors instead of inventing an address standard.

## Milestones and acceptance

| ID | Deliverable | Dependencies | Acceptance gate |
| --- | --- | --- | --- |
| CABI-00 | Artifact/ABI schema, type model, CLI contract, language prototype decision | Current versioned P01–P03 draft and registry | Golden valid/invalid schema cases; reproducible canonical digest; unresolved semantics listed |
| CABI-01 | Assembler/disassembler and fixture runner | CABI-00, reference/native codec and hashes | Every assigned instruction and push boundary round-trips; canonical push bytes; source offsets; normal mode rejects success bytes; malformed inputs reject independently |
| CABI-02 | Minimal typed payment/recovery compiler | CABI-01, signing and minimum VM subset | Exact compiled ordinary payment + generated ABI; valid signature accepted, wrong signer/output/chain rejected; recovery before/after contextual lock boundary |
| CABI-03 | TypeScript call bindings and signed transaction workflow | CABI-00/02, transaction/signing APIs | Generated calls reproduce native/reference bytes; integer/argument/partial-signature mutation cases; no private keys in artifacts |
| CABI-04 | Tokens, state and bounded covenants | CABI-02/03, needed VM/introspection and accounting | Execute mint/transfer rules, stateful counter, limit order, two-input merge and input × output loops; adversarial policy/state/asset substitutions reject |
| CABI-05 | Differential/property/fuzz and stress harness | CABI-01 onward, expanded as validator support lands | Deterministic corpora and minimized discrepancies; correct accept/reject/results/roots/charges across independent engines; recorded stress measurements |
| CABI-06 | Optimizer and application pilot | CABI-04/05, development-chain connect/undo | Optimized/unoptimized equivalence corpus; Frank application flow runs with generated bindings on disposable V2 chain; reorg/undo restores state |

CABI-00/01 can begin before consensus freeze or complete daemon integration. Schema/binding work and backend work can run independently after their interfaces are reviewed; the harness should start with the assembler and grow with supported features. Every behavior-changing draft revision increments the target profile and regenerates affected fixtures through explicit review. Final genesis pins a reviewed profile; it does not prevent earlier development.

## Dogfooding and stress corpus

Use the worked examples as a traceable requirements matrix, not only happy-path demos:

| Scenario | Adversarial checks and measurements |
| --- | --- |
| Payment and recovery | Wrong key/chain/mode, argument order, stale outputs, malformed signatures, maturity and lock boundaries |
| Token mint/transfer | Forged mint context, wrong token/rules roots, unauthorized additional mint, token/native conservation and token-output burn |
| Counter/vault/state transition | Changed state schema/root, missing continuation, weaker successor paths, asset swap, incorrect value, unauthorized termination |
| Limit order and merge | Output index substitution, duplicate successor claims, partial fill arithmetic, wrong counterpart, witness mutation under partial signatures |
| Merkle collections | Odd/power-of-two tree sizes, repeated leaves, proof order/depth/canonicality, nonmembership, cross-domain substitutions |
| Enumeration and costs | Input/output Cartesian products, maximum nested bounds, BREAK paths, stack growth, worst-case byte lengths and static-bound versus observed abstract charge |
| Block execution | Coinbase data/reward mutations, mixed mint/burn/covenant workloads, atomic rejection, connect/disconnect, restart and exact state-root restoration |

Generate both valid typed programs and invalid byte-level mutations. Compare the unoptimized frontend/IR semantics, reference VM and native validator, recording where the test only has two engines or shares a cryptographic dependency. Compiler-generated tests must be complemented by hand-built and independently generated bytecode so a compiler bug cannot hide a validator bug. A mismatch is retained and minimized; never regenerate golden expected results automatically to turn a failure green.

Fuzz boundaries include source parsing, ABI deserialization, integer/bytes codecs, push framing, script syntax, witness construction, proof generation and signature attachment. Run resource-bounded fuzzers in isolated processes and retain seeds/reproducers. Stress reports record exact source/profile/device, cold/warm behavior, input/output/branch/argument sizes, wall time, memory, CPU/GPU work where relevant and abstract charges. Throughput or cost-safety claims need those measurements; compiler acceptance is no proof of a resource bound.

## First dispatch packets

1. **Schema and assembler worker:** CABI-00/01 only, new tooling files; generate Payment assembly and ABI fixture without claiming execution.
2. **Binding worker:** begin after schema review; generate exact TypeScript value codecs and call-plan types, test against independent fixed wires. No production wallet integration yet.
3. **Compiler worker:** begin from the reviewed type/IR contract; implement CABI-02 payment and recovery lowering with stack checks and clear unsupported-feature diagnostics.
4. **Harness worker:** independent of backend; combine existing native/reference modules as they are reviewed, retain failure corpora and identify missing validator features explicitly.

Root review owns target/profile decisions, cross-component semantics and integration. Implementers must not silently change consensus to make a source example compile. A proposed spec change comes with the source example, emitted bytes, differing execution results and a focused regression. This plan scopes the compiler work; it does not mark these packets dispatched or implemented.
