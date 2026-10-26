# Commit performance audit

The **[ABC-anchored progression table](shared-range-progression/TABLE.md)** is the primary benchmark view: untouched ABC0 versus numbered Git prefixes, with footnotes describing the intervening changes. Its status and sample counts distinguish provisional observations from completed repeats. Failed setup checks are shown as FAIL, never credited a rate. [Machine-readable observations](shared-range-progression/RESULTS.json), [ranges and deltas](shared-range-progression/SUMMARY.csv), [exact source/parameter plan](shared-range-progression/PLAN.json).

That table covers shared ABC/eCash commits0–378; it is not the complete native V2 endpoint. The isolated controls below answer repair-specific questions and must not be substituted for the progression.

The three-round progression is complete. Shared endpoint 378 versus ABC 0: 13,176→12,164 individual tx/s (−7.7%); 15,005→24,129 array tx/s (+60.8%); 5,267→5,281 loaded tx/s and 8,241→8,266 concurrent read RPC/s (both about parity). It contains 76 valid samples and 5 untimed synchronization failures across points 78/94; affected cells are FAIL. The individual-submit regression remains unresolved.

Individual-owner follow-up is active. [Source audit of mixed owner 377](../../../daemon/patch-intake/20261023/queue-owner-audit/REPORT.md): the queue commit also reverses peer-capability checks, so its performance change cannot be attributed solely to the queue. The expanded gate also found a stale pre-377 fixture. Its test-only repair advertises actual capability, retains the 16-push assertion and passes 127 gate cases. Actual companion source SHAs are recorded; no production source or review branch is silently changed. The next matched study isolates 1/2/3 and 375/376/377/378, then separates queue and peer behavior. [Current continuation state](CONTINUATION-FIXTURE.json); [earlier stopped gate](CONTINUATION.json).

The first confirmed transport regression has a repair folded into its owning Git commit. The broader 531-commit audit remains open. Source review inputs now reference the repaired branches; all six permanent submodules remain base-only.

