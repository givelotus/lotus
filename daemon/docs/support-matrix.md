# Daemon support and independent feature audit

Checked 2026-10-14. “Applies” means patch application only. A successful build is a separate result; passing tests or synchronization is separate again. Existing production workspaces, running nodes, data, release assets, and tags were not changed by this audit.

## What the current tooling actually supports

| Selector | Source pin consumed by setup | Build targets | Actual support |
|---|---|---|---|
| `v1` (default) | `bitcoin-abc-v1-version`: `8c67fe1e85a602204a2ce65aa3b643469c2c3a1d` | `lotusd`, `lotus-cli` | Maintained 153-patch mainnet series retains the corrected custom assembler in 001; 246 no longer reverses it. Chronik-enabled builds, C++/Rust checks, fresh mainnet replay and Chronik parity pass. Corrected release artifact CI remains required. See [mining repair](ecash-block-assembly-review.md) and [validation](v1-8c67fe1e85-validation.md). |
| `ecash` | `bitcoin-abc-version`: `1fb7db17c176cdea8a2c60d887891589382ee4e3` | `bitcoind`, `bitcoin-cli` | Current acceptance target. Corrected 01, test-only 02 and independent 04 apply in every tested ordering; all six triples yield the same tree. Combined builds, full C++ checks, processor tests and finalization regtest pass. Earlier failures below are historical evidence. See [current combination evidence](ecash02-container-and-combinations.md). |
| `bchn` | `bchn-version`: `abd433abe04f74780744b9eac06731f3690ce68a` (current master, 29.2.1) | `bitcoind`, `bitcoin-cli` | Exact-tip native builds, all 126 C++ suites and two mining functional tests pass with the independent ready-backlog fee-priority fix. Current admission/mining already avoid transitive quadratic tracking. Historical 01/02 are not selected. See [current BCHN audit](bchn-current-audit.md). |
| `doged` | `doged-version` | `doged`, `doge-cli` | Exact pin `9690833b8b6709b7a7837bc397f0d04bf3b885d1` plus two mailbox patches (Apple arm64 test compilation and an AuxPoW Chronik regression): Chronik-enabled daemon/CLI, 740 C++ cases and six isolated functional tests pass. Full mainnet synchronization and network Avalanche behavior remain untested. See [Dogecoin lineage](dogecoin-lineage.md). |
| Bitcoin Core | No selector or pin | No configured target | Not supported by the existing wrapper. Copying BCHN or ABC patches is not a port. |

`ecash-version` (`fa7a44f731a2dfe1587e572d9eb0e4bb7c73d79c`, old ABC v0.24.11) and `lotusd-version` (`v10.4.10`) are historical provenance references: setup/build/refresh do not read them. They do not define today's mainnet version. Their inherited comments about 42 patches, an archived V1, or a stalled/divergent mainnet were obsolete and have been corrected. Release preparation should identify the actual executable source pin and version rather than treating all six files as equivalent inputs.

The original ecash/BCHN executable manifests included `03-mempool-cleanup.patch`, a comment-only no-op that `git apply` rejects. This audit removes all experimental entries from default execution, retaining their payloads for explicit review through the feature planner. The no-op file remains as historical explanation. Slots 10 (NNG) and 11 (ZeroMQ source deletion) are also comment-only placeholders and remain excluded. Manifest existence does not imply implemented or maintained support.

## Historical upstream application evidence before eCash 01 correction

Remote default-branch revisions were checked directly with `git ls-remote <primary repository> HEAD`; the isolated checkouts match those revisions:

