# Initial relay convergence: authoritative request state

**Current candidate: dc1c12adaf**, branch `repair/authoritative-relay-requests-20261021`, source `/Users/shammah/repos/lotus-v2-authoritative-relay-requests`. Base is actual tested521-derived `2b61dded451755e175681f41a57281a5c0554e32`. Exact identities are in delivery.json. Native before/after gates are pending with N1; no500k rerun or performance claim.

## Defects and replacement

Relay-epoch requests were already tracked by the ordinary InvRequestTracker using synthetic(epoch,short-ID) keys, subject to its existing peer limits and timeout semantics. Yet SendMessages additionally copied their solicitation state into the generalized Merklix handler's4096-ID pending set. The ordinary tracker could issue5000+ requests while this duplicate set retained only4096. Consequently valid responses from a non-high-bandwidth peer could be dropped as unsolicited solely because the duplicate set omitted their IDs.

The candidate removes that duplicate relay-epoch registration. A new read-only `InvRequestTracker::IsRequested(peer,key)` query uses the existing ByPeer tree index in O(logN). The handler selects relay-epoch response bodies against the actual requesting peer and declared epoch, then invokes ordinary transaction admission. A response contains at most4096 bodies; one cs_main lock checks those bounded bodies, without scanning/copying100k requests. Selection allocation occurs before the lock. Opted-in unsolicited bodies retain a fast path without that additional lock. All existing validation, rejection, orphan, peer attribution, announcement bounds and timeout rules remain authoritative.

Generic reconciliation and the new page contexts still use their bounded4096 pending sets. There is no new index, auxiliary growing ID set, request-backpressure queue or full-pool scan. The original request order and ordinary full-ID request paths are unchanged.

A separate existing bug affected mixed generic responses: if even one body matched a pending request, other bodies from the same opted-in high-bandwidth peer were silently discarded. The candidate consistently retains all bodies from such opted-in peers, while still clearing their fulfilled pending IDs. Non-high-bandwidth peers continue to have unrequested bodies filtered out.

## Focused gates

1. **relay_epoch_responses_use_authoritative_requests:** actual wire handshake,5000 absent short IDs and two emitted requests. The last body's request is beyond the old4096 duplicate cap. Its funded valid transaction must enter the mempool. The wrong peer, wrong epoch, unrequested transaction and expired request must still fail admission.
2. **shorttx_batch_admission_fallback_and_proactive_push:** leave one pending delayed match beside20 opted-in valid bodies; retain all20, including child/parent. The non-opted-in stage includes an unrequested third body and requires it to remain rejected.
3. **bursts_wait_for_the_relay_tick:** preserve fixed-tick and known-inventory behavior with an actual private capability offer. The former manually inserted handler flag was insufficient after MR06; this is a fixture correction, not a new node behavior.

The matched control uses the candidate's test file with its five production files restored to exact2b61. Tests use only APIs already present in that control. N1 owns build/cache and raw receipts. No standalone build is started by this lane.

## Superseded candidate and source boundary

`superseded-backpressure/` preserves the earlier source proposal and tests. **Do not promote4fac298686.** Although it fixed lost tracking slots, its4096 in-flight window would leave a large ready backlog for the existing GetRequestable full scan/sort on every poll. Root explicitly selected this authoritative-state replacement instead.

Growth investigator owns the independent eventual-reconciliation coverage/page repair. Its generic page scope remains disjoint from this LIVE_MEMPOOL relay-epoch response path. A combined correctness gate must precede a full-peer500k rerun. Nothing here claims which fraction of the observed3318/921 missing IDs came from each defect.

Canonical daemon/v2 currently pins original142, which lacks the later relay-epoch machinery. Do not blindly import this521-derived repair there. The mixed generic-response defect traces to original shared reconciliation owner3a7173fde30; authoritative relay-epoch selection belongs to negotiation owner56443331da. The coordinator must map the tested dependency lineage before promotion.
