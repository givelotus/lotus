# Prepare an isolated local session

This packages an **existing tested local fixture**, not a public network profile.
Its easy proof of work, monetary parameters and magic are for isolated tests.
Do not expose its listeners, allocate public ports, or use real funds. Setup runs
no daemon, wallet client, Node process or compiler and creates no chain homes.
Python 3.10+ is sufficient for the controller and setup script.

## Build native programs in a fresh standalone clone

Install the platform dependencies described by the upstream ABC
`doc/build-*.md` files (CMake, Ninja, a C++ compiler and wallet dependencies).
Use Python 3.10–3.13 explicitly for the native configuration. Keep this clone
separate from any existing workspace, node or data directory. A real `.git`
directory is required by the upstream build; do not use a linked worktree.

From this monorepo, set absolute paths for an **unused** native source directory
and an installed Python interpreter, then run:

```sh
(
set -eu
MONOREPO="$PWD"
NATIVE=/absolute/unused/lotus-v2-native
PYTHON=/absolute/path/to/python3.13
if [ -e "$NATIVE" ] || [ -L "$NATIVE" ]; then
  echo "Native destination already exists: $NATIVE" >&2
  exit 1
fi
git clone https://github.com/Bitcoin-ABC/bitcoin-abc.git "$NATIVE"
git -C "$NATIVE" checkout --detach 1fb7db17c176cdea8a2c60d887891589382ee4e3
while IFS= read -r patch; do
  case "$patch" in ''|'#'*) continue ;; esac
  git -C "$NATIVE" am --keep-non-patch "$MONOREPO/daemon/patches/v2/$patch" || exit 1
done < "$MONOREPO/daemon/patches/v2/series"
cmake -S "$NATIVE" -B "$NATIVE/build" -G Ninja \
  -DCMAKE_BUILD_TYPE=Debug -DBUILD_CHRONIK=OFF \
  -DBUILD_QT=OFF -DBUILD_SEEDER=OFF -DBUILD_ZMQ=OFF \
  -DPython_EXECUTABLE="$PYTHON"
cmake --build "$NATIVE/build" --target lotusd lotus-v2-wallet-client -j 6
)
```

Stop if patch application fails; preserve that clone and its diagnostics.
The checked-in 173-entry series through mailboxes 171–172 includes the private
FD wallet client and its build target. Use the complete series, not a V1 build
or the earlier indexed-store wallet pilot. The executable paths are
`$NATIVE/build/src/lotusd` and
`$NATIVE/build/src/wallet/lotus-v2-wallet-client`. This recipe uses no setup/reset
wrapper and does not touch existing daemon workspaces. Debug/Chronik OFF is the
validated local native build configuration; hashes identify each user's build.

Build the compiler in this checkout with the Node version supported by its
package:

```sh
cd tools/lotus-v2-compiler
npm ci --ignore-scripts
npm run build
cd ../..
```

## Prepare complete inputs offline

Choose two separate paths beneath an existing parent. Neither the output nor
session directory may already exist. Supply actual executable paths, including
Node; setup does not search PATH or download programs.

```sh
python3 tools/lotus-v2-devnet/prepare-local.py \
  --daemon /absolute/lotus-v2-native/build/src/lotusd \
  --wallet-client /absolute/lotus-v2-native/build/src/wallet/lotus-v2-wallet-client \
  --compiler /absolute/lotus/tools/lotus-v2-compiler \
  --node /absolute/path/to/node \
  --output /absolute/existing-parent/local-inputs \
  --session /absolute/existing-parent/new-session
python3 tools/lotus-v2-devnet/devnet.py \
  --config /absolute/existing-parent/local-inputs/config.json \
  --session /absolute/existing-parent/new-session --check
```

`--check` validates the controller configuration and native/fixture hashes
without starting processes or creating the session. Setup checks files and
permissions only; it does not prove that arbitrary supplied binaries implement
the required interfaces. The native series and controller tests establish that
separately. Preserve the generated inputs alongside runtime evidence.

The output contains complete `config.json`, exact copied `manifest.json` and
`network.json`, `provenance.json`, and shell-quoted `commands.txt`. The manifest
SHA256 is `33d84853403b2eaa686a5ad4fdd799daffc8fc9c712b0f8662d914a29f11d720`.
Fixture provenance is checked in under `fixtures/`; no historical `/tmp`
artifact is needed. Network magic `31435769` is the dispatcher test fixture,
with only `127.0.0.1:0`, empty initial peers and receive limit 2097152. Node `b`
connects to node `a` through the controller's resolved ephemeral endpoint.

Operational ceilings are written explicitly: 60000 ms per deadline, 8388608
bytes per node line, 4194304 wallet bytes, 256 queued events, 256 blocks and
4096 mining batches. These controller bounds do not change consensus rules.
The controller checks daemon/client/manifest/network hashes at load time.
Provenance also records Node and the compiler entry/source hashes for auditing;
these additional hashes are not enforced by the current controller schema and
do not cover every compiler dependency. Do not modify the compiler or tools
between preparation and a session.

## Start separately

After reviewing the inputs, run the second command in generated `commands.txt`
(the command without `--check`). It creates the fresh session and starts the
isolated processes. See [README.md](README.md) for interactive commands and
wallet passphrase handling. The setup packet itself performs only offline
validation; it makes no claim of public deployment readiness.

Run the setup path-safety regressions offline with:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
  -s tools/lotus-v2-devnet/fixtures -v
```

These use temporary inert executable files and check path aliases, fresh output
and session preservation; no native binary is invoked.


## Tested two-wallet walkthrough

With the bundled fixture and a fresh session, enter these commands at the
controller prompt. Choose wallet passphrases when prompted; the commands contain
only public inputs. Node names `a` and `b` come from `prepare-local.py`.

```text
wallet create alice --node a
wallet create bob --node b
fund alice --claim 100000 --time 1792022640 --batches 16
mature alice --max-blocks 3 --claim 100000 --time 1792022760 --batches 16
pay alice --to bob --amount 10000 --fee 1000 --mine-to alice --claim 100000 --time 1792022880 --batches 16
wallet reconcile bob
status
stop
```

The explicit timestamps belong to the checked-in local fixture. The amounts are
atoms, and `claim` is a requested ceiling subject to native validation. This
sequence produces funding, maturity and payment blocks; the recipient receives
10000 atoms and the funding input returns 89000 atoms as change. A fee of 100 was
rejected as below the transaction byte floor during validation; 1000 passed.
Native wallet keys and signatures are newly generated, so your transaction IDs,
roots and nonces will differ from recorded evidence. Later operations must use
eligible timestamps and sufficient fees; they do not inherit this sequence's
particular monetary results. See the README for explicit recovery if signing
has an unknown outcome.
