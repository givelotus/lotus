# Private V2 explorer API and implementation contract

Status: implementation proposal for independent review, 2026-10-15. This is a
complete minimal explorer milestone: blocks, full transactions, assets,
confirmation status, branch/path inspection and explicit unavailable states.
Finishing only the existing output inspector does not satisfy this milestone.
Pool discovery, finality, public hosting and deployment are outside this contract.
Their absence is visible in the API and UI, rather than inferred from misses.

## Evidence and architecture decision

Monorepo design base: `f6aa2d37600a1e9fc7310b1e14a1da5c203f2fe3`.
Research input: `docs/plans/lotus-v2-explorer.md` in the separate research
worktree. Native files were inspected read-only in
`/private/tmp/lotus-v2-native-integration-20261015`; its observed HEAD during this
review was `691ee3b5c80cbf5730720868ccb305d8a097925b`. That worktree is under
active integration; implementation must record the exact source it builds.
No running binary or service was inspected, and this document establishes no
runtime validation claim.

The existing source already provides the needed authority boundary:

1. `src/lotus_v2/chronik_sync.cpp::ChronikSync::Step` checks the stable runtime
   snapshot, locates the next active header through bounded `ReadHeaders`, then
   obtains its retained bytes through `ReadConnectedBody`.
2. `MakeChronikBlock` calls native `DecodeBlockWire`, `BlockId`,
   `CompleteTransactionRoot` and `ComputeIdentities`. It currently discards the
   full header and transaction input/witness bytes after extracting outputs and
   spend references. Extend this conversion; do not reconstruct transactions
   from the output records.
3. `chronik/chronik-lib/src/v2{,_ffi}.rs` supplies the committed transition to
   the single `V2Db` owner. `chronik/chronik-db/src/v2_branch.rs` commits records,
   postings, receipt, undo and checkpoint in one synced batch.
4. `chronik/chronik-lib/src/v2_server.rs::Authority` and
   `chronik/chronik-http/src/v2.rs` fence reads against the independently supplied
   native anchor. Reuse these owners and this listener. HTTP does not call back
   into the runtime, scan candidate bodies, or open a second authoritative DB.

Extend that one transition and batch with explorer facts. Keep all legacy
C++ mainnet types, RPCs, Chronik protobuf routes and chainstate APIs unchanged.
The existing four V2 routes retain their meanings. New explorer JSON has a
separate schema prefix `/v2/explorer/v1`; here `v2` is the protocol namespace and
`v1` is this explorer contract version. There is no legacy endpoint fallback.

## Representation and common response envelope

Every hash is 64 lowercase hex characters in native digest/wire order. Do not
reverse BlockID, TxID, TxHash, token ID or branch roots. These are distinct typed
identities; a search form requires the object kind. All integers in **new**
routes, including indexes, flags, lengths and counts, are canonical unsigned
decimal strings. This avoids exceptions around JSON's safe integer range.
Booleans remain booleans. Existing routes retain their current index encoding;
the client normalizes those bounded indexes separately.

Successful data responses have this envelope (angle brackets denote types):

```text
{
  "api_version": "1",
  "snapshot_token": <opaque-string>,
  "snapshot": {
    "chain_id": <hex32>, "genesis": <hex32>, "profile_id": <hex32>,
    "tip": <hex32>, "height": <u64-string>,
    "service_epoch": <opaque-string>, "generation": <u64-string>
  },
  "coverage": {
    "from_height": "0", "through_height": <u64-string>,
    "complete": true, "scope": "canonical_confirmed"
  },
  "data": <route-specific object>
}
```

`service_epoch` is generated once per service open from 128 bits of OS entropy;
failure to obtain it refuses explorer startup. Existing process-local authority
generations reset on restart, so generation alone cannot invalidate old cursors.
Epoch is neither a secret nor a chain identity. A restarted service can have the
same chain/index anchor while still invalidating all previous cursors.

The initial implementation indexes a contiguous history from authenticated
genesis. It does not support a partial bootstrap, pruned explorer records or
claim coverage from the current tip alone. Before complete catchup, status can
report progress, but data routes return unavailable. A later partial-history
contract must use another schema revision with explicit gaps.

List payloads use `{items: [...], next_cursor: <opaque|null>, exhausted: <bool>}`.
`exhausted:true` means the requested range/filter is exhausted in this snapshot,
not that the network has no other history. A work-limited page may be empty and
still return a cursor. Every continuation must advance; an oversized indivisible
item returns an error instead of a nonadvancing cursor.

