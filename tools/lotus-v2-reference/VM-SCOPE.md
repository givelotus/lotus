# Bounded V2 VM reference slice

This review candidate implements the P03 instruction-boundary success scan,
canonical fixed and `PUSHDATA` framing, complete structured decoding of
success-free scripts, and a bounded interpreter for common literals, control,
stack, bytes, arithmetic, SHA256 and HASH256 operations. The allocation is
the 2026-10-14 `docs/lotus-v2/tools/opcodes.json` snapshot with SHA-256
`fb790b230e76befc90a1f183ea727cb3232d1f03e9b5838b10d025d96b9832da`.
The 215 assigned bytes are represented by exact intervals in `vm.py`; the
other 41 bytes invoke P03 automatic success at an instruction boundary.

`evaluate(script, args, profile, input_count=0, output_count=0)` accepts an
explicit `VMProfile` with structural caps and opcode charges. The schedule is
copied into an immutable mapping at profile construction. Each charge is
either a positive constant or a callable taking `(operand_size_bounds,
result_size_bounds)` and returning a positive integer. The caller must supply
conservative nondecreasing formulas; this candidate does not select mainnet
coefficients. Its static cost uses P03's sequence sum, conditional maximum and
full loop bound, with checked u128/cap arithmetic. The `vm_cost.py` pass
follows P05's Known/Unknown stack-size abstraction, merges conditionals,
widens loops with at most two body analyses, and tracks BREAK exits. Unknown
shapes charge MAX_ELEMENT_BYTES for up to six operand and four result slots;
this may overcharge. Cost functions must accept those conservative vectors.
Callers may
provide `field_sizes` vectors for `UTXOOUTPUT`, `OUTPUTRECORD` and path reads;
missing context falls back to the element maximum. This pass only selects
charges; runtime limits and stack checks still enforce validity. The result's
charge covers script bytes and VM instructions only; transaction, witness,
proof, state and block charges stay with the enclosing validator.

Automatic success skips ordinary decoding/execution and returns no stack.
The caller still must validate witness framing, authorization membership,
locks, other required branches and all enclosing resource limits. The helper
checks only script and argument caps from the supplied profile. Assigned
operations outside this slice raise `UnsupportedFeature` if reached. BIP340
`CHECKSIG` and `CHECKSIGVERIFY` use coincurve 21 against explicit 32-byte
P01 message digests supplied in a `SigningContext`. The context requires a
selected P02 leaf hash, and the VM recomputes that hash from the exact script
bytes; it does not construct or authenticate a transaction's `SigMessage` or
prove branch membership. Partial modes require a spend context; mode 02 also
requires a paired output. Wrong framing and malformed keys error, while a
well-framed invalid signature produces canonical `N(0)`. Opcode `ba`
computes unkeyed 32-byte BLAKE3 directly over its byte operand with no Lotus
application tag. CHECKDATASIG profiles and other Merkle operations,
the `UTXOREQUIRESBRANCH` and `OUTPUTREQUIRESBRANCH` path predicates, and the
input/output count, flags, value, token ID, invocation kind, index and branch
root reads needed by the P03 token examples are implemented against an
explicit `InvocationContext`. Other transaction/UTXO/output introspection
and lock checks are not implemented.
`UnsupportedFeature` is a tool error, not consensus acceptance.
The reference is not a complete VM or transaction validator.

`InvocationContext` holds immutable, locally checked input and output views.
For a spend it checks that the selected branch root occurs on the selected
path of the resolved coin. For a mint it checks that the active input is a
mint with the branch root as its token ID, and pushes the positive `mint_delta`
as an `N` above witness arguments. That implicit value counts toward stack,
element, VM-byte and static-cost bounds but not `MAX_ARGUMENTS`. Output
`REQUIRESBRANCH` is true only when a spendable output includes the given
32-byte root on **every** path; merely listing the root among its branches
does not suffice. A missing or bypassable root returns canonical `N(0)`.
Counts and mint-input count come from the context, and explicit duplicate
counts must agree. The context does not resolve outpoints, prove coin or
branch membership, authenticate the claimed mint delta, or check asset
conservation. A transaction validator must supply and authenticate those
facts, as well as the selected path and branch indices. `SigningContext`
matches invocation kind, input index and output count, and authenticates only
that its selected leaf hash matches the script. It has no selected branch
index; the enclosing validator must bind its message digest to the proven
branch and exact transaction.

