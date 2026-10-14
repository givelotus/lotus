# Corrected eCash snapshot assembler

`daemon/patches/ecash/01-nlogn-block-construction.patch` now contains one corrected custom assembler and its regression tests. It retains an independent dependency snapshot; it does **not** restore upstream's assembler or submit a tests-only substitute. No separate corrective patch is required after 01. Lotus maintains its own patch series and protocol fixtures separately.

## Source and provenance

- Exact pinned base: ABC `252182e957120652960c1f88ec96515c448b1204`.
- Corrected source commit: `9d8fa7c8cfccc34829bbc127b5baecbb1aabc7b4`.
- Corrected pinned tree: `81abb3f6849493e617dc9aa30dca769390a80f9f`.
- Mailbox SHA256: `47ed17f2af1c8aabf9debaaf05a75c699f71c97601168a29097ee47e1be11bb5`.
- Production changes: `src/node/miner.cpp`; tests: `src/test/miner_tests.cpp`. `CBlockTemplateEntry` keeps its existing small representation; snapshot accounting is local to construction.

The initial metadata-only backfill preserved the historical broken payload (raw-diff SHA256 `556182643ff288998a6fc1c97238a73f40268de0d5fec5f2fba2dc0c8bf1dedf`, pinned tree `1bffd0dba02e9440857f7abaa9fbeae7743dd2d9`). This correction intentionally changes source. `reference-metadata-provenance.json` retains all previous metadata/source evidence under `history` and records the new payload, metadata, exported commit and resulting tree independently. An isolated `git am --keep-non-patch` replay matches the tested pinned tree exactly.

## Algorithm and policy

Build a flat snapshot of entries with unique direct-parent counts and child-index vectors. Put only zero-parent entries into a priority queue. Repeatedly choose the highest individual modified-feerate **ready** entry, check minimum fee, its actual size/sigchecks against the current block, and transaction finality. Successful inclusion releases each direct-child dependency once; rejected parents leave their descendants blocked.

This fixes the old candidate's stale ancestor fees/resources and repeated ancestry expansion without retaining its ineffective static package-order mechanism. Multiple inputs from one parent are deduplicated by the mempool's direct-parent set. A shared ancestor is represented by its direct graph edges rather than counted once per path. Individual modified fees retain existing no-CPFP policy: an already-included ancestor cannot subsidize a free descendant. Coinbase accounting continues to use actual fees through `AddToBlock`.

The custom design differs from upstream's maintained fee-index scan, skipped-entry hash sets and backlog: it owns one flat graph and a ready heap, and always chooses the highest-priority currently ready transaction. This makes dependency scheduling explicit and independent of maintained ancestor-package indexes or child-container iteration order. It also allocates the whole graph up front. Modern ABC already has efficient direct-parent selection; **no asymptotic or measured speedup over modern ABC is claimed**.

For `n` entries and `m` unique dependency edges, each entry enters the heap at most once and each edge is released at most once. With expected constant-time salted hash lookups, the bound is O(n + m + n log n) time and O(n + m) memory. Describing an arbitrary DAG as O(n log n) while omitting its edges would be incomplete.

## Native before/after checks

Native macOS arm64, Apple Clang 21.0.0, CMake 4.4.4, Ninja 1.13.2; Qt, ZeroMQ and Chronik disabled. Existing production nodes, source workspaces, chain data, tags, and releases remain untouched.

The final test fixtures exercise:

- Paid parent/child inclusion with exactly one byte of block capacity spare.
- The same pair with exactly one sigcheck of remaining capacity.
- A ten-layer diamond graph, plus multiple inputs spending the same parent.
- Highest-feerate ready sibling selection when only one sibling fits.
- Exclusion of a high-fee child whose parent is nonfinal.
- Existing free-descendant and fee-prioritization behavior.

Against these **same final tests**, historical 01 fails eight assertions: free transaction and descendant inclusion, both byte-boundary assertions, sigcheck boundary, both sibling-capacity assertions, and inherited fee-delta grandchild inclusion. With corrected custom 01:

| Exact base | Application | Daemon/CLI/test build | `miner_tests` | Full `check-bitcoin` |
|---|---|---|---|---|
| Pinned `252182e957` | Pass; mailbox replay tree verified | Pass | 5 cases, 384 assertions pass | Pass |
| Declared prior current `8c67fe1e85` | Pass, tree `032102b4e5089170feac0caf37aee4bd22ed27cb` | Not separately run | Not separately run | Not separately run |
| Current master `1fb7db17c1` | Pass, tree `f39e005eb4e6e9934c38d00fed25c465ba800ddc` | Pass | 5 cases, 386 assertions pass | Pass |

Current master remained `1fb7db17c176cdea8a2c60d887891589382ee4e3` when rechecked at completion. The current native run applies **01 alone**, without candidate 04 or the independent pruning fixture. It does not inherit validation from combinations.

## Independent operation counts

The independent `check-ready-heap-assembly.py` adapter compiles the exact `addTxs` method with UBSan and counts operations; the method SHA256 is `9eb3af169f7790183233c4861f5011325c54100879004b7135969f9ab3c92c5f`. It asserts unique inclusion and parent-before-child order. This tests the algorithm through adapters, independently of the native node tests above.

| Shape | Entries | Edges | Edge walks | Finality checks | Hash calls | Heap comparisons |
|---|---:|---:|---:|---:|---:|---:|
| Chain | 10,000 | 9,999 | 9,999 | 10,000 | 19,999 | 0 |
| Layered diamonds | 10,003 | 20,002 | 20,002 | 10,003 | 30,005 | 5,001 |
| Wide fanout | 10,000 | 9,999 | 9,999 | 10,000 | 19,999 | 141,809 |
| Repeated-parent inputs | 10,000 | 9,999 | 9,999 | 10,000 | 19,999 | 0 |

These counts support the stated structural bound and show no ancestry-path expansion. They are not wall-clock benchmarks, public-network measurements, or an assertion that this is faster than modern ABC. The old failure-characterization harness now explicitly reads the superseded patch from Git history; it does not pretend to test this replacement.

## Reproduction and remaining scope

```sh
git checkout --detach 252182e957120652960c1f88ec96515c448b1204
git am --keep-non-patch /path/to/01-nlogn-block-construction.patch
cmake -S . -B build -GNinja -DBUILD_BITCOIN_QT=OFF -DBUILD_BITCOIN_ZMQ=OFF \
  -DBUILD_CHRONIK=OFF -DPython_EXECUTABLE=/opt/homebrew/bin/python3.13
ninja -C build -j6 bitcoind bitcoin-cli test_bitcoin check-bitcoin
build/src/test/test_bitcoin --run_test=miner_tests --color_output=no --report_level=short
```

Use current `BUILD_QT`/`BUILD_ZMQ` flag names on current ABC. This patch remains explicitly selectable as `block-construction`; enabling Chronik does not select it. Candidate 02's unchecked test compile defect and comment-only 03/10/11 remain separate issues. Candidate 04 retains its independent finalization evidence and dependencies.

Native logs: `/tmp/lotus-ecash01-final-regressions-old-{build,miner}.log`, `/tmp/lotus-ecash01-corrected-{dag-build,dag-miner,final-checks,current-build-checks,current-miner,operations}.log`. Machine-readable hashes, trees and results are in [evidence](evidence/ecash01-corrected-snapshot-2026-10-14.json).

No Linux build, Chronik-enabled build, mining mainnet replay, real-network synchronization, or wall-clock performance benchmark was performed for this eCash correction. Lotus's independently maintained patch and validation must establish its own results.
