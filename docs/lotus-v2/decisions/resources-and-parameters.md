# Resource soundness and parameter selection

Decision packet P05, October 9, 2026 (updated October 13, 2026). **Candidate cost algebra and parabolic fee-burn curves specified for D08** (unified Cost Units `cu`, parabolic transaction cost $C_{\text{tx}}$, rolling integer `ema_block_cost` $E_n$, and parabolic block burn floor, eliminating hard step-function walls `MAX_TX_BYTES` and `MAX_BLOCK_BYTES`); **primitive `cu` coefficients and shift constants ($S_{\text{tx\_knee}}, w, E_{\min}, S_{\text{linear}}, S_{\text{quad}}$) remain to be confirmed by hardware benchmark and economic simulation before genesis freeze**. A resource rule is consensus, even when its motivation is protection of a daemon. No post-genesis vote or hardware benchmark may change it implicitly.

## Static cost algebra

Apply P03's bounded instruction-boundary success scan first. An invocation containing an unassigned OP_SUCCESS_N pays a structural charge covering its complete script bytes and scan, plus all outer witness/proof/transaction charges; its suffix need not form an AST and no ordinary VM instructions run. The algebra and size pass below apply only when the scan finds no unassigned success opcode. Future assignments must preserve the old structural-charge floor and the transaction/block validity-subset requirement.

Assign every primitive a positive integer upper-bound charge in **Cost Units (`cu`)** (normalized so **1 wire byte = 1 `cu`**) covering its operands and memory behavior. A charge that grows with operand size is a nondecreasing function of a per-operand size bound; the bound comes from the size pass below, and is MAX_ELEMENT_BYTES wherever that pass has no better answer. Let `cost(node)` be:

```text
ordinary instruction: scheduled upper bound
sequence: sum(cost(child))
conditional: condition/control charge + max(cost(then),cost(else))
loop(bound,body): setup + bound*(iteration_control + cost(body))
```

Generic enumeration bound is always 256 for static charging; input/output bounds are validated counts I/O. Charge BREAK as an instruction but ignore its early termination when calculating the bound. The bound includes unexecuted arms and the complete loop syntax. No path-by-path symbolic execution is needed: the size pass below is a single traversal that merges paths. Use checked unsigned 128-bit cost arithmetic; overflow/exceeding the enclosing cap rejects before execution. The schedule must make all intermediate charge calculations well-defined before a narrowing conversion.

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
| constants, arithmetic on N or U values, comparisons, OUTPUTCONTINUESBRANCH and every other Boolean result, BIN2NUM, DEPTH, SIZE, counts, indices, values | 16 |
| RAWLEFTBITSHIFT | the shifted operand's bound |
| hashes, LEAFHASH, NODEHASH, MERKLEROOT_SORTED, MERKLEROOT_INDEXED, TXID, OUTPOINTTXID, CHAINID, SIGHASH, BRANCHROOT, token IDs, branch roots | 32 |
| CAT | sum of both operand bounds, capped at MAX_ELEMENT_BYTES |
| SPLIT | each piece takes the source's bound |
| NUM2BIN | the width, if it is a constant in 0..MAX_ELEMENT_BYTES pushed by the immediately preceding instruction; otherwise MAX_ELEMENT_BYTES |
| INVERT, AND, OR, XOR | the larger operand bound |
| LESSSWAP | both results take the larger of the two operand bounds |
| DUP, OVER, SWAP, ROT, TUCK, NIP, DROP, alt-stack moves and the other fixed stack shuffles | bounds move with their items |
| PICK, ROLL | with an in-range index pushed as a constant by the immediately preceding instruction, the exact slot. Otherwise PICK yields the maximum bound on `main`, and ROLL sets every `main` slot to that maximum |
| ACTIVEBYTECODE | length of the running script |
| path, complete-output and other transaction or coin reads | with a constant index, that field's actual length in this transaction or its resolved coin; otherwise the maximum of that field over all inputs or outputs |
| NOP | no change |