| Review history | Published commit | Tracked tree |
|---|---|---|
| [Shared eCash](https://github.com/givelotus/bitcoin-abc/tree/perf/commit-regression-repairs-20261023) |d38c382061d54d76e04b3c7316ca31a8820e6b93|2c6b9bc763382dd3236952d5c8c66efe77f10241|
| [Lotus V2](https://github.com/givelotus/lotusd/tree/perf/commit-regression-repairs-20261023) |a367964741e22fbe20c7f62f2d0b68ed652adc61|a576cd04fc505e68069809d0bc00ec8ed96b4955|

The source contains 378 shared + 153 native owners, no extra fixup commits. Owner 86 now grows HTTP body read-ahead lazily, bounded at 16 KiB. The complete shared/native trees differ from the frozen input by exactly those six production lines. Separately, template-specific test expressions move 44 → 88, where their prerequisite API appears; final test content is unchanged. Original histories and all candidate phases remain preserved with verified bundles and complete ownership ledgers.

## Isolated repair controls and earlier reference comparisons

Each row is an independent comparison; do not add percentages or combine unrelated medians. Ranges and all individual observations are in the linked raw results.

| Change / workload | Before | After | Change | Adoption / evidence |
|---|---:|---:|---:|---|
| Upstream0→shared376: individual RPC admissions |11,140 tx/s|10,928 tx/s|−1.9%, overlapping|[Reference comparison](paired-000-376/SUMMARY.json) |
| Same: JSON arrays50 admissions |13,422 tx/s|20,469 tx/s|+52.5%|[Reference comparison](paired-000-376/SUMMARY.json) |
| Same: unloaded reads |13,207 RPC/s|13,148 RPC/s|−0.4%, overlapping|[Reference comparison](paired-000-376/SUMMARY.json) |
|85→initial Beast86: larger echo arrays50 |507,696 RPC/s|357,629 RPC/s|−29.6%|[Introducing-boundary regression](http-085-086-echo-8clients/RESULTS.json) |
|85→shared376: same echo workload |418,881 RPC/s|364,121 RPC/s|−13.1%|[Gap before repair](http-085-376-echo-8clients/RESULTS.json) |
| Shared376→buffer candidate: same echo workload |426,572 RPC/s|460,339 RPC/s|+7.9%|[Source-matched repair control](http-body16k-paired/RESULTS.json) |
| Pre-Beast85→repaired shared377: larger echo arrays50 |513,958 RPC/s|516,748 RPC/s|+0.5%, parity|[Gap recovery](http-prebeast-body16k-final-paired/RESULTS.json) |
| Same: individual echo requests |43,956 RPC/s|46,665 RPC/s|+6.2%|[Final transport comparison](http-prebeast-body16k-final-paired/RESULTS.json) |
| Shared377→buffer repair: individual admissions |12,067 tx/s|12,224 tx/s|+1.3%, overlapping|[Three rotated pairs](http-body16k-queued-admission-paired/RESULTS.json) |
| Same: JSON arrays50 admissions |24,150 tx/s|25,142 tx/s|+4.1%, all three pairs improve|[Three rotated pairs](http-body16k-queued-admission-paired/RESULTS.json) |
| Same: fixed 499,200 timed admissions |22.70s|22.62s|−0.3%, no meaningful gain|[Two reversed pairs](HTTP-BODY-500K-SUMMARY.json) |
| Count-only RPC fix: admissions with 12 concurrent readers |2,715 tx/s|5,349 tx/s|+97.1%|[Isolated control; ownership candidate](unbroadcast-count-only-paired/RESULTS.json) |
| Same: concurrent reads |6,271 RPC/s|8,353 RPC/s|+33.2%|[Isolated control](unbroadcast-count-only-paired/RESULTS.json) |
| Count-fixed reference → complete snapshot feature: loaded admissions |5,390 tx/s|5,288 tx/s|−1.9%|[Source-matched architecture control](snapshot-versus-count-only-paired/RESULTS.json) |
| Same: concurrent reads |8,405 RPC/s|8,629 RPC/s|+2.7%|[Source-matched architecture control](snapshot-versus-count-only-paired/RESULTS.json) |
| Same: writer-only JSON arrays50 |16,537 tx/s|16,021 tx/s|−3.1%, overlapping|[Source-matched architecture control](snapshot-versus-count-only-paired/RESULTS.json) |

The unqueued376 admission control was unfavorable:21,366→20,065 tx/s (−6.1%, overlapping ranges), despite its echo gain. That result is retained in [the raw comparison](http-body16k-admission-paired/RESULTS.json). The subsequent377 controls include the bounded admission owner. These observations do not establish a universal admission speedup or a formal interaction between the two optimizations.

## Snapshot attribution and count-copy fix

The original ABC `getmempoolinfo` calls `GetUnbroadcastTxs().size()`, copying a growing `std::set` under the mempool lock merely to count it. The snapshot producer already supplies a caller-locked count accessor, but the legacy RPC does not use it until snapshot readers replace the implementation. A control adds only that existing accessor and its ordinary RPC use: no CoW publication or readers. It almost doubles loaded writer throughput. Consequently the earlier roughly twofold snapshot-boundary result cannot be attributed entirely to CoW or moving reads outside `cs_main`.

The paired count-fixed versus snapshot comparison above measures the remaining architectural change. The loaded writer ranges are 5,364–5,402 versus 5,261–5,313 tx/s; concurrent reads are 8,381–8,497 versus 8,575–8,742 RPC/s. These small differences occurred under external host load and are not precise hardware-independent costs. Writer-only arrays have overlapping ranges. The feature retains a modest writer-cost observation requiring further profiling; grouping commits does not erase that cost.

The [planned ownership candidate](../../../daemon/patch-intake/20261023/snapshot-count-order/PLAN.md) puts the cheap count fix at new3 and combines original30 publication with original31 read consumers. It accounts for every original owner and preserves both complete tracked trees exactly. Both new boundaries pass their build/correctness gates and the review branches are published and remotely verified. The previous21ac/3cf review tips remain under archive/perf-review-first-repair-20261023. Full native correctness evidence is reused by exact tracked-tree identity; it is not described as a rebuild of the new history. [Isolated source control](../../../daemon/patch-intake/20261023/unbroadcast-count-control/CONTROL.json) and [complete ownership ledger](../../../daemon/patch-intake/20261023/snapshot-count-order/LEDGER.json).

Throughput windows are at least five seconds, with three alternating pairs. Admission uses eight persistent writers, distinct signed 200-byte legacy eCash transactions and 10,000-satoshi fees, with three loopback nodes sharing the host. The fixed 500,000-transaction corpus excludes 800 warmups, leaving 499,200 timed admissions; each side ran twice in reversed order. Those are latency diagnostics. Unrelated CPU-heavy jobs were observed during the study; small differences remain uncertain.

Echo tests use eight independent warmed clients and 414-character hexadecimal arguments. Transaction validation, P2P and profiling are outside those echo clocks. All responses are checked. Separate samples include profiler overhead and are diagnostics only. RPC acceptance, block confirmation, all-peer reconciliation and native V2 transaction throughput are distinct measurements; this pass does not establish the latter three.

## Cause and correctness

Beast's read-size helper uses max(512,capacity−size). Its initially small buffer can stay at 512 bytes as the parser consumes each chunk, producing many receive operations for a larger body. Profiles showed more receive-system-call activity than libevent. The repair reserves at most 16 KiB only for a body requiring more reading, respecting smaller Content-Length values. Existing body/header limits, authentication, sequential arrays and validation remain in place.

Complete shared/native builds and focused correctness gates pass. The full native suite passes **1,203/1,203 cases and 31,488,118 assertions**. Existing HTTP units and interface_http.py pass. The final native daemon also passes large Unicode bodies over plain/TLS, Content-Length/chunked framing and keep-alive follow-ups. Wallet, Chronik, jemalloc, HTTP2 and WebTransport are OFF in this Release/arm64 profile.

[Exact validation and binary identities](../../../daemon/patch-intake/20261023/perf-regression-repaired-stack/VALIDATION.json), [all 531 owner mappings](../../../daemon/patch-intake/20261023/perf-regression-repaired-stack/LEDGER.json), [reviewed production diff](../../../daemon/patch-intake/20261023/perf-regression-repaired-stack/v2-reviewed-production-delta.diff), [native unit log](repaired-stack-build/native-full-unit.log), [live native HTTP checks](native-http-roundtrip/RESULTS.json).

## Remaining work

- Snapshot prefixes29,30,31 and34 now build and pass their common/overlay/snapshot gates. Two prerequisite repairs move an explicit args include34→15 and an intact legacy-SMT test19→34; complete tracked trees are unchanged. Superseded failed attempts remain preserved. [Prerequisite ledger](../../../daemon/patch-intake/20261023/validation-args-ownership/LEDGER.json), [prefix benchmark](snapshot-029-030-031-paired/RESULTS.json). The count/snapshot ownership repair is also gated and published. Broader fee-policy, RPC, relay, block/template and large-pool progression remains open.
- Checkpoint89 failed before timing while peers did not synchronize its9.6MB funding block. [Failure logs and post-failure samples](paired-000-089/FAILURE.json) remain an unresolved intermediate correctness investigation.
- No obvious growing full-pool scan appeared in the large reference run: successive 100k segments took 4.11,4.40,4.17 and4.35 seconds. This does not establish an asymptotic bound.
- Frozen binary caches refuse overwrites. Use a new --variant for a new source history. Preserve historical source/binary identities when comparing revisions.

[Earlier investigation notes](HISTORY.md) are historical; this report is the current entry point. All work stays under ~/repos/lotus-v2-optimizations; the audit reused the existing registered benchmark checkout and created no additional worktree or clone.
