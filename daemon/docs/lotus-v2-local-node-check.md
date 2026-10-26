# Two-process local development-node check

`daemon/tests/check-v2-local-nodes.py` exercises two actual
`lotusd -lotusv2node MANIFEST HOME NETWORK.json` processes. It requires an explicitly
approved binary hash and full source pins, a supplied development manifest and an
independent reference block corpus. It creates fresh isolated homes, binds only
`127.0.0.1:0`, reads the actual ephemeral endpoint and connects the second process
to the first. It never binds Lotus production/default ports or opens live data.

The checks distinguish pending body retention from validation. Native status is
the authority for block ID, height, UTXO root, state root and exact monetary bytes;
all must match caller-supplied reference expectations. ChainID/genesis/profile
identity must agree throughout. The second process synchronizes earlier full
blocks, restarts into its exact persisted tip, then receives newer blocks through
the real socket path. Invalid-body checks require the runtime's deterministic
invalid ledger and exact causal root; unchanged state by itself is inconclusive.

Coin/proof commands run at stationary initial/final tips in both processes.
Membership and empty/other-leaf nonmembership encodings are checked, and both
stores must return identical coin/proof data at the expected authoritative root.
A query may also carry an independent exact `expected` result; without it the
proof gate is cross-store agreement, not an independent cryptographic proof
oracle. No acceptance or coin-lookup callbacks are supplied by the Python test.

The network configuration is deliberately explicit:

```json
{"schema":1,"magic":"31435769","listen":{"address":"127.0.0.1","port":0},"connect":[],"receive_limit":2097152,"local_policy":"bounded-local-v1"}
```

The magic shown is the existing dispatcher test fixture magic, not a network allocation. It remains an explicit caller input. The test does not adopt a network
profile. The second/restarted process receives the first process's actual bound
endpoint in `connect`. Standard ports 10604, 10605 and 8331 are refused even if
unexpectedly returned as an ephemeral endpoint.

The input corpus has schema `lotus-v2/local-node-corpus/1`:

```json
{
  "schema":"lotus-v2/local-node-corpus/1",
  "genesis":{"tip":"<64 hex>","height":0,"utxo_root":"<64 hex>","state_root":"<64 hex>","monetary_bytes":"<112 hex>"},
  "initial_height":2,
  "blocks":[
    {"path":"funding.block","tip":"<64 hex>","height":1,"utxo_root":"<64 hex>","state_root":"<64 hex>","monetary_bytes":"<112 hex>"},
    {"path":"maturity-2.block","tip":"<64 hex>","height":2,"utxo_root":"<64 hex>","state_root":"<64 hex>","monetary_bytes":"<112 hex>"},
    {"path":"signed-spend.block","tip":"<64 hex>","height":3,"utxo_root":"<64 hex>","state_root":"<64 hex>","monetary_bytes":"<112 hex>"}
  ],
  "invalid":{"path":"bad-signature.block","block_id":"<64 hex>","invalid_root":"<64 hex>"},
  "queries":[
    {"stage":"initial","txid":"<funding TxId>","index":0},
    {"stage":"final","txid":"<funding TxId>","index":0}
  ]
}
```

Paths resolve relative to the corpus file. Expected values must come from the
existing independent reference run, not this test's native output. Every initial
and final stage needs explicit queries. `expected`, when supplied on a query,
is `{ "coin": "<CoinEntry hex or null>", "proof": {"presence":0,"coin":null,"bitmap":"<64 hex>","siblings":[]} }`
with the actual expected presence/frames/path. Preserve previous failed corpora;
do not regenerate expectations to erase disagreements.

Once root has approved the built native command, run explicitly with Python 3.11 or newer:

```sh
python3 daemon/tests/check-v2-local-nodes.py \
  --daemon /path/to/reviewed/lotusd \
  --daemon-source <full-native-commit> \
  --expected-daemon-sha256 <approved-binary-sha256> \
  --build-command 'exact configure/build command' \
  --manifest /path/to/explicit-manifest.json \
  --corpus /path/to/reference-corpus.json \
  --corpus-source <full-reference-compiler-commit> \
  --network-magic <explicit-8-hex-magic> --receive-limit 2097152 \
  --output /tmp/new-two-node-run
```

