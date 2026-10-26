# Merklix async versus serial: completed component study

**448/448 timed samples and all correctness gates passed.** Current `std::async`
helps one-caller roots from 1,000 through 500,000 entries in this matrix, but
hurts 64-entry roots and 5,000-entry roots with sixteen concurrent callers.
Persistent pools reduce dispatch cost in some workloads. Generic growing pool D
has no consistent advantage over fixed pool C, and reached its 72-worker cap.
No production code or daemon configuration was changed or adopted.

| change | workload | before ms/root | after ms/root | adoption status | source report |
|---|---|---:|---:|---|---|
| A async → B serial | 64 random, one caller | 0.0254 | 0.0175 | measured only | [full matrix](confidence-table.md) |
| A async → B serial | 500,000 random, one caller | 73.5973 | 208.2635 | retain async for this measured workload | [full matrix](confidence-table.md) |
| A async → B serial | 5,000 random, sixteen callers | 0.1991 | 0.1693 | measured only; no threshold change | [full matrix](confidence-table.md) |
| C fixed pool → D growing pool | 100,000 random, four callers | 4.2140 | 4.9534 | D not adopted | [full matrix](confidence-table.md) |
| C fixed pool → D growing pool | 100,000 random, sixteen callers | 3.3156 | 3.1818 | D not adopted | [full matrix](confidence-table.md) |

All values are aggregate elapsed milliseconds per completed component root;
for concurrent callers this is throughput-equivalent cost, not measured request
latency. The raw `latency_ms_per_root` field multiplies this by caller count;
it is an approximation, not a directly sampled latency distribution. These are
not transaction admission, RPC acceptance, block propagation, all-peer completion
or daemon TPS measurements. Speedups from unrelated comparisons are not added.

## Controlled comparison

A is the exact historical `commitment.cpp` at source commit
`657edc0133cac8d54c5570506dad57bf10e300b5`, tree
`9a06a5a1c13780ae91390c4407ad90fefd35bbea`. B differs by one line disabling the
async branch. Both keep identical in-place pointer-span partitioning, tagged
BLAKE3, inputs, compiler, allocator and timed lifecycle. A launches the left child
at depth <4 with at least 64 entries and two nonempty children, processes the right
child on the caller, and joins the future. A therefore creates one thread/root
for 64 entries, fifteen for larger random fixtures, and three for larger prefix
fixtures; observed counts match those identities exactly.

C replaces only dispatch with a fixed15-worker reclaim-or-wait pool. D replaces
only dispatch with the generic growing pool, explicitly capped at 72 workers
(default4 × 18 logical CPUs). Both reuse workers across roots within each sample
process. Their framework investigation remains separate from the simple A/B
causal result. The pool header and all harness sources are in tooling commit
`b8ca1caa`; the source export includes exact SHA256 values in
[source/SOURCE.json](source/SOURCE.json). Current Grok progression source is a
different historical identity and was neither changed nor used for this study.

Fixtures use deterministic xorshift seed 234567891, sizes64/1,000/5,000/100,000/
500,000, random identities and four concentrated prefixes (LSB-first splitting
at depths 0–1, then long one-sided prefixes). Concurrent cases use four and sixteen
callers at 5,000 and100,000 random entries. Each root is compared to an independent
recursive vector reference; every variant and repetition agrees exactly.

Common AppleClang21.0.0 `-std=c++20 -O3 -DNDEBUG -pthread`, system allocator, same
harness/tagged-hash objects and same vendored NEON BLAKE3 archive. Each case uses
eight rotated variant orders, one process per sample, at least 1.5 seconds of timed
work after three production-root warm-ups. All internal root allocation,
partitioning, hashing, dispatch, thread creation, joins and future destruction
are timed. Caller creation, fixture/reference construction and warm-up are outside
the timed region. Each subprocess has a45-second timeout; none failed or timed out.
The run lasted19:23:54Z–19:36:23.510Z on 2026-10-22, about748.4 seconds of subprocess
wall time and682.5 seconds summed measured regions. All owned processes drained.

## Ratios and uncertainty

[confidence-table.md](confidence-table.md) gives all fourteen workloads, A/B/C/D
medians, and A/B, D/B, D/C time ratios with95% bootstrap intervals; values below1
favor the numerator. Each bootstrap resamples the eight repetition blocks
jointly across variants 10,000 times, fixed seed 20261022. These intervals describe
within-run variation under this host condition, not uncertainty across machines,
days or daemon workloads. [summary.md](summary.md) includes CPU cost, variability,
whole-process peak RSS and thread counts. [analysis.json](analysis.json) contains
additional ratios, first-root costs, process wall time and D worker growth.

