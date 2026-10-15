# Native encrypted SQLite wallet chain pilot

This pilot connects the compiler's existing Payment artifact to a fresh native
wallet key and actual authenticated development-chain storage. It reuses the
complete-block reference/daemon harness with explicit deferred signing. It does
not import, print or sign with a synthetic/public fixture private key.

The native helper receives an explicit manifest, chain home and separate wallet
home. `create` generates/encrypts its key and returns only an x-only public key.
`compile.mjs` compiles the existing Payment source for that public key; `register`
checks its exact script/proof and returned policy root. After the full daemon
accepts funding, `track` authenticates the real outpoint from chain storage.
The first `sign` must explicitly reject immature funding. Only after actual
maturity blocks have been accepted does a second `sign` prepare/sign/reserve and
export full transaction bytes through native wallet APIs. The helper receives
recipient and fee, never caller-supplied signing digests or resolved-coin claims.

The exported full bytes pass independent Python transaction decoding/IDs,
complete-block acceptance, and real offline `lotusd` acceptance. Seven charges
and all exposed roots must agree. The existing harness mutates only a signature
byte, re-mines its block, requires the intended CHECKSIGVERIFY rejection, and
checks restart, undo and reconnect. These are complete offline command checks;
they do not establish public-network or wallet RPC integration.

Build the compiler first (`npm ci --ignore-scripts && npm run build` inside its
directory). From the repository root, supply reviewed native binaries and the
explicit provisional manifest:

```sh
PYTHONPATH=tools/lotus-v2-reference \
/private/tmp/lotus-v2-compiler-review-venv/bin/python \
  tools/lotus-v2-compiler/test/wallet-chain-pilot/run.py \
  --manifest /path/to/explicit-command-manifest.json \
  --daemon /path/to/lotusd --daemon-source 'exact reviewed source/build' \
  --wallet-helper /path/to/lotus-v2-wallet-pilot \
  --wallet-source 'exact reviewed native wallet source/build' \
  --output /tmp/new-native-wallet-chain-run
```

Output must be new. A random temporary passphrase file is created with mode
0600, passed only by path to the native helper, and removed on success/failure.
Requests/passphrase contents are not logged. Encrypted SQLite wallet artifacts,
compiled source/artifact, exact blocks and signed full bytes, public IDs,
subprocess results, roots and charges remain for review. No expected outcomes
are regenerated. New keys intentionally make separate runs different; retained
bytes provide replay evidence for each exact run. Only generated isolated
wallet/data directories are used; no sockets, ports or live wallets are opened.

The native helper protocol is `HELPER MANIFEST CHAIN_HOME WALLET_HOME OPERATION`
with JSON stdin. Operations: create `{passphrase_file}`, register `{script,proof}`,
track `{prev_txid,prev_index}`, sign `{passphrase_file,recipient,fee}` and reconcile.
Sign success returns `{wire,txid,txhash,digest}`. Immature failure must explicitly
identify insufficient mature funds; arbitrary process errors do not satisfy it.
The shared API's `immature` compiler callback records this native rejection and
fails closed if probe evidence is missing. The default public-fixture pilot
retains its separate early-sign/immature-block negative.

Run the optional real integration test with `LOTUS_V2_PILOT_MANIFEST`,
`LOTUS_V2_PILOT_DAEMON`, and `LOTUS_V2_WALLET_HELPER` set, using
`test/wallet-chain-pilot/test_wallet_pilot.py`. The always-available import test
checks that importing orchestration creates no wallet and launches no process.

Before signing, the native `stale` probe prepares against the mature tip,
disconnects that actual tip through the development-chain API, then requires
SignAndReserve to return Stale without exported bytes or a new reservation.
The wrapper checks the changed store tip, reconnects the exact retained maturity
block and verifies original roots before obtaining the valid wallet signature.
After full-block acceptance and the shared harness's independent undo/reconnect,
the wrapper repeats a real daemon undo and reopens the wallet: funding must
reappear as mature while its local export reservation remains set. Reconnecting
the exact signed block must remove that active coin again. Reservations do not
imply confirmation and undo does not revoke previously exported bytes.

The helper `stale` request includes recipient, fee, passphrase_file and
expected_tip. A stale response must identify the disconnected tip/predecessor,
return the explicit Stale result and include no wire. `reconcile` returns the
actual tip/height and explicit tracked-coin present/reserved/mature/value fields;
it never infers confirmation merely from retained historical block bodies.

Build identity matters: helper headers and linked validation libraries must come
from the same reviewed native source as the daemon. A retained initial mixed
build (new DiskStateOptions header with older libraries) failed before wallet
creation with `invalid storage limits` at
`/private/tmp/lotus-v2-wallet-chain-first`. That is an infrastructure failure,
not a transaction rejection or evidence to change the manifest. The failed
fixture and evidence remain intact. Use a new output path with matching sources.

Observed 2026-10-15 with the supplied explicit manifest: matching indexed daemon
`97b78c684` and the native wallet draft linked against that exact checkout passed
the full pilot. Retained evidence:
`/private/tmp/lotus-v2-wallet-chain-matching97`. The accepted mature Payment had
account/enforce cost 279912, invocation cost 50181, fees 1000, subsidy 1999998,
required underclaim 243 and actual underclaim 1900498; independent Python and
the daemon agreed on every field. Both integration/import tests passed without
skips. Native helper source remains a separate candidate owned by the wallet
packet; this compiler packet does not claim an exact wallet commit or published
wallet binary. The helper binary digest is retained in wallet evidence.

For that explicit integration test invocation:

```sh
PYTHONPATH=tools/lotus-v2-reference \
LOTUS_V2_PILOT_MANIFEST=/path/to/manifest.json \
LOTUS_V2_PILOT_DAEMON=/path/to/matching/lotusd \
LOTUS_V2_WALLET_HELPER=/path/to/matching/lotus-v2-wallet-pilot \
/private/tmp/lotus-v2-compiler-review-venv/bin/python \
  tools/lotus-v2-compiler/test/wallet-chain-pilot/test_wallet_pilot.py
```

This is a fresh single-key, single-policy native Payment gate. General coin
selection, multiple policies, address encoding, backup recovery, wallet RPC,
broadcast and automatic chain scanning are outside it. The transient test
passphrase is intentionally removed, so retained encrypted wallet files are
inspection artifacts; full block bytes remain independently replayable.
