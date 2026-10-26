# Script and wallet ABI

Status: review draft, derived from [consensus C04–C25](consensus.md). P01 and P03 now specify candidate signing bytes and opcode semantics; their independent conformance evidence is still pending. This is not a compiler release or a promise of CashScript bytecode compatibility.

## Invocation boundary

| Item | Proposed contract |
| --- | --- |
| Script selection | Spending input selects one committed path; witnesses correspond exactly to its branch indices |
| Method selection | Revealed script plus unordered membership proof selects a leaf; no numeric method index in consensus |
| Arguments | Count followed by length-prefixed byte strings; wire order is bottom-to-top, last argument on top |
| Initial machine | Fresh main stack, empty alternate stack, no shared mutable branch state. In a mint, the node pushes the mint delta above the arguments |
| Numeric operand | 16..1,024 bytes (16-byte int128 baseline up to 8,192-bit big-int; wide products up to 2,048 bytes), signed two's complement, little-endian; no implicit Bitcoin ScriptNum conversion |
| Boolean | Exactly 16-byte int128 zero or one; Boolean consumers reject other values in this draft |
| Bytes | Remain bytes until an explicit opcode interprets them; hashes, keys and signatures are not int128 values |
| Success | Ordinary execution: exactly one Boolean true on main stack, empty alternate stack. An unassigned OP_SUCCESS_N instead succeeds for the whole invocation during P03's scan, after outer witness/proof checks |
| Failure | Invalid encoding/type/range/index, overflow, division by zero, unmatched structure, resource excess, or false result rejects under ordinary execution; P03 defines the success-scan exception |
| State | Not a separate output field. Data or Merkle roots are stored in `branches` in three ways (P02): (1) a data leaf inside the executing branch tree (`BranchNode(DataLeaf, M)`) enforced with `OUTPUTCONTINUESBRANCH` or `OUTPUTEXCLUSIVEBRANCH`, (2) a dedicated unexecuted data branch on a spendable coin (`branches=[CodeRoot, StateMerkleRoot]`, `paths=[[0]]`) read with `UTXOBRANCH`/`OUTPUTBRANCH`, or (3) a pruneable `IS_BURN` (`0x02`/`0x03`) output with `paths=[]` and up to 16 32-byte commitment words/roots. Internal sets and maps use `MERKLEROOT_SORTED` and `MERKLEROOT_INDEXED` |

[P03](decisions/vm-semantics.md) owns exact opcode bytes, stack effects, integer/limb conversions, shifts, LOG/SQRT algorithms, structured control flow, Merkle-root opcodes and crypto profiles. CHECKSIG is BIP340 over P01's exact transaction message; CHECKDATASIG has only selectors 0..3; unknown selectors error. Every otherwise unassigned opcode byte is a generic OP_SUCCESS_N, not an algorithm-specific fallback. Do not infer 33-byte keys for BIP340 or silently substitute a library's Ed25519 acceptance rules. Opcode/cost conformance remains unproven until independent vectors pass.

## Introspection and context

P03 defines field and complete-output/path reads, active invocation kind, branch-continuation (`OUTPUTCONTINUESBRANCH`) and spend-only operations; a mint's delta arrives as a node-pushed stack item above the arguments, and its token ID is read with BRANCHROOT. Every coin a script reads is one the transaction spends (`C13`). Out-of-range or undefined-context reads reject. No operation reads block height, block time, block hashes, or the global UTXO root (`OP_BLOCKHEIGHT`, `OP_BLOCKTIME`, `OP_BLOCKHASH` and `OP_UTXOPROOFVERIFY` are rejected; see [rationale](rationale.md#rejected-opcodes-and-consensus-features-and-how-to-build-those-contracts-instead) for why they are excluded and how limit orders, Dutch auctions, linear vesting, expiring offers and in-contract Merkle collections are built instead), so a script's result does not change as blocks arrive (`C22a`). `SIGHASH` takes a signing mode (`0`, `1` or `2`; mode `2` errors if `INPUTINDEX >= TXOUTPUTCOUNT`) and exposes that mode's invocation digest in $O(1)$ time for application signature policies. Other invocations' successful execution and `TxHash` remain unavailable; the proposed field accessors do not establish the old Master/Companion optimization.

## Signing and addresses

The signing API returns the exact digest and a decoded display of the committed intent: chain, inputs and resolved assets (`InputsRoot` and `CoinsRoot`), paths, outputs (`OutputsRoot`), native fee, positive mint deltas and invocation (`input_index`, `branch_index`, and `Leaf(script)` in a spend). In partial modes `01` and `02`, the preimage commits to the 32-byte per-input digest `OwnInputHash(i)` and either `OutputsRoot` or `OutputLeaf(i)` so every signature check hashes at most 4 BLAKE3 blocks in $O(1)$ time. Hardware wallets must refuse unsupported context, not silently sign a hash they display as an ordinary native payment. [P01](decisions/encoding-and-signatures.md) now defines the preimage bytes; signing fixtures become executable only when generated and independently checked against that proposal.

An address ([`addresses.md`](addresses.md)) encodes a network prefix (`xpi` mainnet, `txpi` testnet, `rxpi` regtest), the separator `"1"`, a 5-bit type selector (`0` = `q` for an explicit 32-byte MAST branch root with `flags=0, branches=[root], paths=[[0]]`; `1` = `p` for the standard 37-byte x-only keyhash template `DUP BLAKE3 PUSH32(keyhash) EQUALVERIFY CHECKSIG`), a 52-symbol payload, and an 8-symbol BCH `PolyMod` checksum XORed against a network-specific constant `K[hrp]`, with no `:` separator so one double-click selects the entire address. A single-root Type-0 or Type-1 address represents a single-branch, single-path output policy (`paths=[[0]]`); multi-branch or multi-path covenant policies are exchanged via `lotus-v2/policy-artifact/1` or complete `Output` descriptors rather than a bare 32-byte root.

