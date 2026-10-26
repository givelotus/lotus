# CABI06 optimizer equivalence preparation

This packet prepares a retained corpus for the existing optimizer. It does not
complete CABI06 or establish daemon acceptance. No optimizer source changes
were needed: no semantic optimizer bug was demonstrated.

[corpus.json](../fixtures/optimizer-equivalence/corpus.json) contains nine
programs and 24 argument cases. [observations.json](../fixtures/optimizer-equivalence/observations.json) retains source, both scripts,
arguments, independent Python VM results, per-artifact P02 branch leaves,
accounting/enforcement charges and exact-cap boundary observations. The test
compares the complete record exactly. No regeneration mode is supplied; changed
observations require investigation. Initial observations were captured 2026-10-15.

The explicit development profile uses script/element bounds 8192, 8 arguments,
128 main-stack items, 16 alternate-stack items, 16384 VM bytes, AST depth 32,
invocation cap 1000000, structural byte weight 1 and weight 1 for every assigned
opcode. These are caller inputs, not launch parameters or calibrated costs.
Accounting and enforcement coincide for this unchanged assigned-opcode schedule;
future extension repricing is untested. Failure charges are independently computed
before execution; malformed arguments can reject before a charge is admitted.

The [independent Python helper](../test/cabi06-reference.py) explicitly asserts
wide-cap acceptance/rejection equality and accepted stack bytes,
success and automatic-success status before the snapshot comparison. The explicit
1000000 cap does not bind any corpus case; no infinite profile is claimed.
Failure diagnostics remain separately
recorded because fused instructions can report differently. Coverage includes
EQUALVERIFY, CHECKSIGVERIFY, literal arithmetic/Boolean folds, noncanonical bool
and int arguments, signed i128 extrema, retained overflow failures, skipped
overflow and two loop iterations.

Successful unoptimized/optimized invocation charges are:

| Program | Unoptimized | Optimized |
| --- | ---: | ---: |
| equalverify | 14 | 6 |
| literal-arithmetic | 38 | 2 |
| bool-canonical | 16 | 8 |
| max-overflow (argument zero) | 18 | 12 |
| branch-skips-overflow | 44 | 40 |
| loop-literal | 28 | 10 |
| checksigverify | 46 | 38 |

Each artifact pair also executes under identical caps at both charges and one
below each, plus cap 1. Cap 6 admits optimized equalverify and rejects its
unoptimized artifact. These are retained discrepancies against literal
same-profile preservation. Semantic preservation with sufficient resources is a
narrower property. Roots and costs can intentionally change when compiling a
new artifact; its commitments must be reinstantiated and signatures recreated.
No fee/parabolic cost or full-state-root equivalence is inferred from branch leaves.

Signed cases execute the public BIP340 fixture key/signature over a zero message
through Python SigningContext, binding each artifact's selected leaf separately.
Valid, altered-signature and invalid-length cases check VM fusion semantics. The
synthetic digest is not authenticated from a transaction. Native execution and
authenticated signing remain sequential integration gates pending the contextual
native runner. Signed native unsupported results must not be called rejection.

Run from `tools/lotus-v2-compiler` after installing reference VM dependencies:

```sh
npm ci --ignore-scripts
npm run build
LOTUS_V2_PYTHON=/private/tmp/lotus-v2-compiler-review-venv/bin/python \
  node --test test/cabi06-equivalence.test.mjs
```

The subprocess has a 30-second wall-clock and 4 MiB output bound. Unsupported
reference execution fails visibly. BREAK, skipped malformed bytecode, automatic
success scanning, size-sensitive profiles, native comparison, authenticated
re-signing, transaction/fee/state commitments remain further preparation.
Connect/disconnect, durable undo/reorg and development-chain pilots remain later
gates. This packet starts no node or network service.
