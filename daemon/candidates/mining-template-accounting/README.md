# Lotus mining-template accounting repair

This standalone mail patch restores the retained upstream fee-rate index and direct-parent assembler. It fixes template-selection resource/fee accounting in Lotus's experimental package accumulator; it does not change block consensus validation or the FRBTC coinbase rule.

## Exact source and application

- Base: `a055e77a25c1664d63080cec4d8409d3a63bc190` (Lotus V1 on ABC `8c67fe1e85a602204a2ce65aa3b643469c2c3a1d`, before this repair).
- Original repair: `e21d07c27a2235667d1450a003e883b246ed5aa3`.
- Expected result tree: `e0d4f9c0219739b6774864858c582a8144a443d9`.
- Changes only `src/node/miner.cpp`, `src/node/miner.h`, `src/test/miner_tests.cpp`.

In a disposable checkout containing the recorded base:

```sh
git checkout --detach a055e77a25c1664d63080cec4d8409d3a63bc190
git am /absolute/path/0001-restore-mining-template-accounting.patch
git rev-parse HEAD^{tree}
```

An actual isolated `git am` replay was verified against the expected tree. This patch has already been folded into maintained Lotus patch 246; do not apply it again to the repaired V1 tree. Compatibility with another Lotus fork or its current branch has not been established. The exact base commit must be available; the mail patch is not a repository bundle.

## Bug and regression evidence

The experimental accumulator charges selected ancestors again, rejecting a fitting child near capacity. Retained ancestor fees can subsidize an unprioritized free descendant, and fee deltas affect grandchildren. The fix removes that accumulator and restores the retained upstream algorithm, with updated fee/prioritization fixtures and a paid parent/child template leaving exactly one byte spare.

The same final native miner tests report five failed assertions before the repair and zero errors after it. The failures cover free transaction inclusion, its descendant, missing fitting child/two instead of three template transactions, and inherited fee-delta grandchild inclusion. Copies of the original before/after logs are in `evidence/`; they contain local test paths. Focused Chronik-OFF builds and all 151 C++ checks passed. Subsequent complete integrated Chronik-enabled V1 builds passed all 156 checks and live mainnet/RPC/Chronik parity; that broader evidence belongs to the integrated repaired tree, not a new independent execution of this packet.

To rerun the focused suite on macOS (adjust the Python interpreter path on another host):

```sh
cmake -S . -B build -GNinja \
  -DBUILD_BITCOIN_QT=OFF -DBUILD_BITCOIN_ZMQ=OFF \
  -DENABLE_UPNP=OFF -DENABLE_NATPMP=OFF -DBUILD_CHRONIK=OFF \
  -DPython_EXECUTABLE=/opt/homebrew/bin/python3.13 -DRust_TOOLCHAIN=1.93.0
ninja -C build -j16 lotusd lotus-cli test_lotus
(cd build && ./src/test/test_lotus --run_test=miner_tests --color_output=no)
ninja -C build -j16 check-bitcoin
```

Run test binaries from the disposable build directory to keep generated fixtures out of other checkouts. No running node, chain data, published release or maintained patch files were changed to prepare this packet.
