# eCash block-construction candidate audit

Historical evidence: this report's 01 failure results refer to the superseded static-package payload (raw SHA256 `556182643ff288998a6fc1c97238a73f40268de0d5fec5f2fba2dc0c8bf1dedf`). Current eCash 01 retains a corrected custom snapshot/ready-heap assembler; see [new source and native evidence](ecash01-corrected-snapshot-assembler.md). Other candidate results below retain their recorded revision scope.

Historical audit of the original broken payload. The upstream-restoration
section below records a superseded mistake, not the final requested repair.
The corrected custom scheduler is documented at the end of this report.

`patches/ecash/01-nlogn-block-construction.patch` is an unvalidated historical
candidate, not a demonstrated optimization. It changes only `src/node/miner.cpp`
and `src/node/miner.h`; it supplies no tests. Absence of test changes is not
proof that existing tests passed. No retained test result was found alongside
the patch. Do not promote it into a maintained, release-ready feature without
repair and upstream integration tests.

Audited payload SHA256:
`556182643ff288998a6fc1c97238a73f40268de0d5fec5f2fba2dc0c8bf1dedf`.
The declared base is Bitcoin ABC
`252182e957120652960c1f88ec96515c448b1204`.
The exact patch applies on this base, and native daemon/test-binary builds
succeed. Running the existing `miner_tests` suite fails three assertions: the
free transaction and its descendant are incorrectly selected
(`src/test/miner_tests.cpp:235` and `:236`), and a block contains seven
transactions where the upstream fixture expects six (`:744`). These are native
integration failures, not merely deductions from the harness. Evidence log:
`/tmp/lotus-ecash-candidate01-miner-tests.log`; support-audit checkout:
`/tmp/lotus-ecash-candidate-build`. Candidate 02 was removed for this run;
its independent test-compilation failure must not obscure candidate 01's
behavioral failure. The support audit records broader application/build results.

The same entry struct and `addTxs` method are also present, byte for byte, in
the final Lotus V1 rebase source at `a055e77a25`. Verify this explicitly with:

```sh
python3 daemon/tests/check-ecash-block-assembly.py --source-tree /tmp/rebase-latest-abc
```

The findings therefore affect V1 mining templates too. V1's existing fixture
was adjusted to accept free descendants, so its passing suite did not detect
the resource-accounting regression. Successful chain replay does not exercise
block-template construction at a constrained size. Repair and targeted native
V1 tests are required before treating its mining implementation as reviewed.

## Reproduce the failures

From the repository root, run:

```sh
python3 daemon/tests/check-ecash-block-assembly.py
```

This compiles the candidate's actual `CBlockTemplateEntry` definition and
`BlockAssembler::addTxs` method, extracted verbatim from its unified diff, into
a small C++17 harness with undefined-behavior sanitizer enabled. It requires
Python 3 and a C++ compiler, and uses a disposable temporary directory.
The adapters supply a topologically ordered mempool, integer fee-rate rounding,
and the pinned `BlockFitter` size/sigcheck inequalities and coinbase reservation.
Transaction identifiers are integers; inputs model parent identifiers rather
than full UTXOs. This is an algorithm-level executable check, not a daemon,
script-validation, or consensus test. Its zero exit status means the known
failures were reproduced; it does **not** certify the patch.

Reproduced failures:

| Case | Observed candidate behavior | Consequence |
| --- | --- | --- |
| Paid parent and paid child, 200 bytes each; available size 401 bytes | Includes only the parent although the child fits | Already included parent is charged again by the child's stale package size |
| Paid parent and paid child, one sigcheck each; available sigchecks 3 | Includes only the parent although the child fits | Already included parent's sigchecks are charged again |
| Zero-fee parent and high-fee child | Includes neither transaction despite a paying combined package | Advertised package scheduling does not implement child-pays-for-parent |
| High-fee parent and zero-fee child | Includes both transactions | Previously collected ancestor fees subsidize a free descendant; differs from pinned upstream policy |
| Diamond: A → B, A → C, B + C → D | D's package charges five transactions for four unique transactions | Size, fees, and sigchecks double-count A |

The independent-transaction fee/size control passes. A 17-transaction chain
with two inputs spending distinct outputs of each parent also completes with
17 contextual checks under the complete candidate. This matters for the
complexity qualification below.

## Scheduling and complexity

`maxPackageFeeRate` is initialized to each transaction's own fee rate.
`AccountForParent` updates it to the maximum of that value and each parent's
package rate. A weighted average of those rates cannot exceed their maximum,
so its `FeeRate() > maxPackageFeeRate` condition does not reset the order to
zero. With the documented topological `entry_id` invariant, children retain a
strictly greater depth than their parents. The proposed package-priority tier
therefore does not work as described. A low-fee parent is marked invalid before
a high-fee child can rescue it. Pinned upstream also excludes such a package;
this particular result is a missing claimed capability, not a regression
against upstream's existing child-pays-for-parent behavior.

