# VM semantics and opcode allocation candidate

Decision packet P03. **Recommended candidate**, not frozen. Resolves concrete stack/control/arithmetic questions for D07; the cost schedule and independent crypto/opcode vectors remain blockers. This is a v2 machine, not Bitcoin Script with implicit inherited edge cases.

## Values and parsing

Stacks contain bounded byte strings. `N(x)` is a signed two's-complement little-endian integer of `16..1024` bytes (`MIN_NUMERIC_BYTES = 16`, `MAX_NUMERIC_BYTES = 1024`, i.e., 128-bit baseline up to 8,192-bit big-int). Constants, counts, indices, values, booleans, and `LOG` push canonical 16-byte signed little-endian `int128`; unary arithmetic preserves `len(a)`, binary arithmetic (`ADD`, `SUB`, `DIV`, `MOD`, `MIN`, `MAX`) operates at `W = max(len(a), len(b))`, and `MUL` produces `max(W, minimal_signed_width(a * b))` up to `MAX_MUL_BYTES = 2048` bytes. `U(x)` interprets `0..1024` bytes as an unsigned little-endian integer, automatically zero-padding shorter operands to `W = max(16, len(a), len(b))` and returning `W`-byte unsigned limbs. Boolean consumers accept only 16-byte `N(0)`/`N(1)`. Comparisons and signatures produce those canonical booleans. For ordinary execution, main and alternate stacks start as described in the ABI; finish requires main=[N(1)], alternate=[]. The success-scan exception below initializes neither stack. Every push, duplicate, move and concatenation must satisfy element/count/total-byte limits before mutation.

First perform the bounded OP_SUCCESS_N scan specified below. If it finds no unassigned success opcode, decode the entire script to structured syntax before execution, including unreachable regions; malformed pushes and unmatched structures reject even in skipped code. Push data bytes are never opcodes. Canonical push framing is one-byte fixed length for 1..75 bytes, or opcode 4c followed by shortest `Bytes(data)` for empty data or lengths ≥76. Bytes 4d and 4e mean NEGATIVE_ONE and ONE; they have no legacy PUSHDATA meaning. Constant opcodes push N values. A fixed-length push of sixteen bytes is allowed even if a constant opcode could produce the same stack item: different programs have different commitments; canonical parsing does not imply a unique program for each computation.

## Closed candidate allocation

Every byte not assigned an instruction in these tables is OP_SUCCESS_N, where N is its unsigned decimal byte value. An unassigned success opcode unconditionally succeeds for the entire invocation under the scan below; it does not push true and continue. Each assigned byte has the semantics below or in the referenced packet. This table is an allocation proposal requiring byte-for-byte vectors before D07 closes. Historical Bitcoin, Mitra and BIGINT assignments are not aliases. NOP remains permanently a NOP.

The [machine-readable opcode registry](../tools/opcodes.json) owns byte assignments. These tables use the same names and bytes; the structural checker verifies their agreement. This pre-genesis allocation groups literals, control, stack, bytes, arithmetic, cryptography, transaction/input/output introspection, and invocation/locks. It is deliberately incompatible with Bitcoin Script and earlier V2 draft bytecode; regenerate scripts, branch roots, token IDs, transaction IDs and signatures together. Unassigned gaps remain success extension points, not aliases for old instructions.

### Literals (`00`–`5d`)

| Hex | Instruction | Stack effect / meaning (rightmost is top) |
| --- | --- | --- |
| 00 | ZERO | push N(0) |
| 01–4b | PUSH_n | push next n bytes, 1≤n≤75 |
| 4c | PUSHDATA | push Bytes payload; only length 0 or ≥76 |
| 4d | NEGATIVE_ONE | push N(−1) |
| 4e | ONE | push N(1) |
| 4f | TWO | push N(2) |
| 50 | THREE | push N(3) |
| 51 | FOUR | push N(4) |
| 52 | FIVE | push N(5) |
| 53 | SIX | push N(6) |
| 54 | SEVEN | push N(7) |
| 55 | EIGHT | push N(8) |
| 56 | NINE | push N(9) |
| 57 | TEN | push N(10) |
| 58 | ELEVEN | push N(11) |
| 59 | TWELVE | push N(12) |
| 5a | THIRTEEN | push N(13) |
| 5b | FOURTEEN | push N(14) |
| 5c | FIFTEEN | push N(15) |
| 5d | SIXTEEN | push N(16) |

### Control (`60`–`6b`)

| Hex | Instruction | Stack effect / meaning (rightmost is top) |
| --- | --- | --- |
| 60 | NOP | no effect; permanently no effect (not an extension point) |
| 61 | IF | pop Boolean; execute selected arm |
| 62 | NOTIF | IF with inverted Boolean |
| 63 | ELSE | structural alternate arm delimiter |
| 64 | ENDIF | structural conditional end |
| 65 | VERIFY | pop Boolean; false rejects |
| 66 | RETURN | reject when executed |
| 69 | ENUMERATE | pop N in 0..256; structured loop (use `TXINPUTCOUNT ENUMERATE` or `TXOUTPUTCOUNT ENUMERATE` to iterate inputs/outputs; `67` and `68` are retired to unassigned `OP_SUCCESS_N`) |
| 6a | ENDENUMERATE | structural loop end |
| 6b | BREAK | `Boolean(cond) N(depth) → empty`: pop `N(depth)` (`1 ≤ depth ≤ active_loop_depth`) and `Boolean(cond)`; if `cond` is `N(1)`, exit `depth` enclosing active loops; if `N(0)`, continue (replaces `DO/UNTIL` without requiring an `IF ... ENDIF` wrapper; use `ONE <depth> BREAK` for unconditional break) |
| 6c | EMITLOG | `item_1 ... item_k N(k) → empty` in off-chain simulation mode (e.g. `PICK(x) PICK(y) PICK(z) PUSH("required_output_template") 4 EMITLOG`); **consensus `OP_INVALID` on-chain** (unconditionally rejects if ever broadcast; the entire `emit` statement including its operand pushes/picks is omitted by the compiler in production builds) |

### Stack (`70`–`81`)

| Hex | Instruction | Stack effect / meaning (rightmost is top) |
| --- | --- | --- |
| 70 | TOALTSTACK | main top moves to alternate top |
| 71 | FROMALTSTACK | alternate top moves to main top |
| 72 | 2DROP | a b → empty |
| 73 | 2DUP | a b → a b a b |
| 74 | 3DUP | a b c → a b c a b c |
| 75 | 2OVER | a b c d → a b c d a b |
| 76 | 2ROT | a b c d e f → c d e f a b |
| 77 | 2SWAP | a b c d → c d a b |
| 78 | DEPTH | push N(main item count before push) |
| 79 | DROP | x → empty |
| 7a | DUP | x → x x |
| 7b | NIP | a b → b |
| 7c | OVER | a b → a b a |
| 7d | PICK | pop numeric n; copy nth remaining item from top, top=0 |
| 7e | ROLL | pop numeric n; move nth remaining item to top |
| 7f | ROT | a b c → b c a |
| 80 | SWAP | a b → b a |
| 81 | TUCK | a b → b a b |

### Bytes (`88`–`94`)

