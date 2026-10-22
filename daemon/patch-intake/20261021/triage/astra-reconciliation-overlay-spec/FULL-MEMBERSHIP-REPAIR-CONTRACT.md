# Permissionless full-membership repair: implementation contract

Status: source implementation authorized; not a runtime success claim. This is the bounded overnight repair contract agreed with the relay owner on 2026-10-21. It does not select an epoch-consensus design or integrate the separate persistent-arena rewrite.

## Problem and boundary

The tested cf50cd5e relay selects admissions younger than 30 seconds, physically prunes admission-query history after 60 seconds, and represents at most 4096 selected transactions. Changing the scheduler cannot make older or higher-ranked live transactions discoverable. The new mode represents a complete captured live mempool, irrespective of admission age and cardinality. Legacy relay remains compatible but retains its explicitly known coverage limits.

No stake, Avalanche quorum, individual transaction voting, local checkpoint seal, vector clock, MinHash, or new chain authority is required. Normal transaction validation and existing chain policy remain authoritative.

## Smallest transport change

Negotiate the previously reserved capability bit 3 and full-mempool scope 5, after verifying those allocations against the integration base. Both peers must negotiate before either interprets the new framing. Existing scopes and messages keep their old serialization and behavior. Reuse the prepared fullrecon prefix/folding/framing helpers where their native-root tests pass; change their singleton body mechanism to a complete-prefix body page. GF hints are optional future optimization, not required for this baseline; legacy BCH/GF processing is preserved.

Each offer names an immutable snapshot with a fresh unpredictable context ID, canonical transaction root, chain anchor for diagnostics/domain binding, and root children. A context ID is a connection-bound snapshot handle, not an Avalanche epoch or a shared ordinal. One active receiving round and one active serving context per peer connection are sufficient. Sending a replacement offer must not silently replace an accepted serving context; close/expire it explicitly or wait. The same underlying captured snapshot may be shared by several connection-owned contexts.

Every request and response binds scope/version, context ID, nonzero monotonically increasing request ID, and exact canonical prefix. The receiver also records the expected prefix digest and owning connection locally. Root and prefix identity come from that owned context, never from an unsolicited response. A response may not retag an old request into a new capture. Duplicate, stale, wrong-peer, wrong-prefix, and unknown-context responses cannot complete work. Unknown contexts return CONTEXT_GONE without reading or hashing the live mempool. Connection teardown cancels all its request ownership.

## Capture and storage

Capture all admitted transaction references and the membership generation under the mempool's existing synchronization. Preserve both TxId and TxHash. Release the mempool lock before sorting, canonical hashing, descriptor construction, serialization, or network I/O. References keep captured bodies immutable even when the live mempool removes them. Admission policy still decides whether a received old body can enter the current mempool.

The interim implementation may make one complete inventory/reference copy per captured generation. Cache and share this capture across peers rather than copy the same generation separately for each peer or request. Never rebuild the full root for each prefix request. A snapshot's sorted index and prefix descriptors are immutable; ordinary arrivals and removals belong to a later capture. The old numeric-MSB published tree is not interchangeable with canonical LSB-first transaction roots.

Reserve a global exposure budget before capturing. Account for records, index/descriptor storage, retained body memory, queued response bytes, and temporary construction memory; a count-only context cap is insufficient. Charge shared underlying storage once or conservatively overcharge each owner. Enforce implementation limits before growing vectors or trees, including adversarial unary prefix paths. If reservation fails, return BUSY and retry fairly; never construct or advertise a truncated snapshot. A bounded-copy baseline can refuse a pool larger than its configured budget; document that limit rather than claim arbitrary-size coverage.

Prototype defaults should permit the 10k real-transaction gate comfortably; use configurable budgets and record the actual charged bytes and peak RSS. Initial reasonable bounds are four shared snapshot captures, one context per direction per connection, and a 256 MiB global snapshot exposure budget, subject to the implementation's conservative accounting. These are resource defaults, not consensus parameters or a 500k performance claim.

## Exact prefixes instead of truncated pages

Prefixes use canonical TxRoot bit order: byte 0 bit 0 first, four bits per expansion, depths 0 through 256. A bucket response contains at most sixteen child descriptors and must recombine to the requested parent digest using the existing canonical empty/singleton/internal-depth rules. Numeric counts are not independently authenticated by this root: counts guide request sizing, but exact digest reconstruction and terminal identities are authoritative. A malicious count cannot suppress a mismatched digest or allocate count-sized storage.

For a mismatching prefix, request a complete body page when its advertised count is at most 64. The sender answers one of:

- OK: every captured body in that prefix, exact complete set, within both the body-count and encoded-byte limits.
- LIMIT: the complete prefix exceeds a limit; no partial body list is claimed complete. The requester expands that prefix and retries its children.
- UNAVAILABLE, CONTEXT_GONE, or BUSY: explicit unresolved/retired/retry outcome.

