# Encoding, transaction identity and signatures

Decision packet P01, October 9, 2026. **Recommended candidate**, not frozen or implemented. Refines D01/D03/D04/D06 and the serialization portions of D12–D14. This packet owns the detailed candidate grammar; the consensus overview links here. Production parameter values and independent vectors remain prerequisites for acceptance.

## Choice and tradeoffs

Use a single canonical byte grammar with fixed-width outer counts, shortest CompactSize for nested collections, explicit transaction kind and lock clock, and separate core/witness identities. Sign every input/output policy and every selected leaf with a single full-transaction signature mode. Exclude mutable confirmation metadata from signatures so a benign reorg need not require resigning; contextual validity still checks that metadata.

Use a 32-byte ChainID chosen independently before genesis construction. It is an immutable network parameter, not the genesis hash and not a hash of a manifest containing itself. A published release manifest later binds ChainID, final parameters and the mined genesis. Different production/test networks must select different IDs. This breaks the would-be genesis/signature/UTXO-root circular dependency.

This recommends an explicit-format change from the earlier 16-byte transaction header. Do not implement both encodings under the same version. CompactSize remains useful for bounded nested lengths; fixed-width wire fields alone do not provide zero-copy access to aligned host structs.

## Primitive encoding

`u8/u16/u32/u64/u128` are unsigned fixed-width little-endian integers. `i128` is exactly 16-byte two's-complement little-endian. `h32` is 32 raw digest bytes, displayed in the same order. Concatenation has no padding. `CS`, `Bytes` and `Vec` are as in C04; each grammar use below fixes the element type. Shortest lengths are mandatory. Reject trailing bytes within the enclosing transaction frame.

For every size/count, first check the declared count against its semantic cap, the remaining frame bytes against a conservative minimum, and all additions/multiplications against overflow. An announced large count does not authorize allocation. Amounts are `u64`; aggregate per-asset amounts and positive mint deltas are `u128`, with checked operations. Output count is at most 2^32−1 and indexing is zero-based. Lower production limits are D08 parameters.

## Complete transaction grammar

```text
Tx = version:u32(2) || kind:u8 || lock_kind:u8 || lock_value:u64
     || input_count:u32 || output_count:u32
     || kind_payload || Input[input_count] || Output[output_count]
     || mint_count:u32 || Mint[mint_count]

kind = 00 ordinary | 01 coinbase
kind_payload(ordinary) = empty
kind_payload(coinbase) = height:u64 || parent_id:h32 || Bytes(extra_nonce)

Input = prev_txid:h32 || prev_index:u32 || sequence:u32 || flags:u8
        || authorization(flags)
authorization(00) = CS(path_index) || Vec(BranchWitness)
authorization(01) = empty
BranchWitness = Bytes(script) || Vec(h32 sibling) || Vec(Bytes(arg))

Output = flags:u8 || value:u64 || token_id? || state?
         || Vec(h32 branch_root) || Vec(Vec(CS(branch_index)))
Mint = token_id:h32 || Bytes(script) || Vec(Bytes(arg))
```

The fixed transaction prefix is **22 bytes** (4+1+1+8+4+4); mint_count adds four bytes after the outputs. Output grammar/flags are C05. Unknown version/kind/flags reject. No token-operation byte, scriptSig, annex, hidden per-input signature-mode byte, or optional trailing section exists.

Ordinary transactions require at least one consuming input. Zero outputs are permitted: a native imbalance becomes fees and a token imbalance becomes a token burn under accounting rules. Every serialized output, even a zero-valued one, must have a valid nonempty authorization policy. Zero amounts do not bypass resource charges. Inputs may not repeat an outpoint. Reference inputs carry sequence `ffffffff` and no authorization bytes.

Coinbase requires zero inputs, zero mints, at least one output, lock_kind/value zero, and only native outputs. It is first and unique in a block. Height is the derived block height; parent_id is the parent BlockID, or zero at genesis. Extra nonce is bounded by a parameter. Genesis allocations and reward entitlement remain D10–D14 choices. The coinbase contains no current-block ID or current-state root. Coinbase core thus depends only on already available parent/height/template data. Coinbase output identity is unique across heights without introducing a post-state-root cycle.

All mint IDs are nonzero, strictly lexicographically ascending, and exactly cover positive token deltas. The script must satisfy C15's proposed program-derived identity. No unused mint entry is accepted. Branch order stays committed as supplied; paths are nonempty and lexicographically ordered, with strictly increasing indices. Duplicate branch roots remain allowed and do not imply distinct signers.

## Absolute and relative locks

All comparisons use the candidate block's derived height and its parent's median time, not local wall time. Define `MTP(parent)` as the sorted median of up to the last eleven available ancestor timestamps including the parent; with an even initial sample size use element `floor(n/2)` in zero-based sorted order. Genesis's pre-parent MTP is zero. Values are unsigned seconds since Unix epoch; differences/additions use checked wide intermediates.

| lock_kind | Rule |
| --- | --- |
| 00 | Disabled; lock_value MUST be zero |
| 01 | Candidate block height ≥ lock_value |
| 02 | MTP(parent) ≥ lock_value |

No sequence value disables an absolute lock. Equality is valid, intentionally specified rather than inherited from Bitcoin's locktime rules. The u64 lock field avoids a 32-bit seconds horizon. Transactions that fail a contextual lock are not permanently invalid for every later block.

For consuming inputs, `sequence=ffffffff` disables relative locking. Otherwise only bits 0..15 and bit 22 may be set; any other set bit rejects. Let `d = sequence & 65535`:

