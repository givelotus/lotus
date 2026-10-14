# eCash block-construction candidate audit

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
