# Lotus v2 consensus specification

Status: **review draft; not launchable**. Requirement IDs below identify proposed rules for conformance work. MUST denotes an obligation within this draft, not a claim that the existing daemon implements it. [Open decisions](decisions.md) and missing parameter values block genesis. Historical v1 consensus is outside this document.

## 1. Validity boundary

**C01 — Scalar semantics.** Define block validity by deterministic parsing, contextual checks, script evaluation, accounting and state transition. Caches, batch signatures, threads, databases, indexing, mempool policy and transport MUST preserve this result. Consensus limits cannot depend on machine speed, cache warmth or local configuration.

**C02 — Unknown data and extension points.** Every opcode byte not assigned an instruction by P03 is OP_SUCCESS_N, with N its unsigned decimal byte value. Encountering an unassigned success opcode during P03's instruction-boundary scan unconditionally succeeds for that invocation, including in skipped code; pushed data bytes do not count. This bypasses that invocation's VM execution, structured decoding and final-stack checks, not witness framing/limits, membership proofs, other required branches, accounting, locks or enclosing budgets. Unknown transaction/header versions, flags, lock kinds, signing modes and signature algorithms MUST reject; CHECKDATASIG defines only selectors 0..3. An assignment may only narrow transaction/block validity, including costs. No other field has success-on-unknown behavior, and no vote implicitly gives one. Network feature negotiation does not change block validity.

**C03 — State.** The validation state contains unspent coins with complete output bytes, creation height and coinbase status, plus any monetary or faucet state required by future blocks. The state commitment design MUST cover that state or define separately authenticated derivation. Header PoW is necessary but not sufficient for block validity.

## 2. Encoding contract (D01)

**C04 — Primitive proposal.** Fixed-width transaction integers use little-endian encoding. Hashes are 32 bytes in digest order; display reversal is not serialization. Byte order is little-endian by convention throughout: wherever consensus orders two hashes or byte strings (branch-tree nodes in P02, LESSSWAP in P03, proof of work in P04) it reads them as unsigned little-endian integers. An unsigned amount is `u64` in `[0, 2^64-1]`, subject to the final narrower asset/supply limits. Aggregate arithmetic uses checked unsigned 128-bit or equivalently bounded mathematical integers. Never reinterpret token units as signed native amounts.

`CS(n)` denotes shortest CompactSize: one byte for 0..252; `fd` plus u16 for 253..65535; `fe` plus u32 through 2^32−1; otherwise `ff` plus u64. Larger-than-needed encodings reject. `Bytes(x)=CS(len(x)) || x`; `Vec(xs)=CS(count(xs)) || encode(each item in order)`. Count and cumulative-byte limits MUST be checked before allocation, indexing, or multiplication. Truncation and trailing bytes reject. Actual limit values remain OPEN.

**C05 — Output proposal.** Serialize `flags:u8 || value:u64 || token_id? || branches || paths`:

- Bit 0 means HAS_TOKEN; every other bit rejects. There is no state field: bit 1, HAS_STATE in earlier drafts, is unassigned.
- Token ID is exactly 32 bytes iff HAS_TOKEN. It MUST be nonzero; native XPI has no token-ID field. Zero is reserved exclusively for native identity in introspection/accounting.
- Branches are `Vec(hash32)`; paths are `Vec(Vec(CS(branch_index)))`. C09 gives their invariants.
- There is no token-operation field. An object/API supplying a nonzero token operation without a token-bearing output is invalid input to the encoder, not a native transfer. Unexpected wire data rejects under the complete grammar.

A one-branch, one-path native output occupies 45 bytes under this proposal; the corresponding token output is 77 bytes. More branches, paths, or larger lengths add bytes. Neither size guarantees cache-line alignment.

**C06 — Transaction candidate.** [P01](decisions/encoding-and-signatures.md) owns the exact ordinary/coinbase grammar: version u32 (7), one u64 lock word packing lock_kind and a 56-bit lock_value, u16 input and output counts, then inputs and outputs, with nothing after the outputs. Its fixed prefix is 16 bytes. There are no read-only inputs: every input of an ordinary transaction either spends a coin or is a mint. Ordinary transactions require a consuming input but may have zero outputs. A coinbase is the transaction whose single input has flags `02` and carries the parent ID and height; it has no other inputs. Unknown version/flags reject. A mint is an input with flags `03` whose `prev_txid` holds the token ID and whose authorization is one branch witness revealing a mint script, its membership proof and arguments; mint inputs are unique per token and exactly cover positive deltas.

