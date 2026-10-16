# Private testnet integration handoff — 2026-10-15

The goal remains active: a reviewed private network on separate machines, including wallet payments relayed A→B and mined from C’s mempool, restart/reorg reconciliation, explorer and authenticated Avalanche. Component passes do not establish completion. QUIC/public deployment deferred.

## Current continuation — supersedes earlier status below

- Reviewed operator source integrated as `80da829b` and `f2abf45a`. Root's
  integrated unittest run passed 65 tests with two explicit native-gate skips;
  log `/private/tmp/lotus-v2-operator-integrated-f2abf45a-20261015.log`.
  Separate actual native gate passed at operator `f5a72c4c`, native e775:
  `/private/tmp/lotus-v2-operator-native-gate-20261015/evidence.json`.
  Independent review verified 58 public commands, recipient exchange, payment
  without mining, independent receiver mining, both clean resumes, reorg and
  original-wire reconfirmation. All children reaped. Same host, Avalanche OFF;
  no separate-machine/finality claim. Owner is preparing tracked evidence.
- Python reference evidence committed `391e2a0f`: all95tests passed at a69d576d;
  `daemon/docs/evidence/v2-python-reference-a69d576d/`. Exact source hashes and
  raw log retained; this is not full final integrated validation.
- Peer lifecycle repair `5eddad1c15` independently reviewed and integrated native
  `63c51499441ded6d0fe34d87ff43d53a14b1398f`. Focused peer/driver tests and full
  Debug Chronik daemon build pass. Immutable binary
  `/private/tmp/lotus-v2-node-build-63c5149944/lotusd`, SHA256
  `7d86468e24d457eaf2bbac541cc33ddd422e8a481fee96c8e5b6c07e70de7d0e`.
  Build log `/private/tmp/lotus-v2-peer-lifecycle-integrated-build-20261015.log`.
  Real-.git staging is this exact native revision. Build no longer running.
- Series308patches000–307 replayed with every intermediate tree checked;
  final `b148281abc3b8a7b599182219835bfc41e2b7ba8`. Prior000–306 unchanged.
  Series commit `9a767a72` parents then-current user tip `391e2a0f`; immediate
  plan commit `b96abff9`. Replay evidence `v2-series-replay-307.json`.
- Quorum owner launched NEW run
  `/private/tmp/lotus-v2-native-quorum-63c5149944-20261015-a`, exec session81970.
  Same reviewed harness/defaults/deadlines, copied clean2024seed. Verify actual
  process status before assuming it remains running. No finality claim yet.
- Runbook owner `explorer_frontend` is updating only its document for integrated
  operator commands and latest source/build pins. Separate-host information
  remains unanswered. Broader final-revision suites and updated coverage remain.

## Latest continuation — supersedes older in-flight notes below

- Monorepo/user branch reached `a5b9d3f4`; native integration and real-.git staging
  now `e775de1363c8ef9411f4c38b6c7504dacf4402be`. Series307patches000–306,
  final tree `5dd4b465f2b84eb56320825819cb5d4afb171ccc`, every intermediate tree
  verified. Series `bf7e71cb` parents `0923f47d`; immediate plan `a5b9d3f4`.
- Current immutable daemon `/private/tmp/lotus-v2-node-build-e775de1363/lotusd`,
  SHA256 `5d2ba8f0a2b5bb84de31a2e76860f8b6ef947ddf611b72bb9f03fb10635c59b0`.
  Full Debug Chronik build passed. It adds independently reviewed process-local
  initial-download completion latch; all initial checks unchanged, driver runtime
  authority still separately fenced. Both focused tests passed independently.
- Old c0 quorum run reached2024 and nine funded proofs, passed nonempty public
  cache pending-stop/observer-recovery, then failed readiness deadline amid IBD
  oscillation. All12owned children exited0; original failure and clean seed remain.
  NEW run `/private/tmp/lotus-v2-native-quorum-e775de1363-20261015-a` stopped
  after quorum7 exited1 with `avalanche-negotiated-capacity`; other11children
  exited0. IBD remained false, but finality was not reached. Raw failing command
  and missing-versus-zero ActiveLimit were not logged. The configured2MiB live
  limit exceeds the earlier256000-byte local guard, supporting a stale/dead peer
  diagnosis rather than oversized live traffic. All failed homes remain intact.
  Sol owner `avalanche_provisioning` now implements typed peer-local outcomes
  and atomic queue batches in new `/private/tmp/lotus-v2-native-peer-lifecycle-20261016`,
  based on e775, with independent review. No blind rerun is authorized. It requires explicit
  selected-block-not-finalized and rival parked/not-conflicting-finalized checks.
  Owner `native_quorum_acceptance`; reviewer `avalanche_provision_review`.
