# Benchmark execution order

The user has paused the benchmark sweep while additional patches and workstreams arrive. Continue repair builds and correctness checks; do not start a benchmark sweep.

When benchmarking resumes, use one repetition initially. Measure the upstream baseline and final eCash and V2 endpoints first. Within each layer, enqueue the midpoint of its unmeasured interval, then process the left and right subintervals breadth first. Continue until every eligible patch boundary is measured. Pre-register the schedule against an immutable canonical manifest; record unavailable metrics and grouped prerequisites explicitly.

This is a coverage schedule, not a monotonicity-based regression bisect: performance may rise and fall repeatedly. Do not discard intervals because their endpoints match. If an early interval shows a large change, it can be prioritized while retaining all remaining work.

Keep legacy version2 and native version7 workloads as separate comparable tracks. Each point records exact commit/tree, canonical prefix, workload, environment and harness identity. Reuse a point only when those identities match. Render graphs and tables in patch order, independently of execution order. Additions or repairs invalidate affected prefixes; never attach old results to a renumbered patch by ordinal alone.

Endpoint comparisons are preliminary single-run observations. They do not attribute a speedup to any one patch; that requires the completed adjacent measurements. Jumping between revisions can rebuild more objects than a sequential sweep, which is an accepted cost for earlier overall results.

## Automated scheduler

`daemon/scripts/schedule-patch-benchmarks.py` generates the schedule deterministically from the canonical manifest. By default it only previews/saves a plan:

```sh
python3 daemon/scripts/schedule-patch-benchmarks.py --plan /path/to/schedule.json
```

When the sweep is explicitly resumed, add `--execute --data <results> --source <dedicated-replay-checkout> --build <incremental-build>` to that command. The source directory is a disposable benchmark clone, not the consolidated development checkout. `--limit 3` visits just the three endpoint points. Omit the limit to fill every point in the schedule. Defaults are one repetition and two build jobs.

Each point invokes `patch-progression.py --point N`. It replays the exact patch prefix, verifies every intermediate canonical tree, then builds, tests and benchmarks only N. Earlier unmeasured points receive no fabricated test/benchmark successes. Matching results are reused by the runner's prefix/harness/source-tree checks; the first failure stops the scheduler and writes its normal failure packet. Re-running the same command resumes through those identity checks. A changed candidate or runner requires a new schedule file. This scheduler never invokes an LLM.

Verification includes complete unique coverage across uneven/empty layer intervals, endpoint-first breadth order, stop-on-failure, changed-candidate rejection, and a real two-patch Git replay without preceding results. The replay test deliberately fails configuration to verify the failure packet and sparse resume command; it does not run daemon benchmarks. Full daemon execution against the final repaired stack remains pending, and the sweep remains held.
