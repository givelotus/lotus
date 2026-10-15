# V2 compiler, ABI generator and contract test plan

October 14, 2026. Implementation roadmap with an initial working compiler; the language remains a draft. This complements [V2-01/V2-04/V2-07](../../daemon/docs/lotus-v2-implementation-plan.md), the [script ABI](../lotus-v2/script-abi.md), and the [worked contracts](../lotus-v2/examples/README.md). It is a tool for exercising the evolving protocol before genesis, not a reason to freeze the draft prematurely.

## Integrated prototype

The [compiler and gallery](../../tools/lotus-v2-compiler/examples/gallery/README.md) provide bound typed templates, multiple methods, pure helper inlining, hash builtins and cross-contract method/root commitments. The bounded optimizer repeats checked literal and stack rewrites to a fixed point; it remains conservative across control flow. Both client runtimes construct explicit multi-input spend/mint calls. Separate mint and mandatory transfer-rule trees produce a signed 1,000-unit issuance and a 700 + 250 transfer with a 50-unit burn. A compiled upgrade method checks sufficient old-token burns and guarded input reads. Root verification passed 44 compiler/runtime tests without skips and 41 reference tests, rebuilt the native fixture checker, and checked all five token invocations plus rejection cases. These checks cover the implemented subset, not all milestone requirements below. Stateful allowances, counters, delayed recovery, complete contextual validation and block connection remain open.

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
| ABI binding generator | Safe typed encoding and decoding; call/transaction planning | Validated artifact → Python and TypeScript bindings plus their shared runtime contract; Rust/Dart later |
| Execution harness | Independent verification and reproducible failures | Artifacts + scenario/parameter profile → traces, acceptance results, roots, costs and minimized regressions |

Start under `tools/lotus-v2-compiler/`, with a machine-readable schema and fixtures under that directory. Keep the existing independent evaluator in `tools/lotus-v2-reference/`. Do not generate node validation code from the compiler backend: sharing a bug must not count as independent agreement. A pinned opcode registry can be shared; implementations of encoding, execution and cost calculation need cross-checks.

**Maintainer-selected direction: TypeScript**, with a bundled Node CLI and a reusable compiler library. Use discriminated unions for the AST and typed stack IR, `bigint` for integer arithmetic with explicit target-width checks, and `Uint8Array` for exact bytes. Runtime validation is required for imported artifacts and all external inputs; TypeScript types alone establish no wire validity. Keep the dependency set small and locked. Normal compiler installation and generated TypeScript use must not require Python or a native Rust extension. No LLVM/native-code backend is needed: the target is Lotus bytecode.

Keep Python as an independent test/reference implementation and as one generated client target. **Python and TypeScript are equal first-release binding targets**, each with a contract-specific API and a small maintained runtime library generated/maintained against the same versioned ABI. The compiler does not run during every client call. Python is required only for the Python client and optional reference checks, not the compiler or TypeScript client. Changes in `~/repos/frank` require a separate scoped revision; this plan makes no changes there.

## Shared library packages and module imports

The compiler needs reusable, reviewable library packages. A contract author should be able to import a checked arithmetic helper, a token policy, or a standard signature utility once and share that source across contracts. This is a compiler/package feature: imported code is resolved and checked at build time, then inlined or compiled into ordinary P03 scripts. The VM gains no dynamic loader, runtime module lookup, or package authority.

Use Finch's language specification as the design reference for module boundaries: module identities come from paths relative to the owning package root; dependency roots come from the root project's manifest/lockfile; imports are explicit; package visibility differs from public visibility; and repeated imports share one immutable module identity. Finch's large language surface is not the Lotus language design, and its implementation is not a dependency.

The initial package model should have:

