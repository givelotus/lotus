# Lotus V2 implementation and launch plan

Updated October 15, 2026. Development plan; no genesis parameters are frozen and no launch is authorized by this document. This restores the implementation plan previously present at `5d7d7130`, retaining milestone IDs while updating source routing, specification dependencies and release requirements.

[Consensus](../../docs/lotus-v2/consensus.md) owns validity, [decisions](../../docs/lotus-v2/decisions.md) owns open choices, and [validation](../../docs/lotus-v2/validation.md) owns conformance obligations. A patch existing, applying, building, passing a model, and passing independent consensus validation are separate statuses.

## Source foundation and current status

The current executable [V2 series](../patches/v2/series) contains 318 patches,
`000`–`317`, on ABC master `1fb7db17c176cdea8a2c60d887891589382ee4e3`.
[Latest replay evidence](evidence/v2-series-replay-317.json) verifies every
intermediate tree. Offline daemon acceptance, restart, disconnect/reconnect,
resumable fork recovery, bounded selection and actual two-process TCP full/compact
synchronization have separate evidence below. Native production of signed fixture-payment blocks also passes across two nodes.
The foreground local controller now completes a live-wallet payment and restart
across two isolated nodes; see the current controller evidence below. Development
profile adoption and public launch remain pending.

### Reviewed audit repairs through 317 (October 15)

Series commit `dfd493fe793752bb7ac32eacc7bfa626d0da1d17` appends ten reviewed repairs to the
previous series, preserving mailboxes 000–307 byte-for-byte. All 318 trees
verify in a new replay; final native source `cd8d5140ec` has tree
`a14a946342d31ee07ee8851906500746800b0c46`. This plan update immediately follows the series commit.

Repairs cover signed late Avalanche responses with pinned ABC abuse policy,
FIFO relay inventory, application-frame retention across authority changes,
portable temporary fixtures, prepared-VM ownership, early mempool resource
checks, wallet descriptor restoration, valid monetary fixtures, and inherited
Lotus branding expectations. Independent focused checks passed. Combined Debug
Chronik-enabled daemon, wallet client, CLI and wallet-tool builds passed.
The linker reports dependencies built for macOS 26.5 while targeting 26.0;
compatibility with older deployment versions has not been demonstrated.

The previous nine-node run established the authenticated default quorum but
failed its unchanged finality deadline. That failure remains preserved; these
repairs have not yet passed a new quorum/finality run. Full final-revision suites,
Linux execution, updated coverage and separate-machine acceptance remain open.
The audit consolidation is a separate reviewed candidate, not yet promoted;
see the Argon consensus and consolidation review in docs/plans.

### Reviewed peer lifecycle repair through 307 (October 15)

All 308 intermediate trees verify in a fresh replay. Source `63c5149944`
has tree `b148281abc3b8a7b599182219835bfc41e2b7ba8`; mailboxes000–306
remain byte-identical. Series commit `9a767a72` parents `391e2a0f`, the
then-current `lotus-v2` tip, followed immediately by this plan update.

The e775 nine-node run terminated one node on a stale peer capacity path;
its failing evidence remains preserved. Patch307 treats dead connections and
permanent negotiated-size rejection as peer outcomes, retries temporary queue
pressure, and preserves genuine local failures. Atomic response preflight avoids
partial batch enqueue. Disconnect releases queued actions, authentication,
discovery and polls while allowing healthy peers to progress. Independent source
review and both focused peer/driver executables pass, including real retained
notices after removal and transport closure. Full Debug Chronik daemon build
passes; immutable daemon SHA256
`7d86468e24d457eaf2bbac541cc33ddd422e8a481fee96c8e5b6c07e70de7d0e`.
Full quorum/finality/fork/restart acceptance remains outstanding. No quorum,
stake, maturity, confidence, consensus or network defaults change.

### Reviewed initial-download latch through 306 (October 15)

All 307 intermediate trees verify in a fresh replay. Source `e775de1363`
has tree `5dd4b465f2b84eb56320825819cb5d4afb171ccc`; mailboxes000–305
remain byte-identical. The series commit parents `0923f47d`, the then-current
`lotus-v2` tip, followed immediately by this plan update.

The c0ddb nine-node run reached eight authenticated eligible peers per node but
failed its quorum-readiness deadline. Routine header refreshes repeatedly
reopened native IBD, unlike pinned ABC's one-way initial catchup latch. Patch306
preserves every initial check and latches completion per process. Independent
review and two focused tests pass, including real pending-journal refusal by the
driver even after IBD is false. Full Debug Chronik build passes; immutable daemon
SHA256 `5d2ba8f0a2b5bb84de31a2e76860f8b6ef947ddf611b72bb9f03fb10635c59b0`.
The earlier failed run and clean2024seed remain preserved. Funded-cache pending
stop/recovery passed independently at c0ddb; full quorum/finality/fork/restart
acceptance is being repeated using a new seed copy and explicit pre-finality
parking assertions. No threshold or consensus change is made.

### Integrated wallet and explorer acceptance (October 15)

The [live explorer gate](v2-explorer-live-acceptance-20261015.md) now passes on
native `c0ddb9cf30` and reviewed frontend `40c3191a` (integrated as `6b2f9972`).
Independent review verified all 42 recorded artifact hashes, source pins, raw
confirmed → detached → re-mined transitions and cleanup. The run has 78 native
wallet/controller checks, 153 explorer checks and 19 actual DOM runs. All ten
native processes exited cleanly. Request-local bounded retries recovered 81
transient 503 responses without manual screen reloads; earlier failures remain.
This is native currency and automated DOM acceptance, not a browser usability
study, accepted-pool indexing, Avalanche finality or separate-machine evidence.
Native token indexing retains its separately reviewed asset gate above/below.

The bounded exact-c0ddb inherited functional smoke completed all ten registered
variants of eight scripts without failures/skips; its detailed evidence is being
finalized separately. Full applicable functional execution remains outstanding.
Funded quorum acceptance is still running after copied-home startup recovery.
Separate test-host access has been requested; no remote deployment is authorized
until the user identifies the test infrastructure and permitted actions.

### Reviewed lifecycle repair through 305 (October 15)

All 306 intermediate trees verify in a fresh replay. Source `c0ddb9cf30`
has tree `2f8ada7e076b9c4e529bc8348834823785029fcd`; mailboxes 000–303
remain byte-identical. The series commit parents `2fed44c7`, the then-current
`lotus-v2` tip, and this plan update follows immediately.

Patch 304 recovers existing pending durable work before Avalanche startup and
saves the last admitted public peer cache during orderly stop. Restored records
still require current-chain validation. Independent focused tests pass journal
reopen/recovery, bounded deadlines, startup gating and real persistence failures.
Patch 305 corrects the driver documentation. The full Debug Chronik-enabled
daemon builds; immutable binary SHA256 is
`5c05a1acf36a91c690505ca08bd291d9fd2e985fd483f9db08386c712c1f8bfa`.
The new copied-home acceptance run reports recovery of the previously pending
height1738 with exact accepted-ledger state; suffix import is still running in
`/private/tmp/lotus-v2-native-quorum-c0ddb9cf30-20261015-a`. Funded cache
retention, actual quorum/finality and restart acceptance remain outstanding.

The preceding exact `8cd36091ba` inherited unit run passed all 305 registered
runners (147 default, 147 upgrade-named, 11 Avalanche). Those runners precede
this lifecycle change and do not prove native funded quorum behavior. Explorer
live run e retains a real repeated-503 availability failure; a bounded frontend
read-retry repair is under independent review. Separate-machine acceptance and
remaining applicable functional gates remain unfinished.

### Historical reviewed repairs through 303 (October 15)

All 304 mailboxes replay in a fresh worktree, verifying every intermediate tree.
Source `8cd36091ba` has tree `497041ae23601156327363373a5aa983c22242a5`.
Mailboxes 000–300 remain byte-identical. Series commit `075f8de3` has parent
`36303480`, the then-current `lotus-v2` tip; this plan update follows immediately.

Patch 301 fixes overlapping Avalanche update batches exhausting the unchanged
read budget; [before/after evidence](v2-avalanche-update-batch.md) and independent
review cover ordered staging, bounds and corruption behavior. Patches 302–303
separate transient HTTP request fencing from durable explorer snapshot versions.
Idle turns preserve continuation tokens; actual context changes, recovery and
ABA still invalidate them. The repaired service/HTTP suites pass 29 tests and
the combined Chronik-enabled daemon builds.

The independently reviewed [native asset gate](v2-explorer-assets-live-acceptance.md)
passes mint/transfer/explicit and implicit burns, exact indexed/native facts,
longer-fork rollback, all four detached outpoints, exact-wire mempool re-mining,
and persisted locations after restart. Five processes exit cleanly. It uses
public native TRUE/MINT test scripts, not a secure token issuance contract or
compiler acceptance fixture. Idle ready observations retain their generation;
brief suspended/unavailable observations are explicitly recorded and bounded.

The funded quorum bootstrap exposed a subsequent lifecycle defect: graceful
shutdown during a pending journal fails peer persistence, and reopening that
home fails before runtime recovery can run. The original data and failure traces
are preserved; a repair and copied-home recovery gate are in progress. No quorum
or finality claim follows from the existing bootstrap. Wallet/explorer DOM
acceptance, exact-revision aggregate tests and separate-machine acceptance remain
unfinished. [Coverage](../../docs/plans/lotus-v2-explorer-coverage.md) identifies
mapped denominators and excludes these newer authority branches from its older
baseline. [Functional inventory](v2-functional-acceptance-matrix.md) distinguishes
execution evidence from still-unrun registered tests.

### Historical reviewed integration through 300 (October 15)

All 301 mailboxes replayed in a fresh worktree with `git am --keep-non-patch`,
verifying every intermediate tree. Final native source `86201398e3` has tree
`d2048e32a58cf773094dbedd740087b9d23f1118`. Mailboxes 000–260, including the
binary literal in 033, are unchanged. Series commit `fb4adb26` has parent
`a6a0f471`, the then-current `lotus-v2` tip; this plan commit immediately follows.

The appended patches integrate native Avalanche driving, candidate reconciliation,
existing-home private proof provisioning, direct block-policy observations, and
schema-3 explorer facts, bounded HTTP queries, asset indexing and atomic undo.
The [explorer integration report](v2-explorer-integration.md) records a successful
Chronik-enabled daemon build, 61 Rust component checks, two native producer/sync
checks and actual observer process checks. The frontend is maintained separately
under `explorer/v2`; 18 tests and independent review pass. A fresh
`chronik-v2-explorer-v1` directory preserves earlier index files.

