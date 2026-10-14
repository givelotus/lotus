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
explicit `VMProfile` with structural caps and opcode charges. The profile
must supply a positive conservative worst-operand charge for every executed
instruction, including delimiters; the reference has no implicit mainnet
limits or coefficients. Its static cost uses P03's sequence sum, conditional
maximum and full loop bound, with checked u128/cap arithmetic. It uses
worst-operand charges supplied by the caller and does **not** yet implement
P05's per-operand size pass. Thus the caller must not pass prices for actual
runtime operand lengths. The result's charge covers script bytes and VM
instructions only; transaction, witness, proof, state and block charges stay
with the enclosing validator.

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

Open specification dependencies: P03's opcode allocation and P05's primitive
cost coefficients, hard resource constants and size pass remain candidates.
This slice therefore cannot select a mainnet cost schedule or demonstrate
that a particular block fits the eventual economic limits.
