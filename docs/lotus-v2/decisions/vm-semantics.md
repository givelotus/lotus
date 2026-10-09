# VM semantics and opcode allocation candidate

Decision packet P03, October 9, 2026. **Recommended candidate**, not frozen. Resolves concrete stack/control/arithmetic questions for D07; the cost schedule and independent crypto/opcode vectors remain blockers. This is a v2 machine, not Bitcoin Script with implicit inherited edge cases.

## Values and parsing

Stacks contain bounded byte strings. `N(x)` is exactly sixteen-byte signed little-endian int128. `U(x)` interprets exactly sixteen bytes as an unsigned limb; its output is also sixteen raw bytes. Boolean consumers accept only N(0)/N(1). Comparisons and signatures produce those canonical booleans. Main and alternate stacks start as described in the ABI; finish requires main=[N(1)], alternate=[]. Every push, duplicate, move and concatenation must satisfy element/count/total-byte limits before mutation.

Decode the entire script to structured syntax before execution, including unreachable regions. Unknown/disabled opcodes and malformed pushes reject even in skipped code. Push data bytes are never opcodes. Canonical push framing is one-byte fixed length for 1..75 bytes, or opcode 4c followed by shortest `Bytes(data)` for empty data or lengths ≥76. Other PUSHDATA forms reject. Constant opcodes push N values. A fixed-length push of sixteen bytes is allowed even if a constant opcode could produce the same stack item: different programs have different commitments; canonical parsing does not imply a unique program for each computation.

## Closed candidate allocation

All bytes not listed here reject; none is a future-success placeholder. Each listed byte has the semantics below or in the referenced packet. This table is an allocation proposal requiring byte-for-byte vectors before D07 closes. Historical Mitra/BIGINT assignments are not aliases.

| Hex | Instruction | Stack effect / meaning (rightmost is top) |
| --- | --- | --- |
| 00 | ZERO | push N(0) |
| 01–4b | PUSH_n | push next n bytes, 1≤n≤75 |
| 4c | PUSHDATA | push Bytes payload; only length 0 or ≥76 |
| 4f | NEGATIVE_ONE | push N(−1) |
| 51–60 | ONE through SIXTEEN | push corresponding N |
| 61 | NOP | no effect; permanently no effect |
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
| ac | CHECKSIG | signature public_key → Boolean, P01 transaction message |
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
| c0–de | Existing introspection/loop allocation | Explicit table below |
| e0–ec | Invocation/policy introspection | Explicit table below |

Existing template spellings may prefix `OP_`; that does not alter bytes. OP_MERKLEVERIFY is replaced by a specifically typed UTXOPROOFVERIFY name at bb: it verifies P02's map proof, not any arbitrarily named Merklix structure. A proof succeeds only if its reconstructed map root equals the 32-byte operand; malformed proof framing errors reject. A well-formed mismatching proof pushes false. The proof's presence flag is part of its bytes; a contract must inspect/require the intended presence and Coin content when relying on the claim. This opcode does not authenticate a map root to a block header by itself.

## Arithmetic edge semantics

PICK/ROLL require `0≤n<remaining_stack_size`; SPLIT requires `0≤i≤len(bytes)`. NUM2BIN width must be 0..MAX_ELEMENT_BYTES and x must fit its signed width; zero width accepts only zero. Larger widths sign-extend. BIN2NUM sign-extends to sixteen bytes and never silently truncates longer input. Decode an unsigned short byte string by appending a zero sign byte before BIN2NUM where needed; an unsigned 128-bit limb with its high bit set stays a U operand, not a positive N.

All signed arithmetic overflow rejects. DIV and MOD reject zero divisor and the minimum-int/−1 case. NEGATE/ABS of minimum-int reject. Carry input must be N(0) or N(1); borrow is one iff a<b+c. Wide operations use bounded 129/256-bit intermediates independent of host integer types.

RAWLEFTBITSHIFT interprets bytes as unsigned little-endian, retains the original byte length and discards shifted-out bits. Positive k shifts left; negative k shifts right; abs(k)≥8*length returns all-zero bytes of the same length. Handle minimum-int k by comparison, not an overflowing signed absolute operation. MULPOW2 uses signed mathematical a, preserves no discarded high bits on multiplication, and truncates division toward zero. For nonzero a, k≥128 rejects; a=0 returns zero. For k≤−128 the division result is zero. Intermediate host shifts by their type width are never the definition.