Native XPI uses a 6-decimal-place base unit (**`1 XPI = 10^6 atoms`**; [P06](decisions/issuance-and-time.md)). Standard wallet UIs and signing displays format native amounts to **2 decimal places (`1.00 XPI`, like dollars and cents)** and hide the lower 4 sub-cent decimal places (`0.00_0000`) by default (exposing full 6-decimal atom precision on hover/detail inspection or hardware-wallet exact-atom screens). Ordinary transaction fees ($\sim 200\text{--}2{,}000\text{ atoms} = 0.0002\text{--}0.0020\text{ XPI}$) therefore sit entirely inside the hidden sub-cent precision as invisible rounding dust to everyday users while preserving $10{,}000$ integer ticks per `0.01 XPI` for [P05](decisions/resources-and-parameters.md)'s parabolic fee-burn accounting and micro-stamps.

Application state is committed in a data leaf with a documented, versioned layout with explicit lengths and units. A covenant must verify successor asset identity, value constraints, state and authorization paths (`OUTPUTCONTINUESBRANCH` or `OUTPUTEXCLUSIVEBRANCH`). A balance equality check alone does not preserve a vault's restrictions.

## Language boundary

The [TypeScript compiler](../../tools/lotus-v2-compiler/README.md) implements a bounded typed source language, schema-2 artifacts, TypeScript/Python call runtimes, local packages (CABI-07), and linked library contracts (CABI-08). The [executable gallery](../../tools/lotus-v2-compiler/examples/gallery/README.md) records its actual coverage. The older [semantic examples](examples/README.md) include unimplemented state and output syntax. The [EVM porting suite](examples/evm-porting/README.md) distinguishes executable slices, proposed source, and irreducible semantic differences. Pin the compiler, evaluator, target profile and optimizer mode in every artifact; candidate implementation is not a consensus freeze.

Each generated artifact records compiler/evaluator revisions, consensus/parameter digests, argument order, selected policy, leaf/proof bytes, core/complete transaction bytes, TxID/TxHash, signature digest, final stack, resulting state and static charges. A pretty source listing is not a conformance vector.

The [compiler and ABI implementation plan](research/plans/lotus-v2-compiler-abi.md) defines staged assembler, typed language, artifact schema, binding generation and independent execution/stress-test gates. The [browser connect protocol (`lotus-connect/1`)](browser-connect.md) specifies how web applications and browser extensions transport `lotus-v2/contract-artifact/2`, `lotus-v2/policy-artifact/1`, and partial `TransactionIntent`s over W3C `MessagePort` channels for connectless intent fulfillment. Development targets a versioned draft profile; final consensus freeze is required for launch, not for beginning tooling.

The first client targets are **Python and TypeScript**, generated from the same versioned interface model with matching runtime libraries and exact-byte cross-language tests. The compiler is written in TypeScript as a small Finch-spec-inspired typed stack pipeline; Python remains an independent reference and generated-client target. Finch implementation code is not treated as conformance evidence.

## Composition proposal LC-1 (not implemented)

This section specifies the next language surface and its lowering contract. It does not change C01–C25, P01–P06, CABI-07/08, the current schema-2 compiler, or the explicit eCash target. Implement it behind a new language version; legacy source continues to have precisely its existing meaning. [Implementation work and acceptance gates](research/plans/lotus-v2-language-composition.md) are separate from this specification. No `OP_DEFINE` or `OP_INVOKE` is introduced: bytes `89` and `8a` already mean SPLIT and NUM2BIN.

### Four different objects

| Object | Creation | Meaning |
| --- | --- | --- |
| Template | `contract Wallet<owner: PublicKey>` | Source plus typed parameters; it has no committed root until fully bound and compiled |
| Bound program | `bind Wallet(owner = key)` | Concrete method scripts and their tree; importing or binding it creates no UTXO |
| Output policy | Explicit branch slots plus named paths | Complete authorization structure for a coin, including AND requirements and OR alternatives |
| Instance | A created outpoint carrying that policy and asset/value | Spendable state; authenticity comes from funding/issuance lineage, not from a source name |

A root is not a deployment address for all these objects. A method leaf is not a branch root, a branch root is not a complete policy, and a `TokenId` identifies a mint tree independently of the output's branch order. Two outputs may share a program but have different policies and owners. Two instances may share every output byte and still have distinct outpoints.

### Explicit entrypoints and visibility

Proposed LC-1 source:

```text
export function authorized(sig: Signature, key: PublicKey): Bool {
    return checksig(sig, key);
}

export contract Wallet<owner: PublicKey, guardian: PublicKey, delay: Int> {
    entry spend(sig: Signature) {
        require(authorized(sig, owner));
    }
    entry recover(sig: Signature) {
        require(check_sequence(1, delay));
        require(authorized(sig, guardian));
    }
}

export token Issuer<issuer: PublicKey> {
    mint issue(delta: Amount, sig: Signature) {
        require(checksig(sig, issuer));
    }
}
```

`entry` is permitted only in a spend `contract`; `mint` only in a `token`. Both return authorization success, never a value to another invocation. LC-1 emits an `INVOCATIONKIND` equality guard for the declared kind in every entry; an untyped caller cannot reuse a mint leaf as a spend authorization. Every declared entry is included in the method tree. Choosing an entry for a witness does not recompile a smaller tree. An empty tree, duplicate entry name, case-folded collision, or entry without an invocation kind rejects. Identical scripts under two names reject as duplicate leaves in LC-1, rather than imply two consensus identities.

