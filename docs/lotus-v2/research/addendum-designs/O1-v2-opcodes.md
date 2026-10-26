# O1 — Lotus V2 planned opcodes and VM semantics: implementation plan

Status: implementation-ready plan, **consensus change**, not yet approved. Every item marked
**[SIGN-OFF]** is a decision the specs leave ambiguous or contradictory. The coding agent must not
start the affected patch until the user has picked a resolution (the recommended one is listed
first). Nothing in this plan was built or executed. All source reads were read-only.

Prepared 2026-10-19.

---

## 0. Inputs, pins and what was verified

| Input | Pin / location | Notes |
| --- | --- | --- |
| P03 VM semantics | `lotus-v2-optimizations` `2db77639:docs/lotus-v2/decisions/vm-semantics.md` | authoritative opcode/semantics text |
| Script ABI (LC-1, LC-2) | `2db77639:docs/lotus-v2/script-abi.md` | LC-2 section §1–§9 (lines 194–296) |
| P01 encoding/signatures | `2db77639:docs/lotus-v2/decisions/encoding-and-signatures.md` | Output grammar, HAS_STATE, sighash |
| Opcode registry | `2db77639:docs/lotus-v2/tools/opcodes.json` | 225 entries, `name/byte/group` only (no stack effects/costs) |
| Structural checker | `2db77639:docs/lotus-v2/tools/spec_candidate_checks.py` | success scan, Merkle, framing, signing vectors |
| Compiler ABI plan | `2db77639:docs/plans/lotus-v2-compiler-abi.md` | §"Tentative Compiler & VM Spec Update (October 18)" |
| Example contract | `2db77639:docs/lotus-v2/examples/evm-porting/proposed/flash-and-staking.lotus` | the path in the task brief (`docs/lotus-v2/evm-porting/...`) does not exist at `2db77639`; the file is under `examples/` |
| Implementation | `lotus-v2-repaired-source` `3cf1891b91` | the checked-out worktree is at `596537e978` (different lineage, same subject). `git diff --stat 3cf1891b91 596537e978` shows **no** differences in `vm.*`, `vm_cost.inc`, `output.*`, `transaction.*`, `ordinary_validation.cpp`, `signing.cpp`, `test_vm.cpp`, so the VM analysis holds for both. The agent must branch from `3cf1891b91` as instructed and re-check this diff first. |
| Patch stack | `lotus-v2-stack-repair` `daemon/patches/v2/series` | `@include ../ecash/series` and then V2 patches `001`…`057`. New patches start at **058**. |

### Verified in source (read directly)

- `vm.cpp` `GenesisAssigned()` assigns `00–5d, 60–6b, 70–81, 88–94, 98–b4, b8–c2, c8–dd, e0–ea, f0–f4` = **215 bytes**
  (`vm_test/opcode_coverage.json` asserts 215). `Assigned()` equals `GenesisAssigned()`. The comment says
  "Frozen genesis allocation for C_account. Extensions must not edit this."
- The implementation still has the **fused loop headers `0x67`/`0x68`** (iterate `input_count`/`output_count`, unbounded by 256),
  plus `0x69` ENUMERATE (bound 0..256) and `0x6a`. `Structure()` treats 67/68/69 as loop frames (max 2 nested).
- `0x6b` BREAK pops only `N(depth)`, and it always exits (`return unsigned(depth)`).
- `0x6c, c3, de, df, eb–ef, f5, f6, ff` are **unassigned**, so the current node treats them as OP_SUCCESS (whole-invocation success).
- `Scan()` handles one byte per opcode and has no EXT2 handling. `Instruction.op` is `uint8_t`, and
  `VmCostProfile::opcode` is `std::array<VmOpcodeCost,256>`.
- `PreparedVmTransaction` is an **immutable** snapshot (`Invocation() const`, copy and move deleted). Contexts borrow it.
  There is no transaction-scoped mutable VM state.
- There are two consensus call paths. (a) `lotus_v2/ordinary_validation.cpp` (`VerifyOrdinaryUncached`) loops `i` ascending,
  then `j` ascending, sequentially, and sums `accounting_cost` against `max_total_invocation_cost`. (b) `src/validation.cpp`
  creates **one `CScriptCheck` per input** (`CheckInputScripts`, around line 3920). With `pvChecks` these are queued
  into `CCheckQueue` and **run in parallel, in arbitrary order**. A `thread_local CachedPreparedVm tl_cache` reuses
  a `PreparedVmTransaction` across checks of the same `CTransaction*`.
- Batch Schnorr (`BatchSigCollector`) is staged per invocation (`staged_sigs`) and merged only on success. This is the
  pattern to copy for ENFORCEOUTPUT effects.
- Static cost: `vm_cost.inc::SizePass`. A loop bound is `input_count`/`output_count` for 67/68, the literal before
  `0x69` when present, and otherwise 256. BREAK is modelled as terminating the sequence (`out.state = nullopt`). Unknown
  ops fall to `Worst(op)`.
- Output model: `output.h` `struct Output {flags, value, token_id, branches, paths}` with `flags & 0xfc` rejected.
  `MAX_OUTPUT_BYTES = 812` is hard-coded in `output.cpp`, `transaction.cpp:312`, `disk_state.cpp:387` and `fast_sync.cpp:98`.
  `test_sparse_state.cpp` asserts the maximum Coin is 868.
- `CTxOut` carries V2 fields `nFlags, tokenId, vBranches, vPaths` (`primitives/transaction.h`), and v7 (de)serialization
  writes `nFlags`, value and an optional token. `compressor.h::TxOutCompression` encodes V2 outputs with tag
  `kV2TagBase + (nFlags & 0x03)` and accepts only `kV2TagBase..+3`. **It would silently drop a HAS_STATE bit and the state root.**
- All TxID, OutputsRoot, OutputLeaf, CoinEntry and OwnInputHash computations go through `EncodeOutput`
  (`signing.cpp`, `transaction.cpp`), so a state root added to `EncodeOutput` reaches every identity and sighash automatically.
  `validation.cpp` also takes `ptxTo->GetOutputsHash()` from the primitives serializer, which must match.
- `tagged_hash.cpp` **already uses `Lotus/v2/state` (`HashDomain::State`)** for the chain StateRoot envelope
  (`sparse_state.cpp::StateRoot`, 130-byte preimage).
- Caches are keyed by TxHash: `ScriptCacheKey` uses `tx.GetHash()`, and `OrdinaryCacheKey` includes txid and txhash.
- Existing divergences that are **out of scope** but should be noted: `CHECKSIG` has an empty-signature special case
  (`vm.cpp` ~1925), while P01 says "No empty-signature special case". An invalid correctly-sized signature throws `NULLFAIL`,
  while P01 says it "pushes false".
- The registry has 225 names, no duplicates, and 31 unassigned bytes: `5e 5f 67 68 6d 6e 6f 82–87 95–97 b5–b7 c4–c7 f7–fe`.
  This matches the P03 listing. Registry bytes for every opcode in this plan match the P03 tables: ENUMERATE 69, ENDENUMERATE 6a,
  BREAK 6b, EMITLOG 6c, STATEHASH c3, TXINPUTCOUNT c9, TXOUTPUTCOUNT ca, UTXOFLAGS de, INPUTWITNESSARG df,
  ENFORCEOUTPUT eb, TXTOKENBALANCE ec, STATEVERIFY ed, UTXOSTATEROOT ee, OUTPUTSTATEROOT ef, ACTIVEBRANCHINDEX f5,
  ACTIVEWITNESSINDEX f6, EXT2 ff.

### Assumed (not verified)

- V2 has **no live genesis**. Editing `GenesisAssigned()` is therefore a pre-genesis reallocation that requires fixtures and
  dev-chain data to be regenerated. It is not a soft fork (see I-18).
- `block_transition.cpp`, `transaction_pool.cpp` and `mempool_overlay.cpp` reach the VM only through `CheckOrdinary*`
  (a grep found no direct `EvaluateVm*` calls there).