LOG returns the following fixed algorithm, **not a claim of exact real logarithm rounding**. Require x>0. Let e=floor(log2(x)) determined by bit length; z=x*2^(127−e). Initialize f=0. Repeat exactly 64 times: t=floor(z*z/2^127); bit=1 if t≥2^128, else 0; z=floor(t/2) if bit=1 else t; f=2*f+bit. Return N(e*2^64+f). Products fit unsigned 256 bits. SQRT is the largest nonnegative integer r with r*r≤x; implementations may use any equivalent bounded algorithm. Monetary consensus need not use these script opcodes to implement its own recurrence.

## Introspection and execution contexts

Indices/results are N values; hashes/outpoints/state/scripts remain bytes. Missing optional state reads as empty bytes; flags distinguish absent from present-empty. Token ID reads zero only for native coins. Every index and integer result must be representable and checked before access. All UTXO reads include reference coins, without changing their accounting treatment.

| Hex | Name | Effect |
| --- | --- | --- |
| c0 | INPUTINDEX | push current spending input index; mint context errors |
| c1 | ACTIVEBYTECODE | push exact active script bytes |
| c2 | TXVERSION | push transaction version |
| c3 | TXINPUTCOUNT | push input count |
| c4 | TXOUTPUTCOUNT | push output count |
| c5 | TXLOCKTIME | push u64 lock_value as N |
| c6 | UTXOVALUE | i → resolved coin value |
| c7 | UTXOBRANCH | i k → resolved branch[k] |
| c8 | OUTPOINTTXHASH | i → prev_txid |
| c9 | OUTPOINTINDEX | i → prev_index |
| ca | UTXOTOKENID | i → resolved asset ID |
| cb | UTXOSTATE | i → resolved state bytes |
| cc | OUTPUTVALUE | j → output value |
| cd | OUTPUTBRANCH | j k → output branch[k] |
| ce | OUTPUTTOKENID | j → output asset ID |
| cf | OUTPUTSTATE | j → output state bytes |
| d0 | TXID | push ChainID-bound core TxID |
| d1 | ENUMERATE_INPUTS | structured loop with fixed input_count bound |
| d2 | ENUMERATE_OUTPUTS | structured loop with fixed output_count bound |
| d3 | ISREFERENCEINPUT | i → Boolean reference flag |
| d4 | TXMINTCOUNT | push mint_count |
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
| e1 | INVOCATIONKIND | push 0 for spend, 1 for mint |
| e2 | MINTTOKENID | push active mint asset; spend context errors |
| e3 | MINTDELTA | push positive mint delta as N; see delta bound below |
| e4 | INPUTPATHINDEX | i → selected path; reference input errors |
| e5 | UTXOPATH | i p → canonical Vec(CS(branch_index)) bytes |
| e6 | OUTPUTPATH | j p → canonical Vec(CS(branch_index)) bytes |
| e7 | UTXOOUTPUT | i → complete serialized Output bytes |
| e8 | OUTPUTRECORD | j → complete serialized Output bytes |
| e9 | BLOCKHEIGHT | push candidate block's derived height |
| ea | BLOCKMEDIANTIME | push MTP(parent), as defined in P01 |
| eb | CHAINID | push the immutable 32-byte chain identifier |
| ec | SIGHASH | push P01's 32-byte FULL message for this invocation |

With u64 amounts and at most 2^32−1 outputs, positive token delta is below 2^96, so MINTDELTA fits N. Returned serialized outputs/paths and active bytecode must fit the element limit; using such an opcode on a larger object errors. This does not make the underlying output invalid by itself. Length-aware costs charge bounded serialization/copy work. There is no introspection of other invocations' successful execution, mutable VM state, signature arguments or WitnessID; P01's PlanHash binding is not such an opcode.

BLOCKHEIGHT/BLOCKMEDIANTIME permit upper-bound expiry checks as well as minimum locks. Absolute transaction locktime alone cannot enforce a certificate's expiration. Both opcodes work in spend and mint contexts; they expose parent-derived context available before current-block execution, not local clock time or the containing block's hash/timestamp. Transactions using them may cease to be valid as the candidate context advances; mempool admission and caches must revalidate accordingly. SIGHASH lets a P-256/Ed25519 policy bind its application signature or WebAuthn challenge to the same full intent as CHECKSIG without attempting to reconstruct hidden witness-plan fields in Script.

