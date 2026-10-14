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
operations outside this slice raise `UnsupportedFeature` if reached. In
particular signature verification, CHECKDATASIG profiles, BLAKE3, Merkle
operations, transaction/UTXO/output introspection and lock checks are not
implemented. `UnsupportedFeature` is a tool error, not consensus acceptance.
The reference is not a complete VM or transaction validator.

Run `PYTHONPATH=tools/lotus-v2-reference python3 -m unittest discover -s
tools/lotus-v2-reference/tests -v` from this worktree root. Fixed tests cover
success bytes in skipped code and data pushes, malformed framing before and
after success, syntax in unreachable arms, boolean and int128 boundaries,
stack caps, full loop charges and unsupported assigned instructions.
P05 charge tests also cover exact short operands, conditional merges,
underflow in skipped arms, accumulating loops, equal and unequal BREAK exits,
constant-index and variable-index field reads, and nested input/output loops.

Open specification dependencies: P03's opcode allocation and P05's primitive
cost coefficients and hard resource constants remain candidates. Field-size
vectors require trustworthy parsed transaction/coin context, which this VM
slice does not provide. Unimplemented assigned operations use conservative
Unknown bounds when their stack effects are not modeled; they still raise
`UnsupportedFeature` if reached by execution.
This slice therefore cannot select a mainnet cost schedule or demonstrate
that a particular block fits the eventual economic limits.