Top-level `function` is an inline helper with an explicit result type. LC-1 does not allow an unmarked `function` in a contract: its diagnostic requests `entry` or a free helper. This avoids silently turning a utility into a public spend leaf. `private`, `package` and `export` are module/package visibility only; none makes a revealed entry secret or inaccessible on chain. Private helpers produce no leaf. Helpers remain acyclic, with expansion depth at most 16 and existing size/work limits. They may use only the context effects admitted at their call site. No inheritance, runtime method lookup, delegatecall, dynamic evaluation, or virtual overrides are implied.

Legacy `function` methods and their roots remain unchanged in language version 0. The LC-1 migration command must show the resulting method set and every changed script/root. An entry name remains an SDK selector, never a consensus method number. One-method programs still require explicit `methodName` in the multi-input planner; an optional UI default cannot alter the witness plan.

### Named branches and required paths

Proposed source is deliberately explicit about branch slots:

```text
policy Holder<owner: ContractRootHash, recovery: ContractRootHash,
              rules: ContractRootHash> {
    branch owner_auth at 0 = owner;
    branch recovery_auth at 1 = recovery;
    branch transfer_rules at 2 = rules;
    path spend = all(owner_auth, transfer_rules);
    path recover = all(recovery_auth, transfer_rules);
    require every_path(transfer_rules);
}
```

This lowers to `branches=[owner,recovery,rules]`, `paths=[[0,2],[1,2]]`. A spender chooses one path (OR); all named branches in it execute (AND). A branch's own entries are alternative leaves, so the recovery program must itself enforce the delay. `require every_path` is a build-time assertion on this constructed policy. A contract checking arbitrary transaction outputs must separately execute `output.requires_branch(rules)`; metadata does not enforce that covenant.

Slots are distinct contiguous integers `0..n-1`, explicitly assigned, never inferred from declaration/import order or alphabetical/hash sorting. Names are local labels. Branch roots must be distinct after binding; aliasing two names to the same root rejects without deduplication. Inside each path the compiler sorts slot numbers; it then sorts complete paths lexicographically and records each name's resulting `pathIndex`. Duplicate paths reject, including two names for the same path. It does not remove redundant supersets: a caller may intentionally select one and signatures bind its choice. A data slot is declared `data state at 3 = state_root` and may not occur in a path. All 32-byte entries, including data, obey C09 distinctness. Branch/path count stays within 16; unconstrained `any/all` expression expansion is not allowed. Each `path` is one explicit conjunction.

Adding a branch, reassigning a slot, or adding a path changes policy bytes and may change authorization. Renaming a label without changing slots, roots or path sets changes only ABI metadata. Reordering declarations, imports, constructor object keys, or entry source order must not change wire policy. Adding or changing a method generally changes its program root. Root equality is always recomputed from emitted script bytes and proofs.

A mint program cannot be placed in an executable policy slot by the typed builder. A caller can construct arbitrary bytes outside the builder; contracts must still enforce invocation kind and all contextual checks. `TokenId` is not implicitly convertible to `ContractRootHash`. Burn outputs use a separate `commitment` builder with `paths=[]`; they are never represented by an empty spend policy.

### Typed builder and companion artifact

The following API is proposed; current code uses `compileContract`, `compilePackage`, `prepareTransactionCall` and `finalizeTransactionCall` directly:

```ts
const owner = bindProgram(walletTemplate, { owner: keyA });
const delayed = bindProgram(recoveryTemplate, { guardian: keyB, delay: 144n });
const rules = bindProgram(transferTemplate, {});
const holder = bindPolicy(holderTemplate, {
  owner: owner.root, recovery: delayed.root, rules: rules.root,
});
const output = holder.output({ asset: token.id, amount: 100n });
const spend = holder.spend({
  outpoint, coin: resolvedCoin, path: 'spend',
  witnesses: {
    owner_auth: owner.entry('spend', { sig: null }),
    transfer_rules: rules.entry('transfer', {}),
  },
});
const mint = token.mint('issue', { sig: null });
// No caller-supplied delta: the planner derives it from all asset inputs/outputs.
const plan = prepareTransactionCall({ ...profile, inputs: [spend, mint], outputs });
```

Use a companion `lotus-v2/policy-artifact/1`, leaving `lotus-v2/contract-artifact/2` byte-for-byte stable. Required fields are: `languageVersion`, target/profile digests, compiler revision and optimizer mode; policy name and constructor types/bindings; slot-ordered `branches` with name, index, kind (`spend`/`data`), root and linked artifact digest; `paths` with names, canonical indices and slot lists; exact policy encoding `Vec(h32)||Vec(Vec(CS(index)))`; and build/lock/link provenance. Any `policyDigest` is an application diagnostic, not an extra consensus field. Define it as `H_app/policy/1(policyEncoding)` with the usual `Lotus/v2/` domain prefix; output flags, asset and value are deliberately outside that digest. Full output bytes remain authoritative for signing.

`ProgramRef<K>` distinguishes spend and mint artifacts; `EntryRef<K>` carries artifact digest, method name, script, proof and argument schema. `PolicyRef` contains complete branch/path bytes. `AssetId` distinguishes native from a nonzero `TokenId`. `StateRef<S>` includes layout/version, commitment and authenticated preimage/proofs. An `InstanceRef` additionally carries outpoint and resolved output bytes; an indexer response alone is not a proof that the node will accept it.

