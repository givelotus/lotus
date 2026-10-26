# Lotus V2 foundations candidate — REVIEW

This is an isolated, review-only patch series on Bitcoin ABC `1fb7db17c176cdea8a2c60d887891589382ee4e3` (`master` as resolved on 2026-10-14). It does not change `daemon/bitcoin-abc-v2-version`, `daemon/patches/v2/series`, an existing workspace, or a release. The final source tree and every intermediate tree are recorded in `manifest.json`.

The original V2 topics 000–005 remain separate. Topic 001 folds the corrected custom direct-parent snapshot and ready-fee heap into the original mining topic. Topic 006 repairs mining tests for dynamically mined regtest blocks and the inherited rules now enforced from genesis. Topic 007 combines the header primitives and independent compact-target vectors. Topic 008 combines the bounded output codec with the follow-up that aligns its public namespace to `lotus::v2` and makes all test checks active in Release builds. Original authors and dates are retained in the mailboxes; each mailbox body identifies its source commit or commits.

These are foundations for evaluation. The chain still inherits upstream network and genesis parameters. Header and output primitives are isolated review code; neither is wired into block or transaction consensus. V2 protocol parameters, independent consensus validation, and network identity remain open. No transaction-worker work is included.

## Replay

From an isolated checkout of the recorded ABC base, apply the files in `series` order with `git am --keep-non-patch`. The generated `manifest.json` lists each expected tree. A separate temporary-index replay with `git apply --cached --whitespace=nowarn` and a fresh `git am` replay both matched all nine intermediate trees and final tree `2e373abb42c7989587cc8083de79a86a00efe3bf`. The `nowarn` setting preserves two trailing spaces in the independently vendored BLAKE3 implementation; it does not suppress application conflicts. No canonical series was replayed or reset for this verification.

## Checks

The following checks are run from the combined source clone `/tmp/lotus-v2-foundations-review`:

```sh
cmake -S . -B build -GNinja -DBUILD_QT=OFF -DBUILD_ZMQ=OFF -DBUILD_CHRONIK=OFF
ninja -C build -j6 test_bitcoin check-lotus-v2-header
./build/src/test/test_bitcoin --run_test=miner_tests --log_level=error --color_output=no

cmake -S src/lotus_v2/output_test -B build-output-debug -DCMAKE_BUILD_TYPE=Debug
cmake --build build-output-debug
ctest --test-dir build-output-debug --output-on-failure
cmake -S src/lotus_v2/output_test -B build-output-release -DCMAKE_BUILD_TYPE=Release
cmake --build build-output-release
ctest --test-dir build-output-release --output-on-failure
```

The combined native `test_bitcoin` build and `check-lotus-v2-header` target passed. The header target reported `V2 header primitive vectors and boundaries passed`. All six `miner_tests` cases passed. Output codec Debug and Release standalone CTests each passed (one test each). Reconfiguring and rerunning the native header/miner checks after the final 008 commit also passed.

On the same repaired mining fixture, temporarily compiling the six-topic scheduler source in place of corrected `miner.cpp` and `miner.h` produced ten failures: free descendants were included, a child was excluded despite one byte or one sigcheck of spare capacity, sibling fee priority was wrong, and ancestor fee deltas leaked into later choices. Restoring the corrected source passed all six `miner_tests` cases in the prior isolated master-base review. The combined candidate must pass the checks above independently.
