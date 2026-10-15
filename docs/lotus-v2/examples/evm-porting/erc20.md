# ERC20: balances, supply and delegated spending

## Original behavior and translation boundary

ERC20 exposes balances, transfers, allowances and observable transfer/approval events. An approval overwrites a spender's allowance; a delegated transfer consumes it. OpenZeppelin's capped extension constrains outstanding total supply, so burning can make room for later issuance. ERC-2612 adds owner nonces and signed approvals with a block-time deadline. [ERC20](https://eips.ethereum.org/EIPS/eip-20), [ERC20Capped at v5.0.2](https://github.com/OpenZeppelin/openzeppelin-contracts/blob/dbb6104ce834628e473d2173bbc9d47f81a9eec3/contracts/token/ERC20/extensions/ERC20Capped.sol), [ERC-2612](https://eips.ethereum.org/EIPS/eip-2612).

Lotus token quantities are native transaction assets. A holder's balance is the sum of identified spendable UTXOs, not a VM account mapping. Every output holds one asset; native fee sponsorship is another input. A `TokenId` commits to the mint program, while each holding can choose a different owner policy. Amounts on wire are u64; this does not preserve arbitrary ERC20 uint256 balances or decimal conventions. Metadata and events need explicit application formats and an indexer.

## Executable warning: a per-mint bound is not a supply cap

[supported/per-mint-limit.lotus](supported/per-mint-limit.lotus) compiles today:

```text
token PerMintLimit<issuer: PublicKey, limit: Amount> {
    function issue(delta: Amount, sig: Signature) {
        require(limit >= delta);
        require(checksig(sig, issuer));
    }
}
```

The node supplies `delta`; it is absent from witness arguments. The [VM cases](evidence/cases.json) accept 1000 units under a limit of 1000 in each of two distinct transactions and reject 1001. The two accepted invocations use distinct hypothetical funding coins, not a connected two-transaction ledger. Nevertheless the script has no state linking them: it cannot enforce a lifetime cap. There are no transfer restrictions in this small mint slice. The existing [fungible gallery](../../../../tools/lotus-v2-compiler/examples/gallery/README.md) separately exercises mandatory transfer branches, mint, transfer and merge.

## Proposed controller and lifecycle

LC-1 sketch below uses proposed standard-library operations, not existing compiler syntax:

```text
contract SupplyController<authority: TokenId, issuer: PublicKey, cap: Amount> {
    state separate {
        enrolled: Bool, asset: TokenId, issued: Amount,
        outstanding: Amount, nonce: Amount, revoked: Bool
    }
    entry enroll(asset: TokenId, sig: Signature) transition {
        require(!enrolled && checksig(sig, issuer));
        require(singleton_input(this, authority));
        next = { enrolled: true, asset: asset, issued: 0,
                 outstanding: 0, nonce: nonce + 1, revoked: false };
        successor controller at outputs[this.input_index]
            preserves this.policy with state = next;
    }
    entry account(sig: Signature) transition {
        require(enrolled && !revoked && singleton_input(this, authority));
        require(checksig(sig, issuer)); // Example mint administration.
        next.outstanding = outstanding + asset_net_spendable_delta(asset);
        require(0 <= next.outstanding && next.outstanding <= cap);
        next.issued = issued + asset_positive_mint_delta(asset);
        next.nonce = nonce + 1;
        successor controller at outputs[this.input_index]
            preserves this.policy with state = next;
    }
}
```

This sketch omits transfer-only authorization routing and codecs; they are required work, not implicit compiler magic. A production transfer entry must authorize burn/accounting updates without granting arbitrary mint authority. The target mint requires the issuer signature **and** the one-unit enrolled controller, independently checks its target asset equals the active mint root, and computes/checks the same successor state. It cannot assume which controller entry ran. Transfer rules on every holding require that controller and verify the same accounting transition independently. Enrollment is allowed only once; revocation is an explicit authorized terminal transition, or a retained revoked state with no issuance path.

Bootstrap uses a separate singleton authority token whose sole mint requires an explicitly named unique seed outpoint, delta 1, and an exact initial controller policy/state. Its generic controller code does not embed the future fungible token ID. Compile that authority first, compile the fungible mint from its ID and code root, then enroll the resulting fungible TokenId. No root depends recursively on itself. A fake controller output with correct code/state but zero authority value is rejected; the singleton asset's genesis and all transitions must preserve exactly one unit.

For each tracked asset define `I = sum(consumed values)`, `O = sum(all output values)`, `E = sum(values in IS_BURN outputs)`, and `D = max(O-I,0)`. Native accounting authorizes exactly `D`; the change in spendable token supply is `O-E-I`, not just `D`. Mixed mint/burn transactions require this full calculation: a positive mint can coexist with explicit burns. Track a signed delta with proven bounded arithmetic before checking the u64 cap. Read only spend inputs for coin fields. The controller and rules prohibit every bypass and require one matching controller successor. Unsolicited burn-output creation with this TokenId still requires either authorized spent tokens or its mint.

This yields an outstanding-supply cap only if **all** initial issuance and every later token spend pass the mandatory rules. It serializes transfers through one controller and needs measured cost. A cheaper separate design records `issued += D` only on mint, requires `issued <= cap`, and never returns burned capacity. Call that a **lifetime issuance cap**. Burning from that token remains possible through native conservation; `totalSupply` is then an indexer-derived quantity rather than a synchronous contract query. These two designs must have different published interfaces.

## Allowance and permit proposal

A bounded delegation vault contains the owner's tokens and a state commitment `(owner, spender, asset, remaining, nonce)`. The owner can revoke or replace its policy; the spender can consume up to `remaining`, creating a prescribed recipient payout and an exact remainder. This reserves funds upfront and differs from ERC20 allowance over a changing account balance.

For closer account behavior, use one authenticated account controller carrying a Merkle balance/allowance map, and require it whenever any enrolled holding is spent. A proposed entry is:

```text
entry transferFrom(owner: PublicKey, spender: PublicKey, amount: Amount,
                   allowance_proof: MapProof, sig: Signature) transition {
    require(checksig(sig, spender));
    old = allowances.authenticate(owner, spender, allowance_proof);
    require(amount <= old.remaining);
    allowances = allowances.update(old, {remaining: old.remaining - amount,
                                        nonce: old.nonce + 1});
    // Explicit token inputs, recipient output, change and controller successor
    // must all be checked; the map update alone authorizes no token movement.
}
```

Map key encoding, absence and sequential updates need canonical libraries. Two updates against the same old root cannot be independently combined; update the second proof against the intermediate root or verify a canonical multiproof. A spender signature binds the full planned transaction. Unlimited allowances require an explicit sentinel and semantics; no overflow sentinel is inferred.

A Lotus permit is an application BIP340 data signature over a versioned domain including ChainID, authority/instance identity, owner, spender, amount, nonce and scope. Consume/recreate the authenticated nonce coin to prevent replay. A relayer may supply native fees. The exact signed bytes and disclosed intent belong in the SDK; argument bytes alone are outside TxID. Existing P03 CHECKDATASIG/SIGHASH support the primitive, but the current frontend lacks their general typed bindings.

This is **not ERC-2612 wire compatibility**. EIP-712 uses Keccak and Ethereum address/signature conventions; the P03 hash set has no Keccak, and CHECKDATASIG verifies explicit keys rather than recovering an Ethereum address. More fundamentally C22a cannot enforce the ERC-2612 upper deadline: `tx.lock <= deadline` does not prevent that transaction mining later. Use a revocable consumed nonce/authority coin and advertise the lack of automatic expiry. A policy change to block-time-dependent validity requires a separate consensus decision. [EIP-712](https://eips.ethereum.org/EIPS/eip-712).

## Required adversarial evidence and gaps

Tests must reject repeated seed issuance, forged/zero-valued controllers, altered cap/state, duplicated successors, missing rules on any OR path, reused nonce, wrong chain/instance/spender, oversized proof, stale map update, signature mutation, native-fee omission, and overflow. Demonstrate successful burn followed by remint under the outstanding cap, rejection under a lifetime cap, and a simultaneous positive mint plus explicit burn. Test the approval replacement race; UTXO conflicts prevent both spends of one state, but do not guarantee which wins.

**Frontend:** state effects, input/output roles, `<=` emission, hash/codec and data-signature bindings. **Library:** singleton bootstrap, exact-policy preservation, authenticated maps, checked aggregate deltas. **SDK:** funding, permit encoding, nonce selection and signing display. **Indexer:** historical issuance/burn supply, balances, metadata/events and reorg rollback. **VM:** no new instruction demonstrated necessary for the Lotus design. **Transaction:** current consume/recreate model expresses it but serializes controller access. **Consensus:** exact expiring ERC-2612 semantics conflict with C22a; this design requests no consensus change.