- RPC JSON (`core_write`/`rpc/rawtransaction`) and Chronik serialize V2 output fields somewhere not inspected here. The agent must
  `git grep vBranches` and add `stateRoot` everywhere a V2 output is rendered.
- The independent Python reference VM used by `vm_test/differential*.py` is not on `2db77639`. It must be updated in its
  own repository and is outside this daemon plan.

---

## 1. Summary

Twelve V2-tier patches (058–069) change the following:

1. A 16-bit internal opcode representation with **EXT2 (`ff xx`) framing**. All 256 `ff xx` values are OP_SUCCESS_EXT. No assigned two-byte ops.
2. Allocation synced to `opcodes.json`: `67/68` retired to OP_SUCCESS, `6c` permanent invalid, and the new bytes assigned.
3. One loop form, `TXINPUTCOUNT|TXOUTPUTCOUNT ENUMERATE`, with a static-cost idiom that keeps the precision of the old fused headers.
4. **Conditional BREAK** (`Boolean(cond) N(depth)`).
5. `HAS_STATE` (flags bit 2) with a 32-byte `state_root` in the wire format, coins DB, compressor, RPC and Chronik.
6. Read-only introspection: `UTXOFLAGS`, `UTXOSTATEROOT`, `OUTPUTSTATEROOT`, `ACTIVEBRANCHINDEX`, `ACTIVEWITNESSINDEX`, `TXTOKENBALANCE`, `INPUTWITNESSARG`.
7. `STATEHASH` and `STATEVERIFY`.
8. **Transaction-scoped VM effects** (`unclaimed_value`, `state_authorized`) with a defined invocation order and a post-check.
   V2 script checks become per-transaction instead of per-input (parallel across transactions only).
9. `ENFORCEOUTPUT` strict mode with a binary `OutputTemplate` parser.
10. A separate, non-consensus **simulation evaluator** (EMITLOG events, constructive ENFORCEOUTPUT).
11. RPC/Chronik exposure for the SDK.
12. Cross-implementation vectors.

---

## Decisions (user, 2026-10-19) — supersede the matching items in section 2

This is work in progress for regtest and testnets, months before release. Where
section 2 offers a recommendation, it is adopted unless changed here. Expect
to refactor; keep choices easy to change.

- **I-1:** encoding B (`0xff` EXT2). May be revisited later.
- **I-2:** the spec text wins; fix the checker in the spec repo separately.
- **I-3:** the scan rejects immediately at `0x6c` (EMITLOG), including in
  skipped arms and after RETURN.
- **I-6:** V2 consensus caps inputs and outputs at 256 each. Set
  `max_inputs`/`max_outputs` to 256 (the code currently only enforces <= 65535
  from the profile; the encoding spec's 65,535 is the wire-format bound).
  `ENUMERATE` keeps `0..256`, which then covers every transaction.
- **I-7:** adopt the `min(256, count)` static-cost rule for
  `TXINPUTCOUNT`/`TXOUTPUTCOUNT ENUMERATE`.
- **I-11 (order dependence):** make claims order-free. During execution,
  ENFORCEOUTPUT checks the template, records `(j, claim)` and does not mutate
  a shared budget; a per-transaction post-check requires
  `sum of claims on j <= outputs[j].value` and that every HAS_STATE output was
  authorized. The search picks the first output matching the template,
  ignoring budgets; a script that needs a specific output pins it (an
  explicit output index in the template, or from the stack). Invocations stay
  parallel; only the post-check is per transaction.
- **I-12:** reading other inputs' witness arguments is allowed; amend VS:236.
  Contract authors must still know arguments are not signed, so a sibling's
  argument is trustworthy only if the sibling's own script checks it.
- **I-13:** use a separate tag, `Lotus/v2/contractstate`, for STATEHASH.
- **I-10, I-17 (state authorization):** document as recommended; revisit when
  state is exercised on regtest.
- **I-4, I-5, I-8, I-9, I-14, I-15, I-16:** adopt section 2 / section 4
  recommendations.

## 2. Spec inconsistencies and gaps (each needs user sign-off)

Locations are `file:line` at `2db77639` (VS = vm-semantics.md, ABI = script-abi.md, ENC = encoding-and-signatures.md,
CMP = lotus-v2-compiler-abi.md, CHK = spec_candidate_checks.py, EX = flash-and-staking.lotus).

**I-1 Two-byte encoding: Candidate A (MSB) vs Candidate B (EXT2). [SIGN-OFF]**
- CMP:214 calls A "**MSB Variable-Length Scheme (Preferred for 2-byte expansion)**". VS:349–352 and ABI:213–215 list A and B as open.
- `opcodes.json` assigns `EXT2 = ff`. VS:218 defines EXT2, the VS:356–359 success listing assumes B, and CHK asserts 225/31 single-byte.
- A is incompatible with the registry. 104 assigned opcodes sit at `0x80–0xff` (SWAP `80`, TUCK `81`, CAT…EXT2), and under A
  every one of those bytes becomes a two-byte prefix. VS:350 says A's one-byte range holds "stack operations `70`–`7f`", but the
  stack table runs to `0x81`. A's numbering is also inconsistent: "a 15-bit opcode `((b0 & 0x7f) << 8) | b1` (`32,768` two-byte
  opcodes across `0x8000`–`0xffff`)" gives a value in `0x0000–0x7fff`, not `0x8000–0xffff`.
- **Recommendation: B.** On-chain: single bytes `00–fe` plus `ff <ext_op>`. Daemon IR is `uint16_t`: a single byte `b` becomes
  `0x00bb`, and `ff xx` becomes `0xff00 | xx`. `0x00ff` is never an executable instruction. Choosing A would require a full
  re-allocation of the registry, which this plan does not cover.

**I-2 The checker's success scan does not implement EXT2. [SIGN-OFF: confirm the spec text wins]**
VS:365 says "At `0xff` (`EXT2`), require at least 1 following byte … if `0xff <ext_op>` is an unassigned two-byte opcode … immediately
return invocation success." CHK:572–608 treats `ff` as an ordinary one-byte assigned op (`continue`), so `ff 4c` would continue and
parse `4c` as PUSHDATA. Recommendation: follow VS. A trailing lone `ff` is Invalid (framing), any `ff xx` is AutomaticSuccess,
and the selector byte is never parsed as a push. Fix CHK separately in the spec repo. The daemon vectors in §7 encode the VS behaviour.

**I-3 EMITLOG is "unconditionally" invalid, but the scan can reach success first. [SIGN-OFF]**
VS:56 says "**consensus `OP_INVALID` on-chain** (unconditionally rejects if ever broadcast …)". VS:367 says "At any other assigned
single-byte instruction, advance one byte". With that rule, `6c fe` scans past `6c` and succeeds at `fe`. Nothing says whether an
`EMITLOG` in a skipped arm rejects. Recommendation: the scan rejects **immediately** at `0x6c`, including in skipped arms and after
`RETURN`, before any later success byte. That makes the rejection unconditional. It is permanent and is never a soft-fork point.
Alternative: reject only at decode time if no success byte is found.

**I-4 Name: `SIMLOG` vs `EMITLOG`.** ABI:194 and CMP:209 headings say `SIMLOG`; every table and the registry say `EMITLOG`.
Recommendation: `EMITLOG`.

**I-5 Retiring `0x67/0x68` and editing a "frozen" genesis allocation. [SIGN-OFF]**
VS:53 says "`67` and `68` are retired to unassigned `OP_SUCCESS_N`". `vm.cpp` says "Frozen genesis allocation … must not edit this."
Changing assigned bytes to success, or success to assigned, is only legal before genesis. Recommendation: treat it as a pre-genesis
reallocation, regenerate every fixture, branch root and dev chain, and record the new `opcodes.json` SHA-256 in `opcode_coverage.json`.