Builder validation recomputes artifacts, root/proof membership and selected policy bytes; rejects missing, duplicate and extra named witnesses; orders witnesses by the selected path's ascending slot indices; and checks each method kind/root matches its slot. It does not select a path based on which keys happen to be available. Mint witnesses have no slot or path index. Both Python and TypeScript produce identical intent/wire bytes and errors for these cases. Signing happens only after positions, paths, leaves, outputs and fee sponsorship are fixed.

### Binding, linking, and deployment

Retain the CABI-07 package lock and CABI-08 link graph. `compilePackage` selects an explicit entry contract and fully typed binding map. LC-1 adds explicit binding instances, so `alice = bind Wallet(owner=A)` and `bob = bind Wallet(owner=B)` can coexist; this is not supported by the current one-binding-per-declared-name interface. Bindings are validated by parameter name and type, and serialized in declaration parameter order. Missing, surplus, duplicate or unresolved bindings reject. Reachable compile-time root dependencies form a DAG. Self/mutual root dependencies reject, including those through aliases; source order cannot break the cycle. Importing an exported template does not instantiate or deploy it. A lock update is an explicit build operation.

`contract_root(boundProgram)` and `leaf_hash(boundProgram.entry)` insert constants, with no authorization, invocation or state read. A policy reference must not collapse to the first branch root. A deployment plan creates outputs in a normal transaction, or spends an explicit unique seed for a one-time issuance. It reports scripts, branches, paths, asset/value, initial state and all required authorizations before signing. There is no implicit constructor execution, registry deployment transaction, globally reserved contract name or CREATE address. Initialization restrictions must be checked by an existing input/mint program; simply compiling an initial state does not authenticate it.

### State and transaction effects

LC-1 proposes explicit `state` layouts and `transition`/`terminal` entry effects. A layout fixes a version, field order, types, lengths, units and hash domain. State fields are witnesses verified against the consumed coin, never trusted SDK values. Numeric state uses exact 16-byte VM integers unless the layout explicitly chooses a narrower encoding with range checks. Merkle map libraries bind key width, key derivation, leaf/presence tags, depth, default nodes and proof size; a root alone does not specify a map or prove absence.

Two layouts are supported by the design and must be named in the artifact:

* `inline`: `BranchNode(Leaf(data_script), methodsRoot)`. The compiler reconstructs the old root from state and supplied methods root, checks BRANCHROOT, proves the active method belongs to that methods root, and derives the new root. Checking only `Node(data,M)==BRANCHROOT` without relating the active method to `M` is insufficient for arbitrary supplied trees. Continuation uses `OUTPUTCONTINUESBRANCH` (`ea`), plus asset/value checks.
* `separate`: immutable code slot plus unexecuted state slot. The compiler checks complete successor branch/path structure, allowing only declared data-slot substitutions. `OUTPUTCONTINUESBRANCH` replaces the active code slot only, so it cannot by itself update a separate data slot. Lower this to bounded field/path comparisons or exact serialized-output comparison using existing opcodes, with explicit resource charges.

`transition` requires exactly the declared successors; `terminal` is explicit and applies its payout/burn/revocation checks. An authenticated singleton asset or equally explicit lineage establishes uniqueness. No script runs merely because somebody creates an output with a familiar root, so a fabricated zero-value coin with plausible state cannot count as a genuine controller. Every transition checks identity and positive authority quantity as well as code/state.

Proposed output effect syntax:

```text
entry release(amount: Amount) transition {
    // Preconditions and authenticated state calculation precede these effects.
    successor next at outputs[2 * this.input_index]
        preserves this.policy with state = next_state;
    payout recipient at outputs[2 * this.input_index + 1]
        asset = this.asset, value = amount, policy = beneficiary;
}
```

This is a language proposal, not accepted compiler syntax. `beneficiary` is a complete policy, or an explicitly declared sole-root payout. `preserves` means exact untouched roots/paths, not just presence. Slots are explicit transaction indices calculated with checked bounded arithmetic. The builder resolves named input/output roles, checks distinctness and forbids moving inputs after signing. The script independently enforces positions, amounts and policy; off-chain role metadata has no authority. Fresh payouts use exact policy equality or `OUTPUTEXCLUSIVEBRANCH` when a sole-root policy is intended. Presence alone can leave a recipient unable to spend.

For one-to-many payouts use an explicit bounded group of slots, or an injective index rule such as `2*i,2*i+1`; require those outputs to exist. For many-to-one merges the program specifies one coordinator, participant membership, distinct outpoints, exact aggregate amounts and one output; each participant independently checks the same transition. No generated `absorbed` leaf or trust in another method's successful execution is implied. A shared singleton coordinator serializes state updates. Static cost includes every branch execution and every scan; transaction planners cannot waive duplicate work.

### Mint authority, supply, and libraries

A mint `delta` is consensus-derived `O_token-I_token>0`, node-pushed above witness arguments. It is not a user amount or a lifetime cap. A check `delta<=cap` allows repeated mint transactions. Authority rotation/revocation requires consumed state; old signed certificates remain valid unless tied to a spent coin or an explicit nonce state. A token output's holder policy and mint tree are separate, and transfer rules must appear on every allowed path if they are to govern burns or later transfers.

The recommended capped-token design uses an independently seeded singleton authority asset with immutable generic controller code and a separate state commitment. Compile controller code from issuer/cap/layout **without its own authority TokenId**. The authority mint can then bind that code root, the exact Unassigned state and a unique seed outpoint; its initial output uses the mint invocation's BRANCHROOT as asset. Controller code reads the consumed coin's nonnative asset ID and value 1 and preserves them in its successor. This establishes only local transition consistency, not external authenticity: the target mint and transfer rules bind the expected authority TokenId/code root and independently verify that exact asset, amount, policy and authenticated state on their consumed controller input.

