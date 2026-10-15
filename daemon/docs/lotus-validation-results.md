# Lotus validation evidence

This file records executed evidence, not planned acceptance. Updated October 14, 2026. Historical records retain their original scope; later records below supersede earlier NOT_RUN entries only for the stated slice.

| Record | Scope | Result | Limits |
| --- | --- | --- | --- |
| DOC-01 | Local source inventory and separation of current/historical docs | Patch bytes/series inspected; CSV contains digests | No patch application, daemon build or chain validation |
| DOC-02 | Current documentation integrity | PASS: local file links across 20 current documents; unique C01–C28/D01–D15; all 299 inventory rows checked against local files; archived spec content hash verified; `git diff --check` | Mechanical document checks only; no proof of protocol correctness |
| DOC-03 | Expanded candidate documentation integrity | PASS: local file links across 29 documents; unique C01–C28/D01–D15; 299 patch digests and archived spec digest; 215 distinct allocated opcode bytes without overlap; staged current-file whitespace check (historical archive excluded) | Link/allocation checks do not validate opcode semantics |
| MODEL-01 | Candidate structural model | PASS: framing/signing inputs (with Merkleized 112B TxID/TxHash over IndexedTreeRoot, CoinsRoot, 41-byte SpendSelector and O(1) partial-mode OwnInputHash/OutputsRoot/OutputLeaf digests); 41 success opcodes and push-boundary scan cases; MERKLEROOT_SORTED and MERKLEROOT_INDEXED across hash_alg in 0..3; 153 ordered-tree paths; compact single-leaf-collapsed sparse membership/absence/insertion order; 56B MonetaryState/StateRoot, telescoping bootstrap reserve conservation (sum B_n = R_0), additive S_n = B_n + T_n, and parabolic C_tx / ema_block_cost / block burn floor; 134/82/64-byte recursive header views; LOG power/monotonic samples; tail integer rounding; ASERT/compact-target boundaries | One construction model; no signature verification, full VM, valid block, economic simulation or independent conformance |
| FACTORY-01 | Software Factory import | Source `e3221c55427328071d046485dc5a648996662b8e`; import provenance in `.agents/software-factory-import.json` | Workflow tests do not validate Lotus consensus |
| V1-BASE | Compatible reference release and target chain | NOT_RUN / not pinned | Release-name and historical-height leads only |
| V1-SYNC | Full clean live-network sync and stalled-state recovery | NOT_RUN | Requires faster hardware and incident evidence |
| V1-RELEASE | Modern compatible daemon release | NOT_RUN | No validated-v1 commit selected |
| V2-REFERENCE | Executable consensus/ABI corpus | PARTIAL: Python reference and TypeScript compiler tests, executable signed payment/token fixtures, native differential checks | Full consensus and block conformance remain incomplete; see October 14 evidence below |
| V2-DAEMON | Payment/block/undo and full feature conformance | PARTIAL: 33 reviewed native module patches replay exactly | Full daemon consensus wiring, block acceptance and persistent undo remain untested |
| V2-PERFORMANCE | Storage, mining, VM, crypto and propagation measurements | NOT_RUN | No nanosecond/throughput/recovery guarantees |
| V2-MONETARY | Exact recurrence and timestamp-incentive analysis | PARTIAL: executable Python recurrence and accounting tests; native patch 029 matches it on 20,300 differential vectors | Native integration, economic simulation and production parameter acceptance remain outstanding |

## October 14 implementation evidence

Canonical V2 commit `c91ab148` integrates the [26-patch native review packet](../candidates/v2-native-reviewed-20261014/README.md). Its manifest records the ABC base, each mailbox digest and intermediate tree; clean replay ends at `b0c32ae8ded2cdfa520bd91cf579d991c8dfa004`. Focused native framing, commitments, state, signing and VM checks passed. The packet records reproduction commands and exact coverage; these isolated modules are not a daemon that accepts V2 blocks.

