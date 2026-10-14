# Independent eCash candidate verification (2026-10-14)

Historical evidence: this report's 01 failure results refer to the superseded static-package payload (raw SHA256 `556182643ff288998a6fc1c97238a73f40268de0d5fec5f2fba2dc0c8bf1dedf`). Current eCash 01 retains a corrected custom snapshot/ready-heap assembler; see [new source and native evidence](ecash01-corrected-snapshot-assembler.md). Other candidate results below retain their recorded revision scope.

The initial `f473cb58` audit found native mining-test failures in then-current 01 and a compile failure in 02. Those two payloads are now corrected; the current 01/02/04 combination passes the separately recorded checks. Default selection remains explicit, while 03 is a no-op explanation and 10/11 are unimplemented placeholders. The results below retain their exact historical source scope.

This independent verification starts from monorepo `f473cb58` in `/tmp/lotus-wt-ecash-verification`, branch `audit/ecash-independent-20261014`. It checks every payload and selected combinations using temporary Git indexes. Builds use a disposable standalone ABC clone at `/tmp/lotus-ecash04-verification`. No production node, workspace, chain data, tag, release asset, or maintained patch payload was changed.

Current 02 is also corrected and independently tested; its old compile failure and append-order conflict below are historical evidence for raw payload SHA256 `cf0b36ba046f6305ae7176bd800854088f328dac0901c4c23996e5150f510432`. See [current container and combination evidence](ecash02-container-and-combinations.md). Files 03/10/11 remain non-implementations.

## Exact source revisions and application