**C07 — Identities.** P01 defines the core projection exactly: `Core(tx)` retains the witnesses without their argument vectors (`Bytes(script) || Vec(h32 sibling)` for each spend or mint witness) and omits only `Vec(Bytes(arg))`. `TxID=H_txid(ChainID || Core(tx))`; `TxHash=H_txhash(ChainID || Tx(tx))`. The block commits to each transaction's TxHash and TxID, in order, using P02's count-bound ordered tree. Reject duplicate TxIDs within a block and any attempted overwrite of an existing outpoint. Signature mode FULL commits to the core (including all revealed scripts and membership proofs), resolved output policies and the active spend/mint selector under C18; P01's two partial modes commit to the signer's own core input, resolved output policy and either all outputs or the same-index output. Witness arguments remain outside TxID and the signature message but inside TxHash; no general claim of argument-byte immutability follows.

## 3. Application hash domains and branch commitments

**C08 — Hashes and trees.** [P02](decisions/commitments-and-state.md) owns the application domain registry and exact branch, ordered-transaction, sparse-UTXO and full-state-envelope algorithms. `H_name(x)=BLAKE3(ASCII(tag) || 00 || x)` with 32-byte output. Leaf/node type bytes are application-level inputs, independent of BLAKE3's internal flags. Header hash-group definitions and their additional domains are in [P04](decisions/header-and-mining.md). Do not reuse a branch-membership proof as an ordered-vector or keyed-map proof.

**C09 — Output authorization structure.** Both branch and path counts MUST be positive and within their final limits. Every path MUST contain at least one in-range index. Indices in a path are strictly increasing. Paths are strictly lexicographically increasing integer vectors, with a proper prefix ordered first. Duplicate paths reject. Branch order is committed as supplied, not sorted by a validator. Branch roots within one output MUST be pairwise distinct; an output that lists the same root twice rejects. Each root therefore has exactly one index in its output. Output well-formedness is checked on creation and on imported state, not deferred to its first spend.

**C10 — Positional witnesses.** A consuming input MUST have `0 <= path_index < path_count` before dereferencing it. Its witness count MUST equal the selected path length. Witness `j` proves and invokes branch `paths[path_index][j]`. No spare, missing or wildcard witnesses exist. Every required branch must succeed, and even an OP_SUCCESS_N invocation requires a valid membership proof.

**C11 — Branch inclusion.** Start with `r=Leaf(script)`; for each supplied sibling in bottom-up order set `r=Node(r,sibling)`; require `r == expected_branch_root`. Zero siblings is the one-leaf case using exactly the same leaf hash. Bound proof length and charge all supplied hashes. This is unordered membership: there is no leaf index, direction mask or claim about method position. A branch commits to an owner's binary tree, not a numbered method table. It does not prove leaf count or uniqueness of hidden leaves. Wallets may use a deterministic construction convention, but validators cannot enforce hidden-tree properties from one inclusion proof.

Adding a method generally changes the branch root and address. Domain separation does not preserve addresses across contract refactors. Distinct tags remove structural ambiguity in hash inputs under the hash security assumptions; they do not make hash collisions mathematically impossible.

Transaction order and state-key direction MUST NOT use this sorted-child operation. An ordered transaction vector and an authenticated key/value map have different proof obligations from branch membership.

## 4. UTXO resolution and conservation

**C12 — Resolution.** Evaluate transactions sequentially in their committed block order against an evolving UTXO view. Every input must resolve to a coin unspent immediately before that transaction. Reject repeated outpoints within a transaction. A later transaction may spend a coin created earlier in the block, provided maturity/context rules permit. Each transaction evaluates against an immutable resolved context; no mid-script state changes.

**C13 — No read-only inputs.** A transaction cannot read a coin without spending it. The input kinds are `01` spend, `02` coinbase and `03` mint, and every other flags value rejects; the read-only reference kind of earlier drafts is gone. Every coin a script can inspect is one the transaction consumes, so each such coin has been authorized by its own policy, and a coin's data cannot be used by a transaction its owner did not approve. Shared data that many transactions need is carried by spending the coin that holds it and recreating it in the same transaction. The coinbase maturity height check applies to spends; the maturity constant remains a parameter to freeze.