**Conditional.** Pop the condition, analyze both arms from the same state. If both results are `Known` with equal `main` and `alt` heights, the result is the slot-by-slot maximum; otherwise `Unknown`. A missing ELSE is an empty arm.

**Loop.** Let `S0` be the state at loop entry, plus the 16-byte index the loop pushes for each iteration. Analyze the body once to get `S1`. Every `BREAK` reached in the body pops its depth operand; for each enclosing loop that the `BREAK` may exit (only the inner loop if the depth is a constant 1 pushed by the immediately preceding instruction, otherwise every active enclosing loop), if the state at `BREAK` after popping is `Unknown` or differs in `main` or `alt` height from that loop's entry state before its index, the state after that loop is `Unknown`; otherwise merge that `BREAK` state slot-by-slot into `S1` and into the exited loop's post-loop state. If `S1` is `Known` with the same heights as `S0` before its index, set to MAX_ELEMENT_BYTES every slot whose bound grew, and analyze the body a second time from that widened state; if any slot still grows, or the heights differ, or either result is `Unknown`, the body is charged in `Unknown` and the state after the loop is `Unknown`. Otherwise the body's charges are those of the second analysis and the state after the loop is the slot-by-slot maximum of `S0`, the second result and any `BREAK` states that exit that loop. Each body is analyzed at most twice, so with nesting depth two the pass visits any instruction at most four times.

**Soundness obligation.** For every execution and every instruction reached, each operand's actual size is at most the bound the pass assigned at that instruction. With charges nondecreasing in the bound, `actual abstract charge <= static charge` continues to hold. `Unknown` reproduces the maximum-operand rule, so the pass can only lower a charge where it has a proof. Runtime element, count and total-byte checks are unchanged and still required; the pass is not a memory proof. Vectors must cover unequal conditional arms, computed PICK/ROLL indices, accumulating and non-accumulating loops, BREAK at equal and unequal heights, and underflow inside an unexecuted arm.

## Unified Cost Units (`cu`) and transaction linear base cost $L(\text{tx})$

All wire bytes, BLAKE3/SHA256 hashing, signature verifications, state-tree updates, and static VM opcode charges are unified into a single integer unit: **Cost Units (`cu`)**, where **1 wire byte = 1 `cu`** and every cryptographic, commitment, state, and VM operation has a deterministic static `cu` charge. Each non-coinbase transaction's linear base cost $L(\text{tx})$ (`u64`) is the checked sum of:

1. Wire parsing and canonicalization by bytes/counts (1 `cu` per serialized wire byte) and all script structural scans.
2. Coin resolution, resolved output bytes and metadata; path/witness matching.
3. Script/mint commitment hashing and every supplied membership sibling.
4. `InputCoreLeaf(i)`, `InputsRoot`, `InputFullLeaf(i)`, `FullInputsRoot`, `OutputLeaf(j)`, `OutputsRoot`, `CoinLeaf(i)`, `CoinsRoot`, `TxID`, `TxHash`, and `OwnInputHash(i)` construction and hashing, charged linearly in $O(\text{tx bytes} + \text{resolved coin bytes})$ even if lazily cached. Both `TxID` and `TxHash` top-level digests hash a fixed 112-byte preimage, and every `CHECKSIG` or `SIGHASH` execution in any mode (`00`, `01`, `02`) hashes a fixed-size preimage of 138, 150 or 178 bytes ($\le 3$ BLAKE3 64-byte compression blocks) in $O(1)$ time, preventing quadratic sighash hashing.
5. Every spend and mint invocation, including signatures, data hashing, byte copies, introspection serialization and Merkle-root opcodes (`MERKLEROOT_SORTED` and `MERKLEROOT_INDEXED`, charged at `k <= floor(size_bound(proof_bytes) / 32)` times the step cost of `hash_alg`, or `max(C_blake3, C_hash256)` when `hash_alg` is non-constant).
6. Native/token aggregation and mint lookup, with a deterministic bounded algorithm/model.
7. State updates and root calculation: each consumed/created key's leaf/value hashing and interior-node updates in P02's compact single-leaf-collapsed sparse tree (~27 hashes per key at $10^8$ coins, bounded by a conservative per-key `cu` charge).

