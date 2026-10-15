# Private V2 controller Payment discovery

The foreground controller integrates the existing confirmed Chronik discovery client with native encrypted-wallet tracking. This is private development tooling. No production listener, chain data, release or published asset is changed.

A node may opt in by adding exactly this object to its existing configuration entry:

```json
"chronik": {
  "url": "http://127.0.0.1:18332",
  "chain_id": "<native lowercase 32-byte chain ID>",
  "profile_id": "<native lowercase 32-byte validation profile digest>"
}
```

These hashes are trusted operator inputs. Startup compares them with that node's native ready event; each discovery also compares native wallet info and node readiness. The Chronik host must publish its `profile_id` as the same validation binding exposed by native `profile_digest`. Configuration does not derive either identity from HTTP. The URL must be an explicit numeric loopback HTTP origin with an explicit port; credentials, DNS, path prefixes, queries and redirects are refused. For nodes on separate machines, run the controller alongside its node or explicitly arrange an SSH forward from a local loopback port to the node-specific Chronik service. Direct remote HTTP/HTTPS endpoints are not supported by this first transport; that is a controller transport scope, not a protocol or network restriction. The controller does not launch or configure an SSH tunnel or Chronik HTTP listener. Nodes without this optional object retain the existing native workflow.

For configured nodes, `wallet reconcile NAME`, `wallet balance NAME`, and `wallet discover NAME` obtain registered native `payment_output.branches`, query all roots together, track each candidate through native `track`, then call native `reconcile`. `discover` requires configuration explicitly. `prepare`, `sign`, native `pay`, and the controller's combined `pay` command run discovery before preparing or signing. Discovery failure is surfaced before a passphrase prompt or signing. Command execution is serialized; the same absolute deadline covers lock acquisition, native info, every HTTP page/retry and native tracking/reconciliation. No discovery results or cursor survive between commands, so a new controller operation starts a fresh snapshot scan.

The transport bounds public requests at 32 KiB, responses at 256 KiB and JSON structural nesting at 32 levels before parsing (quoted delimiters do not count); excess nesting and parser recursion failures return `protocol_error`. It disables redirect handling by accepting only HTTP 200 (409/503 trigger the existing bounded snapshot restart), and uses the command's remaining time for connect/send and every socket read. Checking the deadline on buffered HTTP socket reads also bounds a peer that trickles bytes. Numeric loopback eliminates DNS lookup delays. The existing client retains finite page/retry limits and refuses malformed, foreign, changing or incomplete snapshots.

Only candidate `prev_txid` and numeric `prev_index` enter native `track`. HTTP values, tokens, proofs, branch paths, ownership and spendability never enter wallet state. Native TrackFunding authenticates ownership and the current anchor; a failure stops the operation. Earlier successful tracks may already persist and can be safely retried. Reconcile remains the authority for current coin presence, reservations and maturity. A stale confirmed candidate rejected by native validation is surfaced rather than silently counted.

The returned native reconciliation object retains all its fields and adds `confirmed_discovery` containing the HTTP tip, decimal height/generation, candidate count, `confirmed_only=true` and `pool_indexed=false`. Its snapshot can differ from native reconciliation's newer tip. Native `pending` and transaction `status` commands bypass HTTP, preserving the persisted outgoing transaction and PoolCoordinator lifecycle. The confirmed index cannot discover pending incoming payments and cannot prove that a dishonest server omitted no output.

## Verification and remaining gate

Run:

```sh
python3 -m unittest discover -s tools/lotus-v2-devnet/tests
```

The dedicated controller discovery tests use synthetic native adapters and HTTP on an ephemeral loopback port. They check all-root requests, native-only values and pending state, recreated-controller idempotence with synthetic durable tracking, stale snapshot restarts, malformed/foreign output rejection, unowned native rejection, binding/registration checks, prepare ordering, command-lock deadlines, expired discovery before native mutation an actual trickling HTTP response and an actual HTTP 200 response containing 200,001 bytes of deeply nested JSON rejected before native tracking. Existing client and process/FD controller tests are also included. These checks establish the integration boundary, not live ownership or node acceptance.

Before claiming a working private-testnet wallet flow, the owner must run actual node-specific Chronik listeners with the trusted binding, confirm external Payment funding, discover and authenticate it through the real native client, prepare/pay/spend, confirm, reorg and restart with native durable wallet state. Pending receipt indexing remains unavailable. Production ports and existing homes must remain untouched throughout that gate.
