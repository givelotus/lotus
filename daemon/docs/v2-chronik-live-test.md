# Native V2 Chronik HTTP lifecycle gate

`daemon/tests/check-v2-chronik-live.py` runs the existing native private relay
wallet harness with an actual V2 HTTP listener on each development node. It
requires the opt-in native Chronik host integration and the complete schema 2
local fixture. Static compilation alone does not establish acceptance.

Use reviewed, built daemon, native SQLite wallet client and compiler artifacts.
Supply their exact source commits. The output directory must not exist:

```sh
python3 daemon/tests/check-v2-chronik-live.py \
  --daemon /absolute/path/to/lotusd \
  --wallet-client /absolute/path/to/lotus-v2-wallet-client \
  --manifest tools/lotus-v2-devnet/fixtures/local-test-manifest.json \
  --compiler /absolute/path/to/built/compiler \
  --daemon-source FULL_COMMIT \
  --wallet-source FULL_COMMIT \
  --compiler-source FULL_COMMIT \
  --output /tmp/new-v2-chronik-run
```

The driver creates independent sender and recipient encrypted SQLite wallets,
compiles their Payment policies, mines funding and maturity blocks, and sends two
wallet-originated transactions across A–B–C. C selects payments from its native
pool. The workflow restarts native homes, rebroadcasts persisted signed bytes,
confirms payments, creates a longer competing fork, and re-mines the detached
valid payment. Payment wire bytes are never passed as mining transaction inputs.

The HTTP layer exercises `/v2/status`, branch UTXO and output history queries,
and direct outpoint lookups. It compares native tip/profile/height and coin
presence, checks decimal-string uint64 values, verifies native wallet recipient
values and sender change arithmetic, and checks position matches. Separate
single-root Payment outputs demonstrate OR union and same-output AND exclusion;
this fixture does not create a multi-branch output with multiple matching
positions. Pagination uses one output per page, checks deduplication, retains a
continuation across same-tip restart, and rejects old-tip cursors. History must
remove the detached payment at height 7 and restore it when re-mined at height 8;
confirmed spent funding history must also revert to an unspent observation.

Listeners bind ephemeral loopback ports; ports 10604, 10605 and 8331 are refused.
No existing home is reset. The driver owns and stops its exact child processes.
HTTP 503 responses and changing snapshots receive bounded retries. A genuine
protocol mismatch fails the gate. This gate tests confirmed indexing and does
not establish pool indexing, Avalanche quorum behavior, or mainnet readiness.

`evidence.json` contains the native wallet/relay gate. `chronik-evidence.json`
contains HTTP requests/responses, coherent snapshot checks, lifecycle assertions,
and the native evidence digest. The native evidence records daemon, wallet,
compiler, manifest and harness digests plus exact caller source pins. Raw native
JSONL output and request logs remain in the same fresh directory. Preserve failed
runs as evidence; use another fresh directory for subsequent attempts.