## Exact routes

All paths below are relative to `/v2/explorer/v1`. They are `GET` except the two
explicit `POST` branch routes. Every data route accepts the common optional
query parameter `snapshot_token`; the table lists only additional parameters,
so `none` means no additional parameters. `/status` accepts no parameters and
does not issue a snapshot token. Every successful data envelope issues its exact
snapshot's token; the first ready list or detail request is the token source for
subsequent requests composing that screen. Reject unknown
query parameters, duplicate parameters, noncanonical decimal/hex encodings and
overlong values before reading storage. `page_size` defaults to `25`, maximum
`100`; `cursor` is optional. A cursor includes the entire normalized query and
snapshot binding. Parameters supplied with it must agree.

| Route | Query | `data` and ordering |
| --- | --- | --- |
| `/status` | none | Status described below, including both independent anchors and capabilities. Available while catching up. |
| `/blocks` | `before_height`, `page_size`, `cursor` | Block summaries by descending canonical height; first page starts at tip unless an exclusive `before_height` is supplied. |
| `/blocks/by-height/:height` | none | One block detail, resolving the height in this snapshot. |
| `/blocks/:block_id` | none | One canonical block detail. |
| `/blocks/:block_id/transactions` | `page_size`, `cursor` | Transaction summaries in ascending native transaction index. |
| `/transactions/by-id/:txid` | none | Transaction detail, without unbounded input/output/witness arrays. |
| `/transactions/by-hash/:txhash` | none | Same detail, resolved by exact full identity; both identities always returned. |
| `/transactions/by-id/:txid/inputs` | `page_size`, `cursor` | Input descriptors in native input order, including coinbase and mint inputs. |
| `/transactions/by-id/:txid/outputs` | `page_size`, `cursor` | Complete output records in native output order, including burns and confirmed spends. |
| `/transactions/by-id/:txid/witnesses` | `input_index`, `page_size`, `cursor` | Witness descriptors in native witness order for this input. |
| `/transactions/by-id/:txid/wire` | `offset`, `length` | Exact full transaction bytes, excluding the enclosing block CompactSize length prefix; bounded chunk described below. |
| `/outputs/:txid/:out_idx` | none | One historical output record, whether unspent, spent or burned. Does not change `/v2/utxos` semantics. |
| `/assets` | `page_size`, `cursor` | Known native asset IDs in lexicographic native-byte order, each with detail summary. Includes token outputs that are all burned/spent. Native coin is not an asset ID entry. |
| `/assets/:token_id` | none | Asset detail and truthful metadata availability. |
| `/assets/:token_id/events` | `page_size`, `cursor` | One aggregate event per touched transaction, ordered by `(height, tx_index)` ascending. |
| `/assets/:token_id/outputs` | `view=history\|unspent`, `page_size`, `cursor` | Output records ordered by `(creation_height, tx_index, out_idx)`. History includes burns; unspent excludes them. |
| `POST /branches/outputs` | JSON body: `any_branch`, `positions`, `page_size`, `cursor`, `include_burn` | Existing branch history predicate/order, with the new envelope and restart-safe cursor wrapper. |
| `POST /branches/utxos` | JSON body: `any_branch`, `positions`, `page_size`, `cursor` | Existing branch UTXO predicate/order, with the new envelope and restart-safe cursor wrapper. |

The branch bodies preserve the existing field names and filter algebra, using
decimal strings for `page_size` and positional `position` under this new schema.
Branch `page_size` defaults to `25`, matching the new schema; omitted filter
fields use the existing engine defaults. These two handlers call
the existing branch query engine and convert its bounded record model; they do
not implement a second branch index or predicate evaluator. The new cursor
wrapper contains the existing engine continuation plus the common new cursor
bindings. An old-route cursor is not valid in a new-route request.
Branch list items are `{record:OutputRecord,matching_positions:[<u8-string>...]}`;
their `data` additionally includes `posting_reads` and `work` as decimal strings.
Use the existing engine's continuation to distinguish exhaustion from an empty
work-limited page, then wrap it with the new snapshot bindings.

Register static `by-height`, `by-id` and `by-hash` paths without ambiguity with
dynamic IDs. A block's first transaction page is sufficient for navigation;
block detail never embeds its complete transaction list.

