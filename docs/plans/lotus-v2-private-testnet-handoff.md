# Lotus V2 — Gemini Argon 4 continuation handoff

Snapshot: **2026-10-16 02:29 UTC**. This replaces stale scheduling summaries;
prior versions remain in Git. The private-testnet goal is **active, incomplete**.
This is preparation for a handoff, not evidence that current Codex workers have
stopped. Before taking ownership, inspect actual processes and coordinate the
transfer. Do not edit files concurrently with their listed owner.

## Read first and preserve the actual goal

Read both user objective files:

- `/Users/shammah/.codex/attachments/ff8ddba3-095c-47ec-a423-9fa916a72fa4/pasted-text-1.txt`
- `/Users/shammah/.codex/attachments/3ea1c835-3be0-41d7-918c-90138ada0080/pasted-text-1.txt`

Deliver a reviewed private V2 testnet on separate machines: wallet-created
payments originate on A, relay through B, and are mined from C's mempool;
wallet/indexer/explorer reconcile across restart and reorg; actual pinned-ABC
Avalanche quorum, finality, parking, conflicting branches and recovery work.
Provide builds and operator instructions. Component tests and same-host demos
are not the complete acceptance criterion. QUIC and public deployment are deferred.

Production parameters remain open. Preserve the accepted absolute tail formula
anchored to genesis reward/work, reward lag, and direct genesis-anchored ASERT.
Do not substitute a wall-clock emission schedule or restore iterative previous-tail
adjustment. Preserve pinned ABC quorum/stake/maturity/confidence/default policies.
Do not lower acceptance thresholds or enlarge the finality deadline to get green.

## Safety and integration rules

- Never edit, checkout or reset protected main `/Users/shammah/repos/lotus`, its
  production workspaces, nodes, chain data or releases. V2 shares its Git directory.
- No reset of existing worktrees; no push, tag or publication. New worktrees per
  implementer, disjoint files, one integration owner. User requested Sol6.1 medium
  implementations and Astra unresolved design; independent review is required.
- Test with fresh development data and explicit nonproduction ports. Never use
  10604, 10605 or8331. Do not terminate processes you did not launch.
- Preserve failures, old binaries, source/bytecode/engine mismatches and raw traces.
  Do not delete unknown build/data directories. Disk availability was about105GiB
  at this snapshot, after earlier4GiB constraints; recheck, do not assume.
- Helpers remain inlined, recursion rejected, nesting capped16. CABI07/08 already
  implemented. Never emit OP_DEFINE/OP_INVOKE. Multi-chain research does not permit
  changing Lotus consensus to make examples compile.
- Native source lives in the ABC worktrees; monorepo carries mailbox patches.
  Replay all patches with `git am --keep-non-patch` in a NEW worktree; verify every
  intermediate tree before promotion. Preserve033's binary CSV exactly.
- Series commit parent must be the then-current `lotus-v2` tip. Immediately follow
  it with a commit updating `daemon/docs/lotus-v2-implementation-plan.md`.
  No partial series promotion on a failed tree check.

## Authoritative repositories and exact pins

| Purpose | Path / state at snapshot |
| --- | --- |
| User monorepo | `/private/tmp/lotus-v2-repo`, branch `lotus-v2`, `3e6b49aaca00c98b7bb36d216625473b278de5a1` before this handoff commit |
| Root monorepo integration | `/private/tmp/lotus-v2-integration-owner-20261015`, branch `v2-integration-owner-20261015`, same content; root alone integrates |
| Root native integration | `/private/tmp/lotus-v2-native-integration-20261015`, `7db963beb40b1695da6cd7465d154234d8faf2e7`, tracked clean |
| Native shared Git | `/private/tmp/lotus-v2-native-slice-review/.git` |
| Real-.git full-build clone | `/private/tmp/lotus-v2-daemon-runtime-staging-20261015`, `cd8d5140ec7fce7da9a4e2a5a8b5d803ed4dc3f5`, tracked clean |
| Maintained mailboxes | `daemon/patches/v2/series`,318patches000–317; ABCbase `1fb7db17c176cdea8a2c60d887891589382ee4e3` |

The maintained series ends at native `cd8d5140ec`, tree
`a14a946342d31ee07ee8851906500746800b0c46`. All318 intermediate trees verify;
see [replay evidence](../../daemon/docs/evidence/v2-series-replay-317.json).
Series commit `dfd493fe` and immediate plan `9ab0c7c7` preserve000–307 bytes.
The two later native commits are **not exported/build-integrated yet**:

