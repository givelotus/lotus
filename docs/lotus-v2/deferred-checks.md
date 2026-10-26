# Deferred transaction checks

Status: **review draft; not frozen**. This records the two-phase V2 validation
contract already present in the integration source. It supplements C01, C12a,
C14–C15 and C20–C21; it does not change transaction serialization or introduce
asynchronous acceptance. “Deferred” means after the input invocations within
one validation run, not after a transaction or block has been accepted.

## Successful execution produces records

Resolve the transaction and perform structural, contextual and conservation
checks against its immutable context. Each required spend or mint invocation
executes with its own staged records. Merge an invocation's records into its
input only when that invocation succeeds. If any required invocation or input
fails, the transaction fails; its records cannot authorize an otherwise invalid
transaction. An OP_SUCCESS_N invocation executes no prefix and produces no
records merely because its script bytes contain an instruction.

Inputs may execute in any order or concurrently. Each input completes exactly
once. Duplicate completion or an incomplete run fails closed. Per-input updates
must be safe under concurrent execution and must not change validity with
arrival order. Record order for deterministic sequential evaluation is input
index, witness index, then staging order within that invocation.

After all required inputs have succeeded, run the transaction-wide rules once:
state authorization, followed by output-claim feasibility. An upper bound may
reject earlier during record collection. Parallel execution need not return the
same first diagnostic when several inputs fail, but acceptance MUST be identical
to canonical sequential evaluation. Transactions without input executions must
still run applicable final rules; this mechanism does not waive the separate
ordinary-transaction or coinbase structural rules.

## State-output authorization

A successful ENFORCEOUTPUT with a state-constraining template records the output
indices it matches. Every output carrying HAS_STATE must be covered by at least
one such successful authorization with the expected state root. Matching an
output without constraining its state does not authorize that state. Multiple
authorizations of one output are permitted. A failed invocation, another
transaction, or a previous validation run cannot supply authorization.

The current diagnostic for an uncovered state output is
`state-output-unauthorized`.

## Joint output claims

Each successful ENFORCEOUTPUT records its nonnegative claimed amount and the
nonempty set of output indices matching its template. An invocation with no
matching output fails, including a zero-amount claim. Matching is evaluated
against the actual transaction outputs; construction-time simulation drafts are
not an alternative consensus output set.

For claim c with amount a[c] and matching set M[c], acceptance requires
nonnegative integer assignments x[c,j] satisfying:

- x[c,j] = 0 for j outside M[c].
- Sum over j of x[c,j] = a[c] for every claim.
- Sum over c of x[c,j] <= value[j] for every output.

One claim may split across matching outputs. Overlapping templates cannot each
count the same output's entire value independently. A maximum-flow feasibility
check is one implementation: source-to-claim capacities a[c], claim-to-matching
output capacities a[c], and output-to-sink capacities value[j]. Accept exactly
when maximum flow equals the total claimed. Use checked totals wide enough for
the transaction; do not use floating point or a greedy allocation whose result
depends on claim order. Claims do not themselves modify outputs or waive native
or per-token conservation.

The transaction may record at most **4096 (claim, matching-output) pairs** across
all inputs and invocations. Exactly 4096 is permitted; the next pair rejects
with `claim-pairs-exceeded`. Zero-amount claims still count their pairs. This is
a transaction-wide bound, in addition to per-invocation budgets. Infeasible
claims reject with `output-overclaimed`.

For example, two claims of 7 matching a single output of value 10 reject even
though each claim fits individually. One claim of 7 matching outputs of values
3 and 4 succeeds. Claims 5 matching outputs A/B and 5 matching only A, with
value(A)=value(B)=5, succeed; a greedy choice assigning the first claim to A must
not cause rejection.

## Conservation and acceptance boundaries

Native and token conservation use structural input/output totals, including
burn outputs. They can be decided before script execution: native outputs must
not exceed native inputs, and each positive token delta must correspond to
exactly one mint input, with no mint for a nonpositive delta. The implementation
shares accumulator machinery for these checks, but they are not script-emitted
records and do not wait for phase-two authorization.

Mempool admission, block connection, ordinary validation and RPC simulation must
apply the same transaction-wide rules. A successful per-input script-cache hit
cannot stand in for missing records or final checks. Reuse must preserve the
complete relevant context and records; the current implementation excludes
record-producing runs from pass/fail script-cache shortcuts and creates a fresh
deferred run for each validation. Speculative admission may optimize work only
when it preserves the authoritative native verifier and these final checks.

No transaction may be accepted while a required input or final rule is pending.
A block must wait for all required transaction checks before committing its
state. The implementation may finalize each transaction as its last input
finishes; no block-wide barrier before each transaction's phase two is required.
An optional block-hook interface exists, but its current consensus registry is
empty: it adds no third-phase consensus rule. Adding a registered check in C++
is not authority to change network validity without a specification change.

## Implementation mapping and conformance

Reviewed source: integration control commit `75bf2cb8eda1`, files
`src/lotus_v2/deferred_checks.{h,cpp}`, `src/lotus_v2/vm.cpp`,
`src/lotus_v2/ordinary_validation.cpp`, `src/lotus_v2/vm_simulation.cpp` and
`src/validation.cpp`. This is implementation provenance, not a claim that the
combined stack has completed build or behavioral validation.

Conformance must cover failed-invocation record rollback, failed sibling inputs,
all input completion permutations, duplicate/incomplete completion, uncovered
state outputs, wrong-state templates, overlapping and split claims, the greedy
counterexample above, zero claims, 4096/4097 pairs, conservation overflow and mint
coverage, fresh runs after cache hits, and matching mempool/block/simulation
outcomes. Existing implementation tests live in `test_deferred_checks.cpp`,
`test_vm.cpp` and the deferred-block functional tests. Documentation validation
does not substitute for running those native tests on the final stack.

The [P03 opcode table (`decisions/vm-semantics.md`)](decisions/vm-semantics.md) and machine-readable opcode registry ([`tools/opcodes.json`](tools/opcodes.json)) are synchronized with `ENFORCEOUTPUT` (`0xeb`), `STATEVERIFY` (`0xed`), `STATEHASH` (`0xc3`), `EMITLOG` (`0x6c`), `ENUMERATE` (`0x69`), conditional `BREAK` (`0x6b`), and `EXT2` (`0xff`) (`225` assigned instructions and `31` `OP_SUCCESS_N` bytes), verified by [`tools/spec_candidate_checks.py`](tools/spec_candidate_checks.py).

---

## References

1. **[Nakamoto 2008]** Satoshi Nakamoto, *"Bitcoin: A Peer-to-Peer Electronic Cash System"*, October 2008 (`https://bitcoin.org/bitcoin.pdf`).
2. **[Lau & Wuille 2016a]** Johnson Lau and Pieter Wuille, *"BIP 114: Merkelized Abstract Syntax Tree"*, Bitcoin Improvement Proposals, April 2016.
3. **[Wuille, Nick, & Towns 2020a]** Pieter Wuille, Jonas Nick, and Anthony Towns, *"BIP 341: Taproot: SegWit version 1 spending rules"*, Bitcoin Improvement Proposals, January 2020.
4. **[Wuille, Nick, & Towns 2020b]** Pieter Wuille, Jonas Nick, and Anthony Towns, *"BIP 342: Validation of Taproot Scripts"*, Bitcoin Improvement Proposals, January 2020.
5. **[O'Connor & Piekarska 2017]** Russell O'Connor and Marta Piekarska, *"Enhancing Bitcoin Transactions with Covenants"*, in *Financial Cryptography and Data Security (FC 2017)*, LNCS vol. 10323, pp. 191–198, 2017.
