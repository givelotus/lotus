# Implementation entry contracts

October 9, 2026. These direct-request contracts make the **candidate** implementable without claiming mainnet design approval. The maintainer has authorized autonomous preparation; no worker has been dispatched and no live-network operation is authorized here. Use an isolated checkout at the reviewed documentation candidate revision and record that exact commit before starting. Candidate packet digests are in the structural fixture manifest.

The first two units can start independently. The third is an evidence investigation whose inputs still need to be collected. All three require a strong implementation lane because they touch persistence, protocol bytes or compatibility; the actual harness/model is selected and recorded at dispatch. Review before integration, not merely after tests turn green.

## I01 — Reproducible daemon workspace routing

**Outcome:** a developer can prepare separate reference-v1, candidate-v1, candidate-v2 and upstream workspaces with explicit source pins, without overwriting existing work or suppressing patch failures.

**Evidence:** setup reads the modern ABC pin for v1 while comments describe the extraction anchor; upstream/v2 share a directory; reset/branch checkout can affect valuable work; commit failures are suppressed. See [V1-01 draft](tickets/workspace-provenance.md).

**Boundary:** `daemon/scripts`, Makefile, pin-role metadata, patch-series validation and their disposable-repository tests. Preserve existing workspaces and all data directories. Do not apply the full history, change network consensus or launch a node.

**Implementation contract:** model extraction base, compatible reference, modern candidate and validated-v1 as distinct inputs. Fail before mutation for unknown series, unavailable pin, conflicting workspace, dirty destructive transition, missing/empty/no-diff active patch or unsupported resume state. Handle documented no-ops by explicit disposition, not swallowed errors. Derive all per-series checkout/build/output paths explicitly. A future v2 setup must require an actual validated-v1 commit; absence is a clear error, never fallback to ABC.

**Proof:** isolated Git fixtures demonstrate preserved dirty files, separate paths, deterministic resume, exact pin checkout, failure propagation and no false success. Snapshot input fixture state before/after rejection. Test reset only on disposable owned fixtures with explicit authorization. Publish tested commands and rollback instructions. New tooling must not retroactively mutate historical patch provenance.

**Handoff:** exact base/candidate, commands/results, source-routing table, next rebase step and remaining pin inputs. Rollback is a tooling revert; preserved workspaces remain untouched. Maintainer owns pin/reference selection; the implementation owner is assigned at dispatch.

## I02 — Independent candidate encoding and evaluator foundation

**Outcome:** turn P01–P03 into typed parsing/serialization, commitments and execution modules, with exact generated ordinary-payment data. Mainnet monetary rules and resource calibration are explicitly outside this first unit.

**Inputs:** six [decision packets](../lotus-v2/decisions.md); structural fixtures identify proposed hashes but are not an oracle. Parameters are an explicit immutable configuration passed to the evaluator, including fixture-only ChainID/limits. No production defaults or ad hoc globals. P04 header work is a subsequent bounded integration unit once its fields/hash choice is accepted.

**Boundary:** a new isolated reference-tool directory (recommended `tools/lotus-v2-reference/`), its vector schema, tests and generated examples under `docs/lotus-v2/examples/`. Keep it independent of daemon serialization/sighash/state code. Do not alter v1 or build a network service/general-purpose compiler.

**Stage A:** implement canonical primitive/output/ordinary/coinbase grammars, core/full projections, AuthPlan/Coins/selector messages, branch/ordered/sparse commitments and a versioned vector schema. Use bounded parsers with explicit limits; no allocation from unchecked counts. Prove round-trip uniqueness for valid objects and strict boundary rejection. Independently compare the structural fixtures; investigate disagreements instead of regenerating expected data.

**Stage B:** implement decoded structured syntax, fixed-width stack semantics, parameterized cost algebra and a minimal payment opcode slice. Preserve the full closed opcode table as the intended target; unimplemented instructions cause an explicit tool error, never accepted consensus success. Generate the complete signed payment using a maintained BIP340 library/reference, including public key, digest, signature, bytes, stack and accounting. Then implement remaining opcode groups as separate testable increments against P03. A partial evaluator cannot label arbitrary v2 transactions valid.

**Stage C:** add ordinary consuming/reference resolution, mint-context separation, checked asset conservation and atomic undo against in-memory fixture state. Do not pretend a test subsidy/faucet stub validates production coinbase entitlement. Export which features and parameter profile each result actually covers.

**Proof:** independent byte/message/tree vectors; exact arithmetic and structured BREAK behavior; complete payment acceptance and focused rejection cases; state/undo equality; parameterized cost upper bounds independent of cache state. Crypto profiles require independent acceptance-set vectors; do not rely solely on the same underlying library in two wrappers. A second implementation is still required before genesis.

**Durable shape:** version vectors and parameter schemas from the first artifact; commit to field/encoding semantics, not compiler syntax or a host-memory representation. Known next feature is full monetary/header integration; leave an explicit state/context boundary, not an opaque catch-all object or a plugin framework. Keep unsupported monetary state out of claims of full validation.

**Handoff:** candidate revision and packet/parameter digests, supported feature matrix, generated payment, tests, unresolved discrepancies and exact next unit. Rollback removes an experimental tool/profile; it changes no running network. Mainnet decisions remain with the maintainer.

## I03 — Historical v1 sync investigation

Execute the [incident contract](tickets/v1-sync-obstruction.md) on consistent copies once evidence is available. Missing block/hotfix information blocks reproducing the user's exact failure, not I01 or I02. Pin reference and chain identity before proposing a compatibility repair. Return a reproducible boundary and diagnosis; do not dispatch an unscoped “fix syncing” rebase.

## What is still not ready

Production v2 monetary/faucet code, final header/PoW selection, future-time eligibility, mainnet resource constants and launch identity need explicit acceptance/evidence. Heavy daemon port/sync/benchmark work remains on the faster machine. These are visible dependencies; they no longer prevent implementation of isolated tooling and candidate reference semantics.
