# Private V2 operator runbook

This is a preparation guide for explicitly approved private hosts; it deploys
nothing. Current native source is `63c51499441ded6d0fe34d87ff43d53a14b1398f`.
The earlier c0ddb wallet/explorer lifecycle remains
[recorded evidence](v2-explorer-live-acceptance-20261015.md). The independent
controller-session gate passed at operator `f5a72c4c` / native `e775de1363`;
its [reviewed evidence](v2-operator-workflow-acceptance.md) is archived. Neither result establishes separate-host
operation or finality. Current controller implementation includes `80da829b`
and `f2abf45a`; the [workflow contract](../../docs/plans/lotus-v2-operator-workflow.md)
describes the implemented public commands and their limits.

Version numbers describe different objects: controller config and native network
JSON use schema 1; resumable controller session metadata and the fixture manifest
use schema 2; explorer storage uses schema 3 and `/v2/explorer/v1` uses API version 1.

## 1. Freeze source, build and distribute one identity

Use monorepo `b96abff9` for this recipe. Its 308 V2 mailboxes (`000`–`307`)
reproduce native 63c514's source tree `b148281abc3b8a7b599182219835bfc41e2b7ba8`,
checked in [replay evidence](evidence/v2-series-replay-307.json). Install the upstream
platform build dependencies first; see the native clone's `doc/build-*.md`.
Choose unused absolute paths and an installed Python 3.10–3.13:

```sh
MONOREPO="$PWD"
NATIVE=/absolute/new/native-clone
PYTHON=/absolute/path/to/python3.13
test ! -e "$NATIVE" && test ! -L "$NATIVE" || exit 1
git clone https://github.com/Bitcoin-ABC/bitcoin-abc.git "$NATIVE"
git -C "$NATIVE" checkout --detach 1fb7db17c176cdea8a2c60d887891589382ee4e3
while IFS= read -r patch; do
  case "$patch" in ''|'#'*) continue ;; esac
  git -C "$NATIVE" am --keep-non-patch "$MONOREPO/daemon/patches/v2/$patch" || exit 1
done < "$MONOREPO/daemon/patches/v2/series"
test "$(git -C "$NATIVE" rev-parse HEAD^{tree})" = b148281abc3b8a7b599182219835bfc41e2b7ba8 || exit 1
cmake -S "$NATIVE" -B "$NATIVE/build" -G Ninja \
  -DCMAKE_BUILD_TYPE=Debug -DBUILD_CHRONIK=ON -DRust_TOOLCHAIN=1.93.0 \
  -DBUILD_WALLET=ON -DBUILD_QT=OFF -DBUILD_SEEDER=OFF -DBUILD_ZMQ=OFF \
  -DPython_EXECUTABLE="$PYTHON"
cmake --build "$NATIVE/build" --target lotusd lotus-v2-wallet-client -j2
(cd tools/lotus-v2-compiler && npm ci --ignore-scripts && npm run build)
(cd explorer/v2 && npm ci --ignore-scripts && npm run build)
```