**I-6 `TXINPUTCOUNT ENUMERATE` vs the 256 bound. [SIGN-OFF]**
VS:53 says "ENUMERATE | pop N in 0..256 … use `TXINPUTCOUNT ENUMERATE` … to iterate inputs/outputs". Counts go up to 65,535
(ENC:17). Any covenant that loops over inputs or outputs therefore **errors when there are more than 256** of them. The fused 67/68
had no such cap. With partial-mode (01/02) signatures, a third party can add inputs or outputs and make the covenant unspendable in
that transaction (griefing). Recommendation: keep `0..256` and document "contracts that enumerate inputs or outputs support at most
256", so wallets must split. Alternative: allow up to 65,535 when the bound comes from the idiom in I-7.

**I-7 Static cost of the loop idiom is unspecified. [SIGN-OFF]**
The fused ops were charged at the exact count (`vm_cost.inc`). `TXINPUTCOUNT ENUMERATE` would be charged at 256 × body, or
65,536 × body when nested. That is a large cost regression and can push existing contracts over `max_invocation_cost`.
Recommendation: SizePass rule. If the instruction immediately before `ENUMERATE`, in the same sequence, is `TXINPUTCOUNT`/`TXOUTPUTCOUNT`,
the static bound is `min(256, count)`, with the count taken from the tx context. Otherwise use the literal, otherwise 256.

**I-8 HAS_STATE contradicts older text. [SIGN-OFF]**
- ABI:18 says "State: **Not a separate output field**. Data or Merkle roots are stored in `branches` …". CMP:97 says "State schemas
  describe real byte encodings or branch commitments, **not a fictitious dedicated state field**." ENC:46 marks HAS_STATE "**Tentative LC-2 update**".
- VS:148 says STATEHASH is "matching the 32-byte state branch root stored in `UTXOBRANCH(i, slot)` … `OUTPUTBRANCH(j, slot)`", while VS:202–203/283–288 store it in `state_root`.
- Recommendation: adopt HAS_STATE as a genesis rule, and rewrite ABI:18, CMP:97 and VS:148 to name `state_root`. Branch-stored state stays possible as a convention.

**I-9 Undefined HAS_STATE edge cases. [SIGN-OFF]**
(a) `HAS_STATE|IS_BURN`. VS:238 says a burn output's "`OUTPUTFLAGS` returns `0x02` (native) or `0x03` (token)", which implies a
burn never has state. Recommendation: **reject flags with both 0x02 and 0x04**.
(b) A zero `state_root`. UTXOSTATEROOT/OUTPUTSTATEROOT return `0x00..00` when the state is absent (VS:202–203), which is ambiguous
with a present zero root. Recommendation: **require a nonzero `state_root`** when the flag is set, like `token_id` (ENC:44).
(c) Coinbase. It runs no script, so it can never satisfy the post-check. Recommendation: reject HAS_STATE in coinbase outputs explicitly.

**I-10 `state_authorized` is not authentication. [SIGN-OFF on documentation, and optionally on extending `ea`]**
VS:288 says "(automatically preventing forged initial state on any output that wasn't explicitly authorized by an input or mint contract!)".
`state_authorized[j]` is global to the transaction. Any input the attacker controls can run `<template matching j> FROM_STACK 0 ENFORCEOUTPUT`
(claim 0) and authorize arbitrary state on output `j`. The rule only rejects HAS_STATE outputs that **no** script mentioned. Trust in a
coin's state must come from its own code and lineage (STATEVERIFY plus the successor's own ENFORCEOUTPUT). Also, `OUTPUTCONTINUESBRANCH`
(`ea`) compares only branches and paths, so a contract that continues via `ea` does not constrain the successor's state.
Recommendation: document both facts. Optionally make `ea` also require equal `HAS_STATE` and `state_root`; that changes existing `ea` semantics and needs a decision.

**I-11 Shared mutable state between invocations, and order dependence. [SIGN-OFF, highest priority]**
- ABI:12 says "no shared mutable branch state". VS:236 says "There is no introspection of other invocations' successful execution, mutable VM state …".
- ENFORCEOUTPUT's `unclaimed_value[j]` is shared and mutated, and the scan picks "the first output `j` … [with] `unclaimed_value[j] >= claim_amount`" (VS:306).
  Whether a transaction is valid therefore depends on the **order** in which invocations run, which no spec defines. The daemon currently runs
  per-input checks **in parallel** (`CCheckQueue`).
- Greedy first-match can also fail when a valid assignment exists: input A takes output 0, and input B could only use output 0.
- Recommendation: (1) **canonical order** is input index ascending, then witness index ascending, with mints at their input position;
  (2) V2 transactions get one script-check job per transaction (parallel across transactions); (3) greedy failure is consensus-defined,
  so wallets order their outputs. Alternative: claims become order-free (the template match ignores the budget, and a post-check requires
  Σ claims ≤ value). That is simpler to parallelize but changes the spec's 1-to-1 disambiguation semantics.

**I-12 INPUTWITNESSARG contradicts VS:236 and reads unsigned data. [SIGN-OFF]**
VS:236 says "There is no introspection of other invocations' … **signature arguments** …". VS:182 says `df` reads "argument `a` of witness
`w` of input `i`", which includes other inputs' signature arguments. ENC:128 says arguments are excluded from TxID and SigMessage, so they
can be malleated unless the owning input's script verifies them. Indexing is also unstated.
Recommendation: amend VS:236. `a = 0` is the first wire argument (the bottom of the initial stack, ABI:11). `w` indexes the selected
path's witnesses for a spend, and must be 0 for a mint. A mint's node-pushed delta is not an argument. Coinbase errors.
Document that a reader may rely on a sibling argument only if the sibling's own script authenticates it.

**I-13 STATEHASH domain tag collides in name with the chain StateRoot. [SIGN-OFF]**
VS:148 uses `H_state(...)`. The implementation already uses `Lotus/v2/state` for the block StateRoot envelope. The preimages cannot
collide (a STATEHASH preimage starting with `00` is exactly the 1-byte `k=0` case, while the envelope is 130 bytes), but reusing the
domain conflates two kinds of "state root". Recommendation: add the new tag **`Lotus/v2/contractstate`**. Also specify that
`item_1` is the deepest item, CS is shortest-form, and each item is ≤ element cap.

**I-14 ENFORCEOUTPUT template underspecification (VS:290–303). [SIGN-OFF for each item; recommendations in §4.6]**
(a) The pop order of `stack_branches…` is not given.
(b) The meaning of `branch_count` (0..16, while outputs need 1..16) under each `paths_mode` is not given, nor whether it must equal `len(output.branches)`.
(c) Overlap of `branch_mask` and `branch_stack_mask`, and mask bits ≥ `branch_count`.
(d) `paths_mode = 11` and `state_mode > 2`.
(e) Bit 7 is defined only "under `INHERIT_INPUT_PATHS`", yet EX:38 sets `wildcard_unset_branches: true` with `PathsMode::Explicit`.
(f) Burn outputs. OMIT requires `RequiresBranch`, which is always false for a burn (VS:238), so `burn_mode=1` with any pinned branch can never match. INHERIT requires non-empty coin paths, which a burn can never satisfy.
(g) The range of `expected_value` and `claim_amount` (N up to 1024 bytes; values are u64).
(h) Malformed templates (truncation, trailing bytes): error, or "no match"?
(i) The bit 0–1 text for OMIT, "deducts `claim_amount` if `claim_amount > 0`", is redundant with the general budget rule. Read it as identical.

**I-15 Simulation mode is undefined in places. [SIGN-OFF]**
VS:311 says the simulator "constructively appends (**or coalesces**)". Coalescing is undefined, as are the omitted fields of a synthetic
output (OMIT/MIN value, OMIT token, wildcard branches, OMIT paths), how CHECKSIG behaves before signatures exist, and how TXID/SIGHASH
behave over a provisional transaction. EMITLOG `k` has no bound. Whether the daemon or only the SDK hosts `EvaluateVmSimulated` is
unstated. Recommendations are in §4.9.

