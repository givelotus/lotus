# Encoding, transaction identity and signatures

Decision packet P01, October 9, 2026. **Recommended candidate**, not frozen or implemented. Refines D01/D03/D04 and the serialization portions of D12–D14. This packet owns the detailed candidate grammar; the consensus overview links here. Production parameter values and independent vectors remain prerequisites for acceptance.

## Choice and tradeoffs

Use a single canonical byte grammar with fixed-width outer counts, shortest CompactSize for nested collections, one input layout whose flags select spend, mint or coinbase, an explicit lock clock, and separate core/witness identities. By default sign every input/output policy and every selected leaf in one full-transaction mode; two explicit partial modes let a signer commit to only their own input plus all outputs or one paired output. Exclude mutable confirmation metadata from signatures so a benign reorg need not require resigning; contextual validity still checks that metadata.

Use a 32-byte ChainID chosen independently before genesis construction. It is an immutable network parameter, not the genesis hash and not a hash of a manifest containing itself. A published release manifest later binds ChainID, final parameters and the mined genesis. Different production/test networks must select different IDs. This breaks the would-be genesis/signature/UTXO-root circular dependency.

This keeps a 16-byte transaction prefix but changes its fields from the earlier design. Do not implement both encodings under the same version. CompactSize remains useful for bounded nested lengths; fixed-width wire fields alone do not provide zero-copy access to aligned host structs.

## Primitive encoding

`u8/u16/u32/u64/u128` are unsigned fixed-width little-endian integers. `i128` is exactly 16-byte two's-complement little-endian. `h32` is 32 raw digest bytes, displayed in the same order. Concatenation has no padding. `CS`, `Bytes` and `Vec` are as in C04; each grammar use below fixes the element type. Shortest lengths are mandatory. Reject trailing bytes within the enclosing transaction frame.

For every size/count, first check the declared count against its semantic cap, the remaining frame bytes against a conservative minimum, and all additions/multiplications against overflow. An announced large count does not authorize allocation. Amounts are `u64`; aggregate per-asset amounts and positive mint deltas are `u128`, with checked operations. Input and output counts are each at most 65,535 and indexing is zero-based. Lower production limits are D08 parameters.

## Complete transaction grammar

```text
Tx = version:u32(7) || lock:u64
     || input_count:u16 || output_count:u16
     || Input[input_count] || Output[output_count]

lock       = one little-endian u64 packing two fields
lock_kind  = lock & 0xff              (bits 0..7)
lock_value = lock >> 8                (bits 8..63, 56 bits)

Input = prev_txid:h32 || prev_index:u32 || sequence:u32 || flags:u8
        || authorization(flags)
authorization(01 spend)    = CS(path_index) || Vec(BranchWitness)
authorization(02 coinbase) = empty
authorization(03 mint)     = BranchWitness
BranchWitness = Bytes(script) || Vec(h32 sibling) || Vec(Bytes(arg))

Output = flags:u8 || value:u64 || token_id?
         || Vec(h32 branch_root) || Vec(Vec(CS(branch_index)))
```

An output has no state field. Flags bit 1, which earlier drafts used for HAS_STATE, is unassigned and rejects. A contract that keeps data between spends commits to it inside its own branch tree, using the data-leaf convention in P02; consensus sees only the branch root.

The fixed transaction prefix is **16 bytes** (4+8+2+2); nothing follows the outputs. On the wire the first lock byte is lock_kind and the next seven bytes are lock_value, little-endian. Lock_kind values 3..255 are unassigned and reject; they are not an extension mechanism. There is no transaction-kind field: a coinbase is recognized by its input. Version is 7, chosen so that no parser for Bitcoin-family or Lotus v1 transactions (versions 1 and 2) mistakes a v2 transaction for one of its own; any other version rejects. Input and output counts are at most 65,535 by construction; a larger payment set is expressed as chained transactions. Lower production limits remain D08 parameters. Output grammar/flags are C05. Unknown version/flags reject. No token-operation byte, scriptSig, annex, hidden per-input signature-mode byte, separate mint section, or optional trailing section exists.