[Wallet discovery acceptance](discovery-live-wallet-acceptance.md) now records
78 checks on its separately pinned native/controller/compiler revisions, including
relay, mining, restart and reorg. [Compiler validation](../../docs/plans/lotus-v2-compiler-integrated-validation.md)
records 185 passing tests, two explicit eCash native skips, and 92 cross-engine
comparisons without discrepancies. These are scoped results, not a claim that all
components passed on this final native revision.

Still outstanding: funded quorum/finality/parking/recovery, a reviewed fix for
repeated ancestry reads in large finalization batches, actual explorer/asset
acceptance across restart/reorg, exact-final-revision full validation, and
separate-machine acceptance. Storage experiments remain optional candidates with
[reviewed limitations](../../docs/plans/lotus-v2-storage-experiment-review.md);
no cache/Bloom default or custom database is adopted. Production constants remain
open. QUIC and public deployment are deferred.

### Historical reviewed integration through 260 (October 15)

All 261 mailboxes replay in a fresh worktree with `git am --keep-non-patch`.
Every intermediate tree matches. Final source `e96a6c7da9` has tree
`ff7e7a99a37ad02e0492419334bb704fef109589`. Existing mailboxes 000–218,
including binary patch 033, are byte-for-byte preserved. The series commit's
parent is the then-current `lotus-v2` tip `09bb0951`; this plan update follows
that series commit directly.

The appended changes include the native Chronik bridge, confirmed HTTP service,
linear catchup and authority fences; the bounded Avalanche peer store, wire
adapter, driver and passive status; and reviewed startup/test fixture repairs.
Actual Chronik/wallet reorg evidence is recorded separately in
[evidence/v2-chronik-live-wallet-reorg.json](evidence/v2-chronik-live-wallet-reorg.json).
The [native audit](v2-abc-unit-audit.md) records clean full default and
upgrade-named aggregates (147 runners each), plus 11 Avalanche suites; those
upgrade-named runners do not establish distinct upgrade activation semantics.
The [functional audit](v2-abc-functional-audit.md) records seven inherited and
one SQLite script passing, with the remaining inherited scripts unrun.
These pins and scopes are not an exact-final-revision acceptance claim.

The independently audited [2,024-block stake preparation](evidence/v2-quorum-bootstrap-native.json)
proves actual native blocks, funding and maturity; it does not prove peer proof
admission, quorum, polling or finality. The node's Avalanche driver wiring,
parked-candidate enrollment, private proof provisioning and real quorum test
remain subsequent integration work outside this series. Named compiler policies
and explicit entrypoint/package support are maintained separately in the
monorepo. Actual automatic wallet discovery across reorg is still under test.
Explorer implementation follows the reviewed API contract. Separate-machine
acceptance, production parameters and public deployment remain incomplete.

### Historical private transaction integration through 218 (October 15)

The complete 219-entry series replays with `git am --keep-non-patch` from the
pinned ABC base. Every intermediate tree matches; final source tree is
`028e4b47980e6d3e3f52c987b17f2df96f772313`. Mailboxes 000–172 remain byte-for-byte
unchanged, including the binary literal in 033. The appended commits carry
absolute genesis reward anchors, native wallet submission/status, bounded
transaction pool/history/relay, pinned Avalanche adapters and runtime policy,
and separate Chronik V2 output storage and branch-query foundations.

[Three-node, two-wallet evidence](evidence/v2-private-relay-two-wallets-local.json)
records 67 passing checks: A submits, B relays, C mines from its pool, both wallets
reconcile, processes restart, and a fork detaches payments before valid pending
work is mined again. All nodes used fresh isolated homes on one machine.
[Controller evidence](evidence/v2-private-controller-local.json) records 12 passing
tests including its native wallet payment/restart workflow. These runs do not
prove separate-machine operation or an authenticated Avalanche quorum.

The full native build at `b70441496` builds daemon and wallet client and passes
transaction pool/coordinator/relay and Avalanche adapter/runtime checks with
Chronik disabled. The actual Rust V2 database suite passes seven focused tests.
Chronik's native bridge and HTTP router remain outside this series pending review
fixes and node integration; live indexing, pending transaction indexing and
wallet discovery are unfinished. Avalanche peer wire, persistence integration,
node callbacks and a real quorum/fork demonstration also remain unfinished.
Production parameters and public deployment remain open; QUIC is deferred.

### Historical source milestones through 069

The following records describe the named earlier source trees; later evidence
sections supersede their then-current implementation and acceptance limitations.
The [review packet](../candidates/v2-native-reviewed-20261014/README.md) records
intermediate replay trees and focused validation through patch 032. That reviewed source tree is
`507c91e64c205df7b38e77abff6ebe02fb99bffe`. It includes transaction framing,
commitments, scalar and incremental UTXO models, signing, and a bounded native VM
with explicit static accounting, plus a standalone ordinary-transaction validator, parameterized P05/P06/C16
monetary arithmetic (029), and VM context introspection plus Merkle-proof
opcodes (030), with root's field-size hint validation (031) and the signed compiler token merge in ordinary-validator tests (032). Patch 033 adds wide arithmetic and CHECKDATASIG execution. Patch 034 adds an in-memory ordinary-block connect/undo model. It does not call lotusd `ConnectTip`, and lotusd has not accepted a V2 block. These remain isolated modules: daemon consensus,
persistent chainstate, full transaction/block resource validation,
and mining job integration are still outstanding.

Root review reproduced and corrected maximum-count proof arithmetic, enforced the
8192-byte witness limit, reviewed prepared signing and incremental-tree ownership,
and reran native primitive checks. All 33 mailboxes replay to the recorded trees.
On the 032 tree, the native VM agrees with Python on 363 execution and 494 static-charge cases, plus 3,017 independent byte/arithmetic vectors and 684 Merkle vectors; 103 assigned operations execute and 6 (b0–b4, bd) reject as unsupported. That six-opcode rejection is historical for the 032 tree and is not the current status. In the 033 candidate, b0–b4 and bd execute, and the Python Merkle cost model exists. Native monetary arithmetic agrees with the Python reference on 300 packet and 20,000 root differential vectors. P05 field-size hints are validated against the authenticated transaction. The native stack and the Python reference now derive absent hints for the variable-length field opcodes when an execution context is present. A smaller caller hint still fails. Patch 035 carries that derivation. Patches 036–041 add the development genesis fixture, the local header template, the 256-attempt nonce search, the file-backed UTXO store, and the failing-script rollback tests. Patches 042–045 add the Bitcoin header-parser boundary, the child-header sealer, the harness link, and the ordered transaction root. Replay of patches 000–054 ends at tree 2e5411d50bd0e604afcb9424d318a1cdf1b657c8. Patches 046–048 add the monetary snapshot, the in-memory BIP340 CHECKSIG spend, and the per-transaction UTXO commit. Patch 049 writes one monetary snapshot after a successful ordinary connect and restores the parent if that write fails. Patch 050 pins the development genesis state root to 3ecef0a5a8524cde7fa2921c52256c5a4306783c6d24e8604ec2b6288ec39acf. Patch 051 reopens those two stores after connect. Patch 052 adds a header file snapshot of the existing 134-byte header and BlockId. Patch 053 stores one sealed child header. Patch 054 stores a second sealed header whose previous id is the first header's BlockId. Replay of patches 000–055 ends at tree b1c900c40a25f41a896bad5d3b1df0da6e6acd20. Patch 055 adds the genesis-anchored ASERT candidate. Half-life 172800 and spacing 120 are caller arguments, not chainparams. Replay of patches 000–056 ends at tree 9a3e3e57aa6ee0c0430144ee1200ab9cbe48f6e7. Patch 056 accounts a development coinbase through the existing AdvanceMonetary fields. Its previous id is the parent BlockId and its previous index is the candidate height. A bare development genesis cannot pay the coinbase byte charge. lotusd has not accepted a V2 block.
Signed compiler mint/transfer/merge fixtures execute all selected invocations in
both engines, including rejection cases. Whole-daemon V2 validity, inherited
unit/functional suites, Chronik and network integration remain separate gates.

### Conformance integration through 069 (October 15)

The [ordered gap audit](../../docs/plans/lotus-v2-conformance-gap-audit.md)
records specification ownership and remaining limitations. Patches 057–059 add
contextual header/ASERT validation and valid nonmonotone-time history coverage.
Patches 060–062 and 064–067 add authenticated signing contexts to the native
runner, immutable transaction preparation, negative signing cases and explicit
coverage limits. Patch 063 preserves complete block sizes in header snapshots.
Patch 068 corrects token amounts entering native monetary totals. Patch 069 adds
complete framed-block acceptance with first-only coinbase, duplicate TxID checks,
child-target work, actual frame charges, contextual headers and atomic in-memory
state validation. Its outer cost schedule is an explicit uncalibrated development
model; full-view copying and bounded ancestor verification overhead are not a
measured resource bound.

Fresh replay checks all 70 intermediate trees and ends at `5eadbbf0d3149be54eab8955178b26e09da2c728`.
[Replay evidence](evidence/v2-series-replay-069.json) records source hashes and
expected trees. Mailboxes 000–056, including the binary CSV in 033, are unchanged.
The integrated source passes eight native block suites and the native VM suite;
the combined reference passes 94 tests. The compiler passes 126 tests with no
skips, including authenticated native/Python linked invocations and reference
partial-fill orders. These counts describe their respective suites, not every
V2 requirement. The retained Merkle-cost prose discrepancy and optimizer budget
mismatch remain visible in their reports.

The [separate development profile](../../docs/lotus-v2/development-profile.md)
is proposed only. Its embedded generator reproduces complete genesis and first
block bytes, reference acceptance, overclaim rejection and undo. Existing genesis
fixtures remain unchanged. At the 069 milestone, no daemon had accepted a V2 block. Its next gates were
atomic persistent chainstate/undo with restart and crash evidence, a daemon path
calling the tested complete connector, and reviewed development profile/peering
integration. Absolute reward scheduling is under separate research; the stored
inductive recurrence remains implemented.

### Preserved overnight implementation

The six exported patches are committed in monorepo `efb4d95f6cd19697f32bb10bc47a5a2f56b7e6e5` (October 14, 06:16 PDT), also confirmed on remote branch `lotus-v2` during this review. The source workspace is `/private/tmp/lotus-v2-repo/daemon/workspace-v2`, branch `lotus-v2-work`, clean at `560acd2500` with six commits above the pinned ABC base. Built `build/src/lotusd` and `build/src/lotus-cli` are present. The similarly named `/Users/shammah/repos/lotus/daemon/workspace-v2` is an older, different workspace; do not reset or confuse it with the overnight implementation.