A one-time authorized enrollment stores the future target TokenId in controller state after target compilation. Neither it nor the authority ID is a controller constructor parameter or part of the initial Unassigned state. Transfer rules read their tracked token from the consumed holding; the target mint binds their root after they compile. Minting checks the enrolled target equals BRANCHROOT. Controller transitions enforce cap/nonce/key changes and preserve the one-unit authority asset. Every public controller entry is independently safe even when a caller chooses a different entry from the builder's recommendation. [Bootstrap graphs and negative counterexamples](examples/evm-porting/bootstrap.md) specify the acyclic order for fungible tokens and pools. An enrollment field does not erase a dependency already embedded in code.

Choose supply semantics explicitly: a lifetime-issued cap decrements issuance budget and never refunds burns; circulating supply is indexed from consensus accounting. An ERC20Capped-style outstanding-supply cap with reusable burned capacity must authenticate burn updates too. One conservative construction requires the controller on every token transfer/burn/mint via mandatory transfer rules, tracks transaction net supply including explicit burn outputs, and updates once per transaction. This serializes activity and is not claimed performant. It must also reject hidden supply-changing paths, zero-value counterfeit controllers, arbitrary token destruction of the singleton, and simultaneous untracked mint/burn tricks. The [ERC20 conversion](examples/evm-porting/erc20.md) spells out the accounting limits.

Initial library priorities are checked amounts and wide arithmetic, canonical state codecs/maps, threshold signatures, full-policy comparisons and output-role allocation, unique issuance/controllers, permit intents with consumed nonces, and event commitments. Library contracts link through CABI-08; helpers inline. A library name or interface digest does not attest security. Artifacts retain source/tree digests and target capabilities. Targets reject unavailable features rather than substitute a different integer width, signature algorithm, or transaction model.

---

## Tentative LC-2 Spec Update: Templated Output Enforcement (`ENFORCEOUTPUT`), Shared Off-Chain/On-Chain Generation, `SIMLOG`, and 2-Byte Opcode Encoding

1. **Unified Loop & Conditional `BREAK` (`Boolean(cond) N(depth) BREAK`):**
   - Input and output iteration use `TXINPUTCOUNT ENUMERATE ... ENDENUMERATE` and `TXOUTPUTCOUNT ENUMERATE ... ENDENUMERATE` (retiring the fused `ENUMERATE_INPUTS`/`ENUMERATE_OUTPUTS` opcodes).
   - `BREAK` (`0x6b`) takes `Boolean(cond) N(depth)`: it pops `depth` (`1 <= depth <= active_loop_depth`) and `cond` (`N(0)` or `N(1)`). When `cond == N(1)`, it unwinds `depth` enclosing `ENUMERATE` loops; when `cond == N(0)`, execution continues. This gives bounded `ENUMERATE` loops native `DO/WHILE` and `LOOP/UNTIL` ergonomics (`<until_cond> ONE BREAK`) without wrapping every early exit in `IF ... ENDIF`. Unconditional break is `ONE <depth> BREAK`.
