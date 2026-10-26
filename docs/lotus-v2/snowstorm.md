# Snowstorm reconciliation core

Status: **independently reviewed specification; public contract and acceptance artifacts are being authored. The new core has not yet been implemented or validated.**

The marked specification below takes precedence over historical Snowstorm descriptions in this documentation tree. Optional coordination does not replace ordinary transaction or block validation. Old performance and finality claims are preserved as historical material, not evidence for this core.

<!-- snowstorm-core-normative:begin -->
# Reconciliation core: normative specification

This section specifies a new reconciliation core. Historical miniblock designs and measurements elsewhere do not establish its implementation, performance or safety. This section controls the core where historical descriptions conflict.

## §1 ARCHITECTURE

The core is a sans-IO deterministic state machine. No sockets, threads, wall clock, globals, or hidden randomness. Time and an RNG seed are passed in; all output is returned as Actions. The host serializes all calls (single owner); the core never calls host services. RootFn is the explicit exception: a pure deterministic calculation supplied by Config, with no IO, mutation, hidden randomness or access to peer ground truth.

```
class SnowstormNode {
  explicit SnowstormNode(Config cfg); // beta_max, epsilon, max_set_size, RootFn, rng_seed
  Actions on_tx_admitted(TxHandle, Time);
  Actions on_tx_removed(ShortId, RemovalReason, Time);
  Actions on_tx_body_removed(ShortId, TxHash, RemovalReason, Time);
  Actions on_tx_bodies_result(PeerId, ShortId, BodyResult, Time);
  Actions on_message(PeerId, ByteSpan, Time);
  Actions on_timer(Time);
  Actions on_peer_connected(PeerId, PeerCaps, Time);
  Actions on_peer_disconnected(PeerId, Time);
  Actions on_new_tip(TipParams, Time);
  Actions on_block_disconnected(TipParams, Time);
  Stats stats() const;
};
Action = Send{peer,bytes} | FetchBody{peer,short_id,fetch_id}
       | Frozen{root,txids} | PeerMisbehaved{peer,reason} | ScheduleTimer{at};
```

RemovalReason is expiry, trim, conflict, reorg, batch_loser, variant, replaced or other. TxHandle is an immutable opaque shared handle exposing 32-byte txid, 32-byte tx_hash and short_id. The core computes current short_id from tx_hash and TipParams; a cached handle short_id is not authoritative after rekey. TipParams contains a 32-byte tip context, SipHash k0/k1 and surviving handles. PeerId is a nonzero host-assigned connection identity never reused within a node lifetime; a reconnect has a fresh PeerId. PeerCaps contains protocol_version and positive host-measured RTT. Only version 1 compatible peers enter D and protocol handling; incompatible peers generate no protocol traffic and are not penalized for incompatibility.

Time is signed int64 monotonic microseconds, with 0 <= Time <= INT64_MAX. Calls must be nondecreasing in Time. Backwards times and local arithmetic overflow return no Actions, set Stats.last_api_error, and leave protocol state unchanged. Config requires finite 0<=beta_max<1/3, finite 0<epsilon<1, 1<=max_set_size<=floor((2^21−256)/8) and a nonempty RootFn. Invalid Config throws std::invalid_argument before allocating protocol state. Remote input never throws out of an API call or reaches an assertion. The host must keep admitted distinct-ID count and total admitted body count each <=max_set_size. An over-capacity admission is an explicit local API error, not a false successful admission. Other public operations return typed errors rather than wrapping integers or silently changing operands.

Host contract: every FetchBody token receives exactly one result, even after cancel/reset/disconnect (host owns timeouts). BodyResult contains fetch_id, optional expected_tx_hash, one of admitted, not_found, invalid or local_rejected, and binding status matched or unbound. The host first parses body bytes and verifies their tx_hash maps to the requested short ID with the request's tip key. Unparseable/wrong-ID bytes are unbound peer-local failures; they cannot justify global invalid-ID rejection. Only a matching-ID body that fails actual transaction validation is invalid/matched. admitted requires matched binding, the exact32-byte expected_tx_hash whose current short ID equals the requested ID, and successful actual admission. local_rejected requires matched binding and expected_tx_hash: a valid bound body was not admitted solely because of local policy/resource/temporary-context constraints, and no global invalidity is established. The host must not map policy refusal to admitted, not_found or invalid. On a live token, validate the status and binding enum domains before interpreting status-specific fields. not_found ignores binding/hash fields only after both enum values are valid. invalid/matched requires the matched32-byte hash; invalid/unbound ignores any supplied hash and is donor failure. admitted/unbound, local_rejected/unbound, missing/wrong-binding required hashes or illegal enum values on a live token are local HostContractError with no state mutation or peer penalty. Stale/unknown/completed tokens are ignored before interpreting their payload. The host sends an admitted result before the matching on_tx_admitted; that callback must eventually follow unless a tip transition cancels its generation. It never admits merely because an ID decoded. Tokens increase monotonically across tip/connection generations and never reuse; exhaustion is a nonfatal local error. Existing admitted matching IDs make late failures obsolete, not grounds for removing an admitted body. The core never inserts transactions into the host.

RootFn receives all candidate bodies in canonical (txid bytes,tx_hash bytes) lexicographic order; the identity of the tip is an explicit additional RootFn input. It returns 32 bytes and must be collision-resistant for honest equality inference. Frozen contains sorted unique txids represented by those candidate bodies. Root equality is a peer assertion, not authentication of a Byzantine peer's bodies. Out of scope: SnapBlock/Stage1.5, conflict resolution/BatchId, stake weighting and consensus changes.

## §2 FIELD GF(2^64)

P(x)=x^64+x^4+x^3+x+1 (reduction constant 0x1B). Multiply: hardware carry-less multiply (PMULL/PCLMULQDQ) selected by runtime CPU detection using function target attributes; portable fallback using 4-bit windowed tables. Squaring: byte tables. Inverse: Itoh–Tsujii. Batch inverse: Montgomery's trick. inv(0) returns a typed ZeroInverse error. Batch inverse rejects a batch containing zero atomically with the same error; an empty batch succeeds with empty output. solve(D) for u^2+u=D returns false iff Tr(D)=1; otherwise use the even-degree method with theta=x^61 (Tr(theta)=1), byte-wise tables, and verify y^2+y==D before returning. solve(0) returns true,y=0. Half-trace is incorrect in even-degree fields and forbidden. Runtime backend selection and portable/hardware agreement are observable without exposing mutable dispatch state.

## §3 SHORT IDS AND BODIES

