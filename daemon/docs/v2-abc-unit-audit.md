# V2 inherited native unit audit — 2026-10-15

This audit executes inherited ABC tests separately from focused V2 targets. The initial candidate does not pass the inherited unit gate.

## Exact scope

A new real `.git` clone at `/private/tmp/lotus-v2-abc-unit-audit-20261015` was created from native integration commit `f1c8c92d87023c620819dfc4a6bd88a28c446d46`. Its fresh `build-abc-audit` uses Debug, Chronik ON, wallet ON, Qt/seeder OFF, Rust 1.93.0, Python 3.13.16, AppleClang 21, and two Ninja jobs. Production workspaces, nodes, chain data, tags and releases were untouched.

Discovery found `test_bitcoin`, 147 default Boost suite runners, 147 next-upgrade runners, and a separate 11-suite Avalanche executable. `test_lotus` is not registered here. The similarly named `check-bitcoin-util` is a separate Python utility target, not an additional Boost suite.

## Baseline and controlled correction

Fresh native compilation passed. `activation_tests` and `addrman_tests` then crashed before assertions; `lotusd -version` also exited 139. The retained backtrace reaches `LeaveCritical` / `pop_lock` on an empty stack. Native source compiled with `DEBUG_LOCKORDER`, while sibling Chronik C++ and generated bridges did not.

Only startup correction `229c10aa384a78832b28352a015ad00281f0db04` was applied for a controlled rerun (local equivalent commit `0fce47dc21`). It aligns Chronik Debug compile definitions. Rebuild and `lotusd -version` passed; the two former startup failures passed. No assertion, source behavior or test was removed.

## Results after startup correction

| Gate | Verdict | Evidence |
| --- | --- | --- |
| Native default Boost suites | FAILED | 141 passed, 6 failed, all 147 executed |
| Avalanche | FAILED build / NOT RUN tests | `stakingrewards_tests.cpp:29` references removed `cowperthwaiteHeight`; all 11 runners blocked |
| secp256k1 | PASSED | tests, noverify and exhaustive runners |
| Proof of work | PASSED | `aserti32d_tests` |
| UniValue | PASSED | two runners |
| LevelDB | PASSED | 30/30 CTest tests |
| Next-upgrade variants | NOT RUN | separate gate pending default failures |
| Rust crate tests | NOT RUN | Chronik library compiled; no Rust test claim |

The six failing default suites are:

- `getarg_tests/logargs`: the expected absent string `private` appears in Debug source-location paths under `/private/tmp`. An unchanged controlled rerun with runtime `-logsourcelocations=0` passes. This is an environmental false positive; the default runner failure remains recorded.
- `net_tests/test_userAgent`: fixture expects `/Bitcoin ABC:.../`; implementation advertises `/Lotus:.../`.
- `validation_block_tests`: concurrent processing fixture aborts at line 238 because `ProcessNewBlock` returns false. Underlying rejection classification remains pending.
- `v2_wallet_tests/encrypted_native_payment`: LevelDB reports missing `v2-wallet/chain/LOCK` parent path. This is a V2 test registered inside the native default suite, not an inherited ABC test.
- `bridgeprimitives_tests`: Debug lock assertion fails in `chronik_bridge.cpp:128` while `cs_main` is listed held.
- `chronikbridge_tests`: Debug lock assertion fails in `validation.cpp:4955` while `cs_main` is listed held. Lock identity diagnosis remains pending.

## Coverage meaning and reproduction

Passing inherited crypto, serialization, storage, legacy block validation and networking checks is useful regression evidence for shared code. Legacy fixtures principally exercise ABC transaction/header and chain paths; they do not establish V2 header, monetary, VM, reorg or persistence coverage. V2 focused tests and functional acceptance remain separate.

Configure with `cmake -S . -B build-abc-audit -G Ninja -DCMAKE_BUILD_TYPE=Debug -DBUILD_CHRONIK=ON -DRust_TOOLCHAIN=1.93.0 -DPython_EXECUTABLE=/opt/homebrew/bin/python3.13 -DBUILD_QT=OFF -DBUILD_SEEDER=OFF`. Set `LIBCLANG_PATH=/Library/Developer/CommandLineTools/usr/lib` and `PYO3_PYTHON=/opt/homebrew/bin/python3.13`. Execute `ninja -C build-abc-audit -j2 -k0 check-bitcoin check-avalanche check-pow check-secp256k1 check-univalue check-leveldb`.

[Evidence](evidence/v2-abc-unit-audit/) retains target discovery, baseline/fixed command logs, exact failures and per-suite verdicts. Large individual test logs remain in the isolated build; their filenames, sizes and SHA256 hashes are recorded. No controlled pinned-ABC comparison has yet been run, so inherited versus introduced attribution beyond direct fixture evidence remains pending.

## Independent repair validation

The original failed evidence above is retained. Ordered test fixture commits `d3f1adb136`, `bb53094b56`, `52bcb2521f`, `3f48611f5f`, `00c2352c02`, and `955dfa2ff8` were applied independently to the audit clone after the startup correction. Native audit HEAD is `32078e3833` (equivalent cherry-picks). These change test fixtures only.

`net_tests`, `v2_wallet_tests`, and all 11 Avalanche suites pass. The validation fixture first progressed from `bad-cb-height` to `bad-txns-undersize` after correcting branch heights; preserving assembler minimum coinbase padding then made the full `validation_block_tests` pass. The two Chronik fixtures violated `AssertLockNotHeldInternal` by holding blanket `cs_main` locks across bridge/block-processing calls. Narrowing fixture lock scopes preserves production assertions; both complete Chronik suites now pass.

After targeted reruns, all 147 default Boost runners have executed: 146 pass and only the source-path `getarg_tests` false positive remains. All 147 separately registered `upgrade-activated` runners also executed, with the same 146 passes and one environmental failure. An unchanged controlled full `getarg_tests` rerun using `-logsourcelocations=0` passes. The default aggregate is therefore still recorded FAILED under this path, with a passing controlled check of the actual sensitive-value behavior.

The `upgrade-activated` CMake runners presently supply only a different test-suite name and logger configuration; they do not supply an activation override. Their results establish execution of those registered runners, not a distinct activation scenario.

The coherent daemon supplied to the functional audit was built at `0fce47dc21`, before subsequent test-only commits; its passing startup result has that exact source provenance. No production behavior was changed by fixture repairs. Rust crate tests and a controlled pristine-ABC attribution comparison remain NOT RUN.
