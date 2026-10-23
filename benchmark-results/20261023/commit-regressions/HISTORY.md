# Commit performance regression audit

Source reference: `ef42f1ea59399923a57a9b813e3103c98cbcbc8d`, 378 shared + 153 native commits. Positions below refer to this Git history, not old mailbox numbers. Permanent submodules remain base-only; no repairs have been integrated.

Each throughput sample runs at least five seconds. Three paired rounds alternate before/after order. Both builds use Release, wallet/Chronik/jemalloc/HTTP2/WebTransport off. Timings exclude fixture funding and signing. These measure RPC acceptance, not block confirmation or network finality.

| Change | Workload | Before median (range) | After median (range) | Change | Adoption status |
|---|---|---:|---:|---:|---|
| 376 → 377, bounded RPC admission owner | Individual RPC tx/s | 11,083 (10,351–11,352) | 10,540 (9,927–10,918) | −4.9% | Already in reference; individual-path effect unresolved |
| Same | JSON arrays of 50 tx/s | 18,788 (18,573–19,251) | 23,223 (22,393–23,776) | +23.6% | Clear gain in this workload |
| Same | Unloaded read RPC/s | 12,458 (11,804–14,549) | 12,958 (11,885–13,248) | +4.0% | Overlapping ranges |

Source: [paired raw summary](paired-376-377/SUMMARY.json), [all samples](paired-376-377/RESULTS.json), per-case INPUTS and RESOURCES receipts. Before `43caf1aa50fa0fd17087205a960ec1b5fa582bb5`; after `acf7f61425e613581ddd0f0b71e8ccacd4ef2656`.

The individual-path loss did not repeat in every pair (one pair improved). Do not label this a confirmed regression from the medians alone.

Next comparison is upstream point 0 plus adjacent shared positions 85 → 86, isolating the libevent-to-Beast HTTP server transition. Builds and common correctness gates precede timing. Historical endpoint regressions are triage inputs, not attribution to a particular commit.

Investigate a repeated loss with a separate sampling profile, make a small owning-commit repair, and measure the repair under the same workload before folding it into source history. Repeat endpoint checks because improvements can hide earlier regressions. Record justified feature costs explicitly rather than assuming every commit is monotonic.

## Intermediate gates

Positions85/86 cannot currently be timed with their unchanged unit gates: commit44 references a template accessor first defined by88. See [ordering record](INTERMEDIATE-ORDERING.json). No checks were removed.

Checkpoint89 compiled and passed the common unit suites, but its large array fixture failed before the clock started: node0 connected height211 with a9.6MB funding block; peers did not synchronize within60seconds. The partial comparison is **not** a completed throughput result. [Failure receipt and diagnostics](paired-000-089/FAILURE.json). Next sustained comparison uses upstream0 and shared376, whose fixture and unit gates already passed.

## Upstream versus shared376

Three rotated pairs under the same sustained workload and build profile:

| Workload | Upstream0 median (range) | Shared376 median (range) | Change |
|---|---:|---:|---:|
| Individual RPC tx/s | 11,140 (10,663–11,321) | 10,928 (10,019–11,015) | −1.9%, overlapping ranges |
| JSON arrays50 tx/s | 13,422 (13,276–13,657) | 20,469 (19,913–21,462) | +52.5% |
| Unloaded read RPC/s | 13,207 (12,522–14,023) | 13,148 (12,693–13,238) | −0.4%, overlapping ranges |

[Summary](paired-000-376/SUMMARY.json), [all samples](paired-000-376/RESULTS.json). Three nodes share one host; background relay competes with RPC admission. This is not a transport-only comparison. Historical short-burst35% losses are not reproduced here; neither does this prove all intermediate commits improve performance.

A separate [ordering candidate](../../../daemon/patch-intake/20261023/perf-prefix-order-repair/LEDGER.json) relocates only template-id test expressions44→88. Both complete shared/native tracked trees are identical to the frozen input. Original refs and complete verified input history remain preserved, with a verified incremental candidate bundle. This candidate is not promoted into active source/submodule refs. Candidate benchmark binary caches are isolated from reference binaries.

## Introducing HTTP boundary

After the test-ownership-only candidate repair, both85/86 pass common unit gates;86 also passes its HTTP suite. The preserved cheap-RPC probe runs eight independent warmed persistent clients,207byte data represented as414hex characters, five seconds per case, three rotated pairs. No mempool, transaction validation, P2P, or profiling work occurs during these clocks.

| Cheap echo workload | Before85 median (range) RPC/s | Initial Beast86 median (range) RPC/s | Change |
|---|---:|---:|---:|
| Individual HTTP requests | 43,659 (38,997–43,996) | 42,679 (38,516–43,232) | −2.2%, overlapping |
| HTTP arrays of50 | 507,696 (481,491–510,539) | 357,629 (351,160–371,044) | **−29.6%** |

[Raw results and summary](http-085-086-echo-8clients/RESULTS.json). This establishes an introducing-boundary array regression for this payload/control. It does not establish the loss remains today: checkpoint99 includes later move-response and write/timer optimizations and is being built for a paired comparison against85.

## Later HTTP recovery and a candidate

| Comparison | Workload | Before | After | Change | Status |
|---|---|---:|---:|---:|---|
|85→99, later write/timer fixes present | Larger echo arrays50 RPC/s |434,187|393,426|−9.4%| Existing fixes recover part of initial loss |
|85→376, shared reference | Same |418,881|364,121|−13.1%| Confirmed control gap, all3pairs favor85 |
|376→six-line16KiB body-buffer candidate | Same |426,572|460,339|+7.9%| Candidate only; all3pairs improve |
| Same candidate | Individual admission tx/s |12,444|12,334|−0.9%| Overlapping ranges |
| Same candidate | Transaction arrays50 tx/s |21,366|20,065|−6.1%| **Do not adopt yet**; two pairs lower, one roughly even |

Each row is its own rotated comparison; do not add these speedups or compare medians from different run groups as a causal chain. Sources: [85/99](http-085-099-echo-8clients/RESULTS.json), [85/376](http-085-376-echo-8clients/RESULTS.json), [buffer microbenchmark](http-body16k-paired/RESULTS.json), [buffer admissions](http-body16k-admission-paired/RESULTS.json).

Separate [diagnostic profiles](http-085-376-profiles/RESULTS.json) include sampler overhead and are not throughput claims. Samples show substantially more receive-syscall activity in Beast. Local Boost read_size uses max(512,capacity−size); as the parser consumes each chunk the initially512byte capacity can remain small. Candidate ca84c8ea reserves bounded read-ahead only while reading a body. It passes common units, HTTP units, and interface_http.py. Its CMake cache is byte-identical to its reference. The admission slowdown is unresolved; repeat at377 with the bounded admission owner enabled before deciding. No performance repair is integrated.