Status is `{api_version, ready, reason, indexed_anchor, authoritative_anchor,
service_epoch, generation, binding, coverage, capabilities, limits}` without
requiring a data envelope when no snapshot exists. Anchors are nullable
`{block_id,height}`. `reason` is one of `ready`, `initializing`, `catching_up`,
`authority_unknown`, `recovery`, `busy`, `schema_incomplete`, `index_error`;
use `authority_unknown` when the existing publisher cannot distinguish recovery.
Do not invent a more precise cause. Capability booleans are `blocks`,
`transactions`, `transaction_wire`, `outputs`, `assets`, `asset_events`,
`branches`, `accepted_pool`, `detached_history`, `finality`. The last three are
false for this milestone. Unsupported features remain false even if candidate
or legacy services happen to have superficially similar data.

## Block and transaction objects

`BlockSummary` is `{block_id, prev_id, height, time, size, tx_count,
status:"confirmed", confirmations}`. `BlockDetail` adds
`{header_wire, header:{prev_id,bits,time,nonce,version,size,height,tx_root,
state_root}, body_availability:"complete", finality:"unknown"}`.
`header_wire` is exactly 268 hex characters, encoding the native **134-byte**
header. Native field offsets are 0/32/36/42/50/54/62/70/102 with widths
32/4/6/8/4/8/8/32/32. Header `size` is the full framed block wire length.
Native `BlockId(chain, header)` authenticates its ID; a double SHA256 of raw
header bytes is not a substitute. Genesis keeps its actual zero predecessor;
the sink's self-parented genesis checkpoint is an internal convention only.

`TxSummary` is `{txid, txhash, location:{block_id,height,tx_index},
status:"confirmed", confirmations, input_count, output_count, wire_size}`.
`TxDetail` adds `{lock, core_available:true, witness_available:true,
wire_available:true, finality:"unknown", accounting:{availability:"unknown"}}`.
Do not infer native fees, miner reward split or VM execution cost from output
sums. This milestone can leave that accounting explicitly unknown. Exact native
identity computation is `ComputeIdentities`, with both results exported; never
assign one digest to both fields or import V1 identity rules.

`InputDescriptor` is `{input_index, flags, kind, prev_txid, prev_index, sequence,
path_index, witness_count, coinbase_data, resolved_coin}`. Preserve the raw
selector fields even when their meaning changes by kind:

| Kind | Presentation and contextual fields |
| --- | --- |
| `spend` (`flags=1`) | `path_index` is the selected path. `resolved_coin` has `availability:"complete"` and the exact prior output/creation location, obtained before applying this spend. This is a frozen creation fact, without a mutable historical record's current `spend` member. A broken reference within complete coverage is an index error, not an unknown zero-valued coin. |
| `coinbase` (`flags=2`) | `path_index:null`, `resolved_coin:{availability:"not_applicable"}`; show actual parent/height selector bytes with their native interpretation. |
| `mint` (`flags=3`) | `path_index:null`, `resolved_coin:{availability:"not_applicable"}`; label `prev_txid` as the token/mint-root identity, never as a spent transaction. Link to the asset page. |

`coinbase_data` is `{present:<bool>, wire_ref:<ByteRef|null>}`. It preserves the
absent/present distinction and exact bytes. `WitnessDescriptor` is
`{witness_index, script:ByteRef, siblings:{count,table_ref,inline},
arguments:{count,table_ref,inline}}`. A `table_ref` addresses the canonical
encoded section (including its native count/length framing) in the full wire;
it is always present alongside `count`. `siblings.inline` is an optional complete
array of hex32 values, and `arguments.inline` is an optional complete array of
ByteRefs. Set either to null when its complete descriptor list exceeds the
bounded record budget; clients can retrieve the section through `/wire`.
The descriptor itself is paged under the normal encoding cap. No silently
truncated arrays, including with unusually large profile argument/proof bounds.