Input resolution never loads parent transactions into memory, and outputs carry no inline scripts or state blobs. With the hard consensus caps `MAX_OUTPUT_BRANCHES = 16` and `MAX_OUTPUT_PATHS = 16` ([P01](encoding-and-signatures.md)), every serialized `Output` is at most **812 bytes** (45B native / 77B token for single-branch outputs) and every UTXO `Coin` record is at most **867 bytes** (865 bytes without the outer `CS` length). Spending 256 or 1,000 inputs from the largest transactions in history therefore requires $< 225\text{ KB}$ or $< 870\text{ KB}$ of `Coin` memory, eliminating Bitcoin's PrevTx and oversized-UTXO out-of-memory vectors by construction. Furthermore, each path is a subset of `0..15` stored in RAM as a single `uint16_t` bitmask (`uint16_t paths[16]`, 32 bytes per coin), making `UTXOREQUIRESBRANCH`, `OUTPUTREQUIRESBRANCH`, `OUTPUTEXCLUSIVEBRANCH` and `OUTPUTCONTINUESBRANCH` $O(1)$ bitmask operations.

The sorted/hashed algorithm chosen for asset accumulation must have a bounded worst-case schedule; expected O(1) hash-table lookup is not a worst-case consensus argument. Model at most I+O asset records with a deterministic sort or another explicitly bounded procedure. Storage I/O and peer submission limits remain operational obligations; consensus does not require the entire UTXO set in RAM.

## Parabolic transaction and block cost curves (replacing `MAX_TX_BYTES` and `MAX_BLOCK_BYTES`)

Arbitrary hard step-function byte walls (`MAX_TX_BYTES` and `MAX_BLOCK_BYTES`) are **removed** from consensus. Structural framing bounds (`u16` input/output counts, `MAX_OUTPUT_BRANCHES = 16`, `MAX_OUTPUT_PATHS = 16`, `MAX_ELEMENT_BYTES = 8192`, `MAX_SCRIPT_BYTES`, `MAX_ARGUMENTS`, `MAX_STACK_ITEMS`, etc.) remain enforced before allocation so parsers never allocate unbounded buffers, while aggregate transaction and block capacity are governed by smooth **parabolic integer cost curves** enforced through `C16`'s mandatory 50% native fee burn.

### 1. Parabolic transaction effective cost $C_{\text{tx}}$

Given an ordinary transaction's linear base cost $L = L(\text{tx})$ (`u64` Cost Units), its **parabolic effective cost** $C_{\text{tx}}$ (`u64`, computed with checked `u128` intermediates) is:

$$C_{\text{tx}} = L(\text{tx}) + \big((L(\text{tx}) \cdot L(\text{tx})) \gg S_{\text{tx\_knee}}\big)$$

with candidate knee shift $S_{\text{tx\_knee}} = 17$ ($2^{17} = 131{,}072\text{ cu}$):

- **Flat linear regime for normal payments and consolidations ($L \ll 2^{17}$):** A standard 1-in/2-out native payment ($L \approx 500\text{ cu}$) pays a quadratic surcharge of $(500^2) \gg 17 = 1\text{ cu}$ ($< 0.2\%$), and a 100-input Frank consolidation ($L \approx 32{,}000\text{ cu}$) pays $(32{,}000^2) \gg 17 = 7{,}812\text{ cu}$ ($\approx 1.24\times$ linear), so ordinary users and wallet consolidations never hit a cliff.
- **Super-additive quadratic deterrent against mega-transactions ($L \gg 2^{17}$):** Because $(L_1 + L_2)^2 > L_1^2 + L_2^2$ for positive $L_1, L_2$, combining two large batches into one mega-transaction is strictly more expensive than splitting them into normal-sized transactions. Wallets and exchanges are naturally incentivized to keep individual transactions below the knee, and the mempool ranks and filters all transactions uniformly by $\text{fee} / C_{\text{tx}}$ without needing an arbitrary `MAX_TX_BYTES` cutoff.

