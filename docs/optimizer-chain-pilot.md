# Optimizer complete-block pilot

This explicit opt-in gate reuses the shared
[development-chain pilot](../tools/lotus-v2-compiler/test/development-chain-pilot/run.py)
through `PilotConfig` and `run_pilot`. The original inspection at monorepo
`642d0e3b` found no reusable interface; the shared pilot owner supplied the
configurable API before this matrix could run. The new files contain compiler
adapters and assertions, with no copied block-construction or undo implementation.

## Bounded matrix

Run three source families with optimization disabled and enabled:

| Family | Obligation | Rejected mutation |
| --- | --- | --- |
| Payment | Authenticated signature | Changed signature |
| Payment with integer equality | Signature and x == 1 | Independently signed x == 2; changed signature |
| Payment with literal expressions | Signature, constant arithmetic and Boolean requirements | Changed signature |

Each artifact has its own fresh exclusive offline home and evidence directory.
The shared implementation independently funds its policy, matures the coinbase,
prepares the resolved-coin transaction, signs, constructs/mines complete blocks,
and compares native/reference acceptance and invocation/block accounting and
enforcement charges. It checks restart, rejects immature/bad-signature spends,
disconnects and reconnects the valid spend. The equality variant adds a validly
signed wrong-integer transaction, ensuring rejection is not just bad authentication.

The matrix compares semantic accepted/rejected outcomes across optimization
settings. It retains separate source/artifacts, script bytes, policy roots,
transaction identities, full blocks, charges and final state roots. Changed
scripts must be funded and signed separately; identical roots or costs are not
asserted. An explicit assertion confirms these source families actually optimize
and produce different policy/final-state commitments.

The original
[exact-cap observations](../tools/lotus-v2-compiler/fixtures/optimizer-equivalence/observations.json)
are read without changes, hashed and copied as retained cap discrepancies.
For example equalverify charge 14 versus 6 changes admission at cap 6 under
that corpus's unit-cost profile. That profile differs from the caller's block
manifest. Neither record is converted into a same-profile cost-preservation claim.

## Run and retained evidence

After `npm ci --ignore-scripts` and `npm run build` in the compiler directory,
run with explicit paths and an unused output directory:

```sh
PYTHONPATH=tools/lotus-v2-reference \
/private/tmp/lotus-v2-compiler-review-venv/bin/python \
  tools/lotus-v2-compiler/test/optimizer-chain-pilot/run.py \
  --manifest /private/tmp/lotus-v2-command-repro-artifacts-20261015/manifest.json \
  --daemon /private/tmp/lotus-v2-daemon-costs-exact-20261015/build/src/lotusd \
  --daemon-source dca9abe76 \
  --output /private/tmp/lotus-v2-optimizer-chain-evidence-20261015
```

The optional unittest reads `LOTUS_V2_PILOT_MANIFEST`, `LOTUS_V2_PILOT_DAEMON`
and `LOTUS_V2_PILOT_DAEMON_SOURCE`. It preserves its temporary evidence directory
on both success and failure and checks repeated execution cannot overwrite it.
`matrix.json` contains the six artifact summaries; per-run directories retain
manifest/binary digests and native/reference command evidence. Each shared pilot
bounds subprocesses; the optional matrix subprocess has a 180-second timeout.

This is offline daemon command validation against caller development parameters.
It adopts no launch profile and binds no sockets. It does not establish peering,
Frank integration, broad source equivalence, false-literal contract negatives,
BREAK/success-scan behavior or extension repricing. No consensus changes, golden
updates or equal-root/equal-charge requirement belong to this packet.

## Executed checkpoint (2026-10-15)

All six runs passed against daemon source `dca9abe76` with binary SHA256
`c6ab2d7720a9ee603581a6ac80107e18975272fd0c6c69c7032513ba5b463b15`
and manifest SHA256
`33d84853403b2eaa686a5ad4fdd799daffc8fc9c712b0f8662d914a29f11d720`.
The shared API prerequisite is commit `a661f23a`. Full retained bytes and commands
are at `/private/tmp/lotus-v2-optimizer-chain-evidence-20261015`; a
[checked-in execution summary](../tools/lotus-v2-compiler/test/optimizer-chain-pilot/evidence-20261015.json)
records per-artifact commitments and charges. This execution summary is evidence,
not a regenerated expected-output file.

| Family | Optimization | Invocation charge | Block accounting/enforcement |
| --- | --- | ---: | ---: |
| Payment | Disabled | 50445 | 280722 |
| Payment | Enabled | 50181 | 279912 |
| Equality | Disabled | 50617 | 281396 |
| Equality | Enabled | 50515 | 281062 |
| Literals | Disabled | 54871 | 293955 |
| Literals | Enabled | 50181 | 279912 |

Native/reference charge agreement, valid spend admission, immature and bad-signature
rejection, restart, disconnect and reconnect passed in every run. Both equality
artifacts rejected independently signed wrong-integer spends. The optional
integration unittest also passed, including exclusive-output preservation.
These results close this bounded full-block optimizer matrix; broader CABI06
obligations listed above remain open.
