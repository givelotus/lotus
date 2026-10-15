# Lotus V2 implementation and launch plan

Updated October 14, 2026. Development plan; no genesis parameters are frozen and no launch is authorized by this document. This restores the implementation plan previously present at `5d7d7130`, retaining milestone IDs while updating source routing, specification dependencies and release requirements.

[Consensus](../../docs/lotus-v2/consensus.md) owns validity, [decisions](../../docs/lotus-v2/decisions.md) owns open choices, and [validation](../../docs/lotus-v2/validation.md) owns conformance obligations. A patch existing, applying, building, passing a model, and passing independent consensus validation are separate statuses.

## Source foundation and current status

The current executable [V2 series](../patches/v2/series) contains 34 patches,
`000`–`033`, on ABC master `1fb7db17c176cdea8a2c60d887891589382ee4e3`.
The [review packet](../candidates/v2-native-reviewed-20261014/README.md) records
intermediate replay trees and focused validation through patch 032. That reviewed source tree is
`507c91e64c205df7b38e77abff6ebe02fb99bffe`. It includes transaction framing,
commitments, scalar and incremental UTXO models, signing, and a bounded native VM
with explicit static accounting, plus a standalone ordinary-transaction validator, parameterized P05/P06/C16
monetary arithmetic (029), and VM context introspection plus Merkle-proof
opcodes (030), with root's field-size hint validation (031) and the signed compiler token merge in ordinary-validator tests (032). Patch 033 adds wide arithmetic and CHECKDATASIG execution. These remain isolated modules: daemon consensus,
persistent chainstate, full transaction/block resource validation,
and mining job integration are still outstanding.

Root review reproduced and corrected maximum-count proof arithmetic, enforced the
8192-byte witness limit, reviewed prepared signing and incremental-tree ownership,
and reran native primitive checks. All 33 mailboxes replay to the recorded trees.
On the 032 tree, the native VM agrees with Python on 363 execution and 494 static-charge cases, plus 3,017 independent byte/arithmetic vectors and 684 Merkle vectors; 103 assigned operations execute and 6 (b0–b4, bd) reject as unsupported. That six-opcode rejection is historical for the 032 tree and is not the current status. In the 033 candidate, b0–b4 and bd execute, and the Python Merkle cost model exists. Native monetary arithmetic agrees with the Python reference on 300 packet and 20,000 root differential vectors. P05 field-size hints are validated against, but not yet derived from, authenticated transaction data.
Signed compiler mint/transfer/merge fixtures execute all selected invocations in
both engines, including rejection cases. Whole-daemon V2 validity, inherited
unit/functional suites, Chronik and network integration remain separate gates.

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

## Next bounded work

The coinbase-data and Frank appendix changes are specified. The reviewed 33-patch native series is integrated on the exact ABC pin above; the independent output reference remains `beebcbde`. Patch 033 executes b0–b4 and bd, and the Python Merkle cost model exists. Whole-daemon block acceptance is not done. Derive P05 field sizes from authenticated context, then wire monetary transition into block connect with persistent state/undo, and add mining jobs. Continue with a disposable development genesis/payment/block/undo slice before broad optimization. Do not mark the complete plan implemented merely because documentation, patches or a genesis-search script exist.
