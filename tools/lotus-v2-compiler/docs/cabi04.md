# CABI04 executable covenant packet

This packet is partial CABI04 coverage, not completion of its acceptance gate.
It adds five independently compiled ordinary invocation examples. Existing mint
and transfer examples remain the token coverage. No transaction, accounting,
block acceptance, signature authorization or native VM claim follows from these
invocation tests.

| Example | Executed behavior | Remaining scope |
| --- | --- | --- |
| Counter | One same-policy, same-asset successor with value decremented by one | This is a token-amount countdown, not arbitrary committed application state |
| Vault | Exactly one successor preserves amount, asset and required branch | Owner authorization and recovery lock |
| Limit order | Exactly one quote output pays the fixed amount to a required seller policy | Partial fill arithmetic, offered-asset delivery, authorization and transaction conservation |
| Merge | Exactly two spend inputs of the same asset, one same-policy output with their sum | Both invocations run independently; transaction validator must resolve distinct outpoints and check every input policy |
| Cartesian | Every input/output pair preserves asset and required branch; nonempty inputs/outputs | Authorization, conservation and performance measurements |

The counter requires a positive current value and disallows missing or duplicate
successors. It consumes an asset unit; accounting/burn semantics require a
separate transaction-level fixture. Its amount representation must not be
mistaken for an arbitrary state branch commitment. Vault continuation itself
provides no recovery authorization. LimitOrder deliberately constrains only
quote settlement, so other asset outputs need transaction/application checks.

The companion `examples/gallery/cabi04-scenarios.json` supplies explicit cases.
The test runs seven positive invocation contexts (including both merge inputs)
and 25 adversarial contexts: amount/state-encoding substitution, asset swaps,
missing/duplicate successors, weaker successor policy and wrong merge counterpart.
Every negative must fail at execution; an unsupported VM feature fails the test
and is never counted as a rejection. Expected source behavior is a manually
specified oracle, not an independent source-language interpreter.

Three additional source intents must produce compiler diagnostics: arbitrary
stateful continuation, recovery lock checking, and explicit successor path
checking. These are unsupported frontend behaviors, not rejected transactions.
Recovery immediately before/at its lock boundary remains unexecuted until the
frontend and reference context support the existing P03 lock operations.

Run from the compiler directory:

```sh
npm ci --ignore-scripts
npm run build
LOTUS_V2_PYTHON=/path/to/reference-venv/bin/python \
LOTUS_V2_CABI04_RESULTS=/tmp/cabi04-results \
node --test test/cabi04-gallery.test.mjs
```

The Python environment needs the reference package dependencies. Optional
`LOTUS_V2_VM_REFERENCE_PACKAGE` selects another reference package checkout.
Results preserve source, complete compiler artifact (including bytecode), exact
invocation/profile, source expectation and reference verdict after every case,
including a mismatch before the assertion fails. No fixture regeneration changes
expected outcomes. Local verification used the provided review Python environment;
eight tests passed, without skips. Results are at `/private/tmp/cabi04-results`.

Next frontend work must define byte encodings and authentication for state rather
than introducing a fictitious UTXO state field. Runtime state branch commitment
checks and successor branch/path constraints need typed syntax. Recovery needs
lowering to existing P03 lock opcodes plus contextual lock fixtures at the boundary.