1. `64832d49e428debefff566ac19f36f2006089bfb`: inventory fairness. Repeated soft
   submission/peer refreshes finish the bounded current traversal; hard authority
   fences remain immediate. Real extracted scheduler fails before, passes after;
   independent review passed. Original candidate `0c3d78a5a2`.
2. `7db963beb40b1695da6cd7465d154234d8faf2e7`: three inherited excessive-block RPC
   test brand prefixes changed BitcoinABC→Lotus. EB2.0/13.0/13.1, comment and value
   assertions preserved. Exact frozen-daemon rerun passes. Original `dcb64ada93`.

## Frozen binaries — never infer newer source from these

`/private/tmp/lotus-v2-node-build-cd8d5140ec/` contains daemon, CLI, wallet tool and
V2 wallet client, with provenance and build log. Debug, ChronikON, walletON build
passed. Daemon SHA256:
`5767c34242f939f5d6fb0fa7f740f87b0c829d179717a58eb4df5cb84c88f7d9`.
[Tracked provenance](../../daemon/docs/evidence/v2-native-build-cd8d5140ec.json)
records all binaries. Some dependencies warn macOS26.5 objects target26.0;
older-macOS/Linux compatibility is not established by this build.

Full-tree CMake needs real `.git` (the inherited reflog code breaks worktree files).
Python3.13: `/opt/homebrew/bin/python3.13`; compiler/reference venv:
`/private/tmp/lotus-v2-compiler-review-venv/bin/python`.
Rust1.93; LLVM library envs `/opt/homebrew/opt/llvm/lib`.
Secp archive: `/private/tmp/lotus-v2-native-033-wt/build-secp-install/libsecp256k1.a`.
Boost: `/opt/homebrew/opt/boost/include`. VM/block standalone targets require
field_size.cpp, persistent_utxo.cpp and header.cpp dependencies as registered.

## Highest-priority blocker: real Avalanche finality

Latest actual run:
`/private/tmp/lotus-v2-native-quorum-cd8d5140ec-20261015-a`.
Unchanged harness/defaults, fresh clean2024-block seed copy. All9 proof provisions,
funded pending-stop/recovery and authenticated default quorum passed. The unchanged
300second `real-polled-seed-finality` gate **failed**; only node8 finalized.
Fork/parking/restart gates were not reached. All12 owned native children exited0;
the harness/session47425 is terminal and owned PIDs were checked absent.

[Evidence](../../daemon/docs/evidence/v2-native-quorum-cd8d-finality-deadline-20261015.json)
and [acceptance document](../../daemon/docs/lotus-v2-native-quorum-acceptance-20261015.md)
are integrated at `2f5d1579`. Root verified50raw hashes and every recorded
activation trajectory reference. Final activations:18,18,18,17,18,26,16,17,16.
The prior63c run similarly finalized only one node. Correctly signed late replies
were repaired with pinned ABC fault policy, but that repair was insufficient.
Existing traces have no polling/confidence/disconnect breakdown: do not invent a
root cause or simply repeat this run. Next run needs reviewed passive diagnostics.

Quorum harness/evidence owner clone:
`/private/tmp/lotus-v2-native-quorum-acceptance-20261015`, last evidence32293106.
Owner `/root/native_quorum_acceptance` is completed; no retry active.

## Live candidates — NOT integrated, verify before taking ownership

### A. Verified block-body chunk cache

Owner `/root/audit_safety_repairs`; reviewer `/root/explorer_frontend_review`
(with additional source review from `/root/avalanche_provision_review`).
Worktree `/private/tmp/lotus-v2-runtime-block-cache-20261015`, base64832d49e4,
cache commit `5a26ce6df372f3c37064dd25135fc0783fd24efd` (NOT integrated).
Committed cache files: development_runtime.{h,cpp}, development_node_command.cpp,
test_development_runtime.cpp, development_runtime_test/CMakeLists.txt and new
`development_runtime_test/check_block_chunk_command.py` under `src/lotus_v2/`.
Untracked build `build-cache-review/` is owned evidence, not source to commit.

