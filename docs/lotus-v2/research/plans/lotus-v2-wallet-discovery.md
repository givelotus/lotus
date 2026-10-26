# Private V2 confirmed wallet discovery

This branch adds `tools/lotus-v2-devnet/chronik_discovery.py` as a controller integration adapter. It does not change consensus, the native encrypted wallet, the controller, or its node lifecycle. Integration into a runnable controller and actual native-node acceptance remain the owner's gate.

The wallet's public registered Payment output supplies **all** its Payment roots (`info.payment_output.branches` in the current sole-Payment native client). The client ORs those roots in one `/v2/branches/utxos` request, avoiding separate-root scans with incompatible snapshots. It checks each returned output against that same output's branches. Repeated outpoints are deduplicated; differing duplicate output payloads fail. No manually entered funding outpoint is needed.

`Client(HttpTransport(url), chain_id, profile_id).discover(roots)` returns typed immutable candidates and their confirmed snapshot. `chain_id` and `profile_id` must come from the trusted native wallet/manifest binding, never the HTTP status itself. Current wallet info calls the validation profile `profile_digest`; confirm this equals the Chronik binding's `profile_id` in the deployment manifest. IDs are native lowercase 32-byte wire hex without reversal. Heights, generation and money require canonical uint64 decimal strings. Output indexes remain JSON uint32 integers. The HTTP value is discovery evidence only.

Every page, initial status and final status must have identical chain, profile, tip, height and generation. Both status fences require readiness. A 409, 503, readiness failure or changed stamp discards the entire attempt and starts without a cursor. Default limits are 100 pages of 100 records, two restarts, five seconds per HTTP request, 32 KiB request and 256 KiB response caps. Limits and retries are finite; no partial scan is returned. A call can take up to `(max_pages + 2) * (retries + 1) * timeout` seconds, so the controller must additionally enforce its existing absolute deadline by passing a transport with remaining-deadline checks. No delay/backoff is imposed; bounded retries can fail promptly during sustained recovery. More than 256 roots requires a future native root-set/export and coherent partition protocol; this client fails closed.

## Controller hook

Inside the existing wallet operation lock and deadline, obtain native `info`, require registered Payment policy, take all public `payment_output.branches`, and initialize the client from trusted binding and node-specific Chronik URL. Call:

```python
discovery, state = discover_and_reconcile(
    client, roots,
    lambda point: self._invoke(name, "track", {
        "prev_txid": point.txid, "prev_index": point.index,
    }, deadline),
    lambda: self._invoke(name, "reconcile", {}, deadline),
)
```

The controller must reject native non-success results in these callbacks (its `_invoke` currently does), preserve its session/node namespace checks and use a remaining-deadline-aware transport. Invoke discovery before balance/prepare/send and explicit reconcile; reorg-sensitive UI should show the returned native reconcile tip. The exact `prev_index` request shape should follow current native `RequestShape` (the native client accepts numeric index). The current controller already uses `track` for funding. A successful discovery is not proof of completeness against a dishonest index: no client can prove omitted Payment postings from this API. A failed index scan must be surfaced, never reported as zero balance.

Native `track` calls `PaymentEngine::TrackFunding`. That function reads the authoritative native anchor and walletcontext, validates the coin and Payment ownership, rechecks the anchor, then persists only the outpoint. It never imports HTTP value, token, proof, paths or spendability. Native `reconcile` then obtains current verified walletcontext and reports present/reserved/mature. Native operations may advance beyond the HTTP snapshot: this is intentional and safe because HTTP supplies only hints. A stale/disappeared candidate causes native rejection. Earlier successful track operations can persist if a later callback fails; retries are idempotent. The whole scan is not an atomic import. No HTTP passphrase, secret key, signing request or private wallet file is involved.

Confirmed discovery cannot discover pending inbound transactions. `/v2/status` advertises `confirmed_only=true` and `pool_indexed=false`. Native PoolCoordinator transaction status, persisted outgoing transactions, reservations, rebroadcast and abandon remain authoritative for pending lifecycle. Display confirmed discovery separately from pending receipt/status and avoid promising pending branch indexing. After confirmation, discovery tracks the receiver output and native reconciliation decides availability/maturity; after reorg, reconciliation also updates previously tracked coins absent from the new discovery result.

## Verification

Run `python3 -m unittest discover -s tools/lotus-v2-devnet/tests -p test_chronik_discovery.py`.

Eight tests cover paging and all-root deduplication, uint64 maximum values, stale/unavailable restarts, generation ABA and tip transitions, malformed identities/values/filter results, duplicate conflicts and page/retry bounds, native rejection before reconcile, actual local HTTP request/response transport and HTTP error/redirect/oversize/JSON cases. HTTP tests bind ephemeral loopback ports and use synthetic fixtures; they do not claim a live Chronik/native integration result. No heavy node or production listener was launched. The integration owner must run a real confirmed funding -> discovery -> native track/reconcile -> spend -> confirmation -> reorg/restart flow on private testnet before declaring the controller integrated.
