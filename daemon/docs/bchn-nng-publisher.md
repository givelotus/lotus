# BCHN optional NNG publisher candidate

This independently applicable mailbox targets current BCHN revision
`abd433abe04f74780744b9eac06731f3690ce68a` (GitLab master audited 2026-10-14):

```
daemon/patches/bchn/10-nng-interface.patch
```

It replaces the previous comment-only slot with a real **optional, default-OFF
publisher**, without mining/mempool policy/Chronik dependencies and without
removing ZeroMQ. The current default BCHN manifest still excludes this patch;
apply it to an isolated checkout with `git am`. Its committed source tree is
`37640aa58bd34ad1576d7e319a8487f2ef59df40`; independent `git am` replay matches.

This is a **new BCHN raw-payload wire protocol**, not a drop-in Lotus NNG port.
Messages contain a zero-padded 12-byte topic, a shared little-endian uint64
sequence and raw network-serialized block/transaction/hash payload. The patch
includes `doc/nng.md` with all six topics, byte order, subscription and loss
semantics. BCHN's pure-invalidation path does not emit `UpdatedBlockTip`; clients
must follow disconnected block headers for that rollback.

The simpler publisher is deliberately separated from a full legacy transport
port. Lotus's FlatBuffers request/reply service also depends on ABC chainstate
and block-storage ownership, spent-coin snapshots at admission and serialized
undo offsets. Implementing that protocol would require independent storage,
request bounds and reorg tests; none of that compatibility is implied here.
The existing Lotus implementation remains unchanged.

Configure and build the patched checkout:

```bash
cmake -S . -B build -GNinja \
  -DBUILD_BITCOIN_QT=OFF -DBUILD_BITCOIN_WALLET=OFF \
  -DBUILD_BITCOIN_NNG=ON -DBUILD_BITCOIN_ZMQ=OFF \
  -DENABLE_UPNP=OFF -DENABLE_NATPMP=OFF -DENABLE_MAN=OFF \
  -DBUILD_BITCOIN_SEEDER=OFF
ninja -C build -j6 bitcoind bitcoin-cli
python3 test/functional/interface_nng.py --configfile=build/test/config.ini \
  --nng-library=/opt/homebrew/lib/libnng.dylib
```

The explicit shared-library path is for Homebrew macOS; other hosts can omit it
when ctypes locates NNG automatically. Production has no Python dependency.

Native arm64 macOS validation passed with NNG 1.12.4 in three configurations:
NNG ON / ZeroMQ OFF, both OFF, and both ON. The NNG-only check precedes
context-only relocation of insertions away from ZeroMQ anchors; final-tree
both-ON and both-OFF builds are checked again. OFF builds omit NNG options, dynamic
linkage and undefined symbols; both-ON builds expose/link both interfaces.
The real isolated regtest subscriber passed with ZeroMQ disabled and enabled:
raw connected/disconnected blocks and tip hashes match RPC, sequence order is
checked, a mature P2SH coinbase spend's admitted raw transaction matches, mining
includes that transaction, and invalid-endpoint failure allows clean restart.
All test nodes stop; no production node, chain data or release changes occur.

These are focused transport checks. Full C++ suites, Linux/Windows builds,
ZeroMQ subscriber data flow, mempool-removal/conflict and persisted-tip payloads,
load behavior and client recovery remain unverified. No wall-clock speedup or
reliable-delivery claim is made. Detailed local logs, hashes and exact source
identity are recorded in `bchn-nng-publisher-evidence.json`.
