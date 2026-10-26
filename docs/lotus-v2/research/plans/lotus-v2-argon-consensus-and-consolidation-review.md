# Lotus V2 Argon consensus and consolidation review

Status: design review, 2026-10-15. No consensus source, patch payload, manifest,
network, or published asset was changed. No build or node was run for this review.
An independent reviewer must check the proposed ownership and gates before anyone
executes a consolidation or semantic change.

## Scope and source identity

This review checks claims 1, 2 and 7 and the consolidation recommendations against:

- Monorepo `1e01d6c1b7b63a517376e7f5ee8dfe998a37dce8`, tree
  `2bb7b21c119f9b36e11128e645f39633151e987d`.
- Native source `63c51499441ded6d0fe34d87ff43d53a14b1398f`, tree
  `b148281abc3b8a7b599182219835bfc41e2b7ba8`, inspected read-only at
  `/private/tmp/lotus-v2-native-integration-20261015`.
- The 308-entry maintained V2 manifest, patches `000`–`307`, on the monorepo pin.
- Argon's `review-000-086.md`, `review-087-172.md` and
  `review-173-260.md` in
  `/Users/shammah/.gemini/antigravity/brain/636d0566-bb91-4e80-b1e5-2611e231d925/scratch/`.

Those reports name a different scratch checkout and contain source quotations,
patch descriptions, and specification paths that do not match these pins. Treat
their claims as review leads, not an executable rewrite manifest. In this tree P02,
P03 and P05 live under `docs/lotus-v2/decisions/`; the reported
`docs/lotus-v2/protocol/p05-cost-model.md` does not exist. The three report tables
are insufficient to validate a complete 58-commit proposal for `000`–`307`.

## Consensus findings

### 1. Reserving 256 state-tree levels is intentional development accounting

**Disposition: reject the proposed immediate consensus fix. Retain calibration
work as an open design obligation.**

[P02](../../decisions/commitments-and-state.md), “UTXO map,” specifies a
single-leaf-collapsed tree. Its typical depth near 27 for 100 million coins is an
estimate; it also explicitly allows proof depth `0 <= k <= 256`.
Collapsing singleton subtrees does not bound every occupied split to 27. Shared
prefixes can require deeper paths. A fixed expected-depth constant is not a
worst-case bound.

[P05](../../decisions/resources-and-parameters.md), item 7 of transaction
base cost, explicitly permits a conservative per-key charge. Its primitive
weights and economic shifts remain subject to calibration. The
[development profile](../../development-profile.md), section 3, explicitly
selects `conservative-block-cost-1` and gives its complete state-key formula:

```
h(n) = 1 + (n + 64)
state_key(n) = h(36) + h(33 + CompactSizeWidth(n) + n) + 256*h(67)
```

Here `n` is the serialized coin size. Native `block_cost.cpp::StateKey` and
[reference block_cost.py](../../../../tools/lotus-v2-reference/lotus_v2_reference/block_cost.py)
implement that formula. Native `block_cost.h` describes it as an abstract,
uncalibrated development schedule. Neither requires the storage engine to
materialize an uncollapsed tree.

Argon's displayed `CostBenchmarkParams`, `state_lookup_step`, and `state_key_base`
are absent from the pinned code and the actual 069/071 payloads. The real type is
`BlockCostProfile {hash_base, hash_byte, resolve_byte, asset_comparison}`.
For unit coefficients the reserved branch component is `256*132 = 33,792` per
key, or `101,376` for three keys; coin/key hashing is additional and depends on
encoded size. The report's fixed `34,049` complete per-key total therefore does
not describe this implementation. Its comparison with a launch-style `L≈500`
example establishes that this development profile is expensive, not a departure
from its selected accounting rule. Its claimed `2^24` hard block-cost cap is not
a selected parameter of this profile.

No code replacement is justified by this claim. A future calibrated candidate
must specify a deterministic state-work bound, cover adversarial deep-prefix
keys and insertion/deletion collapse, and reproduce costs across backends.
Do not substitute 27, local cache state, measured I/O, or runtime work counters
for the existing consensus charge. If a new formula is approved, implement it in
both engines, regenerate profile artifacts and fixtures, and use a newly
identified disposable development profile as required by its migration rules.
Do not silently reinterpret an existing chain's cost/EMA state.

### 2. Squared comparison allowances are real and explicitly selected

**Disposition: confirm the arithmetic consequence; reject classification as an
unintentional current consensus divergence.**