| Hex | Instruction | Stack effect / meaning (rightmost is top) |
| --- | --- | --- |
| 88 | CAT | a b → a concatenated with b |
| 89 | SPLIT | bytes N(i) → bytes[0:i] bytes[i:] |
| 8a | NUM2BIN | N(x) N(width) → signed LE encoding of x at exact width |
| 8b | BIN2NUM | 0..1024 bytes interpreted signed LE → N(x) at width max(16, minimal_signed_width(x)); empty → N(0) |
| 8c | SIZE | bytes → bytes N(byte length) |
| 8d | INVERT | bytes → bitwise complement of every byte |
| 8e | AND | a b → bytewise a AND b (shorter operand zero-padded to max(len(a), len(b))) |
| 8f | OR | a b → bytewise a OR b (shorter operand zero-padded to max(len(a), len(b))) |
| 90 | XOR | a b → bytewise a XOR b (shorter operand zero-padded to max(len(a), len(b))) |
| 91 | EQUAL | a b → Boolean byte equality |
| 92 | EQUALVERIFY | EQUAL then VERIFY |
| 93 | LESSSWAP | a b → the same two items with the smaller one deeper and the larger on top, compared as unsigned little-endian integers |
| 94 | RAWLEFTBITSHIFT | bytes N(k) → fixed-width logical shift defined below |

### Arithmetic (`98`–`b4`)

| Hex | Instruction | Stack effect / meaning (rightmost is top) |
| --- | --- | --- |
| 98 | 1ADD | N(a) → N(a+1), checked |
| 99 | 1SUB | N(a) → N(a−1), checked |
| 9a | NEGATE | N(a) → N(−a), checked |
| 9b | ABS | N(a) → N(abs(a)), checked |
| 9c | NOT | Boolean → inverted Boolean |
| 9d | 0NOTEQUAL | N(a) → Boolean(a≠0) |
| 9e | ADD | N(a) N(b) → N(a+b), checked |
| 9f | SUB | N(a) N(b) → N(a−b), checked |
| a0 | MUL | N(a) N(b) → N(a*b), checked |
| a1 | DIV | N(a) N(b) → N(trunc_toward_zero(a/b)) |
| a2 | MOD | N(a) N(b) → N(a−trunc_toward_zero(a/b)*b) |
| a3 | MULPOW2 | N(a) N(k) → checked a*2^k or truncating division |
| a4 | BOOLAND | Boolean a b → Boolean(a AND b) |
| a5 | BOOLOR | Boolean a b → Boolean(a OR b) |
| a6 | NUMEQUAL | N(a) N(b) → Boolean(a=b) |
| a7 | NUMEQUALVERIFY | NUMEQUAL then VERIFY |
| a8 | NUMNOTEQUAL | N(a) N(b) → Boolean(a≠b) |
| a9 | LESSTHAN | N(a) N(b) → Boolean(a<b) |
| aa | GREATERTHAN | N(a) N(b) → Boolean(a>b) |
| ab | LESSTHANOREQUAL | N(a) N(b) → Boolean(a≤b) |
| ac | GREATERTHANOREQUAL | N(a) N(b) → Boolean(a≥b) |
| ad | MIN | N(a) N(b) → N(min(a,b)) |
| ae | MAX | N(a) N(b) → N(max(a,b)) |
| af | WITHIN | N(x) N(lo) N(hi) → Boolean(lo≤x<hi) |
| b0 | ADDCARRY | U(a) U(b) N(c) → U_W((a+b+c) mod 2^(8W)) N(carry), W=max(16,len(a),len(b)) |
| b1 | SUBCARRY | U(a) U(b) N(c) → U_W((a−b−c) mod 2^(8W)) N(borrow), W=max(16,len(a),len(b)) |
| b2 | MUL128_WIDE | U(a) U(b) → U_W(high_W(a*b)) U_W(low_W(a*b)), W=max(16,len(a),len(b)) |
| b3 | LOG | N(x) → N(LOG2_Q64(x)), algorithm below |
| b4 | SQRT | N(x) → N(floor(sqrt(x))); x≥0 |

### Cryptography (`b8`–`c3`)

| Hex | Instruction | Stack effect / meaning (rightmost is top) |
| --- | --- | --- |
| b8 | SHA256 | bytes → SHA256(bytes) |
| b9 | HASH256 | bytes → SHA256(SHA256(bytes)) |
| ba | BLAKE3 | bytes → unkeyed 32-byte BLAKE3(bytes), no application tag |
| bb | CHECKSIG | signature public_key → Boolean, P01 transaction message; 64-byte signature = mode 00, 65-byte = explicit partial mode |
| bc | CHECKSIGVERIFY | CHECKSIG then VERIFY |
| bd | CHECKDATASIG | signature message public_key N(algorithm) → Boolean, profile below |
| be | LEAFHASH | script_bytes → P02 `Leaf(script_bytes)`, 32 bytes |
| bf | NODEHASH | a b → P02 `BranchNode(a,b)`, 32 bytes; a and b must each be exactly 32 bytes |
| c0 | MERKLEROOT_SORTED | leaf_hash proof_bytes N(hash_alg) → root_hash: bottom-up sorted-pair Merkle root, hash_alg in 0..3, 0≤k≤64 siblings |
| c1 | MERKLEROOT_INDEXED | leaf_hash key_bytes proof_bytes N(hash_alg) → root_hash: bottom-up key-bit-indexed Merkle root, hash_alg in 0..3, 1≤len(key_bytes)≤32, 0≤k≤8*len(key_bytes) siblings |
| c2 | SIGHASH | N(mode) → P01's 32-byte message for this invocation in that signing mode (0, 1 or 2); mode 2 errors when INPUTINDEX ≥ TXOUTPUTCOUNT |
| c3 | STATEHASH | item_1 ... item_k N(k) → Hash32 (`0 ≤ k ≤ 64`): canonical tuple state commitment `H_state(CS(k) || CS(len(item_1)) || item_1 || ... || CS(len(item_k)) || item_k)` matching the 32-byte state branch root stored in `UTXOBRANCH(i, slot)` on the spent `vout` and `OUTPUTBRANCH(j, slot)` on the created `vout` |

### Transaction (`c8`–`cf`)

| Hex | Instruction | Stack effect / meaning (rightmost is top) |
| --- | --- | --- |
| c8 | TXVERSION | push transaction version |
| c9 | TXINPUTCOUNT | push input count (`OP_INPUTS`) |
| ca | TXOUTPUTCOUNT | push output count (`OP_OUTPUTS`) |
| cb | TXMINTCOUNT | push the number of mint inputs (flags `03`) |
| cc | TXLOCKTIME | push 56-bit lock_value as N |
| cd | TXLOCKKIND | push absolute lock_kind |
| ce | TXID | push ChainID-bound core TxID |
| cf | CHAINID | push the immutable 32-byte chain identifier |

### Input & Incoming Vout (`d0`–`df`)

| Hex | Instruction | Stack effect / meaning (rightmost is top) |
| --- | --- | --- |
| d0 | INPUTINDEX | push the index of the input this script is running for: the spend input in a spend, the mint input in a mint |
| d1 | INPUTFLAGS | i → flags |
| d2 | OUTPOINTTXID | i → prev_txid |
| d3 | OUTPOINTINDEX | i → prev_index |
| d4 | INPUTSEQUENCENUMBER | i → sequence |
| d5 | INPUTPATHINDEX | i → selected path of spend input i |
| d6 | UTXOVALUE | i → resolved coin value |
| d7 | UTXOTOKENID | i → resolved asset ID (`0x00..00` for native XPI, or 32-byte `token_id`) |
| d8 | UTXOBRANCHCOUNT | i → resolved branch count |
| d9 | UTXOBRANCH | i k → resolved branch[k] |
| da | UTXOPATHCOUNT | i → resolved path count |
| db | UTXOPATH | i p → canonical Vec(CS(branch_index)) bytes |
| dc | UTXOOUTPUT | i → complete serialized Output bytes (use `INPUTINDEX UTXOOUTPUT` for active incoming vout) |
| dd | UTXOREQUIRESBRANCH | i root → Boolean: every path of resolved coin i includes a branch equal to root |
| de | UTXOFLAGS | i → resolved coin flags (symmetric with `OUTPUTFLAGS` `e0`) |
| df | INPUTWITNESSARG | i w a → bytes: push argument `a` of witness `w` of input `i` (enables cross-input state preimage inspection in N-to-1 stateful merges without $O(N^2)$ witness duplication) |

