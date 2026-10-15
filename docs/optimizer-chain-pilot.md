# Optimizer complete-block pilot prerequisite

Review checkpoint: monorepo `642d0e3b`, inspected in a new worktree created from
`8914db5177d7b97fa7aa7d04172f71ead633775c` and fast-forward merged to that
checkpoint. This packet is a bounded test design and prerequisite report.
No optimizer complete-block test has executed.

## Reuse boundary

The existing [development-chain pilot](../tools/lotus-v2-compiler/test/development-chain-pilot/run.py)
is an executable script. Importing it parses process arguments, exclusively
creates its output directory, compiles an artifact and executes the entire chain.
Its `node()` helper hardcodes the sibling `payment.mjs`. That module hardcodes
Payment source, default optimization, method `spend` and one Signature argument.
The Python driver also assumes bad-signature failures name CHECKSIGVERIFY;
unoptimized CHECKSIG plus VERIFY need not expose the same diagnostic.

There is no callable interface accepting a compiler source/options/argument
producer, nor an injected compiler command. Importing through runpy, mutating
subprocess behavior, replacing sibling files or rewriting the script in memory
would couple the new test to private executable details. Copying the complete
block/monetary/undo harness would create an independent maintenance obligation.
The requested extension therefore needs a reusable pilot interface first.
Existing pilot files and consensus code are unchanged.

## Bounded intended gate

Use the exact reviewed daemon build at
`/private/tmp/lotus-v2-daemon-costs-exact-20261015/build/src/lotusd`, source
`dca9abe76`, and caller manifest
`/private/tmp/lotus-v2-command-repro-artifacts-20261015/manifest.json`.
Record complete manifest and binary digests when execution becomes possible;
paths and source labels alone are not execution evidence.

Run three source families with optimization both disabled and enabled:

| Family | Contract obligation | Negative mutation |
| --- | --- | --- |
| Payment | Valid authenticated signature | Changed signature |
| Payment with argument equality | Signature and integer equality | Wrong integer; changed signature |
| Payment with literal expressions | Signature and folded arithmetic/Boolean requirement | Changed signature; separate false-literal source baseline |

Create fresh exclusive evidence directories and offline chain homes for each
artifact. Compile, instantiate policy, fund the resulting policy root, mature
its coinbase, prepare and sign against the actual resolved coin and transaction,
and construct complete mined blocks independently. Require native/reference
agreement on accepted/rejected outcomes, authenticated invocation and block
accounting/enforcement charges, restart state, disconnect and reconnect. Each
negative must preserve its rejected bytes and unchanged tip/state evidence.
For a false-literal source, first establish the separate rejecting program;
it is not a mutation that should preserve the accepted program's obligations.

Across optimization settings compare contract obligations and accepted/rejected
outcomes under the supplied nonbinding profile. Retain each artifact's script,
policy root, transaction IDs/hashes, block roots and charges separately. Changed
scripts require new funding and signatures; equality of roots or charges is not
an optimization requirement. Preserve the existing
[exact-cap discrepancy corpus](../tools/lotus-v2-compiler/fixtures/optimizer-equivalence/observations.json),
including equalverify charge 14 versus 6 under its explicit unit-cost profile;
that profile is distinct from the caller pilot manifest. Do not convert cap
acceptance differences into a same-profile equivalence claim.

## Required reusable interface

The existing pilot owner can expose a guarded `main()` and a callable run function
that accepts an artifact/signing adapter (or compiler command), method and typed
arguments, expected semantic rejection categories, and exclusive output path.
Keep full-block construction, authenticated costing and native/reference
connect/disconnect logic in the shared implementation. The adapter should return
source/artifact, valid finalized wire and named negative finalized wires. It must
not bypass transaction preparation, resolved-coin authentication or re-signing.
After that prerequisite, the new optimizer test can be a thin explicit opt-in
matrix wrapper under `tools/lotus-v2-compiler/test/optimizer-chain-pilot/`.

No daemon command, node, socket, parameter adoption, golden update or consensus
change was made during this inspection. Existing signed Payment pilot evidence
is not evidence that the optimizer matrix has passed.
