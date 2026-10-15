# Prepare an isolated local session

This packages the versioned **absolute-tail local test fixture**
`lotus-v2-local-test-20261015-absolute1`, derived from the earlier tested local
fixture. The schema 2 fixture passes native manifest checks and local multi-node wallet,
relay, mining, restart and reorg tests. Those tests do not demonstrate operation
on separate machines.
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
test "$(git -C "$NATIVE" rev-parse HEAD^{tree})" = \
  028e4b47980e6d3e3f52c987b17f2df96f772313
cmake -S "$NATIVE" -B "$NATIVE/build" -G Ninja \
  -DCMAKE_BUILD_TYPE=Debug -DBUILD_CHRONIK=OFF \
  -DBUILD_QT=OFF -DBUILD_SEEDER=OFF -DBUILD_ZMQ=OFF \
  -DPython_EXECUTABLE="$PYTHON"
cmake --build "$NATIVE/build" --target lotusd lotus-v2-wallet-client -j 6
)
```

Stop if patch application fails; preserve that clone and its diagnostics.
The checked-in 219-entry series through mailbox 218 includes the private
FD wallet client, pool-based mining and TCP transaction relay. Every intermediate
source tree is recorded in `daemon/docs/evidence/v2-series-replay-218.json`.
The final tree must be `028e4b47980e6d3e3f52c987b17f2df96f772313`. Use the complete series, not a V1 build
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
SHA256 is `0ccb2872198a354e9cdc5e9c91d1816cf65bf8109efc200d86537d65dc660d05`.
The manifest uses schema 2 and `tail_formula_version=1`. Its monetary array
retains the original ten fields, then appends genesis tail `1000000` and work `2`
as 32 little-endian bytes. These are the actual local fixture anchors; the
reference toy profile uses `200`/`9`, and the proposed development profile in
`docs/lotus-v2/development-profile.md` is a separate artifact.

The chain ID is `6ff87f5f041a6e4e16018ac58b33f7397d956da5712642015edf5fc560deb9c9`,
genesis ID `53e6c3d9bf12bc18f84e818349da5e5d3d11ee6e33576dab3b81be0a7a978959`,
and native validator profile digest
`1415adf3bc8c1f4d868ddb65aebb8e50205cb07e18d2feef006d4dfca4ecb39b`.
The initial 56-byte monetary envelope, timestamp, difficulty, limits, maturity
and cost schedules are unchanged. Chain ID and genesis commitments are new.
Always choose fresh homes for this identity. Preserve previous homes as legacy
evidence; do not reset or reuse them.

The exact old manifest and provenance are preserved as
`fixtures/legacy-schema1-local-test-manifest.json` and
`fixtures/legacy-schema1-provenance.json`. The schema 2 loader must reject the
legacy manifest. Reproduce and compare every new manifest byte offline using an
environment with the reference dependencies (including `blake3`):

```sh
PYTHONPATH=tools/lotus-v2-reference python3 \
  tools/lotus-v2-devnet/fixtures/reproduce_absolute_fixture.py
```

The script derives the chain ID and zero-value burn note with tagged BLAKE3
using the versioned name, rebuilds transaction/state commitments, and selects
the first valid nonce from zero. It prints the manifest SHA256 and the exact
schema 2 native validator digest. That digest inserts formula version as u64,
genesis tail as u64 and 32 little-endian work bytes after the original ten
monetary fields and before outer costs.

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


## Two-wallet walkthrough for fresh schema 2 sessions

The historical schema 1 walkthrough used these amounts and timestamps. With
the bundled schema 2 fixture and a fresh session, enter these commands at the
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
atoms, and `claim` is a requested ceiling subject to native validation. The intended
sequence produces funding, maturity and payment blocks; the recipient receives
10000 atoms and the funding input returns 89000 atoms as change. A fee of 100 was
rejected as below the transaction byte floor during validation; 1000 passed.
Native wallet keys and signatures are newly generated, so your transaction IDs,
roots and nonces will differ from recorded evidence. Later operations must use
eligible timestamps and sufficient fees; they do not inherit this sequence's
particular monetary results. See the README for explicit recovery if signing
has an unknown outcome.
