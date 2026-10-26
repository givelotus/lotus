# Actual native controller discovery acceptance

`daemon/tests/check-v2-wallet-discovery-live.py` exercises the integrated controller against three actual private V2 native nodes, their actual Chronik HTTP listeners, and independently encrypted SQLite sender/recipient wallets. It derives the lifecycle from `check-v2-private-relay.py` and reuses the bounded JSONL process transport in `check-v2-local-nodes.py`; existing harnesses are unchanged.

The controller's public `wallet balance`, `wallet prepare`, and `wallet pay` commands execute unchanged. A small adapter connects its native process request interface to the existing node transport. Wallet creation/registration and status/rebroadcast use the controller's actual `WalletProcess` private FD bridge. The harness supplies node-specific ready-event chain/profile identities directly as trusted bindings. It creates fresh controller objects around persistent native wallet homes; it does not test configuration parsing, interactive passphrase input, or controller-owned node launch.

Funding is externally mined on B to A's compiled Payment root. A receives no caller-supplied funding outpoint: actual confirmed HTTP discovery supplies candidate outpoints and native tracking authenticates ownership. Later block rewards use a distinct unrelated root. The workflow discovers two mature 100,000-unit coins, prepares and submits two independent 10,000-unit payments with 1,000-unit fees, observes relay across A–B–C, restarts nodes, checks persisted exact signed bytes, and confirms from C's native pool. Recipient discovery authenticates both receipts. A longer competing fork confirms a conflicting 11,000-unit payment, detaches the original confirmations, and re-mines the surviving original payment. Native sender/recipient presence, reservations, maturity and balances are checked after each transition. Discovery also finds the competing transaction's 88,000-unit change and 11,000-unit receipt, which manual outpoint tracking in the older harness did not include.

The authoritative run and compact checkpoint evidence are recorded in `discovery-live-wallet-acceptance.json`. Raw JSONL, full evidence, encrypted wallets and fresh node homes remain in its absolute output path. All native listeners use ephemeral loopback ports; 10604, 10605 and 8331 are refused. The harness has a 180-second overall wall deadline, bounded individual operations and exact child-PID cleanup. Native daemon/wallet hashes are checked before every launch/invocation, and the compiler artifact is checked before compilation.

The Python controller/discovery source includes the bounded backoff fix originally committed as `4cc71cf3`, applied to the reviewed integrated `70b3c27e` source. The daemon and native wallet artifacts deliberately retain separately recorded earlier source pins; this run does not claim an integrated-revision native rebuild. The independent compiler copy was rebuilt from the clean source tree matching `4359d0bf4ef7ad0c1a7779780f099be24c45e008`; its generic artifact reproduces SHA256 `80c96c0f5ce93a5eedc7edfc81dd89bc5d9b8f3759f1447cb02b77b6c1130317`.

Preserved runs `a` and `b` fail during post-reorg discovery because the earlier client retries transient native index fencing immediately. The native loop correctly invalidates HTTP authority while it advances state; the controller fix adds bounded discovery-scan backoff under its existing deadline. Diagnostic run `c` used caller-level safe discovery retries and then caught an inherited balance assertion that excluded automatically discovered competing-payment change; it is not acceptance evidence. Runs `d` and `e` passed the actual lifecycle with the fixed controller, but their caller-supplied compiler-source label was stale; their actual artifact digest is retained and the authoritative run corrects that label. Failed runs remain untouched. The final harness has no caller-level command retry or HTTP readiness barrier.

This validates the private confirmed-discovery wallet lifecycle. Chronik remains confirmed-only, with no pending incoming-output index. It does not establish dishonest-server completeness, Avalanche quorum behavior, production synchronization or release readiness. Production homes, chain data and published assets were untouched.

Reproduce with fresh output and explicitly pinned artifacts:

```sh
python3 daemon/tests/check-v2-wallet-discovery-live.py \
  --daemon /absolute/pinned/lotusd \
  --wallet-client /absolute/pinned/lotus-v2-wallet-client \
  --manifest /absolute/schema2-local-manifest.json \
  --compiler /absolute/pinned-built-compiler \
  --daemon-source FULL_COMMIT --wallet-source FULL_COMMIT \
  --compiler-source FULL_COMMIT --output /tmp/new-discovery-live-run
```
