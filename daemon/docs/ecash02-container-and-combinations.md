# Current eCash candidates: container repair and combinations

The three implemented eCash candidates **01, 02 and 04 apply cleanly on exact current ABC `1fb7db17c176cdea8a2c60d887891589382ee4e3`**, independently and in every order. Their combined source builds and passes native unit and targeted regtest checks. Files 03, 10 and 11 remain explicit non-executable no-op/placeholder notes, not implemented PRs.

## Candidate 02

`02-remove-chaintx-limit.patch` keeps its historical filename but carries the accurate mailbox subject `[test] Verify unchecked long-chain mempool graph bookkeeping`.

- Exported directly from current-base source commit `5f173e591857e7361408d7b016951dfaf3b5a51e`, parent `1fb7db17c176cdea8a2c60d887891589382ee4e3`.
- Resulting independent source tree: `50488425c029d98b50274c0507b2c3c798e4875b`.
- Mailbox SHA256: `4ec4fba03e2f4d17452f948fcce268fc5683bdb82bc52c8086f958b6f78f4928`.
- Only changed source file: `src/test/mempool_tests.cpp`.

The correction uses the supported `SigChecks` helper and names the fixture `unchecked_long_chain_parent_graph`. It inserts 100 entries through `addUnchecked` and checks parent/child links, increasing parent-before-child entry IDs, all 99 ancestors, all 100 descendants including the root, and recursive midpoint removal that preserves the first 49 entries and repairs their links. Output values decrease consistently with the recorded per-entry fee.

This is a container/graph test. It bypasses normal admission and changes no production code, chain-limit policy, consensus, or relay behavior. It does not prove that ordinary admission accepts this synthetic chain. Moving the fixture beside existing finalized-container tests avoids the old append-at-EOF conflict with independent 04.

The former `SigOpCount` compile failure is retained as historical evidence for raw payload SHA256 `cf0b36ba046f6305ae7176bd800854088f328dac0901c4c23996e5150f510432`. `reference-metadata-provenance.json` retains the old payload/tree/envelope under `history` and independently records this intentional test change. Earlier older-base compatibility checks remain historical validation, not the maintenance target.

## Exact current application matrix

All 15 selections pass `git apply --cached` against a fresh temporary index initialized from current `1fb7db17`: three single patches, six ordered pairs, and six ordered triples. All six triples produce the **same source tree** `dbacbe35e3887e00b19eb171bce1dd74adb21b05`. Source equality establishes that these candidate changes do not require an application-order dependency.

| Selection | Application on exact current base | Native verification |
|---|---|---|
| 01 custom snapshot assembler | Pass | Independent daemon/CLI/test build, miner tests and full C++ checks pass; see [01 evidence](ecash01-corrected-snapshot-assembler.md). |
| 02 unchecked-container fixture | Pass | Independent native `mempool_tests`: 10 cases, 1,985 assertions pass. |
| 04 finalized-ancestor pruning | Pass | Independent builds, full C++ checks, processor and real finalization regtest pass; see [04 evidence](ecash-independent-verification.md). |
| Every ordered pair | Pass | Combined behavior is exercised in the complete triple below; separate native builds of every pair were not repeated. |
| Every ordered triple | Pass; identical final trees | One complete triple was built and behaviorally tested. Identical source trees make six redundant builds unnecessary. |
| 03 mempool cleanup | No source diff | Historical no-op explanation, excluded from execution. |
| 10 NNG | No source diff | Unimplemented placeholder, excluded from execution. |
| 11 ZeroMQ deletion | No source diff | Unimplemented placeholder, excluded from execution. Existing build options already disable ZeroMQ. |

Complete application records and mailbox checksums are in [combination evidence](evidence/ecash-current-combinations-2026-10-14.json).

## Combined native and behavioral validation

The actual isolated native combination applies 02, then 01, then 04 to exact current `1fb7db17`. Its tip is `e07e53b53c981732948258fa090ad157622a95dd`, tree `dbacbe35e3887e00b19eb171bce1dd74adb21b05`. It contains no unrelated candidate fixtures or Lotus protocol changes.

On macOS arm64 with Apple Clang 21.0.0, CMake 4.4.4 and Ninja 1.13.2, Qt/ZeroMQ/Chronik disabled:

- `bitcoind`, `bitcoin-cli`, `test_bitcoin` and separate `test-avalanche` compile.
- Full `check-bitcoin` passes.
- `mempool_tests`, `miner_tests`, `validationinterface_tests`: **23 cases / 3,257 assertions pass**.
- Separate `processor_tests`: **64 cases / 44,518 assertions pass**.
- Actual `abc_p2p_avalanche_transaction_finalization.py` passes on fresh isolated regtest in **86 seconds**. It exercises simple transactions, chains, diamonds, resource limits, fees, expiry, eviction, and delayed finalization when a parent is confirmed in a non-finalized block.

This functional test runs temporary local nodes and mocked quorum peers. It does not claim a deployed public-network quorum, Linux validation, Chronik-enabled builds, mainnet replay, or performance measurements for this eCash combination. Lotus has separate protocol and validation evidence.

Current-reference maintenance should use the exact verified `1fb7db17c176cdea8a2c60d887891589382ee4e3` pin so all three implemented candidates share one compatible target. The older `252182e957` reference cannot apply 04. Default candidates should remain commented until explicitly selected; placeholder files must never be passed to the replay tool. Changing the eCash reference pin does not change Lotus's independent V1 source pin, deploy a node, or publish a release.

## Reproduction

In a new standalone ABC clone:

```sh
git checkout --detach 1fb7db17c176cdea8a2c60d887891589382ee4e3
git am --keep-non-patch /path/to/02-remove-chaintx-limit.patch
git am --keep-non-patch /path/to/01-nlogn-block-construction.patch
git am --keep-non-patch /path/to/04-prune-finalized-mempool-ancestors.patch
cmake -S . -B build -GNinja -DBUILD_QT=OFF -DBUILD_ZMQ=OFF -DBUILD_CHRONIK=OFF \
  -DPython_EXECUTABLE=/opt/homebrew/bin/python3.13
ninja -C build -j6 bitcoind bitcoin-cli test_bitcoin test-avalanche check-bitcoin \
  test/functional/test_runner.py
build/src/test/test_bitcoin --run_test=mempool_tests,miner_tests,validationinterface_tests
build/src/avalanche/test/test-avalanche --run_test=processor_tests
/opt/homebrew/bin/python3.13 build/test/functional/test_runner.py --jobs=1 \
  --tmpdirprefix=/tmp/ecash-combination-regtest abc_p2p_avalanche_transaction_finalization.py
```

Native logs: `/tmp/lotus-ecash02-current-{build,mempool}.log` and `/tmp/lotus-ecash010204-current-{build-checks,native,processor,functional}.log`. Machine-readable native results are in [native combination evidence](evidence/ecash-current-native-2026-10-14.json). Existing production workspaces/nodes, chain data and published releases were preserved throughout.