Compiler integration at `379a6882` passes 56 tests without skips, including 256 seeded optimized/unoptimized comparisons against the independent Python VM. The [pipeline demo](../../tools/lotus-v2-compiler/examples/compiler-pipeline/README.md) exercises promise-based semantic dependencies and the bounded symbolic optimizer. Its sample reduces 31 instructions to 11 and 95 bytes to 75. Parsing itself remains synchronous. The [gallery](../../tools/lotus-v2-compiler/examples/gallery/README.md) contains executable mint and transfer contracts.

Native fixture integration `789798c2` executes all five signed mint/transfer witness invocations with charged native VM success, and rejects unauthorized signatures, a re-signed path bypass, and mint-context coin access. It independently checks identities, branch proofs and signatures. The explicit illustrative cost profile is not a frozen network schedule; no full transaction/block validity is inferred from this harness.

Spec/reference correction `7af9277b` passes 44 Python reference tests and the structural fixture checker. It clarifies composed invocation caps, checked u128 intermediate arithmetic, and skipped BREAK behavior. The reviewed native VM agrees with Python on 298 execution and 477 static-cost cases at the 26-patch integration tree. Newer candidates require separate review and evidence before replacing these counts.

Miner integration `41456528` has exact subtree `ade6e7c5c3a3d6cf13d8d44eeec570d37729bf8d`. Root reran 17 workspace tests, strict Clippy and formatting checks; all three OpenCL device tests passed on Apple M5 Max. The [miner packet](../candidates/v2-miner-20261014/README.md) preserves six ordered mailboxes and replay evidence. P04 CPU/GPU parity and startup rejection are tested; daemon mining jobs, submission and an accepted GPU-mined development block remain outstanding.

The subsequent 29-patch source is `33563a7341b6393bf50246c25ab7acb18c31da5c`, tree `f3fd01ed1d52e21a48dd746e4c1a5a3bb9d2fb5f`. Its added byte/numeric operations pass root's 900 independent byte vectors, 2,117 integer vectors, 363 Python execution comparisons and 494 static-charge comparisons. All 215 assigned bytes are classified; 32 unsupported operations reject. The combined VM and ordinary validator pass fresh strict Release builds/CTest. Ordinary validation tests cover signed compiler mint/transfer, authentication/accounting consistency, locks, fee floors, mint coverage, mandatory paths and atomic rejected application. Outer resource derivation and full block consensus remain separate. The first 26 replay trees are unchanged; all three appended trees also match mailbox replay.

The 31-patch source adds 029 (monetary arithmetic) and 030 (VM context/Merkle proofs), final tree `c3925f143830827a7289bf6dead09811983fbaa6`; exact replay from the ABC base reproduces every recorded tree. Root Debug (ASan/UBSan) and Release runs pass all VM differentials (363/900/2,117/494/684), monetary CTest plus 300 packet and 20,000 root differential vectors, and combined vm/ordinary/monetary/signing/output CTests. The compiler native token checker verifies signed mint, transfer and two-input merge fixtures on this tree. No block is parsed, connected or accepted; see the [review record](../candidates/v2-native-reviewed-20261014/README.md#root-review-and-integration-of-029030-october-14-2026) for open cost-model findings. Root follow-up 031 (tree `04b5d3c167ead1b0a1d8187821f72333ac6bded9`) rejects P05 field-size hints below authenticated fields; the same VM, ordinary and token-fixture checks pass on it. Root follow-up 032 (tree `507c91e64c205df7b38e77abff6ebe02fb99bffe`) applies the signed compiler mint, transfer and two-input merge in the native ordinary validator (Debug ASan/UBSan and Release).

The October 9 MODEL-01 hashes below identify that historical run. Current saved fixture digests are maintained in `docs/lotus-v2/examples/candidate-smoke-vectors.json`; do not use the historical hashes as current-file checksums.

## MODEL-01 reproduction

Run the default command in [the model instructions](../../docs/lotus-v2/tools/README.md). Executed locally with `blake3==1.0.11` against the candidate documents. The saved fixture manifest records each of the six packet digests and the generator digest; these content identities identify this run independently of a later commit.

- Generator SHA256: `ef3146d4eb2e98bcfbe043174885d8e93eb3cd4d1a4404f505a63f949c152155`.
- Fixture SHA256: `defad0b014f6dc5438c33985b2cb8f9875c8649e165587e23f15e0d3593756cd`.
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