The DFS has no per-traversal visited set. In isolation, traversing a chain with
two inputs per parent expands to `2^(d+1)-1` stack visits for depth d. However,
the complete candidate's depth ordering normally processes those parents first;
the reproduced 17-transaction case performs only 17 contextual checks. An
exponential complete-assembler execution has **not** been established. Repairing
the scheduling logic alone could expose this latent traversal problem, so a
future implementation needs deduplication and a repeated-parent regression test.

The description of the replaced implementation is also inaccurate for the
pinned base. Its existing `addTxs` iterates the maintained `modified_feerate`
index, uses `missingParentCount`, and decrements direct child counts as parents
are included. Its own comment explicitly explains avoiding quadratic dependency
checks. There is no ancestor-score-update loop in that replaced method.
Ignoring existing index maintenance, its traversal is expected O(n + m) under
normal hash-table assumptions, with n transactions and m dependency edges.
The candidate adds an O(n log n) sort. Its claimed speedup requires measurements
against the actual pinned implementation, not a different historical algorithm.

## Required before promotion

Keep the payload available as a rejected candidate rather than silently changing
mining policy in a metadata or release cleanup. Any replacement should specify
whether package fee selection is intended, account only for unique unselected
ancestors, recompute resource/fee requirements after inclusion, deduplicate DFS
work, and test normal chains, diamonds, repeated parent inputs, exact resource
boundaries, fee prioritization, and invalid/finalized transactions. Tests must
run against both the exact maintained base and the proposed updated upstream.
This audit does not modify the published Lotus V1 patch payload or running
nodes. A V1 repair must be a separate, explicit source change with native
regression evidence, not an incidental metadata rewrite.

## Superseded temporary Lotus V1 upstream restoration

A separate source correction restores the already retained upstream assembler,
which uses the maintained fee-rate index and direct-parent counters. It removes
the experimental package accumulator, DFS, template fields, and the misleading
complexity description. Existing fee/prioritisation fixtures again reject free
transactions subsidized only by previously selected ancestors. A new native
mainnet-fixture test gives a paid parent and child precisely one byte of spare
block capacity; both must enter the template.

Source provenance (before folding into the maintained series):

- Parent: `a055e77a25c1664d63080cec4d8409d3a63bc190`.
- Repair commit: `e21d07c27a2235667d1450a003e883b246ed5aa3`.
- Resulting source tree: `e0d4f9c0219739b6774864858c582a8144a443d9`.
- Isolated clone: `/tmp/lotus-v1-assembly-repair`.
- Reviewable mail patch: `/tmp/lotus-v1-assembly-repair.patch`.

The same final native miner tests fail **five** assertions on the uncorrected
source: free transaction inclusion, its descendant, constrained block count
(two transactions including coinbase instead of three), missing fitting child,
and inherited fee-delta grandchild inclusion (seven transactions instead of six).
After correction, the complete `miner_tests` suite passes and all **151**
`check-bitcoin` targets pass. `lotusd`, `lotus-cli`, and `test_lotus` build.

This focused C++ validation configures **Chronik OFF** in the disposable clone;
it does not replace the normal Chronik-enabled release checks. Rust/Chronik
sources are unchanged by this correction. Original workspaces, running nodes,
chain data, tags, and published assets were not modified by this audit.
The patch-maintenance follow-up folds the correction into patch 246, preserves
the 153-entry series, and compares the resulting complete tree with the tree
above. The earlier V1 test/replay results describe the pre-correction tree;
updated release evidence must identify the corrected tree explicitly.

Evidence logs:

- `/tmp/lotus-v1-assembly-regression-before.log`
- `/tmp/lotus-v1-assembly-regression-after.log`
- `/tmp/lotus-v1-assembly-repair-build-after.log`
- `/tmp/lotus-v1-assembly-repair-cpp-checks.log`

Reproduce after applying the reviewed mail patch to its recorded parent:

```sh
cmake -S . -B build -GNinja \
  -DBUILD_BITCOIN_QT=OFF -DBUILD_BITCOIN_ZMQ=OFF \
  -DENABLE_UPNP=OFF -DENABLE_NATPMP=OFF -DBUILD_CHRONIK=OFF \
  -DPython_EXECUTABLE=/opt/homebrew/bin/python3.13 -DRust_TOOLCHAIN=1.93.0
ninja -C build -j16 lotusd lotus-cli test_lotus
(cd build && ./src/test/test_lotus --run_test=miner_tests --color_output=no)
ninja -C build -j16 check-bitcoin
```

The Python path above records the native macOS run; use an installed compatible
Python interpreter on another host.

## Correct custom scheduler, maintained in its own patches

