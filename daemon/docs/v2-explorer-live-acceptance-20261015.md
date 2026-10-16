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