- A `lotus.toml` manifest naming the package, its source root, its exported library interface, and exact dependencies. A checked-in `lotus.lock` records each dependency's immutable source locator, version/revision, content digest, and resolved package root. Compilation consumes already-resolved files and performs no network access. A root-only local path override may support development, but is never inherited from a dependency.
- Stable module identity derived from `(package identity, normalized relative path)`. Reject path traversal, symlink escape, duplicate module identities, case/Unicode collisions, undeclared files, and source bytes whose digest disagrees with the lock. Do not guess modules through ambient include paths.
- Declaration-only `library` modules. Top-level executable statements and implicit initialization are forbidden. Exported declarations have explicit types and stable interface digests; private helpers remain visible only in their module, while package-scoped declarations can be shared within the package.
- Explicit imports with whole-module aliases, selective names, and renames. The eventual C-like surface can use syntax such as `import math::checked::{add as safeAdd};`; the import path identifies a module, while the manifest/lockfile decides which package owns that path. Exact spelling remains a language-design decision pending syntax fixtures.
- One parsed AST and one promise-scheduler job per immutable module identity. The scheduler resolves imported declarations and their transitive dependencies, deduplicates diamond imports, diagnoses missing/ambiguous/private symbols and cycles with source spans, and enforces graph and expansion limits.
- A sealed build graph in every artifact: root package/module identity, lockfile digest, direct and transitive module source digests, exported interface digests, compiler/optimizer version, target opcode/spec identity, and the compiled dependency graph. Two builds with the same manifest, lock, source bytes, compiler profile and options must produce byte-identical contract artifacts.

Imported pure functions may be specialized and inlined under existing expansion limits. Imported contract methods retain their own policy root and ABI; a caller that commits to one uses an explicit linked-contract artifact binding, so recompiling or upgrading the library cannot silently retarget the commitment. Package versions alone are insufficient provenance: artifacts bind exact source and interface digests. A dependency update that changes emitted bytecode, method roots, witness layout, or resource bounds is a deliberate contract rebuild and produces a visible diff.

**CABI-07 status (implemented in `tools/lotus-v2-compiler`, see its README section "Local packages and explicit imports").** `compilePackage(dir, ...)` (`src/packages.ts`) resolves a strict-TOML-subset `lotus.toml` and a canonical JSON `lotus.lock` from declared files and does not spawn git. A path-only graph writes `lotus-v2/package-lock/1`: per-file BLAKE3 domain-separated digests, a tree digest, the path locator and the resolved package root. A module path, a root `[replace]`, or a quoted import writes offline `lotus-v2/package-lock/2`, including the selected commit and git tree when the package came from git. `lotus-v2-package-fetch` is the only networked package command. The root-only path mechanism is the root manifest's `[sources]` table; `[replace]` is also root-only; dependency `[sources]` and `[replace]` are never inherited. Import syntax is `import ALIAS::module::path::{name, other as local};`, `import ALIAS::module::path as m;` (`m::name(...)`), and a quoted module selector (`"host/owner/repo@vX.Y.Z"`). A final `/vN` with N ≥ 2 is a major-version suffix and is a different module from v1. Branch names and `^` / `~` ranges resolve only through `lotus-v2-package-update`. `ALIAS` is a dependency alias or the keyword `package`; visibility is `function` / `contract` / `token` (module), `package` scoped, or `export` (only from modules listed in `exports`). Each module identity is parsed once and linked by one scheduler job; the diamond fixture (`examples/packages/diamond`) and `test/packages.test.mjs` cover renamed selective and alias imports, duplicate/builtin-shadowing names, private and package-scoped access, missing modules/symbols, unknown aliases, import cycles, lock digest mismatch until relock, traversal/absolute/symlink escapes, case/Unicode collisions, undeclared files and graph limits, all with file/span diagnostics. Deviation: the sealed build graph (`build`, `lotus-v2/build-graph/1`) is an optional schema-2 field emitted only by package builds; single-file `compileContract` artifacts are unchanged and byte-identical. Type errors while expanding an imported helper carry a span in that helper's file and a note at each call site. CABI-08 is implemented for local path libraries (compiler README, `examples/packages/linked`): an exported library contract or token is imported by name or module alias; `contract_root` / `leaf_hash` / `merkle_root` pin its bytecode; helpers stay inlined; `links` records the library tree digest and contract root; generated TypeScript/Python bindings dump that root and the method names. A semantic library byte changes the root after the lock is updated; a comment byte changes source and lock digests only; a stale lock fails. The Python reference VM executed the signed Escrow, Payer and Receiver calls in the CABI-08 test run. The current native `lotus_v2_vm_runner` argv CLI returned `U` on that CHECKSIG script because it has no signing context, so signed native execution was not performed. A proxy mirror, vanity-domain discovery, registries, trust policy and published-package compatibility remain planned. Branch and range selectors stay on `lotus-v2-package-update`.

