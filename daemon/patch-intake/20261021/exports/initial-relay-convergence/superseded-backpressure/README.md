# Initial relay convergence: requests, responses and bounded tracking

This lane addresses initial announcement/request bookkeeping on the **actual tested521-derived** source `2b61dded451755e175681f41a57281a5c0554e32`, not the separately pinned original142 source. Exact candidate identity is in delivery.json. N1 owns before/after native validation and integration. No500k retry or throughput claim is made here.

## Source-supported defects and candidate behavior

1. **Mixed responses lose opted-in bodies.** When a high-bandwidth response contained even one tracked requested ID, HandleShortTx retained only tracked matches and silently discarded other bodies in that response. The same opted-in peer could send those other bodies in a separate response and have them accepted. Candidate c794cb93eb consistently retains all opted-in bodies while still clearing fulfilled pending IDs; non-high-bandwidth peers remain restricted to solicited IDs. Existing rate, size and authoritative transaction validation still apply.

2. **The request tracker and solicitation tracker disagree on capacity.** SendMessages could mark many thousands of short IDs in flight and emit multiple requests, while RecordPendingShortTxRequest retained only4096 IDs per peer/scope/context. The candidate derives available bounded slots before constructing requests. IDs beyond that window remain requestable in the ordinary tracker rather than being marked requested without solicitation state.

3. **Abandoned/fulfilled requests strand slots.** Ordinary request timeouts now release the corresponding pending short ID. Receiving a body by any peer route also releases matching pending slots from other peers when the ordinary synthetic requests are forgotten. Otherwise adding backpressure would permanently strand slots after another peer delivered the transaction. Cleanup scans at most64 existing tracked contexts; it does not scan the mempool.

The source keeps the existing100k short-ID announcement bound and peer permission rules. It does not teach the ordinary request tracker to retry the same unresponsive peer forever. Timeout still advances to other announcers or completes that one-shot announcement; eventual recovery is the separate reconciliation-coverage lane. Transactions removed by fee filters, invalid/conflicting transactions and orphan handling keep their existing meanings.

## Focused reproduction/gates

- Existing `shorttx_batch_admission_fallback_and_proactive_push`: leave one pending delayed match before sending20 opted-in valid bodies. All20 must be admitted, including the child/parent pair. Old selection discards the other bodies.
- `short_id_request_window_backpressure_and_timeout`: announce5000 distinct absent IDs; request4096, retain904 as eligible, deliberately omit the first reply, advance beyond the2-second timeout, request the remaining904, and prove slots are released after their timeout too.
- `short_id_body_satisfies_other_peer_pending_slots`: actual announcement/request bookkeeping plus delayed response state on another peer; receiving the body through the validated-batch callback must release both peers' pending slots.

- `bursts_wait_for_the_relay_tick`: preserve the existing fixed-tick/known-inventory behavior using an actual capability offer. Its former manual private-handler flag does not establish the peer feature required by MR06. This is a fixture correction, not another node behavior change.

The mixed-response test also includes an unrequested third body in its non-high-bandwidth stage and requires it to remain rejected.

For a matched old-production control, keep the candidate's two test files but restore its three production files to exact2b61. The tests use no newly added public helper API. N1 was given the frozen source and selectors; actual results remain pending.

## Scope and integration

Growth investigator owns4096 recovery coverage and explicit page/range protocol work. This lane changes only SendMessages request construction/cleanup and the pending/response section of V2PeerProtocolHandler. Paging dispatch/handler edits are disjoint and require combined review before benchmarking. Network captures have not established which fraction of the observed3318/921 missing IDs came from these defects.

The response selection predates sendinvshort in original shared reconciliation owner `3a7173fde30`; current fixup commits target negotiation owner564 pending the coordinator's causal-prefix mapping. The request-window construction belongs to negotiation owner564. Do not blindly apply either to original142: it lacks these later helpers and feature exchange. Preserve validated source identities and parent mapping.