**C14 — Accounting.** Let `I_a` be the sum of consuming-input values for asset `a`, and `O_a` the sum of output values. Compute with checked arithmetic. For native XPI, ordinary transactions require `I_native >= O_native`; `F=I_native-O_native`. Tokens never pay native fees. For each token, if `O_a <= I_a`, the difference is a burn; if `O_a > I_a`, C15 must authorize precisely the positive delta. Spending still requires every branch under C10, regardless of whether accounting balances.

**C14a — Token output burn (candidate, pending D10).** Let `n` be the number of token-bearing outputs (HAS_TOKEN) that an ordinary transaction creates. Require `F >= 2 × DUST_LIMIT × n`. That amount is burned: it is part of `B` in C16 and is never collectable by a coinbase, so a miner cannot create token outputs for free. A token output holds no native value, so this is the only native cost of adding one to the coin set, and it does not depend on any judgment of what the token is worth. The rule deliberately charges every token output created, including transfers and change, not only minted ones. A matching consensus minimum value for native outputs remains to evaluate. DUST_LIMIT is a consensus **minimum**, frozen at genesis: it is the lowest value the network will ever accept and the only one a syncing node checks. A higher working value may be chosen later by a non-consensus process, such as a coin vote, and enforced as policy by online nodes, for example by Avalanche declining to finalize blocks that violate it. Such policy can only tighten this rule, never loosen it, so every block it accepts also satisfies consensus. Consensus burns only the minimum; a policy that wants the surplus burned must require the coinbase to leave it unclaimed (C16's underclaim).

**C15 — Minting proposal, pending D05.** Token ID is `mint_root`, a branch root (C11) over the token's mint scripts, used directly; zero is forbidden. Execute exactly one matching mint input (P01) for each positive delta in a dedicated mint context binding that asset and delta. No native mint input exists. Program-derived identity allows the same policy to authorize later mints; it is not intrinsically unique issuance. One-time policies require a uniquely consumed anchor. Supply caps, revocation and circulating-supply claims need explicit authenticated state or conserved authority, not an assumption that an off-chain certificate disappears when replaced.

**C16 — Native issuance.** Coinbase is the only native issuance exception. Let subsidy entitlement be `R`, total native fees `F` of the block's ordinary transactions, mandatory fee burn `B`, actual coinbase output sum `C`, and underclaim `U=R+F-B-C >=0`, adjusted for any mandatory allocation rule. With no double-counted application burn, net native supply change is `C-F=R-B-U`. Half of the fees are burned, as in Lotus v1. Let `T` be the block's total token output burn under C14a and `G=F-T` the remaining fees. Then `B = T + (G - floor(G/2))`: the token burn is burned whole, and of the rest the coinbase may collect at most `floor(G/2)`, the odd unit being burned. The split is computed once per block on the totals, not per transaction. Exact faucet allocation, cap burn, subsidy rounding, entitlement, and application-burn representation remain OPEN under D10–D11.

**C17 — Atomicity.** Validate all required branches, mints, conservation and contextual rules before committing a transaction. Validate block roots and total budgets before committing a block. Failure leaves no consensus state changes. Disconnect MUST restore coins and all monetary/faucet metadata exactly. State import MUST reproduce the same rules and root; a matching root is not evidence that unverified history was executed.

## 5. VM, signatures and optimization

**C18 — Invocation.** Every execution has an immutable context: core transaction, complete witnesses if introspection exposes them, resolved coin records in input order, chain domain, invocation kind (spend/mint), the index of the input the script is running for, its path and branch indices in a spend or its token ID and delta in a mint, active leaf bytes/hash, and arguments. No block-context field is available to opcodes (C22a). Undefined context reads reject. A mint script runs for its own mint input: INPUTINDEX returns that input's index and CHECKSIG uses the mint selector, never a spending input's context.

[P01](decisions/encoding-and-signatures.md) defines the exact FULL message: ChainID, mode, TxID, CoinsHash and a typed spend/mint selector, and two spend-only partial-mode messages selected by a 65-byte signature. Resolved output policies and all selected scripts and membership proofs are committed through `Core(tx)` and `Coins`; confirmation metadata, current block hash/time and witness argument bytes (including signatures) are excluded. Contextual locks/maturity still validate separately. BIP340 verification uses that message without replacing its internal hash algorithm.

**C19 — Scalar execution.** Apply P03's success scan after the outer witness/proof checks. If it returns unconditional success, no VM stack is initialized or executed. Otherwise arguments initialize a fresh stack in wire order, last argument at top. In a mint invocation the node then pushes the positive delta (P03); it is a validator-supplied value, not witness data. The token ID is read with BRANCHROOT. The alternate stack starts empty. Branch invocations share no mutable VM state. The proposal uses byte strings with explicit exact-width signed int128 numerical operands and canonical booleans, as detailed in the ABI. Ordinary executions finish with exactly one true value and empty alternate stack. Arithmetic overflow, invalid operand encoding, invalid index and stack underflow reject. [P03](decisions/vm-semantics.md) supplies assigned instructions, generic success bytes, control/arithmetic semantics and explicitly selected crypto profiles. Independent vectors, review and costs remain required before D07 closes.

**C20 — Cache equivalence.** Reference validation executes each invocation. An implementation may reuse a result only when all observable context and invocation inputs are equivalent and all proof/well-formedness checks still occur. At minimum include actual leaf identity, canonical argument vector, invocation context, resolved coins, rule set and all observable transaction/block data. Hashing concatenated arguments without lengths is not a unique vector encoding. Root alone does not identify an executed MAST leaf, and TxID omits witness arguments. Include unambiguous invocation-kind tags rather than overloading input index zero as a “pure” sentinel.

The absence of OP_INPUTINDEX is not a purity proof: CHECKSIG, relative locks, implicit spent-coin fields, active script, mint context and future introspection may depend on the invocation. Conservatively disable cross-input result caching until a closed opcode dependency analysis proves equivalence. Cache identity and invalidation are daemon details, not a new consensus hash formula. Static charges never shrink on hits.

**C21 — Covenant aggregation.** A companion must not treat another coin's branch commitment as proof that its invariant ran. A permitted optimization must establish a consuming designated master, its selected path and executed leaf, noncircular obligation to perform the invariant, and coverage of every companion and relevant output. With the currently proposed introspection surface, that proof is not specified; the Master/Companion shortcut is excluded from reference examples. Repeated independent checks remain valid. An output's covenant is preserved only if its spending program enforces the required successor policy; conservation alone does not preserve governance.

## 6. Structured control flow and resources

**C22 — Loops.** Only structurally matched enumeration loops are allowed, at lexical nesting depth at most two. All combinations, including inputs × outputs, are allowed. Input/output bounds are validated transaction counts; generic bounds are runtime integers 0..256. Each iteration pushes a fresh index from zero upward. Zero iterations execute no body. Code without an unassigned success opcode is decoded once, including skipped regions; pushed data is not decoded as instructions. No dynamic jumps, recursion, or script-generated executable code exists.

`depth OP_BREAK` requires an integer in `[1, active_loop_depth]`. It exits the named enclosing loop and any inner loops, landing after its matching end; it does not roll back stack effects. Conditional/loop frames crossed by the jump must unwind consistently. P03 defines structured ExitLoops propagation, canonical Boolean conditions and decoding of unexecuted regions; those semantics must not be replaced by assumptions about C++ pointer arithmetic.

**C22a — Monotone validity.** Once a transaction is valid against a chain tip, it remains valid on every extension of that chain until one of its inputs is spent by another transaction. Minimum locks, relative locks and coinbase maturity only ever become satisfied. No script operation reads block height, block time, block hashes or any other state that advances with the chain. A reorganization that removes an input's creating block is the only other cause of invalidation. A node therefore never re-executes scripts for mempool transactions when a block arrives; it only removes those whose inputs the block consumed. The assignment of an extension point (C02) is the one event that requires a re-check. A design that would relax this rule is recorded in §9; it is not adopted.

**C23 — Static bound.** Invocations accepted by the success scan pay P03's structural scan/byte charge and all outer charges; they have no AST execution charge. For other invocations, compute a conservative deterministic upper bound from decoded syntax before execution. Sequence costs add. A conditional includes its condition/control cost and the maximum of both arms. A loop with bound `b` costs setup plus `b × (iteration_control + body_bound)`; generic loops use 256 even when runtime N is smaller. Input/output loops use I/O. Early termination, false predicates and BREAK do not lower the charge. Use checked arithmetic; overflow or excess budget rejects. The pass traverses syntax, not expanded iterations. Size-dependent charges use the per-operand bounds of P05's size pass, which tracks an upper bound on each stack item's size through the same traversal and falls back to MAX_ELEMENT_BYTES (working value 8192) wherever the stack's shape is not determined by the syntax. That pass selects charges only; it rejects nothing.

**C24 — Aggregation.** Charge parsing, all proof verification, accounting, state operations and every branch/mint invocation. Sum at transaction and block scope. An I×O scan repeated by I spending invocations has I²O body work; depth two alone does not make it cheap. Fixed per-input limits cannot substitute for transaction/block limits. Charges are independent of caches, batch verification and execution ordering.

**C25 — Bounded primitives.** Every operation requires a conservative charge covering maximum permitted operand size, signature/curve work, hashing, copies, concatenation and memory use. Independent limits bound total bytes, counts, proof depth, syntax depth, operand bytes, stack/altstack entries and total VM bytes. Define budget units as abstract integers, never CPU cycles. A structural O(script_bytes) cost pass is defensible only with bounded operands and a complete schedule. For each accepted execution, prove actual charged work ≤ static bound. Increasing allowed bounds must not decrease estimates. Local admission/rate limits protect repeated invalid submissions but cannot change block validity.

## 7. Blocks, time and genesis blockers

**C26 — Block transition.** [P04](decisions/header-and-mining.md) proposes a 134-byte recursive header and exact block framing, size/height checks and PoW digest. The validation order must cover parsing, parent/context, target/PoW, complete transaction/root checks, first-and-only coinbase, ordinary transitions in order, total cost and the post-state envelope. Commit only after all checks pass. P01's parent/height-derived coinbase identity and P02's dependency order avoid embedding the containing block hash in its own coin records. The specified ASERT candidate still needs independent vectors/acceptance; monetary/future-time details remain blockers, not inherited defaults.

**C27 — Time and issuance.** Lotus v1 already uses a six-byte unsigned timestamp. The older v2 draft regressed to 32 bits; P04 retains the 48-bit timestamp in a new-header design. Width does not determine truthful timestamps. P01 fixes proposed absolute/relative lock clocks and boundaries; P06 separates bootstrap clock choices and a precisely rounded tail candidate from economic incentive claims. Target/ASERT anchors, future-time eligibility and all monetary initialization must be frozen before launch. No timestamp-honesty theorem is adopted here.

**C28 — Freeze.** Before genesis, fill every parameter and algorithm below, generate reference vectors, and obtain independent conformance/review evidence. Unknown values are blockers, not implementation defaults.

| Required parameter or algorithm family | Status |
| --- | --- |
| Versions/byte grammar/ranges; count and size limits | P01 candidate; mainnet limits and vectors pending |
| Opcode map, conversions, arithmetic, shifts, fixed-point math, crypto profiles | P03 candidate; independent vectors/review/costs pending |
| Signature domain and sighash preimage | P01 exact candidate; independent vectors/acceptance pending |
| Ordered transaction tree, state map, hash domains | P02/P04 candidates; vectors/acceptance pending |
| Header/PoW/compact target and ASERT | P04 candidate; width/hash selection, ASERT vectors and future-time rule pending |
| Cost budgets, primitive schedule and memory limits | P05 cost algebra; numerical calibration OPEN |
| Locktime/sequence and coinbase | P01 candidate; maturity value and reward rules pending |
| Issuance, fee burn, faucet, authenticated monetary state | P06 alternatives/exact tail candidate; product/economic decisions OPEN |
| Genesis allocations, empty state, chain identity and launch manifest | OPEN |

A complete genesis package must contain no OPEN rows and no dependence on unspecified behavior inherited from Bitcoin ABC.

## 8. Relay and mempool (not consensus)

Mechanics not described here are inherited from the Bitcoin ABC base: peer-to-peer framing, block and transaction propagation, orphan handling, reorganization, RPC and Avalanche. Five areas differ because the transaction model differs.

- **No standardness templates.** There is no separate list of standard script forms. Consensus already rejects noncanonical encodings, unknown versions, flags, lock kinds and signing modes, duplicate branch roots and trailing bytes; ordinary VM executions also require clean final stacks, so a node relays every transaction that is consensus-valid against its tip and mempool, subject only to the extension-point rule below, the fee floor and policy values that tighten consensus parameters (C14a).
- **Unassigned extension points are not relayed or mined.** A transaction is refused if P03's instruction-boundary scan finds an unassigned OP_SUCCESS_N in any revealed script, including skipped arms. Push payload bytes do not count. Unknown CHECKDATASIG selectors reject in consensus rather than acting as extension points. Blocks containing otherwise valid transactions that reveal an unassigned OP_SUCCESS_N remain consensus-valid.
- **Fee floor by cost.** The minimum relay fee is priced on P05's static cost units and bytes, not bytes alone. Its value is a node setting.
- **Accept by TxID, reject by TxHash.** Witness arguments are outside TxID, so one TxID can circulate with different TxHashes, and anyone can produce an invalid variant of a valid transaction by altering its witness arguments. The mempool holds at most one transaction per TxID and treats a second TxHash for a held TxID as a duplicate, not a conflict. A rejection is remembered by TxHash only, never by TxID, so an invalid variant cannot block the valid one that follows; the exception is a failure that does not depend on the witness arguments, such as a missing input, a value imbalance or an invalid branch proof, which may be remembered by TxID. Announcements and requests between peers identify transactions by TxHash.
- **No revalidation on new blocks.** By C22a, a block removes only the mempool transactions whose inputs it consumed.

## 9. Under consideration: block-dependent transactions (speculative, not adopted)

Nothing in this section is in force. C22a and §8 stand as written, and no opcode in P03 reads block data. This section records a design being weighed so that its costs can be compared with other ways of solving the same problems.

**What it would allow.** Three things that monotone validity (C22a) rules out:

- A signature, offer, certificate or quote that stops working after a time. Today the only way to withdraw one is to spend a coin it is tied to.
- Randomness taken from a block hash.
- A transaction bound to one chain history.

**Readable values.** A script could read values from the parent of the block that includes the transaction: its hash, its height and its MTP-11. Other header fields, or the whole parent header, are candidates. Every value comes from the parent, so block validation stays deterministic and transactions in a block can still be checked in any order. The parent's own time is a poor candidate on its own: it can move backwards from one block to the next, so a comparison against it can turn true, false and true again, where MTP-11 only moves forward.

**Flag.** A transaction is block-dependent if any script it executes reads one of these values. The node learns this during validation; nothing in the encoding declares it. An unconfirmed transaction that spends an output of a block-dependent transaction inherits the flag.

**Mempool handling.** This is relay behaviour, not consensus.

- A block-dependent transaction is evaluated against the current tip as its parent.
- When a block arrives or the chain reorganizes, every block-dependent transaction and its unconfirmed descendants move to a pending pool and are revalidated against the new tip before they are admitted again.
- One that fails against the node's tip is rejected without a ban score. The sender may be one block ahead or behind, as with a transaction whose lock is not yet satisfied.
- The signing message does not include block data, so cached signature checks remain valid across revalidation. A CHECKDATASIG over data derived from a block value is checked again. Any cache of whole-script results, and the reject-by-TxHash memory of §8, is keyed by tip for these transactions or not used.
- A node may keep a reduced form of each script to make revalidation cheap. During the P05 charging pass it marks block values and everything computed from them, runs the rest once and stores the results, and keeps only the marked part to run again. For a script that compares MTP-11 with a deadline, the part kept is that comparison. A script written so that a block value feeds everything keeps its whole body.
- The pending pool is capped by the total cost of the parts that must be run again, so the work a new block triggers is bounded.
- A block template is checked by full execution before mining, so a fault in the reduced form cannot put an invalid transaction in a block.

**Consequences.**

- A reorganization can invalidate a confirmed transaction with no one double-spending, and everything built on its outputs goes with it. The exposure depends on the condition: "MTP-11 is at or after T" only ever becomes true and is safe; "MTP-11 is before T" fails if the new chain includes the transaction after T; a condition on the parent hash fails on any reorganization at that depth.
- Nodes spend validation work on transactions that expire unmined. This already happens when a transaction is relayed and later evicted; what is added is the repeated work per block, which the cap bounds.
- Randomness from the parent hash is usable only when the block is fixed in advance. A script that reads whichever parent it happens to get lets the spender see the outcome and wait for a better block. A contract therefore commits first and requires settlement at one exact height, which needs the parent height to be readable. A miner who would lose can still discard a block at the cost of its reward, so the stake must stay well below the reward, and the contract needs a path for a settlement that misses its block. All transactions in a block read the same value; a contract that needs a value per coin hashes it with its own outpoint.
- If the parent's state commitment were readable, a script would have a trustworthy root to check a UTXO proof against, which UTXOPROOFVERIFY lacks today.

**Open questions.**

- Whether the cost of revalidation is worth it, compared with other ways of making a signature stop working after a time.
- Which header fields to expose, and whether to expose the whole header.
- Whether outputs of a block-dependent transaction need any protection against the reorganization case above.
