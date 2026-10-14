# Lotus V2 encoding reference: first output slice

This is an independent Python reference for candidate C04/P01 fixed-width integers, shortest CompactSize, bounded `Bytes`/`Vec`, and the complete `Output` grammar. It accepts an **explicit** `Profile`; the profile in `fixtures/outputs-v1.json` exercises the candidate's 16-branch, 16-path and 812-byte hard caps and an illustrative 8192-byte `Bytes` cap. It is a test profile, not a production parameter selection. Callers may select stricter bounds. An output decoder consumes exactly one frame and rejects surplus bytes.

It does not decode transactions, coinbase or input authorization, calculate commitments, run scripts, verify signatures, check asset accounting, or decide whether an output is valid in block context. Burn outputs are syntactically valid; state pruning happens elsewhere. This is validation support for future ABC daemon changes and is not an ABC patch.

Run from the monorepo root:

```sh
PYTHONPATH=tools/lotus-v2-reference python3 -m unittest discover -s tools/lotus-v2-reference/tests -v
```

`fixtures/outputs-v1.json` is a versioned, hand-reviewed wire corpus. Tests compare both encoder and decoder to those fixed bytes; they never regenerate fixture expectations. The first two output wires also match the *working-tree* structural fixture `ordinary_op_one_fixture.output` and `.burn_output` at the SHA-256 below, checked independently with this decoder on 2026-10-14. The inherited worktree HEAD fixture differed, so it is deliberately not a dynamic test dependency. The comparison decoded both wires and re-encoded them byte-for-byte (45-byte spendable and 43-byte burn output); no discrepancy was found for these applicable fields. Other structural fixture fields are outside this slice.

Source snapshots consulted (SHA-256 of the then-current uncommitted source; no copies committed):

| Path | SHA-256 |
| --- | --- |
| `docs/lotus-v2/decisions/encoding-and-signatures.md` | `9a5c7b7393281db8bf4319aca2db6209c87cee785dba0b6f730d53a7ab5407a3` |
| `docs/lotus-v2/decisions/commitments-and-state.md` | `82510831cdba20e326105490935bf38843896f9eec4599a0ca440e8ed25e2b8f` |
| `docs/lotus-v2/decisions/resources-and-parameters.md` | `ca120833322c78ffca2a43c04532a121d308dd33776fc394ee90082dc51582d7` |
| `docs/plans/implementation-entry.md` | `4e2b28be06d840cc781662dbcefb6f02b8274f7c296e249730637f3184cb6042` |
| `daemon/docs/lotus-v2-implementation-plan.md` | `04827db9f91f539a1dc1a2151d56b3331b5e71c69b79a38b5d1b989fa76e329d` (initial read) |
| `docs/lotus-v2/examples/candidate-smoke-vectors.json` | `854734ecbf7f538c107d4b95431c62a529e39e3477c2dbfdc88e96df0a538136` (comparison snapshot) |

Open specification point for the implementation owner: P01 says to check additions/multiplications against overflow without choosing a machine width for parser offsets. This reference uses Python's exact integers and bounds every declared count by the profile and remaining frame bytes before constructing any tuple. ABC must implement equivalent checked arithmetic in its chosen integer widths; tests should cover counts near each width boundary and truncated frames.