The page wire body count is bounded before allocation. Bound the entire frame before decoding; retain the prepared 2 MiB cap or the smaller existing transport cap. Measure encoded size before producing OK. One request yields at most one response frame. No response vector truncation, implicit continuation, or fixed-depth overflow list is allowed. A prefix larger than 4096, 65535, or the page limit continues splitting beyond depth 16. At depth 256 there is at most one TxId: an oversized singleton or unavailable body is an explicit unresolved outcome, not success or an infinite LIMIT loop.

Before exposing an OK page to admission, reject duplicate TxIds, incorrect TxHashes, out-of-prefix members, and any page whose canonical prefix digest or exact expected membership fails verification. Recompute the subtree at its absolute depth, not as a fresh depth-zero root. A malicious count inconsistency is rejected even when the digest happens to match. Different TxHashes for one TxId are not silently deduplicated. An expansion only authenticates descendant digests; a terminal complete page proves the exact enumerated contents.

Equal local/remote prefix digests can skip that subtree using the pinned local view. Empty remote prefixes require no body fetch even if local extras exist. This is a pull operation: local extras are retained, not removed to imitate the remote snapshot. The reverse direction transfers the other difference. All matches are against pinned views, never a moving pool re-read.

## Work, pacing, retention, and recovery

Use depth-first traversal with a bounded deferred-prefix stack (at most 64 * 15 + 1 entries for 16-way expansion), not a queue proportional to all leaves. Keep at most one outstanding request in each receiving round unless a separately bounded pipeline is necessary. Progress is completion of an owned verified response, not receipt of an arbitrary packet.

Pace requests and responses against the existing shared 32-per-second per-peer inbound command budget, counting response frames rather than only requests. Reserve headroom for summaries and ordinary control traffic. An initial eight request/response work exchanges per second per direction fits below the limit when both directions run, provided legacy reconciliation for that peer is not simultaneously consuming the same budget. Use bounded queues and timer-driven continuation; do not raise the generic limit or issue sixteen unsolicited responses to one mask request. Timeout retries allocate fresh request IDs and do not erase the prefix's unresolved obligation.

Serving contexts have bounded idle and absolute leases, renewed only by verified progress, and are released on completion acknowledgment, cancellation, disconnect, or expiry. Choose a lease long enough for the configured snapshot size and paced frame budget; do not give every large snapshot a fixed 30-second lifetime. A practical prototype may use a 60-second idle lease and a 30-minute absolute lease, with shorter tests overriding them. Expiry is explicit; restart under a new context and fresh immutable capture. No retained root is immortal, and no new offer silently takes over an old context.

Admission runs through the ordinary validation path after membership verification. Parent/child ordering may cross prefixes: retain bounded verified recovery work and retry missing-parent children after their recovered parents admit, or collect and topologically submit the recovered set under the same global budget. A one-shot page admission that permanently drops a valid child before its parent arrives is not sufficient. Already-present exact transactions are successful no-ops; conflicting witnesses, policy failures, spent inputs, and unavailable ancestors are explicit outcomes. Do not force admission because a body belongs to an advertised root.

Maintain separate outcomes: remote snapshot coverage, bodies reconstructed, admission accepted/already-present, and unresolved/invalid. Finishing a DFS is not proof that live mempools are equal. Even successful complete remote coverage does not remove local extras or guarantee remote policy accepts them. Later rounds and reverse pulls cover changes after capture. Under a finite stable compatible set, reachable serving peers, fair scheduling, sufficient budget, and successful normal admission, repeated bidirectional passes must cover every member; no age/rank blind spot may remain.

## Required focused gates

1. Canonical root and absolute-prefix reconstruction match the native TxRoot implementation, including singleton collapse, empty children, depth 252/256, and TxHash distinctions.
2. More than 4096 records in one old 16-bit prefix are all discoverable; complete-page byte LIMIT forces deeper expansion without truncation. Exercise a count above 65535 without narrowing it to uint16.
3. Wrong context/request/peer/prefix, replay, corrupted page, duplicate identity, false counts, and unavailable singleton never produce successful coverage. Unknown-context requests do not capture a new pool.
4. Insert/remove after capture leaves all responses and root unchanged. A new round sees the changed membership. Disconnect, timeout, BUSY, cancellation, and allocation failure release reservations and permit retry.
5. Parent and child in different prefixes, with child delivered first, eventually admit under normal validation; accepted duplicates are harmless. Reorg/policy failures remain explicitly unresolved.
6. Actual three-node integration with Avalanche off and no stake: isolated injection of at least 10k valid transactions, age beyond 60 seconds, reconnect, exact TxId inventory equality on every node. Include balanced missing/extras, not only one empty receiver. Use ordinary negotiated mode, not a hidden BIP35 dump, cap raise, or unsolicited-body bypass.
7. Record frame counts/rate-limit drops, pinned/queued bytes, release after disconnect, and time to convergence. Then test churn/partition recovery. A 500k gate is separate and only scheduled after this focused gate passes.

Owner implements in isolated source. Astra's overlay and protocol reviewers inspect the actual candidate once, raise concrete blockers, and verify any narrow repairs. N1 exclusively owns native build and network-test leases. No canonical source promotion follows merely from this design note.