`ByteRef` is `{offset,length}` into the transaction's exact full wire, both
decimal strings. `/wire` defaults to offset `0`, length `32768`, maximum length
`32768`; returns `{txid,txhash,total_bytes,offset,bytes_hex,next_offset}`.
`next_offset:null` means end of frame. Offset past end is `416 invalid_range`;
offset equal to end returns an empty final chunk. Negative/overflowing offsets,
zero length or an excessive length are `400 invalid_limits`. Chunk requests
accept an optional `snapshot_token` obtained from transaction detail; a mismatched
token returns `409 stale_snapshot`. Require that token after the first chunk.
This prevents assembling bytes across changed canonical membership. Native
frames are retained in fixed chunks so serving one chunk never reads the entire
transaction or block. The frontend can show exact bytes and public witnesses
without needing to interpret arbitrary scripts as text or execute them.

`OutputRecord` has `{txid,out_idx,flags,value,has_token,token_id,is_burn,branches,
paths,creation,spend}` using existing record semantics and new integer encoding.
`token_id` retains the actual raw field even on native outputs; `has_token`
governs its interpretation. Branches are ordered roots, and each path is an
ordered list of zero-based branch positions. Show all of them. An indexed root
is public authorization structure, not proof of ownership. Hidden scripts,
hidden leaves and unknown proof positions remain unknown. The existing branch
queries keep OR-within-root-sets and AND-across-positions on the same output;
they are a required explorer screen alongside block/tx/asset screens.

## Native bridge and persisted model

Extend `ChronikBlock`/`NativeBlock` with fixed `header_wire[134]`. Extend
`ChronikTransaction`/`NativeTx` with the exact full frame, lock, all input core
descriptors, and validated byte offsets/lengths for witness/coinbase sections.
Keep the existing spend subset and output wires for compatibility and branch
indexing. Add bounded metadata types in new `v2_explorer` modules; do not copy
the native consensus engine into Rust or JavaScript.

Reserve these exact bridge additions before implementation. CXX names below are
in the existing `chronik_v2` namespace; the C++ producer uses equivalent types
prefixed `Chronik`. `NativeTx.inputs` remains the existing spend subset and
`NativeTx.outputs` remains the existing output-wire vector:

```text
WireRange { offset: u64, length: u64 }
NativeWitness {
  script: WireRange,
  siblings_table: WireRange, siblings_count: u32,
  arguments_table: WireRange, arguments_count: u32
}
NativeFullInput {
  prev_txid: [u8;32], prev_index: u32, sequence: u32, flags: u8,
  path_index: u8, has_coinbase_data: bool, coinbase_data: WireRange,
  witnesses: Vec<NativeWitness>
}
NativeTx += { wire: Vec<u8>, lock: u64, full_inputs: Vec<NativeFullInput> }
NativeBlock += { header_wire: [u8;134] }
```

Every range is relative to the full transaction frame. Script and coinbase ranges
address payload bytes only. Each table range begins at its native count field
and includes the complete count and element framing, matching the exact source
frame; table count must equal the exported count. Empty payload ranges preserve
their actual offset; absent coinbase data uses `{offset:0,length:0}` and
`has_coinbase_data:false`. Preserve raw `path_index` in transport and map it to
JSON null for non-spends. The native profile must bound witness counts before
constructing CXX vectors. Optional HTTP inline tables may be null in the minimum
implementation; the exact referenced bytes remain available. These DTOs carry
native-decoded facts, not claims that a Rust parser revalidated consensus.

In `chronik-db/src/v2_explorer.rs`, reserve Rust public persisted/model names
`WireRange`, `WitnessFact`, `InputFact` with fields corresponding exactly to the
three bridge types above (`InputFact` also has
`resolved_creation: Option<ResolvedCreation>`).
`ResolvedCreation {outpoint: OutPoint, output: Output, creation: TxLocation}`
contains no spend state. `ExplorerTxFacts {wire: Vec<u8>, lock:u64,
inputs:Vec<InputFact>}` and `ExplorerBlockFacts {header_wire:[u8;134]}` are the
required transition additions:
`ConfirmedTx.explorer: ExplorerTxFacts` and
`CommittedBlock.explorer: ExplorerBlockFacts`. They are mandatory in schema 3,
never an optional incomplete-success path. Persist transaction fixed metadata
as `TxMeta {location:TxLocation, lock:u64, input_count:u32, output_count:u32,
wire_size:u64}` and block metadata as
`BlockMeta {anchor:Anchor, header_wire:[u8;134], tx_count:u32}`. Large wire and
descriptor vectors are split into the records below rather than serialized into
`TxMeta`. Name the persisted input descriptor `InputMeta`: it has every
`InputFact` field except `witnesses`, replaced by `witness_count:u32`.
Modules may use bounded internal serde representations where existing
public types lack serde support, without changing these logical field shapes.