An ordinary transaction is one with no coinbase input. Ordinary transactions require at least one consuming input. Zero outputs are permitted: a native imbalance becomes fees and a token imbalance becomes a token burn under accounting rules. Every serialized output, even a zero-valued one, must have a valid nonempty authorization policy. Zero amounts do not bypass resource charges. Inputs may not repeat a `(prev_txid, prev_index)` pair, whatever their flags. Input flags are `01` spend, `02` coinbase and `03` mint; `00` and every other value reject. The same numbering, 1 spend, 2 coinbase, 3 mint, is used wherever the kind of an input or invocation is tagged: in AuthPlan, in the signing selectors and by P03's INVOCATIONKIND. Earlier drafts had a read-only reference input kind, which has been removed (C13).

A coinbase is a transaction whose only input has flags `02`. That input carries `prev_txid` = the parent BlockID (zero at genesis), `prev_index` = the derived block height as u32, `sequence` = `ffffffff`, and no authorization bytes. It resolves no coin. A coinbase therefore has exactly one input and no spends or mints; it requires at least one output, lock zero, and only native outputs. The first transaction of a block MUST be a coinbase and no later transaction may contain a flags-`02` input. The u32 height field bounds chain height at 2^32−1. Parent ID and height in the input make every coinbase TxID unique without a separate payload or transaction-kind field. There is no extra-nonce field: P04's 64-bit header nonce supplies the search space per template, and a pool gives each worker its own template by placing a 32-byte tag in a coinbase output as an extra branch root that no path uses. Genesis allocations and reward entitlement remain D10–D14 choices. The coinbase contains no current-block ID or current-state root. Coinbase core thus depends only on already available parent/height/template data. Coinbase output identity is unique across heights without introducing a post-state-root cycle.

