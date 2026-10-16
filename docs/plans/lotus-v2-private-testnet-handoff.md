# Private testnet integration handoff — 2026-10-15

The goal remains active: a reviewed private network on separate machines, including wallet payments relayed A→B and mined from C’s mempool, restart/reorg reconciliation, explorer and authenticated Avalanche. Component passes do not establish completion. QUIC/public deployment deferred.

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

### Explorer availability

Frontend and API implemented. Actual run `/private/tmp/lotus-v2-explorer-live-acceptance-20261015-e` FAILED because repeated transient503 responses exhausted explicit UI reloads. Preserve this evidence. Snapshot-token correctness repairs are integrated; durable generation remained stable. No complete wallet/explorer reorg acceptance claim.

`explorer_frontend` now owns a NEW isolated frontend repair: bounded idempotent read503 retry under original deadline, same snapshot token, navigation cancellation, no409/mutation retry, bounded visible failure. `explorer_frontend_review` reviews independently. Do not raise harness reload budget or retry until green. Prior harness `d5ea1f7b` and failure documentation `a21e2d6b` in `/private/tmp/lotus-v2-explorer-live-20261015` are not integrated. Ask ordered commit list later.

## Validation status

Exact8cd inherited aggregates completed:305/305 runners (147default,147upgrade-named,11Avalanche). Evidence integrated as `9df84e01`, `daemon/docs/v2-final-unit-8cd36091ba.md` and its evidence directory. Independent reviewer rehashed all305 retained logs and both binaries, verified terminal success and exact source. These results precede lifecycle repair; upgrade names do not force distinct activation.

`avalanche_node_integration` now owns a bounded unchanged functional smoke at c0ddb9cf30 (8scripts/10variants), fresh isolated docs/evidence. It must preflight generated config, CLI/wallet-tool provenance and coordinate resources with quorum/explorer owners; no broad reruns or source edits. Status is requested/preflight, not yet passed.

## Completed scoped evidence; do not repeat broad work

- Compiler:185/187 pass, two unavailable eCash interpreter skips;92 Python/native comparisons without mismatches. `docs/plans/lotus-v2-compiler-integrated-validation.md`.
- Wallet actual discovery/pay/relay/mining/restart/reorg gate:78 checks at documented earlier pins. `daemon/docs/discovery-live-wallet-acceptance.md`.
- Native token index mint/transfer/explicit+implicit burn/reorg/exact-wire remine/restart: independent review passed final run h. `daemon/docs/v2-explorer-assets-live-acceptance.md`. Public permissive TRUE/MINT scripts, not secure issuance or compiler contracts.
- Coverage baseline: `docs/plans/lotus-v2-explorer-coverage.md`; exact older pins, newer authority repair excluded. No full path coverage claim.
- Storage cache/Bloom/body-locator experiments reviewed. `docs/plans/lotus-v2-storage-experiment-review.md`. No default engine change or production adoption; further broad benchmarks unnecessary for milestone.
- Functional inventory: `daemon/docs/v2-functional-acceptance-matrix.md`;292 scripts/319 variants classified. Exact-pin execution remains outstanding, not implied by inventory.

## Finish order

1. Fix explorer availability and finish live acceptance with independent review.
2. Complete the running suffix bootstrap and genuine funded quorum/persistence/fork/restart gates; copied-home startup recovery has passed.
3. Integrate owned reviewed commits; export new native mailboxes only after fresh complete intermediate-tree replay. Update plan immediately after series commit.
4. Validate final integrated revision across applicable functional/native/compiler/wallet/Chronik gates; update coverage for changed scope and preserve failures.
5. Prepare reproducible build/profile/peer/funding/mining/wallet/explorer runbook. Request separate-host access when local prerequisites are ready; no unspecified infrastructure authorization.
6. Demonstrate separate-machine workflow and audit every goal requirement before declaring completion.

Full objectives remain in `/Users/shammah/.codex/attachments/ff8ddba3-095c-47ec-a423-9fa916a72fa4/pasted-text-1.txt` and its referenced predecessor. This handoff does not reduce their scope.