short_id is the 64-bit SipHash-2-4(k0,k1,tx_hash) result; zero maps to one. The tx_hash argument is exactly its canonical 32-byte sequence, not TxId||TxHash. Different witness tx_hash values generally have different IDs but can collide. R is keyed by distinct short_id; each ID owns its admitted body bucket. A second distinct body under an ID changes the body/root view but not the ID sketch, ID admission sequence or ID change log. Duplicate admission of the same tx_hash is a no-op.

on_tx_body_removed(id,hash) removes precisely that body, changes the root/body view immediately, and removes the ID/logs a minus only when its last body leaves. Unknown body removal is a no-op. on_tx_removed(id) is the explicit whole-bucket operation; every body under that ID leaves. Host normal removal callbacks use the body-specific method. Every RemovalReason has these same core set semantics.

Sketch reconciliation establishes distinct-ID equality in tested trials, not complete collision-body agreement. A colliding body can be hidden by the ID sketch, and globally rejecting an authenticated invalid matching-ID body can conservatively suppress a valid colliding body for the height. These are explicit limitations; ordinary host validation and block fallback remain mandatory. No claim of collision-complete transaction dissemination is made.

## §4 CODING

### §4.1 Cells and decode

Cell={int32 count;u64 s1,s3,s5}, serialized in 28 bytes little-endian. count never wraps and −2^31 is forbidden: exceeding ±(2^31−1) returns local Overflow or remote PeerMisbehaved(count_overflow). Adding nonzero x with sign sigma in {−1,+1}: count+=sigma;s1^=x;s3^=x^3;s5^=x^5. A residual is received cell minus requester reference encoding at the same index.

decode(residual,idx,in_reference) returns Zero, One{x,sigma}, Two{x1,sigma1,x2,sigma2}, or Undecodable:

- Zero iff count=0 and all syndromes zero.
- One requires |count|=1,s1!=0,s3=s1^3,s5=s1^5,schedule_includes(s1,idx), and count=+1 iff s1 absent from reference (−1 iff present).
- Two requires count in {−2,0,+2},s1!=0. D=1 xor s3*s1^−3; solve(D) succeeds; x1=s1*u;x2=x1 xor s1. Require distinct nonzero roots, s5=x1^5 xor x2^5 and schedule inclusion for both. Each sigma is −1 if root in reference, +1 otherwise; require sigma1+sigma2=count. Return roots in increasing unsigned order.
- Otherwise Undecodable. Checks do not authenticate a chosen malicious set; finite syndromes are not an injective commitment for arbitrary large sets.

### §4.2 Integer Rateless IBLT schedule

Credit: Yang et al., SIGCOMM2024. Item x has i0=0. SplitMix64 state starts x. Each step adds 0x9e3779b97f4a7c15 modulo2^64; z=(z xor(z>>30))*0xbf58476d1ce4e5b9; z=(z xor(z>>27))*0x94d049bb133111eb; output=z xor(z>>31), all operations u64 modulo arithmetic. Draw u as low32 bits of exactly one output; s=2^32−u.

Given included i, next j is the least integer j>i with `s*(j+1)*(j+2) >= 2^32*(i+1)*(i+2)`. Compute with u128 integer square root of the quadratic discriminant and exact integer adjustment. No floating point. Stop/exhaust if j>max_symbol_index; never wrap. The corresponding continuous inverse-CDF has survival (i+1)(i+2)/((j+1)(j+2)), hence marginal inclusion2/(j+2). uint32 quantization is the exact implemented law. T3 retains target1/(1+i/2), million samples and4σ tolerance. This discrete law explicitly corrects the former inverse-square formula's .6400000001303852 index1 probability, which was inconsistent with2/3.

### §4.3 Sketch

encode(set,[a,b)) returns cells. Incremental cache updates every admitted ID add/remove at every cached scheduled index. Use 64-byte-aligned SoA cell storage and precomputed (x,x^3,x^5) per ID. Body-only bucket changes do not modify sketches. Range bounds and overflow are checked before mutation.

### §4.4 Peeler

Use a worklist; each pass snapshots its dirty set; changes requeue cells; attempt singletons before pairs, batch-invert s1^3 for pair candidates and recheck staleness before solving. Run until empty, without an iteration cap. Each successful item removal changes reference membership and subtracts that item from every stored scheduled residual exactly once. A Two event is atomic and removes two distinct items. The node does not subtract them again.

Keep a per-pass claim ledger of item/sign. A repeated item claim in the same fixed snapshot/reference pass is inconsistent_symbols and terminates that session, not an endlessly toggling +x/−x cycle. A host/reference change not caused by that pass closes the current pass, applies its residual delta and starts a new pass with an empty ledger. The raw received cells remain immutable. Claimed items beyond the validated maximum possible signed difference are a structural inconsistency; storage exhaustion is separately ResourceLimit, never an iteration cap. No hostile input triggers debug assertions. Recoverably validate hostile inconsistency and capacity before any internal debug invariant assertion. Each successful decode audit records its entire original source cell, index, both original membership bits and grouped One/Two outputs before any residual update. Independently rechecking a Two uses that original pair cell, not two fictitious singleton checks.

Peeler append validates the entire input batch before mutation. A prohibited INT32_MIN count or reconstruction overflow returns Error::overflow; an out-of-range index returns Error::invalid_range; conflicting duplicate indices, within the batch or against stored raw cells, return Error::inconsistent_symbols; insufficient capacity returns Error::capacity. Each such error leaves all peeler state unchanged. Identical duplicate raw cells are no-ops.

## §5 SET STORE

R is the tracked host-admitted, not-removed body set of this height, keyed by ID; conflicts are not resolved by this core. The explicit conservative exception is an ID already rejected for this height: a later host admission under that ID returns RejectedId diagnostic with no core insertion, including a valid colliding body. This exception must be reported, not called an exact host-pool mirror; normal validation is never bypassed. Every ID appearance/disappearance appends (strictly increasing seq,item,sign) to a log and records its admission seq. Body-bucket changes additionally advance seq, with an explicit body-only log event (zero ID-sketch delta), because snapshot body/candidate roots must retain their original identities. snapshot(S) is the exact ID/body state as of S. Cached snapshot symbols revert all later ID changes for requested indices; body-only changes do not affect symbols. Retain log back to oldest pin. If max_change_log would be exceeded, expire oldest pins (ties session identity), release their retained metadata/body handles, truncate the unneeded prefix; their continuations return snapshot_expired without retaining a tombstone per request.

