# Generic bounded cooperative pool E

**The reusable executor direction is implemented and component-validated.** E
uses a fixed hardware-sized worker set, shares callback CPU permits with external
helpers, reclaims or helps queued jobs at joins, bounds queued/accepted work, and
never grows threads on Get. All 544 accepted timed samples passed reference checks;
focused concurrency/lifetime tests and ThreadSanitizer also passed.

This candidate solves D's worker-growth problem, but its current scheduler adds
substantial overhead for small/lightly loaded work. No production integration or
uniform performance improvement is claimed. The original A/B/C/D dataset and D
header are unchanged.

| change | workload | before ms/root | after ms/root | adoption status | source |
|---|---|---:|---:|---|---|
| A async → E bounded pool | Merklix 64 random, one caller | 0.02512 | 0.06959 | prototype; regression | [Merklix table](merklix-summary.md) |
| D growing → E bounded pool | Merklix 500k random, one caller | 64.12288 | 64.66574 | prototype; near parity | [Merklix table](merklix-summary.md) |
| D growing → E bounded pool | Merklix 100k random, sixteen callers | 2.89072 | 3.26999 | prototype; regression | [Merklix table](merklix-summary.md) |
| independent async → shared E | three synthetic clients, 4096 rounds | 0.04002 | 0.08363 | prototype; regression | [mixed table](mixed-summary.md) |
| independent async → shared E | twenty-four synthetic clients, 4096 rounds | 0.05169 | 0.03924 | prototype; improvement | [mixed table](mixed-summary.md) |
| independent async → shared E | twenty-four synthetic clients, 16384 rounds | 0.04931 | 0.05066 | prototype; regression | [mixed table](mixed-summary.md) |

Values are aggregate elapsed milliseconds per completed component root. Concurrent
values describe throughput-equivalent cost, not request latency. These are neither
production subsystem benchmarks nor daemon TPS, RPC acceptance or all-peer results.

## Model and limits

The full [model and API contract](../../../daemon/bench/merklix-async-vs-serial/COOPERATIVE-MODEL.md)
is part of the source delivery. On this 18-logical-CPU host, E created exactly 18
workers before timing, retained18, never created a timed worker, and never exceeded
18 simultaneously executing callbacks, including external Get helpers. D remained
at its original explicit72-worker cap in this new comparison.

Get reclaims its own queued task, otherwise executes other ready FIFO tasks before
waiting. An internally waiting callback releases its CPU permit and reacquires it
before resuming. FIFO dispatch has own-job and inline-backpressure exceptions;
there is no strict subsystem latency/fairness guarantee under infinite production.

Ready queue capacity is72. External producers backpressure before the accepted-job
limit 1224; internal producers run inline at queue pressure and fail explicitly at
the hard accepted-job cap rather than deadlocking with a permit held. Completed
Futures and externally retained arguments are application memory, not queue memory.
Post intentionally discards task exceptions; Async/Get propagates them.

This supports structured same-pool descendant joins, not arbitrary cyclic,
ancestor, cross-root or cross-pool future graphs. External blocking I/O belongs
elsewhere. Helping is reentrant: hold no application lock across submission, Get,
Future assignment or Future destruction. Both logical and synchronous callback
nesting are limited to 64, with explicit length_error on further submission. It
uses no fibers and does not promise unbounded recursion. The pool outlives Futures;
single-owner Shutdown closes external admission, drains accepted descendants and
joins quiescent workers. Callbacks cannot shut down their own pool.

## Correctness and resource observations

Focused assertions passed at caps 1/2/18, queuecapacity 1, concurrent nested roots,
move-only captures/results, exceptions, consumed Get, overwritten/destroyed Future
joining, Post errors, shutdown descendant draining and closed admission. A logical
10,000-dependency chain fails explicitly at the supported depth bound; it does not
rely on a timeout crash. Every concurrent client completes its asserted workload.
A detached callable-destructor reentry regression passes. The same tests pass
ThreadSanitizer without diagnostics; logs retain worker, active, queue, unfinished,
callback-depth and helping/backpressure counters.

