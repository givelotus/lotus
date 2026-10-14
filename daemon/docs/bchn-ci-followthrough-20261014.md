# BCHN upstream CI followthrough

This is an isolated review record; it does not change a node, submitted source,
Lotus main or a release. Status observations are dated explicitly and are not a
claim that incomplete sanitizer jobs passed.

## Original verified-account pipelines

MRs 2174 (mining), 2175 (diagnostic mempool), 2176 (NNG), 2177 (ZeroMQ default)
and 2178 (ZeroMQ removal) ran after GitLab account verification. All five
`sanitizer-undefined` jobs reached approximately 3,608 seconds and terminated
with `job_execution_timeout`. The fork's project-level `build_timeout` was
3,600 seconds. Those jobs inherit `allow_failure: true` from upstream's
`.sanitizer-common`: a green pipeline does not establish sanitizer success.

All five original jobs completed the full C++ unit binary under UBSan with
`*** No errors detected`, and reported Qt/seeder suite passes. That is real
component-level sanitizer evidence, even though the complete integration job
did not finish. Retained traces contain no explicit
`runtime error:`/UndefinedBehaviorSanitizer diagnostic. Four contain no completed functional-test failure. The mining
trace also reports a real `p2p_compactblocks.py` failure waiting 30 seconds for
an end-to-end block announcement. Its root cause remains unproven.
The hard-timeout job did not retain its configured failure-artifact archive,
so per-node debug logs needed to identify that event are unavailable.

At that failing step, the test manually constructs and solves a block, then
calls `submitblock`; it does not invoke the changed transaction selector.
The full native unsanitized compact-block test passes on the mining candidate.
That narrows the investigation but does not reproduce the Linux sanitizer
runner or prove the CI failure harmless.

## Retry configuration and pending work

After the user's report, root changed only the fork project's timeout from
3,600 to 10,800 seconds and retried the failed sanitizer jobs:

| MR | Original sanitizer job | Retried job |
|---|---|---|
| 2174 | 17182327867 | 17184742893 |
| 2175 | 17182330966 | 17184743711 |

Both retries started on 2026-10-14 at approximately 22:14 UTC. Their full
results remain pending. No timeout or P2P source change was made to these MRs.
The sanitizer job makes a fresh build with ccache disabled, runs native unit
checks, then Qt/seeder/util and the full functional suite; a larger job budget
is an infrastructure adjustment, not a patch-specific fix.

A local background monitor preserves API status snapshots and periodic trace
checkpoints under `/tmp/bchn-ci-retry-watch-20261014/`. Original complete traces
are retained separately as `/tmp/bchn-ci-job-<job-id>.log`.

## Separate NNG lint finding

NNG MR 2176 has a genuine required-job failure in `static-run-linters`: the
raw substring `strerror` also matches the independent `nng_strerror` API.
Candidate commit `63e495c3c1696204b568360a6a3c463b38f6ecc9` changes only the
lint regular expression and its explanatory comment. Actual lint and shell
syntax checks pass; temporary tracked C++ probes confirm ordinary `strerror`,
`std::strerror` and `strerror_r` remain rejected, while `nng_strerror` is accepted.
Those probes were removed. The candidate also composes with the two ZeroMQ
patches in both orders, yielding the same tree. It awaits root review/push;
this record does not claim the upstream lint job has been fixed yet.
