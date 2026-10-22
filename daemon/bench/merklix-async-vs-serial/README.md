# Merklix TransactionSubtreeA: async versus serial

**Measured:** 448 samples completed on 2026-10-22; all reference and focused
correctness gates passed. See the [report](../../../benchmark-results/merklix-async-vs-serial-20261022/REPORT.md)
for all workloads, confidence intervals, resource costs and limitations.

A is byte-identical historical production `commitment.cpp` at commit
`657edc0133cac8d54c5570506dad57bf10e300b5`; B disables only its async condition.
Both preserve span partitioning, tagged hashing, inputs, compiler and allocator.
Async launches the left child when depth <4, entries >=64, and both partitions
are nonempty; the caller processes the right child and joins the future.
C substitutes a fixed min(15, hardware concurrency) worker pool. D substitutes
a growing persistent pool capped by `LOTUS_POOL_MAX` (default 4×hardware threads).
The original A/B question remains distinct from experimental pool evaluation.
No daemon change was adopted.

Source inputs and SHA256 provenance are preserved in the canonical report's
`source/SOURCE.json`. The historical source pin is intentional; current Grok
progression source is a separate identity. Set `SRC` to this immutable export
when rebuilding. `make-variants.sh` verifies every exported source hash and pin,
or accepts a clean Git checkout of that exact historical commit.

The harness times full BuildTxSubtreeA calls, including allocation, partition,
hash, dispatch, join and future destruction. Fixture/reference creation and three
warm-up roots are excluded. All timed roots compare against an independent
recursive vector reference. The matrix covers 64/1,000/5,000/100,000/500,000 random
and four-prefix fixtures, plus four and sixteen concurrent callers at 5,000 and
100,000 random entries. Eight rotated orderings, at least 1.5 seconds/sample,
one process/sample, and a 45-second timeout produce 448 observations.

Raw JSON includes wall/CPU/root, process peak RSS, successful pthread starts,
first production-root wall/CPU (lazy pool construction included), worker starts
before timing and subprocess wall through process exit. RSS includes reference
and fixture allocations. Subprocess wall also includes fixture/reference/warm-up;
it does not isolate pool teardown. Concurrent wall/root is throughput-equivalent
cost; `latency_ms_per_root` is caller-count multiplication, not sampled latency.
Thread counters are gated against exact expected caller/A/B/C counts.

D supports move-only captures and movable object results; void work uses Post,
which intentionally discards exceptions. Get runs an unstarted job inline or
waits for a running job and rethrows its exception. Destroying or overwriting a
Future joins its previous job. The pool outlives all Futures. Stop external
submitters before destruction; draining jobs may still submit descendants.
Jobs may block only through acyclic Future dependencies, and must not destroy
the pool. Workers start lazily and never shrink. Shutdown freezes worker growth
before joining; initial thread-start failure falls back to inline execution.
This prototype is not validated for arbitrary blocking dependency graphs.
CCheckQueue, validation caches and signature pools remain outside this study.

Reproduce only in a coordinated host window:

```sh
# See COMMANDS.txt in the report directory for compiler and sanitizer gates.
SRC="$PWD/benchmark-results/merklix-async-vs-serial-20261022/source" \
  daemon/bench/merklix-async-vs-serial/make-variants.sh
LOTUS_POOL_MAX=72 python3 daemon/bench/merklix-async-vs-serial/correctness-smoke.py NEW_RESULT_DIR
LOTUS_POOL_MAX=72 python3 daemon/bench/merklix-async-vs-serial/run-matrix.py NEW_RESULT_DIR 8 1.5
python3 daemon/bench/merklix-async-vs-serial/analyze.py NEW_RESULT_DIR
```

Create NEW_RESULT_DIR first; the smoke and matrix refuse existing raw files.
The measured host had 18 logical CPUs, AppleClang 21 and the system allocator.
An unrelated existing one-core explore job was preserved; this was not an idle
host. The full matrix took about 12.5 minutes and is a component study, not TPS.

## Generic cooperative executor follow-up E

The [E model](COOPERATIVE-MODEL.md) implements a fixed hardware-sized callback
budget, shared external-helper permits, bounded admission/queue backpressure,
cooperative joining and quiescent shutdown. Focused and ThreadSanitizer tests
pass. The separate [E report](../../../benchmark-results/merklix-cooperative-pool-e-20261022/REPORT.md)
contains 448 fresh ACDE Merklix samples and 96 synthetic mixed-client samples.
E stayed within18 callback slots with zero timed worker creation, but small-job
scheduler overhead regressed and performance improvements were workload-specific.
It remains a reusable prototype, with no daemon adoption. Original D results and
header are immutable; use `make-cooperative-variants.sh`/`build-e` for this lane.