**I-16 Small gaps.**
- ACTIVEWITNESSINDEX in a mint is unspecified (VS:217). Recommend `N(0)`.
- TXTOKENBALANCE (VS:200) does not say whether mint inputs or burn outputs count. Recommend: `total_in` = consuming spend inputs only;
  `total_out` = all outputs including burns; this matches ENC:51 accounting, so a mint's delta = out − in.
- "in $O(1)$" means a precomputed map. The asset id must be exactly 32 bytes.
- ABI:249, CMP:242 and EX comments say spend trees are "`nFlags == 0`". Input flags are `01` for spend (ENC:51), so `00` rejects. This is a documentation typo.
- CHK `main()` prints "41 success opcodes" but asserts 31.
- The VS heading "Control (`60`–`6b`)" omits `6c`.

**I-17 Soft-fork limits introduced by ENFORCEOUTPUT and HAS_STATE. [SIGN-OFF to record in VS:371]**
Old nodes treat an OP_SUCCESS invocation as success **without** executing its claims or authorizations. A future opcode that **sets**
`state_authorized` would make a transaction valid to new nodes and invalid to old nodes, which is a hard fork. Recommendation: add to the
soft-fork contract that newly assigned opcodes may consume `unclaimed_value` (stricter) but may never authorize state or relax the post-check.

**I-18 Example contract issues (not daemon-blocking).**
- EX:117–118 (`flash_loan(state_preimage: Bytes32) … state_verify(state_preimage)`) passes the root itself, which is a tautology,
  and the name is misleading.
- EX:92 uses `this.witness_index` for siblings, which assumes every sibling selected the same path slot.
- EX:110 claims `utxo_value(this.input_index)` per input; this is correct for N-to-1.
- None of these change the daemon.

---

## 3. Opcode table (checked against `opcodes.json`; "now" = behaviour at `3cf1891b91`)

N = 16-byte canonical int128 unless stated. "Err" = script error (`VmStatus::Invalid`). "ctx" = requires an authenticated context
(without one: `Unsupported`, as the current `Context()` does). Cost shape: `base + per_operand_byte·Σops + per_result_byte·Σresults`
(existing `VmOpcodeCost`), plus the listed extras. No numeric schedule is frozen (VS:390).

| Byte(s) | Name (registry ✓) | Stack effect | Consensus rules / failures | Static size pass (result bytes) | Cost extras | Simulation mode | Now |
|---|---|---|---|---|---|---|---|
| 67, 68 | — (retired) | — | OP_SUCCESS_103/104 (I-5) | structural only | structural | same | fused loops → **remove** |
| 69 | ENUMERATE ✓ | `N(bound) →`; each iteration pushes `N(i)` | bound canonical N, `0..256` (I-6) else Err; ≤2 nested loops at decode | body × bound; bound = literal \| idiom count (I-7) \| 256 | per-iteration `6a` charge (existing) | same | exists (keep) |
| 6a | ENDENUMERATE ✓ | structural | unmatched → decode Err | — | per iteration | same | exists |
| 6b | BREAK ✓ | `Boolean(cond) N(depth) →` | always pop both; depth ∈ 1..active_loops (≤2) else Err; cond ∈ {N(0),N(1)} else Err; cond=1 → ExitLoops(depth); outside a loop → Err when executed; in a skipped arm, no error | pops 2; **not** terminating: the fall-through state continues; exit states recorded for depth (literal) or all depths | base + operand 32 | same | depth-only → **change** |
| 6c | EMITLOG ✓ | sim: `item_1…item_k N(k) →` | consensus: **scan-time Invalid** (I-3) | n/a | n/a | records event `(items…)`, topic = item_k (top); k ∈ 0..64, stack must hold k+1 | unassigned (success!) → **change** |
| c3 | STATEHASH ✓ | `item_1…item_k N(k) → Hash32` | k ∈ 0..64 else Err; underflow Err; digest `H_contractstate(CS(k)‖Σ CS(len)‖item)` (I-13), item_1 deepest | pops k+1 (k from literal, else worst 64×limit); push 32 | per_operand_byte over the preimage size (charge Σ(len+CS)+CS(k)) | same | unassigned |
| c9 / ca | TXINPUTCOUNT / TXOUTPUTCOUNT ✓ | `→ N` | as now | 16 | — | counts include appended drafts | exist |
| de | UTXOFLAGS ✓ | `i → N(flags)` | ctx; i in range; input must be a spend with a resolved coin (else Err, like `CoinAt`) | 16 | — | same | unassigned |
| df | INPUTWITNESSARG ✓ | `i w a → bytes` | ctx; i < inputs; input flags 1: w < len(witnesses); flags 3: w == 0; flags 2: Err; a < len(args) (I-12); result ≤ element cap | exact field size from tx (new `0xdf` field-size vector), else max arg size | per_result_byte | same | unassigned |
| eb | ENFORCEOUTPUT ✓ | `[Hash32 st]? [roots…]? [N(v)]? template N(claim) →` (pushes nothing) | §4.6; no match → Err; template malformed → Err; records `(claim, match mask)` and, with a state mode, the authorization of every matched output; staged and committed on invocation success; assignment checked in phase 2 (claim assignment section) | pops variable (needs literal template; else worst); no push | base + per_operand_byte·(template + popped) + **new** flat `per_tx_output × output_count` (node schedule: 32); static charge = executed charge | constructive (§4.9) | unassigned |
| ec | TXTOKENBALANCE ✓ | `Bytes32(asset) → N(in) N(out)` | ctx; asset exactly 32 bytes else Err; zero = native; totals precomputed; asset absent → 0 0 | push 16, 16 | O(1) | over provisional outputs | unassigned |
| ed | STATEVERIFY ✓ | `Hash32 →` | ctx; spend-only (mint → Err); operand exactly 32 else Err; coin lacks HAS_STATE → Err; mismatch → Err | pop 1 | operand 32 | same | unassigned |
| ee | UTXOSTATEROOT ✓ | `i → Hash32` | spend coin required (CoinAt); zeros if no HAS_STATE | 32 | — | same | unassigned |
| ef | OUTPUTSTATEROOT ✓ | `j → Hash32` | j < outputs; zeros if no HAS_STATE | 32 | — | drafts included | unassigned |
| f5 | ACTIVEBRANCHINDEX ✓ | `→ N(k)` | ctx; spend: `coin.paths[path_index][witness_index]`; mint: N(−1) | 16 | — | same | unassigned |
| f6 | ACTIVEWITNESSINDEX ✓ | `→ N(w)` | ctx; spend: witness_index; mint: N(0) (I-16) | 16 | — | same | unassigned |
| ff xx | EXT2 ✓ / OP_SUCCESS_EXT_N | — | scan: lone trailing `ff` Invalid; any `ff xx` AutomaticSuccess (none assigned) | structural | structural | same | unassigned (single-byte success) |
| dc, e7 | UTXOOUTPUT / OUTPUTRECORD | unchanged | serialized output now includes `state_root` (≤844 B) | field sizes grow | per_result_byte | — | exists |
| e0 | OUTPUTFLAGS | unchanged | may now return 0x04/0x05 | — | — | — | exists |
| ea | OUTPUTCONTINUESBRANCH | unchanged | does not inspect state (I-10) | — | — | — | exists |

---

## 4. Design details

### 4.1 Opcode representation and framing (patch 058)

- `vm.h`: `using VmOpcode = uint16_t; constexpr VmOpcode VM_EXT2_PREFIX = 0xff; inline constexpr VmOpcode Ext2(uint8_t x){return 0xff00|x;}`.
- `Instruction.op` becomes `VmOpcode`. Every `case 0x..` stays a single-byte value.
- `VmCostProfile` gets `std::array<VmOpcodeCost,256> ext_opcode{}` (all unused until a soft fork). `OpCost(VmOpcode, …)` indexes by width.
  `CheckCostProfile` requires a positive base for every **assigned** opcode in both tables. `field_sizes` keys widen to `VmOpcode`.
