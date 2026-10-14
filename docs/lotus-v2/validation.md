# Conformance and genesis acceptance

Status: planned validation contract. No v2 conformance run has passed yet.

The [candidate structural checks](tools/README.md) now run against saved [fixtures](examples/candidate-smoke-vectors.json). They are same-author construction checks, not the independent evaluator or complete conformance corpus described below. Packet and generator digests make their scope reproducible.

## Reference implementation boundary

Build a small scalar evaluator independent of optimized daemon code. Its public boundary is `evaluate(parameter_set, prior_state, block_bytes) -> accepted(post_state, receipts, undo) | rejected(stage, reason)`. Test transaction validation with an explicit candidate block context; do not hide context in process globals. The evaluator must parse canonical bytes itself. Sharing the daemon's parser, sighash builder and state-update routines would weaken differential evidence at those boundaries.

The evaluator is a specification tool, not a network service. The first version needs ordinary payments, deterministic commitments and disconnect/reconnect. Add mint/loop behavior only against accepted rules. Use locally constructed benign conformance fixtures; no current-network exploitation workflow is required.

## Vector record contract

Use JSON manifests plus content-addressed binary fixtures. Required fields:

| Field | Meaning |
| --- | --- |
| `schema` | `lotus/conformance/v1`; unknown schema rejects in the harness |
| `id`, `requirements`, `decisions` | Stable case ID and applicable C/D identifiers |
| `spec_sha256`, `parameters_sha256` | Exact rule and parameter artifacts |
| `generator_revision`, `evaluator_revision` | Immutable source commits; uncommitted generation must record its patch digest |
| `kind` | `parse`, `script`, `transaction`, `block`, `undo`, or `equivalence` |
| `fixtures` | Relative artifact paths, byte lengths, SHA256 digests; no absolute local paths |
| `pre_state`, `context` | Complete relevant state/context fixtures, not just TxID |
| `expected` | Acceptance and post-state/undo/stack/cost, or first deterministic validation stage and reason |
| `observed` | Implementation revision, parameters, result and log digest; absent until executed |

A versioned machine-readable schema and runner are deliverables of V2-01. A prose table is not claimed to be that validator. Expected outputs must be independently checked; regenerating expectations from the implementation under test does not establish correctness. Error ordering is normative only if explicitly specified; otherwise compare validity and invariant class, not incidental daemon error strings.

## Requirement coverage

| Requirements | Required evidence |
| --- | --- |
| C01–C07 | Encoding uniqueness, bounded allocation, exact flags/counts/lengths, core versus witness identity and commitments |
| C08–C11 | Uniform one-leaf hashing; typed domain registry; positional mapping; empty/out-of-range path rejection; multi-leaf membership and ordered-tree distinction |
| C12–C17 | Authorization independent of conservation; asset-separated sums; zero token-ID rule; rejection of read-only inputs; token-output burn (C14a) and the half-fee burn; exact mint coverage; atomic state and undo |
| C18–C21 | Explicit signing/mint contexts; argument framing; actual leaf binding; independent invocation; cached/uncached equality |
| C22–C25 | Monotone validity (C22a): no opcode reads advancing chain state, and a mempool transaction is invalidated only by a spent input; syntax/control-flow termination; depth checks; BREAK frame restoration; memory/primitive caps; monotonic checked bounds; transaction/block aggregation |
| C26–C28 | Coinbase uniqueness without cycles; root/state coverage; target/work/time boundaries; exact reward and reorg state; complete frozen parameters |

Formal obligations are conditional statements, not labels: unique decoding; every consumed coin authorized; no native creation outside coinbase; token growth only under the corresponding mint authority; bounded execution/memory; static upper-bound soundness; optimized/scalar equivalence; reversible accepted transitions. State assumptions about collision resistance and signature unforgeability explicitly. They do not prove economic incentive compatibility.

## Generic success-opcode cases

