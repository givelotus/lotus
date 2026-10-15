# Private Lotus V2 explorer: research and proposed scope

Status: review proposal, 2026-10-15. No explorer implementation, listener,
public deployment, consensus change, or release operation is included.

## Recommendation and evidence

Build a small V2 frontend against a dedicated, lossless V2 read API. Start with
an output inspector using the four existing confirmed routes; expand to blocks,
transactions and assets only after their authoritative backend queries exist.
Use the Bitcoin ABC explorer as a reference for navigation and presentation.
A full fork would still require replacing its protocol model and data access.
This is an engineering inference from the sources below, not a measured estimate.

The maintained Chronik explorer verified in this research is Bitcoin ABC's
[eCash explorer](https://github.com/Bitcoin-ABC/bitcoin-abc/tree/master/web/explorer).
Its [README](https://raw.githubusercontent.com/Bitcoin-ABC/bitcoin-abc/master/web/explorer/README.md)
configures a Chronik URL and runs a Rust executable. Its
[dependency manifest](https://raw.githubusercontent.com/Bitcoin-ABC/bitcoin-abc/master/web/explorer/explorer-server/Cargo.toml)
uses the ABC Chronik client and core crates alongside Axum and server templates.
The upstream [server source](https://github.com/Bitcoin-ABC/bitcoin-abc/blob/master/web/explorer/explorer-server/src/server.rs)
contains block, transaction, CashAddress, mempool and SLP/ALP token handling.
Those are concrete compatibility boundaries: pointing its config at V2 JSON
cannot make it understand V2 outputs, native assets or identities.

Maintenance is evidenced by explorer-specific commits
[754d37333cd2](https://github.com/Bitcoin-ABC/bitcoin-abc/commit/754d37333cd276669f59a14fbaebf19090efddc7)
(2026-10-12, nonstandard script lengths) and
[b43357b70a71](https://github.com/Bitcoin-ABC/bitcoin-abc/commit/b43357b70a71566e363d7d83b3998a67a203d2a0)
(2026-10-02, incomplete pushdata). The
[upstream path commit feed](https://api.github.com/repos/Bitcoin-ABC/bitcoin-abc/commits?path=web/explorer&per_page=5)
was checked on the research date. The closed
[D19130 review](https://reviews.bitcoinabc.org/D19130)
records linking explorer builds to Chronik/client changes. These observations
establish continuing work, not a V2 compatibility or security endorsement.
The repository [COPYING](https://raw.githubusercontent.com/Bitcoin-ABC/bitcoin-abc/master/COPYING)
is MIT; preserve copyright and permission notices for any copied material and
review notices of selected dependencies/assets before redistribution.

Searches did not establish a second independently maintained Chronik explorer
with inspected source, license and recent maintenance evidence. Do not count
hosted instances of the ABC explorer as independent implementations or claim
other Bitcoin RPC explorers support Chronik. No claim of exhaustive discovery
is made. A later fork decision should pin one exact upstream revision and audit
its selected files rather than treating the moving links above as a source pin.

| Option | Useful reuse | Required work and decision |
| --- | --- | --- |
| Full ABC explorer fork | Existing block/transaction navigation, templates and packaging | Replace legacy protobuf/client assumptions, addresses, token parsing, identities and status semantics; inherit a larger maintenance surface. Defer unless a prototype demonstrates meaningful reuse. |
| Selected ABC presentation reuse | Table and detail-page patterns, with notices for copied code | Still implement V2 types and adapter; review each selected dependency and asset. Reasonable after contract stabilization. |
| Minimal V2 frontend | Direct match to existing bounded V2 JSON | Implement small routing, exact integer formatting, filters and state handling. Recommended first private milestone; no network write features. |

## Inspected local sources and current capability

Monorepo base: `54a2b011`, inspected through isolated integration worktree
`/private/tmp/lotus-v2-integration-owner-20261015`. Native source was read only at
`/private/tmp/lotus-v2-native-integration-20261015`, HEAD
`d8203d7f6c3cc195c7edff53a7223a28ad810b05` when inspected. These are research
provenance, not a claim that a binary or live service matches that HEAD.

The earlier [indexing proposal](lotus-v2-chronik-indexing.md) explains public
branch/path data and filter algebra. Its statement that native HTTP integration
is future work is historical: inspect current native code for implemented scope.
Relevant native paths are `chronik/chronik-http/src/v2.rs`,
`chronik/chronik-lib/src/{v2.rs,v2_server.rs}`,
`chronik/chronik-db/src/v2_branch.rs`,
`chronik/bitcoinsuite-core/src/lotus_v2.rs` and
`src/lotus_v2/chronik_sync.{h,cpp}`. This proposal does not edit them.

The router currently registers exactly these routes:

| Existing route | Actual data available |
| --- | --- |
| `GET /v2/status` | Version, confirmed-only/pool flags, readiness, observation generation, chain/profile/tip/height snapshot |
| `POST /v2/branches/outputs` | Paginated confirmed output creation/spend history matching branch predicates; optional burns |
| `POST /v2/branches/utxos` | Paginated matching confirmed unspent outputs; burns excluded |
| `GET /v2/utxos/:txid/:out_idx` | One confirmed UTXO record, or `utxo_not_found` |

Output records include outpoint, flags, decimal-string value, token ID, complete
ordered branch roots, paths, creation location (block ID, height, transaction
index, TxID and TxHash), and optional spend location/input index. Output history
is not a complete transaction-detail or block-list API. The stored transition
model supplies confirmed locations/outputs/spends; it does not itself provide a
lossless complete header, transaction witness, asset registry or supply history.

Hex is native wire order without reversal; money and heights are decimal
strings. Requests support `any_branch`, positional clauses, cursor, page size
and history-only `include_burn`. OR within each root set, AND across positions
and any-branch selector must match the same output. Current bounds include
32 KiB request body, 256 KiB response encoding, 100 outputs/page, 16 positional
clauses and 256 total roots, with further query work limits. Use returned opaque
cursors; never fabricate them or interpret a partial work page as the full set.

Readiness is fenced against a coherent authority generation and indexed anchor.
Unknown authority, recovery, disagreement, busy database or a changed observation
can produce `503 index_unavailable`; stale cursors produce `409 stale_cursor`.
`GET /v2/status` can return 200 with `ready:false`: transport success alone is
insufficient. `confirmed_only:true` and `pool_indexed:false` explicitly exclude
pending discovery. No current block, transaction, asset, mempool or subscription
route is established by this inspection.

## UI scope and truthful status

The first private inspector displays profile/chain identity, current indexed
anchor/readiness, branch filters, matching creation/spend history, and full
output detail. Display branches as zero-based authorization positions and paths
as ordered alternatives referencing those positions, according to the output
encoding. They are unrelated to blockchain forks. Burns are explicitly marked
unspendable; matching roots never establish ownership. Revealed spending scripts
and membership proofs may be shown only when actually available from validated
transaction data. Hidden scripts, hidden leaf counts and hidden tree positions
remain unknown.

The full explorer milestone has blocks, transaction details, native/asset amounts
and asset history. Search uses explicit object kinds (block ID/height, TxID,
TxHash, token ID, branch root, outpoint), because a 32-byte string is ambiguous.
Do not reuse legacy CashAddress interpretation as a V2 owner identity.

| State | Required display rule |
| --- | --- |
| Confirmed | Current anchored authoritative chain membership; location shown. Confirmations are tip height minus containing height plus one only in a coherent snapshot proving ancestry. |
| Pending | Only accepted transaction-pool membership from a separately implemented pool API. Submission or retained candidate block data cannot establish this. |
| Unknown | Missing data, unsupported pool/asset/history capability, failed lookup outside documented coverage, or unavailable authority. Never substitute zero confirmations, empty balances or a rejection label. |
| Detached | Previously observed membership no longer on the authoritative chain; show an observation history only if explicitly retained. Pending readmission requires fresh pool evidence. |
| Finality | Unknown until a V2 authority supplies documented finality evidence. Confirmation depth and legacy ABC `is_final` are insufficient. |

A UTXO 404 means no unspent record in the indexed snapshot. It does not identify
whether the transaction is unknown, spent, burned, pending or on another chain.
A history record's null spend means no indexed confirmed spend at its snapshot;
it cannot rule out pending conflicts. Cache responses with their anchor and
generation. On stale cursor clear paging state and restart; on 503 retain prior
content only with its stale anchor and unavailable label. Avoid mixing pages or
detail records across incompatible anchors.

Asset detail initially shows token ID and exact integer units from available
outputs. `HAS_TOKEN` determines asset interpretation; zero token ID on native
outputs is not an SLP/ALP token. The consensus C15 mint-root identity can authorize
later mints and does not establish a unique genesis issuance. Names, symbols,
decimals, issuer identity, mint caps and circulating supply are unknown unless a
separate authenticated, documented source supplies them. Never sum a partial
output page into total asset supply or silently assume decimals.

## Required backend contract, without invented routes

The following are proposed query capabilities, not registered URLs. HTTP paths
and schemas must be reviewed with their owners before implementation. Extend the
V2 namespace and preserve the four existing route meanings; no frontend fallback
to legacy eCash protobuf endpoints or unrestricted node RPC.

| Proposed operation | Minimum returned facts and prerequisite |
| --- | --- |
| Capability/status expansion | ChainID, genesis/profile binding, API/schema version, indexed and authoritative anchors, readiness/recovery, coverage start, supported block/tx/asset/pool features. Keep unsupported explicit. |
| Block page/detail | Bounded anchored canonical-height pages; block ID, parent, height, exact header fields and transaction count/order. Requires authoritative header/body source and retained coverage; header-only bodies explicitly unavailable. |
| Transaction lookup/detail | Typed TxID versus TxHash lookup, exact identities, full decoded core/witness availability, inputs with resolved coin provenance, outputs, containing canonical location and status. Requires complete native decoding and identity fixtures, not reconstruction from outputs. |
| Block transactions | Bounded cursor over exact block order, bound to block ID and snapshot. No unbounded block response or implied body availability. |
| Output lookup/history | Extend confirmed output lookup to spent/burn records if needed; existing UTXO route retains its meaning. Include creation/spend context and availability. |
| Asset output/history query | Bounded token-ID postings over complete covered confirmed history, burns/mints/transfers distinguished through validated source facts. Supply statistics require separate conservation accounting and complete coverage. |
| Accepted pending lookup/history | Later gate: accepted-pool generation, TxID/TxHash, dependencies/conflicts and lifecycle events. Explicitly unsupported until admitted-pool authority/index integration exists. |

All new reads need exact integers, documented hash encoding, chain/profile
binding, one snapshot envelope, bounded requests/work/encoding, opaque cursors,
coverage/availability semantics and recovery/reorg fencing. Fees, burn breakdowns
and resource costs are shown only with authoritative resolved inputs and native
accounting; output sums alone cannot establish them. Raw bytes/proofs require
separate native round-trip and commitment checks. Notifications are deferred;
bounded polling with cancellation/backoff suffices for the initial private UI.

## Disjoint implementation work and gates

These are future work packages, not permission to modify code in this research.
Declare shared registration files before parallel work and integrate sequentially.

| Work package | Exclusive initial ownership | Acceptance evidence and dependency |
| --- | --- | --- |
| Contract/fixtures | New `docs/plans/lotus-v2-explorer-api.md` and new fixture directory | Reviewed operation schemas, errors/unknown states, native-wire hex and maximum integers; no consensus edits. First gate. |
| Confirmed block/transaction read model | New native adapter/query modules; declared additions to Chronik V2 bridge/DB | Source-to-API identity/header/body/input parity, bounded reads, checkpoint/reorg/crash reconciliation. Owns no frontend or pool lifecycle. Depends on contract. |
| Asset index/query | New V2 token posting/accounting module and its tests | Reference full-scan equivalence, mint/burn/transfer distinctions, reconnect/undo and coverage rules. Shared DB registration integrated by one owner. Depends on lossless records. |
| HTTP assembly | V2 HTTP registration and response serialization only | Limits, unavailable authority, anchor ABA, stale paging and no partial success under reorg. Consumes query interfaces; does not implement consensus or independently launch nodes. |
| Frontend | New isolated `explorer/v2/` candidate directory, subject to repository layout review | Four-route inspector first; exact values, branch/path display, unknown states, accessible navigation. Fixtures before live service; no wallet keys, broadcast, faucet or mint operations. |
| Private end-to-end review | New dedicated validation script/evidence files | Explicit reviewed binaries/profile, loopback ephemeral ports and disposable datadirs only; blocks, spend/mint/burn, recovery, reorg, unavailable index and frontend parity. Separate approval of any future deployment. |
| Pending extension | Separate future pool adapter/index contract | Parent-child admission/removal, conflicts, expiry, mining, restart and reorg readmission; no inference from candidate-body retention. Independently gated. |

Do not launch a node to validate this proposal. Before live integration, resolve
current daemon build/startup gates and verify the exact tested binary matches the
selected source. No mainnet, production workspace, chain data, release assets,
public hosting or repository push is part of these work packages.