Session-open atomically pins raw R(S), candidate bodies C(S), exclusions E(S)=R_ID(S) minus C_ID(S), its RootFn result and a monotonic exclusion version. These metadata and cells are immutable for that session. Exclusions arise solely from Lambda<=−Btx in this core. Conflict losers removed by the host leave R through a removal call; no undocumented host exclusion setter or BatchId rule exists. Surviving handles and new tip key/context are supplied on_new_tip/on_block_disconnected. Both reset R, recompute IDs, clear logs/pins/sessions/Pending/probation/rejected/local_rejected/unavailable/fetches/awaiting-admission/voting/peer models, preserve compatible connections and monotonic token generators, and restart waves from the new context. Old asynchronous results cannot mutate the new generation.

## §6 SESSIONS

### §6.1 Canonical wire grammar and ownership

Each payload starts u8 version=1,u8 kind (0=req,1=symbols,2=close), then32-byte tip_context. Peer capability must advertise version1. Every following integer is u64LE unless stated; all vector counts are canonical CompactSize. Boolean bytes must be0 or1. No trailing bytes are allowed.

REQ: session_id,request_id,poll_id,open:u8,reference_size,known_excl_present:u8,[known_excl_version if present],range_count,then range_count pairs(begin,end).

SYMBOLS: session_id,request_id,poll_id,status:u8 (0=normal,1=expired,2=resource_limited). Expired ends there. Resource_limited has one reason:u8 (0=declared_reference_capacity,1=symbol_budget,2=session_capacity,3=storage_capacity) and then ends. Normal continues S,current_seq,range_count,ranges,cell_count,cells (each28B),root_vote[32],excl_version,has_exclusions:u8,[exclusion_count,IDs if present]. current_seq is responder sequence at response construction; it never changes the pinned cell/root/exclusion meaning. It is diagnostic, not replacement snapshot evidence.

CLOSE: session_id. Session/request/poll IDs are nonzero except poll_id0 means nonvoting continuation. All increase without reuse per requester lifetime; exhaustion is a local error. Tip context and connection generation route inbound messages; old context/session IDs and unknown/completed logical request IDs are ignored. Old-poll data for a still-outstanding request follows the rules below and never supplies fresh root votes. REQ ranges are sorted, nonempty, nonoverlapping; total cells checked without overflow. Exclusion IDs are strictly increasing nonzero u64. All counts, message bytes and static limits are checked before allocation. SYMBOLS ranges must exactly match the outstanding request and cell_count must equal their total length. Conflicting duplicates, changed S, incorrect flags/encoding or unexpected ranges emit PeerMisbehaved and close that peer's active session. Unknown/stale well-formed responses are ignored, not penalized solely for reordering.

Only one requester session and one outstanding request exist per peer/direction. First open pins S/C/E/root. Repeated open for the same active session never repins; a newer session replaces the old one. Requests for identical ranges in that session always encode identical cells. Unknown/older or expired session continuations return expired without creating a new pin. Keep only the latest session identity/high-water state per connection, not unbounded tombstones.

A logical data request has one request_id, immutable ranges and original_sent_time. It retains that identity until its matching normal/terminal response is accepted or the session closes. A new wave polling an unfinished session resends this SAME logical request with a fresh poll_id; ordinary timeout retransmission repeats the latest poll_id as well. Nonvoting continuations create a new request_id with poll_id0. Store only current logical request, original send timestamp, latest send timestamp and latest poll ID; no historical request map. Responder echoes both IDs. A well-formed response matching active session/request/ranges may advance reconciliation even if its poll_id is old. It supplies a root vote ONLY if its echoed poll_id equals the current wave's selected poll. Once the logical request completes, later duplicates are ignored, not peeled again. A late response cannot become fresh by being relabelled; timing adaptation in§6.5 makes subsequent genuinely fresh votes possible. CLOSE only closes its matching session.

A correlated expired or resource_limited response closes and invalidates that requester model, cancels its outstanding request/timer, releases evidence and never decodes or supplies a root/item vote. If its echoed poll_id is current, it counts as answered nonmatch for that wave; an old-poll terminal response can close its still-active logical request but gives no new-wave answer/evidence. Next time this peer is selected, open a fresh session; never reopen recursively in the same API call. An unsolicited/old-session/completed-request terminal response is ignored and cannot close a new session.

A syntactically valid declared-capacity mismatch returns resource_limited(reason0) without PeerMisbehaved; a valid request exceeding a responder session/storage allowance returns the corresponding resource status. Malformed/overflowing encodings still emit PeerMisbehaved and close according to static parse rules; no undeclared status or empty normal response is sent. Honest local log/model expiry is nonpunitive and its later continuation gets expired. Terminal statuses have no root field and cannot be interpreted as normal vote metadata.

Unknown exclusion version is the explicit known_excl_present=0 flag, not an overloaded integer sentinel; every new session uses it and obtains the full list. A continuation may use the immutable pinned version; omission is allowed only for a requester that explicitly declared that version known. A normal response claiming omission when unknown is malformed.

### §6.2 Reference transitions, completion and lifetime

Reference_j=(own R_ID union plus_j) minus minus_j. State includes session/request/poll identity,S,latest current_seq,raw/residual cells,plus/minus,immutable exclusions/root,own_seq_at_done,evidence wave and declared sizing operands. Every stored residual equals its raw cell minus encoding of current reference. Independently observable diagnostics permit oracle recomputation after every call.

Own ID add x: if in neither plus nor minus, reference gains x and residuals subtract x; otherwise reference unchanged. Own ID removal: if in neither plus nor minus, add to plus so reference retains x; otherwise no reference change. Body-only changes do not alter reference.

Decoded +x: if rejected, terminate this session without inserting/fetching. If x is unadmitted and local_rejected, close this session nonpunitively without inserting or fetching. If x is unadmitted and in probation (§6.3), register donor and possibly FetchBody, then close/invalidate this session before applying the positive membership transition. Otherwise erase x from minus, insert plus, atomically apply the peeler's single removal; register donor/fetch if unadmitted and available. Decoded −x: add minus, erase plus, atomically apply its peeler removal. Emit at most one active fetch per ID globally.

First request is[0,1). At symbol0 receipt, before any peeling, capture reference_size_at_symbol0 and raw0.count minus its reference0.count. Infer snapshot_size=reference_size_at_symbol0+residual0.count; require0<=snapshot_size<=M. Subsequent request size n=max(stuck+1,abs(c0)) uses the current post-peel stored residual0 count and number of nonzero stored cells. Ask sequential next not-yet-requested indices, dividing n into messages of at most max_cells; send one piece at a time and recompute the next n only after processing its response. No artificial margin or fixed packet target. A response that completes decoding sends CLOSE rather than continuation.

Done means all stored residuals zero after the whole valid response; record own_seq_at_done, close, discard residuals/worklists/claims, compact plus:=plus minus ownR,minus:=minus intersect ownR, retaining identical reference. Before discarding, discover available donors for all unadmitted IDs established present in that reconstructed raw snapshot, including excluded IDs. This does not require a fresh +decode and fixes Pending masking of an honest donor.

