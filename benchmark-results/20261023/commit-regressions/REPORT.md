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