Chronik requires Rust, libclang and the Python/PyO3 build dependencies; on macOS
set `LIBCLANG_PATH` and `PYO3_PYTHON` to the installed tools as in the
[native build audit](v2-abc-unit-audit.md). Keep the native clone's real `.git`.
Record SHA256 for each rebuilt executable; binary hashes depend on the build.
The reviewed latest Debug Chronik daemon build has SHA256
`7d86468e24d457eaf2bbac541cc33ddd422e8a481fee96c8e5b6c07e70de7d0e`;
its [peer repair/build provenance](lotus-v2-implementation-plan.md#reviewed-peer-lifecycle-repair-through-307-october-15)
is distinct from the older c0ddb explorer and e775 operator runtime gates.
Do not label those gates rerun on 63c514. Record the wallet/compiler/frontend
hashes alongside the selected daemon; the earlier exact artifact pins remain in
the linked acceptance records. The integrated frontend contains reviewed
request code `40c3191a`.

Distribute the **same bytes** of
[`local-test-manifest.json`](../../tools/lotus-v2-devnet/fixtures/local-test-manifest.json)
and its [provenance](../../tools/lotus-v2-devnet/fixtures/provenance.json).
This easy-PoW schema-2 fixture is only for isolated testing, with no real funds.
Do not substitute the separately proposed development profile. Expected values:

| Fact | Exact value |
| --- | --- |
| Manifest SHA256 | `0ccb2872198a354e9cdc5e9c91d1816cf65bf8109efc200d86537d65dc660d05` |
| Chain ID | `6ff87f5f041a6e4e16018ac58b33f7397d956da5712642015edf5fc560deb9c9` |
| Genesis ID | `53e6c3d9bf12bc18f84e818349da5e5d3d11ee6e33576dab3b81be0a7a978959` |
| Validator profile | `1415adf3bc8c1f4d868ddb65aebb8e50205cb07e18d2feef006d4dfca4ecb39b` |

To reproduce it offline, install the pinned reference dependencies from
`tools/lotus-v2-reference/requirements-vm.txt`, then run:

```sh
PYTHONPATH=tools/lotus-v2-reference "$PYTHON" \
  tools/lotus-v2-devnet/fixtures/reproduce_absolute_fixture.py
```

## 2. Run the supported local A → B → C wallet flow

Use [offline preparation](../../tools/lotus-v2-devnet/SETUP.md#prepare-complete-inputs-offline)
with the binaries built above, an absolute Node.js 22+ executable, and fresh
`--output`/`--session` directories. `prepare-local.py` emits two local nodes.
Before launch, edit its new `config.json` to contain three entries using the
same generated pinned `network` object:

```json
[
  {"name":"a","home":"nodes/a","network":{"path":"network.json","sha256":"<generated network SHA256>"},"connect_to":[]},
  {"name":"b","home":"nodes/b","network":{"path":"network.json","sha256":"<same SHA256>"},"connect_to":["a"]},
  {"name":"c","home":"nodes/c","network":{"path":"network.json","sha256":"<same SHA256>"},"connect_to":["b"]}
]
```

Keep the remaining generated fields. Validate before starting:

```sh
python3 tools/lotus-v2-devnet/devnet.py --config /absolute/inputs/config.json \
  --session /absolute/new-session --check
python3 tools/lotus-v2-devnet/devnet.py --config /absolute/inputs/config.json \
  --session /absolute/new-session
```

Enter these real controller commands; passphrases are prompted locally:

```text
wallet create alice --node a
wallet create bob --node c
wallet create miner --node c
fund alice --claim 100000 --time now --batches 16
mature alice --max-blocks 3 --claim 100000 --time now --batches 16
wallet prepare alice --to bob --amount 10000 --fee 1000
pay alice --to bob --amount 10000 --fee 1000 --mine-to miner --claim 100000 --time now --batches 16
wallet status alice <returned TxID>
wallet reconcile bob
status
stop
```

Proceed to payment only after maturity completes. Amounts are integer atoms;
claims are ceilings, and fees/time/nonce budgets can be refused. `pay` submits
through A's private wallet FD, waits for C to report the relayed transaction,
and asks C to mine its actual pool. The mining request contains no payment wire.
A retained candidate is pending until native acceptance. Full command/recovery
semantics are in the [controller guide](../../tools/lotus-v2-devnet/README.md).

## 3. Separate-host P2P and local explorer preparation

Operators must first supply approved private numeric addresses, reachable ports
and access rules. No host addresses are allocated here. Use A with no upstream,
B connecting to A, C connecting to B. On each host create a fresh private run
directory, copy the identical manifest, and write this pinned native network
file with the placeholders replaced by approved values:

```json
{"schema":1,"magic":"31435769","listen":{"address":"<local private numeric IP>","port":48001},"connect":[],"receive_limit":2097152,"local_policy":"bounded-local-v1","chronik_bind":"127.0.0.1:18331"}
```

`31435769` is the existing dispatcher fixture magic, not a network allocation.
Port 48001 is an explicit example nonproduction P2P choice; verify it is free on
each host. B/C replace `connect:[]` with one
`{"address":"<upstream private numeric IP>","port":48001}` entry. Use no
10604, 10605 or 8331 endpoint. Keep Chronik and the explorer on loopback; permit
P2P only between the approved hosts. Maintain synchronized host clocks.

Give each host a controller config containing only its local node (`a`, `b` or
`c`), a relative home beneath its own session, the hash/path of this network
file, and `connect_to:[]`. Keep explicit remote upstreams in the network's
`connect` field. Recompute the network SHA256 after editing. Add that local
node's discovery binding:

```json
"chronik":{"url":"http://127.0.0.1:18331","chain_id":"<Chain ID above>","profile_id":"<Validator profile above>"}
```

Replace both identity placeholders with the exact table values. The controller
now accepts `chronik_bind` and optional native `avalanche` configuration and
preserves them in effective network files. Avalanche credentials are null for
an observer or an absolute local file path; `initial_download` requires explicit
uint32 `minimum_height` and positive uint32 `maximum_tip_age_seconds`. Select
those values and a funded profile through the separate Avalanche gate; enabling
it is not a quorum claim. Configuration cannot be changed during resume.

Run the same `devnet.py --config ... --session ... --check` and launch commands
from section 2 on each host, in A/B/C order. Each controller owns only local
children. Use `status a`, `status b`, `status c` at their respective prompts;
compare identity, tip/roots, recovery flags and active peers. The A/B/C counts
are 1/2/1 after links activate. `inspect` also returns native status.

From another terminal on that host:

```sh
curl --fail http://127.0.0.1:18331/v2/explorer/v1/status
cd /absolute/lotus/explorer/v2
node server.mjs --port 0 --api http://127.0.0.1:18331
```

Open the printed loopback URL on that host. For an operator workstation, use an
explicit SSH loopback forward managed by the operator; the UI proxy accepts
loopback API origins. Explorer ready requires complete schema-3 catchup in the
separate `chronik-v2-explorer-v1` directory. Check its chain/profile/anchor before
viewing blocks, TxID/TxHash, outpoints and branches. A 404 is covered-history
absence; pending membership and finality are unavailable.

## 4. Public recipients, independent mining and clean resume

At C's controller, create the recipient and independent mining wallet:

```text
wallet create bob --node c
wallet create miner --node c
recipient export bob --output /absolute/new/bob-recipient.json
```

Copy only the public descriptor to A using an operator-managed channel and
verify its returned SHA256 with Bob out of band. Export refuses overwrite;
import checks chain/genesis/profile and recompiles the public Payment root.
At A's controller:

```text
wallet create alice --node a
recipient import bob-remote --file /absolute/received/bob-recipient.json
fund alice --claim 100000 --time now --batches 16
mature alice --max-blocks 3 --claim 100000 --time now --batches 16
wallet prepare alice --to-recipient bob-remote --amount 10000 --fee 1000
wallet pay alice --to-recipient bob-remote --amount 10000 --fee 1000
wallet status alice <returned TxID>
```

`wallet pay` persists/submits through A's local private FD and performs no mining.
Accepted submission or pending status is not confirmation. B relays to C over
P2P. C's operator independently runs:

```text
mine 1 --to miner --claim 100000 --time now --batches 16
wallet reconcile bob
```

A checks `wallet status alice TXID`.
Verify the exact TxID in the accepted block/explorer; an empty pool selection
proves no payment inclusion. `--to` still targets local wallets, and top-level
`pay --mine-to` remains the local combined convenience command. No remote child
control or mining orchestration is added.

For an orderly restart, enter `stop`, wait for owned children to exit, then run:

```sh
python3 tools/lotus-v2-devnet/devnet.py --config /absolute/inputs/config.json \
  --session /absolute/existing-session --resume --check
python3 tools/lotus-v2-devnet/devnet.py --config /absolute/inputs/config.json \
  --session /absolute/existing-session --resume
```

Resume accepts only new-format schema-2 sessions marked cleanly `stopped`.
It restores recorded wallet bindings/imports and requires unchanged config,
identity, executable/compiler/Node pins and managed paths. Old sessions,
unclean/partial startup, live locks, missing homes and pin drift are refused;
there is no attach/reset/adopt command. After resume, reconcile wallets, verify
persisted tip/roots, and require explorer old tokens/cursors to return 409 with
its new epoch. Preserve failed homes/logs; copy homes only after shutdown.

The proven conflicting-chain/re-mining flow remains the isolated
[`check-v2-explorer-live.py`](../tests/check-v2-explorer-live.py) gate in its
[acceptance record](v2-explorer-live-acceptance-20261015.md): a competing native
wallet spend on a stopped snapshot produces confirmation → detached/pending →
re-mined at heights 5/7/8. The newer operator gate covers independent sessions
and clean resume on one host. There is no interactive fork command; separate-host
reorg and actual Avalanche finality remain acceptance work.

Wallet keys/passphrases stay in each host's native encrypted wallet/private FD channel,
never HTTP, argv or environment. On unknown signing outcome, inspect `wallet
pending`, `wallet export`, `wallet status`, then explicitly `wallet broadcast`
the persisted transaction; do not issue another payment as recovery.

For trouble: compare manifest/binary/network hashes first; check numeric peers,
reachability and clocks; wait for native recovery/maturity before retrying public
reads. Sustained 503 requires native/index diagnostics, while 409 starts a new
observation. Schema mismatch requires preserving the old index and reviewing a
separate replay directory. See [Avalanche bootstrap scope](v2-quorum-bootstrap-test.md)
for its distinct funded profile and gates. This runbook changes no consensus
parameters and makes no separate-host, Avalanche quorum or deployment claim.