RootMatched (§8) is a distinct close status, never Done and never a claim that raw residuals are zero or raw sets equal. It closes after the first matching-root response without running the peeler.

A Done model completed in wave w remains until after scoring wave w+1, then all its allocated membership/exclusion/cell capacity is released. Only peers sampled in the wave being scored may contribute; unsampled retained models are never extra votes. On repoll, use a fresh session if prior is closed; the new session replaces the old model, so old evidence is not combined with it. A current session/model that becomes Done in this wave or the previous wave can provide one per-peer/item observation when sampled; duplicate responses never duplicate observations. RootMatched evidence lasts only its poll wave. At each wave score release expired models before opening the next wave. Idle peers outside these windows retain only fixed connection metadata; no membership model survives into a new session.

### §6.3 Body failure, probation, alternate donors

On invalid/matched for outstanding unadmitted x: remove x from every plus/Pending/probation/donor/confidence record, apply necessary residual deltas, invalidate/close every model affected by x, mark rejected for this height, and emit PeerMisbehaved(invalid_body). Rejected IDs are never fetched or accepted by this core this height; this conservative rule has the collision limitation in§3.

On not_found, or invalid/unbound: mark unavailable only for that donor connection generation and ID, emit body_not_found or wrong_body_binding, remove the unadmitted x from EVERY plus/reference/Pending record (including directly corroborated but unvalidated other-peer claims), close/invalidate affected models, and put x in global body probation. This explicitly replaces the earlier rule retaining assumptions at other peers, to preserve the literal no-fake-in-any-reference T10 postcondition. Keep only bounded alternate donor identities, not trusted membership. Later claims for probation x may trigger a fetch from an untried donor, but cannot reinsert x into any reference or evidence until actual host admission. Multiple malicious donors and repeated claims cannot restore fake membership after failure.

On admitted/matched, clear any probation mark without inserting into R, and retain the same bounded per-ID fetch record in explicit awaiting_admission state with token, expected_tx_hash and generation. It supports Pending and retains Lambda even when all sessions are closed; it suppresses any new fetch until a matching current-generation on_tx_admitted consumes it. A timer between result and callback does not clear it or fabricate R membership. Duplicate results are ignored. An independent successful admission during an in-flight fetch also consumes its record/support and makes its later result obsolete; a tip transition cancels in-flight and awaiting records. A mismatching-body admission does not consume an awaiting record for another body, although it may create the same collision bucket. A matching callback after a cancelled tip is a normal current-generation host admission only if revalidated/rekeyed by the host; it cannot resurrect cancelled confidence/token state. The host owns eventual callback completion/cancellation, not a hidden core timeout. Disconnecting the donor connection cancels its in-flight fetch token before any later result is interpreted and immediately retries an already known usable alternate donor, if present. A result for that cancelled token is stale and ignored before payload validation. Disconnect does not cancel an awaiting_admission record: the host already admitted that body, so its matching callback remains required and consumes the record unless a tip transition cancels the generation.

On local_rejected, remove unadmitted x from all plus/Pending/supporting models as a nonpunitive local outcome, cancel its fetch, and mark x in bounded local_rejected storage. No PeerMisbehaved or fake counter increment occurs. Suppress future unadmitted claims/refetch for this ID until tip reset or independent successful host admission; such admission clears the local mark and uses normal own-add semantics. Do not mark global invalidity or bypass host policy. Liveness of fetching a transaction the host refuses to admit is not promised.

Available donor discovery occurs on valid positive decode or successful raw-snapshot Done, irrespective of exclusions. Keep at most max_donors per ID, ordered by first discovery then PeerId. Remove unavailable/disconnected/stale-generation donor entries immediately, retaining their separate unavailable marks. The cap counts only currently usable candidates: failed earlier sources cannot occupy all slots and block a later honest donor. If all usable slots are occupied, prefer the existing ordered candidates; any subsequent failure frees a slot for a newly discovered donor. After failure retry an already known alternate immediately. A later newly discovered honest donor can supply x even if no +decode occurred in its earlier Done. One in-flight OR awaiting-admission record per ID; host timeout of an actual fetch gives not_found, while an admitted callback remains the host's obligation. Admission removes probation/Pending, retains accumulated Lambda if present, and applies normal own-add semantics. All-unavailable sources leave no Pending assumption; probation persists to tip reset. No timer-based arbitrary expiry rejects an honest delayed fetch; host returns its explicit timeout outcome.

### §6.4 Limits, sizing and accounting

Let M=max_set_size, D<=1024. All values below are exact derived limits except explicitly operational peer/range/message constants. All products are checked u64/u128 arithmetic. Limits are public read-only values but definitions reside in src/limits.h. These bound owned requested allocation bytes, including C++ object padding/container capacities, not just live elements. Allocator-internal metadata and host-owned TxHandle payload memory are excluded and separately observable through process RSS; the core's shared-handle/index storage is included.

| Collection | Maximum retained records |
|---|---:|
| admitted distinct IDs; admitted bodies | M each |
| per-peer ranges/request |64 operational |
| cells/message |min(65536,6*M+32), additionally total payload<=2MiB operational |
| exclusion IDs/session |M |
| change-log entries |8*M+64 |
| max_symbol_index |min(2^39−1,64*M+4096) |
| global Pending; combined in-flight/awaiting-admission records |2*M+32 each |
| global probation; rejected; local_rejected; unavailable(peer-generation,ID) pairs |8*M+128 each |
| candidate donors/ID |min(D,8),8 operational |
| total donor records |8*(10*M+160) |
| plus entries/session; minus entries/session |4*M+64 each |
| snapshot body-handle pins/session; candidate body handles/session |M each |
| unique received symbol slots/session |3*(snapshot_size+reference_bound)+32 |
| claim entries/peeling pass |snapshot_size+reference_bound |
| worklist/staleness records/session |one per symbol slot |
| per-call diagnostic decode groups |sum of each processed session's claim limit; a Two consumes2claim units |
| per-call other diagnostic records |16*(D+1)+4*max_cells+4*(2*M+32) |
| queued outbound payloads inside core |none across calls; returned Actions <=16*(D+1)+4*max_cells+4*(2*M+32) records, each Send<=2MiB |