Install the signing dependencies in an isolated Python 3.13 environment with
`pip install -r tools/lotus-v2-reference/requirements-vm.txt`. The CLI accepts
one JSON invocation on stdin or from a file:

```sh
PYTHONPATH=tools/lotus-v2-reference python3.13 -m lotus_v2_reference.vm_runner case.json
```

The JSON object has `script` and `args` as hex, `profile` with every
`VMProfile` cap and `opcode_costs` keyed
by two-digit opcode hex, and optional `signing` with `selected_leaf_hash`,
`messages` keyed by decimal mode, `invocation_kind`, `input_index` and
`output_count`. It may include `invocation` with `inputs`, `outputs`,
`invocation_kind`, `input_index`, `branch_root`, an explicit `output_profile`,
and for a spend `selected_path_index` and `selected_branch_index`, or for a
mint `mint_delta`. Each input has `flags` and either a resolved `coin` or
`mint_token_id`; each output/coin has `flags`, `value`, nullable `token_id`,
`branches` as root hex strings, and `paths` as index arrays. Counts are
derived from the context; without it, explicit `input_count` and
`output_count` are required. Supplied counts must agree with the context.
An opcode charge is a positive integer or an object with
`base`, `operand_byte` and `result_byte` coefficients. Each coefficient must
be nonnegative and `base` positive. The runner emits a stage-only trace,
invocation result and calculated script/VM cost. Its caller must derive the
message digest from an independently validated transaction and selected
method; a supplied digest is an explicit assertion, not proof of a payment.

Run `PYTHONPATH=tools/lotus-v2-reference python3 -m unittest discover -s
tools/lotus-v2-reference/tests -v` from this worktree root. Fixed tests cover
success bytes in skipped code and data pushes, malformed framing before and
after success, syntax in unreachable arms, boolean and int128 boundaries,
stack caps, full loop charges and unsupported assigned instructions.
P05 charge tests also cover exact short operands, conditional merges,
underflow in skipped arms, accumulating loops, equal and unequal BREAK exits,
constant-index and variable-index field reads, and nested input/output loops.
Published BIP340 vectors test exact 32-byte-message Schnorr verification,
wrong-message behavior and invalid x-only key framing. Runner tests exercise
an actual `PUSH_32 owner CHECKSIG` invocation with explicit illustrative costs.
The BLAKE3 opcode is checked against the official unkeyed empty-input vector
and through the JSON runner with an explicit size-based charge.
P03 hand-assembled token transfer, mint issuance and token upgrade scripts
exercise required-path behavior, mint delta placement, signing failure,
context/count mismatches and the same multi-input, multi-output shape used
by the compiler gallery. These tests establish the invocation behavior, not
end-to-end transaction validity or a consensus resource schedule.

Open specification dependencies: P03's opcode allocation and P05's primitive
cost coefficients and hard resource constants remain candidates. Field-size
vectors require trustworthy parsed transaction/coin context, which this VM
slice does not provide. Unimplemented assigned operations use conservative
Unknown bounds when their stack effects are not modeled; they still raise
`UnsupportedFeature` if reached by execution.

Primitive API references: [coincurve 21](https://ofek.dev/coincurve/api/) and
[BIP340 test vectors](https://github.com/bitcoin/bips/blob/master/bip-0340/test-vectors.csv).
The unkeyed hash vector is from the
[BLAKE3 reference vectors](https://github.com/BLAKE3-team/BLAKE3/blob/master/test_vectors/test_vectors.json).
This slice therefore cannot select a mainnet cost schedule or demonstrate
that a particular block fits the eventual economic limits.