- `Scan()`: on `ff`, if `pos == size` → `VmFailure("truncated EXT2")`. Otherwise read the selector; if `AssignedExt(x)` is false
  (always false today) → return success. Otherwise emit `Instruction{Ext2(x)}`.
- Never parse the selector as a push.

### 4.2 Allocation (patch 059)

`GenesisAssigned` becomes a table generated from the registry: `00–5d, 60–66, 69–6c, 70–81, 88–94, 98–b4, b8–c3, c8–df, e0–ef, f0–f6, ff`.
That is 225 entries. Add a unit test that compares the table byte for byte with the pinned `opcodes.json` (SHA-256 recorded).
`0x6c` is "assigned" for counting purposes but rejected by `Scan` (I-3). New semantic opcodes are added as
`throw VmFailure("assigned opcode not implemented", true)` until their patch lands, so in this interim they are Unsupported, never success.

### 4.3 Loops and BREAK (patches 060, 061)

- `Structure()`: loop frames come only from `0x69`.
- `Execute()`: delete the 67/68 branches.
- `SizePass::Analyze`: idiom bound (I-7). Add a `ContextCount(previous)` helper beside `LiteralValue(previous)`.
- BREAK (`Execute`): `depth = Numeric(Pop()); cond_bytes = Pop(); cond = Boolean(cond_bytes)`. Validate depth (1..active_loops) **before**
  acting on cond, then `if(cond) return depth;` else continue. Charge with both operand sizes.
- SizePass BREAK: pop 2; record exit states as today; then **continue** with the fall-through state instead of `nullopt`.
- Update `differential_cost.py` and `test_vm.cpp` vectors that use `67/68`/`4e6b` (10 occurrences in `test_vm.cpp`, plus `differential*.py`).

### 4.4 Output data model (patch 062)

- `Output`: add `Hash32 state_root{}` and `bool HasState() const { return flags & 4; }`.
- Wire format: `flags ‖ value ‖ token_id? ‖ state_root? ‖ Vec(h32) ‖ Vec(Vec(CS))`.
- Rules:
  - `flags & 0xf8` → reject.
  - `(flags & 6) == 6` → reject (I-9a).
  - `HasState()` with an all-zero `state_root` → reject (I-9b).
- `MAX_OUTPUT_BYTES = 844` (812 + 32). `MAX_COIN_BYTES = 900` (36 + CS(3) + 844 + 17).
- Update the constants in `transaction.cpp`, `disk_state.cpp`, `fast_sync.cpp`, `test_output.cpp` and `test_sparse_state.cpp`. Replace the literals with the constant.
- `CTxOut`: add `uint256 stateRoot`. Extend `SetNull`, `operator==`, `ToV2Output`/`FromV2Output` (both overloads) and the v7 serializer
  and unserializer in `primitives/transaction.h` (write the state root after the token). Keep `GetOutputsHash()` consistent with `EncodeOutput`.
- `compressor.h`: widen the V2 tag range to `kV2TagBase..kV2TagBase+7` (`nFlags & 0x07`) and write and read `stateRoot` when bit 2 is set.
  This is a coins-DB format change; existing dev chain data must be reindexed (assumed pre-genesis).
- `block.cpp` coinbase rules: reject HAS_STATE (I-9c).
- Interim, until patch 066: `ordinary_validation` and `validation.cpp` reject any HAS_STATE output (`"state-output-unauthorized"`), so no
  unauthorized state can exist mid-stack.
- RPC `decoderawtransaction`/`getrawtransaction`/`gettxout`, and Chronik output encoding: add a `stateRoot` field
  (find the sites with `git grep -n vBranches src/rpc src/chronik* src/core_write.cpp`).
- Wallet decoders (`wallet/v2_*`) round-trip the field.

### 4.5 Transaction-scoped effects (patch 066)

New in `vm.h`:
```cpp
struct VmTransactionEffects {            // owned by one validation run of one tx
    std::vector<uint64_t> unclaimed_value; // = outputs[j].value
    std::vector<uint8_t>  state_authorized;
    void Reset(const Transaction&);
};
struct VmInvocationEffects { std::vector<std::pair<uint16_t,uint64_t>> claims; std::vector<uint16_t> authorized; };
```
- `VmExecutionContext` gains `VmTransactionEffects *effects` (nullable; `ENFORCEOUTPUT` without it is Unsupported).
- The machine reads the committed budget plus its own staged claims. On `Success`, the staged effects are applied; on any failure they
  are discarded (same pattern as `staged_sigs`). AutomaticSuccess applies nothing.
- `bool FinalizeVmTransactionEffects(const Transaction&, const VmTransactionEffects&, std::string&)`: every `HasState()` output must have
  `state_authorized` set. This runs after all invocations succeed, in both `VerifyOrdinaryUncached` and the V2 path in `validation.cpp`.
- **The effects must not live in `PreparedVmTransaction`.** It is cached in `tl_cache` and reused across checks, so effects stored there
  would go stale between validation runs.
- `validation.cpp::CheckInputScripts`: for a V2 transaction (any input with `nFlags` 1 or 3), create **one** check that loops
  `nIn` ascending and `j` ascending, with a fresh `VmTransactionEffects`, then finalizes. Non-V2 behaviour is unchanged.
  The sig-check limiter accounting stays per transaction.
- Invocation order (I-11): input index ascending, then witness index; mint inputs at their position.
  `VerifyOrdinaryUncached` already does this, so add a comment and a test that pins it.

### 4.6 ENFORCEOUTPUT (patch 067), with the recommended answers to I-14

New `output_template.h/.cpp`: `bool ParseOutputTemplate(span, OutputTemplate&, std::string&)`. Every parse error is a script Err.

```
flags:u8   v=bits0-1  t=bits2-3  p=bits4-5  burn=bit6  wild=bit7
[template_value:u64]     iff v∈{01,10}
[template_token_id:h32]  iff t==10
branch_count:u8 (0..16)  branch_mask:u16  branch_stack_mask:u16  state_mode:u8 (0..2)
[template_state_root:h32] iff state_mode==1
popcount(branch_mask) × h32  (ascending slot)
[paths: Vec(Vec(CS))]    iff p==01   (shortest CS; ≤16 paths; ≤16 entries; each index <16)
no trailing bytes; total ≤ element cap (max 865 bytes)
```

Template-level errors (raised before scanning):
- `p == 11`, or `state_mode > 2`;
- the two masks overlap;
- `branch_count ≥ 1` and a mask bit ≥ `branch_count`;
- `p == 10` (INHERIT) in a mint invocation;
- `p == 10` with `burn = 1`;
- `burn = 1` and `p == 01` with a non-empty paths vector;
- `burn = 1` with `p == 00` and any pinned branch. Recommended reading: OMIT with burn skips the path check, so pinned roots are compared by slot only;
- a template state root that is all zero, when `state_mode == 1`.

Pop order (I-14a):
1. Pop `claim` (N, 0 ≤ claim ≤ 2^64−1, else Err).
2. Pop `template`.
3. If `v == 11`, pop `expected_value` (N, 0..2^64−1, else Err).
4. For the set bits of `branch_stack_mask` in **descending** slot order, pop 32 bytes each (wrong size is Err). The highest slot is on top, so the script pushes in ascending slot order.
5. If `state_mode == 2`, pop the 32-byte `expected_state` (zero is Err).

`Match(j)` is true iff all of the following hold:
- `IsBurn() == burn`.
- Value, by `v`: OMIT any; EXACT `==`; MIN `>=`; FROM_STACK `==`.
- Token, by `t`: OMIT any; NATIVE `!HasToken`; EXACT (zero ⇒ native, else `HasToken && id ==`); SELF `HasToken && id == BRANCHROOT`.
- If `branch_count ≥ 1`: `len(branches) == branch_count`.
- For every pinned slot `i` (static or stack): `i < len(branches)` and `branches[i] == root_i`.
- Paths, by `p`:
  - OMIT: if not burn, `RequiresBranch(root_i)` for every pinned root.
  - EXPLICIT: `paths == template_paths`.
  - INHERIT: `paths == coin.paths` and `len(branches) == len(coin.branches)`; for unpinned `i`, if `wild == 0` then `branches[i] == coin.branches[i]`.
    Outside INHERIT, bit 7 is accepted and has no effect (I-14e).