The [worker handoff](../../AGENTS.md#v2-implementation-continuation-2026-10-14) records exact six-patch temporary-index replay agreement, builds of daemon/CLI/test binary with Chronik disabled, `util_tests/test_FormatUserAgent`, isolated `interface_rpc.py`, and version/help checks as passing. These are preserved historical results, not reruns by this planning review. Full C++/Chronik coverage and V2 consensus conformance remain unestablished; upstream network/genesis parameters remain in this development source. Compare patch 001 with the later corrected V1 scheduler before treating that shared-fix gate as complete.

V2 uses its own ABC-based series and selectively carries forward verified Lotus V1 changes. It does **not** apply this series on top of an entire V1 patch stack: doing so would duplicate changes and import obsolete protocol rules. Preserve the validated V1 source/patch provenance as the compatibility and implementation reference. Before promoting a V2 daemon candidate, record the exact V1 reference commit, ABC base, V2 patch digests, ordered replay tree and relevant shared-fix regression results. Shared fixes must retain the corrected custom mining scheduler; never substitute the superseded upstream-assembler restoration.

The maintainer's October 14 V1 evidence identifies corrected source `0b7939e926b8353ad09d8edc47f355ddacc30502`, tree `73e9db8356d5f9e617f40d4d9228209e117b08f0`, with Chronik-enabled builds, all 156 C++ checks, isolated mainnet replay and RPC parity. That is reported V1 evidence, not validation of this V2 series or a declaration that release assets were published. Resolve and preserve that reference when preparing implementation; do not reset an existing workspace to obtain it.

[series-legacy-plan.txt](../patches/v2/series-legacy-plan.txt) is historical inventory only. Its old ABC pin, issuance patches, opcode numbers, V1 checkpoints/seeds and genesis placeholders are not an application or launch recipe. Existing V1 daemon, chain data and published releases remain independent.

## Milestones and acceptance gates

Every milestone must record source/spec/parameter digests, reproducible commands, expected and actual results, and remaining limitations in the [validation ledger](lotus-validation-results.md). The structural checker is useful preparation, not the reference evaluator or an independent implementation. All milestones below remain incomplete until their evidence is recorded.

| ID | Deliverable and dependencies | Required completion evidence |
| --- | --- | --- |
| V2-00 | Accepted implementation profile for P01–P06; D01–D15 closure matrix | Exact candidate encoding, opcode registry, signature profiles, tree domains, resource algebra and parameter choices. Each open value has an owner and blocks the affected acceptance gate; no placeholder silently becomes a production constant. |
| V2-01 | Independent parser, assembler, evaluator and vector corpus; accepted V2-00 payment slice | Canonical serialization and rejection cases, signed payment, independently verified identities/signatures, typed trees, exact cost/accounting results. Replace pseudocode examples with executable examples. A second implementation must independently check consensus results before launch. |
| V2-02 | Daemon payment/block/state slice; V2-01 and isolated development-chain profile | Clean patch replay/build; fresh regtest genesis; wallet-generated signed payment; daemon/reference agreement on transaction, header and state roots; connect/disconnect and restart restore exact state. Inherited Bitcoin/V1 transaction and block parsers cannot accept V2 by accident. |
| V2-03 | Native assets, minting, burn outputs and asset-aware RPC; V2-02 | Conservation, mint authorization/context, token IDs, burn accounting, invalid/malformed cases and reorgs. Wallet/indexer distinguish native and token amounts and consuming versus mint inputs. |
| V2-04 | Complete VM, ABI and resource enforcement; V2-02, D07–D09 | All 215 assigned opcodes and 41 success bytes checked against the registry; script scanning, numeric/signature boundaries, nested enumeration, branch continuation and input × output covenants. Frozen accounting costs and stricter enforcement costs produce the specified state roots and burn floors. |
| V2-05 | Monetary state, difficulty/time, Avalanche payout policy and authenticated persistence; V2-02 and integrated V2-04 costs | Exact bootstrap/tail recurrence, fee/burn/reward transitions, genesis/height-1 indexing, ASERT and time eligibility, state proofs, atomic undo/restart. Economic simulation and payout-profile evidence described below. |
| V2-06 | Miner/pool implementation and measured optimization; V2-02, integrated V2-04/V2-05 | CPU and GPU hash agreement, accepted mined development blocks, pool/template mutation tests, scalar-equivalent caches/batches, bounded resource behavior and measured performance. See miner contract below. |
| V2-07 | SDK/wallet/indexer integration, network qualification and reproducible genesis/release; V2-00–V2-06 complete | Cross-component conformance, independent consensus review, multi-node development-chain replay/reorg/recovery, final manifest and independently reproduced genesis. Mainnet publication/launch is a separate explicit action after all blockers close. |

Development-chain genesis blocks and provisional parameters are necessary in V2-02 and may be replaced. Only the final mainnet genesis waits for all specification and parameter freeze gates. V2-03–V2-05 can progress separately after their interfaces are stable; none is evidence that the combined state transition works until integration passes.

## V1 reuse and replacement map

References below are source leads under [patches/v1](../patches/v1), not instructions to apply entire ranges. For each imported behavior record its original patch/commit, current source location, disposition (`reuse`, `adapt`, `already upstream`, `replace`, `retire`) and replacement commit/tests. The same audit applies to every inherited chain parameter and legacy V2 patch.

| V1 reference | V2 disposition and requirements |
| --- | --- |
| `000-decouple-avalanche.patch` | Adapt separation of hard consensus and parking. Reuse ABC staking winner/payout machinery as P06 policy; do not restore a hard-coded V1 miner fund or introduce treasury contracts. |
| `001-nlogn-block-construction.patch`, `002-remove-chaintx-limit.patch` | Retain the corrected dependency snapshot/ready-heap algorithm and its native regressions. Adapt transaction identities, dependency edges, live resource/fee accounting and reward-funded coinbase costs. Test diamonds, repeated parents, failed parents, fee deltas and constrained templates. |
| `004-start-asert-from-after-genesis.patch`, `005`–`026` activation/validation patches | Audit individually. P04 uses a fixed genesis ASERT anchor; P01–P03 define new validity from genesis. Do not carry forward old script flags, BIP34 scriptSig parsing, historical exceptions or activation dates as V2 rules. |
| `071`–`079` Taproot work; `101-implement-malfix.patch`; `105-new-lotus-sighash.patch` | Use implementation lessons/tests, replace protocol bytes with P01–P03 branch/path authorization, core/full identities and signing domains. V1 signatures, opcode bytes and Taproot output templates are not V2 encodings. |
| `087-add-log2fixedpoint.patch`, `088`, `095` issuance changes | Reuse audited integer-math techniques where applicable. Replace V1 issuance with P06 bootstrap reserve plus adaptive tail; no legacy issuance runtime switch in production. |
| `094-new-lotus-block-header.patch`, `099` template fix, `115` mining API | Adapt recursive-header/mining interface lessons to P04's 134-byte header and tagged BLAKE3. Replace V1 metadata/header offsets and SHA256 mining code; see the end-to-end miner gate. |
| `102`–`104`, `107`, `110`, `114` address/denomination changes | Reuse codec structure only after D14 selects the V2 address/network profile. Encode 10^6 atoms/XPI consistently in RPC, SDKs, wallets and miner payouts; prevent V1/V2 destination confusion. |
| `025`, `078`, `080`, `084`, `089`–`090`, `098`, `118`–`119` network/genesis settings | Replace network identity, datadir, ports, genesis, checkpoints and seeds. Never copy V1 or ABC chain commitments into the new chain. |
| `155`, `158`, `175` NNG; `240` address RPC; `246` Chronik/RTT integration | Adapt enabled notifications, indexing and target-time plumbing. Rebuild transaction/header/disk-offset and address schemas for V2; V1's 160-byte headers and dual identities are reference tests, not compatible formats. |

V1 patches can contain unrelated historical changes. Review actual diff hunks, not filenames alone. Keep executable manifests free of empty placeholders and prove ordered replay before claiming an implementation candidate exists.

## Miner and pool contract (V2-06)

Update the repository's [miner](../../miner), including its Rust block/template parser, CPU verifier, OpenCL kernels, library, CLI and GUI. The V2 branch now includes the maintained V1 miner plus tested P04 CPU and OpenCL hashing, explicit protocol selection and fallible startup configuration. The [six-patch review packet](../candidates/v2-miner-20261014/README.md) records exact source trees and validation. V2 network mining remains disabled until daemon jobs and scheduling are integrated. Merely updating the daemon's block assembler does not complete mining support.

The miner must preserve V1 mining while adding explicit protocol selection (proposed CLI `--protocol=v1|v2`, with an equivalent GUI setting and V1 as the default). Selection binds the template parser, header serialization, hash function, target interpretation and GPU kernel together; a raw kernel switch alone is insufficient. Reject a mismatched chain/job/profile and fail clearly if the chosen backend is unavailable. Until end-to-end V2 support is implemented, selecting V2 must report unsupported operation rather than run the V1 kernel. Use the newer maintained miner on `main` as the porting reference, preserving its packaging and toolchain fixes when integrating onto the older V2 branch.

Deliver this in reviewable slices: explicit dispatch and V1 regressions; independent V2 CPU hashing; OpenCL BLAKE3 kernel with CPU/GPU parity; daemon job/submission integration; then an actually mined development block accepted by the full daemon. Each slice records whether V2 mining is usable; a flag or hash benchmark alone does not close V2-06.

1. Implement P04 byte-for-byte: little-endian fields, u48 timestamp, u64 nonce, header/body/work disclosures, domain-tagged BLAKE3 and target comparison. Compare **BlockID**, not intermediate WorkHash, against the target. Independently verify full-header, CPU and GPU results, including nonce carries, maximum values and target equality/boundaries.
2. Specify the daemon job/template and submission API: chain identity/profile, parent, height, target, allowed time range, transactions, coinbase construction, fees, payout policy, and all commitments. A job must identify which fields workers may mutate and which commitments must be recomputed. Freeze matching SDK/pool wire examples.
3. Support miner vanity/extranonce data. The maintainer requested one optional opaque coinbase argument, never executed or success-scanned, committed by both identities and charged as bytes. P01/P04 now specify `CoinbaseData = Vec(Bytes(data))`: count zero or one, present payload 1..8192 bytes, wholly retained in both core/full input projections. Implement and independently check these exact bytes; this remains a draft profile. Parent ID and derived height remain mandatory and cannot be overwritten by miner data.
4. Rebuild dependent coinbase identities, output outpoints, transaction root, post-state root, exact block size and BodyHash when a permitted template mutation requires it. Nonce-only updates do not change BodyHash. Workers cannot submit arbitrary state roots; the daemon independently validates the complete block and resource-adjusted reward.
5. Partition work among workers; test stale jobs, parent changes/reorgs, cancellation, duplicate shares, nonce range rollover, time rolling, payout changes and malformed submissions. Include opaque payloads containing opcode-like bytes. Verify that actual GPU-produced development blocks are accepted by an independent CPU validator and the daemon.
6. Package supported miner platforms and record reproducible builds and measured hash rates/resource use. Do not promote the spec's illustrative nanosecond claims to measured results. If a platform lacks a working GPU backend, report that limitation explicitly.

## Monetary, coinbase and state contract (V2-05)

Implement 1,000 atoms per decimal kB and the P05 reward-funded coinbase/envelope charge. Test exact and one-atom-excess claims, odd fees, token burns, zero ordinary transactions and insufficient entitlement. Distinguish explicit native burns from miner underclaim and count each supply reduction once. Freeze accounting-cost rules for monetary EMA/state commitments while allowing only the specified stricter enforcement behavior.

Genesis has zero native issuance and initializes `(R0, T0, W_-1, E0)` without advancing the recurrence. Height 1 performs monetary step 0. Commit and restore all monetary fields with the UTXO transition; test restart/reorg across the first blocks and fee/resource boundaries.

Coinbase parent ID and height are context-validated fixed input fields, not arbitrary witness bytes. Reject incorrect parent/height and u32 height overflow; retain duplicate-TxID-in-block and occupied-outpoint protections. Identical coinbases on competing sibling blocks are not a global duplicate ban. Require connect/disconnect tests demonstrating no UTXO overwrite and exact restoration, even if an old coinbase is fully spent. Optional vanity data must not be necessary for uniqueness along a chain.

Reuse ABC's Avalanche staking payout policy with an explicit V2 profile: fraction, activation, eligible winners, absent/alternative winners, replay/reorg behavior and payout basis after required resource deductions. Local quorum state cannot become hard block validity. This is not a treasury contract or monetary-state extension.

Calibrate P06 constants before freeze. Incorporate Frank's burn-to-speak demand: a fiat burn budget `A` at price `P` buys `A/P` XPI of burns, conditional on real adoption and budget persistence. Model changing adoption/budgets, mining response lag, hardware/energy costs, tail bounds, integer rounding, price/demand shocks and fee burns. A $1 reference price and eventual trillions of XPI are design scenarios, not a peg or a proven supply trajectory. At constant 250,000 XPI tail per 120-second block, annual issuance is 65.7 billion XPI (365 days), requiring equivalent aggregate annual burns for steady supply after bootstrap; this is not a launch demand assumption. P06/rationale now include this context and exact paper provenance. Simulations and D10 parameter closure remain pending.

## Compiler and generated ABI tooling

The [compiler/ABI plan](../../docs/plans/lotus-v2-compiler-abi.md) adds CABI-00–CABI-06: canonical assembler, typed contract compiler, versioned artifacts, generated Python and TypeScript bindings, independent execution/stress harness and later optimization. Begin schema/assembler work alongside V2-01, then compile the worked contracts as V2-04 semantics land. A compiler-generated signed payment accepted by independent engines is an explicit integration gate; complete application/block tests wait for chain transitions. Compiler work does not require final genesis parameter freeze.

## SDK, wallet, indexer and node integration (V2-07)

- Publish exact schemas and independent vectors for transactions, addresses, signing modes, blocks, proofs and amounts. Audit in-repository Rust/Dart SDKs plus the maintained Frank TypeScript/wallet integration in `~/repos/frank`; changes in that separate repository require their own revision/evidence records.
- Wallets must construct and sign V2 payments, select paths/branches, distinguish tokens/burn outputs and display partial-signature intent. Test change, fee estimation, coinbase maturity, locks, multi-party signing and reorg recovery.
- Chronik and any enabled NNG interface must decode V2 disk framing, distinguish TxID/TxHash, index assets/branches and supply correct raw bytes and connect/disconnect notifications. Compare RPC, indexer and independent decoding on coinbase, payment, mint, burn and covenant fixtures.
- Implement atomic block/UTXO/monetary/undo persistence; prove crash/restart behavior before asynchronous-write optimizations. Authenticate state-query proofs and define snapshot completeness/trust/import behavior separately from root verification.
- Exercise peer framing, header synchronization, malformed/oversized inputs, chain selection, mempool dependencies, relay/resource limits and cross-network rejection. New transport or advisory voting cannot change consensus results.

## Reproducible genesis and launch gate

The final manifest must contain exact serialized parameters, their digest and all resulting genesis artifacts. Close D01–D15 and map C01–C28 (including subrequirements) to passing independent evidence before freezing it.

1. Select ChainID independently, before hashing genesis, avoiding any circular definition through the genesis hash. Freeze transaction/header versions, address encoding, message magic, ports, datadirs/database versions and separate mainnet/testnet/regtest profiles.
2. Freeze opcode registry and domains, signature acceptance, parser/VM limits, primitive cost weights, fee/burn rules, maturity/locks, ASERT anchor/half-life/target and time eligibility. Freeze P06 reserve/tail bounds and initial work/EMA values; candidate values are not automatically approved.
3. Specify exact genesis coinbase bytes, optional data, native-zero outputs, parent zero and height zero. Compute its identities, ordered transaction root, initial UTXO root and unchanged initial monetary-state commitment according to P01/P02. Resolve genesis resource/claim applicability explicitly; an ordinary-block reward deduction must not accidentally make zero-issuance genesis impossible.
4. Serialize the complete block and exact size; generate BodyHash, WorkHash and BlockID with a reproducible genesis tool. Search the frozen nonce/time space and save full bytes, nonce, hashes, decoded target, roots and generator source/build identity. Recompute from scratch with an independent implementation and verify proof of work and full genesis rules.
5. Install only these verified artifacts into chain parameters and fixtures. Remove inherited checkpoints, assumed-valid/assumeutxo data, minimum-chainwork assumptions and seeds unless independently appropriate for this chain. Use owned, tested seed infrastructure and document bootstrap procedures.
6. Run a final multi-node rehearsal with these binaries/profiles: fresh datadirs, mining and payouts, wallet transfers/assets, indexer agreement, restart, fork/reorg and state recovery. Reproduce release packages and document operational recovery and V1/V2 separation. No automatic coin/database migration is implied.
7. Record independent review, every acceptance result and the exact release commit/manifest/build hashes. Obtain the separate launch/publication instruction before publishing network artifacts or starting public services. A mined placeholder does not close a missing consensus decision.

## Test migration

The compiler plan also owns [V2-native fixture infrastructure](../../docs/plans/lotus-v2-compiler-abi.md#v2-native-test-fixture-infrastructure): deterministic basic-contract builders, offline JSON bundles for native/functional tests, and an inventory distinguishing reusable, migrated, retired and new tests. Preserve rejection intent and independently hand-encoded vectors. A compiler-generated signature-valid transaction is not a full-validity fixture until the relevant VM/accounting/block checks pass.

## Disk validation and SQLite wallet evidence (patches 070–080)

The 81-entry series replays from the pinned ABC base with every intermediate
source tree checked. Final tree: `739cfb30718475b24421e8143cdaed877977d1f8`.
See [replay evidence](evidence/v2-series-replay-080.json).

Storage-independent complete-block validation now stages coin, authenticated-tree,
monetary and header changes before one synchronous LevelDB batch publishes them
with immutable undo and complete block bytes. Reads authenticate stored coins;
backend faults remain operational errors. The store binds the full validator
parameter fingerprint. Tests cover restart, disconnect, reconnect, resource
limits and injected storage failures. Eight block tests and both disk suites pass.
The cache is bounded; pending block overlays and undo consume additional memory.
Undo pruning, full startup integrity scans and a daemon chain coordinator remain
open. These are module results, not `lotusd` V2 acceptance.

V2 wallet storage is SQLite-only (`wallet.sqlite`). BerkeleyDB sources, discovery,
link requirements and dependency selection are removed; no legacy `wallet.dat`
loading or migration is supported. The wallet packet builds daemon, CLI, wallet
tool and unit tests without BerkeleyDB. Nine wallet suites (40 cases) and an
isolated ABC regtest wallet test pass, including encryption, reopening, backup,
restore and foreign-format rejection. That evidence is for the wallet packet's
exact source, not a full combined-tree daemon build or V2 transaction signing.
The storage development marker still needs binding to an adopted network profile.

## Full build, restart context and undo integrity (patches 081–083)

All 84 mailboxes replay with exact intermediate trees; final tree
`304e8896364cd69bd92aece89427687811feb844`.
See [replay evidence](evidence/v2-series-replay-083.json).

The full ABC build now exposes the V2 validation library and disk checks. A fresh
Debug clone builds daemon, CLI and SQLite wallet tool, and passes both disk
checks with Chronik off. Building this library does not enable V2 daemon acceptance.

Disk transitions persist the newest eleven headers with complete block bytes.
The stored connector authenticates the linked window against the stored tip and
derives height/MTP after reopen and disconnect; caller-stale values are replaced.
The reader checks stored body header and length, not full transaction validity.
Trusted initial-state construction remains the enclosing initializer's job.
Malformed history tests pass; eleven-header rollover coverage remains pending.

A reproduced corruption of an undo record's old coin previously published an
inconsistent restored state. Disconnect now authenticates changed restored coins,
reachable tree paths and immediate child records before its atomic write.
Eight corruption cases leave the current state unchanged. Debug and sanitizer
checks pass for the repair, and both disk suites pass on the combined source.
Opaque header/monetary metadata semantics remain validator-owned.

## Rollover, clock admission and peer codecs (patches 084–092)

All 93 mailboxes replay with exact intermediate trees, ending at
`98de8af521031cec003a41372810a2ff90611c98`.
See [replay evidence](evidence/v2-series-replay-092.json).

Complete synthetic-funded blocks at heights 11 and 12 now test the eleven-header
rollover, exact MTP, disconnect, reopen and reconnect. This closes the rollover
coverage item above. Explicit caller clock/window arguments control reversible
future-time deferral before state mutation. Boundary acceptance, backward clocks,
u64 extremes and separate invalid/storage errors pass native disk tests.

The parameterized TCP envelope and compact-block codec library is available in
the full build. It preserves complete witness-specific transaction identities,
bounds framing/allocation, and distinguishes malformed messages, capacity refusal,
full-block fallback and unvalidated reconstruction. Review repaired low-limit
handshake framing, prefilled-byte quota checks and stale-response ambiguity.
Production-code Debug tests and standalone synthetic-collision sanitizer tests
pass. A successful codec result is not chain acceptance. Socket lifecycle,
handshake ordering/timeouts, bounded per-peer/global request guards, download
scheduling and chain synchronization remain runtime integration work.

Header profiles now support an exact genesis BlockID; storage fingerprint version
2 includes it. Nonzero anchors reject another genesis despite matching time and
target. Existing incompatible stores fail closed, without automatic migration.
Zero anchors remain for synthetic module fixtures only: the forthcoming daemon
initializer must require a nonzero manifest anchor and validate complete genesis,
initial state and target/work agreement before opening usable chainstate.

## Explicit development initialization and offline daemon acceptance (093–102)

All 103 mailboxes replay with exact intermediate trees, ending at
`fb01e797cef82ffb3e8db6f89297817fb2390f7e`.
See [replay evidence](evidence/v2-series-replay-102.json). Existing patches 000–092
retain their exact bytes. Mailboxes with initially empty commit bodies carry
explicitly attributed integration review notes; source trees are unchanged.

Native commit `74ac986ec523f1990bce9d1e2732eb4753dbcbcd` was built from a
fresh, clean clone at `/private/tmp/lotus-v2-daemon-command-exact-20261015`.
Debug `lotusd`, `check-lotus-v2-development-chain`, `check-lotus-v2-disk` and
`check-lotus-v2-peer-codec` pass with Chronik off. Build output is retained at
`/private/tmp/lotus-v2-command-exact-build-20261015.log`.

The initializer requires an explicit manifest, exact nonzero genesis identity,
canonical target/work, zero genesis issuance, unchanged initial monetary state,
valid VM schedules and authenticated genesis UTXO/state commitments. Restart
checks retained history and body availability. Chain-aware disconnect validates
restored predecessor metadata before atomic publication and refuses genesis undo.

The separate `lotusd -lotusv2development MANIFEST DATADIR` command supports
`status`, `submit BLOCK_FILE`, and `disconnect EXPECTED_TIP_HEX` before inherited
chain initialization. It starts no sockets, RPC server or Chronik. A dedicated
marked directory rejects legacy-looking data and profile mismatches. Namespace
marker creation is not fsynced; interrupted namespace initialization requires
explicit recovery. LevelDB state batches retain their synchronous write guarantee.

The reproducible `src/lotus_v2/development_command_test/verify.py` process checks
passed against that exact daemon. Evidence and all command results are retained
at `/private/tmp/lotus-v2-command-exact-evidence-20261015/evidence.json`.
Using the proposed profile as explicit offline input, the daemon accepted first
block `a7edf76ddaacd6dd59023be9468e6d0724482fd6f794ebc473d1edd54d66af2b`
with Python-reference state root
`d3a19d0f6d0f7414bdf1ccaaf8eb38c46f28d2c3017ffedf71762fcc28900669`.
Separate-process restart, disconnect to genesis, reconnect, genesis undo refusal,
mutated-body rejection without state change, strict manifest failures and
preservation of legacy-looking directories also pass. This demonstrates offline
V2 daemon acceptance through the explicit development path. It does not demonstrate
peer acceptance, signed mature spending, inherited ConnectTip integration or a
public testnet. The proposed network profile has not been adopted.

## Next bounded work

Finish the TCP/compact-block runtime with handshake ordering/timeouts, bounded
request retention, download scheduling and chain synchronization. Preserve Bitcoin
parsing and mainnet chainparams. Review the proposed development profile before
adoption. The signed Payment pilot below establishes mature spending and one-block
undo/reconnect. Extend coverage to fork selection, token/covenant transactions and
optimizer variants. QUIC remains a separately reviewed
second networking milestone. No public testnet or mainnet parameter freeze is claimed.

## Accepted-block cost diagnostics (patch 103)

All 104 mailboxes replay with exact intermediate trees; final tree
`1ab2e37d3cbcfc739e07d74db9416fb67a4b437a`. See
[replay evidence](evidence/v2-series-replay-103.json). Independent review found no
semantic change: diagnostics retain the authenticated effective costs passed to
monetary validation and appear only after durable acceptance. Integer values use
decimal strings to preserve precision.

Fresh clean native source `dca9abe76` at
`/private/tmp/lotus-v2-daemon-costs-exact-20261015` builds Debug lotusd and passes
development-chain, disk and peer-codec checks with Chronik off. Log:
`/private/tmp/lotus-v2-costs-exact-build-20261015.log`. The process-level verifier
also passes at `/private/tmp/lotus-v2-costs-exact-evidence-20261015`: first-block
accounting/enforcement totals both equal the independent Python value 46,362,
and rejected submissions expose no accepted costs. Restart/undo/reconnect and
malformed-input checks retain their prior scope. This enables full signed compiler
block comparisons without changing schedules or adopting a network profile.

## Signed compiler block pilot and next peer interfaces

Compiler work integrated separately after patch 103 now compiles Payment, funds
its policy with a coinbase, rejects an immature spend and a changed signature at
the intended checks, and accepts the signed mature spend at height 3. The fresh
clean `dca9abe76` daemon and Python reference agree on UTXO/state roots and all
seven exported charges. Separate-process restarts, undo and reconnect pass.
See [compiler pilot](../../tools/lotus-v2-compiler/docs/development-chain-pilot.md)
for exact source, binary hash, commands and evidence. This is offline daemon
acceptance; wallet operation, transaction relay, fork selection and general
optimizer equivalence are still open.

The [session review](../../docs/plans/lotus-v2-peering-session-review.md) records
upstream version suffix behavior and the V2 ordering/capacity boundary. The next
packet is a socket-free, parameterized handshake session with services zero.
Serving validated history needs a separate authenticated body retrieval interface;
legacy service bits cannot substitute for that evidence. Network/profile adoption
and isolated listening-node tests remain pending, without changing the remaining
TCP/compact and QUIC milestone scope.

## Socket-free sessions and retained bodies (104–108)

All 109 mailboxes replay with exact intermediate trees; final tree
`c32e78420c3eacaa30f2de5c68491a7a3060949d`. See
[replay evidence](evidence/v2-series-replay-108.json). Earlier mailbox bytes are
unchanged. The test-only mailbox with an empty original commit body carries an
explicitly attributed integration review note; source payloads are unchanged.

The version codec preserves inherited optional suffixes, nonce defaults and
bounded trailing bytes. The independent session gates hello/verack/application
ordering, fixed monotonic deadlines and receive-limit switching between coalesced
frames. Local services remain zero. Debug and ASan/UBSan suites pass, including
two-session action exchange and tiny advertised limits. Independent review found
no blocker. This packet opens no sockets and makes no history availability claim.

Retained-state reads use the current head or immutable undo record by BlockID,
without scanning the live UTXO set. Persisted/cached head mismatch, malformed
undo records and profile errors fail operationally without changing output.
Debug and ASan/UBSan disk suites pass, including a checksum-preserving persisted
head mutation. Historical reads still allocate the full undo record: this API
does not establish a network memory budget or promise pruning/retention policy.

The enclosing body reader checks complete framing, transaction root, BlockID,
PoW, monetary work and state commitment. Capacity refusal precedes a second
body copy. Missing includes checkpoint metadata without a body. Available does
not assert active-chain membership or rerun historical VM execution. Native
regressions cover current/historical reads, corruption, cap boundaries and
unchanged state/output; synthetic checkpoint cases are explicitly not evidence
of complete-block acceptance.

Clean native commit `7432a0aa1` in
`/private/tmp/lotus-v2-daemon-session-storage-20261015` builds Debug lotusd and
passes full-tree development-chain, disk, peer-codec and peer-session checks with
Chronik off. Log: `/private/tmp/lotus-v2-session-storage-combined.log`. The signed
Payment process pilot also passes on that exact build, retaining roots, all seven
charges, intended signature/maturity rejection, restart and undo/reconnect at
`/private/tmp/lotus-v2-signed-pilot-session-storage-20261015`.

Next runtime dependencies include an indexed active header chain, best-work fork
selection, bounded downloads/reorg recovery and body serving. Profile adoption
and isolated socket tests remain pending. The six-case compiler optimizer block
pilot is integrated separately; its retained cost-cap discrepancies preclude a
general equivalence claim. No public testnet or QUIC readiness is claimed.

## Scoped signing-secret cleanup (109–110)

All 111 mailboxes replay with exact intermediate trees; final tree
`5d2c403287a8783b47e7bb3c140e62093a08cbb1`. See
[replay evidence](evidence/v2-series-replay-110.json). Earlier mailboxes remain
byte-identical. Patch 109 has an explicitly attributed integration note because
the original source commit had no body; its source payload is unchanged.

The local BIP340 signing keypair is now scoped and cleansed on successful signing
and exception exits using ABC's existing memory cleansing primitive. Caller-owned
secret and auxiliary input buffers remain the caller's responsibility. Full-tree
validation links the crypto target; standalone signing consumers compile the same
cleansing source. This adds no wallet format or consensus change.

Root review rebuilt exact source `0e9d9fefc` signing tests in Release at
`/private/tmp/lotus-v2-signer-root-check-20261015`: both the signing-vector and
instrumented cleanup suites pass, including allocation-failure paths. The Release
VM suite and runner build also pass at
`/private/tmp/lotus-v2-vm-cleanse-integration-20261015`. A fresh full daemon build
at `/private/tmp/lotus-v2-daemon-signer-cleanup-20261015` subsequently passed:
Debug lotusd plus development-chain, disk, peer-codec and peer-session checks,
with Chronik off. The checkout is clean at exact native commit `0e9d9fefc`;
build log: `/private/tmp/lotus-v2-signer-cleanup-build.log`. The signed compiler
Payment pilot passes again at
`/private/tmp/lotus-v2-signed-pilot-signer-cleanup-20261015`, including mature spend
acceptance, independent roots/charges, intended negative cases, restart,
undo and reconnect. This remains offline acceptance, without socket activation.

## Indexed development chain and shared home loader (111–114)

All 115 mailboxes replay with exact intermediate trees; final tree
`cafb55a9957cb39e6825e6bb30d021740bd88d88`. See
[replay evidence](evidence/v2-series-replay-114.json). Earlier mailbox bytes are
unchanged; the test-only empty-body commit has an attributed integration note.

Indexed development homes publish header records, active-height mappings and
active summaries in the same synchronous batch as coins, state and undo.
Disconnect retains historical Connected knowledge while removing active mapping.
Generic older homes fail closed; no implicit migration or reset is performed.
Header-only admission verifies PoW and bounded ancestry without accepting a body
or promoting its state root. Locator/header queries use direct height lookups;
single-candidate fork planning enforces actual database-read budgets and explicit
all-ancestor time eligibility. It does not perform global selection or activation.

Debug and ASan/UBSan index/storage suites pass, including an independent Boost
work-arithmetic oracle, corruption, injected writes and reopen checks. Root's
combined Release initializer/disk suites pass. Clean native `97b78c684` at
`/private/tmp/lotus-v2-daemon-indexed-exact-20261015` builds Debug lotusd and passes
full-tree chain-index, development-chain, disk, peer-codec and peer-session checks
with Chronik off. Log: `/private/tmp/lotus-v2-indexed-exact-build.log`.

The shared home loader reuses strict manifest parsing and namespace checks for
offline consumers. Process checks pass at
`/private/tmp/lotus-v2-indexed-command-evidence-20261015`, including malformed
configuration and legacy-looking-directory refusal. The signed Payment pilot
passes at `/private/tmp/lotus-v2-signed-pilot-indexed-20261015`, retaining independent
roots/charges, negative cases, restart, undo and reconnect. Wallet-produced bytes
remain a separate pending pilot; these results do not establish wallet integration.

[Resumable reorg recovery](../../docs/plans/lotus-v2-reorg-recovery.md) remains an
implementation proposal. Per-block atomicity does not establish multi-block
recovery. Network/profile adoption, socket tests and public testnet readiness
remain pending.

## Native wallet and bounded downloads (115–118)

All 119 mailboxes replay with exact intermediate trees; final tree
`b50c03f8522987ff230a1c1eceae2de0b8b4de85`. See
[replay evidence](evidence/v2-series-replay-118.json). Earlier mailboxes remain
byte-identical.

The SQLite-only native Payment wallet owns a fresh encrypted key, binds its
profile and exact compiled policy, resolves funding from authenticated chainstate,
checks maturity and stale plans, validates FULL signatures and persists outgoing
bytes/reservations before export. Failure injection verifies SQLite rollback and
no export. Reconciliation preserves reservations across restart and disconnect;
missing coins alone do not imply confirmation. Independent source review found
no blocker in this caller-serialized offline scope. No legacy wallet.dat import,
Berkeley DB dependency, broadcast or wallet RPC is added.

The socket-free download coordinator bounds jobs, bytes, transaction slots,
cache candidates and retained response guards. Full/compact fallback reserves
the maximum allowance in advance. Deferred work retains its lease; cancellation,
reorg and callback/allocation failure release heavy state while preserving stale
response protection. Debug and ASan/UBSan checks pass, including quota boundaries
and 220 allocation-failure positions. Independent review found and verified fixes
for fallback reservations, temporary-object lifetime and callback reentry.
Callbacks still own consensus/backend budgets and ambiguous-write reconciliation.

Clean source `9f529da1c` in
`/private/tmp/lotus-v2-daemon-wallet-download-exact-20261015` builds Debug lotusd
and the wallet pilot helper with Chronik off. Full-build wallet, download and
initializer checks pass; the wallet run reports 194 observed checks. Log:
`/private/tmp/lotus-v2-wallet-download-build.log`. Root's Debug standalone download
check also passes. Its separate Release attempt stops on the inherited
`crypto/sha256.cpp` unused `SelfTest` warning under NDEBUG and Werror; retained log
`/private/tmp/lotus-v2-download-root-check.log`. No upstream cryptography was changed
to suppress that standalone build limitation.

The compiler harness was integrated separately. Actual encrypted-wallet-produced
Payment bytes pass independent Python and the exact daemon's complete-block checks,
with matching roots and all seven charges, at
`/private/tmp/lotus-v2-wallet-chain-root-exact-20261015`. Native immaturity/stale-plan
refusal, changed-signature block rejection, restart, undo/reconnect and reservation
persistence pass. See the [wallet pilot](../../tools/lotus-v2-compiler/docs/wallet-chain-pilot.md).
The earlier mixed-header/library failure is preserved and the standalone helper
configuration now refuses mismatched dependency roots. Networked wallet use,
resumable fork recovery, selection and socket activation remain incomplete.

The registered Boost wallet test also passes syntax compilation using its actual
`test_bitcoin` compile command from exact `9f529da1c`. This checks registration and
fixture compatibility; it is not a claim that the complete inherited test binary
has been built or executed for this packet.

## Explicit recovery homes and resumable fork switching (119–125)

All 126 mailboxes replay with exact intermediate trees; final tree
`86981cda134577304e58bf58b00cdb5159b6ed00`. See
[replay evidence](evidence/v2-series-replay-125.json). Earlier mailboxes remain
byte-identical. Two empty-body original commits carry explicitly attributed
integration notes without changing their source payloads.

Recovery is opt-in on fresh schema-V3 indexed homes with explicit journal and undo
creation caps. Existing V2 command homes remain unchanged. Journal progress and
active state publish together; ordinary writers are fenced while recovery is
pending. Failed sync poisons the handle until reopen reveals which complete batch
won. Journals embed bounded source/replacement bodies and reserve fixed diagnostic
space; decoding and preparation check body/aggregate allowances before copies.
LevelDB internal block allocation and repeated journal copies remain documented
resource limitations, not claimed total-memory bounds.

The coordinator executes at most one block transition per call through the
existing complete connector and predecessor-checked undo. Tests use immutable
Python-generated complete blocks, first validated by the native oracle, for two
source detaches and three replacement attaches. Invalid-middle replacement,
all-ancestor clock rollback, source-detach operational refusal, restart at every
step and exact journal-cap fallback all restore the expected complete state.
Source operational causes are retained without classifying the target invalid.
Independent Debug/Release tests and focused source review pass. Storage Debug and
ASan/UBSan tests cover corruption, quotas, CAS and injected WAL failures. Darwin
rejects leak detection before execution; the passing sanitizer run disabled that
unsupported feature.

Clean native `11dd297c3` at `/private/tmp/lotus-v2-daemon-recovery-exact-20261015`
builds Debug lotusd and the wallet helper with Chronik off. Full-tree recovery
storage, real-fork, wallet and initializer checks pass. Log:
`/private/tmp/lotus-v2-recovery-build.log`. The actual native-wallet complete-block
pilot also passes at `/private/tmp/lotus-v2-wallet-chain-recovery-exact-20261015`.
That pilot uses the existing offline command; it does not demonstrate daemon
reorg orchestration or peer synchronization.

Candidate selection, durable terminal receipts, cancellation and node integration
remain separate gates. The current generic validator Invalid result includes
some unsupported/provider/host-limit paths; do not turn the coordinator's returned
replacement-invalid flag into a permanent invalid-root fact. A typed failure audit
and repair must precede that selector behavior. No network/profile adoption or
public testnet readiness is claimed.


## Bounded injected-stream transport (126–127)

All 128 mailboxes replay with exact intermediate trees; final tree
`3b6cfed8197ab22e295530098b1d348d90a53c13`. See
[replay evidence](evidence/v2-series-replay-127.json). Existing mailboxes,
including the binary CSV in 033, remain byte-identical.

The transport owns the existing session over a caller-owned, already-connected
nonblocking stream interface. Explicit caps bound logical read buffers, queued
frames and I/O work; fixed frame and handshake deadlines survive partial writes,
trickle reads and coalesced input. Reentry guards, pending-event backpressure,
callback failure and close-once cleanup are tested. These are logical byte bounds,
not process RSS bounds; caller-owned and allocator buffers remain separate.

Independent review found no blocker. Mocked-stream Debug, Release and ASan/UBSan
checks passed; allocation-failure injection remains untested. Root standalone
Debug check passes. Clean native `3fa0c7073` at
`/private/tmp/lotus-v2-daemon-transport-exact-20261015` builds and passes the
full-tree transport, session and download targets with Chronik off. Build log:
`/private/tmp/lotus-v2-transport-build.log`. No full daemon rebuild or live socket
behavior is claimed for this packet. Socket activation, adopted profile,
candidate selection and typed permanent-invalidity evidence remain open gates.


## Typed validation failures and unchanged recovery checkpoints (128–130)

All 131 mailboxes replay with exact intermediate trees; final tree
`2476329a3bef6711174c7d850de4a3aba704e948`. See
[replay evidence](evidence/v2-series-replay-130.json). Existing mailboxes remain
byte-identical. Patch 128 carries an attributed integration explanation for the
original empty commit body, without changing its source diff.

VM provider/allocation failures and local host-step exhaustion now remain
operational; unsupported execution remains U. Ordinary/block validation returns
Inconclusive for these paths. Only an opaque deterministic-failure token binds a
fully authenticated body to its exact parent, validator profile and pre-block
UTXO root. The storage validator fingerprint definition moved unchanged into the
block transition layer. Early header failures retain their existing check order
and conservatively emit no token; this is a documented evidence-coverage limit.

Disk connectors clear optional proof output at entry. Recovery verifies all four
token bindings before recording replacement-invalid diagnostics and never advances
a journal checkpoint on Inconclusive. Wallet and offline command surfaces retain
that distinction. The compiler differential adapter separately retains native E
as operational-error, records inconclusive comparison evidence and exits nonzero.

Focused Debug/Release VM checks cover injected SHA256/provider/allocation failures,
healthy invalid signatures, host-work limits and structural-cost behavior.
Ordinary, complete-block and signed-runner suites pass. A supplemental immutable
reference-generated fork fixture uses an explicitly bound max_steps=1 host guard;
existing fixture bytes and development defaults are unchanged. Its target is
reference-valid and accepts under the ordinary native guard, while the restricted
native run remains inconclusive with no token. Recovery retries across reopen
preserve raw journal bytes, tip, root, money, touched coins, bodies and active
index, and leave output progress untouched. Deterministic invalid-middle rollback
still restores the source. Root standalone Debug recovery/disk suites pass.

Clean native `e8914e477` at
`/private/tmp/lotus-v2-daemon-typed-validation-exact-20261015` builds lotusd and the
wallet helper with Chronik off. Full-tree recovery storage, real-fork, initializer
and wallet checks pass (207 observed wallet checks; nonce-search counts vary).
Log: `/private/tmp/lotus-v2-typed-build.log`. The actual native-wallet signed
complete-block pilot also passes at
`/private/tmp/lotus-v2-wallet-chain-typed-exact-20261015`.

These results supersede the generic-Invalid classification warning for the tested
paths above. Durable terminal receipts, persistent invalid-root propagation,
candidate selection and network activation remain separate integration gates.
No live peer synchronization or public testnet readiness is claimed.


## Candidate selection and durable recovery (131–139)

All 140 mailboxes replay with every intermediate tree checked; final tree
`5bb91c1495838ce19893162fa797f7ffa6c97fdb`. See
[evidence](evidence/v2-series-replay-139.json). Mailboxes 000–130 are unchanged.
Empty source commit bodies in 131, 133, 135, 136 and 138 receive explicitly
attributed integration explanations without changing source payloads.

Explicit opt-in V4 storage adds bounded candidate inventory, work ranking,
terminal recovery receipts and invalid-descendant propagation. V3 remains
supported without automatic migration. Selection uses bounded passes and checks
availability, eligibility and state fences again before dispatch. Choices are
trusted controller data, not cryptographically sealed rankings; recovery Prepare
rechecks definitive fences. The body pool authenticates framing and commitments;
retention is distinct from contextual block acceptance. Pins and logical byte
budgets do not establish a process RSS bound. Connected history is not pruned.

Recovery records deterministic failure against its historical target-parent root,
not the restored source root. Operational failures remain inconclusive. Terminal
receipt creation and journal removal are atomic; acknowledgement and descendant
propagation fence subsequent recovery. Journal checksums detect local corruption,
not malicious disk rewriting. Review also repaired invalid-target dispatch and
aliased-output reentry accounting. V3 journal behavior remains covered.

Clean native `f93ea73fd` at
`/private/tmp/lotus-v2-daemon-candidates-exact-20261015` builds lotusd and the wallet
pilot with Chronik off. Full-tree reorg, wallet, development-chain, candidate-store,
candidate-selection, candidate-body-pool and peer-download checks pass. Wallet
checks observed 191 assertions (nonce-search counts vary). Logs:
`/private/tmp/lotus-v2-candidates-configure.log` and
`/private/tmp/lotus-v2-candidates-build.log`. The signed native-wallet complete-block
pilot passes at `/private/tmp/lotus-v2-wallet-chain-candidates-exact-20261015`.

Root standalone store, selector, recovery/disk, body-pool, download and signing
checks pass. Independent packet checks include Debug/Release and ASan/UBSan
coverage; storage sanitizer checks disabled leak detection. Body-pool checks
exercise allocation failures and pinned-object lifetime. These checks validate
modules and offline complete-block execution. Runtime orchestration, socket
activation and two-node synchronization remain outstanding; this is not evidence
of a usable public testnet.


## Explicit TCP streams and shared manifest parsing (140–142)

All 143 mailboxes replay with every intermediate tree checked; final tree
`6d5ac2f059e4ec757c7d20465225f3f348d51de0`. See
[evidence](evidence/v2-series-replay-142.json). Existing mailboxes 000–139 remain
byte-identical. No partial replay was promoted.

The strict development manifest parser is now callable without opening the
legacy offline command home. It supplies no networking defaults and parsing
alone does not establish genesis validity. The existing command uses the same
parser and initialization path. Clean native `17d6c881e` builds lotusd and the
wallet helper with Chronik off; its signed-wallet complete-block pilot passes at
`/private/tmp/lotus-v2-wallet-chain-runtime-manifest-20261015`. Build logs:
`/private/tmp/lotus-v2-runtime-staging-configure.log` and
`/private/tmp/lotus-v2-runtime-staging-build.log`.

The TCP adapter implements caller-selected numeric IPv4/IPv6 endpoints,
nonblocking connect/listen/accept/read/write, fixed connect deadlines, explicit
readiness polling and descriptor ownership. Interrupted I/O returns WouldBlock;
close does not retry an ambiguous descriptor. SIGPIPE is suppressed on supported
Linux/macOS paths. No DNS, default endpoints, seeds or daemon listener is added.
The abstract stream remains available on other platforms.

Actual macOS arm64 IPv4/IPv6 loopback tests use ephemeral port zero and pass in
Debug and ASan/UBSan. Coverage includes fragmented Transport handshake/application
messages, bounded backpressure, EPIPE survival, failure-preserved outputs,
deadlines, moves and descriptor reuse after close. Independent read-only review
found no blocker. Native `8a4cc1aa7` full-tree build and check-lotus-v2-peer-tcp
also pass in `/private/tmp/lotus-v2-daemon-runtime-staging-20261015`; log
`/private/tmp/lotus-v2-runtime-tcp-build.log`. Linux execution remains unverified.

These are transport tests, not synchronized nodes. The runtime owner, peer
application dispatcher, local block production/transaction submission and actual
two-node synchronization remain integration gates. No published development
network or mainnet parameter selection is implied.


## Bounded development runtime owner (143–145)

All 146 mailboxes replay with every intermediate tree checked; final tree
`0f3fb028b95ef20df63728d65a4a8cd8d2c785d5`. See
[evidence](evidence/v2-series-replay-145.json). Mailboxes 000–142 remain
byte-identical. Each new mailbox retains its source commit explanation.

DevelopmentRuntime owns explicit V4 storage, the body pool and candidate
selector. Each tick performs one selection, preparation, recovery, acknowledgement,
propagation or reopen action. Recovery performs at most one block transition;
its VM/overlay/undo bounds remain separate from selector query limits. Header
insertion preserves in-progress scans and availability epochs. Bodies and chain
changes invalidate cached choices. Inconclusive execution pauses with the exact
journal checkpoint intact. Storage ambiguity discards cached authority and
requires a separate reopen tick; no cached result decides whether a write landed.

The runtime exposes bounded read-only queries without a mutable store handle.
Source restoration uses retained disk bodies even when the volatile pool is
empty. Pool retention remains authentication, not contextual acceptance. Epoch
exhaustion refuses changes before wraparound. Reentrant mutation returns Busy.
Peer fetch epochs must be distinct from selector context generations: immutable
body downloads need not be cancelled by ordinary active-chain growth.

The real-block suite covers competing forks, stale choices, invalid-middle
rollback and exact source restoration, receipt/propagation gates, host-limit
pause/retry/reopen, insertion during bounded scans, callback reentry, capacity
refusal and counter exhaustion. A write injector reports failure after a
successful synchronous write; reopening observes the actual durable detach
checkpoint and resumes. Tests compare monetary bytes, roots, coins/proofs and
raw journal/metadata. Existing golden bytes remain unchanged.

Exact runtime source `86676b778` (agent `d3e86735b`) and tests `1859fe3fa`
(agent `442f73617`) pass strict Debug, ASan/UBSan and independent Release. Final
Release 2/2 passes against test SHA256
`2299f66ea45986af7054fa76c75f094ae1bb45f460be116e28c6a615681dd62e`;
log `/private/tmp/lotus-v2-header-runtime-final-test.log`. Full-tree native
`9345b70ec` builds lotusd and passes check-lotus-v2-development-runtime in
`/private/tmp/lotus-v2-daemon-runtime-staging-20261015`; log
`/private/tmp/lotus-v2-development-runtime-full-build.log`.

This owner has no sockets or implicit profile adoption. Peer application routing,
production of locally mined signed-payment blocks, and a runnable two-process
node remain subsequent gates. Passing this suite alone does not prove network
synchronization or a usable testnet.

## Runtime peer dispatcher (146–151)

All 152 mailboxes replay in a fresh worktree with every intermediate tree
verified; final tree `a016a158d309c188999b2501bb8f738cd1f47d1b`.
See [replay evidence](evidence/v2-series-replay-151.json). Prior mailboxes remain
byte-identical. The public development-home helper preserves the existing
namespace/identity checks without opening storage. The runtime metadata query
now enforces its documented aggregate header, monetary and auxiliary payload cap;
auxiliary-only and one-byte-short caps preserve outputs, and exact caps succeed.
Runtime and disk tests pass (2/2) in the focused Debug build.

The dispatcher routes header pages, full blocks, compact blocks and missing
transactions through the existing transport, shared download manager and runtime.
Fetch epochs survive ordinary tip growth. Serving queries resume across ticks
with budgets of one; timeout and peer work progress with one-action budgets.
Drivers must drain notices before and after ticks. Backpressure retains output,
and terminal connection failures cancel downloads. Storage ambiguity invalidates
cached authority before reopening.

Ten integration groups pass in Debug and ASan/UBSan. They include actual
127.0.0.1 ephemeral TCP synchronization of five blocks between two independent
V4 runtimes, exact tip/root/monetary/coin/proof comparisons, compact completion
and full fallback, invalid-fork restoration, ordinary growth with pending jobs,
WAL write ambiguity and tiny-budget fairness. This is a single-process runtime
test, not yet a two-process daemon demonstration.

Full-tree native `6a527b286` builds lotusd and passes runtime and dispatcher
checks with Chronik off. Log:
`/private/tmp/lotus-v2-dispatcher-full-build.log`. Aggregate metadata boundary
checks: `/private/tmp/lotus-v2-runtime-cap-test.log`. Replay log:
`/private/tmp/lotus-v2-replay-151.log`.

The runnable development node command, local block-template production and
signed-payment propagation remain subsequent gates. No network parameters or
mainnet defaults are frozen by this integration.

## Native production and two-process development nodes (152–162)

All 163 mailboxes replay with every intermediate tree checked in a new replay
worktree; final tree `3ca125eace35c7d933320934711d62628ee78675`.
See [replay evidence](evidence/v2-series-replay-162.json). Mailboxes 000–151 are
byte-identical, including original binary patch 033. The fresh replay through
161 was extended by the separately checked test-only 162 commit.

Block preview reuses the transaction evaluator while preserving Stage's leading
checks and failure-proof authority. Every preview aborts, including Ready. The
assembler performs two aborted previews: a zero claim quotes existing monetary
entitlement and mandatory deductions, then the final fixed-width claim computes
roots and verifies unchanged charge/framing invariants. Supplied signed ordinary
transactions execute in order. Nonce search keeps the existing 256-attempt and
nonwrapping limits. Found bytes still require normal full validation.

The runtime facade owns all access to private profiles/storage. Preview leaves
selector state and epochs unchanged, respects journal/receipt/propagation fences,
and preserves outputs on Busy/Closed access refusal. Allocation refusal is local;
storage failure discards cached authority and requires reopen. Signed dependent
payment tests, exact wire/roots/cost comparisons, raw database preservation,
nonce limits, stale parents and recovery fences pass in Debug and Release.
Final test SHA256 `2008c51c18a445dc80aac931ca366210f3e554a183a3c856d3cd7562e72b3b84`;
Release log `/private/tmp/lotus-v2-assembler-tests-release-test.log`.
Full-tree `b968c50a8` builds lotusd and passes preview, assembler, runtime and
dispatcher checks; `eaecdb04b` also passes the final wrapper test extension.
Logs: `/private/tmp/lotus-v2-runtime-assembly-full-build.log` and
`/private/tmp/lotus-v2-runtime-assembly-final-check.log`.

The explicit `-lotusv2node MANIFEST HOME NETWORK.json` mode owns isolated V4
storage, bounded TCP peers, one download manager and a nonblocking JSONL control
loop. Its entry precedes inherited network initialization. Mainnet parsing,
chainparams and the 80-byte reader are unchanged. Numeric endpoints, magic and
profiles are caller supplied. Notice draining, duplicate-download Busy handling,
serving budgets and transport lifetime fixes were independently reviewed.

Actual node source `cecfdc1ed69c60c72ad5457a0f99c88e8b1e8a01`, binary SHA256
`167cfe2538a9fccfd7cf3e29a70b769a34ae930c349b62772dec9862058bf1f6`,
passes two-process testing with a transparent 50 ms TCP delay relay, fresh homes
and ephemeral loopback ports. Node B synchronizes two full blocks, restarts with
exact persistent state, rejects a known-invalid body with its exact durable
causal root, and accepts the next valid signed-payment block through compact
relay. Reference roots, monetary bytes and coin frames agree; membership and
nonmembership proofs agree between stores. Checkpoints wait for all recovery
flags to clear. All three process starts exit zero and cleanup reports no errors.
See [test protocol and limits](lotus-v2-local-node-check.md) and the
[recorded run](evidence/v2-two-local-nodes-160.json). Raw artifacts remain at
`/private/tmp/lotus-v2-two-real-nodes-quiescent-20261015`.

This run uses independently supplied block bytes. Native interactive production,
wallet submission without competing for the live database lock, and user-facing
local network setup remain subsequent gates. No public service, frozen issuance,
mainnet parameters, QUIC or quicksync capability is claimed.

## Native mining command (163–164)

All 165 intermediate replay trees match; final tree
`536775a80a980e5427c0a958c8bed6f0ac8cb342`. See
[replay evidence](evidence/v2-series-replay-164.json). Earlier mailboxes remain
byte-identical. `mineblock` accepts canonical signed transaction bytes in order,
an explicit zero-valued native coinbase destination, parent/time/claim and a
bounded nonce slice. It performs two abort-only previews and at most 256 nonce
attempts, with no wrapping. Found bytes enter normal admission and retention;
the response explicitly reports pending validation, not acceptance. One mining
request executes per event-loop pass. Typed capacity/reopen failures stay local.
`readblock` serves chunks of at most 64 KiB from previously connected disk bodies;
whole-body reads remain bounded by the manifest cap.

Exact native `3a8b8dcaaa68b095ec2b22611f82e2f4bf29ea37`, binary SHA256
`fdffaaf226fab90220d2c8571cbafb7b675d40db6fe1035014d795c1bf870b34`,
passes real two-process funding, maturity and signed Payment mining. The actual
242/242/450-byte blocks were fetched in 97-byte chunks and independently executed
by the Python reference. Header/transaction/coinbase identities, roots, monetary
bytes, charges, live coins and proofs agree. Peer propagation and restart persist
those results. Twenty-one negative requests preserve the observed chain and
invalidity state, including canonical-number, capacity, stale-parent, immature
and invalid-signature cases. Zero attempts do not mutate state, and exhaustion
at the maximum u64 nonce returns no next nonce. All process starts exit zero.

See [test protocol and scope](lotus-v2-native-mining-check.md) and
[recorded run](evidence/v2-native-mining-164.json). Raw artifacts remain at
`/private/tmp/lotus-v2-native-mining-chunked-20261015`; build log is
`/private/tmp/lotus-v2-native-mine-command-final-build.log`.

The signer in this gate is an independent public fixture. It is not a user-wallet
claim. The existing offline wallet helper cannot open the node's live V4 home;
a proof-verifying provider and controller are separate implementation packets.
No profile adoption, issuance freeze or public listener is implied.

## Authenticated wallet providers and outgoing recovery (165–170)

All 171 replay trees match; final tree
`997831f6ce8d95e0538220e1d01bfeb0f003fd44`. See
[replay evidence](evidence/v2-series-replay-170.json). Earlier mailboxes are
byte-identical. Existing disk Payment APIs now adapt to the same provider-based
engine, preserving deterministic selection, FULL signing, ordinary validation,
anchor rechecks and atomic SQLite outgoing/reservation writes.

The node exposes a bounded `walletcontext` query only at a quiescent authoritative
state. It returns the profile identity, canonical tip/header history, monetary
bytes, UTXO root and an optional coin proof. The native adapter checks exact JSON
shape and correlation, profile binding, header links/MTP, state commitments and
canonical native inclusion/absence proofs. Malformed or unavailable replies are
operational failures, never absent coins. The caller-controlled full node remains
the chain validation authority: eleven headers and coin proofs do not establish
full chain validity. A final anchor check cannot lock an advancing chain through
a subsequent SQLite commit; exported bytes still require node validation.

Read-only outgoing recovery lists at most the existing 1,000 stored IDs and
returns exact persisted signed bytes under a caller byte cap. It works while
locked, preserves reservations, and refuses a wallet requiring reopen. This lets
a client recover after signing persisted but its response was lost; it must not
automatically resign or abandon an uncertain payment. Canonical transaction and
ID checks belong to the consuming client before recovered bytes are returned.

Focused Debug and optimized Release provider suites each pass 2/2, including the
existing wallet regression suite. Optimized local objects link the reviewed
Debug dependencies; this is not a full Release daemon claim. Test source SHA256
`92e0ec3a123332e857705627813818fa1cd1bde126a5a4b125d39a8d0714df69`;
logs `/private/tmp/lotus-v2-provider-tests-debug-ctest.log` and
`/private/tmp/lotus-v2-provider-tests-release-ctest.log`. Mutations cover context,
profiles, headers/history, monetary/root commitments and real coin proofs;
stale-anchor/typed failure cases preserve output and reservations. Disk/provider
unsigned intent matches, and independently randomized signatures validate.

Full-tree `7505c866f` builds lotusd and passes 208 wallet and 481 provider checks
with Chronik off. Log `/private/tmp/lotus-v2-live-wallet-provider-build.log`.
Source review also checks bounded context output including escaped IDs/newline,
quiescence and final identity/root rechecks. The standalone wallet client and
interactive controller are not yet integrated or demonstrated against live
nodes; this packet alone does not close that user-facing workflow gate.


### Private-channel native wallet client (patches 171–172)

A standalone POSIX `lotus-v2-wallet-client` uses the existing encrypted SQLite
wallet and provider-backed PaymentEngine. The controller supplies one private
socketpair for bounded `walletcontext` exchanges and a separate EOF-framed secret
pipe. The client never opens the node database or handles secrets through public
JSON. Pending/export recovery returns persisted canonical transaction bytes with
native identity checks. Ambiguous signing or subsequent output failures report
`outcome_unknown`; callers must recover explicitly without automatic re-signing.

Fresh replay checked all 173 intermediate trees, preserving prior mailboxes,
ending at tree `8ddc44ec9a7bde2a59d3f56dca26705b1ba5762b`.
See `evidence/v2-series-replay-172.json`. Native source
`c605e6e9f12d9fa80a50103d40973531dcdceb95` builds both targets with Chronik off.
Daemon SHA256 `8b8a35603ae1c66c16635522c2a1069db967cb403ef369b73ecae5f8a3bb1de4`;
wallet-client SHA256 `962dc9640e7246306f7513662c838ec0ddabc32383d84b4382dd12b6b5a95eef`.
Build log: `/private/tmp/lotus-v2-wallet-client-full-build.log`.

The exact client passes 21 private-channel boundary checks: encrypted creation,
locked info/pending, strict JSON, secret limits/TTY refusal, malformed and oversized
context replies, correlation, typed stale replies, EOF and a fixed trickle
deadline. Closed stdout exits without SIGPIPE. Evidence is in
`evidence/v2-wallet-client-172.json`, with scripts/logs under
`/private/tmp/lotus-v2-wallet-cli-mock-20261015`. These mock checks do not demonstrate
valid-context signing or an interactive live-node payment; that gate remains
separate and pending.


### Interactive local wallet workflow

The [local controller](../../tools/lotus-v2-devnet/README.md) and
[offline setup guide](../../tools/lotus-v2-devnet/SETUP.md) provide a foreground
playground using the existing checked-in test profile. Setup copies its exact
manifest, pins supplied binaries and creates explicit loopback/ephemeral-port
configuration. It does not start processes, choose production parameters or
reuse existing chain homes. The guide includes a fresh standalone native build
recipe and a two-wallet walkthrough.

The controller keeps node databases owned by their running native processes.
Wallet operations use private socketpairs and the authenticated provider;
passphrases travel over separate private EOF-framed pipes. Policies are compiled
by the shared compiler from the canonical Payment source. Funding and payment
use native template construction, nonce search and normal block admission.
Sign-result ambiguity preserves public recovery information and requires explicit
pending/export recovery rather than automatic re-signing or abandonment.

Independent process tests cover framing/correlation/deadlines, bounded events,
secret transport and cleansing, directory containment, shutdown interruption,
and recovery from lost persisted-signature results. The real-node gate creates
two encrypted wallets, compiles their policies, funds and matures an input,
pays 10000 atoms with a 1000-atom fee, observes the recipient on the other node,
and reopens the newly created node/wallet homes with the same persisted state.
A first 100-atom fee attempt was correctly rejected as below the byte floor;
its evidence is preserved, with no consensus adjustment.

This is an isolated local playground, not a public network launch. Peers exchange
blocks over the current TCP/compact implementation; there is no transaction
mempool relay, QUIC or commitment-based quicksync yet. Mainnet parameters remain
open, Chronik is off, and no production workspace, live chain or release was
modified. Prior module-level and independent reference execution evidence remains
separate from this native wallet/controller integration gate.


The final combined gate passes **19/19** tests (18 process tests and one real-node
flow) in 25.820 seconds. Exact source/test/compiler/binary hashes, command, final
roots and cleanup are recorded in
[evidence/v2-interactive-wallet-172.json](evidence/v2-interactive-wallet-172.json).
The integrated source and both test files match those tested hashes. All four
native node processes, including the two reopened instances, exit 0 with streams
closed and no cleanup errors. The gate also confirms immature-payment refusal
without reservations and byte-identical outgoing export after restart. Final
height is 3, tip `5a23b7500d8d08c50ead1ae8e895f920b80a1f3ea26d632324d982da164a3203`.
Raw public exchanges and preserved earlier outcomes remain in the evidence paths
recorded by that file. No daemon is left running by these checks.