| Primary repository | Current revision | Existing candidate application |
|---|---|---|
| [Bitcoin ABC](https://github.com/Bitcoin-ABC/bitcoin-abc) | `8c67fe1e85a602204a2ce65aa3b643469c2c3a1d` | ecash 01 fails `src/node/miner.h`; 02 applies independently. |
| [BCHN](https://gitlab.com/bitcoin-cash-node/bitcoin-cash-node) | `abd433abe04f74780744b9eac06731f3690ce68a` | BCHN 01 and 02 fail. |
| [Bitcoin Core](https://github.com/bitcoin/bitcoin) | `f13ae519de94394314cd63a27924b0998ac65d45` | BCHN 01 expects nonexistent `src/miner.cpp`/`.h`; 02 fails its test context. No Core-specific candidates exist. |
| [Doged](https://github.com/doged-io/doged) | `9690833b8b6709b7a7837bc397f0d04bf3b885d1` | ecash 01 and 02 apply, individually and together. This is not a build/sync result. |

At the older pinned ABC `252182e957` and BCHN `0bc23ac4c`, 01 and 02 apply. All 03/10/11 files contain no valid patch hunks. Full check results are recorded in [application evidence](evidence/feature-apply-2026-10-14.json).

Checks used isolated `/tmp/lotus-upstream-feasibility-*` checkouts and disposable candidate worktrees. A standalone local-object clone was required for pinned ABC builds: upstream CMake assumes `.git` is a directory, so linked worktrees fail configuring `.git/logs/HEAD`. No source workaround was added to the candidate for the successful standalone configuration.

## Unmodified upstream build evidence

Pinned ABC `252182e957` was also compiled **without** experimental patches. Reversing candidate 01 after removing candidate 02 restored a clean tracked source tree; daemon/CLI rebuild passed. Regenerating cached build metadata produced `Bitcoin ABC version v0.32.8-252182e95712` without a dirty suffix. This records actual base-only compilation, not an inference from the changed miner build. No upstream-mainnet behavior or Chronik check was run for this base-only build.

Pinned BCHN `v28.0.0` (`0bc23ac4c1365f34ed824e2b07e554ec06a5f5cd`) initially failed configuration because optional manpage generation requires unavailable `help2man`. Reconfiguration with `-DENABLE_MAN=OFF` succeeded, without a source patch. Building `bitcoind bitcoin-cli` passed all 228 Ninja steps. The clean-tree binaries report `v28.0.0-0bc23ac4c`; no experimental candidate was applied. At that earlier audit, BCHN unit, consensus, mainnet synchronization and current-tip builds were not run. Current-tip checks are recorded separately in [the current audit](bchn-current-audit.md).

```sh
cmake -S /tmp/lotus-bchn-base-build -B /tmp/lotus-bchn-base-build/build -GNinja \
  -DBUILD_BITCOIN_QT=OFF -DBUILD_BITCOIN_ZMQ=OFF \
  -DENABLE_UPNP=OFF -DENABLE_NATPMP=OFF -DENABLE_MAN=OFF \
  -DPython_EXECUTABLE=/opt/homebrew/bin/python3.13
ninja -C /tmp/lotus-bchn-base-build/build -j6 bitcoind bitcoin-cli
```

Both base-only audits use Apple Clang 21.0.0 (`clang-2100.1.1.101`), CMake 4.4.4, Ninja 1.13.2, current installed dependencies, and disposable standalone clones. Logs and results are summarized in [base build evidence](evidence/upstream-base-build-2026-10-14.json).

## Historical pinned ABC candidate build/test evidence

On macOS arm64, a standalone clone at `252182e957` with exact ecash 01 and 02 configured with Ninja, Qt/ZMQ/UPnP/NATPMP/Chronik disabled, Python 3.13. Daemon and CLI compiled. `test_bitcoin` failed compiling candidate 02: `TestMemPoolEntryHelper` has no `SigOpCount` member (`mempool_tests.cpp:786`). No silent compatibility fix was applied.

After reversing only 02 in the disposable clone, exact candidate 01 compiled the test binary. Running `test_bitcoin --run_test=miner_tests --log_level=test_suite` failed three assertions in `CreateNewBlock_validity_no_preconsensus`: free child and high-fee descendant were included where the existing test excludes them (`miner_tests.cpp:235–236`), then block transaction count was 7 rather than 6 (`:744`). This is concrete behavioral incompatibility, not merely missing test coverage. Whether a changed CPFP policy is intended requires explicit design and updated policy tests; the unchanged test suite does not pass. There is no mainnet sync or Chronik claim from this build.

Local evidence logs: `/tmp/lotus-ecash-standalone-configure.log`, `/tmp/lotus-ecash-candidate-build.log`, `/tmp/lotus-ecash-candidate01-test-build.log`, `/tmp/lotus-ecash-candidate01-miner-tests.log`. A compact permanent summary is in [native candidate evidence](evidence/ecash-candidate-build-2026-10-14.json).

## Feature boundaries and dependencies

| Feature | ABC / ecash | ABC-derived Dogecoin | BCHN | Bitcoin Core |
|---|---|---|---|---|
| Chronik | Existing `BUILD_CHRONIK`; runtime `-chronik=1` | Existing `BUILD_CHRONIK`; Dogecoin consensus/indexing still requires its separate lineage validation | No implemented port here | No implemented port here |
| NNG | Implemented in Lotus V1 with `BUILD_BITCOIN_NNG`; ecash slot 10 is a placeholder | No implemented local port | Independent default-OFF raw-payload publisher, explicitly experimental and not Lotus wire-compatible | No port |
| Block construction | Corrected ecash 01 uses a custom snapshot/ready heap; native pinned/current checks pass, with no measured speedup claim | Original ecash 01 application was checked; corrected Dogecoin port is not validated here | Current-tip ready-backlog fee-priority fix has native and functional evidence; no speedup claim | Requires a new port/review of current mining interfaces |
| Transaction chain limits | Existing ABC policy must be assessed as upstream behavior; candidate 02 changes no policy | 02 changes no policy | Limits already removed upstream in 2021; historical 02 changes no policy | No implemented policy change; current cluster/package policy must be evaluated independently |
| Disable ZeroMQ | `BUILD_ZMQ=OFF` (legacy `BUILD_BITCOIN_ZMQ` alias) | `BUILD_ZMQ=OFF` | `BUILD_BITCOIN_ZMQ=OFF` | `WITH_ZMQ=OFF` |
| Delete ZeroMQ source | Placeholder only | No patch | Placeholder only | No patch |

Chronik requires its own bridge/storage/serialization implementation and Rust dependencies. It does **not** require NNG, ZeroMQ deletion, mining algorithm replacement, chain-limit changes, or Avalanche policy changes. In Lotus V1 the whole mainnet patch series defines consensus; selecting `BUILD_CHRONIK` does not make arbitrary subsets of that historical series supported. NNG and Chronik have separate CMake guards.

Disabling ZeroMQ is independent of enabling NNG. Removing ZeroMQ source would require updating build/install/tests and documenting the loss of its public notification API; enabling NNG is a migration choice rather than a technical dependency. Build wrappers should expose explicit choices instead of silently attaching mining/policy patches to indexing.

The independent planner resolves implemented build flags and experimental patch selection, and fails closed for placeholders:

```sh
# Existing Chronik, with no policy/mining patches:
python3 daemon/scripts/feature-plan.py --target doged --features chronik,zeromq-off

# Experimental review only; check exact clean HEAD without modifying it:
python3 daemon/scripts/feature-plan.py --target doged \
  --features block-construction,long-chain-container-test --allow-experimental \
  --check-workspace /tmp/lotus-upstream-feasibility-doged

# Patch path output can feed isolated candidate tooling:
python3 daemon/scripts/feature-plan.py --target ecash \
  --features block-construction --allow-experimental --patches
```

No candidate depends on another candidate. `long-chain-container-test` deliberately names what patch 02 does; requesting a standalone `tx-chain-limit` policy change fails rather than silently substituting an unchecked insertion test. The planner reports application, build and behavior separately and never starts a node or mutates the checked tree/index.

## Historical static-package candidate review limits

Patch 01 adds no tests and changes transaction selection. A passing compilation would not establish its advertised O(n log n) bound or mining correctness:

- Summing parents' package statistics counts shared ancestors more than once, affecting fee, size and sigcheck decisions.
- Ancestor DFS has no visited set during traversal. Repeated paths in layered diamonds can expand repeatedly even though final insertion deduplicates transaction IDs.
- Package totals remain static after ancestors enter the block; package-fit decisions can reject transactions that would fit based on their remaining ancestors.
- Package-level fit is checked before insertion. Targeted tests must cover DAG ordering, partial packages, shared ancestors, capacity/sigchecks, fees, invalid ancestors, prioritization, and interruption/time limits. BCHN's candidate explicitly ignores its time-limit argument.

The entry-ID topological-order assumption does have supporting ABC source invariants (`txmempool.cpp` asserts ancestor entry IDs precede a child); that evidence does not resolve the other issues. Patch 02 uses `addUnchecked`, bypassing admission policy, and its spend/value construction is not an end-to-end valid-chain fixture.

Do not submit these candidates as ready upstream improvements or enable them in a supported release based on a clean patch application. Retain separate consensus, synchronization, Chronik RPC/disk parity, reorg behavior, and Avalanche tests for any Dogecoin lineage candidate.

## Later independent eCash candidate verification

ABC master advanced to `1fb7db17c176cdea8a2c60d887891589382ee4e3` during this session. Every eCash payload was checked again independently at that exact revision, original `8c67fe1e85`, and pinned `252182e957`. Newly added candidate 04 passes independent native builds, full `check-bitcoin`, processor tests and real isolated transaction-finalization regtest at both newer revisions, but fails application at the older default pin. Candidate 01/02 failures and no-op/placeholder classifications remain unchanged. See [the independent report](ecash-independent-verification.md) for combination conflicts, exact trees and test-only diamond coverage. This is not an all-patches-pass result.

## Corrected custom eCash 01

The static-package 01 described in historical sections above has been replaced by a corrected custom dependency snapshot and ready heap, retaining the intended independent implementation. One mailbox patch contains the algorithm and native regressions. It passes daemon/CLI/test builds, native miner tests and full `check-bitcoin` at pinned `252182e957` and current `1fb7db17c1`; it also applies cleanly at `8c67fe1e85`. The bound is expected O(n + m + n log n), with independent operation-count evidence and no claimed wall-clock speedup over already efficient modern ABC. See [current source and evidence](ecash01-corrected-snapshot-assembler.md). Candidate 02 and placeholders remain separately classified. Lotus maintains its own patch series and validation; this eCash diff changes no live daemon or release.