- State: mode 0 requires `!HasState`; modes 1 and 2 require `HasState && state_root == expected`.
(Superseded, user 2026-10-20: there is no per-output budget in `Match`; claims are assigned in phase 2.)

Scan `j` over the outputs in range (all outputs, or the one index of `output_mode` 1/2) and collect every match into the
match mask. If there is none, Err. Otherwise stage the record `(claim, mask)`, stage the authorization of every matched
output if `state_mode != 0`, and push nothing.

Cost:
`base + per_operand_byte·(template_len + Σpopped) + per_tx_output·output_count` (no result push).
The `per_tx_output` term is flat: it does not depend on the output mode or on how many outputs match, so the static
charge and the executed charge are the same. It pays for the scan and for the claim's phase-2 edges (at most one per
output); see the claim assignment section for how the node value 32 was chosen.
For the size pass, a literal template push immediately before the claim allows an exact pop count. Otherwise treat it as unknown and
charge `Worst(eb)` with operands at the limit. This needs the new `per_tx_output` coefficient in `VmOpcodeCost`
(defaults to 0; `CheckCostProfile` requires it to be > 0 for `eb`). [SIGN-OFF: the cost-model extension]

### 4.7 STATEHASH / STATEVERIFY / introspection (patches 063–065)

- `HashDomain::ContractState` → `"Lotus/v2/contractstate"` (I-13).
- STATEHASH streams the preimage into a BLAKE3 hasher; it never materializes it.
- `PreparedVmTransaction` precomputes a `std::unordered_map<Hash32, {u128 in, u128 out}>` (or a sorted vector) for TXTOKENBALANCE.
  Zero is the native key; spend coins go into `in`, all outputs into `out`.
  Reuse the totals logic in `ordinary_validation` by extracting it into a shared helper to avoid divergence.
- `DeriveFieldSizes` adds `0xdf`: a per-input maximum argument size, or the exact size for a literal `(i, w, a)` triple.
  This is optional; the conservative maximum is acceptable.

### 4.8 Signing, sighash and identities

- `state_root` sits inside `Bytes(Output)`, so OutputLeaf, OutputsRoot, TxID, TxHash, CoinEntry/CoinsRoot and OwnInputHash commit to it.
  No preimage layout changes. Fixed sizes stay fixed (the 32-byte digests), so the P01 lengths 138/150/178 are unchanged.
- ENFORCEOUTPUT effects and EMITLOG never enter any digest.
- INPUTWITNESSARG reads data that is outside TxID and sighash but committed by TxHash. Validity may depend on it, which is consistent with
  caches keyed by TxHash (verified).
- Nothing in `signing.cpp` changes except the shared `EncodeOutput`. Add regression vectors whose identities differ only by `state_root`.

### 4.9 Simulation evaluator (patch 068), recommended answers to I-15

- New TU `vm_simulation.cpp` and header `vm_simulation.h`, exported entrypoint
  `SimulationResult EvaluateVmSimulated(const SimTransaction&, const SimOptions&)`. It is **not** declared in `vm.h`.
  Consensus code cannot set the mode: `Machine` gets a `const bool simulation` that only this TU sets. Add a test that the consensus
  entrypoints reject `6c` while this one accepts it.
- `SimTransaction` = a draft transaction, which may have zero outputs and unsigned witnesses, plus resolved coins.
  Invocations run in the canonical order (§4.5).
- EMITLOG: k ∈ 0..64. Record `{input, witness, instruction offset, items[1..k]}`; the topic is the top item.
- Constructive ENFORCEOUTPUT. First try the strict match over the current outputs, including earlier drafts; this **is** the coalescing.
  If nothing matches, append a draft and match it:
  - value: EXACT or FROM_STACK value; MIN uses `template_value`; OMIT uses `claim`;
  - token: by mode (OMIT → native; SELF → BRANCHROOT);
  - branches: pinned roots; unpinned slots under INHERIT with `wild == 0` copy the coin; any other unpinned slot gets the placeholder
    `H("Lotus/v2/sim/placeholder", u16 draft ‖ u8 slot)`, which is distinct and flagged `wallet_fill_required`;
  - `branch_count`: the template value; if 0, use max(pinned slot)+1 (at least 1);
  - paths: explicit or inherited; OMIT gives the single path `[0..count−1]`;
  - burn: per bit 6 (burn ⇒ `paths=[]`);
  - state: the expected root when `state_mode != 0`.
  Report `{draft index, template bytes, popped values, claim, preceding "lotus.output.draft" event}`.
- CHECKSIG/CHECKSIGVERIFY/CHECKDATASIG: `SimOptions::signatures = Verify | AssumeValid`. With AssumeValid, a correctly sized signature
  pushes true and records a signing request (input, witness, mode, provisional digest).
- TXID, SIGHASH, OUTPUTRECORD, OUTPUTSTATEROOT and counts are flagged **provisional** in the result whenever drafts were appended.
- The post-check is reported, not enforced.

### 4.10 What the daemon exposes for the compiler, wallet SDK and indexers (patch 069)

Editions and `optimizer_version` are compiler-only; the daemon never sees them. The daemon exposes:

1. `getv2vmprofile`: the assigned-opcode inventory (single and EXT2) with a status, the `opcodes.json` SHA-256, `VmProfile`, `VmCostProfile`
   and their digests (the artifact "target profile digest"), plus loop and template limits.
2. `testv2transaction` (strict, non-mutating): per-invocation status, error string, accounting/enforcement cost, matched `j`/claims/authorizations,
   the final `unclaimed_value`, and the post-check result.
3. `simulatev2transaction` (§4.9): events, drafts, signing requests and provisional flags. Behind `-v2simulationrpc` (default on regtest/dev only). [SIGN-OFF]
4. Stable error strings for ENFORCEOUTPUT/STATEVERIFY failures (`enforce-no-match`, `enforce-template-*`, `state-mismatch`, `state-output-unauthorized`, …).
5. RPC and Chronik `stateRoot`. Chronik may index `branches[0]`/`branches[1]` by the slot convention (ABI §8). This is **index-only**:
   the daemon must not enforce the slot convention in consensus.

---

## 5. Patch-by-patch plan (V2 tier, appended to `lotus-v2-stack-repair/daemon/patches/v2/series` after `057`)

Each patch is one authored commit on the V2 tier, exported with the stack's existing tooling. Each must replay cleanly and keep every
intermediate tree buildable with its tests passing. Paths below are relative to the source root (`src/`).

