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
A fresh standalone macOS arm64 Debug build of exact MR 2174 commit
`640b8bd1c8e88107421a201828eaaf2b46802b28`, with undefined-behavior
instrumentation, also passes the full compact-block test with
`UBSAN_OPTIONS=print_stacktrace=1:halt_on_error=1:log_path=stdout`. Build
commands and runtime symbols confirm instrumentation. That narrows the
investigation but does not reproduce the Linux runner or prove the original
CI failure harmless.

## Retry configuration and pending work

After the user's report, root changed only the fork project's timeout from
3,600 to 10,800 seconds and retried the failed sanitizer jobs:

| MR | Original sanitizer job | Retried job |
|---|---|---|
| 2174 | 17182327867 | 17184742893 |
| 2175 | 17182330966 | 17184743711 |

Both retries started on 2026-10-14 at approximately 22:14 UTC. Their full
results remain pending. Both retries have completed all 708 C++ cases under
Linux UBSan with no errors. The full compact-block functional test also passes
in both retries: mining MR 2174 in 47 seconds at 23:00:34 UTC and diagnostic
MR 2175 in 41 seconds at 22:59:47 UTC. Thus the original announcement timeout
did not recur on the unchanged submitted mining source; its cause is still
unproven. See [retained progress evidence](evidence/bchn-ubsan-retry-progress-20261014.json). No timeout or P2P source change was made to these MRs.
The sanitizer job makes a fresh build with ccache disabled, runs native unit
checks, then Qt/seeder/util and the full functional suite; a larger job budget
is an infrastructure adjustment, not a patch-specific fix.

A local background monitor preserves API status snapshots and periodic trace
checkpoints under `/tmp/bchn-ci-retry-watch-20261014/`. Original complete traces
are retained separately as `/tmp/bchn-ci-job-<job-id>.log`.

## Separate NNG lint finding

NNG MR 2176 has a genuine required-job failure in `static-run-linters`: the
raw substring `strerror` also matches the independent `nng_strerror` API.
Reviewed follow-up `69462d0ec7ec651165249fed78b938c09b1cc861` preserves the
unsafe C/Windows strerror-family ban while allowing independent identifiers.
An executable permanent regression runs through the existing CMake lint suite
and tests the actual linter in a disposable repository. Root pushed the reviewed
source; required GitLab lint job 17185211785 passes in pipeline 2948599926.
The fresh sanitizer job 17185211816 remains running with the three-hour budget.
The maintained optional export and exact-tree/order evidence are documented
in `bchn-nng-publisher.md`; no C++ publisher behavior changed for this lint fix.