One-entry cache stores authenticated previously-connected bytes. Detached blocks
remain readable as before. Every chunk checks current runtime authority/profile;
stamp includes identity/profile/tip/root/revision/invalid_epoch/body_epoch/context
_generation. Caller cap applies on hits; chunks<=64KiB; output unchanged on failure.
Old entry clears before replacement. Node rechecks memory snapshot AFTER Status,
which can silently fault runtime, before publishing bytes. Existing full-body API
for peers/Chronik remains. No claim the whole command becomesO(chunk): Status still
has metadata costs. Optional per-call counters count actual load **attempts**.

Final cache session98229 is terminal exit0: registered runtime test passed6.09s
and the actual extracted ReadBlock/FaultEnv adapter passed2.28s (2/2). Source and
artifact-hash review is green; frontend reviewer is independently rerunning these
two executables. No cache-owned build/node process remains. Evidence directory:
`/private/tmp/lotus-v2-runtime-block-cache-evidence-20261015/`; `final-test.log`
and `final-artifacts.json` bind source/three binaries. The negative control removes
the postStatus fence and fails stale-publication; restored fence passes. Adapter
does not execute full actual Node::Status/whole node. A separate NodeStatus
serializer is being prepared, so recheck dirty files before taking ownership.
Cache commit and later diagnostics serializer must remain separate.

**Known integration blocker discovered after those passes:**
`chronik_sync_test/CMakeLists.txt` introspects the runtime test target's SOURCES.
The new object-library test refactor would omit implementations from that caller.
Owner is authorized to repair that CMake file separately, search other consumers,
and run affected Chronik sync/explorer standalone checks. Do NOT merge cache until
this compatibility follow-up and independent review pass. Production behavior is
unchanged by this build-registration problem.


### B. Passive Avalanche diagnostics

Owner `/root/avalanche_provisioning`; reviewer `/root/avalanche_provision_review`.
Worktree `/private/tmp/lotus-v2-native-ava-diagnostics-20261016`, base64832d49e4,
candidateHEAD3c7a68e3a4.
Candidate changes: avalanche_{poll,peer,driver}.{h,cpp}, NEW avalanche_diagnostics.h,
test_avalanche_{v2,peer,driver}.cpp, avalanche_driver_test/README.md.
Candidate commit `3c7a68e3a4` is now ready, NOT integrated. Poll session88394/
test0.61s, peer session54321/test1.93s, and driver session53703/test1.79s all passed
and are terminal. No owned compiler/node remains. Final exact-commit review is
pending; prior source review was green. Cache compatibility checks now own the
heavy window. No full daemon or acceptance run was performed.

Fixed saturating counters/gauges report query expiry, applied/ignored/rejected/local
responses, classified peer failures, queue/backpressure, tracked disconnect causes
and optional current-tip confidence. They must not affect protocol decisions.
Unknown/external causes remain explicit, not inferred by subtracting overlaps.
NodeStatus serialization is owned by cache agent in a separate dependent commit.
Next: final independent review; serialize and build combined
source, freeze binary, then NEW unchanged-quorum run after review.

### C. Consolidation builder, first boundary only

Owner `/root/audit_network_repairs`; reviewer `/root/explorer_storage_review`.
Monorepo `/private/tmp/lotus-v2-consolidation-builder-20261015`, branch
`audit-v2-consolidation-builder`, base66b378fdc007acce99f3a5e390149d704be1fa17.
Latest root inspection finds an untracked builder script being written; no candidate
native tree or build is yet reported. Owns only
`daemon/scripts/consolidate-v2-candidate.py` and
`daemon/tests/test-consolidate-v2-candidate.py`. Recheck as implementation continues.
Reserved NEW native/evidence paths:
`/private/tmp/lotus-v2-consolidated-inherited-20261015` and
`/private/tmp/lotus-v2-consolidated-inherited-evidence-20261015` were nonexistent.

Reviewed [ledger](lotus-v2-consolidation-ledger.md) and JSON integrated at
c88d6d6c/3e6b49aa:318mailboxes,1051file diffs,1053exclusive units,51proposed topics.
All source/section/binary hashes and DAG validate. Three context SCCs remain.
First inherited topic:64owned file sections in original order from pinnedABCbase.
Builder verifies ledger before mutation, refuses existing destinations/dirty roots,
uses git apply --index withoutthreeway/futureblob fallback, preserves first conflict
and stops. Draft commit allowed only after all64 apply; build gates still pending.
Do not replace maintained series from a mapping or clean application alone.
Newer648/7db/cache/diagnostics are outside this immutable000–317 ledger.

## Functional testing and queued automation