### Output, Asset & State Accounting (`e0`–`ef`)

| Hex | Instruction | Stack effect / meaning (rightmost is top) |
| --- | --- | --- |
| e0 | OUTPUTFLAGS | j → output flags (`0x01` `HAS_TOKEN`, `0x02` `IS_BURN`, `0x04` `HAS_STATE`) |
| e1 | OUTPUTVALUE | j → output value |
| e2 | OUTPUTTOKENID | j → output asset ID (`0x00..00` for native XPI, or 32-byte `token_id`) |
| e3 | OUTPUTBRANCHCOUNT | j → output branch count |
| e4 | OUTPUTBRANCH | j k → output branch[k] |
| e5 | OUTPUTPATHCOUNT | j → output path count |
| e6 | OUTPUTPATH | j p → canonical Vec(CS(branch_index)) bytes |
| e7 | OUTPUTRECORD | j → complete serialized Output bytes |
| e8 | OUTPUTREQUIRESBRANCH | j root → Boolean: every path of output j includes a branch equal to root |
| e9 | OUTPUTEXCLUSIVEBRANCH | j root → Boolean: output j has a path consisting of that branch alone, and every other path of output j also includes it |
| ea | OUTPUTCONTINUESBRANCH | j new_root → Boolean: spend-only; output j has the exact same paths and branches as the spent coin (INPUTINDEX), except the active invocation's BRANCHROOT is replaced by new_root (preserving C09 distinct branches) |
| eb | ENFORCEOUTPUT | `[Hash32(expected_state)] [stack_branches...] [N(expected_value)] template_bytes N(claim_amount) → N(matched_output_index)`: match an output against a partial `OutputTemplate`, validate/claim `output[j].state_root` when `state_mode != 0`, deduct `claim_amount` from `unclaimed_value[j]`, and push matched index `j` (or reject if unsatisfied) |
| ec | TXTOKENBALANCE | `Bytes32(asset_id) → N(total_in) N(total_out)`: push transaction-wide sum of input values and sum of output values for `asset_id` (`0x00..00` for native XPI, or 32-byte `token_id` for tokens) in $O(1)$ from `PreparedVmTransaction` |
| ed | STATEVERIFY | `Hash32(expected_state) → empty`: spend-only; require `(coin[INPUTINDEX].flags & 0x04) != 0` (`HAS_STATE`) and immediately verify `expected_state == coin[INPUTINDEX].state_root` in $O(1)$ |
| ee | UTXOSTATEROOT | `i → Hash32`: push the 32-byte `state_root` of resolved coin `i` (or `0x00..00` if `(coin[i].flags & 0x04) == 0`) |
| ef | OUTPUTSTATEROOT | `j → Hash32`: push the 32-byte `state_root` of output `j` (or `0x00..00` if `(output[j].flags & 0x04) == 0`) |



### Invocation, Locks & Two-Byte Opcode Extension (`f0`–`f6`, `ff`)

| Hex | Instruction | Stack effect / meaning (rightmost is top) |
| --- | --- | --- |
| f0 | ACTIVEBYTECODE | push exact active script bytes |
| f1 | INVOCATIONKIND | push 1 for spend, 3 for mint, the same numbers as input flags |
| f2 | BRANCHROOT | push the 32-byte root the active script was proven against: the branch root in a spend, the token ID in a mint |
| f3 | CHECKLOCKTIMEVERIFY | N(kind) N(bound) → empty, absolute transaction lock check |
| f4 | CHECKSEQUENCEVERIFY | N(kind) N(bound) → empty, current consuming input's relative lock check |
| f5 | ACTIVEBRANCHINDEX | push N(k), the branch slot index `0..15` in the resolved coin (`coin.paths[path_index][witness_index]`) for a spend invocation, or N(−1) in a mint invocation |
| f6 | ACTIVEWITNESSINDEX | push N(witness_index), the position of the active witness within the selected path |
| ff | EXT2 | two-byte opcode prefix: consumes the following selector byte `ext_op` (`00`–`ff`) to form a 16-bit opcode `ff00`–`ffff`; unassigned `ff <ext_op>` pairs are `OP_SUCCESS_EXT_N` |