The DB owner alone resolves `resolved_creation` before staging each spend;
the bridge supplies no caller-authoritative coin values. Its conversion sets
this field to None, then DB staging requires/resolves it for spend inputs and
leaves it None for coinbase/mint. Reject caller-supplied conflicting values.
The native service `initialize_genesis(NativeBlock)` already receives the block,
but currently passes only its transactions to DB initialization. Change
`V2Db::initialize_genesis` to accept the complete `CommittedBlock` and retain
header/full facts. Require genesis anchor/self-parent convention there, while
persisting the exact header's zero predecessor. Update all genesis fixtures;
an empty synthetic header is not a compatible explorer fixture.

Capture frame ranges from native decoding of the authenticated connected body.
Prefer a V2-only optional frame-location output in the existing block/transaction
codec over a second parser. If an implementation initially re-encodes a decoded
transaction with `EncodeTransaction`, it must compare every byte to its exact
source frame before export. Headers must match the first 134 source bytes.
Offsets must be checked against frame bounds before allocation or persistence.
`MakeChronikBlock` remains the source of IDs, complete ordered transactions and
mint selectors. It must not accept partial record population as a successful
explorer block. No second runtime read is needed for each HTTP request.

Within the same DB batch, reserve these exact ASCII prefix families. Existing
single-byte `b/t/o/u/p` keys and singletons `v2-binding`, `tip`, `disconnected`
remain owned by `v2_branch.rs`. Every explorer family starts with `e`, which
does not overlap them; concatenated fields below have fixed widths:

| Family | Key and value |
| --- | --- |
| Canonical height | `eH + height_be64 → block_id` |
| Block | `eB + block_id → BlockMeta` |
| Block transaction | `eO + block_id + tx_index_be32 → txid, txhash` |
| Transaction | `eT + txid → TxMeta`, joined with existing `t + txid` location; equality required, no competing location authority |
| Full identity | `eX + txhash → txid` (reject conflicting reuse) |
| Input | `eI + txid + input_index_be32 → InputMeta` |
| Witness | `eW + txid + input_index_be32 + witness_index_be32 → WitnessFact` |
| Transaction wire | `eR + txid + chunk_index_be32 → at most 32 KiB` |
| Asset registry | `eA + token_id → AssetSummary` |
| Asset event | `eE + token_id + height_be64 + tx_index_be32 → AssetEvent` |
| Asset output | `eP + token_id + height_be64 + tx_index_be32 + out_idx_be32 → outpoint` |

Expose these snapshot methods from the model/query modules through the shared
`ReadSnapshot`: `explorer_block(id)`, `explorer_block_at_height(height)`,
`explorer_tx(txid)`, `explorer_tx_by_hash(txhash)`, `explorer_input(txid,index)`,
`explorer_witness(txid,input_index,witness_index)`,
`explorer_wire_chunk(txid,chunk_index)`, `asset_summary(token_id)`, plus bounded
exclusive-key iterators for the page families. Return `Result<Option<T>>` for
point reads and `Result<Option<(key,T)>>` for next-key reads. Query modules own
page budgeting/cursors; DB methods own key-prefix and stored-record validation.
These helpers use the existing snapshot handle rather than opening storage.

Existing historical output records provide spend resolution even after the coin
has been consumed. Resolve against the current batch's staged state first, so
an in-block parent/child works. Never call current runtime `ReadCoin` to resolve
historical inputs: already-spent coins are absent from that UTXO view.

Receipt equality for idempotent replay must bind every new explorer fact,
including wire bytes, all inputs and header. Undo must cover every new key and
old aggregate value. Extend `validate_undo` to validate exactly the expected key
set and ownership; merely adding writes will currently make disconnect fail.
Handle exact-tip replay before resolving new spends against current spend state:
authenticate incoming complete native facts against the stored receipt and its
frozen resolved creations, then return the idempotent result. Coins spent by
that already-committed block must not cause an otherwise identical replay to
fail as a double spend. A changed frame, selector, descriptor or header fails
the receipt comparison before any mutation.
Recompute the expected canonical-height, block-order, full-identity, frame-chunk
and descriptor entries from receipt facts, and compare their current values
before undo. Validate asset events/postings against the receipt's resolved
inputs/outputs/mints and validate aggregate old/new counter arithmetic and
`first_seen` preservation. A correct prefix/key length alone cannot authorize
restoring an arbitrary value or deleting another block's key. Include the exact
derived explorer/asset facts in the versioned receipt equality contract.
No mutable explorer cursor/snapshot state is stored in that batch.

