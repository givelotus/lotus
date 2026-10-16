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

The repaired `8cd36091ba9da0665ceab621ce42306963fcbfd9` binary's first run is
retained at `/private/tmp/lotus-v2-explorer-live-acceptance-20261015-b`.
The HTTP-only twenty-round/two-second idle probe passed. The run then failed
in the harness DOM wait helper: it matched the normal phrase “detached history
unavailable” as a service failure. The helper now recognizes error prefixes.
Idle-probe failures use a dedicated nonretryable exception, and successful DOM
and native parity audits have an additional final context fence before evidence
publication. This retained harness failure establishes no frontend defect or
completed explorer lifecycle acceptance.

Run `/private/tmp/lotus-v2-explorer-live-acceptance-20261015-c` is also retained.
Its idle probe passed; a live DOM navigation then received an intentional brief
503 during the native owner's authority suspend and correctly marked content
stale with a Reload screen action. The DOM driver now verifies that state and
exercises at most three explicit reloads per screen, preserving every transient
notice/status in its evidence. Context fences wait for coherent ready status
before comparing durable stamps, so temporary null anchors do not authorize a
whole-observation restart. Neither change retries a 409 inside the idle probe.

Run `/private/tmp/lotus-v2-explorer-live-acceptance-20261015-d` reached actual
three-node funding/maturity history, thirty checks and 555 HTTP responses. Live
DOM block/transaction/outpoint/typed-search/branch checks and native wire parity
passed those observations. Its final status fence encountered a temporary
`ready:false`; the later coherent context was unchanged, so the harness refused
to classify it as a legitimate publication and stopped. The final fence now
uses the same coherent-ready bounded wait as the other context reads, sharing
the whole-observation deadline. The run and original failure remain retained.

## Repaired-binary availability gate (retained failure)

Run `/private/tmp/lotus-v2-explorer-live-acceptance-20261015-e`, harness
`d5ea1f7b`, used immutable native
`8cd36091ba9da0665ceab621ce42306963fcbfd9` (binary SHA256
`635d7c5a6512b686e7af5add1daa29c8252eb5f77db5dcae4fd49f0dd84b2d0d`)
and reviewed frontend `dc9236e44cf7f4d9fe26d98f07817370bd895f21`.
It reached real funded native payment confirmation at height 5, but did **not**
complete the lifecycle. A typed branch search exhausted its three explicit
stale-screen reloads on 503 while the durable context remained unchanged. The
harness truthfully failed its configured availability bound and did not restart
the whole observation to hide that failure.

Before failure, 78 explorer checks included 24 native-parity snapshots, seven
actual DOM runs, six native-pending versus confirmed-history misses, eighteen
stale-token rejections and fifteen stale-cursor rejections. Four token checks
proved same-tip service-restart invalidation. The independent HTTP-only idle
probe passed. There were 1,836 wrapper HTTP observations: 1,748 success, 49
transient unavailable, 33 expected stale and six expected covered-history misses.
DOM fetches and explicit reload notices are recorded separately in each DOM
result; the failing DOM stderr retains its exhausted reload notices.

All seven owned native processes exited zero; all seven private proxies were
terminated. The raw explorer evidence SHA256 is
`c5aac2efbffba9165ebe86eb8bbe5574b19121df78eba1a52ac01f4ce48d0be9`.
Independent review found no remaining concrete harness false-failure in this
attempt. Reorg/re-mining and a complete usable DOM lifecycle remain pending;
asset accounting remains the separately owned native asset gate.