CHECKLOCKTIMEVERIFY accepts kind 1 or 2 and nonnegative bound: require tx.lock_kind=kind and tx.lock_value≥bound. CHECKSEQUENCEVERIFY accepts kind 1 (height) or 2 (512-second units), bound 0..65535; require current spend's enabled relative lock of that kind and encoded delay≥bound. Both consume their operands. Global P01 lock checks enforce the actual candidate context. Mint context may use the absolute check but not the input-relative check.

## Structured evaluation and BREAK

Grammar: a sequence consists of ordinary instructions, `IF sequence [ELSE sequence] ENDIF` (or NOTIF), and `ENUMERATE* sequence ENDENUMERATE`. Constructs must nest properly; crossing a loop delimiter with an unmatched conditional rejects at decode time. At most two nested loop nodes are permitted on any syntax path, including skipped arms. A separate fixed parameter bounds conditional/AST nesting.

A loop captures its bound once on entry. Each iteration pushes N(index), evaluates its body, then advances; the body may consume or leave that index like any stack value. Bound zero does not evaluate the body. IF consumes one canonical Boolean only when executed. Underflow/runtime operand errors in unexecuted code do not occur; its syntax/opcodes are nevertheless checked and charged conservatively.

Define evaluation results `Continue`, `ExitLoops(d)`, or `Error`. BREAK with `1≤d≤active_loop_depth` produces ExitLoops(d). Sequence/conditional nodes immediately propagate it. A loop receiving ExitLoops(1) terminates and returns Continue; receiving ExitLoops(d>1) terminates and returns ExitLoops(d−1). This specifies conditional-frame unwinding without byte-offset guesses. All existing stack effects persist. No BREAK signal may escape the top-level sequence.

## CHECKDATASIG profile proposal

Message operand is exactly 32 bytes for every profile. Stack signature, message, public_key, N(algorithm) are consumed. Unknown algorithm, wrong size, or malformed/noncanonical public key errors. Any correctly sized signature that fails the selected profile, including scalar/point canonicality, subgroup or verification checks, produces false. Application protocols must domain-separate their message construction.

- **0:** BIP340, 32-byte x-only secp256k1 key, 64-byte signature, direct verification over message bytes.
- **1:** ECDSA over P-256, SEC1 compressed 33-byte key, signature r||s as two unsigned big-endian 32-byte integers; 1≤r<n and 1≤s≤floor(n/2). The message is the already-computed 256-bit digest supplied to ECDSA, not hashed again. DER and high-S encodings are not accepted. P-256 point/domain parameters and ECDSA follow [SEC1](https://www.secg.org/sec1-v2.pdf) and [FIPS 186-5](https://csrc.nist.gov/pubs/fips/186-5/final).
- **2:** Strict prime-subgroup Ed25519 profile: canonical 32-byte public-key/encoded-R points, 64-byte R||S signature, S<L; A and R must be nonidentity points in the prime-order subgroup. Verify the uncofactored equation `[S]B=R+[h]A`, using the pure-Ed25519 SHA512 challenge over R||A||message and canonical encodings. This intentionally specifies a narrower acceptance profile than some Ed25519 libraries; do not substitute their default verifier. [RFC 8032](https://www.rfc-editor.org/rfc/rfc8032) supplies curve/encoding/hash definitions. The message is 32 application bytes, not Ed25519ph mode.

These profiles are proposals needing independent library/edge-vector review and costs; they are not an assertion that existing Lotus libraries accept exactly this set. Dedicated key types and explicit algorithm selection prevent a 64-byte signature from ambiguously selecting two algorithms. An on-device WebAuthn assertion additionally requires the application's challenge/origin/authenticator policy and cannot be reduced to the existence of P-256 verification.

## Cost proof obligations

Costs use decoded syntax and maximum permitted operands, never interpreter execution to estimate a bound. Account for pushes/copies, control frames, stack memory, proof hashing and each crypto profile. A bounded algorithm can still be too expensive; no numerical cost schedule is frozen here. Test skipped invalid opcodes, nested condition/loop exits, boundary arithmetic and both stack caps with the reference evaluator before adopting this allocation. Adding any unlisted opcode after genesis would change validity.
