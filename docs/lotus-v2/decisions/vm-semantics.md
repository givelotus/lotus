# VM semantics and opcode allocation candidate

Decision packet P03, October 9, 2026. **Recommended candidate**, not frozen. Resolves concrete stack/control/arithmetic questions for D07; the cost schedule and independent crypto/opcode vectors remain blockers. This is a v2 machine, not Bitcoin Script with implicit inherited edge cases.

## Values and parsing

Stacks contain bounded byte strings. `N(x)` is exactly sixteen-byte signed little-endian int128. `U(x)` interprets exactly sixteen bytes as an unsigned limb; its output is also sixteen raw bytes. Boolean consumers accept only N(0)/N(1). Comparisons and signatures produce those canonical booleans. For ordinary execution, main and alternate stacks start as described in the ABI; finish requires main=[N(1)], alternate=[]. The success-scan exception below initializes neither stack. Every push, duplicate, move and concatenation must satisfy element/count/total-byte limits before mutation.

First perform the bounded OP_SUCCESS_N scan specified below. If it finds no unassigned success opcode, decode the entire script to structured syntax before execution, including unreachable regions; malformed pushes and unmatched structures reject even in skipped code. Push data bytes are never opcodes. Canonical push framing is one-byte fixed length for 1..75 bytes, or opcode 4c followed by shortest `Bytes(data)` for empty data or lengths ≥76. Bytes 4d and 4e have no legacy PUSHDATA meaning: they are unassigned OP_SUCCESS_N opcodes. Constant opcodes push N values. A fixed-length push of sixteen bytes is allowed even if a constant opcode could produce the same stack item: different programs have different commitments; canonical parsing does not imply a unique program for each computation.

## Closed candidate allocation

Every byte not assigned an instruction in these tables is OP_SUCCESS_N, where N is its unsigned decimal byte value. An unassigned success opcode unconditionally succeeds for the entire invocation under the scan below; it does not push true and continue. Each assigned byte has the semantics below or in the referenced packet. This table is an allocation proposal requiring byte-for-byte vectors before D07 closes. Historical Bitcoin, Mitra and BIGINT assignments are not aliases. NOP remains permanently a NOP.