| # | Title | Files | Tests |
|---|---|---|---|
| 058 | vm(v2): 16-bit opcode IR and EXT2 two-byte framing | `lotus_v2/vm.h`, `vm.cpp` (Scan, Instruction), `vm_cost.inc` (OpCost, CheckCostProfile, ext table), `vm_test/runner.cpp`, `test/fuzz/v2_vm_and_tx.cpp` | scan vectors §6.1 (lone `ff` Invalid, `ff00`/`ff4c`/`ffff` success, `01ff` push payload, `fe ff`, `ff` in a skipped arm) |
| 059 | vm(v2): sync opcode allocation with registry (retire 67/68, EMITLOG invalid, register new bytes) | `vm.cpp` (GenesisAssigned table, Scan 6c), `vm_test/opcode_coverage.json` (225 entries, new spec sha), `vm_test/check_opcode_coverage.py`, `differential*.py`, `test_vm.cpp` | registry equality test; `67`/`68` now AutomaticSuccess; `6c` Invalid everywhere incl. skipped arm/after RETURN/before success; new bytes Unsupported |
| 060 | vm(v2): unify loops on ENUMERATE with count-idiom static bound | `vm.cpp` (Structure/Execute), `vm_cost.inc` (SizePass idiom) | `c9 69 … 6a` at 0/1/256/257 inputs (257 → Err); nested ×2; cost equals the old 67 charge for identical bodies |
| 061 | vm(v2): conditional BREAK | `vm.cpp`, `vm_cost.inc` | cond 0 continues, 1 exits; depth 2; invalid depth with cond 0 still Err; non-Boolean cond Err; skipped-arm BREAK no Err; SizePass fall-through |
| 062 | output(v2): HAS_STATE state_root in wire, coins, RPC and Chronik | `lotus_v2/output.h/.cpp`, `transaction.cpp`, `field_size.cpp`, `disk_state.cpp`, `fast_sync.cpp`, `sparse_state.cpp`, `block.cpp`, `ordinary_validation.cpp` (interim reject), `primitives/transaction.h/.cpp`, `compressor.h`, `validation.cpp` (interim reject), `kernel/coinstats.cpp`, RPC/Chronik/wallet V2 output renderers | `test_output` (844 maximum, flags 0x04/0x05, reject 0x06/0x07/0xf8/zero root), `test_sparse_state` 900, primitives round-trip, compressor round-trip, identities differ by state root, coinbase reject |
| 063 | vm(v2): UTXOFLAGS, UTXOSTATEROOT, OUTPUTSTATEROOT, ACTIVEBRANCHINDEX, ACTIVEWITNESSINDEX | `vm.cpp`, `vm_cost.inc` (Transfer cases) | mint/coinbase errors; −1 in mint; zeros without state |
| 064 | vm(v2): TXTOKENBALANCE with prepared asset totals | `vm.h/.cpp` (PreparedVmTransaction), shared totals helper extracted from `ordinary_validation.cpp` | native/token/absent asset; mint delta = out−in; burn outputs counted; 31/33-byte asset Err |
| 065 | vm(v2): INPUTWITNESSARG, STATEHASH, STATEVERIFY, `Lotus/v2/contractstate` | `vm.cpp`, `vm_cost.inc`, `field_size.*`, `tagged_hash.h/.cpp` | index bounds per input kind; k=0/64/65; preimage vectors from Python; STATEVERIFY mint Err, missing state Err, mismatch Err |
| 066 | validation(v2): transaction-scoped VM effects, canonical order, post-check, per-tx script check | `vm.h/.cpp`, `ordinary_validation.cpp`, `validation.cpp` (V2 single check job), remove interim rejects from 062 | staged effects discarded on failure; HAS_STATE without authorizer rejects; parallel block connect gives the same result as sequential; `tl_cache` reuse does not leak effects |
| 067 | vm(v2): ENFORCEOUTPUT strict mode and OutputTemplate parser | new `lotus_v2/output_template.h/.cpp`, `vm.cpp`, `vm_cost.inc` (`per_tx_output`), `CMakeLists.txt` (both), `vm_test/CMakeLists.txt` | §6.3 matrix; flash-loan, mint+vault, N-to-1 merge, double-claim, greedy-order and forged-state (I-10) cases |
| 068 | vm(v2): non-consensus simulation evaluator (EMITLOG, constructive ENFORCEOUTPUT) | new `lotus_v2/vm_simulation.h/.cpp`, `vm.cpp` (simulation flag), CMake | consensus rejects 6c while sim accepts; draft construction rules; signing requests; provisional flags |
| 069 | rpc(v2): VM profile, test and simulate RPCs; Chronik stateRoot; functional tests | `rpc/` V2 file(s), Chronik bridge, `test/functional/feature_v2_vm_opcodes.py` (new), `test/fuzz/v2_vm_and_tx.cpp` | functional test: create, spend and continue a stateful vault; reorg/undo restores state roots and claims; RPC schema |

Stop at 058–061 if I-1, I-3, I-5, I-6 or I-7 are unsigned. Stop 062 on I-8/I-9, 066 on I-11, 065 on I-12/I-13, 067 on I-14/I-17,
and 068 on I-15.

---

## 6. Test vectors: what to generate and how

Use one generator, `src/lotus_v2/vm_test/generate_opcode_vectors.py`. It should **import, not copy**, the primitives from a pinned
`spec_candidate_checks.py` (`u, cs, blob, h, leaf, branch, indexed_tree_root, op, OPCODES, success_scan`), loaded by path and pinned by
SHA-256 the same way `opcode_coverage.json` pins `opcodes.json`. Patch `success_scan` locally for EXT2 (I-2) until the spec repo fixes
it, and assert that the patched result differs from the upstream result only on `ff`-containing cases. Write the output to
`vm_test/v2_opcode_vectors.json`, consumed by `test_vm.cpp` and `runner.cpp`. Run Python with `-I`. Where the reference VM covers the
opcodes, run the differential against it.

1. **Scan/framing:** all 31 single-byte success bytes; `67`, `68`; all 256 `ff xx`; lone `ff`; `ff` after a truncated push (error);
   `6c` in every position; the CHK cases re-run.
2. **Control:** ENUMERATE bounds 0/1/256/257; the idiom at counts 0/1/255/256/257; BREAK operand matrix {cond 0, 1, 2, non-16-byte} × {depth 0, 1, 2, 3}
   × {in loop, nested, skipped arm, top level}; expected status plus static and executed cost (unit schedule).
3. **ENFORCEOUTPUT matrix:** each value_mode × token_mode × paths_mode × burn × wild × state_mode over a fixed 4-output transaction.
   Mask overlap, out-of-range bits, truncation and trailing bytes; pop-order cases with three stack roots. Budget cases: 1-to-1 twice
   with identical templates (succeeds via unclaimed), N-to-1 (100+100 ≤ 200), over-claim (100+101 > 200). Greedy-order failure.
   Mint-only modes; INHERIT in a mint (Err).
4. **State:** STATEHASH digests for k=0,1,64 and items of length 0/16/8192; STATEVERIFY outcomes; HAS_STATE output bytes, OutputLeaf,
   TxID and each sighash mode with and without state; Coin record of 900 bytes.
5. **Introspection:** UTXOFLAGS, UTXOSTATEROOT, OUTPUTSTATEROOT, ACTIVE*, TXTOKENBALANCE and INPUTWITNESSARG per input kind (spend/mint),
   including out-of-range indexes.
6. **Example contracts:** hand-assemble the bytecode equivalents of EX `FlashVault.flash_loan`, `StakingMint.deposit_and_mint` and
   `StandardStakingVault.merge`, and run them in full-transaction contexts. Adversarial variants: a forged-state authorizer (I-10)
   expected **valid**, documenting the weakness; a value shortfall; a wrong token; dropped paths.
7. **Simulation:** given a zero-output draft, the drafts produced by each template; the EMITLOG event list.

Each vector records the registry SHA, generator commit, profile digest, script hex, arguments, transaction hex, resolved coins,
expected status/error class, final stack, costs and effects.

---

## 7. Cost accounting and block limits

- New coefficient `per_tx_output` for `eb` (flat per transaction output; static = executed). All new opcodes need a positive base, enforced by `CheckCostProfile`.
- Static (size-pass) charges must bound executed charges for every new opcode. Extend `differential_cost.py` to assert
  `executed ≤ static` over the §6 vectors.
- The worst cases per invocation, all bounded by `max_invocation_cost` and the transaction's `max_total_invocation_cost`:
  - ENFORCEOUTPUT: 65,535 outputs × each template check is O(16 + 16·17) comparisons;
  - STATEHASH: 64 × 8,192 bytes hashed;
  - INPUTWITNESSARG: copies ≤ 8,192 bytes.
- Per-transaction memory for effects is O(outputs). Asset totals are O(assets).
- The block-level `CheckInputsLimiter` and sig-check limiters stay per transaction, so the single-job change in patch 066 keeps their totals.
- Moving to one check per V2 transaction removes intra-transaction parallelism. Benchmark block connect with large V2 transactions
  (≥256 inputs) before and after. This is a performance risk, not a correctness risk.

---

## 8. Risks

