# Complete signed development-chain pilot

This explicit offline integration gate compiles the existing Payment source,
mines a coinbase paying its commitment, waits the supplied profile's maturity,
signs a real spend, and validates complete framed blocks through both the Python
reference and `lotusd -lotusv2development`. Each daemon operation is a fresh
process using an isolated new home. It exercises persistent restart, rejection
without state change, disconnect and reconnect. It opens no sockets.

Build the compiler first with `npm ci --ignore-scripts && npm run build` in
`tools/lotus-v2-compiler`. Use the reference Python environment with blake3 and
coincurve. From the repository root:

```sh
PYTHONPATH=tools/lotus-v2-reference \
/private/tmp/lotus-v2-compiler-review-venv/bin/python \
  tools/lotus-v2-compiler/test/development-chain-pilot/run.py \
  --manifest /path/to/explicit-command-manifest.json \
  --daemon /path/to/reviewed/lotusd \
  --daemon-source 'exact reviewed commit and build scope' \
  --output /tmp/new-signed-payment-run
```

The caller supplies every chain, target, issuance and resource parameter through
the existing command manifest. This script does not select or adopt a network
profile. Its test coinbase underclaims to 100000 atoms; the signed transaction
pays a 1000 atom fee. Those are pilot transaction choices, not protocol defaults.
They must be valid under the supplied profile or generation fails. Maturity is
bounded to 1–32 blocks and mining to one million nonce trials per header. Each
Node process has a 30 second deadline; daemon commands have 60 seconds. This
is not a maximum-resource or performance benchmark.

`payment.mjs` compiles `examples/gallery/payment.lotus` using the public fixture
secret scalar 1. It prepares/signs through the existing compiler runtime;
Python independently decodes full bytes and checks both TxId and TxHash.
Python computes all transaction/VM/block charges, advances the monetary state,
constructs roots and mines headers, then calls `connect_complete_block` before
submitting the same complete bytes to the daemon. The current command returns
block ID, height, UTXO/state roots and seven accepted-only decimal charges.
Every returned root and charge must match the independent reference. Native
transaction IDs are not separately exposed; exact transaction bytes and the
accepted block commitment bind those IDs, and the reference records them.

Before maturity, a properly framed and mined candidate containing the signed
spend is rejected specifically for maturity. Its placeholder state root is
intentionally unvalidated because the maturity failure precedes final root
validation. A changed signature at maturity has an independently recomputed
transaction root and valid PoW; both validators reject it. Every rejection is
followed by a new-process status check. The valid spend must remove the funding
coin, survive restart, undo to the exact previous roots, survive another restart,
and reconnect to the identical final state. The reference also restores its
exact coin map and monetary state during undo.

Output creation is exclusive. Existing output directories are never reused;
blocks, manifest, source/compiler artifact, public signatures, both transaction
IDs, roots, charges and subprocess evidence survive failures. A later assertion
failure adds `failure.json`; it does not regenerate expected results. The daemon
binary and supplied manifest SHA256 are recorded, with the caller's source/build
identity. Failed early setup may leave only the manifest/artifact; command
failures retain their stdout/stderr in `evidence.json`.

The integration test is explicit and runs separately from normal compiler tests:

```sh
PYTHONPATH=tools/lotus-v2-reference \
LOTUS_V2_PILOT_MANIFEST=/path/to/explicit-command-manifest.json \
LOTUS_V2_PILOT_DAEMON=/path/to/reviewed/lotusd \
LOTUS_V2_PILOT_DAEMON_SOURCE='reviewed commit/build scope' \
/private/tmp/lotus-v2-compiler-review-venv/bin/python \
  tools/lotus-v2-compiler/test/development-chain-pilot/test_pilot.py
```

Observed 2026-10-15: the supplied provisional command manifest in
`/private/tmp/lotus-v2-command-repro-artifacts-20261015/manifest.json` passed with
`/private/tmp/lotus-v2-full-validation-buildsrc-20261015/build/src/lotusd`.
That binary was the root's source-copy scratch build containing charge-export
commit `dca9abe76` over the command candidate `74ac986ec`; it is not claimed to be
an exact clean checkout build. Evidence is retained in
`/private/tmp/lotus-v2-signed-pilot-charges`. This establishes actual complete
signed block acceptance through the isolated offline daemon command. It does
not establish network-facing ConnectTip/P2P/RPC, wallet operation, launch-profile
approval, crash fault tolerance or general compiler equivalence.