- Exact c0 functional smoke evidence integrated `a06ef593`:
  `daemon/docs/v2-functional-smoke-c0ddb9cf30.md`. All10variants/8scripts passed;
  root independently verified binary/script/artifact hashes, JUnit and source.
  Remaining284scripts/309variants were not run by that gate.
- Runbook `daemon/docs/v2-private-testnet-runbook.md` integrated `0923f47d`.
  It accurately describes the c0 recipe and current operator gaps, not completed
  separate-host acceptance. It will need its build tree/pin refreshed after final
  operator/native acceptance; older recipe is deliberately pinned.
- Astra operator contract `docs/plans/lotus-v2-operator-workflow.md` integrated
  `ac0c5378`, independently reviewed. Sol6.1medium owner
  `operator_workflow_implementation` works in
  `/private/tmp/lotus-v2-operator-workflow-20261015`; owns controller.py, devnet.py,
  config.schema.json and controller tests only. Config compatibility, explicit
  clean-stop resume and public recipient export/import are in progress. Reviewer
  `explorer_frontend_review`. No native/consensus/compiler changes in that task.
- Separate-host aliases/OS/architecture and permission for fresh isolated test
  directories/listeners were requested asynchronously and remain unanswered.
  Continue local work; do not deploy to unspecified hosts.

## Ownership and safety

One root integrates. Use new isolated worktrees and disjoint files; implementation agents use Sol 6.1 medium. Preserve main at `/Users/shammah/repos/lotus`, all production workspaces/data/releases and existing worktrees. No reset, push, tag or publication. No test ports 10604, 10605 or 8331. Do not weaken pinned ABC quorum/stake/maturity/confidence defaults or invent production constants. Do not redo compiler imports or emit OP_DEFINE/OP_INVOKE.

## Authoritative state

- Monorepo: `/private/tmp/lotus-v2-integration-owner-20261015`; user branch `/private/tmp/lotus-v2-repo` is fast-forwarded through `9df84e01` before this update. Verify cleanliness and HEAD before further integration.
- Native integration: `/private/tmp/lotus-v2-native-integration-20261015`, `c0ddb9cf307a97a43309b72cffef383c29e559e8`. Reviewed lifecycle repair `1c8428c91b` and documentation correction are integrated, built, and exported.
- Maintained series:306 patches000–305, final tree `2f8ada7e076b9c4e529bc8348834823785029fcd`. Every intermediate tree verified. Evidence `daemon/docs/evidence/v2-series-replay-305.json`. Prior000–303 byte-identical. Series commit `293e9249` parents then-current user tip `2fed44c7`; immediate plan commit `15c87074`.
- Immutable current daemon `/private/tmp/lotus-v2-node-build-c0ddb9cf30/lotusd`, SHA256 `5c05a1acf36a91c690505ca08bd291d9fd2e985fd483f9db08386c712c1f8bfa`; provenance alongside. Full Debug Chronik build passed. Dependency macOS deployment warnings retained; no portability claim.
- Real-.git build clone `/private/tmp/lotus-v2-daemon-runtime-staging-20261015`, `build-chronik-v2`, now c0ddb9cf30. Unit build window released. No further source changes during current acceptance runs. Approximately8GiB free; avoid full clones and costly parallel jobs.

## Two critical acceptance gaps

### Avalanche recovery and quorum

Agent `avalanche_provisioning` implemented `a4e9aeb100` in `/private/tmp/lotus-v2-native-avalanche-lifecycle-20261015`; independent reviewer passed source and focused real journal reopen/deadline/persistence-failure tests. Root integrated it as above. Startup recovers pending durable work before driver/listener; stop persists last admitted public cache without claiming current eligibility. Load still revalidates.

The immutable repaired daemon recovered a NEW COPY of failed seed `/private/tmp/lotus-v2-native-quorum-enabled-seed-20261015-a`. Original failed at height1737 with pending journal; preserve it. Old binary recovery probe also failed before readiness. Do not relabel original clean or restart existing homes casually.