Require vectors for every currently unassigned byte at an instruction boundary; success in skipped arms and after RETURN; ignored malformed suffixes; truncated/noncanonical pushes before success; success bytes inside fixed and length-prefixed push payloads; and ordinary full decoding when no success byte is found. Separately verify that successful invocation does not bypass membership proofs, witness/count/byte limits, other required branches, mint/accounting/lock rules or transaction/block budgets. Unknown CHECKDATASIG selectors, including 4..15, must error in ordinary execution. Compare a mock assigned instruction against the old success rule to establish valid-set inclusion, including changed stack effects and cost floors. Relay refusal must use the same instruction-boundary scan. These are required independent conformance cases, not claims that the structural scanner alone validates transactions.

## Fee, genesis and upgrade-state regression obligations

- Byte fees at 1, 999, 1000 and 1001 bytes; include all witness bytes. Reject an ordinary transaction one atom below its minimum even if a different transaction pays excess fees.
- Coinbase-only blocks with added burn outputs and spendable zero-valued outputs: increased bytes/state work must increase applicable charges; claiming the full pre-charge reward fails. Test mandatory token burns, odd fees, underclaim exactly at/below the threshold, explicit burn outputs, insufficient subsidy, and compact transaction-frame length boundaries.
- Coinbase `CoinbaseData` framing: zero elements is canonical absence; one nonempty element of 1 and exactly 8192 bytes accepts subject to the block budget; one empty element, 8193 bytes, more than one element, non-shortest CompactSize and truncated count/length/payload reject. Treat every payload byte as opaque, including opcode-looking bytes: no execution, `OP_SUCCESS_N` scan, membership proof or authorization result may depend on it. Charge encoded bytes and hashing; a larger payload must affect the coinbase/envelope deduction and cost as specified by P05.
- Hold the parent ID, height and outputs fixed while changing only `CoinbaseData`; independently verify both TxID and TxHash change and the block transaction root follows. Verify that spend/mint argument stripping does not strip coinbase data. Check the coinbase `prev_txid` against the actual parent BlockID, `prev_index` against derived height, genesis zero parent ID and u32 height overflow rejection. On competing sibling blocks, identical coinbases may both validate against their own branch state. On one chain, duplicate TxIDs within a block and insertion into an occupied outpoint must still reject, with no BIP30-style exception or global duplicate-coinbase ban.
- Genesis commits its initial monetary record without running a recurrence or charging recurring fees; native issuance is zero. Height 1 consumes step 0 entitlement, height 2 consumes step 1; disconnect restores each prior record and UTXO root exactly.
- Simulate an assigned success opcode with increased execution cost. Old/new validators must agree on frozen accounting, EMA and exact state roots for every block accepted by the new rules. Higher enforcement costs may require greater reward underclaim or reject a block, never rewrite its monetary transition.
- Cross-check every opcode name/byte against the registry, the full success-byte complement, pushed success bytes and literal data-script RETURN encoding. Run all end-to-end examples after reassembly; the smoke scanner is not a VM.
- Avalanche integration: no-winner fallback, alternative winners, resource-adjusted payout basis, restart/reorg, and deterministic historical validation independent of polling state. These are separate daemon tests, not claims from structural vectors.

## Gate sequence

1. **Specification closure:** accepted definitions and all numerical parameters; no unresolved normative references, code-default semantics, or conflicting decision statuses.
2. **Reference slice:** ordinary payment from bytes through block acceptance and undo; independently checked identities and signature preimages.
3. **Complete conformance:** every requirement mapped to vectors/proof obligations; assets, loops and monetary state included.
4. **Daemon agreement:** reference and scalar daemon agree; then each optimization agrees on the same corpus, including rejection and cost results.
5. **Operational qualification:** reorg/restart/import/indexer/persistence tests; fault-injected interrupted commits never advertise a state beyond a durable recoverable boundary.
6. **Capacity qualification:** weakest supported hardware and worst permitted operand sizes; bytes, dependency edges, proofs, signatures and VM memory measured separately. Define thresholds before measurement.
7. **Independent review and launch reproduction:** review the exact source/parameter/genesis candidate; reproduce builds and genesis; all blockers closed. A later candidate change reruns affected gates.

Record results in [daemon validation results](../../daemon/docs/lotus-validation-results.md). The v1 gate is independent: a passing v2 regtest cannot establish live-network compatibility. Snapshot authentication is also independent of historical execution; record the trust and validation mode used.