| Hex | Instruction | Stack effect / meaning (rightmost is top) |
| --- | --- | --- |
| 00 | ZERO | push N(0) |
| 01–4b | PUSH_n | push next n bytes, 1≤n≤75 |
| 4c | PUSHDATA | push Bytes payload; only length 0 or ≥76 |
| 4f | NEGATIVE_ONE | push N(−1) |
| 51–60 | ONE through SIXTEEN | push corresponding N |
| 61 | NOP | no effect; permanently no effect (not an extension point) |
| 63 | IF | pop Boolean; execute selected arm |
| 64 | NOTIF | IF with inverted Boolean |
| 67 | ELSE | structural alternate arm delimiter |
| 68 | ENDIF | structural conditional end |
| 69 | VERIFY | pop Boolean; false rejects |
| 6a | RETURN | reject when executed |
| 6b | TOALTSTACK | main top moves to alternate top |
| 6c | FROMALTSTACK | alternate top moves to main top |
| 6d | 2DROP | a b → empty |
| 6e | 2DUP | a b → a b a b |
| 6f | 3DUP | a b c → a b c a b c |
| 70 | 2OVER | a b c d → a b c d a b |
| 71 | 2ROT | a b c d e f → c d e f a b |
| 72 | 2SWAP | a b c d → c d a b |
| 74 | DEPTH | push N(main item count before push) |
| 75 | DROP | x → empty |
| 76 | DUP | x → x x |
| 77 | NIP | a b → b |
| 78 | OVER | a b → a b a |
| 79 | PICK | pop numeric n; copy nth remaining item from top, top=0 |
| 7a | ROLL | pop numeric n; move nth remaining item to top |
| 7b | ROT | a b c → b c a |
| 7c | SWAP | a b → b a |
| 7d | TUCK | a b → b a b |
| 7e | CAT | a b → a concatenated with b |
| 7f | SPLIT | bytes N(i) → bytes[0:i] bytes[i:] |
| 80 | NUM2BIN | N(x) N(width) → signed LE encoding of x at exact width |
| 81 | BIN2NUM | 0..16 bytes interpreted signed LE → N(x); empty → N(0) |
| 82 | SIZE | bytes → bytes N(byte length) |
| 83 | INVERT | bytes → bitwise complement of every byte |
| 84 | AND | equal-length a b → bytewise a AND b |
| 85 | OR | equal-length a b → bytewise a OR b |
| 86 | XOR | equal-length a b → bytewise a XOR b |
| 87 | EQUAL | a b → Boolean byte equality |
| 88 | EQUALVERIFY | EQUAL then VERIFY |
| 8b | 1ADD | N(a) → N(a+1), checked |
| 8c | 1SUB | N(a) → N(a−1), checked |
| 8f | NEGATE | N(a) → N(−a), checked |
| 90 | ABS | N(a) → N(abs(a)), checked |
| 91 | NOT | Boolean → inverted Boolean |
| 92 | 0NOTEQUAL | N(a) → Boolean(a≠0) |
| 93 | ADD | N(a) N(b) → N(a+b), checked |
| 94 | SUB | N(a) N(b) → N(a−b), checked |
| 95 | MUL | N(a) N(b) → N(a*b), checked |
| 96 | DIV | N(a) N(b) → N(trunc_toward_zero(a/b)) |
| 97 | MOD | N(a) N(b) → N(a−trunc_toward_zero(a/b)*b) |
| 98 | RAWLEFTBITSHIFT | bytes N(k) → fixed-width logical shift defined below |
| 99 | MULPOW2 | N(a) N(k) → checked a*2^k or truncating division |
| 9a | BOOLAND | Boolean a b → Boolean(a AND b) |
| 9b | BOOLOR | Boolean a b → Boolean(a OR b) |
| 9c | NUMEQUAL | N(a) N(b) → Boolean(a=b) |
| 9d | NUMEQUALVERIFY | NUMEQUAL then VERIFY |
| 9e | NUMNOTEQUAL | N(a) N(b) → Boolean(a≠b) |
| 9f | LESSTHAN | N(a) N(b) → Boolean(a<b) |
| a0 | GREATERTHAN | N(a) N(b) → Boolean(a>b) |
| a1 | LESSTHANOREQUAL | N(a) N(b) → Boolean(a≤b) |
| a2 | GREATERTHANOREQUAL | N(a) N(b) → Boolean(a≥b) |
| a3 | MIN | N(a) N(b) → N(min(a,b)) |
| a4 | MAX | N(a) N(b) → N(max(a,b)) |
| a5 | WITHIN | N(x) N(lo) N(hi) → Boolean(lo≤x<hi) |
| a8 | SHA256 | bytes → SHA256(bytes) |
| aa | HASH256 | bytes → SHA256(SHA256(bytes)) |
| ac | CHECKSIG | signature public_key → Boolean, P01 transaction message; 64-byte signature = mode 00, 65-byte = explicit partial mode |
| ad | CHECKSIGVERIFY | CHECKSIG then VERIFY |
| b1 | CHECKLOCKTIMEVERIFY | N(kind) N(bound) → empty, absolute transaction lock check |
| b2 | CHECKSEQUENCEVERIFY | N(kind) N(bound) → empty, current consuming input's relative lock check |
| b4 | ADDCARRY | U(a) U(b) N(c) → U(low128(a+b+c)) N(carry) |
| b5 | SUBCARRY | U(a) U(b) N(c) → U((a−b−c) mod 2^128) N(borrow) |
| b6 | MUL128_WIDE | U(a) U(b) → U(high128(a*b)) U(low128(a*b)) |
| ba | CHECKDATASIG | signature message public_key N(algorithm) → Boolean, profile below |
| bb | UTXOPROOFVERIFY | outpoint proof map_root → Boolean, P02 single-key proof |
| bd | LOG | N(x) → N(LOG2_Q64(x)), algorithm below |
| be | SQRT | N(x) → N(floor(sqrt(x))); x≥0 |
| bf | BLAKE3 | bytes → unkeyed 32-byte BLAKE3(bytes), no application tag |
| c0–df | Introspection and loop allocation | Explicit table below; cf and d3 are OP_SUCCESS_207 and OP_SUCCESS_211 |
| e0–ed | Invocation introspection, branch checks, ordering and tree hashes | Explicit table below |
| all otherwise unassigned bytes | OP_SUCCESS_N | Unconditional invocation success during the scan below |