Supported manifest boundary is deliberately narrow: schema 1, no supplied field
size hints, matching ordinary/monetary dust limits, and exclusively zero-valued
pruned genesis outputs with the empty authenticated UTXO root. Unsupported inputs
fail before opening the daemon home. The malformed-signature negative must
report CHECKSIGVERIFY failure in both engines; an unrelated rejection does not
satisfy that gate. Its core TxId must remain identical while its TxHash changes.

Root independently reran the complete pilot against fresh clean native commit
`dca9abe76` at `/private/tmp/lotus-v2-daemon-costs-exact-20261015` after a Debug
Chronik-OFF build and development-chain/disk/peer-codec checks. Evidence:
`/private/tmp/lotus-v2-signed-pilot-exact-20261015`. The accepted signed spend is
at height 3, tip
`360c4b9efd2075255e164a0aac3d7dda6c81842e41a9928c89fc9bc794b6b86d`,
state root `34871de41cbd90fddc1d049830eab41e7c9ae4e0b8367fa52073e430a3330448`.
All seven charges and both roots agree, including after undo/reconnect. The
daemon SHA256 is
`c6ab2d7720a9ee603581a6ac80107e18975272fd0c6c69c7032513ba5b463b15`.
This supersedes the scratch-build limitation for this exact pilot run; the
network, wallet and general-equivalence limitations still apply.

## Reusable compiler pilot API

Importing `run.py` creates no directory and launches no subprocess. Call
`run_pilot(PilotConfig(...), compiler=None)` explicitly; it returns the same
summary stored in `summary.json`. `main(argv=None)` retains the original CLI and
Payment defaults. Configuration includes manifest, daemon, output, daemon_source,
node, optional compiler_helper path, source text, compiler options, method,
non-signature arguments, and signature_argument. The built-in helper accepts
Int/Amount arguments as decimal strings, Bool as booleans and byte arguments as
hex strings. It continues to use only the public fixture secret 1.

The optional compiler callback has signature `compiler(mode, request) -> dict`.
Alternatively `compiler_helper` selects a Node module invoked with mode
`artifact` or `sign`. Both receive the same JSON request fields: source, options,
method, args, signature_argument; sign additionally receives `context` with the
dynamically mined funding outpoint and coin. Helper subprocesses inherit the
caller's environment. Artifact response remains `{source, artifact, owner}`;
sign response remains `{wire, bad_wire, txid, txhash, digest, signature}`.
The harness still independently validates both complete-block engines; the
compiler callback cannot supply roots, charges or acceptance results.

A sign response may additionally supply `negatives` with up to 31 entries
`{name, wire, reference_errors?, native_errors?}`. Each name is a unique lowercase
ASCII/digit/hyphen identifier, maximum 64 characters. These exact full transactions
are framed into freshly mined negative blocks, rejected by both engines, retained
as `<name>.block`, and followed by restart checks. Evidence uses the exact name
as its native label. Extra negatives default to intended `VERIFY` failures.
The original bad signature keeps its identical TxId/different TxHash gate.

`reference_negative_errors` and `native_negative_errors` configure allowed
substrings for the bad-signature diagnostic; defaults remain CHECKSIGVERIFY.
For optimized versus unoptimized contracts callers can explicitly accept
`('CHECKSIG', 'VERIFY')`. Empty sequences explicitly request rejection-only
coverage, which does not establish the intended failure category. Per-negative
error sequences have the same meaning. No expectations are inferred from a
failed execution or refreshed automatically.

CLI equivalents include `--compiler-helper`, `--source` (file), `--options`
(JSON file), `--method`, `--arguments` (JSON file), `--signature-argument`, and
repeatable `--reference-negative-error`/`--native-negative-error` arguments.
Default Payment observations and complete bytes remain unchanged by this API
refactoring. The integration tests now also exercise a different method name,
renamed signature argument, Int argument and optimization disabled, plus import
without filesystem/process side effects, against the exact `dca9abe76` daemon.