Before CABI-07 the compiler only parsed one source string and shared helper declarations inside it; it had no module loader, import syntax, manifest, or lockfile. Add CABI-07 for deterministic package/module resolution and CABI-08 for end-to-end shared-library contracts, while preserving the current single-file API as a convenience wrapper over one in-memory module. CABI-07 acceptance requires a local multi-package fixture with a diamond dependency, a renamed selective import, duplicate and private-symbol rejection, cycle/missing-module diagnostics, lock/source digest mismatch rejection, path-escape rejection, deterministic artifact digests, and zero network access. CABI-08's local acceptance is two contracts through one versioned library, linked roots in the artifact and in the generated clients, a semantic dependency change that alters the contract root, and signed Python execution of that fixture. Signed native execution waits on a runner that can take a signing context. Do not claim published package-registry compatibility until a registry and trust policy are separately specified.

Proposed source shape (illustrative; package builds now accept this import form, while the single-file API rejects imports):

```lotus
import lotus_std::amounts::{checkedAdd as safeAdd};

contract Escrow<owner: PublicKey> {
    function spend(amount: Amount, signature: Signature) {
        require(safeAdd(amount, 1) > amount);
        require(checksig(signature, owner));
    }
}
```

`lotus_std` is a dependency alias declared by the consuming package manifest. The remaining path selects a module within that package. `checkedAdd` is exported by the library, imported under a local name, type checked at the call site and inlined under the existing helper-expansion budget. A library that exports a contract/policy is imported as a typed artifact; its exact source/interface digest and resulting root are pinned when another contract commits to it. This separation lets libraries share helpers while making consensus-visible commitments explicit.

The initial payment slice is implemented: real source parsing and type checks, bytecode/ABI emission, generated call construction, and an actual signed transaction under an explicit fixture profile. It must compare exact bytes and signing results with independent reference/native modules. Native modules cover framing/cryptography; the separate reference VM now also executes the gallery Payment, hashlock, helper and linked-commitment invocations. Neither establishes contextual or block validity. The first slice does not close all CABI-00–03 requirements.

## Finch specification influence and deliberately small scope

The maintainer identified `~/repos/finch-language-full-spec/` as a design reference and explicitly said its implementation is far from the specification. Use **`docs/language/SPECIFICATION.md`**, especially sections 2 (compilation), 11 (bounded compile-time evaluation), 13 (typed stack IR) and 16 (ABI separation), as inspiration. `FINCH_LANGUAGE_DESIGN.md` supplies rationale; do not infer implemented behavior, readiness or reusable compiler code from that repository.

Borrow these design principles:

- Preserve source spans through parsing, typed semantic construction and emitted bytecode. Verify stack heights/types at control-flow merges independently of the source frontend's claims.
- Separate parsed, typed, lowered and verified artifacts. Compiler verification establishes properties of emitted code; it never grants consensus validity or lets the daemon skip validation.
- Bind template values and specialize helpers at compile time. Begin with deterministic constants, bounded helper evaluation and simple typed generics; reject dependency cycles and expansion-budget exhaustion with useful source diagnostics.
- Keep exported method/type interfaces immutable and versioned. Generate Python and TypeScript from one resolved interface model rather than scrape source text or independently infer method signatures.
- Separate portable wire identity from host memory layout and programming-language representations. Finch's native ABI, operation selectors and message envelopes do not become Lotus consensus formats.

The initial contract language can be small: named methods, typed parameters/constants, local expressions, `require`, conditionals and bounded loops. A single familiar C/D-like surface is a proposed starting point for review, using the existing contract examples. Forth-like assembly remains the inspection/debugging representation. Multiple surface syntaxes, a general effect/ownership system, exceptions, coroutines, capabilities, runtime allocation, general reflection and hygienic macros are outside the first compiler. Typed stack effects and explicit transaction/state obligations provide the useful checks without reproducing the whole Finch language.

In particular, deterministic compile-time work gets fuel/output-size/instantiation limits and no ambient network, clock, random or filesystem access. If dependency files are supported, resolve only declared inputs and bind their content digests. Compile-time specialization must not silently unroll a large runtime enumeration and change code/resource requirements; emit an explicit cost/size report and require the same acceptance semantics.

