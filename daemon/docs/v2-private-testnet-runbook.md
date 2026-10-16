# Private V2 operator runbook

This is a preparation guide for explicitly approved private hosts. No remote
infrastructure is selected or deployed. Local three-node funding, wallet relay,
Chronik and explorer restart/reorg flows passed on native
`c0ddb9cf307a97a43309b72cffef383c29e559e8`; see
[the exact runtime evidence](v2-explorer-live-acceptance-20261015.md).
Separate-host operation and a funded Avalanche quorum remain separate gates.
The current controller has operator gaps listed below; a complete remote wallet
walkthrough cannot yet be performed with its public commands.

## 1. Freeze source, build and distribute one identity

Use monorepo `45faac3d` for this recipe. Its 306 V2 mailboxes reproduce native
c0ddb's source tree `2f8ada7e076b9c4e529bc8348834823785029fcd`, checked in
[replay evidence](evidence/v2-series-replay-305.json). Install the upstream
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
test "$(git -C "$NATIVE" rev-parse HEAD^{tree})" = 2f8ada7e076b9c4e529bc8348834823785029fcd || exit 1
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
Record SHA256 for each rebuilt executable; rebuilding does not reproduce a
platform-independent binary hash. The passing local artifacts were daemon
`5c05a1acf36a91c690505ca08bd291d9fd2e985fd483f9db08386c712c1f8bfa`
and the separately pinned wallet client
`080c39f2b71e0180933d216e7ef2b06dd32eccc9d83720cae34b2e61e4df50ff`
(source `1ab203f0c53ea4e620fac80ac6781e6176fa3fac`). Its production wallet source
is unchanged in c0ddb; a newly built wallet still needs its own hash/evidence.
The integrated frontend contains reviewed request code `40c3191a`.

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
directory, copy the identical manifest, and write this **raw native** network
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

Launch the raw native owner in a terminal whose stdin stays open:

```sh
/absolute/lotusd -lotusv2node /absolute/manifest.json /absolute/new-home /absolute/network.json
```

Its stdin/stdout is local JSONL. Send
`{"id":"operator-status-1","command":"status"}` and compare all three profile
identities, authoritative tip/roots, recovery flags and `peer_active` across
hosts. Expect A/B/C active peer counts 1/2/1 only after all links activate.
The ready event reports the actual `chronik_address`.

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

## 4. Persistence, reorg and operator limits

For a raw native node, send `{"id":"operator-stop-1","command":"stop"}`,
wait for its process to exit, then repeat its exact launch command with the same
home/manifest/network. Require the persisted tip/roots and bindings to agree;
explorer epoch must change and old tokens/cursors must return 409. Preserve
failed homes and logs. Copy a home only after clean shutdown.

The proven conflicting-chain/re-mining workflow is the isolated
[`check-v2-explorer-live.py`](../tests/check-v2-explorer-live.py) gate described in
[its acceptance record](v2-explorer-live-acceptance-20261015.md). It creates a
competing native wallet spend on a stopped-home snapshot, mines a heavier chain,
and checks confirmation → detached/pending → re-mined at heights 5/7/8. There is
no public interactive controller fork/reorg command.

Current tooling gaps, verified against this checkout:

- Controller sessions always require a new directory; no resume/attach command
  exists. Its `stop` preserves wallets/homes but cannot reopen them interactively.
- `--to` resolves a wallet in the same local controller. Public remote-recipient
  export/import and cross-host recipient payment commands are absent.
- The controller launches only local child nodes. A remote C cannot be selected
  by its `--mine-to`; remote operator coordination is required.
- The controller's exact network validator rejects native `chronik_bind` and
  `avalanche` fields. Raw native launch supports them; the tested live discovery
  harness used an adapter. Interactive controller-owned wallet + HTTP startup
  therefore still needs tooling work.

Keys/passphrases stay in each host's native encrypted wallet/private FD channel,
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
