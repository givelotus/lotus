# Next bounded history cohort: WebSocket foundation repairs

Proposal, self-review and corrections; not yet executed.

Input candidates are the verified cohortA shared8267586b and native4c2007d0 trees. The standalone relay rank-cache candidate remains outside this pure history cohort. All source refs, full input and cohortA incremental bundle remain retained. No active pins change.

Proposed folds, referring to original inventory numbers rather than filenames:

-111 compression output sizing and126 misplaced AddConnection documentation into96, which introduces the compression helper and AcceptWebSocketPeer declaration.
-101 remaining NET_WSS-to-TCP port correction and102 proxy/onlynet rejection plus its functional test into97, the outbound WebSocket feature.

Review corrections and gates:

1. Use exact committed diffs from the frozen source ownership map, not archival mailboxes. Archive subjects can describe a wider historical patch than the actual current commit:101 already notes that one inbound-WebSocket correction/test lives in97. Retain that earlier hunk and fold only101's remaining committed delta.
2. A fail-closed proxy policy is part of safely introducing outbound connections; keep its functional test at97. Verify all options, dialer hooks and positive TLS cases exist at that point. Do not hoist later TLS APIs merely to make the test compile.
3.111 is a same-feature allocation refinement, not a new independent compression format. Preserve the exact flush-loop semantics and all existing zstd encode/decode tests.126 is comment ownership only; preserve the full declaration and documentation.
4. Build and gate both materially changed earlier owners96 and97, including relevant zstd/WebSocket/net tests and proxy functional checks. Any prerequisite/context conflict is recorded explicitly, not resolved by restoring a whole later file.
5. At the old126 checkpoint require exact cohortA source-tree identity. Require exact shared2c6b9bc7 and nativea576cd04 endpoint trees. Account for all old owners through a composed old→cohortA→cohortB map; no exclusions. Expected reduction is four only if every fold and gate succeeds.
6. The full native rank-cache benchmark owns the source checkout now. Do not start this replay until all benchmark processes are drained and both source/host locks can be acquired. Preserve and back up the separately measured rank-cache optimization before considering its functional adoption.

This review approves preparing the cohort, subject to actual committed-hunk and prerequisite verification. It does not claim four commits removed or earlier owners validated yet.