Existing template spellings may prefix `OP_`; that does not alter bytes. OP_MERKLEVERIFY is replaced by a specifically typed UTXOPROOFVERIFY name at bb: it verifies P02's map proof, not any arbitrarily named Merklix structure. A proof succeeds only if its reconstructed map root equals the 32-byte operand; malformed proof framing errors reject. A well-formed mismatching proof pushes false. The proof's presence flag is part of its bytes; a contract must inspect/require the intended presence and Coin content when relying on the claim. This opcode does not authenticate a map root to a block header by itself.

## Arithmetic edge semantics

PICK/ROLL require `0≤n<remaining_stack_size`; SPLIT requires `0≤i≤len(bytes)`. NUM2BIN width must be 0..MAX_ELEMENT_BYTES and x must fit its signed width; zero width accepts only zero. Larger widths sign-extend. BIN2NUM sign-extends to sixteen bytes and never silently truncates longer input. Decode an unsigned short byte string by appending a zero sign byte before BIN2NUM where needed; an unsigned 128-bit limb with its high bit set stays a U operand, not a positive N.

All signed arithmetic overflow rejects. DIV and MOD reject zero divisor and the minimum-int/−1 case. NEGATE/ABS of minimum-int reject. Carry input must be N(0) or N(1); borrow is one iff a<b+c. Wide operations use bounded 129/256-bit intermediates independent of host integer types.

RAWLEFTBITSHIFT interprets bytes as unsigned little-endian, retains the original byte length and discards shifted-out bits. Positive k shifts left; negative k shifts right; abs(k)≥8*length returns all-zero bytes of the same length. Handle minimum-int k by comparison, not an overflowing signed absolute operation. MULPOW2 uses signed mathematical a, preserves no discarded high bits on multiplication, and truncates division toward zero. For nonzero a, k≥128 rejects; a=0 returns zero. For k≤−128 the division result is zero. Intermediate host shifts by their type width are never the definition.

LOG returns the following fixed algorithm, **not a claim of exact real logarithm rounding**. Require x>0. Let e=floor(log2(x)) determined by bit length; z=x*2^(127−e). Initialize f=0. Repeat exactly 64 times: t=floor(z*z/2^127); bit=1 if t≥2^128, else 0; z=floor(t/2) if bit=1 else t; f=2*f+bit. Return N(e*2^64+f). Products fit unsigned 256 bits. SQRT is the largest nonnegative integer r with r*r≤x; implementations may use any equivalent bounded algorithm. Monetary consensus need not use these script opcodes to implement its own recurrence.

## Introspection and execution contexts

Indices/results are N values; hashes/outpoints/scripts remain bytes. Token ID reads zero only for native coins. Every index and integer result must be representable and checked before access.

