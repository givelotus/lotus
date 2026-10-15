# CABI05 invocation differential harness

Build with `npm ci --ignore-scripts && npm run build` in this compiler directory.
Run explicitly (output directory must be new):

```sh
LOTUS_V2_PYTHON=/path/to/reference-venv/bin/python \
LOTUS_V2_NATIVE_VM=/path/to/lotus_v2_vm_runner \
node test/differential/run.mjs /tmp/cabi05-run 79225
```

An optional third argument loads an existing `lotus-v2/differential-corpus/1`
JSON corpus with `seed` and `cases`. The committed `test/differential/corpus-v1.json`
is a deterministic replay input. Cases preserve source, complete compiler artifact,
exact script, arguments, profile and context. Independent hand bytecode remains
beside generated compiler output. The compiler is an artifact producer, not a
third VM. Artifact roots and leaf hashes are recorded; Python independently
computes the same script leaf. No optimizer comparison or recompilation occurs
between engines. Signed cases use the existing compiled payment fixture and its
public signature; the second case mutates one signature byte.

The Python adapter invokes the reference JSON runner. Unsigned native cases use
`--charge SCRIPT INPUTS OUTPUTS ARGS...`; signed cases require the extended runner
`--context FULL_TX CHAIN_ID INPUT_INDEX WITNESS_INDEX RESOLVED_COIN...`, which
extracts script and arguments from the exact full transaction. Its output is
`STATUS ACCOUNTING ENFORCEMENT STACK...` (legacy unsigned runner has only the
first two fields). S/A accept, I rejects, U is unsupported. Missing executable is
explicitly unsupported; broken protocols, timeout and launch failures are tool
errors. Neither status is converted into consensus rejection. A configured old
runner lacking `--context` produces a tool error, never a signed pass.

Every invocation has a five second timeout and 1 MiB output bound; corpus size is
bounded at 256. Node version, OS, architecture, profiles and elapsed process times
are retained. These are process bounds, not measured peak memory or device
calibration. Unsigned profile matches native `--charge` except the native dynamic
step cap (100000) and static charge cap (10000000) are distinct; Python exposes
only the latter. Native context profile uses its explicit larger limits. Do not
use this corpus to assert step-limit equivalence.

Reports retain accept/reject/unsupported, roots, charges and available stacks.
Python currently exports a single accounting charge, so separate enforcement is
null; legacy native unsigned mode lacks final stack. Comparisons include only
fields exported by both engines. Missing fields are coverage gaps, not equality.
This is bounded invocation evidence, not full transaction or block acceptance.
Signed Python receives prepared signing digests; native derives them from full
bytes and resolved coins, providing an independent check at that boundary.

Disagreements produce individual executable case JSON beside `report.json`.
Creation is exclusive and never replaces earlier reports or expectations. Exit
status is nonzero for discrepancies/tool errors. Unsupported counts are printed
separately. No automated golden regeneration or consensus repair exists. Failure
minimization is deferred: preserving a full context is preferable to a reducer
that silently changes the signing obligation. The tests exercise retention using
an explicit injected disagreement; it is labelled synthetic and is not an engine
bug claim. Observed engine mismatches must be kept as actual replay inputs.

This packet does not cover maximum proofs, maximum loops, mixed transactions,
outer resource budgets, complete accounting/enforcement equality, or performance.

Native leaf values in the report are adapter-derived from the transmitted script;
they are not exported by C++. Python leaf values are independently computed.
Native roots therefore are not an independent root equality gate. The committed
corpus recorded 17 invocations without observed discrepancies using the extended
runner; the default generator recorded 53. This finite evidence does not imply
blanket equivalence.

## Authenticated signed context followup

New generated signed cases and `authenticated-corpus-v1.json` supply
`transaction_context` to Python. Both engines receive identical full transaction
bytes, ChainID, active input/witness indices and resolved coin frames. Python
checks the explicit script/arguments against that witness, authenticates proofs
and derives its signing messages; no trusted digest is supplied. The adapter
requires the authenticated-context API, so an older reference cannot silently
ignore the new field. Set `LOTUS_V2_REFERENCE_PATH` to the updated reference root;
the linked-library tests additionally support `LOTUS_V2_VM_REFERENCE_PACKAGE`.

The original `corpus-v1.json` is preserved as historical trusted-digest coverage.
It does not provide the new signing derivation gate. Replay the new signed corpus:

```sh
node test/differential/run.mjs /tmp/cabi05-authenticated 79225 test/differential/authenticated-corpus-v1.json
```

The CLI now includes Escrow, Payer and Receiver compiled from the existing linked
package fixture, including the unchanged compiler artifacts and original module
sources. Valid calls, signature mutations and the existing wrong-root constraint
are executed through Python authenticated contexts and native `--context`.
Tests also reject explicit script-argument/witness disagreement. This replaces
the obsolete linked-library test that invoked context-free native CHECKSIG and
reported permanently unavailable signing. Full transaction and block acceptance
remain separate stages. Earlier retained reports and corpora are not replaced.