2. **Symmetric Incoming-Vout, Cross-Input Witness & Asset Introspection:**
   - Adds `UTXOFLAGS` (`0xde`, symmetric with `OUTPUTFLAGS` `0xe0`), `INPUTWITNESSARG` (`0xdf`, reading argument `a` of witness `w` of input `i` so N-to-1 stateful merges can inspect sibling inputs' state preimages without $O(N^2)$ witness duplication), `STATEHASH` (`0xc3`, canonical tuple state commitment `item_1 ... item_k N(k) → Hash32` matching `UTXOBRANCH`/`OUTPUTBRANCH` alongside `CAT`/`SPLIT`/`NUM2BIN`/`BIN2NUM`), `TXTOKENBALANCE` (`0xec`, returning `N(total_in) N(total_out)` in $O(1)$ for any `AssetId`), `ACTIVEBRANCHINDEX` (`0xf5`, returning `0..15` in a spend or `-1` in a mint), and `ACTIVEWITNESSINDEX` (`0xf6`).
3. **Templated Output Enforcement (`ENFORCEOUTPUT` `0xeb`) & Value-Budget Claiming:**
   - Rather than duplicating output-construction rules in an external JSON template and positional index checks in script, contracts express output requirements through a single shared transition function that calls `enforce_output(template, claim_amount)` (`ENFORCEOUTPUT` `0xeb`):
     - `OutputTemplate` supports omitting, pinning, or popping from the stack at runtime `value` (`OMIT`, `EXACT`, `MIN`, `FROM_STACK`), `token_id` (`OMIT`, `NATIVE_XPI`, `EXACT`, `SELF_BRANCH_ROOT`), `paths` (`OMIT`, `EXPLICIT`, `INHERIT_INPUT_PATHS`), and individual `branches[0..15]` via `branch_mask` (static 32-byte roots) and `branch_stack_mask` (runtime-computed 32-byte roots popped from the stack, e.g., from `STATEHASH`), where `0` bits in `branch_mask | branch_stack_mask` represent omitted/wildcard branch slots filled by the wallet.
     - **On-chain:** `ENFORCEOUTPUT` finds the first output `j` matching the template with `unclaimed_value[j] >= claim_amount`, deducts `unclaimed_value[j] -= claim_amount` (preventing double-claim attacks across inputs while natively supporting N-to-1 UTXO consolidations where multiple inputs claim their share of a single consolidated output `j`), and pushes the matched index `N(j)` onto the stack so the script can read any omitted fields (`j OUTPUTVALUE`, `j 1 OUTPUTBRANCH`, etc.).
     - **Off-chain (Implicit `EMITLOG` & Constructive Simulation Mode):** Because `.simulate()` runs *before* the transaction's outputs exist in order to discover them, running strict `ENFORCEOUTPUT` during initial simulation would fail immediately. Instead, during `.simulate()`, `enforce_output(role, template, claim_amount)` **implicitly emits a `"lotus.output.draft"` `EMITLOG` (`0x6c`)** with the role metadata, and the simulator constructively appends (or coalesces) a matching draft output `j` in the simulated transaction and pushes `N(j)` onto the stack so subsequent instructions (`j OUTPUTVALUE`, etc.) succeed in a single pass. When `.sign()` is called after the wallet materializes the outputs, it compiles the original contract source in production mode (eliding all `emit` / `wallet::*` statements) through the **pinned versioned optimizer (`edition`, `optimizer_version`)**—the exact same pipeline that generated the Merkle roots originally—and runs strict `ENFORCEOUTPUT` verification before signing.
4. **Structured Simulation Logs (`EMITLOG` `0x6c` — Consensus `OP_INVALID` On-Chain, Entire Statement Elided in Production Builds):**
   - Contracts may declare structured events (`emit("required_output_template", x, y, z)`).
   - In simulation mode, the compiler lowers the `emit` statement to standard stack instructions—e.g. `PICK(x) PICK(y) PICK(z) PUSH("required_output_template") 4 EMITLOG`—where arguments can be stack element references (`PICK`), constants (`PUSH`), or expressions pushed in the exact canonical order expected by standard wallet event handlers, and `EMITLOG` (`0x6c`) pops `N(k)` (`4`) and those `k` items (`+(k+1) - (k+1) = 0` net stack effect for the statement).
   - In production mode (used to generate the on-chain `BranchRoot` / `token_id` Merkle roots and witness scripts during `.sign()`), the compiler omits the entire `emit` AST statement before running the versioned optimizer, so `PICK`/`PUSH` operands for `EMITLOG` never block peephole/stack optimizations and add zero wire overhead.
   - In the node validator, `0x6c` (`EMITLOG`) is permanently defined as **`OP_INVALID`** (never `OP_SUCCESS_N`), so any accidental attempt to broadcast simulation bytecode is deterministically rejected.
5. **Two-Byte Opcode Architecture (Compiler 16-Bit IR & On-Chain MSB Extension):**
   - The compiler IR, assembler, disassembler, and cost tables represent all opcodes as 16-bit unsigned integers (`uint16_t`).
   - For on-chain two-byte opcode expansion, two designs are recorded for genesis freeze selection:
     - **MSB Variable-Length Encoding (Candidate A):** Reserve bit 7 (`0x80` MSB) of the first opcode byte as the two-byte indicator (`0x00`–`0x7f` = 128 single-byte hot instructions for literals, pushes, control flow, and stack ops; `0x80`–`0xff` followed by `b1` = `32,768` two-byte instructions `((b0 & 0x7f) << 8) | b1`).
     - **Escape Prefix Byte `EXT2` `0xff` (Candidate B):** Keep the existing single-byte table (`0x00`–`0xfe`) and reserve `0xff <ext_op>` for 256 two-byte instructions (`0xff00`–`0xffff`).
   - In both encodings, unassigned two-byte opcodes follow the same `OP_SUCCESS` scan and soft-fork upgrade contract as single-byte unassigned opcodes (while `EMITLOG` remains permanently `OP_INVALID` on-chain).
6. **Standardized Ephemeral Wallet Functions (`lotus_std::wallet`) & Wallet-Centric Fluent Pipeline:**
   - Rather than making each contract call construct its own transaction in isolation, the SDK centers on a configured **`Wallet`** instance (`new Wallet({ contracts, utxos, indexerUrls, kdf, signer })`) that already knows the contract registry, tracked/available UTXOs, Chronik/indexer endpoints, and the user's KDF / recipient derivation function:
     ```ts
     const wallet = new Wallet({
       contracts: [DexPoolContract], // optional local overrides
       registryUrls: ["https://registry.lotus.org"], // off-chain contract registry keyed by token_id / branch_root
       utxos: cachedUtxos,
       indexerUrls: ["https://chronik.lotus.org"],
       kdf: userHdKdf,
     });

     const txid = await wallet
       .send(dexPool.swap({ deltaX: 100_000n }), toAddrOrKdf)
       .simulate()
       .maxSlippageBps(50)
       .withFeeRate(1000)
       .sign()
       .send();
     ```
   - When `.send(contractCall, toAddr | kdfFunc).simulate()` runs, `wallet` compiles and executes the contract in simulation mode and intercepts standardized `lotus_std::wallet` `EMITLOG` events:
     - `wallet::output_draft(role, template, claim_amount, branch_roles)` (`"lotus.output.draft"`, auto-emitted by `enforce_output`): registers each required output draft and **automatically fills omitted `0`-bit user spend branch slots** (`branches[0]`) in `OutputTemplate` using `toAddr` or a fresh unlinked branch root derived from `kdfFunc` (while still allowing explicit `.fillBranch(role, branch)` overrides in the fluent chain).
     - `wallet::require_funding(token_id, amount)` (`"lotus.input.funding"`): automatically selects funding UTXOs from `wallet.utxos` / `indexerUrls` and attaches native XPI or token change outputs derived via `kdfFunc`.
     - `wallet::require_mint_authority(token_id, delta, mint_entry)` (`"lotus.input.authority"`): looks up the mint contract for `token_id` in `wallet.contracts` (or fetches and verifies it from `registryUrls` by `token_id`), attaches the `nFlags = 3` Mint Authority input (`prev_txid = token_id`), and binds `mint_entry`.
     - `wallet::require_companion(role, token_id, branch_root)` (`"lotus.input.companion"`): queries `wallet.utxos` / `indexerUrls` to discover and attach coupled multi-UTXO contract inputs (e.g., vault or singleton controller UTXOs) and resolves their contracts by `(token_id, branch_root)` via `registryUrls`.
     - `wallet::require_lock(scope, kind, min_bound)` (`"lotus.tx.lock"`, auto-emitted by `check_locktime` / `check_sequence`): populates `tx.lock` or `input.sequence` on the unsigned transaction plan.
     - `wallet::quote(token_in, amount_in, token_out, amount_out, fee)` (`"lotus.ui.quote"`): powers post-`.simulate()` fluent assertions like `.maxSlippageBps(bps)`, `.minAmountOut(amount)`, and `.inspectQuote()` before `.sign().send()`.
7. **Content-Addressed Off-Chain Contract Registry (Keyed by `token_id` and `branch_root`, Strictly Non-Consensus):**
   - Because every `token_id` in Lotus V2 is the 32-byte `BranchRoot` of its mint authority program (`in.prevout.GetTxId()` when `nFlags == 3`) and every covenant branch in `coin.branches[0..15]` is a 32-byte `BranchRoot` (Merkle root over `Leaf(script_bytes)`), an off-chain npm-style package registry keyed by **`token_id` / `branch_root`** is **cryptographically self-verifying** and **100% outside consensus**:
     - **Lookup by `token_id` or `branch_root`:** When a wallet encounters an unfamiliar token UTXO or covenant branch on-chain (or via `wallet::require_mint_authority` / `wallet::require_companion` during `.simulate()`), it queries `registryUrls` by the 32-byte root (`GET /v1/by-root/<32-byte-hex>`) to fetch the contract source and pinned `(edition, optimizer_version)`.
     - **Zero-Trust Client Verification via the Versioned Optimizer:** The wallet passes the downloaded contract source through the pinned `(edition, optimizer_version)` production compiler/optimizer pipeline—the exact same deterministic process that generated the Merkle roots originally—and verifies that the resulting `BranchRoot` equals the 32-byte `token_id` or `branch_root` on the UTXO before running `.simulate()` or `.sign()`.

8. **Canonical Branch Slot Convention (`branches[0]` = Owner/`CHECKSIG`, `branches[1]` = Enforcement ABI), `HAS_STATE` (`0x04`), and Direct $O(1)$ State Verification (`STATEVERIFY` `0xed`):**
   - Single-value-slot `Output` framing (Option 2A) and P02's separation between **Mint trees** (`nFlags == 3`, defining *what token it is* via `token_id`) and **Spend/Enforcement trees** (`nFlags == 0`, defining *what ABI the UTXO conforms to*) are strictly preserved using a canonical branch slot layout across all contracts, wallets, and indexers:
     - **`branches[0]` (Owner / Authorization Branch by Convention):** Holds the owner's `CHECKSIG` / wallet KDF branch root (or `0x00..00` / unspendable stub for ownerless shared pools). This guarantees that wallets and Chronik indexers can always index and query user ownership uniformly at slot `0` (`branches[0]`), and in `OutputTemplate` bit `0` of `branch_mask` is always the user/KDF slot!
     - **`branches[1]` (Universal Enforcement / ABI Contract by Convention, `branches[1] == STANDARD_VAULT_ABI_ROOT`):** Holds the covenant/enforcement contract root (with `paths = [[0, 1]]` when both owner signature and enforcement ABI are required, or `paths = [[1]]` when the enforcement contract alone governs spending). Because wrapping an asset locks the underlying token inside a dedicated Vault UTXO and mints a fresh receipt token UTXO, layers live in separate UTXOs and each stateful UTXO only ever has a single enforcement contract (`branches[1]`) and a single 32-byte `state_root`!
     - **`Output.flags` Bit 2 (`0x04` `HAS_STATE` — Single 32-Byte `state_root`) & $O(1)$ `STATEVERIFY` (`0xed`):**
       - When `HAS_STATE` (`0x04`) is set on an `Output`, a single 32-byte `state_root` is stored in the `Output` header (`STATEHASH` `0xc3` of `branches[1]`'s state tuple), leaving all `16` branch slots (`branches[0..15]`) 100% for executable contracts.
       - **Input State (`STATEVERIFY` `0xed`):** `<state_hash> STATEVERIFY` immediately checks `(coin[INPUTINDEX].flags & 0x04) != 0` and `state_hash == coin[INPUTINDEX].state_root` in $O(1)$.
       - **Output State (`ENFORCEOUTPUT` `0xeb` with `state_mode`):** When a contract enforces output `j` via `ENFORCEOUTPUT` with `state_mode != 0` (`EXACT_STATE` or `FROM_STACK`), it checks `output[j].state_root == expected_state` and marks `state_authorized[j] = true` (and the validator rejects any `HAS_STATE` output `j` that was not authorized by an executing script in the transaction, preventing forged initial state).
     - **Token-Specific Mint Contract (`token_id = BranchRoot(StakingMint<UNDERLYING, STANDARD_VAULT_ABI_ROOT>)`):** Because `STANDARD_VAULT_ABI_ROOT` is fixed independently of any token, each wrapper token's Mint contract embeds `STANDARD_VAULT_ABI_ROOT` and `UNDERLYING` (`AssetId::XPI` or `TokenId`) with zero circular dependency.
   - Depositing/wrapping executes as a canonical 3-input transaction:
     1. **Deposit Input:** Spends the user's `UNDERLYING` asset (`XPI` or `Token`) into a Vault output (`flags = HAS_STATE | ...`, `token_id = UNDERLYING`, `branches = [OwnerOrPoolAuthRoot, STANDARD_VAULT_ABI_ROOT]`, `state_root = STATEHASH(receipt_token_id, ...)`).
     2. **Minting Input (`nFlags == 3`):** Executes `StakingMint<UNDERLYING, STANDARD_VAULT_ABI_ROOT>::mint`, whose `BRANCHROOT` (`0xf2`) is the minted wrapper's `token_id`, calling `ENFORCEOUTPUT` (`0xeb`) with `state_mode = FROM_STACK` to verify `output[vault_out].state_root == STATEHASH(this.branch_root, ...)`.
     3. **Fee Input:** Pays native XPI transaction fees (coalesced with the Deposit Input when `UNDERLYING == AssetId::XPI`).

9. **Zero-Callback Flash Loans, Off-Chain Signed Oracles (`CHECKDATASIG`), and Multi-Hop DeFi Pipelines:**
   - **Off-Chain Oracles via `CHECKDATASIG` (`0xbd`, Zero UTXO Contention):** Oracles never need on-chain UTXOs (which would serialize transactions and require singleton token authentication). Instead, an oracle signs `(price, timestamp)` off-chain, and the spending contract verifies the signature in $O(1)$ via `CHECKDATASIG` (`0xbd`) and bounds staleness via `CHECKLOCKTIMEVERIFY` (`0xf3`).
   - **Zero-Callback Flash Loans (5 Lines, Zero Reentrancy):** In EVM, flash loans require a reentrant callback dance (`flashLoan()` $\rightarrow$ `onFlashLoan()` $\rightarrow$ `repay()`). In Lotus V2, because all inputs and outputs in a transaction are validated atomically against `TXTOKENBALANCE` conservation, a Vault or Pool supports flash loans with a single stateless entry that simply requires its own UTXO to be recreated in the outputs with `old_value + fee`:
     ```rust
     contract FlashVault<const FEE_BPS: Int> {
         entry flash_loan(state_preimage: Bytes32) {
             // 1. Verify current vault state in O(1)
             state_verify(state_preimage);

             // 2. Compute required repayment = old_value + fee
             let old_val = utxo_value(this.input_index);
             let fee = (old_val * FEE_BPS) / 10_000;
             let new_val = old_val + fee;

             // 3. Require successor vault output with the same branches, paths, token_id, and state_root,
             //    holding at least new_val. Inside this transaction, the borrowed funds can be used across
             //    any other contract inputs (arbitrage, liquidations, collateral swaps) with zero callbacks!
             let out_idx = enforce_output(
                 "flash_repay",
                 OutputTemplate {
                     value_mode: ValueMode::FromStack(new_val),
                     token_mode: TokenMode::Exact(utxo_token_id(this.input_index)),
                     paths_mode: PathsMode::InheritInputPaths,
                     state_mode: StateMode::FromStack(state_preimage),
                 },
                 claim_amount: new_val,
             );
         }
     }
     ```
   - **Atomic Multi-Hop Pipelines (e.g., Swap `XPI` $\rightarrow$ `USDC` $\rightarrow$ Stake into `sUSDC`):** Because tokens are native UTXO values rather than isolated inside ERC-20 storage maps, the wallet chains multiple contract calls in one transaction without cross-contract `CALL` opcodes:
     - **Input 0:** User's `XPI` input.
     - **Input 1:** `AmmPool` UTXO swapping `XPI` $\rightarrow$ `500 USDC`.
     - **Input 2 (`nFlags == 3`):** `StakingMint<USDC, STANDARD_VAULT_ABI_ROOT>` minting `500 sUSDC` and enforcing via `ENFORCEOUTPUT` that the `500 USDC` from the AMM swap is locked directly into a new `USDC` Vault UTXO (`branches[1] == STANDARD_VAULT_ABI_ROOT`, `state_root = STATEHASH(sUSDC_TOKEN_ID, ...)`).
     - **Outputs:** Updated `AmmPool` UTXO + new `USDC` Vault UTXO + user's `500 sUSDC` receipt token UTXO.

---

## References

1. **[Lau & Wuille 2016a]** Johnson Lau and Pieter Wuille, *"BIP 114: Merkelized Abstract Syntax Tree"*, Bitcoin Improvement Proposals, April 2016.
2. **[Wuille, Nick, & Ruffing 2020]** Pieter Wuille, Jonas Nick, and Tim Ruffing, *"BIP 340: Schnorr Signatures for secp256k1"*, Bitcoin Improvement Proposals, January 2020.
3. **[Wuille, Nick, & Towns 2020a]** Pieter Wuille, Jonas Nick, and Anthony Towns, *"BIP 341: Taproot: SegWit version 1 spending rules"*, Bitcoin Improvement Proposals, January 2020.
4. **[Wuille, Nick, & Towns 2020b]** Pieter Wuille, Jonas Nick, and Anthony Towns, *"BIP 342: Validation of Taproot Scripts"*, Bitcoin Improvement Proposals, January 2020.
5. **[O'Connor & Piekarska 2017]** Russell O'Connor and Marta Piekarska, *"Enhancing Bitcoin Transactions with Covenants"*, in *Financial Cryptography and Data Security (FC 2017)*, LNCS vol. 10323, pp. 191–198, 2017.
6. **[O'Connor, Aumasson, Neves, & Wilcox-O'Hearn 2020]** Jack O'Connor, Jean-Philippe Aumasson, Samuel Neves, and Zooko Wilcox-O'Hearn, *"BLAKE3: One Function, Fast Everywhere"*, January 2020 (`https://github.com/BLAKE3-team/BLAKE3-specs`).