Native `AuthenticatedTransactionCostsResolved` adds
`(r*r + r + spends)*asset_comparison`, where `r=I+O`.
`AuthenticatedEnvelopeCost` adds `(N*N+N)*asset_comparison`.
Both terms are explicitly documented in the development profile and implemented
in the Python reference. P05 item 6 also requires bounded native/token
aggregation and mint lookup; its subsequent paragraph explicitly rejects an
expected hash-table bound as sufficient consensus reasoning. The report's claim
that no aggregation term exists in P05 is incorrect.

The algebra has the consequence identified by the report: a base charge quadratic
in `r` can produce a fourth-degree transaction effective charge after
`L + ((L*L) >> tx_knee_shift)`. An envelope quadratic in `N` can produce a
fourth-degree block burn term after squaring block cost. For a fixed number of
transactions whose individual fourth-degree effective costs dominate, squaring
that block cost can even give eighth-degree dependence on transaction record
count. These are statements about charged formulas before integer truncation,
width limits and structural caps; they are not measured CPU complexity.
The input/output caps in the development profile are 256 each.

`monetary.cpp::TransactionEffectiveCost`, `BlockEffectiveCost` and
`RequiredBlockBurn` make these stages explicit. No implementation bug follows
solely from the variable name “linear”: it means the base charge before the
parabolic surcharge, and the selected profile deliberately reserves quadratic
comparison work. The profile also acknowledges unpriced oracle bookkeeping and
does not claim a calibrated resource guarantee.

Argon's suggested linear adjacent-TxID-order pass is not the actual decoder:
`block_wire.cpp::CompleteTransactionRoot` uses a `std::set<Hash>` to reject
repeated TxIDs while retaining block transaction order. `DecodeBlockWire` invokes
that routine. A unique sequence need not be sorted by TxID. Removing this work
on the premise that canonical ID sorting is already checked would change the
wrong requirement.

A useful follow-up is a calibration proposal comparing the current bound with a
specified deterministic comparison schedule, including mint/path lookups and
block duplicate detection. Establish an upper bound and rounding/overflow rules
before replacing any quadratic term. Test exact costs, transaction knees, block
burn, EMA recurrence, minimal-block affordability, maximum allowed counts, and
whole-block post-state roots in both engines. Keep this source change separate
from consolidation and include an explicit new profile/migration decision. No
production coefficient is proposed here.

### 7. Branch-query width differences implement the written semantics

**Disposition: no VM semantic change; a small prose correction and stronger
conformance coverage are justified.**

[P03](../../decisions/vm-semantics.md) already distinguishes these cases:

| Opcode | Width rule with an otherwise valid context/index | Evidence |
| --- | --- | --- |
| `dd` UTXOREQUIRESBRANCH | Non-32-byte root returns false | P03 every-path predicate paragraph; native `RequiresBranch`; reference `vm_context.requires_branch` |
| `e8` OUTPUTREQUIRESBRANCH | Non-32-byte root returns false | Same predicate and both engines |
| `e9` OUTPUTEXCLUSIVEBRANCH | Non-32-byte root errors | P03 “root operand must be exactly 32 bytes”; explicit checks in both engines |
| `ea` OUTPUTCONTINUESBRANCH | Non-32-byte root errors; requires a spend invocation | P03 explicit “MUST be exactly 32 bytes, else error”; native `ContinuesBranch` and reference evaluator |

The `dd/e8` predicate is true iff the root is exactly 32 bytes and the other
conditions hold. Existing native `test_vm.cpp` also explicitly checks the `e9`
width failure. Both engines therefore agree on the relevant acceptance behavior;
the asymmetry is not evidence of an accidental implementation mismatch.
Changing `dd/e8` to error would invalidate programs that handle their false
result. Changing `e9/ea` to false would permit programs currently rejected.
Neither belongs in a history cleanup.

The two prose occurrences of `OUTPUTCONTINUESBRANCH (cf)` in P03's continuation
and indexed-proof discussions should say `(ea)`. The opcode table and engines
already use `ea`; `cf` is **CHAINID**, contrary to the report's BIN2NUM statement.
Recommended bounded follow-up: correct those two prose references, clarify that
`e9` malformed width errors, and qualify the burn-output false statement to
valid operands/context so it does not appear to override width errors.
Add a shared test matrix for root lengths 0/31/32/33, matching/nonmatching roots,
spendable/burn outputs, invalid indices and spend/mint contexts. Compare acceptance
and result values, without requiring identical diagnostic ordering when several
operands are invalid. Run the spec candidate checker if editing P03, and update
any document-digest artifacts through their prescribed generator.

