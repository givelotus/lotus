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

Both retries started on 2026-10-14 at approximately 22:14 UTC. Their final results are recorded below. Both retries completed all 708 C++ cases under
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
The fresh sanitizer job 17185211816 was still running when monitoring of that
superseded protocol candidate stopped; its CI record remains historical only.
The maintained optional export and exact-tree/order evidence are documented
in `bchn-nng-publisher.md`; no C++ publisher behavior changed for this lint fix.

## NNG scope correction

The user rejected the raw-payload publisher as a scope change: BCHN NNG must
preserve the existing Lotus/Tobias FlatBuffers and RPC interfaces, including
mining. A separate compatibility worker owns that replacement. The publisher's
lint/CI records above are historical evidence only; do not promote its raw
protocol mailbox/export candidate or infer consumer compatibility from those
checks. No further update or external discussion of MR 2176 is authorized by
this followthrough work. Mining/mempool sanitizer monitoring continues separately.

## Final mining and mempool retry results

| MR | Retried UBSan job | Result | C++ cases | Functional cases | Duration |
|---|---|---|---|---|---|
| 2174 | 17184742893 | Success | 708 pass | 191 pass | 5,846 s |
| 2175 | 17184743711 | Failed | 708 pass | 190 pass, one fail | 5,903 s |

MR 2174's complete UBSan run succeeds, including Qt/seeder/util checks. Its
latest pipeline has all 33 jobs successful. MR 2175 has 32 successful jobs and
one failed optional sanitizer job. Neither retained full trace contains an
explicit UBSan runtime diagnostic, but MR 2175's failed full job must not be
described as a clean sanitizer/integration pass. Both source MRs remain unchanged.

The sole MR 2175 failure is `mining_getblocktemplate_errors.py`, whose second
node was expected to return a disconnected-node error. The retained artifact
proves ordering: node1's GBT RPC begins at `23:47:03.932715`; its final peer's
socket closes at `.933306` and is disconnected at `.934139`. The helper only
waited for node0, so node1 legitimately still had a peer when called. This is
an upstream test synchronization race, independently reproduced with upstream
C++ code; it is not a demonstrated mempool diagnostic defect.

A separate [test-only candidate](../candidates/bchn-gbt-disconnect/README.md) adds
a second `disconnect_nodes` call in the opposite direction. It preserves both
error assertions and existing timeouts. Real transparent TCP proxies delaying
only FIN propagation reproduce the original failure and verify the fix with
the identical schedule, on upstream C++ binaries and a native Debug UBSan
binary. Ten ordinary fixed-test UBSan repetitions also pass.

Candidate source commit `029370ebe42a07ee9cc19aff55a1bb963c2c1504` applies directly
to the pinned base and has tree `997734ce27472b34c55be37628c82961e6a88bc7`. Its
mailbox replay matches. Keep it separate from MR 2175; source publication, a
new independent upstream MR and its Linux CI await root review. No external
action was performed for this candidate.

See [final statuses, artifact chronology and reproduction hashes](evidence/bchn-ubsan-followthrough-final-20261014.json).
