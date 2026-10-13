# Lotus validation evidence

This file records executed evidence, not planned acceptance. Updated October 9, 2026.

| Record | Scope | Result | Limits |
| --- | --- | --- | --- |
| DOC-01 | Local source inventory and separation of current/historical docs | Patch bytes/series inspected; CSV contains digests | No patch application, daemon build or chain validation |
| DOC-02 | Current documentation integrity | PASS: local file links across 20 current documents; unique C01–C28/D01–D15; all 299 inventory rows checked against local files; archived spec content hash verified; `git diff --check` | Mechanical document checks only; no proof of protocol correctness |
| DOC-03 | Expanded candidate documentation integrity | PASS: local file links across 29 documents; unique C01–C28/D01–D15; 299 patch digests and archived spec digest; 215 distinct allocated opcode bytes without overlap; staged current-file whitespace check (historical archive excluded) | Link/allocation checks do not validate opcode semantics |
| MODEL-01 | Candidate structural model | PASS: framing/signing inputs (with witnesses minus arguments in Core, 41-byte SpendSelector and O(1) partial-mode OwnInputHash/OutputHash digests); 41 success opcodes and push-boundary scan cases; MERKLEROOT_SORTED and MERKLEROOT_INDEXED; 153 ordered-tree paths; compact single-leaf-collapsed sparse membership/absence/insertion order; 134/82/64-byte recursive header views; LOG power/monotonic samples; tail integer rounding; ASERT/compact-target boundaries | One construction model; no signature verification, full VM, valid block, economic simulation or independent conformance |
| FACTORY-01 | Software Factory import | Source `e3221c55427328071d046485dc5a648996662b8e`; import provenance in `.agents/software-factory-import.json` | Workflow tests do not validate Lotus consensus |
| V1-BASE | Compatible reference release and target chain | NOT_RUN / not pinned | Release-name and historical-height leads only |
| V1-SYNC | Full clean live-network sync and stalled-state recovery | NOT_RUN | Requires faster hardware and incident evidence |
| V1-RELEASE | Modern compatible daemon release | NOT_RUN | No validated-v1 commit selected |
| V2-REFERENCE | Executable consensus/ABI corpus | NOT_RUN | Open decisions; examples currently pseudocode |
| V2-DAEMON | Payment/block/undo and full feature conformance | NOT_RUN | Depends on validated v1 and accepted rules |
| V2-PERFORMANCE | Storage, mining, VM, crypto and propagation measurements | NOT_RUN | No nanosecond/throughput/recovery guarantees |
| V2-MONETARY | Exact recurrence and timestamp-incentive analysis | NOT_RUN | Economic objective and mechanism must be specified |

## MODEL-01 reproduction

Run the default command in [the model instructions](../../docs/lotus-v2/tools/README.md). Executed locally with `blake3==1.0.11` against the candidate documents. The saved fixture manifest records each of the six packet digests and the generator digest; these content identities identify this run independently of a later commit.

- Generator SHA256: `c2b71d132bbdd91d4a28da40175f10a35627f859fc2b486ccdcc8676fbc058b2`.
- Fixture SHA256: `b23a4ec9d8ec595e8014d17bcf2cc3e1082dc5bf42dce8cf864eb15bc1345d63`.
- Result: all model assertions passed; a subsequent default run matched the saved fixture and packet digests exactly. Expectations were constructed by the same model, so this is not independent verification.

## Result record template

```text
id:
status: NOT_RUN | PASS | FAIL | INCONCLUSIVE
requirements/work-packet:
source_commit / dirty_patch_digest:
reference_commit:
spec_digest / parameter_digest / fixture_digest:
chain_genesis / tested_height_and_hash:
hardware / OS / compiler / dependencies / build_flags:
commands_and_validation_shortcuts:
expected_result:
observed_result:
log_or_artifact_paths_and_sha256:
reviewer / timestamp:
limitations / next_action:
```

For performance include dataset seed, transaction/dependency counts, byte sizes, repetitions, warm/cold state, quantiles, CPU/memory/I/O and thresholds chosen beforehand. For sync include shortcut configuration, fixed-height state comparisons, restarts and failures. For fault recovery identify the interrupted durability boundary and recovered state. Publish portable artifact paths and redacted diagnostics, never wallet material or node credentials.

Commit preparation normalized CSV line endings to LF. The archived specification deliberately preserves its original bytes, including historical trailing whitespace; its content digest remains unchanged. Earlier working-tree `git diff --check` results covered tracked edits, not then-untracked artifacts.