The output directory must be new. Raw stdout/stderr JSONL, all stdin commands,
network profiles, exact process commands/PIDs, binary/input hashes, authoritative
responses, checks and failures are retained beside both homes. Waits have an
explicit 1–120 second per-stage bound. Cleanup addresses only the exact child
handles: stop, bounded wait, terminate, then kill if needed; no process-name or
port-wide cleanup is used.

Transport counters record full/compact requests and fallbacks. Initial sync must
show a full-block request. Later compact request evidence is labelled attempted;
request counts alone do not prove compact reconstruction. A zero compact delta
is explicitly not demonstrated. Compact-retained counters are recorded separately;
retained bytes plus independently expected authoritative tip/root/money establish
the combined propagation gate, while retention alone never establishes acceptance. This canned block corpus does not establish a
usable testnet, a native block assembler/miner, wallet usability, or public P2P
compatibility. Native-mined blocks and interactive signed payments remain later
gates. Source preparation and Python syntax checks alone are not runtime evidence.

The default `--relay-delay 0.05` adds a transparent loopback TCP relay between
the two native nodes. It forwards actual bytes unchanged and synthesizes no
messages or validation results. Delaying each chunk forces requests/responses
to remain in flight across multiple native event-loop turns, covering duplicate
live-job rescheduling/peer-disconnection regressions. The relay permits four
connections, keeps at most one 16KiB chunk pending per direction, applies TCP
backpressure instead of unbounded queues, and bounds blocked writes at two
seconds. Its exact sockets/threads are closed and joined during cleanup.
Connection/chunk counts, forwarded bytes, delays, stream hashes and errors are
retained in `relay.jsonl` and run evidence. `--relay-delay 0` explicitly disables
this regression gate. Full sync, restarted-peer activation and final coin/proof
queries also require the real native peer to remain active.

For the preserved native-wallet pilot corpus, an initial height of two followed
by height three supplies both cold full synchronization and a newer compact
candidate. Expected coin frames may be supplied separately as `expected_coin`
(including null for a spent outpoint), while exact proof expectations remain
optional. Derivation can replay existing independently accepted reference blocks
and compare them with their earlier recorded expectations; it must never replace
those expectations on disagreement. Root's preserved derivation artifact is
`/private/tmp/lotus-v2-local-node-reference-corpus-20261015.json`, backed by
`/private/tmp/lotus-v2-local-node-corpus-derive-20261015.py`. No native node was
launched during that derivation.

## Observed isolated execution

Root approved native source pin
`cecfdc1ed69c60c72ad5457a0f99c88e8b1e8a01`, binary
`/private/tmp/lotus-v2-daemon-runtime-staging-20261015/build/src/lotusd`, SHA256
`167cfe2538a9fccfd7cf3e29a70b769a34ae930c349b62772dec9862058bf1f6`.
The recorded build command is `cmake --build build --target lotusd check-lotus-v2-peer-dispatcher -j 6`
in that clone; build log is `/private/tmp/lotus-v2-node-command-full-build.log`.
The independent reference derivation used monorepo commit
`58b72d8c7ee40abfed460fc3e41fde3f5a00cf1d` and the preserved native-wallet pilot
blocks. No expected state or corpus bytes changed after native execution.

The first actual run passed at
`/private/tmp/lotus-v2-two-real-nodes-first-20261015`. Its first matching sync
snapshot still had a pending journal, so checkpoint waits were strengthened to
require `tip_known=true` and false reopen/paused/journal/receipt/propagation flags.
The fresh run at `/private/tmp/lotus-v2-two-real-nodes-quiescent-20261015` passed
with those stricter checkpoints. The earlier evidence remains intact.

Observed: two full-block requests/retained bodies synchronized node B to height
two; its persisted restart restored the same roots and monetary bytes. The
bad-signature sibling obtained its exact deterministic-invalid causal root and
was never connected. One newer compact request/retained body, with zero full
requests/fallbacks, brought both stores to the independent expected height-three
tip, roots and money. Membership, spent-outpoint OtherLeaf nonmembership, and new
output membership proofs agreed across stores; all queried coin frames matched
independent supplied expectations. The 50ms relay forwarded 38 actual chunks /
4740 bytes over two connections. All three process starts (including B restart)
exited zero, with no cleanup errors or remaining child handles.

These observations demonstrate local socket synchronization and persistence for
this exact supplied corpus/profile/binary. They do not establish native mining,
a usable testnet, arbitrary transaction acceptance, or public-network readiness.