A mint is an input with flags `03`. It resolves no coin and is not a consuming input. Its authorization is one BranchWitness. Compute `mint_root` from `Leaf(script)` and the supplied siblings exactly as C11 computes a branch root; the `prev_txid` field holds the token ID, which MUST be nonzero and equal `mint_root` itself (C15's proposed program-derived identity). The root is already a domain-tagged BLAKE3 commitment, so it is not hashed again. `prev_index` MUST be zero and `sequence` MUST be `ffffffff`. A token's mint policy is thus a script tree like any branch: several mint methods may be committed and only the one used is revealed; a single-script policy is the zero-sibling case. The token ID sits in the core while the script, proof and arguments are witness data, as with a branch root and its revealed leaf. A token ID and a branch root are the same kind of value. The consequence is that every script tree names a token whose ID is its root. Leaves are not typed, so a contract keeps its mint scripts and its spend scripts in separate trees (P02): the token ID is the root of the mint scripts alone, and they name the root of any rules tree that outputs must carry. The spend/mint tag in the signature selector keeps a signature for one use from authorizing the other. No separate mint count or mint section exists: `input_count` counts mint inputs, and a transaction that mints nothing carries no mint bytes.

Mint inputs may appear at any input position and are committed in wire order. The no-repeat rule above permits at most one mint input per token ID. Mint inputs MUST exactly cover positive token deltas: one for every token whose output sum exceeds its consuming-input sum, and none for any other token. A mint input contributes no amount of its own; the positive delta is computed by accounting and bound into its invocation. Several mint inputs in one transaction mint several tokens. A real outpoint and a mint pseudo-outpoint use different hash domains (`H_txid`, `H_branch`) and different flags.

Branch order stays committed as supplied; paths are nonempty and lexicographically ordered, with strictly increasing indices. Branch roots within one output must be pairwise distinct; a repeated root rejects. A repeated root added no authorization, and uniqueness gives each root a single index, which the branch-requirement opcodes in P03 rely on.

## Absolute and relative locks

All comparisons use the candidate block's derived height and its parent's median time, not local wall time. Define `MTP(parent)` as the sorted median of up to the last eleven available ancestor timestamps including the parent; with an even initial sample size use element `floor(n/2)` in zero-based sorted order. Genesis's pre-parent MTP is zero. Values are unsigned seconds since Unix epoch; differences/additions use checked wide intermediates.

| lock_kind | Rule |
| --- | --- |
| 00 | Disabled; lock_value MUST be zero |
| 01 | Candidate block height ≥ lock_value |
| 02 | MTP(parent) ≥ lock_value |

No sequence value disables an absolute lock. Equality is valid, intentionally specified rather than inherited from Bitcoin's locktime rules. The 56-bit lock field avoids a 32-bit seconds horizon. Transactions that fail a contextual lock are not permanently invalid for every later block.

For consuming inputs, `sequence=ffffffff` disables relative locking. Otherwise only bits 0..15 and bit 22 may be set; any other set bit rejects. Let `d = sequence & 65535`:

- Bit 22 clear: candidate height ≥ coin.creation_height + d.
- Bit 22 set: MTP(parent) ≥ coin.creation_parent_mtp + 512*d.

`creation_parent_mtp` is the parent's MTP at the block that created the coin, stored in its authenticated coin record. Coinbase creation uses the same metadata. Maturity is a separate height check. Same-block ordinary outputs have creation_height equal to the candidate height and creation_parent_mtp equal to current parent MTP, so only zero relative delay can pass. Overflow rejects rather than wraps. Relative-lock encoding is independent of local replacement policy.

Coinbase maturity applies to consumption: `height >= creation_height + COINBASE_MATURITY`. Ordinary coins have no maturity delay and may be spent in the block that creates them. The maturity value is at least one and remains uncalibrated.

## Core and complete identities

`Core(tx)` uses the exact Tx grammar with each consuming input's `Vec(BranchWitness)` omitted entirely (including its count), retaining path_index, and each mint input's BranchWitness omitted entirely. A mint input's core form is thus its 41 fixed bytes, with the token ID in `prev_txid`. Coinbase has no witnesses, but the identity domains still differ.

```text
TxID   = H_txid(ChainID || Core(tx))
TxHash = H_txhash(ChainID || Tx(tx))
```

TxHash is the Lotus v1 name for the hash of the complete transaction, witnesses included; earlier v2 drafts called it WitnessID. `H_name` domains are defined in the commitment packet. The block transaction root commits, in order, to each transaction's TxHash and TxID together (P02). Duplicate TxIDs within a block reject regardless of witness differences. Inserting any output whose outpoint already exists in the current state rejects; never overwrite a coin. Coinbase parent/height identity and unique consumption provide the induction base for outpoint uniqueness. Replaying a transaction on a competing fork can be valid if the same inputs exist there; ChainID separates networks, not every future fork of one network.

## Authorization plan and resolved outputs

Signers should authorize the method choices, not just the resulting outputs. A coinbase runs no script, so none of the following is defined for it. Define:

```text
AuthPlan = input_count:u16 || InputPlan[input_count]
InputPlan(spend) = 01 || CS(selected_path_index)
                   || Vec(CS(branch_index) || Leaf(script))
InputPlan(mint) = 03 || Leaf(mint_script)

Coins = input_count:u16 || CoinEntry[input_count]
CoinEntry(spend) = Bytes(Output(resolved_coin))
CoinEntry(mint) = Bytes(empty)
PlanHash  = H_authplan(AuthPlan)
CoinsHash = H_spentoutputs(Coins)
```

InputPlan branches occur in selected path order, exactly one per required branch. Scripts and their proofs are checked against the resolved coin's roots before treating this plan as authorized. A leaf in the plan is a commitment to the actual script, not a branch root or witness position. Mint leaves use the same leaf function as spend leaves and are distinguished by their InputPlan tag and the selector's invocation tag; the token ID itself is already in the core at that input.

Coins includes complete outputs for spend inputs in wire order; outpoints, flags and sequences are already in Core. A mint input resolves no coin, so its entry is the single byte `00` (zero-length Bytes), which keeps entries aligned with input indices and cannot be confused with a serialized output. It excludes confirmation height, creation MTP and coinbase status. Those fields remain authenticated contextual inputs for locks/maturity; they do not affect the signing digest. Moving the same ordinary coin to a different block can change contextual validity without changing the signature's intent.

AuthPlan excludes membership proofs and argument vectors. Those remain committed by TxHash and are validated at execution. This avoids signature self-reference and allows independent signature production. A method that needs authenticated application arguments must explicitly verify them or bind their effect to committed transaction fields. There is no general claim that all witness bytes are signer-immutable. There is no TxHash introspection opcode in this proposal.

## Exact CHECKSIG message

Three signing modes are proposed. The mode is always part of the message. A 64-byte signature selects mode `00`; a 65-byte signature is 64 signature bytes followed by one mode byte, which MUST be `01` or `02`. Any other length or trailing byte, including an explicit `00`, is a script error. Because adding a mode later would take a hard fork, this set is meant to be complete: there is no NONE, no all-inputs-one-output mode, no CODESEPARATOR, signature deletion, or legacy fallback. More unusual commitments are built in script from introspection and CHECKDATASIG.

```text
SpendSelector = 01 || Leaf(script)
MintSelector  = 03 || token_id:h32 || positive_delta:u128 || Leaf(mint_script)

InputCore(i) = input i exactly as it appears in Core(tx)
OwnInput(i)  = InputCore(i) || Bytes(Output(resolved_coin_i)) || InputPlan(i)
OutputsHash  = H_outputs(output_count:u16 || Output[output_count])

mode 00 FULL
  SigMessage = H_sighash(ChainID || 00 || TxID || CoinsHash || PlanHash || Selector)
mode 01 OWN_INPUT_ALL_OUTPUTS
  SigMessage = H_sighash(ChainID || 01 || version:u32 || lock:u64
                         || OwnInput(i) || OutputsHash || Selector)
mode 02 OWN_INPUT_ONE_OUTPUT
  SigMessage = H_sighash(ChainID || 02 || version:u32 || lock:u64
                         || OwnInput(i) || Bytes(Output[i]) || Selector)
```

Modes 01 and 02 correspond to Bitcoin's ALL|ANYONECANPAY and SINGLE|ANYONECANPAY. `i` is the index of the input whose script is executing. Both are defined only for spend invocations; a 65-byte signature in a mint invocation is a script error. In mode 02 the paired output is the one at the same index as the input; `i >= output_count` is a script error, never a signature over a placeholder. Neither message contains the index itself, so a signed input (and in mode 02 its paired output) may be placed at any position, provided the pair stays aligned. Same-index pairing is what stops one output from satisfying two different signed inputs. P02's registry holds the tag `outputs = Lotus/v2/outputs`.

A partial-mode signature covers the transaction version and lock, the signer's own outpoint, sequence, path choice, resolved coin and selected scripts, and the stated outputs. It does not cover any other input, any other input's coin, or in mode 02 any other output; anyone may add those. It is bound to one coin through the outpoint, so it is never shared across inputs, and it remains usable in any transaction that satisfies it until that coin is spent. The absolute lock is a not-before bound, not an expiry. No script condition can express an expiry either (C22a): a signed offer stays usable until one of its inputs is spent, so withdrawing it means spending that coin. Wallets and signing devices must display the mode and must not treat a partial-mode request as an ordinary payment.

In mode 00 the selector deliberately omits the input, path and branch indices. TxID, CoinsHash and PlanHash already commit to every input, every resolved coin and the script selected at every position, so no input can be added or re-planned under an existing signature. One mode-00 signature therefore authorizes every spend invocation of the same script in the same transaction: a consolidation of many coins held by one policy needs one signing operation, and a `(message, public key, signature)` verification result may be reused wherever that triple recurs, including across inputs. This is signature-result reuse, not the script-result caching restricted by C20, and static charges are unchanged. A signature still cannot move to another script, another transaction, or between spend and mint. Wallets must treat one signature as approval of every input in the transaction that runs that script.

CHECKSIG verifies the stack signature against **these 32 message bytes**, using the BIP340 algorithm unmodified (including its SHA256-based challenge calculation). Do not substitute BLAKE3 inside BIP340 because Lotus uses BLAKE3 for its message construction. No current block hash/height/time, coin confirmation metadata, signatures or TxHash enters this preimage. Reorganizations still require rechecking contextual validity and caches.

CHECKSIG stack order is `[..., signature, public_key]`; it consumes both and pushes canonical int128 Boolean. Public key is exactly 32-byte BIP340 x-only encoding; the signature operand is exactly 64 or 65 bytes as defined above, of which the first 64 are the BIP340 signature. Wrong length or invalid key encoding is a script error; a correctly sized but invalid signature pushes false. CHECKSIGVERIFY consumes the Boolean and rejects false. No empty-signature special case. Wallets must not reuse signing nonces across messages or signature algorithms. [BIP340](https://github.com/bitcoin/bips/blob/master/bip-0340.mediawiki) defines the signature algorithm; this packet defines Lotus's message.

## Acceptance evidence still required

Generate exact primitive, ordinary/coinbase, core/full, Coins/AuthPlan/selector and signing vectors in the independent reference tool; compare a second implementation. Test confirmation-metadata changes separately from output/method changes. Account for the per-transaction construction cost of CoinsHash and PlanHash and per-invocation signature charges. Freeze ChainID, versions and limits in the parameter manifest. This packet resolves proposed byte meaning; it does not supply mainnet constants, signed fixtures, or acceptance of this three-mode set without review.
