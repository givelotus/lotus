# Resource soundness and parameter selection

Decision packet P05, October 9, 2026. Candidate rules for D08; **numeric mainnet calibration remains open**. A resource limit is consensus, even when its motivation is protection of a daemon. No post-genesis vote or hardware benchmark may change it implicitly.

## Static cost algebra

Assign every primitive a positive integer upper-bound charge covering its operands and memory behavior. A charge that grows with operand size is a nondecreasing function of a per-operand size bound; the bound comes from the size pass below, and is MAX_ELEMENT_BYTES wherever that pass has no better answer. Let `cost(node)` be:

```text
ordinary instruction: scheduled upper bound
sequence: sum(cost(child))
conditional: condition/control charge + max(cost(then),cost(else))
loop(bound,body): setup + bound*(iteration_control + cost(body))
```

Generic enumeration bound is always 256 for static charging; input/output bounds are validated counts I/O. Charge BREAK as an instruction but ignore its early termination when calculating the bound. Includes unexecuted arms and the complete loop syntax; no path-by-path symbolic execution is needed; the size pass below is a single traversal that merges paths. Use checked unsigned 128-bit cost arithmetic; overflow/exceeding the enclosing cap rejects before execution. The schedule must make all intermediate charge calculations well-defined before a narrowing conversion.

With nonnegative charges, structural induction proves monotonicity in bounds: sums, max, and multiplication by nonnegative bounds are monotone. An ordinary instruction's charged work is bounded by its schedule. A selected conditional arm is bounded by max; a loop executes no more than its captured bound and BREAK only removes work. Induction therefore establishes `actual abstract charge <= static charge`, **conditional on correct primitive upper bounds and control semantics**. It does not prove a nanosecond bound or a hardware-independent memory-latency bound.

Decode/charge syntax once per invocation, not once per expanded iteration. Nested I×O loops remain legal; I identical invocations still charge I²O inner work. No optimization discounts. Runtime memory/stack/range checks remain necessary even when static cost fits.

## Size-bounded charging

MAX_ELEMENT_BYTES has a working value of 8192, chosen so that a post-quantum signature or key (for example SLH-DSA at about 7.9 KB) fits in one stack item. A large limit must not raise the price of scripts that only handle small items, so size-dependent charges use a bound computed per operand, before execution, by one traversal of the decoded script.

The pass **never rejects a script and adds no validity rule**. It only chooses charges. Where it cannot follow the stack it falls back to the maximum, which is the rule this packet had before.

**State.** Either `Known(main, alt)`, two lists holding one byte-size bound per stack item, or `Unknown`. In `Unknown` every operand is charged at MAX_ELEMENT_BYTES. The initial state is `Known`: the witness arguments at their actual lengths in wire order, then N-sized (16) for the mint delta in a mint invocation; `alt` is empty.

**Transfer rules.** An instruction that needs more items than a `Known` state holds moves the pass to `Unknown` (it would error if executed, but it may sit in an arm that never runs).

| Instruction | Bound of each result |
| --- | --- |
| PUSH_n, PUSHDATA | exact data length |
| constants, arithmetic, comparisons, DEPTH, SIZE, counts, indices, values | 16 |
| hashes, TXID, CHAINID, SIGHASH, BRANCHROOT, token IDs, branch roots | 32 |
| CAT | sum of both operand bounds, capped at MAX_ELEMENT_BYTES |
| SPLIT | each piece takes the source's bound |
| NUM2BIN | the width, if it is a constant pushed by the immediately preceding instruction; otherwise MAX_ELEMENT_BYTES |
| INVERT, AND, OR, XOR | the larger operand bound |
| DUP, OVER, SWAP, ROT, TUCK, NIP, DROP, alt-stack moves and the other fixed stack shuffles | bounds move with their items |
| PICK, ROLL | with an index pushed as a constant by the immediately preceding instruction, the exact slot. Otherwise PICK yields the maximum bound on `main`, and ROLL sets every `main` slot to that maximum |
| ACTIVEBYTECODE | length of the running script |
| state, path, complete-output and other transaction or coin reads | with a constant index, that field's actual length in this transaction or its resolved coin; otherwise the maximum of that field over all inputs or outputs |
| EXTENSION0–7 and NOP | no change |

**Conditional.** Pop the condition, analyze both arms from the same state. If both results are `Known` with equal `main` and `alt` heights, the result is the slot-by-slot maximum; otherwise `Unknown`. A missing ELSE is an empty arm.

**Loop.** Let `S0` be the state at loop entry, plus the 16-byte index the loop pushes for each iteration. Analyze the body once to get `S1`. If `S1` is `Known` with the same heights as `S0` before its index, set to MAX_ELEMENT_BYTES every slot whose bound grew, and analyze the body a second time from that widened state; if any slot still grows, or the heights differ, or either result is `Unknown`, the body is charged in `Unknown` and the state after the loop is `Unknown`. Otherwise the body's charges are those of the second analysis and the state after the loop is the slot-by-slot maximum of `S0` and the second result. A BREAK reached at a `main` or `alt` height different from the loop's exit height makes the state after the loop `Unknown`. Each body is analyzed at most twice, so with nesting depth two the pass visits any instruction at most four times.