| Hex | Name | Effect |
| --- | --- | --- |
| c0 | INPUTINDEX | push the index of the input this script is running for: the spend input in a spend, the mint input in a mint |
| c1 | ACTIVEBYTECODE | push exact active script bytes |
| c2 | TXVERSION | push transaction version |
| c3 | TXINPUTCOUNT | push input count |
| c4 | TXOUTPUTCOUNT | push output count |
| c5 | TXLOCKTIME | push 56-bit lock_value as N |
| c6 | UTXOVALUE | i → resolved coin value |
| c7 | UTXOBRANCH | i k → resolved branch[k] |
| c8 | OUTPOINTTXID | i → prev_txid |
| c9 | OUTPOINTINDEX | i → prev_index |
| ca | UTXOTOKENID | i → resolved asset ID |
| cc | OUTPUTVALUE | j → output value |
| cd | OUTPUTBRANCH | j k → output branch[k] |
| ce | OUTPUTTOKENID | j → output asset ID |
| d0 | TXID | push ChainID-bound core TxID |
| d1 | ENUMERATE_INPUTS | structured loop with fixed input_count bound |
| d2 | ENUMERATE_OUTPUTS | structured loop with fixed output_count bound |
| d4 | TXMINTCOUNT | push the number of mint inputs (flags `03`) |
| d5 | INPUTSEQUENCENUMBER | i → sequence |
| d6 | INPUTFLAGS | i → flags |
| d7 | UTXOBRANCHCOUNT | i → resolved branch count |
| d8 | OUTPUTBRANCHCOUNT | j → output branch count |
| d9 | OUTPUTFLAGS | j → output flags |
| da | ENUMERATE | pop N in 0..256; structured loop |
| db | ENDENUMERATE | structural loop end |
| dc | BREAK | pop N(depth); exit that many enclosing active loops |
| dd | UTXOPATHCOUNT | i → resolved path count |
| de | OUTPUTPATHCOUNT | j → output path count |
| e0 | TXLOCKKIND | push absolute lock_kind |
| e1 | INVOCATIONKIND | push 1 for spend, 3 for mint, the same numbers as input flags |
| df | UTXOREQUIRESBRANCH | i root → Boolean: every path of resolved coin i includes a branch equal to root |
| e2 | BRANCHROOT | push the 32-byte root the active script was proven against: the branch root in a spend, the token ID in a mint |
| e3 | OUTPUTREQUIRESBRANCH | j root → Boolean: every path of output j includes a branch equal to root |
| cb | OUTPUTEXCLUSIVEBRANCH | j root → Boolean: output j has a path consisting of that branch alone, and every other path of output j also includes it |
| e4 | INPUTPATHINDEX | i → selected path of spend input i |
| e5 | UTXOPATH | i p → canonical Vec(CS(branch_index)) bytes |
| e6 | OUTPUTPATH | j p → canonical Vec(CS(branch_index)) bytes |
| e7 | UTXOOUTPUT | i → complete serialized Output bytes |
| e8 | OUTPUTRECORD | j → complete serialized Output bytes |
| e9 | LESSSWAP | a b → the same two items with the smaller one deeper and the larger on top, compared as unsigned little-endian integers |
| ea | LEAFHASH | script_bytes → P02 `Leaf(script_bytes)`, 32 bytes |
| eb | CHAINID | push the immutable 32-byte chain identifier |
| ec | SIGHASH | N(mode) → P01's 32-byte message for this invocation in that signing mode (0, 1 or 2) |
| ed | NODEHASH | a b → P02 `BranchNode(a,b)`, 32 bytes; a and b must each be exactly 32 bytes |
| all otherwise unassigned bytes | OP_SUCCESS_N | Unconditional invocation success during the scan below |

A mint is an input (flags `03`), so a mint script has an input position like any other and INPUTINDEX returns it. A mint input resolves no coin: UTXO-prefixed reads at a mint input's index error, and a script that scans inputs tests INPUTFLAGS first. A mint invocation receives the rest of its context on the stack instead of through context-only opcodes: after the witness arguments are pushed, the node pushes the positive mint delta as N, so it is on top. The token ID is not pushed: in a mint it is the root the script was proven against, which BRANCHROOT returns in any invocation. With u64 amounts and at most 2^16−1 outputs, positive token delta is below 2^80, so it fits N. A mint script must consume the delta. This stack shape is not a security boundary between mint and spend scripts; P02 requires them to be kept in separate trees. Returned serialized outputs/paths and active bytecode must fit the element limit; using such an opcode on a larger object errors. This does not make the underlying output invalid by itself. Length-aware costs charge bounded serialization/copy work. There is no introspection of other invocations' successful execution, mutable VM state, signature arguments or TxHash; P01's core witness binding is not such an opcode.

BRANCHROOT lets a script name the tree it belongs to without containing its own hash. UTXOREQUIRESBRANCH and OUTPUTREQUIRESBRANCH answer, in one operation, whether a policy makes a given tree mandatory: true iff the root operand is exactly 32 bytes and every path contains at least one branch index whose root equals it. Because C09 makes branch roots distinct within an output, at most one index k has that root, and the result equals: k exists and bit k is set in the intersection of all path index sets. Together they let a covenant require that a successor output stays under its own rules for any policy shape, using a single loop over outputs. Walking paths and their entries in script would need three nested loops, which C22 forbids. Their cost is charged at the maximum permitted paths times path length. A mint, coinbase or out-of-range index errors for the UTXO form.