A/B was0.353 [0.351,0.356] at 500,000 random entries, but1.451 [1.432,1.686] at 64
random entries and1.176 [1.141,1.211] at 5,000 random entries with sixteen callers.
D/C was1.175 [1.140,1.224] at 100,000 entries/four callers and0.960 [0.945,0.968]
at 100,000 entries/sixteen callers. D/C at 500,000 random entries was1.000
[0.975,1.015]. A generic growing pool is not justified as a uniform replacement
by this evidence.

The reserved window excluded other study builds/benchmarks, but an unrelated
`explore` process82695 consumed about one CPU core in the initial snapshot and
was preserved. This was not an idle host. Per-sample load averages are retained;
there is no continuous attribution of other applications' CPU activity. Matrix
rotation limits systematic ordering bias but cannot eliminate host interference.

## Resources and lifecycle

CPU milliseconds/root at 500,000 random entries were A 248.515/B 208.212/C 248.790/
D 248.508: reduced wall time consumes more aggregate CPU. Process peak RSS there
was approximately57/56/56/56MB. At500,000 prefix entries it reached101/101/106/
104MB. Peak RSS includes reference, fixture and warm-up allocations, not just
incremental production-root memory; thread virtual stack reservations are not
measured. Raw observations are in [raw.jsonl](raw.jsonl).

C created15 workers during warm-up and zero during timing. D retained2–3 workers
for a single64-entry root workload,15–21 for 5,000 random entries/one caller,
37–50 for 5,000/four callers,42–62 for 100,000/four callers, and72 for 100,000/
sixteen callers. In that last case D created54–57 workers during the timed phase.
These are exact retained-worker peaks inferred from successful thread starts:
D never shrinks; caller threads are recorded separately. Thus three serial
warm-up roots do not establish a fully grown pool for concurrent workloads.
Growth costs are included in D's timed data. A's thread/root counts show creation
volume; its peak simultaneously live thread count was not sampled.

The first production-root wall/CPU fields include lazy pool startup. They follow
reference construction, so they are not cache-cold measurements. For64 random
entries, first-root median wall milliseconds were A 0.0408/B 0.0209/C 0.1099/D 0.0421,
versus steady medians0.0254/0.0175/0.0155/0.0153. Subprocess wall time includes
process startup, fixture/reference/warm-up and pool teardown; these components
cannot be isolated by subtracting that total. This records full process lifecycle
while preserving the requested dispatch-only steady comparison.

## Correctness and preservation

The focused pool gate passes with assertions enabled, including move-only
captures/results, exception propagation, consumed Get errors, nested trees at
caps 1/2/4, overwritten/destroyed Future joining, caps and shutdown descendant
draining. The same gate passes ThreadSanitizer without diagnostics. Fifty-six
short A/B/C/D workload smokes pass exact reference/cross-variant roots plus
thread-counter assertions. All448 measured samples also check every computed
root. This is component correctness coverage, not whole-daemon race validation.

Before timing, review fixed the C generator argument and include placement, D
shutdown growth/vector mutation and Future move-assignment lifetime, and the
macOS thread counter (the original dyld interpose section did not count calls
from its own image). The first smoke file with broken counters is retained under
an explicitly superseded filename and excluded from the timing dataset. D's
contract restricts Async to movable object results; Post discards exceptions;
the pool outlives Futures; external submitters stop before destruction; draining
jobs may submit descendants; jobs use acyclic Future dependencies. Arbitrary
blocking dependency graphs and broad production reuse are not validated.

[COMMANDS.txt](COMMANDS.txt), [HASHES.txt](HASHES.txt), [environment.json](environment.json),
[correctness-smoke.log](correctness-smoke.log) and [LOCAL-ARTIFACTS.sha256](LOCAL-ARTIFACTS.sha256)
record commands, identities and gates. Exact build products/test binaries/debug
symbols are preserved in the local canonical archive
`daemon/.local-artifact-archive/merklix-async-vs-serial-20261022/build-and-tests.tar.gz`;
archive and binary hashes are recorded, not claimed remotely backed up. Source,
raw results and small evidence are committed. No daemon source, validation
cache, CCheckQueue, Grok source/build/mailbox, production node or release changed.

Source/results delivery commit: `49ffe8d4`; no remote push was performed.
A verified incremental recovery bundle preserves that commit and its ancestry
back to prerequisite `6c85f365` at
`daemon/.local-artifact-archive/merklix-async-vs-serial-20261022/source-through-49ffe8d4.bundle`.
Its SHA256 is recorded with the local artifact hashes. The source snapshot and
generated diff artifacts intentionally preserve upstream bytes, including
inherited whitespace. All variants use the same successful-pthread-start counter;
its per-start bookkeeping is included in measured CPU and wall costs.