Set `SCHEMA_VERSION = 3` for these required records. Existing schema-2
directories fail with a clear schema mismatch; no implicit migration, reset or
deletion. Prepare a separately named explorer index directory and replay native
retained history when runtime work is authorized. On a missing historical body,
stop and report incomplete coverage; never manufacture a complete transaction.
Native node commits and index commits remain separate, reconciled by existing
`ChronikSync::Step`. On restart authority begins unknown; only successful
reconciliation and complete explorer coverage permit publication.

## Asset semantics and independent implementation hook

Take the union of token IDs in `HAS_TOKEN` outputs, resolved `HAS_TOKEN` spend
coins, and all mint-input selectors. Emit one event for each union member, even
when it occurs only in inputs and is fully burned implicitly. An event records
`{token_id,location,spent_units,output_units,explicit_burn_units,
minted_units,implicit_burn_units,has_mint_input}`. All amounts are exact unsigned
decimal strings. Compute checked u128 totals over the authenticated transaction
and resolved spend coins: `I = spent_units`, `O = output_units` including burn
outputs, `B = explicit_burn_units`; `minted_units=max(O-I,0)` and
`implicit_burn_units=max(I-O,0)`. Require a bijection between positive token
deltas and mint inputs: exactly one matching mint input for each positive delta,
no mint input without a positive delta, and no duplicate mint selectors.
Disagreement is a transition error, matching native ordinary-validation shape
checks. An event can contain mint,
transfer and burn effects simultaneously; do not force it into one category.
Explicit burns are additional to implicit burns. Live UTXO unit change is
`O - B - I`; burns never become spendable asset outputs.

This is indexing of an accepted native transition, not a new consensus mint
validator. Zero-valued token outputs and burn-only occurrences still create a
registry entry. C15 mint-root identity permits later mint events; first observed
occurrence is not a unique genesis or issuer identity.

Asset detail is `{token_id,first_seen,event_count,output_count,
metadata:{availability:"unknown",name:null,symbol:null,decimals:null,
issuer:null,mint_cap:null},supply:{availability:"unknown"}}`. Counters are exact
checked u64 values over covered history and undone atomically. Supply is
deliberately unknown in this minimum contract: no circulating-supply claim is
required for asset browsing/history. An optional future accumulator must prove
genesis, complete coverage, overflow behavior and both burn modes independently.
Frontend presents integer units, never an assumed decimal precision or sums of
one page as total holdings/supply. Native currency is displayed separately.

Asset work consumes an immutable per-transaction view:
`AssetTxView<'a> {location:TxLocation, outputs:&'a [Output],
resolved_spends:&'a [ResolvedCreation], mint_token_ids:&'a [Hash32]}`. The mint
slice retains one entry per mint input, so duplicates cannot disappear before
validation. In `v2_asset.rs` reserve
`AssetEvent {token_id:Hash32, location:TxLocation, spent_units:u128,
output_units:u128, explicit_burn_units:u128, minted_units:u128,
implicit_burn_units:u128, has_mint_input:bool}` and
`AssetSummary {token_id:Hash32, first_seen:TxLocation, event_count:u64,
output_count:u64}`. A pure
`derive_asset_events(view: AssetTxView<'_>) -> Result<Vec<AssetEvent>>` lives in the new asset
module; it performs no writes and has no runtime/HTTP dependency. The DB owner
invokes it while staging each transaction and incorporates its posting/counter
mutations and undo in the existing batch. Queries consume the same ReadSnapshot.
Return events sorted by native token bytes. `event_count` counts touched
transactions; `output_count` counts every created token output, including burns
and zero values, never a transaction's native outputs. `first_seen` is the first
covered canonical transaction occurrence and is removed if undo removes the
last event. This is the parallel implementation seam; a second DB writer is
forbidden. Only the integration owner exposes any crate-private snapshot/staging
access needed by the sibling modules; neither asset nor explorer helpers open a
second RocksDB handle or bypass the parent's batch.

## Fences, absence, reorg and limits