## Consolidation boundaries

A smaller series is reasonable, but **58 is a hypothesis, not an acceptance
criterion**. The present numeric map is unsafe. For example, these are the actual
patches at the selected pin:

| Patch | Actual role | Proposed ownership/dependency |
| --- | --- | --- |
| 215 | Registers native Avalanche adapters and runtime checks in CMake | Avalanche proof/quorum/runtime group; split registration hunks only with recorded ownership |
| 216 | Supplies ABC source/generated includes to those adapters | Same native build boundary as 215 |
| 217 | Defines translation hook for native Avalanche test linkage | Native proof/quorum tests, before integrated linking |
| 226 | Registers durable Avalanche peer store and checks | Peer-store 221–225 group plus its native base dependencies |
| 247 | Links native Avalanche driver and integration check | Driver 242/245/246/259 group after peer adapter/runtime dependencies |
| 248 | Matches Chronik Debug lock-order compile definitions to native code | Shared Chronik/CXX build prerequisite, not HTTP mutation guards |
| 258 | Repairs inherited Chronik C++ test lock contracts | Chronik native tests, not HTTP shutdown revocation |

The Argon 173–260 report assigns these numbers to different Rust Chronik DB,
service, test-runner and HTTP changes. Do not count one number in two groups or
move a build change merely because an inaccurate table labels it Chronik.
Similarly, cross-range assignments such as 178–180 to monetary foundations and
to a later monetary group need one destination. A partially split patch such as
061 or 108 needs explicit file/hunk ownership, not two full applications.

### Workstream A: exact-tree candidate history

The consolidation owner should create a new isolated candidate from the pinned
ABC base and retain the original 308 mailboxes unchanged. Before editing history,
produce a machine-readable ledger containing each original ordinal, filename,
source commit, parent/tree, payload digest, destination group, prerequisites,
and reason. Every patch or deliberately split hunk must be assigned exactly once.
A reviewer must reject missing entries, overlaps, unknown numbers and dependencies
on an unintroduced API or test fixture.

Use this broad dependency order to organize that ledger, with finer splits where
reviewability or intermediate buildability requires them:

1. Inherited-node policy/activation/miner/identity changes and their test repairs.
2. Header/hash/codec/commitment/state primitives, signing and VM with their tests.
3. Ordinary validation, monetary/profile/context and complete block transition.
4. Disk state, genesis binding, historical reads/index and recovery/runtime.
5. Session/transport/download/dispatcher and preview/assembly/node integration.
6. Wallet/provider/client and pool/history/relay integration after their APIs.
7. Native Avalanche proof/quorum, durable runtime decisions, peer store,
   negotiated adapter, driver and development-node lifecycle.
8. Chronik decoding/query/database, bridge/service/authority, native sync,
   explorer schema3 and node authority wiring after required facts APIs.

These are dependency domains, not eight final commits. Shared dependencies can
interleave domains. In particular, postpone runtime assembly-facade hunks until
assembler APIs exist; define `HeaderClock` before the node links a caller;
introduce recovery/index APIs before their consumers. Retain focused tests and
build registration in the earliest group where all prerequisites exist.

Patches 261–300 require their own verified ledger for Avalanche provisioning and
explorer integration. The three supplied reports do not establish coverage of
those additions. The following later patches also cannot be omitted:

| Patch | Required final behavior | Destination constraints |
| --- | --- | --- |
| 301 | Batch cache bounds overlapping Avalanche ancestry reads | Runtime Avalanche decisions plus its standalone regression project |
| 302 | Request fences separate from durable explorer generations | Chronik service/FFI/HTTP authority after schema3 explorer APIs; preserve authority tests |
| 303 | Unchanged native turns retain explorer tokens | Node-to-Chronik publication integration, dependent on corrected authority semantics |
| 304 | Recover pending native work before Avalanche startup; preserve peer cache on stop | Node/runtime/driver lifecycle plus dedicated lifecycle tests |
| 305 | Documents peer-cache persistence during recovery | Same final lifecycle behavior as 304 |
| 306 | Initial-download completion latch | Node progress/authority boundary plus both new test executables |
| 307 | Terminal connections are peer outcomes; local failures stay failures | Peer adapter/driver/node error contract plus updated peer/driver tests |