No opcode exposes the height, time or hash of the block being built or of any ancestor; earlier drafts had BLOCKHEIGHT and BLOCKMEDIANTIME at bytes e9 and ea; they now hold LESSSWAP and LEAFHASH. This keeps validity monotone (C22a): a script's result depends only on the transaction, its resolved coins and ChainID, so it cannot change as blocks arrive. A script can require that a height or time has been reached by constraining TXLOCKTIME or the input's sequence, which the node enforces as minimum locks. A script cannot require that a height or time has not yet passed. A certificate or quote that must stop working is instead tied to a coin and ends when that coin is spent, which is an ordinary input conflict. SIGHASH takes the signing mode as an operand and pushes P01's message for that mode: 0 everywhere, 1 or 2 only in a spend invocation; any other value, or a partial mode in a mint invocation, errors. A script may fix the mode with a constant or take it from a witness argument so the signer chooses. This lets an ECDSA or Ed25519 policy checked with CHECKDATASIG bind its signature to the same intent as CHECKSIG in any of the three modes, without one opcode per mode and without reconstructing hidden witness-plan fields in Script.

CHECKLOCKTIMEVERIFY accepts kind 1 or 2 and nonnegative bound: require tx.lock_kind=kind and tx.lock_value≥bound. CHECKSEQUENCEVERIFY accepts kind 1 (height) or 2 (512-second units), bound 0..65535; require current spend's enabled relative lock of that kind and encoded delay≥bound. Both consume their operands. Global P01 lock checks enforce the actual candidate context. Mint context may use the absolute check but not the input-relative check.

## Structured evaluation and BREAK

Grammar: a sequence consists of ordinary instructions, `IF sequence [ELSE sequence] ENDIF` (or NOTIF), and `ENUMERATE* sequence ENDENUMERATE`. Constructs must nest properly; crossing a loop delimiter with an unmatched conditional rejects at decode time. At most two nested loop nodes are permitted on any syntax path, including skipped arms. A separate fixed parameter bounds conditional/AST nesting.

A loop captures its bound once on entry. Each iteration pushes N(index), evaluates its body, then advances; the body may consume or leave that index like any stack value. Bound zero does not evaluate the body. IF consumes one canonical Boolean only when executed. Underflow/runtime operand errors in unexecuted code do not occur; its syntax/opcodes are nevertheless checked and charged conservatively.

Define evaluation results `Continue`, `ExitLoops(d)`, or `Error`. BREAK with `1≤d≤active_loop_depth` produces ExitLoops(d). Sequence/conditional nodes immediately propagate it. A loop receiving ExitLoops(1) terminates and returns Continue; receiving ExitLoops(d>1) terminates and returns ExitLoops(d−1). This specifies conditional-frame unwinding without byte-offset guesses. All existing stack effects persist. No BREAK signal may escape the top-level sequence.

## Exclusive branch check

OUTPUTREQUIRESBRANCH proves that a root is present on every path of an output and says nothing about what else is there. That is right when the holder is meant to add branches of their own, as with a token's rules. It is not enough when a script creates a coin for someone else or continues a contract: a spender could satisfy it and still require a further branch on every path, one only they can satisfy or one nobody can, leaving the coin held hostage or burned.

OUTPUTEXCLUSIVEBRANCH closes that with one more condition. It is true exactly when both hold for output j:

1. Some path consists of the single branch whose root equals `root`. The coin can therefore always be spent by satisfying that branch alone.
2. Every other path also includes that branch. No path lets anyone spend without it.

Other paths that pass are only stricter versions of the first and add no way to spend. The root operand must be exactly 32 bytes. The node answers from the output's own branches and paths, at the same charge as OUTPUTREQUIRESBRANCH.

## Tree-hash opcodes and LESSSWAP