For every data route: observe authority/epoch; reject an unknown anchor; try-lock
the one DB owner; obtain a snapshot; verify binding, checkpoint, coverage and
authority stamp; do bounded reads and bounded encoding; observe again before
returning success **or not-found**. Changed stamps produce `503
index_unavailable`, including anchor ABA. A request validated against an old
cursor returns `409 stale_cursor` only after the service has a coherent ready
view. Never send part of a response before the final fence. Client requests
already in flight can receive a coherent older observation; their snapshot is
the truth they display, not a claim that the tip cannot advance afterward.

New cursors carry version, epoch, generation, full binding, anchor, route kind,
normalized filter digest and exclusive last key. Decode to bounded fixed fields;
validate membership/key shape before iteration. Clients treat them as opaque.
They need not be signatures: hostile cursor contents cannot bypass key prefixes,
binding checks or work limits. Any new publication invalidates previous cursors,
even when the anchor returns to the same block. Snapshot tokens contain only
token version, epoch, generation, chain/genesis/profile binding and anchor;
they exclude route kind, filter and last key so one token composes different
routes at one observation. All point/detail/list routes accept optional
`snapshot_token`; successful responses expose the matching token so the UI can
pin a multi-request page. On mismatch return `409 stale_snapshot`.

These restart/ABA cursor guarantees apply to the new explorer schema, including
its two branch wrappers. The four existing `/v2` routes retain their previous
snapshot-only cursor contract; those cursors do not carry service epoch or
authority generation. Their per-response authority fence remains useful but
does not make an old branch cursor restart-safe. The explorer UI uses only the
new branch wrappers when composing pinned views. Do not mix an existing-route
branch response into a new-schema snapshot or claim that a before/after status
poll closes that race. This preserves old clients without silently weakening
the new UI's consistency contract.

Confirmed means canonical indexed membership in this ready snapshot.
Confirmations are checked `tip.height - location.height + 1`, calculated only
after canonical membership is established; overflow is an unavailable result.
`pending` is never returned in this milestone because accepted-pool capability
is false. A miss does not mean rejected, pending, zero balance or zero
confirmations. Detached objects disappear from this index after undo; the client
may label its prior cached observation “no longer confirmed at the current
snapshot,” but cannot claim retained server-side detached history. Finality is
always unknown. Candidate body retention never proves pending membership.

New-route errors are bounded JSON `{api_version:"1",error:{code,meaning},
snapshot:<snapshot|null>,coverage:<coverage|null>}`. Use `400 invalid_request`,
`400 invalid_limits`, `400 invalid_cursor`, `409 stale_cursor`, `409
stale_snapshot`, `413 request_limit`, `413 record_limit`, `416 invalid_range`,
and `503 index_unavailable`. `404 not_in_covered_chain` includes the fenced
snapshot and means absent from covered canonical history only. For unknown
token IDs it makes no assertion about off-chain/pending assets. Internal DB
corruption and contradictory authenticated data are 503, never empty lists.
Status returns 200 with `ready:false` when it can report a coherent observation;
storage contention or incoherent authority may return 503. All responses use
`Cache-Control: no-store`; the UI may retain explicitly labeled old snapshots.

Bounds: 32 KiB request/query budget, 256 KiB JSON response budget, 100 items per
page, cursor/token at most 2 KiB, 32 KiB raw wire per chunk, at most 1024 examined
records and 4096 key reads per new page. Count work before performing it; retain
existing tighter branch-query bounds. Encode incrementally to a capped buffer;
do not first allocate arbitrary JSON then check its length. Count every new
record, wire chunk, secondary key, receipt/undo byte and staging allocation in
the existing 32 MiB maximum batch reservation. A native accepted block that
exceeds index capacity makes indexing unavailable; it never invalidates the
native block. Status reports this operational failure truthfully.

The native retained-body helper currently reads a whole historical delta before
its output cap is enforced (`disk_body.h` documents this). This plan does not
claim that helper has a hard preallocation bound. Sync remains one bounded
configured body per step, while HTTP serves bounded indexed records. Acceptance
must report that storage limitation; any stronger memory guarantee requires a
separate measured storage change.

## Disjoint work packages and integration order

The integration owner owns shared registrations and batches. Implementers use
separate worktrees and declare file ownership before coding. Paths in the first
four rows are relative to the native tree; frontend paths are monorepo paths.

