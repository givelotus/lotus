# Generic cooperative executor E: prototype contract and review

E keeps the reusable `Async`/`Post` direction and replaces D's growth-on-wait
model. It is a component candidate, not production integration. Historical D's
header and completed 448-record dataset remain unchanged.

## Scheduling and CPU budget

`CooperativeWorkPool` creates a fixed worker set once. Default and environment
configuration are bounded by hardware thread count, not four times hardware;
explicit constructor budgets are caller-controlled. One shared permit budget
counts every thread currently executing a callback, including external Get
helpers. No worker is added by submission or Get. A blocked nested callback
releases its permit, then reacquires a permit before resuming user code.

Get first reclaims its own queued job. When its target is already running, it
executes another ready FIFO job before sleeping. Queue dispatch is FIFO except
for own-job reclamation and inline backpressure. There is no subsystem priority,
strict arrival-order completion or latency/QoS guarantee under an infinite
producer stream. Finite mixed-client tests assert completion for every client;
raw samples include minimum client completions and other-job help counts.

External waiters participate only after acquiring the same CPU permit. External
caller code outside callbacks is not controlled by the executor. Consequently a
CPU-intensive entry point must itself enter via Async/Get to share the global
budget. E's Merklix benchmark does exactly that; its timed root scheduling cost
is included. A/C/D retain their original direct root entry. Hash, partition,
fixtures and component root outputs are unchanged. This is deliberately more
than replacing only a recursive dispatch statement.

The budget counts callback bodies, not arbitrary application code, result moves
or destructors outside callbacks. Fixed worker threads plus blocked caller
threads can exceed the budget in OS thread count; they cannot all execute pool
callbacks at once. This is not a global process CPU throttler.

## Bounded admission and backpressure

Default ready queue capacity is four times the callback budget. Completed or
reclaimed jobs are removed, so stale queue entries do not consume capacity.
When full, an internal producer runs its newly submitted job inline using its
existing permit. An external producer waits for a permit and runs that job
inline. No producer waits for queue space while holding an execution permit.
User callbacks and last-owner callable destruction run outside scheduler locks.

Accepted unfinished jobs have a second hard limit: queue capacity plus budget
multiplied by64. External submissions backpressure before admission at that
limit. Internal submissions fail explicitly with `length_error` at the hard
limit rather than blocking a producer that holds a permit. Completed Futures
and arguments retained by blocked external submitters belong to application
memory; the executor does not bound those objects. Post intentionally discards
callback exceptions, so applications requiring errors must use Async/Get.

## Dependencies, reentrancy and stack limits

Supported joins are structured same-pool descendant joins: CPU callbacks submit
children and finish their joins before completing. True cyclic dependencies,
ancestor waits, arbitrary cross-root or cross-pool future graphs, and external
blocking I/O are outside the contract. I/O should use a separate executor.
A generic future API alone does not prove progress for arbitrary task graphs.

Helping is reentrant. Hold no application lock across Async, Post, Get, Future
move assignment or Future destruction, because all may execute other callbacks.
A Future must not be consumed or moved concurrently. The pool must outlive its
Futures. Callbacks must not destroy or shut down their own pool.

This stack-based prototype has no fibers or resumable continuations. Logical
submission depth and synchronous callback nesting are limited to64. Exceeding
either fails submission with `length_error`; it is not silently converted into
a possibly deadlocking wait. Helping unrelated ready work can consume this
nesting allowance, so the limit can reject a logically shallower tree under
unusual interleavings. User recursion performed entirely inside one callable
is not bounded by the executor. Deep arbitrary graphs would require a different
continuation representation, not more worker threads.

## Lifetime, exceptions and shutdown

Async accepts move-only callables and movable object results. Void work uses
Post; reference results are unsupported. Get rethrows the callable exception,
consumes its Future, and rejects subsequent Gets. Destroying or overwriting a
Future joins its existing job without throwing its callable exception.

Shutdown closes external admission, permits accepted jobs to submit descendants,
waits for accepted work to become quiescent, and joins the fixed workers. Public
Shutdown is single-owner/nonconcurrent and cannot be called from a callback.
After explicit Shutdown, completed Futures can still be fetched while the pool
object exists. Stop external submitters before object destruction. Partial worker
construction failure stops and joins workers already created.

Focused tests cover caps1/2/hardware, queuecapacity1 pressure, concurrent roots,
move-only values/captures, exceptions, consumed Get, destructor/assignment joins,
Post errors, descendant draining, admission closure and explicit depth errors.
A regression exercises detached helped callables whose destructors reenter
scheduler inspection; releasing their last owner under the scheduler mutex was
found during review and fixed before the accepted measurement candidate.

## Production gate

No production adoption is implied by a microbenchmark. A future integration
must select concrete CPU callsites, route entry points through the shared pool,
review all lock and Future-destruction scopes, identify external blocking work,
and establish application-owned shutdown order. CCheckQueue, validation caches,
Grok's stack and unrelated pools remain untouched.