1. **Order dependence and parallelism (I-11).** Missing one of the call paths, for example the `validation.cpp` CScriptCheck path, causes
   consensus divergence between mempool and block validation. Mitigation: one shared `RunV2TransactionScripts()` helper used by both paths,
   plus a parallel-vs-sequential test.
2. **Stale effects through `tl_cache`** in `validation.cpp`. Mitigation: effects are never stored in `PreparedVmTransaction`.
3. **The compressor silently drops the HAS_STATE bit** (verified bug if not fixed). This corrupts the coins DB and UTXO root.
   Mitigation: round-trip test in patch 062; reindex the dev chains.
4. **Genesis reallocation** breaks every existing script and branch root that uses 67/68, or that relied on the bytes now assigned
   being OP_SUCCESS. Mitigation: regenerate fixtures; confirm no persistent V2 network relies on them (assumption).
5. **The state-authorization weakness (I-10)** could lead to a false sense of security in contracts. Document it in the ABI and the
   compiler lints.
6. **The success-opcode soft-fork contract (I-17)** is now constrained.
7. **Spec churn:** HAS_STATE and ENFORCEOUTPUT are marked "Tentative" or "Recommended candidate". Freeze them before 062/067 merge.
8. **Cost schedule not frozen:** unit-schedule tests only. Mainnet constants remain a separate P05 obligation.
9. **Unverified interfaces:** RPC/Chronik render sites were not inspected; the reference Python VM is outside this repository.

## Follow-up: generic two-phase (deferred) checks (user, 2026-10-20)

The spec is WIP and the deferred rules will change as contracts get built, so
the post-check is a small generic mechanism, not ENFORCEOUTPUT-specific code.

- **Phase 1 (per input, parallel on CCheckQueue):** the VM runs one
  invocation and appends typed *effects* to that input's own slot, with no
  shared mutable state. Examples: an output claim `(output j, amount)`, a
  state authorization `(output j)`, and later kinds as the spec grows.
- **Phase 2 (per transaction):** registered *deferred check kinds* run over
  the transaction's collected effects once all its inputs have succeeded.
  ENFORCEOUTPUT's sum check and the HAS_STATE authorization check are the
  first two kinds.
  - Interface sketch:
    `struct DeferredCheck { name; bool Check(const PreparedTx&, Span<const InputEffects>, TxValidationState&); }`,
    plus a static registry.
  - Adding a kind means one effect type and one check, with no scheduler
    changes.
- **Optional phase 3 (per block):** a hook for future rules that span
  transactions. None exist yet, so it is a no-op with tests.
- **Scheduling stays separate from the kinds.**
  - Block connect: each transaction keeps an atomic count of pending inputs.
    The input job that reaches zero runs phase 2 for that transaction, so
    there is no block-wide barrier. A failed input marks its transaction
    failed and phase 2 is skipped.
  - Mempool acceptance and RPC test/simulate paths run phase 1 and then
    phase 2 inline.
  - The simulation evaluator reuses the same kinds.
- **Determinism:** phase 2 sees effects ordered by input index (then witness
  index), whatever order the inputs ran in.
- **Tests:**
  - Parallel and sequential block validation give identical results.
  - Each kind passes and fails.
  - A test-only dummy kind proves new kinds plug in.
  - Effects from a failed input never reach phase 2.

### Revision (user, 2026-10-20): accumulate inline against per-output counters

Instead of per-input effect lists checked afterwards, each check kind owns
per-transaction accumulators, for example one atomic counter per output.
Inputs update them as they run.

- **Upper-bound rules fail fast inline.** Example: claims on output j must
  not exceed its value. `fetch_add` the claim; if the new total exceeds the
  value, the transaction is invalid immediately. The outcome doesn't depend
  on order, because the final total is the same whichever input crosses the
  limit. Use 128-bit or overflow-checked addition.
- **Existence, lower-bound and equality rules need a final read.** Example:
  every HAS_STATE output was authorized by someone. Inputs set flags inline,
  but "nobody set it" is only knowable once all inputs are done. The final
  read is O(outputs) and runs in the input job that brings the transaction's
  pending-input count to zero.
- **Kind interface:** an accumulator type, an inline update (may fail), and an
  optional final check. A kind with no final check needs no phase 2.
- **Error reason:** valid/invalid is order-independent, but when a
  transaction breaks two rules, which reason gets reported could vary.
  Report the canonical reason by re-evaluating the failed transaction's rules
  in a fixed order. This is cheap and runs only on failure.
- **Script execution cache:** an input skipped because its script result is
  cached would contribute no claims or flags. V2 inputs that produce effects
  must either cache their effects with the result, or bypass the script cache.
  Start by bypassing it; the cache was keyed on pass/fail only.
- **Mempool, RPC and simulation paths** use the same accumulators
  sequentially.

### Unified accounting kinds (user, 2026-10-20)

Value conservation and ENFORCEOUTPUT claims use the same counter mechanism.
Inputs and outputs add to or subtract from counters; final rules check the
totals.

| Kind | Counter | Adds | Subtracts | Final rule |
|---|---|---|---|---|
| Native conservation | per tx | input values | output values (incl. burns) | >= 0, remainder is fee |
| Token conservation | per token id | input amounts, mint deltas | output amounts (incl. burns) | == 0 |
| ENFORCEOUTPUT claims | per output | output value (initial) | each script's claim | >= 0 at every step (fail fast) |
| State authorization | per HAS_STATE output | set by an authorizing script | — | must be set |

- **Conservation moves into this framework.** Structural contributions
  (output values, input values) are applied when the transaction is prepared.
  Script contributions (claims, authorizations) are applied by input jobs.
- **Order-free and atomic.** All kinds tolerate any order, so input jobs
  update them atomically and in parallel. The last input to finish runs the
  final rules.
- **Same rules everywhere.** Mempool, RPC and simulation run the same kinds
  sequentially.
- **Contract rules plug in as new kinds.** A new rule is one more row: a
  counter, its contributions, and a final rule.

### ENFORCEOUTPUT claim assignment (user, 2026-10-20) — supersedes the per-output counter rows above

- **Consensus rule:** a transaction is valid only if there exists an
  assignment of every ENFORCEOUTPUT claim to an output its template matches,
  such that no output's assigned claims exceed its value. No other shape rule
  and no special cases.
- **Phase 1 (per input, parallel):** each ENFORCEOUTPUT checks its template
  and records `(claim amount, match mask over outputs)`. A template that
  matches no output fails immediately. ENFORCEOUTPUT never pushes an output
  index.
- **Phase 2 (per transaction):** one feasibility check by max-flow (source
  -> claims -> matching outputs -> sink, capacities = claim amounts and output
  values; feasible iff the max flow equals the total claimed).
- **One code path for every transaction.** No fast path for single-match
  claims, at least until it is measured and needed; any later optimization
  must be proven equivalent.
- **Splitting is intended (user, 2026-10-21).** The flow may divide one
  claim's amount among several outputs its template matches; that is the
  point of the rule. Assigning a whole output to one claim is already
  expressible with SIGHASH_SINGLE.
- **Cost (user, 2026-10-21, supersedes the per-pair weight):** each
  ENFORCEOUTPUT costs a flat `per_tx_output × number of transaction outputs`,
  one constant, identical in the static and the executed charge. A claim has
  at most one edge per output, so the charge is at least the constant times
  the claim's edges. The node value is 32: on the ladder benchmark (the
  slowest assignment found, `bench/v2_claim_flow.cpp`) one edge at the cap
  takes 22–27 cost units of VM time.
- **Per-transaction cap:** `MAX_TX_CLAIM_PAIRS = 4096` (claim, matching
  output) pairs, failing with `claim-pairs-exceeded`. It is still needed:
  the node budget is per invocation (`max_invocation_cost`), with no
  per-transaction total, so 256 inputs could together record far more pairs
  than the cost of phase 2 at the cap was measured for (about 5 ms).
- **The other kinds are unchanged:** native/token conservation and state
  authorization stay as above.
