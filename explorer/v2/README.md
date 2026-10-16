# Private Lotus V2 explorer

This browser client implements the private `/v2/explorer/v1` contract in
`docs/plans/lotus-v2-explorer-api.md`. It browses canonical blocks, both native
transaction identities, paged inputs/outputs/witnesses, bounded wire chunks,
assets/events/history/unspent outputs and branch/path predicates. Native amounts
are exact integer strings. Pending membership is unsupported; finality,
accounting, asset metadata and supply remain explicitly unknown.

## Build and connect

Requires Node.js 22 or newer and the pinned TypeScript compiler:

```sh
cd explorer/v2
npm ci
npm test
npm run build
node server.mjs --port 0 --api http://127.0.0.1:18331
```

The command prints its ephemeral **127.0.0.1** browser URL. Open that URL; its
`api` query configures the same-origin loopback proxy. Supply an explicit fixed
local `--port` if required. The server refuses a missing port and refuses a
non-loopback proxy target. Stop with Ctrl-C. It serves only the small static
allowlist and proxies only the new explorer namespace. Nothing is deployed. Incoming proxy request bodies and upstream requests have
absolute 15-second deadlines; status and data responses are read incrementally
under the same 256 KiB byte cap.

Run the separately built native Chronik service with explorer schema 3 and a
fresh isolated index according to its integration instructions. This frontend
does not launch a node, create an index, modify a wallet, or accept secrets. A
schema-2 index or legacy `/v2` service cannot satisfy this contract. The API
origin form also supports a direct loopback service if that service permits the
browser origin through CORS. No fallback to old routes exists.

## Observations and error states

The first data response pins the complete screen. Every following detail,
page, witness and wire request carries its opaque snapshot token. Epoch,
generation, chain/profile, anchor and token must agree before rendering.
Navigating cancels earlier requests. A 409 from initial composition or continuation clears pages and retries the whole
screen once; repeated changes require a manual reload. A 503 retains the prior
observation, marks it stale and disables its continuation buttons. A 404 means
only absence from covered canonical history. Empty work-limited pages keep their
continuation button; no holdings or supply are calculated from a page.

Branch roots are ORed within each set and positions are ANDed on the same
output. Each positional filter is `{"position":"0","roots":["<hex32>"]}`.
All ordered branches and paths are displayed without interpreting hidden
scripts or ownership. Script/witness data is escaped hex, never executed.

## Validation boundaries

Runtime responses have bounded reads and explicit envelope, identity, integer,
coverage and route checks, including full frozen creations, witness table counts,
route identity matching, wire ranges, status anchors/capabilities and cursor limits. Rendering uses DOM text nodes, never HTML insertion.
Tests use clearly synthetic contract fixtures under `tests/`; fixtures are not
served by the dev server and the live adapter has no mock-data fallback.

`npm test` checks identity order, maximum u64/u128 decimal rendering, malformed
responses, snapshot restart/generation mixtures, branch POST/token semantics,
wire bounds, malformed primitive mutations for every route, request cancellation,
malicious field escaping, a real stalled incoming socket deadline, screen navigation
and stale states. Fixture success establishes client behavior only. Actual
native API screen validation remains a separate integration gate and must name
the exact native service revision and observed chain/profile.