All56 Merklix ACDE smokes and12 mixed A/E smokes pass exact outputs and thread/
budget assertions. All448 Merklix plus96 mixed timed samples check every root.
Observed E queue peak was68/72 on Merklix and36/72 on mixed work. Actual callback
nesting peaked below64 in timing. Queuecapacity1 focused tests exercised thousands
of inline-backpressure events, while the timed workloads did not fill the default
queue. Tests observed other-job helping; raw samples distinguish it from own-task
reclamation. Every mixed timed client completed work: the smallest per-client count
across E samples was778 roots.

CPU overhead remains material: at 64 random Merklix entries, median CPU milliseconds
per root were A 0.03151/C 0.02496/D 0.02524/E 0.49222. At500k random they were about
232.03/231.88/232.15/238.17. A review hypothesis is that mutex traffic and waking
all waiters at every submission/completion dominate tiny jobs; that attribution
has not been profiled or isolated. Avoiding72 workers is not sufficient to make
this version faster. In the 4096-round/24-client synthetic case, E reduced wall
cost to 0.759 [0.742,0.780] of async and CPU cost from 0.84508 to 0.64167ms/root.
Atthree clients, E's wall ratio was2.090 [2.072,2.116].

[analysis.json](analysis.json) includes CPU, RSS, wall variability, first-root and
whole-process timings, helping counts and bounds for every case. Peak RSS includes
fixture/reference/warm-up allocations. Pool startup is in first-root observations;
subprocess wall includes startup/reference/warm-up/teardown and does not isolate
each phase. Fixed workers plus blocked caller threads can exceed18 OS threads;
the strict18 budget applies to callback execution, not all application code.

## Experimental identity and preservation

The new session reran A/C/D alongside E on the same historical source pin
657edc0133cac8d54c5570506dad57bf10e300b5, using the canonical immutable input export
from the original study. Source, kernel, fixtures, partition/hash, compiler and
allocator match across variants. E additionally schedules the whole root through
the shared executor so its callback budget covers caller-side work; this scheduling
cost is timed. A/C/D keep direct root entry. E therefore tests the intended managed
entry model, not only a dispatch substitution. The source/tooling candidate is
commit 1da5614d; exact measured source and binary hashes are retained.

Merklix uses all 14 original workloads, eight balanced ACDE order rotations and
>=1.5s/process sample. Mixed uses three deterministic integer CPU-kernel families,
3/12/24 clients and4096/16384 rounds per leaf, depth3 fork/join, with independent
std::async versus one shared E executor. All use AppleClang21, common-O3/system
allocator settings, and45-second sample bounds. No timed failures or exclusions.
This is a separate dataset: do not compare E directly against old-session medians.

Accepted timing ran20:20:28Z–20:35:02Z on 2026-10-22 after lazy's explicit full drain.
No study compilation ran during timing. The host window excluded other study jobs;
per-sample load averages are recorded, not a proof of an idle host. Eight paired
repetition blocks are bootstrapped jointly10,000 times with seed 20261022 for 95%
intervals. These intervals characterize this session, not cross-machine/day risk.

An earlier partial candidate was stopped after static review found last-owner
helped-job destruction under the scheduler mutex. That release moved outside the
lock and received a regression before this candidate's gates and fresh timing.
The rejected attempt is preserved separately and excluded from every result here.
Original D evidence, Grok source/build/mailboxes, CCheckQueue, validation caches,
production nodes and releases were untouched. No worker processes remain.

Next production work requires selecting real CPU callsites, reviewing all lock/
Future-destruction scopes, separating blocking I/O and establishing application
shutdown ownership. E remains a reusable architectural prototype; it is not
adopted into the daemon. Raw records, summaries and commands are committed;
local binary/build archives are hash-recorded. No remote push was made by this lane.