The user's requirement is to fix the custom algorithm in Lotus patch `001` and
eCash patch `01` independently. The temporary upstream restoration above was
the wrong requested fix and is superseded. Lotus patch `246` no longer reverses
the custom scheduler. Patch `001` now contains both the implementation and its
native regression fixtures; `077` receives context-only adaptation and `246`
keeps Lotus-specific fixture/API adaptations.

The corrected algorithm builds a flat dependency snapshot with one salted
TxId lookup index and a max heap of dependency-ready transactions. It uses the
existing deterministic modified-fee comparator. Only successful inclusion
releases children. Unique direct-parent sets prevent diamond/repeated-input
double counting. Each transaction's own fee rate, resources and contextual
validity are checked against current block state, so already included ancestor
resources/fees/deltas cannot leak into descendants. This retains individual-fee
mining policy; it does not introduce CPFP. Unlike upstream's maintained
fee-index/backlog traversal, this is a new snapshot/heap implementation.
Expected time is O(n + m + n log n), space O(n + m). There is no demonstrated
speedup over modern upstream.

Corrected Lotus source:

- Base: `8c67fe1e85a602204a2ce65aa3b643469c2c3a1d`.
- Exactly 153 commits, tip `0b7939e926b8353ad09d8edc47f355ddacc30502`.
- Final tree: `73e9db8356d5f9e617f40d4d9228209e117b08f0`.
- Source/build: `/tmp/lotus-v1-custom-assembly`.
- Historical failing source with identical final fixtures:
  `e6408272a2df57a47314c50f31a66d3c55709376` in
  `/tmp/lotus-v1-assembly-repair` (test-only, not a maintained candidate).

The historical algorithm fails **eight** native assertions with the final
fixtures; the corrected custom scheduler passes. Coverage includes exact byte
and sigcheck boundaries, ten-layer shared-ancestor diamonds, repeated parent
inputs, highest-fee ready siblings competing for limited capacity, nonfinal
parents, and existing free-descendant/prioritisation expectations. Full normal
**Chronik-enabled** daemon/CLI/test builds and Rust tests/Clippy pass, as do all
**156** C++ check targets. Clean `git am` replay verifies every one of the 153
intermediate trees and mail metadata hashes. Original authors/dates and
unchanged messages are preserved; changed rationale is explicitly new text.

Independent operation counts compile the actual method with test adapters:

```sh
python3 daemon/tests/check-ready-heap-assembly.py --source-tree /tmp/lotus-v1-custom-assembly
```

| Shape | n | m | Edge walks | Context checks | Heap comparisons |
| --- | ---: | ---: | ---: | ---: | ---: |
| Chain | 10,000 | 9,999 | 9,999 | 10,000 | 0 |
| Layered diamonds | 10,003 | 20,002 | 20,002 | 10,003 | 5,001 |
| Wide fanout | 10,000 | 9,999 | 9,999 | 10,000 | 141,809 |
| Repeated-parent inputs | 10,000 | 9,999 | 9,999 | 10,000 | 0 |

Assertions also verify unique selection and parents-before-children order.
This supplies reproducible operation evidence, not a consensus test or
wall-clock benchmark. Native integration tests above supply separate behavior
evidence.

Logs are `/tmp/lotus-v1-custom-assembly-miner-tests-before.log`,
`/tmp/lotus-v1-custom-assembly-miner-tests.log`,
`/tmp/lotus-v1-custom-assembly-build-final.log`,
`/tmp/lotus-v1-custom-assembly-cpp-checks.log`,
`/tmp/lotus-v1-custom-series-verify.log`, and
`/tmp/lotus-v1-custom-series-operations.log`.

A fresh corrected-tree node replayed mainnet to **1,401,052** with
`initialblockdownload=false`, then accepted fresh blocks beyond the copied block
files. It uses `/tmp/lotus-v1-custom-assembly-mainnet-20261014` (RPC 12604,
Chronik 19331). Chronik/RPC parity passes at **11 sampled heights and 15
coinbase/non-coinbase transactions**: exact 160-byte headers, merkleized TxIds,
raw disk bytes and transaction sizes. `verifychain 4 1000` returns true;
`getchaintips` has only the active tip, with no parked branch. Read-only
`getblocktemplate` succeeds for height 1,401,053. Its live mempool was empty;
dependent-transaction selection is covered by the separate native fixtures.

Mainnet evidence is in `/tmp/lotus-v1-custom-assembly-chronik-parity.log`,
`/tmp/lotus-v1-custom-assembly-verifychain.log`,
`/tmp/lotus-v1-custom-assembly-chaininfo.json`,
`/tmp/lotus-v1-custom-assembly-chaintips.json`, and
`/tmp/lotus-v1-custom-assembly-blocktemplate.json`.

Existing working nodes, original workspaces, original chain data, tags, and
published releases remain untouched. These source checks support review;
publication still follows the normal candidate/artifact verification path.