Preserve patch 033's binary literal for `vm_test/bip340_test_vectors.csv` and its
use by `differential_wide.py`. Export with binary-capable Git mailboxes. Preserve
exact blob IDs, modes and content, not just text-diff statistics or line-ending
normalization. The actual 033 payload changes seven files and includes wide
arithmetic, static cost, differential tests and the CSV; the report's narrower
three-file description is insufficient for ownership.

Acceptance gates for this history-only candidate:

- Replay all exported candidate mailboxes independently from the immutable base;
  final tree must be exactly `b148281abc3b8a7b599182219835bfc41e2b7ba8`.
- Record a fresh tree at every candidate boundary and compile/link the available
  daemon, CLI and test targets at **every** intermediate commit. Run every
  registered test/check target at that commit, including introduced standalone
  projects. CTest alone misses the integrated `check-lotus-v2-*` custom targets.
  Discover and retain both forms, plus relevant Rust checks when introduced.
- Check Debug and Release and the intended feature variants through a documented
  gate matrix; no intermediate “temporarily broken until the next commit” waiver.
  Reorder or merge related groups if a boundary fails. An inherited failure needs
  a separate reviewed fix or blocks approval; do not hide it by dropping a test.
- Preserve authorship and explicit maintenance-message provenance; retain the
  original ledger outside rewritten commits. A clean message is not permission
  to fabricate original intent or attribution.
- Obtain independent review of the ledger, intermediate results and tree equality.
  Do not promote, replace the active manifest, or publish solely to hit 58 commits.

### Workstream B: separately reviewed changes

Consensus fixes, profile calibration, VM wording/tests, prototype retirement,
shared-parser refactors, and removing audit JSON are separate changes with
explicit final-tree deltas. They cannot be included under the exact-tree claim.
They may be reviewed before consolidation, but then establish a new agreed
baseline and record the separate delta before producing any consolidated series.

The prototype “unused” conclusion is too strong. The actual APIs are
`PersistentUtxoStore`, `PersistentMonetaryStore`, `PersistentHeaderStore`,
`SealChildHeader` and `SealChildHeaderWithTxRoot`, not several class names quoted
by the report. Current `block.h::ConnectOrdinaryBlock` exposes optional store
arguments and `block.cpp` has storage/rollback paths. Existing callers include
`test_block_store.cpp`, `test_block_monetary_store.cpp`,
`test_block_seal_store.cpp`, `test_block_dev_coinbase.cpp`, and the dedicated
persistent-store tests.

The integrated CMake file explicitly registers
`check-lotus-v2-persistent-utxo`, `check-lotus-v2-persistent-monetary` and
`check-lotus-v2-persistent-header`. It also links the retained `block.cpp` oracle
and prototype storage dependencies into disk/reorg tests. Standalone
`block_test`, `block_seal_test` and `persistent_header_test` projects exercise
additional seal/store paths. At this pin, `lotus_v2_validation` itself does not
list `block.cpp` or the prototype stores as production source; the report's
claimed production-library linkage does not match the current CMake file.

A retirement owner must first enumerate all symbol/include/build/script users
and identify which tests provide independent oracle or crash/undo coverage.
Migrate valuable coverage to the current transition/LevelDB implementation or
retain an explicitly test-only oracle, then remove obsolete APIs, callers,
targets and files together in a reviewed source-change commit. Verify the
replacement tests and full registered suite; provide the before/after coverage
mapping. “Not used by the node” is insufficient proof that deletion is free.
Likewise audit JSON with no build reader can still be review evidence; archive or
relocate it with provenance only after checking repository/tool references.

## Ownership and completion criteria

- A consensus/spec reviewer owns claim dispositions, VM wording and any future
  cost-profile proposal. A second reviewer checks acceptance/EMA implications.
- A native/Rust integration reviewer owns the actual build dependency ledger,
  especially 215–217/226/247/248/258 and 301–307.
- A consolidation owner creates only the candidate history and reproducible
  evidence; an independent reviewer checks exact coverage and every boundary.
- A storage/test owner separately proposes prototype retirement and coverage
  migration. No deletion is authorized by this document.

This review establishes source/document agreement for the three investigated
claims and identifies concrete flaws in the proposed grouping. It does not
certify the full V2 protocol, all 308 patches, execution performance, or any
candidate's intermediate buildability. Those remain explicit gates for later
work. Main, production workspaces/data, tags and releases remain outside scope.