LEAFHASH and NODEHASH compute P02's branch-tree leaf and node hashes exactly as consensus does when it checks a membership proof: the domain tag, the leaf or node marker, the length framing of a leaf, and the ordering of a node's two children are all applied by the opcode. A script supplies only the script bytes, or the two child hashes. Everyone who computes these hashes, wallet, node and script alike, uses the same tagged functions; there is no untagged form. LEAFHASH does not parse its operand as a script; any byte string up to MAX_ELEMENT_BYTES is accepted. Each is charged as one hash over its operands at their size bounds.

With them a script can build the root of a branch tree from its parts and compare it with BRANCHROOT, or require it on an output through OUTPUTREQUIRESBRANCH or OUTPUTEXCLUSIVEBRANCH. Their main use is P02's data-leaf convention, by which a contract keeps state inside its own tree and consensus needs no state field. They also let a script check an arbitrary membership proof against any branch root.

LESSSWAP is a general ordering operation on byte strings. It reads each operand as an unsigned little-endian integer, so the last byte is the most significant, which is the byte order of every integer in this specification and the order P02 uses for branch-tree nodes. Operands may be any length up to MAX_ELEMENT_BYTES; a shorter one is treated as zero-extended, and if the two are then numerically equal the shorter is the smaller. It leaves the smaller deeper and the larger on top, so a following CAT yields `smaller || larger`. Identical operands are left as they are. NODEHASH orders its operands itself and does not need it; LESSSWAP is for contracts that keep sorted structures of their own. The numeric comparisons apply only to N values.

## Extension points

Maintainer direction, October 11, 2026: every otherwise unassigned opcode byte is a generic OP_SUCCESS_N extension point. This replaces the eight no-op EXTENSION instructions and the reserved CHECKDATASIG algorithm selectors. The current tables assign 213 bytes and leave 43 success bytes:

```text
4d 4e 50 62 65 66 73 89 8a 8d 8e a6 a7 a9 ab ae af
b0 b3 b7 b8 b9 bc cf d3 ee ef f0 f1 f2 f3 f4 f5 f6 f7
f8 f9 fa fb fc fd fe ff
```