reference_bound is fixed at open as M+max_plus (=5*M+64). Since own R_ID<=M and plus<=4*M+64, this bounds the live reference including retained own removals and imported assumptions. REQ.reference_size encodes this fixed declared bound, not a live cardinality. Responder accepts any declared bound in[0,5*M_responder+64] and never claims to verify the requester's hidden cardinality; underreporting merely lowers the requester's served-symbol allowance. Above its local bound it returns ResourceLimit/abstention without allocation. Responder budget=3*(pinned snapshot_size+declared_bound)+32; requester budget uses inferred snapshot_size and its actual declared bound. This is an explicit immutable-capacity replacement for the old ambiguous moving-reference cap, not a request-sizing margin. Unique indices, not retransmissions, consume budget. Symbol0 must be the sole first range[0,1); no later symbols are accepted before size inference succeeds. A new initial request carries unknown exclusion version, and the Config M ceiling guarantees its full exclusion list plus256bytes of framing/first cell fits2MiB. Subsequent requests size their cell fragments against actual serialized header/exclusion bytes as well as max_cells. Different capacity peers can resource-limit rather than silently adopt another M.

Before any own admission/removal or pooling change would overflow a peer model's plus/minus/reference cap, expire that peer's session/model and release its evidence first, then apply the authoritative own-set change. Never reject an otherwise in-capacity host admission merely because a stale peer model is full. This does not penalize the peer for honest local churn; Stats counts local_model_expiry. Remote-attributable overflow remains PeerMisbehaved(resource_limit). Before any sequence mutation, validate global admitted-body/ID capacity and integer range, so a local error cannot partially mutate R.

The Pending storage cap includes a reserved per-ID slot for every in-flight/awaiting-admission record, even when probation excludes that ID from mathematical Pending. Thus the union of Pending and active-fetch/awaiting IDs is <=2*M+32; admitted-result transition consumes its existing reservation and cannot fail or evict confidence merely to allocate new Pending support. Refuse a new fetch/assertion before exceeding that union cap, using the named resource-limit behavior below.

Every actual core-owned allocation belongs exactly once to fixed node bytes, fixed peer bytes, one collection record capacity above, immutable snapshot storage or returned action/last-call diagnostic storage. Fixed peer floor is <=1024bytes and fixed node floor<=4096bytes. Each record class has sizeof/alignment/owned capacity<=128bytes excluding explicitly counted variable payloads; variable bytes (raw message/action/exclusion arrays) are counted separately, not double charged as records. SoA symbol storage counts exact raw/residual/count/index/dirty arrays and padding; it may not claim28B when actual Cell is32B. Actual requested bytes must be <= floor +128*sum(record capacities)+sum(explicit variable byte capacities). Per-peer model bytes include its responder and requester pins/models, not just plus/minus; global probation/local_rejected/unavailable/donor/Pending/awaiting-admission bytes remain in node total. Total node bound includes D*floor, active/fresh session allocations, bounded global tables and current Actions/diagnostics; it is not independent of D. The mandatory100-peer test checks fixed D*floor plus this complete dynamic bound. Completed idle peer-owned dynamic capacity is exactly zero. The 128-byte record ceiling applies to actual core-retained records, including retained diagnostic records, and all returned Actions remain fully counted. A caller-owned value copy materialized by stats() is an observational output, not retained protocol state; its objects may be larger than 128bytes and its allocation is separately attributed from core state. This does not permit the core to retain oversized public-view records internally: it must use compact records or structure-of-arrays storage with explicitly counted variable payloads and materialize the public views only for the caller. Excluding caller-owned observational copies never excludes the retained source diagnostics or returned Actions.

On remote-attributable overflow close offending session, release its model/pins, clear its wave evidence, count named limit and emit PeerMisbehaved(resource_limit). Local admitted-state capacity errors return last_api_error with no partial mutation. Before a Pending/donor insertion would exceed its global limit, refuse the new assertion, close its source session and leave admitted R unchanged. When probation/rejected/local_rejected/unavailable storage exhausts, set a fixed node-wide suspended_unadmitted flag for the rest of this height, close/clear all unadmitted speculative models/fetch assumptions, and accept no further unadmitted sketch claims/fetches until tip reset; ordinary valid host admissions remain allowed. This preserves failure marks without eviction/refetch cycles, exposes degraded operation rather than claiming liveness under resource attack, and is covered by boundary tests. No silent audit truncation: an operation unable to reserve its declared bounded audit/action storage returns ResourceLimit before protocol mutation.

### §6.5 Timers

RTT_j is the current positive delay estimate, initially PeerCaps.rtt, with operational minimum1microsecond. For the first normal/terminal response to the active logical request: if sent only once, sample Time−original_sent_time and replace RTT_j with max(1,sample); if reissued/retransmitted, exact request-to-response delay is ambiguous, so set RTT_j=max(RTT_j,Time−original_sent_time,1). The latter elapsed time is explicitly a conservative upper elapsed estimate, not a fresh-vote claim. original_sent_time is retained unchanged for that one logical request; all Time arithmetic is checked. This bounded state repairs underestimated RTT even when useful data arrives from an old poll. Duplicate/completed/unknown replies never update RTT.

Outstanding deadline=latest_actual_sent_time+2*RTT_j; factor2 operational in params.h. At or after deadline resend once, then rearm from actual Time. A wave poll reissue also updates latest_sent_time/deadline but never original_sent_time or request_id. Repeated timer call at identical Time emits no second resend. ScheduleTimer reports earliest future deadline; host services it on time. If host calls late, finish overdue wave at its logical deadline but open next wave at current Time; no unbounded zero-time catch-up loop. D=0 idles with no wave/timer/freeze. Local deadline overflow is nonfatal error and suspends scheduling, never wraps. Already-captured wave deadlines do not move when RTT changes; only later waves use the new estimate.

Regression: initial RTT1ms, current stable RTT3ms. The t3ms old-poll reply advances its still-active request and raises estimate to at least3ms; it never votes in the new wave. The next fresh poll has deadline at least6ms later, allowing an honestly fresh reply/vote. Preserve exact wave deadlines and extend this regression to larger latency jumps, no loss and10% loss.

## §7 ASSUME-PRESENT POOL

Always on, no Config.pooling. Pending consists of unadmitted/unrejected/nonprobation/non-local-rejected IDs decoded positive this height with an in-flight fetch, an awaiting-admission record or an open-session plus assertion. A new session starts plus=Pending,minus empty, unknown exclusion version; never starts from old peer membership. On positive decode, unadmitted eligible x enters all other open-session plus sets where x is in neither plus nor minus; apply residual delta. Wrong assumptions yield negative decode and remove that peer's plus. Admission removes Pending and normal own-add does not double-update already assumed references. Pending support is recomputed after every close/failure/removal; copying an ID into a new session does not create an independent donor, and known failed IDs enter probation instead of sustaining an assumption chain. Limits in§6.4 apply even with stalled sessions. Body failures follow§6.3 rather than retaining false assumptions. Correctness of valid decoded differences does not depend on assumptions being true; bandwidth improvement is an empirical question, not a theorem.