Agent `native_quorum_acceptance` owns isolated harness worktree `/private/tmp/lotus-v2-native-quorum-acceptance-20261015`; commits through `26caab8f` are not integrated. Actual run `/private/tmp/lotus-v2-native-quorum-c0ddb9cf30-20261015-a` recovered pending height1738 with exact ledger state and is importing the suffix. Original failed homes remain unchanged. New gate tests nonempty funded public proof persistence across pending stop and same-home recovery as an observer. Then finish bootstrap2024, nine real proofs/full mesh, actual quorum/finality/parking/conflicting forks/restart. Ask owner for ordered owned commits before integrating.

### Explorer availability — resolved in scoped live acceptance

Reviewed frontend `40c3191a` is integrated as `6b2f9972`; harness commits through
`8e8d43d6` are integrated through root `a8cecc18`. Passing run f evidence is
integrated as `d96efee6` in `daemon/docs/v2-explorer-live-acceptance-20261015.md`.
Independent audit verified42artifacthashes,78nativewalletchecks,153explorerchecks,
19actualDOMruns, same-home confirmed5→detached7→remined8 membership, and ten clean
native exits. Request-local retries recovered81transient503 with zero manual
reloads. Failed run e remains preserved. This gate is complete for native
currency at its exact documented pins; assets retain their separate gate.

## Validation status

Exact8cd inherited aggregates completed:305/305 runners (147default,147upgrade-named,11Avalanche). Evidence integrated as `9df84e01`, `daemon/docs/v2-final-unit-8cd36091ba.md` and its evidence directory. Independent reviewer rehashed all305 retained logs and both binaries, verified terminal success and exact source. These results precede lifecycle repair; upgrade names do not force distinct activation.

`avalanche_node_integration` now owns a bounded unchanged functional smoke at c0ddb9cf30 (8scripts/10variants), fresh isolated docs/evidence. It must preflight generated config, CLI/wallet-tool provenance and coordinate resources with quorum/explorer owners; no broad reruns or source edits. Execution passed all ten variants, without failures/skips, in32.49seconds; scoped evidence commit is being finalized.

## Completed scoped evidence; do not repeat broad work

- Compiler:185/187 pass, two unavailable eCash interpreter skips;92 Python/native comparisons without mismatches. `docs/plans/lotus-v2-compiler-integrated-validation.md`.
- Wallet actual discovery/pay/relay/mining/restart/reorg gate:78 checks at documented earlier pins. `daemon/docs/discovery-live-wallet-acceptance.md`.
- Native token index mint/transfer/explicit+implicit burn/reorg/exact-wire remine/restart: independent review passed final run h. `daemon/docs/v2-explorer-assets-live-acceptance.md`. Public permissive TRUE/MINT scripts, not secure issuance or compiler contracts.
- Coverage baseline: `docs/plans/lotus-v2-explorer-coverage.md`; exact older pins, newer authority repair excluded. No full path coverage claim.
- Storage cache/Bloom/body-locator experiments reviewed. `docs/plans/lotus-v2-storage-experiment-review.md`. No default engine change or production adoption; further broad benchmarks unnecessary for milestone.
- Functional inventory: `daemon/docs/v2-functional-acceptance-matrix.md`;292 scripts/319 variants classified. Exact-pin execution remains outstanding, not implied by inventory.

## Finish order

1. Preserve the completed reviewed explorer gate; integrate pending functional smoke evidence.
2. Complete the running suffix bootstrap and genuine funded quorum/persistence/fork/restart gates; copied-home startup recovery has passed.
3. Integrate owned reviewed commits; export new native mailboxes only after fresh complete intermediate-tree replay. Update plan immediately after series commit.
4. Validate final integrated revision across applicable functional/native/compiler/wallet/Chronik gates; update coverage for changed scope and preserve failures.
5. Prepare reproducible build/profile/peer/funding/mining/wallet/explorer runbook. Separate-host OS/architecture/SSH aliases and permission for fresh test directories/listeners have been requested asynchronously. No unspecified infrastructure is authorized.
6. Demonstrate separate-machine workflow and audit every goal requirement before declaring completion.

Full objectives remain in `/Users/shammah/.codex/attachments/ff8ddba3-095c-47ec-a423-9fa916a72fa4/pasted-text-1.txt` and its referenced predecessor. This handoff does not reduce their scope.