Finch provenance: repository HEAD `15016224e74f00b750f08d429c589f4969dc06a3`, inspected read-only on October 14, 2026. The language specification's SHA-256 is `12629049f6e588e7df55fee0e93b7fc52704f6949ecb137efcac51f0867b347a`. No Finch implementation, tests or runtime were adopted or validated by this planning review.

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

The first release generates **both Python and TypeScript** with matching exact-atom and wire-corpus tests. Python maps integers to range-checked `int` (rejecting `bool` where an integer is required), byte values to `bytes`, and structured call/state values to generated typed dataclasses. TypeScript uses `bigint`, `Uint8Array`, generated interfaces and runtime checks; compile-time TypeScript types alone cannot validate network or JSON data. JSON export/import uses the artifact's canonical decimal/hex rules in both clients. Rust and Dart bindings may follow the same schema and corpus.

Generated files contain contract-specific types, constructor/method descriptions and thin typed wrappers. Small versioned runtime libraries own canonical value/witness encoding, profile compatibility, transaction planning, signature-request assembly and finalization; they reuse reviewed signing/crypto services instead of emitting a fresh cryptographic implementation per contract. Applications supply coins, network/profile and signing callbacks. Compilation or ABI import never reads wallet secrets, chooses a network or sends a transaction implicitly.

Each Python/TypeScript pair must reproduce identical constructor/script commitments, argument vectors, transaction bytes, TxID/TxHash and signing digests for the same fixture. Test signed/unsigned extrema, excess-width values, negative amounts, Boolean/int confusion, byte lengths, argument order, malformed artifact versions, partial signing and signature attachment. Also cross-consume fixtures: Python prepares and TypeScript finalizes, and vice versa. Generated APIs are source-language-specific conveniences over the same Lotus byte contract. A generated address is only available once D14's actual address/policy encoding is specified; early tools expose explicit policy descriptors instead of inventing an address standard.

## Milestones and acceptance

| ID | Deliverable | Dependencies | Acceptance gate |
| --- | --- | --- | --- |
| CABI-00 | Artifact/ABI schema, type model, CLI contract, TypeScript backend and small surface-language prototype | Current versioned P01–P03 draft and registry | Golden valid/invalid schema cases; reproducible canonical digest; unresolved semantics listed |
| CABI-01 | Assembler/disassembler and fixture runner | CABI-00, reference/native codec and hashes | Every assigned instruction and push boundary round-trips; canonical push bytes; source offsets; normal mode rejects success bytes; malformed inputs reject independently |
| CABI-02 | Minimal typed payment/recovery compiler | CABI-01, signing and minimum VM subset | Exact compiled ordinary payment + generated ABI; valid signature accepted, wrong signer/output/chain rejected; recovery before/after contextual lock boundary |
| CABI-03 | Python + TypeScript call bindings/runtime libraries and signed transaction workflow | CABI-00/02, transaction/signing APIs | Both generated clients cross-reproduce native/reference bytes and signatures; integer/argument/partial-mode cases; no private keys in artifacts |
| CABI-04 | Tokens, state and bounded covenants | CABI-02/03, needed VM/introspection and accounting | Execute mint/transfer rules, stateful counter, limit order, two-input merge and input × output loops; adversarial policy/state/asset substitutions reject |
| CABI-05 | Differential/property/fuzz and stress harness | CABI-01 onward, expanded as validator support lands | Deterministic corpora and minimized discrepancies; correct accept/reject/results/roots/charges across independent engines; recorded stress measurements |
| CABI-06 | Optimizer and application pilot | CABI-04/05, development-chain connect/undo | Optimized/unoptimized equivalence corpus; Frank application flow runs with generated bindings on disposable V2 chain; reorg/undo restores state |
| CABI-07 | Deterministic package manifests, lockfiles, module resolution and import visibility | Current compiler parser/scheduler and artifact schema | Local two-package diamond builds offline; alias/selective imports, visibility, ambiguity, cycles, digest mismatch and path escape cases; deterministic sealed module graph in artifacts. **Implemented** (package builds only; see status above) |
| CABI-08 | Shared contract libraries and dependency-aware ABI/client generation | CABI-07, CABI-03/04 | Two contracts consume one versioned library; generated TypeScript/Python bindings preserve linked contract roots; source update changes expected commitments; Python/native VM fixture execution. **Implemented for local path libraries** (see status above). A semantic source byte changes the linked root; comment-only bytes do not. Python executed the signed fixture. Signed native execution was not performed: the current runner has no signing context (`U`). Registries remain open. |

