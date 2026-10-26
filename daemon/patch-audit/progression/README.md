# Supervised canonical patch progression

`daemon/scripts/patch-progression.py` applies the ordered canonical mailboxes in `canonical-manifest.json`
with `git am`, starting at ABC `1fb7db17c176cdea8a2c60d887891589382ee4e3`.
The original 84-patch mapping in `split-manifest.json` remains historical
provenance. A later repaired tree must never be described as the original split
tree. Application, native compilation, correctness and timing are separate gates.

`contracts.json` distinguishes author-recorded rationale from source inference,
invariants, prerequisites, appropriate workloads and unresolved intent. Contracts
are keyed by stable `contract_id` values: historical split IDs or descriptive IDs
for newly separated purposes. Always join through `contract_ref` or `contract_id`,
never the current global number. `source_split_ids` retains historical lineage.
`canonical-manifest.json`, when present, records the current ordered filenames
and their original split ordinal/file/commit. `-N` always selects the current
canonical ordinal. Moving a prerequisite changes its suffix identities; it does
not silently turn a later mailbox into a duplicate or empty placeholder.

The persistent supervising agent diagnoses a failure, edits the source, folds
the change into the relevant candidate mailbox, records its rationale and
commits the outer candidate before resuming. There is no model API call inside
the deterministic runner and no automatic replacement agent per failure.

```sh
python3 daemon/scripts/patch-progression.py \
  --data /Users/shammah/repos/lotus-v2-optimizations/benchmark-results/canonical-progression \
  --source /private/tmp/wt-compile-repair \
  --build /private/tmp/build-compile-repair -N 0
```

For a fresh checkout, one command creates an isolated source clone at the pinned
ABC base, applies the same manifest, and runs the gates:

```sh
python3 daemon/scripts/patch-progression.py --data ./results \
  --source ./replay-source --build ./replay-build -N 0
```

An absent or empty source directory is initialized from the public Bitcoin ABC
repository. `--upstream <url-or-local-clone>` can explicitly select a clone source;
only the declared ABC base is used. Existing nonempty non-repositories are refused.
The benchmark imports constants from the exact replay source, without consulting
historical worktrees. Chronik uses installed Python 3.13 when available; its
selected interpreter path, binary hash and version are recorded.
Functional regressions use owned temporary nodes and ports based at 32000 (P2P)
and 35000 (RPC), with fresh chain caches per boundary attempt. They run sequentially
before the common benchmark nodes start.

`-N 20` reconstructs the clean base and applies patches 1 through 20, verifies
that all earlier gates have current successful evidence, then gates patch 20
and proceeds. It refuses a resume past a failed, missing or stale record.
`-N 0` can reuse successful records with exactly matching identities. Source
files with unchanged bytes recover their former mtimes after prefix replay;
the separate build directory and its Ninja object files are retained.

Each record identifies the ordered canonical mailbox prefix, replayed source
commit/tree, daemon binary, compiler versions, flags, repetitions and every
Python harness file. Required native/Python/functional gates are part of each
canonical prefix; changing a gate invalidates that boundary and its suffix.
Editorial contract changes alone do not invalidate measurements. Changing an earlier mailbox invalidates that boundary and
all downstream evidence. Original attempts and complete command logs remain
under timestamped attempt directories. A final failure packet identifies the
patch, original patch, source, working diff, failed commands/tests and resume
command. No timing runs after a correctness failure, and the first workload
failure stops repetitions and progression.

The native gates include mining, mempool and RPC plus every available native
suite touched by the prefix and suites explicitly required by contracts. Both
Bitcoin and Avalanche registrations are checked; missing suites fail closed.
Required Python wire-vector and functional tests also run before timing, alongside the disk-state
target when present, and Chronik compilation at patches changing Chronik.
Common legacy timing applies to Layer 1; frozen historical batch timing applies
where the original batch implementation or compatible V2 implementation exists.
V2 kernel counters are measured only when the native benchmark exists. Missing
metrics are unavailable, not inferred zeroes or synthetic upstream baselines.

This directory freezes the prior study's workload scripts and dependencies.
The historical adapters retain exact-work checks, fixed seeds, no automatic
batch splitting, fail-closed worker errors, and owned-node failure diagnostics.
Production data, original source checkouts, the immutable split review branch,
active patch directories and release assets are outside this workflow.

### Historical context and canonical patch ownership

`historical-context-inventory.json` records the user-supplied reference documents
and read-only worktree identities, including dirty-diff hashes. Section-specific
references and SHA256 hashes live in each patch's `contracts.json` entry and are
included in failure packets. Historical benchmark claims are authorial context,
not reproduced measurements for this candidate. In particular, the MDBX report
measures fresh indexing and explicit reindexing; it does not prove RocksDB key
migration. The reference implementation moves legacy files and opens an empty
index. The candidate currently refuses legacy RocksDB data without mutation;
automatic key migration remains unsupported.

One purposeful change is the canonical patch boundary. Fold a discovered defect
and its regression tests into the first responsible logical patch; do not retain
a later fixup mailbox merely to preserve old patch counts or intermediate trees.
The repair ledger preserves the before/after source identities and failed evidence.
Historical splits and consolidation maps explain provenance, not final granularity.
When removing artificial catch-up/removal churn, preserve an explicit mapping from
all original contributions to their final canonical owners and invalidate the
changed prefix and every later result.

The end product is one ordered ABC-to-eCash-to-V2 stack with global patch numbers.
Layer directory names do not select independent branches. The V2 consensus
boundary separates incomparable benchmark metrics in downstream graphs.

Generate the current global graph, per-metric raw/baseline-percent rows, complete
JSON and full-precision CSV (including n/min/max) with:

```sh
python3 daemon/scripts/report-patch-progression.py --data <progression-data>
```

The report rejects stale prefix/harness identities and leaves incomplete patches
visible without performance points. `refresh-progression-manifest.py --data
<progression-data>` records actual replay parents/trees in the versioned global
manifest; unknown canonical source identities remain null. Historical split
`sha/tree/parent` fields remain provenance only.

The shared eCash layer preserves its legacy transaction-root header commitment;
it has no V2 UTXO/Merklix state commitment. Full eCash snapblock/template features
may therefore have distinct V2 capability-upgrade patches which use V2 header
commitments. Preserve those purposeful adaptations and establish their exact
validation/trust conditions independently. Root equality or cache membership by
itself is never evidence of script or UTXO validity.

The user retained BLAKE3 for Lotus V2. Shared eCash identifiers, including internal
batch IDs, use SHA256/SHA256d; BLAKE3 vendor and adapters remain in V2. Historical
performance reports are context, not measurements of this candidate. BLAKE3's
internal chunk tree is not the Lotus Merklix tree and is not a rationale for this
choice. No additional hash-selection study gates the progression.