Final-cd8 batch002 now has8passing identities across scoped runs:7original fixtures
plus the independently reviewed excessive-block branding fixture. Original failure
and a port-preflight enforcement mistake are preserved, not relabelled green.
All subprocesses stopped. Root verified raw hashes; evidence integrated29e05e25/
a7c8a816. First8 identities had passed on older63c, not automatically on cd8.
**311 of319 variants remain unrun on the final-cd8 pin.**

[Plan and receipts](../../daemon/docs/v2-functional-final-cd8d5140ec-plan.md).
Source/binaries frozen at `/private/tmp/lotus-v2-functional-final-cd8d5140ec-20261015`.
Owner clone `/private/tmp/lotus-v2-functional-final-cd8d5140ec-docs-20261015`.
Integrated supervisor throughffdf8cac defaults dry-run, explicit batch range,
verifies hashes, refuses existing run dirs, fail-closed allocated port checks,
jobs1,1800s/batch,4GiB launch,2GiB floor/scratch, exactJUnit, owned-process-group
cleanup. All6parser tests pass, including JUnit errors/skip/nonzeroexit/identity.
38 ordinary batches003–040 cover282unique queued variants; other feature/platform/
resource lanes and the final rerun of first8 remain explicit pending work.
Batch019 dynamic node count requires review. No further execution authorized while
cache/diagnostics builds own the resource window. Next eligible batch003 is prepared.

## Other completed component evidence and remaining scope

- Compiler: `docs/plans/lotus-v2-compiler-integrated-validation.md` —185/187 tests
  passed, two eCash interpreter skips;92cross-engine comparisons, mismatches kept.
  Exact pins in report. This is not the current full combined acceptance gate.
- Python reference:95tests passed at a69d576d, evidence
  `daemon/docs/evidence/v2-python-reference-a69d576d/`.
- Operator: `daemon/docs/v2-operator-workflow-acceptance.md`, integrated93d479b3;
  same-host independent sessions, AvalancheOFF, public recipient exchange, payment,
  receiver mining, clean resumes and reorg recovery. Not separate-host or finality.
- Explorer native currency live/reorg and asset mint/transfer/burn/remine/restart
  evidence exists. Asset gate used public TRUE/MINT native fixtures, not secure
  compiler-issued contracts. Never broaden that claim.
- Coverage: `docs/plans/lotus-v2-explorer-coverage.md` is older exactpins; frontend
 681/750lines, native220/260lines/107of164branches, Rust2565/2971lines. New authority,
 lifecycle, audit/cache/diagnostics changes are not covered by that baseline.
- Storage experiments are reviewed evidence, not an adopted engine replacement.
  Do not restart broad MonadDB research. Repeated transaction encode/identity work
  remains an open performance finding; cache repair addresses retained-body reads.
- Argon audit findings1/2cost accounting and7branch-root asymmetry match explicit
  development rules. Read `lotus-v2-argon-consensus-and-consolidation-review.md`;
  don't silently change consensus while squashing. P03's two cf→ea prose typos
  were corrected atd5a44570, preserving VM behavior.

## Next actions in order

1. Reinspect current HEADs, dirty files, actual sessions/PIDs and owner transfer.
   Preserve moving work; do not run a competing Gemini integration loop.
2. Finish cache final regression/review; finish diagnostic driver test/review and
   separate NodeStatus serializer. Integrate only approved exact commits, preserving
   already-integrated648/7db. Do not mistake an agent base for the current native tip.
3. Build combined daemon/tools, freeze source/binary provenance, replay/export new
   append-only mailboxes in fresh worktree and follow series-parent/plan ordering.
4. Run NEW quorum acceptance unchanged with diagnostic evidence. If failed, use
   measured counters to identify cause; no threshold/deadline relaxation.
5. Resume bounded functional batches as resource windows permit. Final acceptance
   needs all applicable inherited/native/compiler/reference/wallet/Chronik suites
   on an exact integrated revision plus updated meaningful coverage.
6. Continue isolated consolidation construction with ledger provenance. Every
   boundary builds and runs native units/registeredCTests/cumulativeV2checks;
   owning-boundary regressions; final/config-change fullfunctional and four-config
   Debug/Release ChronikON/OFF matrix. Preserve exact final tree and033binary.
7. Finish separate-machine demo and runbook. Host/access information has been asked
   but not supplied; do not deploy unspecified infrastructure. This is not a reason
   to stop useful local implementation/testing or claim the overall goal complete.

The goal remains active until all original requirements have direct evidence.