CABI-00/01 and CABI-07 can begin before consensus freeze or complete daemon integration. Schema/binding work and backend work can run independently after their interfaces are reviewed; the harness should start with the assembler and grow with supported features. Every behavior-changing draft revision increments the target profile and regenerates affected fixtures through explicit review. Final genesis pins a reviewed profile; it does not prevent earlier development.

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
2. **Binding worker:** begin after schema review; generate Python and TypeScript contract wrappers plus shared-runtime interfaces and call-plan types, test both against independent fixed wires and cross-language round trips. No production wallet integration yet.
3. **Compiler worker:** begin from the reviewed type/IR contract; implement CABI-02 payment and recovery lowering with stack checks and clear unsupported-feature diagnostics.
4. **Harness worker:** independent of backend; combine existing native/reference modules as they are reviewed, retain failure corpora and identify missing validator features explicitly.

Root review owns target/profile decisions, cross-component semantics and integration. Implementers must not silently change consensus to make a source example compile. A proposed spec change comes with the source example, emitted bytes, differing execution results and a focused regression. The TypeScript payment worker is dispatched; the remaining packets are dependency-ordered future work, not completed milestones.

## Spec feedback from executable contracts

Treat the source examples as hypotheses until their emitted bytes execute. Each disagreement must retain the source, compiler/target digests, exact bytecode and transaction, resolved test coins, signature messages, independent results, and a minimal reproducer. Classify it as a compiler bug, validator bug, ambiguous rule, or incorrect example before choosing a fix. A spec correction must update the relevant normative packet and independent regression; changing compiler output to match one implementation is insufficient. Keep acceptance results for framing, signatures, VM invocation, transaction accounting and block/state validation separate. The near-term goal is to progressively turn those stages green for one real payment, then expand the contract corpus.

## V2-native test fixture infrastructure

The compiler and generated clients are also test-development infrastructure. Transaction wire changes affect parser/serialization tests, signing, mempool admission, block assembly, RPC/indexer fixtures, wallet flows and functional-test transaction builders. Audit each suite's actual assumptions; arithmetic/cryptographic utilities and tests independent of transaction format may remain applicable. Do not mechanically replace expected bytes or disable rejection checks to make inherited fixtures pass.

Provide reusable, deterministic builders for payment first, then recovery, authorized mint/transfer, burn outputs and a small stateful covenant. Each builder takes explicit profile, coins, methods, arguments, outputs, locks and signing modes and returns the generated artifact, exact transaction bytes, signing requests/signatures and expected *supported-stage* results. Public fixture keys are explicit; no network or wall-clock dependence. A default fixture should be well-formed and signed, while tests name the specific mutation intended to invalidate it. Validity still depends on the actual stage under test.

Publish versioned offline JSON fixture bundles for C++ and Python functional tests. The TypeScript compiler runs during deliberate fixture generation, not inside consensus validation; daemon unit tests can consume checked-in bytes without requiring Node. Record source/profile/compiler identities and generation commands. Separate fixture generation from expectation verification: independent native/reference results and hand-encoded adversarial vectors remain required.

Track migration in four buckets: (1) reusable unchanged tests, (2) equivalent behavior with V2 builders, (3) retired legacy-only semantics with an explicit reason, and (4) new V2 semantics requiring new tests. Preserve the behavioral intent of migrated tests, including negative cases, fee/resource boundaries and reorg/undo. For each rejection test, first establish that the unmutated baseline passes the same validator, then apply one named mutation and assert the intended error. Legacy-network compatibility suites stay in V1; V2 tests must not claim compatibility with their transaction bytes.

The first Payment compiler candidate now emits real signed transaction bytes and ABI wrappers. It is awaiting root review and currently establishes framing/commitment/signature agreement only; VM, accounting and complete block acceptance are still required before its output can serve as an end-to-end valid-chain fixture. The immediate follow-on is to run that exact compiled payment through the VM and transaction validator, then use it in a mined development block and disconnect test.