The suffix N is decimal: byte 50 is OP_SUCCESS_80 and byte ff is OP_SUCCESS_255. Success is for the complete script invocation, not just a Boolean result or a no-op. This follows the unconditional-success principle in [BIP342](https://bips.dev/342/#specification). It leaves a spend path rather than permanently stranding a coin behind an undefined instruction. Wallets and relay policy must nevertheless refuse unassigned success instructions: before activation they provide no authorization protection.

**Validation order and scan.** First enforce transaction/witness framing, script and argument byte/count limits, path/witness matching, and the script's membership proof. These are outside the VM and cannot be bypassed. Then scan the script from byte zero, at instruction boundaries, before executing any instruction or checking structured control flow:

1. At an unassigned OP_SUCCESS_N, immediately return invocation success. Do not parse the suffix, execute the prefix, or require clean final stacks. An earlier RETURN, an unmatched IF or loop delimiter, or a success opcode in an unexecuted arm does not prevent this result.
2. At PUSH_n, skip exactly n data bytes; truncation rejects. At 4c, parse shortest CompactSize, require the allowed canonical push form, check the element limit and available bytes, then skip the payload. A malformed push before a success opcode rejects because later instruction boundaries cannot be established. Push payload bytes never trigger success.
3. At any other assigned instruction, advance one byte without executing it. If the scan reaches the end without success, run ordinary full decoding, static charging and execution. All ordinary syntax, runtime and final-stack rules then apply.

Only this invocation succeeds automatically. Every other branch on the selected path, every other input/mint, conservation, locks, block commitments and enclosing resource budgets still require validation. A sole-branch policy whose revealed script contains an unassigned success opcode is effectively anyone-can-spend; a separate required owner branch remains enforced.

**Soft-fork contract.** Assigning a success byte may define new operations, stack effects or suffix syntax, because old nodes accepted the whole invocation without interpreting those effects. The new valid transaction/block set MUST be a subset of the old valid set, including outer framing, limits and aggregate charges. Freeze activation and costs before assignment. No existing assigned opcode, push framing, CHECKDATASIG algorithm selector, version, flags, lock kind or signing mode gains implicit success behavior. CHECKDATASIG recognizes only algorithms 0..3; every other selector errors. Future cryptography can use a generic success byte instead of reopening that closed selector set.

Relay/mining policy refuses a transaction if the scan finds an unassigned success opcode in any revealed script, including skipped arms. Output roots do not reveal hidden scripts, so this policy is not a creation-time inspection guarantee. At activation, recheck affected mempool entries and caches. Activation/signalling remains a separate network-upgrade decision.

**Charges.** An automatically successful invocation pays a deterministic structural charge for its complete script bytes and the success scan, plus ordinary witness parsing, argument bytes, proof and transaction/block overhead. It executes no VM instructions and has no ordinary AST/size-pass charge. This charge is computable even when the ignored suffix is malformed. The assigned implementation's charge must be at least this baseline and cover its additional work. CHECKDATASIG with a nonconstant selector is charged at the most expensive defined profile plus hashing at operand bounds; unknown selectors error. A new operation expressible with existing instructions remains a compiler function and needs no assignment.

## CHECKDATASIG profile proposal

Message operand is exactly 32 bytes for every defined profile (0..3). Stack signature, message, public_key, N(algorithm) are consumed. Every algorithm outside 0..3 errors; there are no reserved success selectors. A wrong size or a malformed/noncanonical public key errors. Any correctly sized signature that fails the selected profile, including scalar/point canonicality, subgroup or verification checks, produces false. Application protocols must domain-separate their message construction.

- **0:** BIP340, 32-byte x-only secp256k1 key, 64-byte signature, direct verification over message bytes.
- **1:** ECDSA over P-256, SEC1 compressed 33-byte key, signature r||s as two unsigned big-endian 32-byte integers; 1≤r<n and 1≤s≤floor(n/2). The message is the already-computed 256-bit digest supplied to ECDSA, not hashed again. DER and high-S encodings are not accepted. P-256 point/domain parameters and ECDSA follow [SEC1](https://www.secg.org/sec1-v2.pdf) and [FIPS 186-5](https://csrc.nist.gov/pubs/fips/186-5/final).
- **2:** Strict prime-subgroup Ed25519 profile: canonical 32-byte public-key/encoded-R points, 64-byte R||S signature, S<L; A and R must be nonidentity points in the prime-order subgroup. Verify the uncofactored equation `[S]B=R+[h]A`, using the pure-Ed25519 SHA512 challenge over R||A||message and canonical encodings. This intentionally specifies a narrower acceptance profile than some Ed25519 libraries; do not substitute their default verifier. [RFC 8032](https://www.rfc-editor.org/rfc/rfc8032) supplies curve/encoding/hash definitions. The message is 32 application bytes, not Ed25519ph mode.
- **3:** ECDSA over secp256k1, SEC1 compressed 33-byte key, signature r||s as two unsigned big-endian 32-byte integers; 1≤r<n and 1≤s≤floor(n/2). The message is the already-computed 256-bit digest supplied to ECDSA, not hashed again. DER and high-S encodings are not accepted. This is the same curve as profile 0 with the older signature scheme, included because many signing cards, secure elements and HSMs implement secp256k1 ECDSA but not BIP340. A device that hashes its input with SHA256 before signing is accommodated by applying the SHA256 opcode to the message in script. Profile 0 remains preferred where the device supports it.

These profiles are proposals needing independent library/edge-vector review and costs; they are not an assertion that existing Lotus libraries accept exactly this set. Dedicated key types and explicit algorithm selection prevent a 64-byte signature from ambiguously selecting two algorithms. An on-device WebAuthn assertion additionally requires the application's challenge/origin/authenticator policy and cannot be reduced to the existence of P-256 verification.

## Cost proof obligations

Ordinary invocations use decoded syntax and per-operand size bounds from P05's size pass (the maximum permitted operand where it has none), never interpreter execution to estimate a bound. Automatically successful invocations use the structural charge above. Account for pushes/copies, control frames, stack memory, proof hashing and each crypto profile. A bounded algorithm can still be too expensive; no numerical cost schedule is frozen here. Test success scanning, pushed success bytes, malformed pushes before and after success, nested condition/loop exits, boundary arithmetic and both stack caps with the reference evaluator. Assigning a success byte must satisfy the soft-fork contract above.