- Bit 22 clear: candidate height ≥ coin.creation_height + d.
- Bit 22 set: MTP(parent) ≥ coin.creation_parent_mtp + 512*d.

`creation_parent_mtp` is the parent's MTP at the block that created the coin, stored in its authenticated coin record. Coinbase creation uses the same metadata. Maturity is a separate height check. Same-block ordinary outputs have creation_height equal to the candidate height and creation_parent_mtp equal to current parent MTP, so only zero relative delay can pass. Overflow rejects rather than wraps. Relative-lock encoding is independent of local replacement policy.

Recommend that coinbase maturity apply to both consumption and references: `height >= creation_height + COINBASE_MATURITY`. Ordinary coins have no maturity delay. This avoids immediate dependence on newly issued, immature state while leaving same-block references to ordinary outputs available. The maturity value is at least one and remains uncalibrated. A reference never receives spendable-value credit.

## Core and complete identities

`Core(tx)` uses the exact Tx grammar with each consuming input's `Vec(BranchWitness)` omitted entirely (including its count), retaining path_index. Each Mint is replaced by its token_id; mint_count remains. Coinbase has no witnesses, but the identity domains still differ.

```text
TxID      = H_txid(ChainID || Core(tx))
WitnessID = H_witnessid(ChainID || Tx(tx))
```

`H_name` domains are defined in the commitment packet. The block transaction root commits to WitnessIDs in order. Duplicate TxIDs within a block reject regardless of witness differences. Inserting any output whose outpoint already exists in the current state rejects; never overwrite a coin. Coinbase height/parent identity and unique consumption provide the induction base for outpoint uniqueness. Replaying a transaction on a competing fork can be valid if the same inputs exist there; ChainID separates networks, not every future fork of one network.

## Authorization plan and resolved outputs

Signers should authorize the method choices, not just the resulting outputs. Define:

```text
AuthPlan = input_count:u32 || InputPlan[input_count]
           || mint_count:u32 || MintPlan[mint_count]
InputPlan(reference) = 01
InputPlan(spend) = 00 || CS(selected_path_index)
                   || Vec(CS(branch_index) || Leaf(script))
MintPlan = token_id:h32 || Leaf(mint_script)

Coins = input_count:u32 || Bytes(Output(resolved_coin))[input_count]
PlanHash  = H_authplan(AuthPlan)
CoinsHash = H_spentoutputs(Coins)
```

InputPlan branches occur in selected path order, exactly one per required branch. Scripts and their proofs are checked against the resolved coin's roots before treating this plan as authorized. A leaf in the plan is a commitment to the actual script, not a branch root or witness position. Mint leaves use the same bytecode leaf function but are distinguished by their MintPlan and invocation tag.

Coins includes complete outputs for consuming and reference inputs in wire order; outpoints, flags and sequences are already in Core. It excludes confirmation height, creation MTP and coinbase status. Those fields remain authenticated contextual inputs for locks/maturity; they do not affect the signing digest. Moving the same ordinary coin to a different block can change contextual validity without changing the signature's intent.

AuthPlan excludes membership proofs and argument vectors. Those remain committed by WitnessID and are validated at execution. This avoids signature self-reference and allows independent signature production. A method that needs authenticated application arguments must explicitly verify them or bind their effect to committed transaction fields. There is no general claim that all witness bytes are signer-immutable. There is no WitnessID introspection opcode in this proposal.

## Exact CHECKSIG message

Only sighash mode `00` (FULL) is proposed here. Mode is part of the message, not appended to the 64-byte signature. There is no ANYONECANPAY, NONE, SINGLE, CODESEPARATOR, signature deletion, or legacy fallback.

```text
SpendSelector = 00 || input_index:u32 || CS(path_index)
                || CS(branch_index) || expected_branch_root:h32 || Leaf(script)
MintSelector  = 01 || mint_index:u32 || token_id:h32
                || positive_delta:u128 || Leaf(mint_script)

SigMessage = H_sighash(ChainID || 00 || TxID || CoinsHash || PlanHash || Selector)
```

CHECKSIG verifies the stack signature against **these 32 message bytes**, using the BIP340 algorithm unmodified (including its SHA256-based challenge calculation). Do not substitute BLAKE3 inside BIP340 because Lotus uses BLAKE3 for its message construction. No current block hash/height/time, coin confirmation metadata, signatures or WitnessID enters this preimage. Reorganizations still require rechecking contextual validity and caches.

CHECKSIG stack order is `[..., signature, public_key]`; it consumes both and pushes canonical int128 Boolean. Public key is exactly 32-byte BIP340 x-only encoding; signature is exactly 64 bytes. Wrong length or invalid key encoding is a script error; a correctly sized but invalid signature pushes false. CHECKSIGVERIFY consumes the Boolean and rejects false. No empty-signature special case. Wallets must not reuse signing nonces across messages or signature algorithms. [BIP340](https://github.com/bitcoin/bips/blob/master/bip-0340.mediawiki) defines the signature algorithm; this packet defines Lotus's message.

## Acceptance evidence still required

Generate exact primitive, ordinary/coinbase, core/full, Coins/AuthPlan/selector and signing vectors in the independent reference tool; compare a second implementation. Test confirmation-metadata changes separately from output/method changes. Account for the per-transaction construction cost of CoinsHash and PlanHash and per-invocation signature charges. Freeze ChainID, versions and limits in the parameter manifest. This packet resolves proposed byte meaning; it does not supply mainnet constants, signed fixtures or approval to drop other sighash use cases without review.