## §8 VOTING

Inputs beta_max,epsilon; D=current compatible connected population. M0=floor((1+beta_max)*D/2),M1tx=ceil((1−beta_max)*D),Broot=ceil(log2(25/epsilon)),Btx=ceil(Broot/3). For binary64 epsilon compute the stable equivalent ceil(log2(25)−log2(epsilon)) without overflowing the25/epsilon intermediate; positive normal/subnormal values remain valid. For D>0 and valid beta,M0<M1tx<=D. Constants are labelled derived/operational in params.h; T=25,Kop=8,deadline_factor2 and minimum RTT1us are operational. K=min(D,8). At wave start choose K distinct peers uniformly from canonical ordered peer list with the seeded RNG, independently across waves. Capture population,root,RTTs and start time. Deadline=start+2*max selected RTT; end when all selected peers answered or deadline, whichever first. First correlated NORMAL SYMBOLS with the current poll_id per peer supplies its one root vote; current-poll expired/resource_limited statuses count answered nonmatches with no item evidence; missing peers are nonmatches; continuations/old-poll responses do not vote. Connection population change abandons the wave, resets C and discards all stale population evidence before resampling. Own-root change resets C and invalidates every previously captured root/membership vote for that wave; no mixed-root sample is scored. Reconciliation may continue, but root scoring resumes only next wave.

Own candidate IDs={x in R_ID:Lambda_x>−Btx}; own exclusions are the complement in R_ID. Lambda is initially0 for a newly admitted or Pending ID, accumulates across waves, and transfers unchanged from Pending to admitted. Last-body removal clears its Lambda; a later admission starts0 unless it is currently Pending with a new valid lifetime. Invalid rejection/no remaining Pending support clears unadmitted Lambda. Global confidence entries are bounded by admitted+Pending+probation records. Own RootFn includes all bodies under candidate IDs. Body-only root changes reset C too.

At wave start M1hat=M1tx for the first wave of this population/root generation; thereafter ceil(D*previous_wave_matches/previous_wave_K), clamped[M0+1,D], from the preceding completed wave only. If that wave was invalidated, retain the last valid prior estimate; never use current-wave matches or hidden truth.

Root increment is the extended log hypergeometric ratio L(Y;D,M0,M1hat,K). Validate0<=Y<=K<=D and0<=M0<M1<=D. K=0,Y=0 gives0. Where both pmfs positive use their exact log2 ratio from a log-factorial table. Exactly one zero gives the corresponding signed infinity. For both-zero outcomes, extend monotonically: Y>min(K,M0) gives+infinity; Y<max(0,K−(D−M0)) gives−infinity. These branches exhaust feasible both-zero outcomes because support endpoints are nondecreasing in M. This is an explicit decision extension, not a claim that0/0 is an ordinary ratio. No finite sentinel/NaN.

C:=clamp(C+L,0,Broot), with explicit infinity branches. Finite upper saturation deliberately discards surplus evidence compared with unbounded CUSUM and is a conservative protocol amendment. Each transaction uses Lambda:=clamp(Lambda+Lx,−Btx,+Btx), same support extension. Kx=0 changes nothing.

Per-transaction evidence uses only current-wave sampled peers, at most once each/item. RootMatched: correlated first response root equals the captured own root and current own root, so record that peer's asserted yes on each captured candidate and no on excluded/Pending IDs, close immediately and perform no decoding/continuation. This is immediate evidence available in the wave, scored once at wave completion. It proves nothing about a malicious body's availability. Any own-root change before scoring discards it. Reconciled: mismatching-root peer abstains until its current session is Done during this or previous wave; x is yes iff in that pinned reconstructed reference and not in pinned exclusions. It speaks on x only if x in plus or admission_seq(x)<=own_seq_at_done; otherwise abstain. Pending has no admission sequence, so requires plus. Exclusions/candidate metadata are pinned with S, never live-mixed. Repoll new session replaces prior model and starts abstaining again until its own completion/match. Abstainers are not imputed. For each x, Kx is the number of distinct current-wave sampled peers eligible to provide evidence about x under these rules; Yx is the number of those peers whose evidence is yes (x in W_j). The transaction increment is exactly Lx=L(Yx;D,M0,M1tx,Kx), using the extended log hypergeometric ratio defined above, not M1hat. Kx=0 contributes zero.

Freeze when C>=Broot and every current candidate has Lambda=+Btx. Emit once per (tip,root,candidate bodies) frozen transition; later root change invalidates frozen status, resets C and permits a new transition. Continue reconciliation. T=25 calibrates only the finite25-wave boundary-null test under its sampling assumptions. It is not an unlimited-height epsilon bound, nor a proof of agreement, nor a per-item error bound for completion-conditioned/reused evidence. Evaluation must report false/split freezes and assumption violations explicitly. Passing acceptance tests does not establish statistical safety.

## §9 SIMULATOR AND EVALUATION

Drives SnowstormNode only through public API, reusing test/harness by include. Discrete-event network over5regions with log-normal jitter sigma=.25, per-link bandwidth and configurable loss; deterministic seed, parallel only across trials. Per-height pool: each honest node misses independent uniform subset size U[0,skew], has5 unique own transactions admitted in its order;10% of nodes hold everything. Ground truth stays outside core. Separate malicious peers send actual serialized withhold/inflate, early equivocation, fake-item, garbage and snapshot-inconsistent messages. Record agreement, correctness,false/split freezes,freeze ms/waves mean/p50/p99,symbols/pair/trueDelta,bytes/node/wave/height,peakRSS,fakes rejected,limit hits. Stamp every file with actual source commit,dirty flag,binary hash,configuration hash,seed and start time.

Main evaluation uses600nodes×500peers;200×32 is additionally the small-network check. Every original R1–R14 workload/adversary/loss/churn/arrival scenario,10heights/trial and50fresh trials remains required at both scales; R14 contains separate10%-withhold and10%-equivocation variants. Mandatory always-on Pending supersedes obsolete pooling-off protocol configurations. R11 andR12 are independent fresh-seed replications of R3 andR4 under the mandatory protocol, explicitly labelled replication rather than a pooling ablation; no production pooling flag or invented comparative benefit is introduced. This explicitly changes the obsolete ablation interpretation, not the trial counts or scenarios. Detailed network constants, metric estimands/censoring and neighborhood adversary-bound verification are fixed and independently reviewed before simulator evaluation; they are experiment inputs, not core protocol parameters. Old simulator measurements are superseded provenance only.

## §10 STATS AND OBSERVABILITY

