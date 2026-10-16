# Private testnet integration handoff — 2026-10-15

The goal remains active: a reviewed private network on separate machines, including wallet payments relayed A→B and mined from C’s mempool, restart/reorg reconciliation, explorer and authenticated Avalanche. Component passes do not establish completion. QUIC/public deployment deferred.

## Ownership and safety

One root integrates. Use new isolated worktrees and disjoint files; implementation agents use Sol 6.1 medium. Preserve main at `/Users/shammah/repos/lotus`, all production workspaces/data/releases and existing worktrees. No reset, push, tag or publication. No test ports 10604, 10605 or 8331. Do not weaken pinned ABC quorum/stake/maturity/confidence defaults or invent production constants. Do not redo compiler imports or emit OP_DEFINE/OP_INVOKE.

## Authoritative state

- Monorepo: `/private/tmp/lotus-v2-integration-owner-20261015`, baseline `4d65f14b` before this handoff.
- User branch: `/private/tmp/lotus-v2-repo`, `lotus-v2`; verify HEAD and cleanliness before fast-forward.
- Native integration: `/private/tmp/lotus-v2-native-integration-20261015`. Baseline `8cd36091ba9da0665ceab621ce42306963fcbfd9`; reviewed lifecycle repair now cherry-picked as `1c8428c91b`, followed by peer-cache documentation correction. These additions are not yet exported into mailboxes or fully built.
- Maintained series: 304 patches, 000–303, final tree `497041ae23601156327363373a5aa983c22242a5`. Every intermediate tree verified. Evidence: `daemon/docs/evidence/v2-series-replay-303.json`. Preserve existing bytes, including binary patch033. Next series commit must parent current lotus-v2 tip, immediately followed by implementation-plan update.
- Immutable tested daemon: `/private/tmp/lotus-v2-node-build-8cd36091ba/lotusd`, SHA256 `635d7c5a6512b686e7af5add1daa29c8252eb5f77db5dcae4fd49f0dd84b2d0d`. Does not include lifecycle repair.
- Real-.git build clone: `/private/tmp/lotus-v2-daemon-runtime-staging-20261015`, `build-chronik-v2`. Unit agent holds exclusive build-only window until released. Do not change source/config or overlap builds. Approximately 7.6 GiB disk free; avoid new full clones.

## Two critical acceptance gaps

### Avalanche recovery and quorum

Agent `avalanche_provisioning` implemented `a4e9aeb100` in `/private/tmp/lotus-v2-native-avalanche-lifecycle-20261015`; independent reviewer passed source and focused real journal reopen/deadline/persistence-failure tests. Root integrated it as above. Startup recovers pending durable work before driver/listener; stop persists last admitted public cache without claiming current eligibility. Load still revalidates.

Next: after build window release, build immutable daemon and validate a NEW COPY of failed seed `/private/tmp/lotus-v2-native-quorum-enabled-seed-20261015-a`. Original failed at height1737 with pending journal; preserve it. Old binary recovery probe also failed before readiness. Do not relabel original clean or restart existing homes casually.

Agent `native_quorum_acceptance` owns isolated harness worktree `/private/tmp/lotus-v2-native-quorum-acceptance-20261015`; commits through `26caab8f` are not integrated. All its processes stopped awaiting fixed binary. New gate tests nonempty funded public proof persistence across pending stop and same-home recovery as an observer. Then finish bootstrap2024, nine real proofs/full mesh, actual quorum/finality/parking/conflicting forks/restart. Ask owner for ordered owned commits before integrating.

### Explorer availability

Frontend and API implemented. Actual run `/private/tmp/lotus-v2-explorer-live-acceptance-20261015-e` FAILED because repeated transient503 responses exhausted explicit UI reloads. Preserve this evidence. Snapshot-token correctness repairs are integrated; durable generation remained stable. No complete wallet/explorer reorg acceptance claim.

`explorer_frontend` now owns a NEW isolated frontend repair: bounded idempotent read503 retry under original deadline, same snapshot token, navigation cancellation, no409/mutation retry, bounded visible failure. `explorer_frontend_review` reviews independently. Do not raise harness reload budget or retry until green. Prior harness `d5ea1f7b` and failure documentation `a21e2d6b` in `/private/tmp/lotus-v2-explorer-live-20261015` are not integrated. Ask ordered commit list later.

## Running validation

`avalanche_node_integration` runs exact8cd Debug Chronik-ON inherited aggregates, session89467, 305 registered checks (313 Ninja steps), last231 steps without errors. Query actual handle/owner before treating it terminal. Build succeeded. Owner releases shared build window after results/logs captured; docs live in `/private/tmp/lotus-v2-final-unit-docs-8cd36091ba-20261015`. Upgrade-named runners do not prove distinct activation. These results precede lifecycle repair.

## Completed scoped evidence; do not repeat broad work

- Compiler:185/187 pass, two unavailable eCash interpreter skips;92 Python/native comparisons without mismatches. `docs/plans/lotus-v2-compiler-integrated-validation.md`.
- Wallet actual discovery/pay/relay/mining/restart/reorg gate:78 checks at documented earlier pins. `daemon/docs/discovery-live-wallet-acceptance.md`.
- Native token index mint/transfer/explicit+implicit burn/reorg/exact-wire remine/restart: independent review passed final run h. `daemon/docs/v2-explorer-assets-live-acceptance.md`. Public permissive TRUE/MINT scripts, not secure issuance or compiler contracts.
- Coverage baseline: `docs/plans/lotus-v2-explorer-coverage.md`; exact older pins, newer authority repair excluded. No full path coverage claim.
- Storage cache/Bloom/body-locator experiments reviewed. `docs/plans/lotus-v2-storage-experiment-review.md`. No default engine change or production adoption; further broad benchmarks unnecessary for milestone.
- Functional inventory: `daemon/docs/v2-functional-acceptance-matrix.md`;292 scripts/319 variants classified. Exact-pin execution remains outstanding, not implied by inventory.

## Finish order

1. Fix explorer availability and finish live acceptance with independent review.
2. Release unit build window, build lifecycle repair, execute copied-home recovery and genuine funded quorum gates.
3. Integrate owned reviewed commits; export new native mailboxes only after fresh complete intermediate-tree replay. Update plan immediately after series commit.
4. Validate final integrated revision across applicable functional/native/compiler/wallet/Chronik gates; update coverage for changed scope and preserve failures.
5. Prepare reproducible build/profile/peer/funding/mining/wallet/explorer runbook. Request separate-host access when local prerequisites are ready; no unspecified infrastructure authorization.
6. Demonstrate separate-machine workflow and audit every goal requirement before declaring completion.

Full objectives remain in `/Users/shammah/.codex/attachments/ff8ddba3-095c-47ec-a423-9fa916a72fa4/pasted-text-1.txt` and its referenced predecessor. This handoff does not reduce their scope.