**Soundness obligation.** For every execution and every instruction reached, each operand's actual size is at most the bound the pass assigned at that instruction. With charges nondecreasing in the bound, `actual abstract charge <= static charge` continues to hold. `Unknown` reproduces the maximum-operand rule, so the pass can only lower a charge where it has a proof. Runtime element, count and total-byte checks are unchanged and still required; the pass is not a memory proof. Vectors must cover unequal conditional arms, computed PICK/ROLL indices, accumulating and non-accumulating loops, BREAK at unequal heights, and underflow inside an unexecuted arm.

## Transaction and block charge domains

A complete schedule must separately cover:

1. Wire parsing and canonicalization by bytes/counts; all script structural scans.
2. Coin resolution, referenced output bytes and metadata; path/witness matching.
3. Script/mint commitment hashing and every supplied membership sibling.
4. Core/Coins/AuthPlan construction and hashing, charged by their bytes even if cached.
5. Every spend and mint invocation, including signatures, data hashing, byte copies, introspection serialization and state-proof opcodes.
6. Native/token aggregation and mint lookup, with a deterministic bounded algorithm/model.
7. State updates and root calculation: a conservative charge for each consumed/created key's leaf/value hashing and 256 sparse-tree levels, without relying on shared-path or cache savings.
8. Block parsing/header/transaction-tree/monetary/undo work and all transaction charges.

A reference to a large output is not cheap just because its input wire record is small. Max output bytes, reference count and coin-resolution charges must cover it. A transaction-level cost cap alone cannot bound a block full of individually acceptable expensive transactions. Conversely, a block cap does not replace bounds on rejected transaction parsing and mempool admission.

The sorted/hashed algorithm chosen for asset accumulation must have a bounded worst-case schedule; expected O(1) hash-table lookup is not a worst-case consensus argument. Model at most I+O asset records with a deterministic sort or another explicitly bounded procedure. Storage I/O and peer submission limits remain operational obligations; consensus does not require the entire UTXO set in RAM.

## Parameter manifest to freeze

| Family | Required named parameters / constraints |
| --- | --- |
| Wire | MAX_TX_BYTES, MAX_BLOCK_BYTES, MAX_INPUTS, MAX_OUTPUTS, MAX_BLOCK_TXS, MAX_MINTS |
| Output/authorization | MAX_OUTPUT_BYTES, MAX_STATE_BYTES, MAX_BRANCHES, MAX_PATHS, MAX_PATH_BRANCHES, MAX_BRANCH_PROOF_DEPTH |
| VM | MAX_SCRIPT_BYTES, MAX_ARGUMENTS, MAX_ELEMENT_BYTES (working value 8192), MAX_STACK_ITEMS, MAX_ALTSTACK_ITEMS, MAX_VM_BYTES, MAX_AST_DEPTH; loop depth=2 and generic bound=256 |
| Work | MAX_INVOCATION_COST, MAX_TX_COST, MAX_BLOCK_COST and every primitive/structural coefficient |
| Time/chain | COINBASE_MATURITY, POW_LIMIT, ASERT anchor and half-life, timestamp/future-eligibility rules |
| Money | Tail initialization/floor/cap/precision, bootstrap initialization/clock/decay, fee-burn ratio, DUST_LIMIT and the token-output burn multiple (C14a), allocation and faucet state parameters |
| Identity | ChainID, header/transaction versions, exact genesis bytes/hash, network/address/seed/directory configuration |

Represent constants in a versioned machine-readable manifest, not scattered daemon defaults. Its byte grammar and digest must be fixed before freezing; a JSON file with unspecified number/string canonicalization is not yet a consensus hash preimage. An outer release manifest can hash the exact canonical parameter-file bytes without making its own digest part of those bytes.

Feasibility constraints matter as much as maxima: a standard payment must fit all caps; a useful two-level covenant must fit its transaction budget; configured state-proof payloads and any intended full-output introspection must fit MAX_ELEMENT_BYTES; total stack memory must cover legal individual elements; the maximum block's declared byte/count fields must be representable. An output too large for full-output introspection must still be usable through field accessors, or its construction limit should be lowered. Document which capabilities are intentionally bounded out.

## Calibration procedure

Before selecting numerical mainnet values, define supported hardware and a target full-block verification/recovery envelope. Measure scalar worst permitted operands, including each crypto algorithm, wide math, LOG's fixed 64 rounds, hashing, copying, proof handling, sparse-tree updates, large referenced coins and asset aggregation. Measure cold and warm state and rejected submissions. Fit conservative integer coefficients with documented margin, then verify complete workloads against both per-transaction and block caps.

A separate named development profile may choose smaller values for fixtures. Its name and ChainID must differ from production, and passing it must not be represented as mainnet capacity qualification. No development value is adopted by this packet merely to make the checklist green.

Implementation can begin on the parameterized parser/evaluator and cost algebra before calibration. Mainnet readiness cannot. This separates a real implementation dependency from a launch dependency without pretending either is complete.