### 2. Rolling integer `ema_block_cost` ($E_n$) and parabolic block burn floor

Let $C_{\text{block}}$ be the sum of $C_{\text{tx}}$ over all ordinary (non-coinbase) transactions in block $n$, accumulated in checked `u128` arithmetic:

$$C_{\text{block}} = \sum_{\text{tx} \in \text{block}} C_{\text{tx}}$$

The canonical 56-byte `MonetaryState` record ([P02](commitments-and-state.md)) maintains a rolling integer exponential moving average $E_n$ (`ema_block_cost:u64`) of block cost units with candidate smoothing shift $w = 10$ ($2^{10} = 1024\text{ blocks} \approx 34.1\text{ hours}$ at 2-minute blocks), updated after accepting block $n$:

$$E_{n+1} = E_n - (E_n \gg 10) + (C_{\text{block}} \gg 10)$$

Let $F_n$ be total native transaction fees of block $n$'s ordinary transactions, $T_{\text{tok},n}$ the mandatory token-output burn (`C14a`), $G_n = F_n - T_{\text{tok},n}$ the remaining native fees, and $\text{BurnedFees}_n = G_n - \lfloor G_n / 2 \rfloor = \lceil G_n / 2 \rceil$ the mandatory 50% burned share of remaining native fees under `C16`. Consensus requires $\text{BurnedFees}_n$ to be at least the **Required Block Burn Floor**:

$$\text{BurnedFees}_n \ge \left(\big(C_{\text{block}} \cdot \max(E_n,\, E_{\min})\big) \gg S_{\text{linear}}\right) + \left(\big(C_{\text{block}} \cdot C_{\text{block}}\big) \gg S_{\text{quad}}\right)$$

Why this synergy with `C16`'s 50% fee burn replaces `MAX_BLOCK_BYTES`:

- **Miner self-dealing immunity:** In a chain where miners keep 100% of transaction fees, a fee floor does not constrain block size because a miner can include their own dummy transactions paying high fees to themselves at zero net cost. Because `C16` permanently burns $\text{BurnedFees}_n = G_n - \lfloor G_n / 2 \rfloor$, **not even a miner mining their own transactions can stuff a block for free**: every additional `cu` of block cost increases the irrevocable native XPI burn required for the block to be consensus-valid.
- **Sustained-load congestion pricing (`ema_block_cost` linear term):** When sustained demand (whether byte-heavy or VM/crypto-heavy, since all opcodes and hashes bill into $L(\text{tx})$) pushes $E_n$ above $E_{\min}$, the linear term $\big(C_{\text{block}} \cdot \max(E_n, E_{\min})\big) \gg S_{\text{linear}}$ automatically raises the marginal burn required per `cu` across subsequent blocks.
- **Single-block spike protection (quadratic term):** The quadratic surcharge $(C_{\text{block}} \cdot C_{\text{block}}) \gg S_{\text{quad}}$ makes sudden single-block stuffing spikes quadratically expensive in burned XPI even when $E_n$ is low, while allowing elastic burst capacity during genuine demand spikes without a hard `MAX_BLOCK_BYTES` ceiling.

## Parameter manifest to freeze