Stats includes per-peer state bytes,stored symbols,change-log length,open sessions,limit hits by named limit,decode-step count,fakes rejected,unavailable marks,last_api_error and suspended_unadmitted. Also immutable sorted own-ID/body/candidate/Pending/probation/rejected/local_rejected/confidence views; admission seqs; wave population/sample/root/start/deadline/number; C and Lambda; per-peer active/fresh/RootMatched/Done status,plus/minus/exclusions,pinned metadata,raw/residual cells with indices,own_seq_at_done; fetch tokens, awaiting-admission expected hashes and donors; exact capacity-byte ownership terms and last-call action/decode/completion/error audit.

Last-call diagnostic events carry one strictly increasing per-call order across committed atomic One/Two decodes, completions, returned actions and requester-model lifecycle events. A created event precedes any decode using that model. A released event denotes actual destruction of the retained requester model, after its final committed decode/completion and emitted fetch-support action; it is emitted for replacement, expiry, invalidation, disconnect and tip-reset destruction. Done completion ends active reconciliation but is not model release: retained membership remains until its specified evidence-window release. Responder pins are not requester-model lifecycle events. Decode events never report policy-rejected or probation candidates as committed. Every lifecycle event consumes the existing other-diagnostic-record allowance. The ordered trace must allow the host to reconstruct references from independently known admission/outcome events, model creation and previously validated decodes, including synchronous cross-session pooling, without trusting reported membership bits as their own oracle.

Audit contains every transient event in the preceding call, including models closed before stats(); each grouped One/Two has original source cell and membership bits. Entries are reset at the start of the next API call and bounded as§6.4, never silently truncated. stats() is a read-only value copy and may allocate outside hot paths; nodes receive no oracle truth. The harness consumes Stats after each call and independently reconstructs/encodes the reference, validates full decode postconditions and checks byte accounting. Successful reconciliation Done is checked against captured raw snapshot; honest RootMatched is checked against captured candidate truth and explicitly never asserted raw-exact. All7000T7 trials and5/20/100-node T9 cases exercise actual voting/fast paths and require quiescent candidate agreement/body validity, plus exact raw snapshot checking for every actual Done. Honest excluded-extra RootMatched and malicious root-echo fixtures are mandatory negative-claim tests.
<!-- snowstorm-core-normative:end -->


## 1. Executive Summary & Pseudo-Consensus Philosophy

This historical section and its subsections are preserved unchanged in [Snowstorm superseded designs](research/snowstorm-superseded-designs.md); the normative reconciliation-core specification above replaces them.

## 2. Why Snowstorm is *Pseudo-Consensus*

A foundational architectural principle of Lotus V2 is the strict boundary between **Hard Consensus Validity** and **Snowstorm Pseudo-Consensus Coordination**.

### 2.1 Hard Consensus Invariance (`consensus.md` C01–C28)

The prior description is preserved unchanged in [Snowstorm superseded designs](research/snowstorm-superseded-designs.md); use the normative core contract above for current reconciliation semantics.

### 2.2 Incentive Compatibility: Why Participation is a Strict Nash Equilibrium

The prior description is preserved unchanged in [Snowstorm superseded designs](research/snowstorm-superseded-designs.md); use the normative core contract above for current reconciliation semantics.

### 2.3 Three-Stage Block Reception Pipeline (`Stage 1: Cached Layer Match` $\to$ `Stage 1.5: 1-RTT Peer Miniblock Delta` $\to$ `Stage 2: cmpctblock`)

The prior description is preserved unchanged in [Snowstorm superseded designs](research/snowstorm-superseded-designs.md); use the normative core contract above for current reconciliation semantics.

### 2.4 System, Network, and Adversary Model

The prior description is preserved unchanged in [Snowstorm superseded designs](research/snowstorm-superseded-designs.md); use the normative core contract above for current reconciliation semantics.

## 3. Resolving the Set-Reconciliation Trilemma

This historical section and its subsections are preserved unchanged in [Snowstorm superseded designs](research/snowstorm-superseded-designs.md); the normative reconciliation-core specification above replaces them.

## 4. Mathematical & Wire Specification of `RatelessMiniblock`

This historical section and its subsections are preserved unchanged in [Snowstorm superseded designs](research/snowstorm-superseded-designs.md); the normative reconciliation-core specification above replaces them.

## 5. Multi-Peer Coupled BCH Peeling & The Six Formal Theorems

This historical section and its subsections are preserved unchanged in [Snowstorm superseded designs](research/snowstorm-superseded-designs.md); the normative reconciliation-core specification above replaces them.

## 6. Epoch Crystallization State Machine, Hypergeometric SPRT Confidence & `BatchId(E)` Conflict Quarantine

This historical section and its subsections are preserved unchanged in [Snowstorm superseded designs](research/snowstorm-superseded-designs.md); the normative reconciliation-core specification above replaces them.

## 7. Complete 16-Pass Adversarial Red-Team Matrix

This historical section and its subsections are preserved unchanged in [Snowstorm superseded designs](research/snowstorm-superseded-designs.md); the normative reconciliation-core specification above replaces them.

## 8. Benchmark Summary

This historical section and its subsections are preserved unchanged in [Snowstorm superseded designs](research/snowstorm-superseded-designs.md); the normative reconciliation-core specification above replaces them.

## 9. References

