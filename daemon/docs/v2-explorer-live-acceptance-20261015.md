# Private native explorer acceptance harness — 2026-10-15

`daemon/tests/check-v2-explorer-live.py` instruments the existing
`check-v2-wallet-discovery-live.py` unchanged. The driver creates three isolated
native processes, compiler Payment wallets, mature funding, controller
prepare/pay through the private FD relay, pending relay, native `minepool`
confirmation, persisted restart, a conflicting competing chain and re-mining.
No payment wires are manually supplied to a block producer.

The wrapper checks the new `/v2/explorer/v1` service while that lifecycle runs:

- Fetches bounded native `readblock` chunks and saves the exact bodies. The
  independent reference decoder authenticates block IDs, complete transaction
  roots and ordered TxID/TxHash pairs. Header bytes, full frames, core selectors,
  outputs, paths, public witnesses and framed proof/argument tables must match
  the actual decoded bytes.
- Composes paged blocks, height/ID details, transactions, inputs, outputs,
  witnesses, historical outpoints, wire chunks and branch wrappers under one
  token. Native spend references and current native UTXO presence check indexed
  historical spend state. Empty work pages preserve their cursor.
- Checks unsupported pool/detached/finality capabilities, independently native
  pending membership versus confirmed-history 404, publication/restart stale
  tokens/cursors, and same-home confirmation → detach → re-mining membership.
- Starts the actual private frontend proxy on explicit loopback port `0` and
  compares its responses with direct HTTP. Runs the built frontend through
  Happy DOM with real fetch; no mock adapter or fixture server is involved.
  This is DOM execution evidence, **not manual browser evidence**.

The ordinary wallet driver creates native currency transactions. The asset list
must agree with native token occurrences, and real asset detail/event/output
screens run if native tokens occur. `--require-assets` fails if none occur.
A separate native accepted token/mint/burn lifecycle is required to complete the
asset gate; an empty asset list is not evidence for asset accounting.

Run with the wallet driver's normal required arguments plus explicit
`--reference-package`, `--reference-source`, `--frontend-package`,
`--frontend-source`, `--expected-daemon-sha256`, `--expected-wallet-sha256` and
`--expected-manifest-sha256`. The reference environment must provide its normal
Blake3 dependency. The frontend package must already have `dist/` and its pinned
Happy DOM development dependency. Source commits, binary/input/module hashes,
raw native JSONL, every HTTP request/response, exact body bytes, DOM text and
cleanup results are retained in the new output directory.

The harness refuses an existing output path, uses ephemeral loopback listeners,
and owns/cleans every native and proxy process. Failures are retained. It never
resets a home, deploys a site, touches production ports or changes a published
release. Preparation/syntax checks alone establish no runtime result.

## First actual attempt (retained failure)

Harness commit `b4aae19d` ran against immutable native
`86201398e3df61605c2eb2d09c201ce774013e7f`, binary SHA256
`8c6c2d0ed9fc490b8cdb8900f01564ca6902c5d7dbe269eae8d0becefe27ae32`.
Output `/private/tmp/lotus-v2-explorer-live-acceptance-20261015-a` is retained.
The service repeatedly invalidated pinned observations at unchanged genesis;
status generation reached `12316` at height `0`, with one service epoch and the
same native anchor. The harness exhausted its 20,000-request safety budget
before funding. A cleanup force-audit repeated that assertion, while the owned
native/proxy processes were still stopped. This run establishes a failure of
idle snapshot stability, not explorer acceptance.

The wrapper now fails immediately when a pinned request is invalidated at its
unchanged native anchor and skips additional audit work after the primary
failure, preserving cleanup and the original cause. A repaired immutable native
binary is required before another actual run; the existing failure is not reset.

## Review corrections before the repaired-binary run

A same-tip 409 can follow a legitimate header/body/policy context change. The
lifecycle gate now records both raw native observations, durable HTTP stamps,
the old pinned envelope, the error context and elapsed time, and restarts the
whole observation at most three times. Native coin reads and multi-screen DOM
results are accepted only across a stable context; an unchanged-context error
remains a failure. Temporary ready/busy status alone is not a durable stamp
change authorizing a retry.

An independent initial-A probe uses HTTP only, before peers or further native
JSONL commands. Over at least two seconds and twenty coherent rounds it requires
one durable epoch/generation/binding/anchor and exact pinned response. Bounded
transient unavailable attempts remain in the request trace; 409, durable stamp
churn or sustained unavailability fails the probe.

Live DOM execution now includes historical outpoint details and all seven typed
search modes. Unknown asset lookup is explicitly a covered-history absence when
the native asset registry is empty. This wallet gate does not establish asset
accounting even if tokens happen to appear; `--require-assets` fails explicitly
and directs review to the separately owned native asset lifecycle harness.