| Owner | Exclusive files / scope | Integration seam |
| --- | --- | --- |
| Native block/transaction producer | `src/lotus_v2/chronik_sync.{h,cpp}`, new `chronik_explorer.{h,cpp}`, dedicated tests; necessary V2-only codec location additions in `block_wire`/`transaction` agreed first | Emits complete header/frame/core/witness location facts in one authenticated transition. Does not edit Rust DB/HTTP or frontend. |
| Block/transaction model and query | New `chronik-db/src/v2_explorer.rs`, `chronik-indexer/src/query/v2_explorer.rs`, corresponding tests | Bounded records/key planning/read methods consumed by DB owner. No independent service or DB. |
| Asset model and query | New `chronik-db/src/v2_asset.rs`, `chronik-indexer/src/query/v2_assets.rs`, corresponding tests | Pure event derivation and bounded query helpers; no edits to shared `v2_branch.rs`, bridges, router or frontend. |
| Native integration / HTTP owner | Existing `chronik-lib/src/v2{,_ffi,_server}.rs`, `chronik-db/src/v2_branch.rs`, existing `chronik-http/src/v2.rs`, new `chronik-http/src/v2_explorer.rs`, module/build registrations | Owns schema bump, one atomic batch/undo, service epoch, new route registration, budgets and all cross-module interfaces. Integrates producer/model commits sequentially. |
| Frontend | New monorepo `explorer/v2/` only, including client types, fixtures, navigation and tests | Typed new-schema API adapter, including branch wrappers; consumes reviewed contract fixtures. No native or shared docs edits. |
| Review/evidence | Dedicated validation/evidence files assigned after implementation | Independent contract/identity/reorg/bounds review, then isolated runtime evidence when authorized. No patch/export or deployment action implied. |

The frontend includes overview/status, canonical block list and detail,
transaction details/input/output/witness views, asset list/detail/events/outputs,
and branch query/path inspector. Search has explicit block height, BlockID,
TxID, TxHash, token ID, branch root and outpoint modes. Every screen displays the
chain/profile and observation anchor; it clears paging and retries on 409 and
labels retained content stale on 503. Use native big integers or decimal-string
formatting; validate all runtime API data. Render script/data as escaped hex,
preserve keyboard navigation and avoid arbitrary HTML. Fixtures may unblock UI
development, but the milestone is incomplete until the actual native API serves
all required screens.

## Review and acceptance gates

1. Independent review resolves this contract and shared Rust/CXX shapes before
   parallel implementation. Agree actual key prefixes and staging byte accounting
   with the one DB owner; record any contract changes here.
2. Native fixtures prove exact 134-byte headers, byte-for-byte transaction frame
   round trips, distinct TxID/TxHash and native ordered transaction root parity.
   Include coinbase data absent/present, mint/spend ordinals, all branch/path
   positions, scripts/proofs/arguments, maximum integers and chunk boundaries.
3. DB tests compare indexed blocks/transactions/assets to a full native fixture
   scan. Include in-block parent/child spends, multiple mints of the same asset,
   mixed mint/explicit burn, implicit burn, zero-valued asset output and a token
   with no unspent outputs. Reconnect restores identical query content.
4. Crash/restart/reorg tests cover node ahead/index behind, divergent suffix,
   duplicate exact replay, conflicting frame replay, missing body, missing/corrupt
   undo, failed new-key batch, schema-2 refusal and fresh schema replay. Each new
   key family disappears/restores correctly on undo. Restart rejects old tokens
   at an unchanged tip; ABA is fenced during encoding and before a 404.
5. HTTP tests use in-process router calls for every route, malformed parameters,
   bounded scans, empty continuation pages, work exhaustion, oversized records,
   chunk reconstruction, snapshot-pinned detail composition, busy DB and shutdown.
   Hold the DB lock and confirm every handler rejects promptly instead of blocking.
6. Frontend checks use real contract fixtures to cover complete navigation,
   exact integer rendering, branch/path semantics, pending/finality unavailable,
   stale content and reorg pagination reset. Then exercise the same screens
   against an isolated actual service and compare displayed identities/amounts.

The final integration record names exact native/monorepo commits, commands and
coverage. Unit/fixture success does not establish node startup or deployment.
This design work launches no node, changes no main checkout, resets no directory,
pushes no branch and publishes nothing. Implementation and private validation
remain separate from any future deployment decision.