Existing template spellings may prefix `OP_`; that does not alter bytes. In-script global UTXO proofs are rejected because proving against a moving global `UtxoRoot` inside script creates TOCTOU race conditions and violates C22a monotone validity (see [rationale](../rationale.md#2-op_utxoproofverify-in-script-global-utxo-state-proofs)). P02's compact `UtxoRoot` proofs remain strictly for RPCs, snapshots and optional `ProvenTx` relay packages, and contracts authenticate their own internal sets and key-value maps in script with `MERKLEROOT_SORTED` (`0xc0`) and `MERKLEROOT_INDEXED` (`0xc1`).

## Arithmetic edge semantics

PICK/ROLL require `0≤n<remaining_stack_size`; SPLIT requires `0≤i≤len(bytes)`. NUM2BIN width must be 0..MAX_ELEMENT_BYTES and x must fit its signed width; zero width accepts only zero. Larger widths sign-extend. BIN2NUM accepts `0..1024` bytes (`MAX_NUMERIC_BYTES = 1024`), sign-extending or compacting redundant sign bytes to width `max(16, minimal_signed_width(x))` and never silently truncating input. Decode an unsigned byte string as a nonnegative N by appending a zero sign byte before BIN2NUM where needed. Bitwise `AND`, `OR`, and `XOR` automatically zero-pad the shorter operand to `max(len(a), len(b))` (accelerated with 16-byte SIMD NEON/SSE2 chunks in the native evaluator).

Signed numeric operands `N(x)` have byte width `16 <= len <= 1024` (8,192-bit big-ints over 64-bit / 128-bit limbs). Unary arithmetic (`1ADD`, `1SUB`, `NEGATE`, `ABS`, `SQRT`) preserves operand width `len(a)` and rejects overflow at that width; binary `ADD`, `SUB`, `DIV`, `MOD`, `MIN`, `MAX` operate at `W = max(len(a), len(b))` and reject overflow at `W`; `MUL` widens when necessary to `max(W, minimal_signed_width(a * b))` up to `MAX_MUL_BYTES = 2048` bytes (so 16-byte products that fit `int128` remain 16 bytes and overflow only if configured via `NUM2BIN` or exceeding 2,048 bytes). DIV and MOD reject zero divisor and the minimum-int/−1 overflow at width `W`. NEGATE/ABS of minimum-int at width `len(a)` reject. `ADDCARRY`, `SUBCARRY`, and `MUL128_WIDE` accept `0..1024`-byte unsigned operands, automatically zero-padding shorter operands to `W = max(16, len(a), len(b))`; carry input must be `N(0)` or `N(1)`, and borrow is one iff `a < b + c`.

RAWLEFTBITSHIFT interprets bytes as unsigned little-endian, retains the original byte length and discards shifted-out bits. Positive k shifts left; negative k shifts right; abs(k)≥8*length returns all-zero bytes of the same length. Handle minimum-int k by comparison, not an overflowing signed absolute operation. MULPOW2 uses signed mathematical a at width `W = len(a)`, preserves no discarded high bits on multiplication, and truncates division toward zero. For nonzero a, `k >= 8*W` or signed overflow at width `W` rejects; a=0 returns zero. For `k <= -8*W` the division result is zero. Intermediate host shifts by their type width are never the definition.

LOG returns the following fixed algorithm, **not a claim of exact real logarithm rounding**. Require x>0. Let e=floor(log2(x)) determined by bit length, and let `k = max(127, e)`; `z = x * 2^(k - e)`. Initialize f=0. Repeat exactly 64 times: `t = floor(z * z / 2^k)`; `bit = 1` if `t >= 2^(k+1)`, else `0`; `z = floor(t / 2)` if `bit = 1` else `t`; `f = 2 * f + bit`. Return 16-byte `N(e * 2^64 + f)`. SQRT is the largest nonnegative integer r with `r * r <= x`, returned at the input's byte width `len(x)`; implementations may use any equivalent bounded algorithm (such as Newton-Raphson `isqrt`). Monetary consensus need not use these script opcodes to implement its own recurrence.

## Introspection and execution contexts

Indices/results are N values; hashes/outpoints/scripts remain bytes. Token ID reads zero only for native coins. Every index and integer result must be representable and checked before access.

A mint is an input (flags `03`), so a mint script has an input position like any other and INPUTINDEX returns it. A mint input resolves no coin: UTXO-prefixed reads at a mint input's index error, and a script that scans inputs tests INPUTFLAGS first. A mint invocation receives the rest of its context on the stack instead of through context-only opcodes: after the witness arguments are pushed, the node pushes the positive mint delta as N, so it is on top. The token ID is not pushed: in a mint it is the root the script was proven against, which BRANCHROOT returns in any invocation. With u64 amounts and at most 2^16−1 outputs, positive token delta is below 2^80, so it fits N. A mint script must consume the delta. This stack shape is not a security boundary between mint and spend scripts; P02 requires them to be kept in separate trees. Returned serialized outputs/paths and active bytecode must fit the element limit; using such an opcode on a larger object errors. This does not make the underlying output invalid by itself. Length-aware costs charge bounded serialization/copy work. There is no introspection of other invocations' successful execution, mutable VM state, signature arguments or TxHash; P01's core witness binding is not such an opcode.

BRANCHROOT lets a script name the tree it belongs to without containing its own hash. UTXOREQUIRESBRANCH and OUTPUTREQUIRESBRANCH answer, in one operation, whether a policy makes a given tree mandatory: true iff the root operand is exactly 32 bytes, the coin/output is spendable (`path_count >= 1`, i.e. `(flags & 0x02) == 0`), and every path contains at least one branch index whose root equals it. Because C09 makes branch roots distinct within an output, at most one index k has that root, and the result equals: k exists and bit k is set in the intersection of all path index sets. Together they let a covenant require that a successor output stays under its own rules for any policy shape, using a single loop over outputs. Walking paths and their entries in script would need three nested loops, which C22 forbids. With C09's hard caps (`MAX_OUTPUT_BRANCHES = 16`, `MAX_OUTPUT_PATHS = 16`), each path is a 16-bit mask and these checks are pure $O(1)$ bitmask operations. For a pruneable burn/commitment output (`(flags & 0x02) != 0`), `OUTPUTFLAGS` returns `0x02` (native) or `0x03` (token), `OUTPUTPATHCOUNT` returns `0`, `OUTPUTBRANCHCOUNT` returns `1..16`, `OUTPUTBRANCH(j, k)` returns the $k$-th 32-byte commitment word or Merkle root, `OUTPUTPATH` errors (out of range), and `OUTPUTREQUIRESBRANCH`, `OUTPUTEXCLUSIVEBRANCH`, and `OUTPUTCONTINUESBRANCH` return `false` (`N(0)`) because the output has no spend paths (`path_count == 0`). A mint, coinbase or out-of-range index errors for the UTXO form.

No opcode exposes the height, time or hash of the block being built or of any ancestor. This keeps validity monotone (C22a): a script's result depends only on the transaction, its resolved coins and ChainID, so it cannot change as blocks arrive. A script can require that a height or time has been reached by constraining TXLOCKTIME or the input's sequence, which the node enforces as minimum locks (enabling Dutch auctions and linear vesting curves over `TXLOCKTIME`; see [rationale](../rationale.md#1-op_blockheight-op_blocktime-op_blockhash-and-block-dependent-transactions)). A script cannot require that a height or time has not yet passed; a certificate or quote that must stop working is instead tied to a coin and ends when that coin is spent, which is an ordinary input conflict. SIGHASH takes the signing mode as an operand and pushes P01's message for that mode: 0 everywhere, 1 or 2 only in a spend invocation; any other value, a partial mode in a mint invocation, or mode 2 when `INPUTINDEX >= TXOUTPUTCOUNT` errors. A script may fix the mode with a constant or take it from a witness argument so the signer chooses. This lets an ECDSA or Ed25519 policy checked with CHECKDATASIG bind its signature to the same intent as CHECKSIG in any of the three modes, without one opcode per mode and without reconstructing hidden witness-plan fields in Script.

CHECKLOCKTIMEVERIFY accepts kind 1 or 2 and nonnegative bound: require tx.lock_kind=kind and tx.lock_value≥bound. CHECKSEQUENCEVERIFY accepts kind 1 (height) or 2 (512-second units), bound 0..65535; require current spend's enabled relative lock of that kind and encoded delay≥bound. Both consume their operands. Global P01 lock checks enforce the actual candidate context. Mint context may use the absolute check but not the input-relative check.

## Structured evaluation and BREAK

Grammar: a sequence consists of ordinary instructions, `IF sequence [ELSE sequence] ENDIF` (or NOTIF), and `ENUMERATE sequence ENDENUMERATE`. Constructs must nest properly; crossing a loop delimiter with an unmatched conditional rejects at decode time. At most two nested loop nodes are permitted on any syntax path, including skipped arms. A separate fixed parameter bounds conditional/AST nesting.

`ENUMERATE` (`0x69`) pops a canonical numeric bound `0 <= bound <= 256` once on entry; iterating over all inputs or outputs uses `TXINPUTCOUNT` (`0xc9`) `ENUMERATE` (`0x69`) `...` `ENDENUMERATE` (`0x6a`) or `TXOUTPUTCOUNT` (`0xca`) `ENUMERATE` (`0x69`) `...` `ENDENUMERATE` (`0x6a`), retiring the formerly fused `0x67`/`0x68` loop headers. Each iteration pushes `N(index)`, evaluates its body, then advances; the body may consume or leave that index like any stack value. Bound zero does not evaluate the body. IF consumes one canonical Boolean only when executed. Underflow/runtime operand errors in unexecuted code do not occur; its syntax/opcodes are nevertheless checked and charged conservatively.

Define evaluation results `Continue`, `ExitLoops(d)`, or `Error`. `BREAK` (`0x6b`) pops `N(depth)` (`1≤d≤active_loop_depth`) and `Boolean(cond)`; when `cond == N(1)`, it produces `ExitLoops(d)`, and when `cond == N(0)`, it returns `Continue` (eliminating the need to wrap loop exits in `IF ... ENDIF`; an unconditional break is `ONE <depth> BREAK`). Sequence/conditional nodes immediately propagate `ExitLoops(d)`. A loop receiving `ExitLoops(1)` terminates and returns `Continue`; receiving `ExitLoops(d>1)` terminates and returns `ExitLoops(d−1)`. This specifies conditional-frame unwinding without byte-offset guesses. All existing stack effects persist. No `BREAK` signal may escape the top-level sequence. `BREAK` is an ordinary instruction in the decode grammar: an out-of-range depth, non-Boolean `cond`, or `BREAK` outside a loop errors when that instruction executes, while `BREAK` in a skipped conditional arm or zero-iteration loop does not itself reject. The containing syntax must still decode and nest correctly.

`EMITLOG` (`0x6c`) is a simulation-only structured event opcode (`item_1 ... item_k N(k) → empty`). In `sim_bytecode`, the compiler lowers an `emit` statement by pushing its arguments (via `PICK` for stack references, `PUSH` for constants, or arbitrary expressions) followed by the topic/event tag and `N(k)`, and `EMITLOG` pops `N(k)` and all `k` items—giving the entire `emit` statement a net stack delta of `0` (`+(k+1) - (k+1) = 0`) while allowing arguments to be assembled in any standardized order expected by wallet event handlers without contorting the contract's working stack. When compiling production on-chain `bytecode`, the compiler omits the entire `emit` statement (both its operand `PICK`/`PUSH` instructions and `EMITLOG`), preserving the exact same stack layout before and after. On-chain, `EMITLOG` (`0x6c`) is **permanently `OP_INVALID`** (never `OP_SUCCESS_N`), so any accidental attempt to broadcast unstripped simulation bytecode is deterministically rejected by nodes.

## Exclusive branch, branch-continuation, and templated `ENFORCEOUTPUT` (`0xeb`)

OUTPUTREQUIRESBRANCH proves that a root is present on every path of an output and says nothing about what else is there. That is right when the holder is meant to add branches of their own, as with a token's rules. It is not enough when a script creates a coin for someone else or continues a contract: a spender could satisfy it and still require a further branch on every path, one only they can satisfy or one nobody can, leaving the coin held hostage or burned.

OUTPUTEXCLUSIVEBRANCH (`0xe9`) closes that for single-branch continuation. It is true exactly when both hold for output j:

1. Some path consists of the single branch whose root equals `root`. The coin can therefore always be spent by satisfying that branch alone.
2. Every other path also includes that branch. No path lets anyone spend without it.

Other paths that pass are only stricter versions of the first and add no way to spend. The root operand must be exactly 32 bytes.

When a coin carries multiple branches that must all be preserved across a state transition—for example, a token coin carrying both the token's mandatory rules branch and a stateful limit-order, auction or vault branch, or an output combining an owner branch with a rate-limiting covenant branch—`OUTPUTEXCLUSIVEBRANCH` does not apply because the continuing path intentionally requires multiple branches (`AND` composition), and verifying that every other branch and path is unchanged would otherwise require loops in Script.

`OUTPUTCONTINUESBRANCH` (`ea`) handles both single-branch and multi-branch state transitions in one operation:

- It is defined only in spend invocations (`INVOCATIONKIND == 1`); executing it in a mint invocation (`INVOCATIONKIND == 3`) is a script error.
- It pops `new_root` (which MUST be exactly 32 bytes, else error) and output index `j` (which MUST satisfy `0 <= j < TXOUTPUTCOUNT`, else error).
- Let `coin` be the resolved coin of the current spend input (`INPUTINDEX`), and let `k = paths[path_index][witness_index]` be the unique branch index in `coin.branches` of the active invocation's `BRANCHROOT` (also exposed directly via `ACTIVEBRANCHINDEX` `0xf5`).
- It pushes `N(1)` (`true`) iff:
  1. `output[j].paths == coin.paths` (the output has the exact same path count and the exact same branch-index vectors in every path as `coin`), and
  2. `len(output[j].branches) == len(coin.branches)`, `output[j].branches[k] == new_root`, and for every `m != k` (`0 <= m < len(coin.branches)`), `output[j].branches[m] == coin.branches[m]` (which by C09's distinct-branch invariant is already guaranteed not to collide with `new_root` on any valid output).
- Otherwise it pushes `N(0)` (`false`). Passing `BRANCHROOT` as `new_root` checks that output `j` has the exact same branches and paths as the spent coin without modification. With `MAX_OUTPUT_BRANCHES = 16` and `MAX_OUTPUT_PATHS = 16`, the node evaluates `OUTPUTCONTINUESBRANCH` in $O(1)$ by comparing the 32-byte `uint16_t paths[16]` bitmask array and at most 16 32-byte branch roots.

### Templated Output Enforcement, Value-Budget Claiming & Direct `state_root` Verification (`ENFORCEOUTPUT` `0xeb`, `STATEVERIFY` `0xed`)

Because wrapping an asset creates a separate Vault UTXO (holding the underlying asset under `branches[1] = VaultABI` and `state_root = STATEHASH(...)`) and mints a fresh receipt token UTXO (`branches[0] = OwnerCheckSig`), each stateful UTXO only ever has a **single 32-byte `state_root`**:

- **Wire Format (`Output.flags` bit 2 = `0x04` `HAS_STATE`):**
  - When `(output.flags & 0x04) != 0` (`HAS_STATE`), `Output` carries a single 32-byte `state_root: h32` field (`Output = flags:u8 || value:u64 || token_id? || state_root? || Vec(h32 branch_root) || Vec(Vec(CS(branch_index)))`).
- **Immediate $O(1)$ Input State Verification (`STATEVERIFY` `0xed`) & Output State Authorization (`ENFORCEOUTPUT` `0xeb`):**
  1. **Input State (`STATEVERIFY` `0xed`):**
     - `<expected_state> STATEVERIFY` pops the 32-byte `expected_state` (typically computed from witness arguments via `STATEHASH` `0xc3`), requires `(coin[INPUTINDEX].flags & 0x04) != 0` (`HAS_STATE`), and immediately verifies `expected_state == coin[INPUTINDEX].state_root` in $O(1)$.
  2. **Output State (`ENFORCEOUTPUT` `0xeb` with `state_mode`):**
     - When `ENFORCEOUTPUT` matches an output `j` with `state_mode != 0` (`EXACT_STATE` or `FROM_STACK`), it requires `(output[j].flags & 0x04) != 0` and `output[j].state_root == expected_state`, and sets `state_authorized[j] = true` on `PreparedVmTransaction`.
     - After all scripts in the transaction execute, every output `j` with `(output[j].flags & 0x04) != 0` (`HAS_STATE`) MUST have `state_authorized[j] == true` (automatically preventing forged initial state on any output that wasn't explicitly authorized by an input or mint contract!).
- **`ENFORCEOUTPUT` (`0xeb`) Stack & Binary `OutputTemplate` Encoding:**
  - **Stack:** `[Hash32(expected_state)] [stack_branch_roots...] [N(expected_value)] template_bytes N(claim_amount) → N(matched_output_index)` (`0 <= claim_amount`).
  - **Binary `OutputTemplate` Encoding:**
    1. `template_flags` (`1 byte`):
       - `bits 0..1` (`value_mode`): `00 = OMIT` (any value; deducts `claim_amount` if `claim_amount > 0`), `01 = EXACT_VALUE` (requires `output[j].value == template_value` and `unclaimed_value[j] >= claim_amount`), `10 = MIN_VALUE` (requires `output[j].value >= template_value` and `unclaimed_value[j] >= claim_amount`), `11 = FROM_STACK` (pops runtime-computed `N(expected_value)` from the stack, requiring `output[j].value == expected_value` and `unclaimed_value[j] >= claim_amount`).
       - `bits 2..3` (`token_mode`): `00 = OMIT` (any asset), `01 = NATIVE_XPI` (`!output[j].HasToken()`), `10 = EXACT_TOKEN_ID` (`output[j].token_id == template_token_id`, where `0x00..00` matches native XPI and non-zero matches that token), `11 = SELF_BRANCH_ROOT` (`output[j].HasToken() && output[j].token_id == BRANCHROOT`).
       - `bits 4..5` (`paths_mode`): `00 = OMIT` (requires `RequiresBranch` for every pinned branch in `branch_mask | branch_stack_mask`), `01 = EXPLICIT_PATHS` (serialized `Vec(Vec(CS(branch_index)))` follows pinned branches), `10 = INHERIT_INPUT_PATHS` (spend-only: requires `output[j].paths == coin.paths` and `len(output[j].branches) == len(coin.branches)`, where unset bits in `branch_mask | branch_stack_mask` inherit `coin.branches[i]` unless bit 7 `WILDCARD_UNSET_BRANCHES` is set).
       - `bit 6` (`burn_mode`): `0` requires spendable output (`!output[j].IsBurn()`), `1` requires burn/commitment output (`output[j].IsBurn()`).
       - `bit 7` (`wildcard_unset_branches`): when `1`, any branch slot `i` (`0 <= i < branch_count`) whose bit in `branch_mask | branch_stack_mask` is `0` is a **wildcard** (omitted from `template_bytes`, matching any valid 32-byte branch root supplied by the wallet in `output[j].branches[i]`); when `0` under `INHERIT_INPUT_PATHS`, unset bits must equal `coin.branches[i]`.
    2. `[Optional] template_value` (`8 bytes` uint64 LE, present iff `value_mode == 01` or `10`).
    3. `[Optional] template_token_id` (`32 bytes`, present iff `token_mode == 10`).
    4. `branch_count` (`1 byte`, `0..16`), `branch_mask` (`2 bytes` uint16 LE, static branch roots embedded in `template_bytes`), `branch_stack_mask` (`2 bytes` uint16 LE, dynamic branch roots popped from the VM stack at runtime), and `state_mode` (`1 byte`: `0 = OMIT` requiring `!output[j].HasState()`, `1 = EXACT_STATE` reading 32-byte `template_state_root` from `template_bytes`, `2 = FROM_STACK` popping 32-byte `expected_state` from the VM stack).
    5. `[Optional] template_state_root` (`32 bytes`, present iff `state_mode == 1`).
    6. `popcount(branch_mask) * 32 bytes`: the static 32-byte `Hash32` roots for each set bit `i` in `branch_mask` in ascending slot order.
    7. `[Optional] paths`: canonical `Vec(Vec(CS(branch_index)))` present iff `paths_mode == 01`.
- **Transaction-Wide Value-Budget Claiming (`unclaimed_value`):**
  - `PreparedVmTransaction` initializes `unclaimed_value[j] = tx.outputs[j].value` and `state_authorized[j] = false` across all `0 <= j < TXOUTPUTCOUNT`.
  - When `ENFORCEOUTPUT` executes, it scans `j = 0 .. TXOUTPUTCOUNT - 1` for the first output `j` that satisfies all template constraints and has `unclaimed_value[j] >= claim_amount`.
  - If found, it deducts `unclaimed_value[j] -= claim_amount`, sets `state_authorized[j] = true` if `state_mode != 0`, and pushes `N(j)` onto the stack (allowing the script to immediately inspect any omitted fields of output `j`, such as `DUP OUTPUTVALUE` or `1 OUTPUTBRANCH`). If no output satisfies both the template and `unclaimed_value[j] >= claim_amount`, execution rejects.
  - Because `unclaimed_value[j]` tracks remaining unclaimed value rather than a boolean flag, two inputs cannot double-count the same output value, while **N-to-1 consolidations** (e.g., two 100-unit inputs each claiming `100` against a single 200-unit output `j`) succeed naturally (`100 + 100 <= 200`), and read-only shared state assertions pass `claim_amount = 0`.
- **Implicit `EMITLOG` & Constructive Simulation Mode (Avoiding the Chicken-and-Egg Trap):**
  - When `.simulate()` runs to *discover* what outputs, locks, and funding inputs a transaction needs, `tx.outputs` has not been populated yet; if `ENFORCEOUTPUT` ran as a strict rejection check during initial simulation, it would fail on the first output requirement before the transaction could be built.
  - Therefore, in `sim_bytecode`, the compiler lowers `enforce_output(role, template, claim_amount)` to **implicitly emit a `"lotus.output.draft"` `EMITLOG` (`0x6c`)** (carrying the `role` label, `template_bytes`, any `FROM_STACK` value/branch/state_root, and `claim_amount`), and in off-chain simulation mode (`EvaluateVmSimulated`), if no existing draft output `j` matches `ENFORCEOUTPUT`, the simulator **constructively appends (or coalesces) a synthetic draft output `j` into the simulated transaction's output list**, sets `output[j].state_root = expected_state`, and pushes `N(j)` onto the stack rather than failing.
  - Once `.simulate()` completes and the wallet materializes all drafted outputs, KDF branches, `state_root`s, and funding inputs, `.sign()` compiles the original contract source in production mode (omitting all `emit` / `wallet::*` statements) through the **pinned versioned optimizer (`edition`, `optimizer_version`)**—the exact same deterministic compilation pipeline that generated the on-chain `BranchRoot` / `token_id` Merkle roots originally—and verifies the completed transaction against the strict consensus evaluator before signing.

## Tree-hash opcodes, general Merkle root verification and LESSSWAP

LEAFHASH and NODEHASH compute P02's branch-tree leaf and node hashes exactly as consensus does when it checks a membership proof: the domain tag, the leaf or node marker, the length framing of a leaf, and the ordering of a node's two children are all applied by the opcode. A script supplies only the script bytes, or the two child hashes. Everyone who computes these hashes, wallet, node and script alike, uses the same tagged functions; there is no untagged form. LEAFHASH does not parse its operand as a script; any byte string up to MAX_ELEMENT_BYTES is accepted. Each is charged as one hash over its operands at their size bounds.

With them a script can build the root of a branch tree from its parts and compare it with BRANCHROOT, or require it on an output through OUTPUTREQUIRESBRANCH, OUTPUTEXCLUSIVEBRANCH, OUTPUTCONTINUESBRANCH or ENFORCEOUTPUT. Furthermore, because `H_name(x) = BLAKE3(ASCII(tag) || 00 || x)` (`C08`) uses a plain ASCII prefix before unkeyed `BLAKE3`, any script can compute any domain-tagged hash in P02's registry (`H_txid`, `H_inputcore`, `H_output`, `H_coinentry`, `H_merkleidx`, etc.) in three instructions (`<"Lotus/v2/...\x00"> SWAP CAT BLAKE3`) without a separate opcode per domain tag. Contracts commit state via `STATEHASH` (`0xc3`), `STATEVERIFY` (`0xed`), and `ENFORCEOUTPUT` (`0xeb`) into `Output.state_root` (`HAS_STATE` `0x04`), or on a pruneable `IS_BURN` (`0x02`/`0x03`) output with `paths = []` and up to 16 32-byte commitment words/roots.

For contracts that maintain large internal sets, allowlists, or key-value maps, prove inputs or outputs of parent/injected transactions (`OUTPOINTTXID(i)`), or verify cross-chain SPV proofs, two dedicated opcodes fold a multi-level Merkle path in one instruction with an explicit `N(hash_alg)` selector (`0..3`, matching `CHECKDATASIG`'s selector convention):

- **`MERKLEROOT_SORTED` (`0xc0`):** Stack `leaf_hash proof_bytes N(hash_alg) → root_hash`.
  - Require `len(leaf_hash) == 32`, `len(proof_bytes) == 32 * k` for an integer `0 <= k <= 64`, and `hash_alg in 0..3`; any other operand length or selector value is a script error.
  - Initialize `acc = leaf_hash`. For step `s = 0 .. k - 1`, let `sib = proof_bytes[32*s : 32*(s+1)]`, and let `(lo, hi) = (acc, sib)` if `acc <= sib` (unsigned little-endian 256-bit comparison, as in P02 `BranchNode` and `LESSSWAP`) else `(sib, acc)`:
    - `hash_alg == 0` (Lotus Tagged BLAKE3): `acc = H_branch(01 || lo || hi)` (P02 `BranchNode(acc, sib)`)
    - `hash_alg == 1` (Raw BLAKE3): `acc = BLAKE3(lo || hi)`
    - `hash_alg == 2` (SHA256): `acc = SHA256(lo || hi)`
    - `hash_alg == 3` (HASH256 / Double-SHA256): `acc = SHA256(SHA256(lo || hi))`
  - Push the 32-byte `acc`. When `k == 0` (`proof_bytes` is empty), returns `leaf_hash` unchanged. Static cost is charged from P05's size bound `floor(bound(proof_bytes) / 32)` capped at 64 hashes and the hash cost of `hash_alg` (or `max(C_blake3, C_hash256)` when `hash_alg` is non-constant).
- **`MERKLEROOT_INDEXED` (`0xc1`):** Stack `leaf_hash key_bytes proof_bytes N(hash_alg) → root_hash`.
  - Require `len(leaf_hash) == 32`, `1 <= len(key_bytes) <= 32`, `len(proof_bytes) == 32 * k` for an integer `0 <= k <= 8 * len(key_bytes)`, and `hash_alg in 0..3`; any other operand length or selector value is a script error.
  - Initialize `acc = leaf_hash`. For step `s = 0 .. k - 1` (from the leaf bottom-up toward the root):
    - Let `bit = (key_bytes[s // 8] >> (s % 8)) & 1` (least-significant-bit first, matching P02) and `sib = proof_bytes[32*s : 32*(s+1)]`.
    - Let `(l, r) = (acc, sib)` if `bit == 0` else `(sib, acc)`:
      - `hash_alg == 0` (Lotus Tagged BLAKE3): `acc = H_merkleidx(01 || u16(s) || l || r)` (P02 `IndexedNode(s, l, r)`)
      - `hash_alg == 1` (Raw BLAKE3): `acc = BLAKE3(l || r)`
      - `hash_alg == 2` (SHA256): `acc = SHA256(l || r)`
      - `hash_alg == 3` (HASH256 / Double-SHA256): `acc = SHA256(SHA256(l || r))`
  - Push the 32-byte `acc`. When `k == 0`, returns `leaf_hash` unchanged. `merkleidx = Lotus/v2/merkleidx` is registered in P02.
  - Because step `s = 0 .. k - 1` uses bit `s` of `key_bytes` (`(index >> s) & 1`), `hash_alg == 0` directly matches P02's `IndexedTreeRoot` (`InputsRoot`, `OutputsRoot`, `CoinsRoot`), enabling $O(\log N)$ verification of any input or output of an injected/parent transaction (`OUTPOINTTXID(i)`), while `hash_alg == 3` directly matches Bitcoin/BCH/Lotus-v1 bottom-up `HASH256` Merkle trees.
  - Because `MERKLEROOT_INDEXED` returns the computed root rather than asserting equality, a single `proof_bytes` witness argument supports both **membership/non-membership checks** and **atomic in-place updates**: the contract calls `MERKLEROOT_INDEXED` with `(old_leaf_hash, key_bytes, proof_bytes, hash_alg)` to verify against the current map root, and calls `MERKLEROOT_INDEXED` with `(new_leaf_hash, key_bytes, proof_bytes, hash_alg)` to compute the updated map root for `OUTPUTCONTINUESBRANCH` (`ea`) or `ENFORCEOUTPUT` (`eb`).

LESSSWAP is a general ordering operation on byte strings. It reads each operand as an unsigned little-endian integer, so the last byte is the most significant, which is the byte order of every integer in this specification and the order P02 uses for branch-tree nodes. Operands may be any length up to MAX_ELEMENT_BYTES; a shorter one is treated as zero-extended, and if the two are then numerically equal the shorter is the smaller. It leaves the smaller deeper and the larger on top, so a following CAT yields `smaller || larger`. Identical operands are left as they are. NODEHASH and MERKLEROOT_SORTED order their operands themselves and do not need it; LESSSWAP is for contracts that keep sorted structures of their own. The numeric comparisons apply only to N values.

## Extension points & Two-Byte Opcode Encoding (MSB `0x80` / `EXT2` `0xff`)

Maintainer direction, October 11–18, 2026:
1. **Two-Byte Opcode Encoding (MSB `0x80` Variable-Length vs. `EXT2` `0xff` Prefix):**
   - **Candidate A (MSB Variable-Length Two-Byte Opcodes):** Bit 7 (`0x80` MSB) of the first opcode byte indicates opcode width:
     - When `(b0 & 0x80) == 0` (`0x00`–`0x7f`): 1-byte opcode (128 single-byte instructions for literals `00`–`5d`, control flow `60`–`6c`, and stack operations `70`–`7f`).
     - When `(b0 & 0x80) != 0` (`0x80`–`0xff`): 2-byte opcode; the decoder reads a second byte `b1` (`0x00`–`0xff`) to form a 15-bit opcode `((b0 & 0x7f) << 8) | b1` (`32,768` two-byte opcodes across `0x8000`–`0xffff`). A trailing `b0 >= 0x80` at end-of-script without `b1` rejects at framing/scan time.
   - **Candidate B (`EXT2` `0xff` Escape Prefix, compatible with current 1-byte `0x80`–`0xf6` table):** Every otherwise unassigned single-byte opcode (`0x00`–`0xfe`, excluding `EMITLOG` `0x6c`) is a generic `OP_SUCCESS_N` extension point, and byte **`0xff` (`EXT2`)** is the two-byte opcode prefix (`0xff <ext_op>`, forming 256 two-byte opcodes `0xff00`–`0xffff`).
2. **Unassigned Single-Byte `OP_SUCCESS_N` Table (under Candidate B):**
   - The current single-byte tables assign 225 bytes (including `EMITLOG` `0x6c` as `OP_INVALID` and `EXT2` `0xff`) and leave 31 single-byte success opcodes plus 256 two-byte extension opcodes (`0xff00`–`0xffff`):

```text
5e 5f 67 68 6d 6e 6f 82 83 84 85 86 87 95 96 97
b5 b6 b7 c4 c5 c6 c7 f7 f8 f9 fa fb fc fd fe
```

The suffix N is decimal: byte 5e is `OP_SUCCESS_94` and two-byte sequence `ff 00` is `OP_SUCCESS_EXT_0` (`0xff00`). Success is for the complete script invocation, not just a Boolean result or a no-op. This follows the unconditional-success principle in [BIP342](https://bips.dev/342/#specification). It leaves a spend path rather than permanently stranding a coin behind an undefined instruction. Wallets and relay policy must nevertheless refuse unassigned success instructions (both single-byte and `0xff <ext_op>`): before activation they provide no authorization protection.

**Validation order and scan.** First enforce transaction/witness framing, script and argument byte/count limits, path/witness matching, and the script's membership proof. These are outside the VM and cannot be bypassed. Then scan the script from byte zero, at instruction boundaries, before executing any instruction or checking structured control flow:

1. At an unassigned single-byte `OP_SUCCESS_N`, immediately return invocation success. At `0xff` (`EXT2`), require at least 1 following byte `ext_op` (a trailing `0xff` at end-of-script without its selector byte rejects as malformed framing, just like a truncated `PUSH_n`); if `0xff <ext_op>` is an unassigned two-byte opcode (`OP_SUCCESS_EXT_N`), immediately return invocation success. Do not parse the suffix, execute the prefix, or require clean final stacks. An earlier RETURN, an unmatched IF or loop delimiter, or a success opcode in an unexecuted arm does not prevent this result.
2. At `PUSH_n`, skip exactly `n` data bytes; truncation rejects. At `4c`, parse shortest CompactSize, require the allowed canonical push form, check the element limit and available bytes, then skip the payload. A malformed push before a success opcode rejects because later instruction boundaries cannot be established. Push payload bytes never trigger success.
3. At any other assigned single-byte instruction, advance one byte (or two bytes for an assigned `0xff <ext_op>` instruction) without executing it. If the scan reaches the end without success, run ordinary full decoding, static charging and execution. All ordinary syntax, runtime and final-stack rules then apply.

Only this invocation succeeds automatically. Every other branch on the selected path, every other input/mint, conservation, locks, block commitments and enclosing resource budgets still require validation. A sole-branch policy whose revealed script contains an unassigned success opcode is effectively anyone-can-spend; a separate required owner branch remains enforced.

**Soft-fork contract.** Assigning a single-byte success opcode or a two-byte `0xff <ext_op>` opcode may define new operations, stack effects or suffix syntax, because old nodes accepted the whole invocation without interpreting those effects. The new valid transaction/block set MUST be a subset of the old valid set, including outer framing, limits and aggregate charges. Freeze activation and enforcement costs before assignment. The monetary accounting schedule and accounting success-byte set stay fixed at genesis (P05), so old and upgraded validators derive identical post-state roots for every newly valid block. No existing assigned opcode, push framing, CHECKDATASIG algorithm selector, version, flags, lock kind or signing mode gains implicit success behavior. CHECKDATASIG recognizes only algorithms 0..3; every other selector errors. Future cryptography can use a generic success byte or `0xff <ext_op>` two-byte opcode instead of reopening that closed selector set.

Relay/mining policy refuses a transaction if the scan finds an unassigned single-byte or two-byte (`0xff <ext_op>`) success opcode in any revealed script, including skipped arms. Output roots do not reveal hidden scripts, so this policy is not a creation-time inspection guarantee. At activation, recheck affected mempool entries and caches. Activation/signalling remains a separate network-upgrade decision.

**Charges.** An automatically successful invocation pays a deterministic structural charge for its complete script bytes and the success scan, plus ordinary witness parsing, argument bytes, proof and transaction/block overhead. It executes no VM instructions and has no ordinary AST/size-pass charge. This charge is computable even when the ignored suffix is malformed. After assignment, the frozen accounting view keeps this exact baseline; the separate enforcement view must cover all additional execution work. Only frozen accounting costs update the monetary EMA (P05). CHECKDATASIG with a nonconstant selector is charged at the most expensive defined profile plus hashing at operand bounds; unknown selectors error. A new operation expressible with existing instructions remains a compiler function and needs no assignment.

## CHECKDATASIG profile proposal

Message operand is exactly 32 bytes for every defined profile (0..3). Stack signature, message, public_key, N(algorithm) are consumed. Every algorithm outside 0..3 errors; there are no reserved success selectors. A wrong size or a malformed/noncanonical public key errors. Any correctly sized signature that fails the selected profile, including scalar/point canonicality, subgroup or verification checks, produces false. Application protocols must domain-separate their message construction.

- **0:** BIP340, 32-byte x-only secp256k1 key, 64-byte signature, direct verification over message bytes.
- **1:** ECDSA over P-256, SEC1 compressed 33-byte key, signature r||s as two unsigned big-endian 32-byte integers; 1≤r<n and 1≤s≤floor(n/2). The message is the already-computed 256-bit digest supplied to ECDSA, not hashed again. DER and high-S encodings are not accepted. P-256 point/domain parameters and ECDSA follow [SEC1](https://www.secg.org/sec1-v2.pdf) and [FIPS 186-5](https://csrc.nist.gov/pubs/fips/186-5/final).
- **2:** Strict prime-subgroup Ed25519 profile: canonical 32-byte public-key/encoded-R points, 64-byte R||S signature, S<L; A and R must be nonidentity points in the prime-order subgroup. Verify the uncofactored equation `[S]B=R+[h]A`, using the pure-Ed25519 SHA512 challenge over R||A||message and canonical encodings. This intentionally specifies a narrower acceptance profile than some Ed25519 libraries; do not substitute their default verifier. [RFC 8032](https://www.rfc-editor.org/rfc/rfc8032) supplies curve/encoding/hash definitions. The message is 32 application bytes, not Ed25519ph mode.
- **3:** ECDSA over secp256k1, SEC1 compressed 33-byte key, signature r||s as two unsigned big-endian 32-byte integers; 1≤r<n and 1≤s≤floor(n/2). The message is the already-computed 256-bit digest supplied to ECDSA, not hashed again. DER and high-S encodings are not accepted. This is the same curve as profile 0 with the older signature scheme, included because many signing cards, secure elements and HSMs implement secp256k1 ECDSA but not BIP340. A device that hashes its input with SHA256 before signing is accommodated by applying the SHA256 opcode to the message in script. Profile 0 remains preferred where the device supports it.

These profiles are proposals needing independent library/edge-vector review and costs; they are not an assertion that existing Lotus libraries accept exactly this set. Dedicated key types and explicit algorithm selection prevent a 64-byte signature from ambiguously selecting two algorithms. An on-device WebAuthn assertion additionally requires the application's challenge/origin/authenticator policy and cannot be reduced to the existence of P-256 verification.

## Cost proof obligations

Ordinary invocations use decoded syntax and per-operand size bounds from P05's size pass (the maximum permitted operand where it has none), never interpreter execution to estimate a bound. Automatically successful invocations use the structural charge above. Account for pushes/copies, control frames, stack memory, proof hashing and each crypto profile. A bounded algorithm can still be too expensive; no numerical cost schedule is frozen here. Test success scanning, pushed success bytes, malformed pushes before and after success, nested condition/loop exits, boundary arithmetic and both stack caps with the reference evaluator. Assigning a success byte must satisfy the soft-fork contract above.

---

## References

1. **[Nakamoto 2008]** Satoshi Nakamoto, *"Bitcoin: A Peer-to-Peer Electronic Cash System"*, October 2008 (`https://bitcoin.org/bitcoin.pdf`).
2. **[Lau & Wuille 2016a]** Johnson Lau and Pieter Wuille, *"BIP 114: Merkelized Abstract Syntax Tree"*, Bitcoin Improvement Proposals, April 2016.
3. **[Wuille, Nick, & Towns 2020a]** Pieter Wuille, Jonas Nick, and Anthony Towns, *"BIP 341: Taproot: SegWit version 1 spending rules"*, Bitcoin Improvement Proposals, January 2020.
4. **[Wuille, Nick, & Towns 2020b]** Pieter Wuille, Jonas Nick, and Anthony Towns, *"BIP 342: Validation of Taproot Scripts"*, Bitcoin Improvement Proposals, January 2020.
5. **[Möser, Eyal, & Sirer 2016]** Malte Möser, Ittay Eyal, and Emin Gün Sirer, *"Bitcoin Covenants"*, in *Financial Cryptography and Data Security (FC 2016)*, LNCS vol. 9604, pp. 126–141, 2016.
6. **[O'Connor & Piekarska 2017]** Russell O'Connor and Marta Piekarska, *"Enhancing Bitcoin Transactions with Covenants"*, in *Financial Cryptography and Data Security (FC 2017)*, LNCS vol. 10323, pp. 191–198, 2017.
7. **[Wuille, Nick, & Ruffing 2020]** Pieter Wuille, Jonas Nick, and Tim Ruffing, *"BIP 340: Schnorr Signatures for secp256k1"*, Bitcoin Improvement Proposals, January 2020.
8. **[O'Connor, Aumasson, Neves, & Wilcox-O'Hearn 2020]** Jack O'Connor, Jean-Philippe Aumasson, Samuel Neves, and Zooko Wilcox-O'Hearn, *"BLAKE3: One Function, Fast Everywhere"*, January 2020 (`https://github.com/BLAKE3-team/BLAKE3-specs`).