- Pinned eCash reference: `252182e957120652960c1f88ec96515c448b1204`.
- Candidate 04's declared base and Lotus ABC base: `8c67fe1e85a602204a2ce65aa3b643469c2c3a1d`.
- Current [Bitcoin ABC primary repository](https://github.com/Bitcoin-ABC/bitcoin-abc) master at audit start (`git ls-remote ... HEAD`): `1fb7db17c176cdea8a2c60d887891589382ee4e3`. Compared with 8c67, its two newer commits change dust policy/tests and RPC spelling, not the candidate's mempool implementation.

| Candidate | Pinned 252182 | Declared 8c67 | Current 1fb7 | Actual validation/status |
|---|---|---|---|---|
| 01 block construction | Applies | Fails `miner.h` | Fails `miner.h` | Previously built at the pin; three existing mining assertions fail. Payload unchanged since that native audit. |
| 02 “remove chain limit” | Applies | Applies | Applies | Only adds an unchecked-container test; changes no policy. Pinned native compile fails `SigOpCount`; current 1fb7 plus 04 independently reproduces the same compile failure. |
| 03 mempool cleanup | No diff | No diff | No diff | Comment-only historical no-op; not executable. |
| 04 finalized-ancestor pruning | Fails `txmempool.cpp` | Applies | Applies | Independently tested as described below; not applicable to the wrapper's older default eCash pin. |
| 10 NNG | No diff | No diff | No diff | Unimplemented placeholder. |
| 11 ZeroMQ deletion | No diff | No diff | No diff | Unimplemented placeholder; existing build flags already disable ZeroMQ. |

Application uses `git read-tree <exact SHA>` and `git apply --cached` in a temporary index; clean application is not a build result. [Recorded evidence](evidence/ecash-independent-application-2026-10-14.json) contains every individual result, failure text, patch checksums, and tested combination tree IDs.

Combination findings:

- 01 then 04 fails at every revision: 04 does not apply to the old pin, while 01 does not apply to either newer revision.
- 02 then 04 conflicts at the appended mempool test on both newer revisions; at the old pin 04 also conflicts in production source.
- 04 then 02 applies at both newer revisions, but application order cannot repair 02's missing helper API. It is not a passing combination.
- No-op and placeholder files cannot become implementations by adding them to a combination. They remain excluded.

No existing candidate was silently rebased or repaired to make the matrix appear green. Candidate 02's API typo could be changed to `SigChecks`, but that would still not turn unchecked insertion into admission-policy coverage; retaining the exact payload and documenting its failure is clearer.

## Candidate 04 native evidence

Build configuration: macOS arm64, Apple Clang 21.0.0 (`clang-2100.1.1.101`), CMake 4.4.4, Ninja 1.13.2, Python 3.13. Qt, ZeroMQ, and Chronik are disabled. Candidate 04 is applied with `git am --keep-non-patch`; no compatibility changes are made to it.

At declared base 8c67, the exact candidate source tree is `bdfa61cf6b966e3fa3f0d33ef8be91fb7d5de0e8`:

- `bitcoind`, `bitcoin-cli`, `test_bitcoin`, and the separate `test-avalanche` binary compile.
- `mempool_tests`, `miner_tests`, and `validationinterface_tests` pass: 22 cases and 2,347 assertions, including the candidate's new chained-finalization fixture.
- Full `check-bitcoin` passes, including its configured upgrade-activated runners. This does not mean every independent CMake test suite was run.
- Separate `processor_tests` passes: 64 cases and 44,787 assertions.
- Upstream `abc_p2p_avalanche_transaction_finalization.py` passes in isolated regtest (83 seconds): real transaction admission/finalization for simple transactions, chains and diamonds, plus full-block, minimum-fee, expiry, eviction, and parent-confirmed-in-a-non-finalized-block behavior. The harness uses temporary nodes and mocked local quorum peers; it is not public-network Avalanche deployment evidence.

An additional independent [test-only mailbox fixture](../candidates/ecash-finalized-pruning-verification/README.md) passes 21 assertions after exact 04. It checks a partially finalized diamond in both lookup modes, exact new finalization IDs/counts, rejection of a locked unfinalized child, and clearing old result IDs when re-finalizing. Its tree at 8c67 is `3c8c5d7c34faf50b6cff90129b9fc348462b2429`. The maintained candidate 04 remains byte-for-byte unchanged.

At current master snapshot 1fb7, the exact candidate-04 tree is `53d432b7f758fe031478b5324490463822a05320`. Daemon, CLI, `test_bitcoin` and `test-avalanche` compile; the same 22 focused native cases / 2,347 assertions and 64 processor cases / 44,681 assertions pass. Applying 02 after 04 then attempting the actual mempool test object independently reproduces `no member named 'SigOpCount' in 'TestMemPoolEntryHelper'` at line 875. Candidate 02 was reversed afterward; no compile fix was substituted. Full `check-bitcoin` also passes at this current revision, as does the same real regtest finalization test (83 seconds). The independent partial-diamond fixture applies and passes all 21 assertions here too, producing source tree `adf8942ce052de140594d4c6272a5a95b2a41f1e`.

## Scope and interpretation

The production changes in 04 are confined to ancestor traversal/finalization and associated declarations; converting the unused success return to `void` compiles against the checked callers. Skipping finalized branches relies on upstream's finalized-state invariant. The unit fixtures and real regtest exercise representative boundaries; they do not constitute an exhaustive proof over all reorg/state transitions.

No scaling benchmark, lock-contention measurement, sanitizer run, Chronik check, public-network quorum test, mainnet replay, or Linux build was run in this independent audit. The code structurally avoids walking already-finalized ancestry; its exact performance claim remains unbenchmarked. Chronik does not require this optimization, mining patch 01, candidate 02, NNG, or ZeroMQ deletion.

Local logs are named `/tmp/lotus-ecash04-8c67-{configure,build,native-tests,check-bitcoin,processor,functional}.log`, `/tmp/lotus-ecash04-independent-{build,test}.log`, and `/tmp/lotus-ecash04-current-*.log`. Earlier unchanged 01/02 native evidence remains in [the mining review](ecash-block-assembly-review.md) and [candidate build record](evidence/ecash-candidate-build-2026-10-14.json).

Reproduce exact-04 checks in a new standalone clone:

```sh
git checkout --detach 8c67fe1e85a602204a2ce65aa3b643469c2c3a1d
git am --keep-non-patch /path/to/04-prune-finalized-mempool-ancestors.patch
cmake -S . -B build -GNinja -DBUILD_QT=OFF -DBUILD_ZMQ=OFF -DBUILD_CHRONIK=OFF \
  -DPython_EXECUTABLE=/opt/homebrew/bin/python3.13
ninja -C build -j6 bitcoind bitcoin-cli test_bitcoin test-avalanche check-bitcoin \
  test/functional/test_runner.py
build/src/test/test_bitcoin --run_test=mempool_tests,miner_tests,validationinterface_tests
build/src/avalanche/test/test-avalanche --run_test=processor_tests
/opt/homebrew/bin/python3.13 build/test/functional/test_runner.py --jobs=1 \
  --tmpdirprefix=/tmp/ecash04-regtest abc_p2p_avalanche_transaction_finalization.py
```