| Family | Required named parameters / constraints |
| --- | --- |
| Wire framing | `u16` input/output counts (`MAX_INPUTS`, `MAX_OUTPUTS`), `MAX_BLOCK_TXS`, `MAX_MINTS` (`MAX_TX_BYTES` and `MAX_BLOCK_BYTES` removed in favor of parabolic $C_{\text{tx}}$ and block burn floor) |
| Output/authorization | `MAX_OUTPUT_BRANCHES = 16`, `MAX_OUTPUT_PATHS = 16` (implied `MAX_PATH_BRANCHES = 16`, `MAX_OUTPUT_BYTES = 812`, `MAX_COIN_BYTES = 867`), `MAX_BRANCH_PROOF_DEPTH = 64` |
| VM | `MAX_SCRIPT_BYTES`, `MAX_ARGUMENTS`, `MAX_ELEMENT_BYTES` (working value 8192), `MAX_STACK_ITEMS`, `MAX_ALTSTACK_ITEMS`, `MAX_VM_BYTES`, `MAX_AST_DEPTH`; loop depth=2 and generic bound=256 |
| Cost & parabolic curves | Primitive/structural `cu` schedule (1 wire byte = 1 `cu`), `MAX_INVOCATION_COST`, candidate shift parameters ($S_{\text{tx\_knee}} = 17$, $w = 10$, $E_{\min}$, $S_{\text{linear}}$, $S_{\text{quad}}$) and initial $E_0$ |
| Time/chain | `COINBASE_MATURITY`, `POW_LIMIT`, ASERT anchor and half-life (working value 172800 s), timestamp/future-eligibility rules |
| Money | 56-byte `MonetaryState` initial values ($R_0 = M_{\text{boot}}$, $T_0$, $W_{-1}$, $E_0$), bootstrap shift ($k_{\text{boot}} = 20$), tail bounds ($T_{\min}, T_{\max}$), `DUST_LIMIT` and the token-output burn multiple (`C14a`), genesis allocations (protocol faucet rejected under `D11`) |
| Identity | `ChainID`, header/transaction versions, exact genesis bytes/hash, network/address/seed/directory configuration |

Represent constants in a versioned machine-readable manifest, not scattered daemon defaults. Its byte grammar and digest must be fixed before freezing; a JSON file with unspecified number/string canonicalization is not yet a consensus hash preimage. An outer release manifest can hash the exact canonical parameter-file bytes without making its own digest part of those bytes.

Feasibility constraints matter as much as maxima: a standard payment must sit comfortably in the flat linear region ($L(\text{tx}) \ll 2^{S_{\text{tx\_knee}}}$); a useful two-level covenant must fit its invocation budget; every valid `Output` ($\le 812\text{ bytes}$) fits well inside `MAX_ELEMENT_BYTES` (8192) for `UTXOOUTPUT` / `OUTPUTRECORD` introspection; total stack memory must cover legal individual elements; and bounded parser allocations must prevent out-of-memory conditions on rejected inputs before block fee-burn validation runs.

## Calibration procedure

Before freezing the numerical mainnet shift constants ($S_{\text{tx\_knee}}, w, E_{\min}, S_{\text{linear}}, S_{\text{quad}}$) and primitive `cu` schedule, define supported hardware and a target full-block verification/recovery envelope. Measure scalar worst permitted operands, including each crypto algorithm, wide math, LOG's fixed 64 rounds, hashing, copying, proof handling, sparse-tree updates, large spent coins and asset aggregation. Fit conservative integer `cu` coefficients (normalized to 1 wire byte = 1 `cu`) with documented margin, and validate the parabolic transaction and block burn floor shifts against economic and hardware stress simulations.

A separate named development profile may choose smaller values for fixtures. Its name and ChainID must differ from production, and passing it must not be represented as mainnet capacity qualification. No development value is adopted by this packet merely to make the checklist green.

Implementation can begin on the parameterized parser/evaluator, unified `cu` cost algebra, and parabolic fee-burn checks before final constant calibration. Mainnet readiness cannot. This separates a real implementation dependency from a launch dependency without pretending either is complete.
