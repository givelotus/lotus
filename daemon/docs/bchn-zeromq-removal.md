# BCHN: disable ZeroMQ, then remove its source

These are two separate optional mailbox patches against BCHN master
`abd433abe04f74780744b9eac06731f3690ce68a` (29.2.1). The daemon uses CMake and
Ninja; the native builds below exercise that actual build system.

1. `11-disable-zeromq.patch` changes `BUILD_BITCOIN_ZMQ`'s default from ON to
   OFF. It retains all source, dependencies, notification/RPC code and the
   explicit `-DBUILD_BITCOIN_ZMQ=ON` choice. Existing CMake caches retain their
   values; use a fresh build directory or pass OFF explicitly.
2. `12-remove-zeromq.patch` follows 11 and removes the implementation and public
   interface completely: `src/zmq`, CMake discovery/options/linkage, publisher
   CLI arguments including hidden disabled-build arguments, logging/help
   categories, `getzmqnotifications`, obsolete help translations, depends
   recipes/patches, install/CI requirements, examples, docs and associated
   functional/lint plumbing. A new negative functional test checks the removed
   RPC, logging category, six former CLI options and subsequent clean restart.

Patch 12 requires 11 first. Neither depends on mining 01, diagnostic mempool 04,
NNG 10, Chronik, or a policy/consensus change. NNG remains independently
selectable. Historical release notes and incidental opaque keys, onion seed
addresses and fixture strings are preserved. This is a deliberate reduction in
source, dependencies and exposed interfaces, with no claimed performance gain.

The default BCHN manifest remains base-only. Source removal requires explicit
selection; no working node, existing workspace, chain data or release is changed.

## Apply and build

From the Lotus monorepo, use a fresh checkout and build directory:

```sh
git clone https://gitlab.com/bitcoin-cash-node/bitcoin-cash-node.git /tmp/bchn-no-zmq
git -C /tmp/bchn-no-zmq checkout --detach abd433abe04f74780744b9eac06731f3690ce68a
git -C /tmp/bchn-no-zmq am "$PWD/daemon/patches/bchn/11-disable-zeromq.patch"
# Stop here to retain source and an explicit ON choice, or apply the next patch:
git -C /tmp/bchn-no-zmq am "$PWD/daemon/patches/bchn/12-remove-zeromq.patch"
cmake -S /tmp/bchn-no-zmq -B /tmp/bchn-no-zmq-build -GNinja \
  -DBUILD_BITCOIN_QT=OFF -DENABLE_MAN=OFF \
  -DENABLE_UPNP=OFF -DENABLE_NATPMP=OFF
ninja -C /tmp/bchn-no-zmq-build bitcoind bitcoin-cli test_bitcoin check-bitcoin
python3 /tmp/bchn-no-zmq/test/functional/interface_no_zmq.py \
  --configfile=/tmp/bchn-no-zmq-build/test/config.ini
```

Do not pass `BUILD_BITCOIN_ZMQ` after source removal: that option no longer
exists. To add NNG, independently apply 10 and configure
`-DBUILD_BITCOIN_NNG=ON`; it does not restore ZeroMQ or its RPC.

The feature planner distinguishes the existing build flag from source changes:

```sh
# Existing upstream build flag; no source patch selected:
python3 daemon/scripts/feature-plan.py --target bchn --features zeromq-off
# Default-OFF source patch only, preserving an explicit ON choice:
python3 daemon/scripts/feature-plan.py --target bchn \
  --features zeromq-default-off --allow-experimental
# Ordered 11 then 12; add independent NNG if desired:
python3 daemon/scripts/feature-plan.py --target bchn \
  --features zeromq-remove,nng --allow-experimental
```

The planner reports patches; it does not apply them. Removal rejects concurrent
`zeromq-on`/`zeromq-off` flags because the underlying option is deleted.

## Validation

Native macOS arm64 validation uses Apple Clang 21 and installed development
libraries. A fresh build of 11 alone selects OFF without passing a ZeroMQ flag;
daemon/CLI builds, version checks and `mining_basic.py` regtest pass.

Both ordered mailboxes replay with `git am` to source tree
`6826005544fef3f7403f6a5ce33acdf0b7750663`. Standalone source removal builds
`bitcoind`, `bitcoin-cli`, `test_bitcoin` and passes all 126 C++ suites.
`interface_no_zmq.py` and `rpc_help.py` regtests pass. The negative interface
test fails against both the earlier ZeroMQ-enabled binary (RPC still present)
and the separate default-OFF binary (logging category still present), as
expected. Its initial
post-removal run exposed a test expectation error (the option parser omits the
argument value in diagnostics); the final test corrects that expectation.

All 170 valid raw patch orders respecting 11-before-12 apply cleanly. All 60
full five-patch orders yield identical tree
`8292404672aa11aa669e5752864104469d529dbd`, matching the tested combined source.
This includes all 64 ordered combinations of independent feature units 01,
04, 10 and removal (11 then 12). Applying 12 without 11 correctly fails.
The combined tree builds and passes all 126 C++ suites with NNG enabled and
with NNG disabled. The real NNG subscriber regtest and removed-ZeroMQ runtime
regtest pass with NNG enabled. `otool`, `nm`, binary strings and help checks
confirm no ZeroMQ linkage/symbols/interface; disabling NNG also removes its
linkage/symbols/help.

Changed shell/YAML files pass syntax checks, and the Linux depends package graph
excludes ZeroMQ. Linux/Windows binaries, Qt builds, Docker images and complete
Gitian/CI executions were not run. No mainnet synchronization, throughput or
reproducible-binary claim is made.

Reproduce the ordering proof without changing any checkout/index:

```sh
python3 daemon/tests/check-bchn-patch-combinations.py --upstream /tmp/bchn-no-zmq \
  --expect-tree 8292404672aa11aa669e5752864104469d529dbd
```

See [ordering evidence](evidence/bchn-zmq-removal-orders-20261014.json) and
[native/runtime evidence](evidence/bchn-zmq-removal-validation-20261014.json)
for exact patches, trees, modes, log hashes and remaining validation boundaries.

## Upstream submissions

- [MR 2177](https://gitlab.com/bitcoin-cash-node/bitcoin-cash-node/-/merge_requests/2177): default-disable only, commit `19b1d245742c949087f03f063721770816c150ec`.
- [MR 2178](https://gitlab.com/bitcoin-cash-node/bitcoin-cash-node/-/merge_requests/2178): complete source/interface removal, commit `c3fde6e531223eea0a0249414913cdd65cb403fc`, depending on MR 2177. Its branch contains the prerequisite followed by the removal commit; both target upstream master, and the description asks to merge the prerequisite first.

Both submitted source trees exactly match the independently tested exports. Neither includes NNG or mining/mempool changes. Public API removal is explicitly documented. See [submission identities](evidence/bchn-interface-submissions-20261014.json). Initial fork CI remains subject to GitLab account verification; local evidence is separate from upstream CI and maintainer acceptance.