1. **[Vermorel, Séchet, Chancellor, & van der Wansem 2018]** Joannes Vermorel, Amaury Séchet, Shammah Chancellor, and Tomas van der Wansem, *"Canonical Transaction Ordering for Bitcoin"*, June 12, 2018.
2. **[Vermorel, Séchet, Chancellor, & Cox 2018]** Joannes Vermorel, Amaury Séchet, Shammah Chancellor, and Jason Cox, *"Merklix Tree for Bitcoin"*, July 2018.
3. **[Chancellor 2026]** Shammah Chancellor, *"Adaptive PoW Monetary Policy Without Oracles: A Constructive Mechanism for Pseudo-Stability via Work-Coupled Tail Emission and Burn"*, Lotus Network Technical Paper, 2026.
4. **[Merkle 1987]** Ralph C. Merkle, *"A Digital Signature Based on a Conventional Encryption Function"*, in *Advances in Cryptology — CRYPTO '87*, Lecture Notes in Computer Science, vol. 293, pp. 369–378, Springer, 1988.
5. **[Minsky, Trachtenberg, & Zippel 2003]** Yaron Minsky, Ari Trachtenberg, and Richard Zippel, *"Set Reconciliation with Nearly Optimal Communication Complexity"*, *IEEE Transactions on Information Theory*, vol. 49, no. 9, pp. 2213–2218, September 2003, DOI: `10.1109/TIT.2003.815784`.
6. **[Dodis, Ostrovsky, Reyzin, & Smith 2004/2008]** Yevgeniy Dodis, Rafail Ostrovsky, Leonid Reyzin, and Adam Smith, *"Fuzzy Extractors: How to Generate Strong Keys from Biometrics and Other Noisy Data"*, in *Advances in Cryptology — EUROCRYPT 2004* (extended version in *SIAM Journal on Computing*, vol. 38, no. 1, pp. 97–139, 2008; introduces BCH syndrome decoding / PinSketch).
7. **[Luby 2002]** Michael Luby, *"LT Codes"*, in *Proceedings of the 43rd Annual IEEE Symposium on Foundations of Computer Science (FOCS)*, pp. 271–280, November 2002.
8. **[Shokrollahi 2006]** Amin Shokrollahi, *"Raptor Codes"*, *IEEE Transactions on Information Theory*, vol. 52, no. 6, pp. 2551–2567, June 2006, DOI: `10.1109/TIT.2006.874390`.
9. **[Goodrich & Mitzenmacher 2011]** Michael T. Goodrich and Michael Mitzenmacher, *"Invertible Bloom Lookup Tables"*, in *Proceedings of the 49th Annual Allerton Conference on Communication, Control, and Computing*, pp. 792–799, September 2011 (`arXiv:1101.2245`).
10. **[Corallo 2016]** Matt Corallo, *"BIP 152: Compact Block Relay"*, Bitcoin Improvement Proposals, May 2016.
11. **[Ozisik et al. 2019]** A. Pinar Ozisik, Gavin Andresen, Brian N. Levine, Darren Tapp, George Bissias, and Sunny Katkoori, *"Graphene: A New Protocol for Block Propagation Using Set Reconciliation"*, in *Proceedings of the ACM Special Interest Group on Data Communication (SIGCOMM)*, pp. 303–317, August 2019.
12. **[Naumenko et al. 2019]** Gleb Naumenko, Gregory Maxwell, Pieter Wuille, Alexandra Fedorova, and Ivan Beschastnikh, *"Erlay: Efficient Transaction Relay for Bitcoin"*, in *Proceedings of the 2019 ACM SIGSAC Conference on Computer and Communications Security (CCS)*, pp. 817–831, November 2019 (`arXiv:1905.10518`).
13. **[Chawla et al. 2019]** Nakul Chawla, Hans Walter Behrens, Darren Tapp, Dragan Boscovic, and K. Selçuk Candan, *"Velocity: Scalability Improvements in Block Propagation Through Rateless Erasure Coding"*, in *2019 IEEE International Conference on Blockchain and Cryptocurrency (ICBC)*, pp. 447–454, May 2019.
14. **[Rocket et al. 2019]** Team Rocket, Maofan Yin, Kevin Sekniqi, Robbert van Renesse, and Emin Gün Sirer, *"Scalable and Probabilistic Leaderless BFT Consensus through Metastability"*, `arXiv:1906.08936`, 2019.
15. **[Babel et al. 2023/2025]** Kushal Babel, Andrey Chursin, George Danezis, Lefteris Kokoris-Kogias, and Alberto Sonnino, *"Mysticeti: Low-Latency DAG Consensus with Fast Commit Path"* (*"Mysticeti: Reaching the Limits of Latency with Uncertified DAGs"*), `arXiv:2310.14821` / *Network and Distributed System Security Symposium (NDSS)*, 2025.
16. **[Yang, Gilad, & Alizadeh 2024]** Lei Yang, Yossi Gilad, and Mohammad Alizadeh, *"Practical Rateless Set Reconciliation"*, in *Proceedings of the ACM SIGCOMM 2024 Conference*, pp. 186–205, August 2024 (`arXiv:2402.02668`).
17. **[Nakamoto 2008]** Satoshi Nakamoto, *"Bitcoin: A Peer-to-Peer Electronic Cash System"*, October 2008 (`https://bitcoin.org/bitcoin.pdf`).
18. **[Oak 2026]** Professor Oak, *"Snowball to Snowstorm: Rateless Set Reconciliation and Probabilistic Mempool Preconsensus for Proof-of-Work Blockchains"*, October 2026.


## Changes

- Archived the complete prior document without changing its bytes; retained the §2 hard-consensus/optional-coordination introduction and §9 bibliography unchanged here. Superseded frame, partition, decimation, degree-3, sizing, streaming, BatchId, Avalanche and SnapBlock sections now point to the archive.
- Replaced the old “implemented & verified” status with the actual specification/contract-authoring state. Historical benchmark, simulator and integration results do not validate this core.
- Resolved §2.1/§5.4 legacy mandatory Merklix root gates in favor of explicit host admission, raw-snapshot Done and separately labelled untrusted RootMatched evidence. Ordinary validation and fallback remain mandatory; root votes do not authenticate bodies.
- Resolved §2.4/§4.1/§5.3 identity conflicts: short IDs use tx_hash only, zero maps to one, collision bodies share one sketch ID, and body-specific removal updates roots without incorrectly changing the ID sketch. Full collision-body dissemination is not claimed.
- Resolved §5 Theorem 2’s legacy sign/count and isolated-projection rules in favor of mixed-sign count-zero pairs, current-reference membership, the S5 check, always-on bounded Pending assumptions and body-failure probation.
- Resolved §6.2’s ξ regularization, M0+8 alternative, imputed abstention, settled-only root and 95%-wave rules in favor of the marked exact support extension, M0+1 clamp, explicit abstention, Lambda>-Btx candidate set and all-or-deadline waves.
- Corrected the integer schedule’s demonstrated index-1 probability conflict while retaining T3’s target, sample count and tolerance. Corrected positive-decode minus-set removal and structural contradictory-cell termination without an iteration cap.
- Defined immutable snapshot candidate/exclusion metadata, logical request versus poll correlation, conservative RTT adaptation, terminal resource/expiry responses, and bounded awaited-admission/body-policy outcomes. These resolve ambiguity before executable-contract freeze.
- Replaced incomplete peer-byte accounting with actual bounded ownership accounting, including Pending, failure tables, donor and snapshot state, Actions and audit storage. The fixed per-peer floor is explicitly counted.
- The mandated root-match shortcut establishes asserted candidate agreement, not unconditional raw-set equality. Finite-horizon threshold calibration does not establish unlimited-height or selected-evidence statistical safety. These limitations remain explicit for evaluation and the paper.
- Artifact review clarification: defined atomic malformed-batch peeler append errors; made live BodyResult enum validation precede ignored-field handling; cancelled in-flight donor fetches on disconnect while preserving already-admitted callback obligations; distinguished caller-owned Stats copies from fully counted compact retained diagnostics; and required ordered committed-decode/model-lifecycle observations for independent reference auditing. No trial counts, retained-state limits or returned-action accounting were reduced.
