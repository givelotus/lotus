# Worked contract examples

Status: semantic examples for review. These programs are pseudocode, not executable bytecode. Candidate byte/commitment/signature semantics now exist in P01–P03; generated signatures and complete execution results still await the reference assembler/evaluator; no illustrative hash is presented as a computed result.

The separately generated [structural fixtures](candidate-smoke-vectors.json) cover framing, hashing, trees and selected integer algorithms. Their [generator and scope](../tools/README.md) are explicit: they do not execute these contracts or verify a signed payment.

## 1. Ordinary payment

```text
contract Payment(owner: XOnlyPublicKey) {
    spend(signature: SchnorrSignature) {
        require(checksig(signature, owner, invocation.signing_message));
    }
}
```

Symbolic assembly: `<owner> OP_CHECKSIG`. Arguments bottom-to-top: `[signature]`; pushing owner leaves signature below the key. The proposed CHECKSIG pops key then signature and pushes int128 Boolean success. Selected policy: one branch `Leaf(script)`, `paths=[[0]]`; path index zero, exactly one witness, empty membership proof.

Pre-state: one mature native coin with value 100000 and the payment policy. Transaction: consume it and create native outputs of 60000 and 39000 to two fully specified recipient policies, no references or mints. Expected native fee: 1000. With valid authorization, the final stack is `[true]`, the input is removed and both outputs are inserted. Coinbase fee collection is a separate block-level result. Changing a committed output changes core identity and the signing message.

Cost report must include parsing, coin resolution, root verification, push/CHECKSIG and accounting; it cannot assume a signature-cache hit. Signature bytes are intentionally absent until exact sighash framing is agreed.

## 2. Recovery vault

Policy: `branches=[owner, recovery]`, `paths=[[0],[1]]`. Owner is a signature program; recovery is a signature program with an explicit timelock. The whole recovery condition belongs inside its branch or in a separate required branch on that path. A path containing only a guardian signature does not inherit a timelock from another unselected path.

Expected result: each selected path requires exactly its listed witness(es). The recovery program must specify height or median-time clock and boundary equality. No expected time-boundary bytes are generated until locktime/sequence semantics are frozen.

## 3. Token lifecycle

Under the proposed program-derived identity, a mint input authorizes a positive delta of 1000 units into a recipient policy. Native inputs separately cover fees. A later transaction consuming 1000 units and producing 700 + 250 units burns 50 token units; it has no mint input. Every consumed token coin still executes its selected authorization path. A minted token output does not automatically acquire the issuer's transfer restrictions.

A one-time mint policy requires a specified anchor outpoint to be consumed, checks its asset and authorization context, and bounds exactly the selected token's positive delta. Mere presence as a read-only reference is insufficient. A replacement delegation certificate does not revoke an earlier certificate without an explicit validity interval or authenticated revocation state.

## 4. Input × output vault transition

```text
contract Vault(policy_id, asset_id, owner: XOnlyPublicKey) {
    spend(owner_signature) {
        require(checksig(owner_signature, owner, invocation.signing_message));
        for input in tx.inputs {
            if input.consumes_coin && belongs_to_this_vault(input, policy_id) {
                matches = 0;
                for output in tx.outputs {
                    if output.state.parent_outpoint == input.outpoint {
                        require(output.asset_id == asset_id);
                        require(valid_successor_policy(output, policy_id));
                        require(valid_transition(input.coin, output));
                        matches += 1;
                    }
                }
                require(matches == 1);
            }
        }
    }
}
```

This describes a one-successor-per-vault-input application, not a generic balance aggregator. State parsing and `belongs_to_this_vault`, policy equality and transition rules must be lowered to actual opcodes. Immutable, distinct parent-outpoint tags make one output unable to match two distinct inputs. Extra unrelated outputs are governed by the chosen application rules and native/token conservation. Every relevant vault input must select a path that requires this invariant.

An invocation scans I×O pairs. Repeating it on K inputs charges K×I×O body work, plus other costs. This deliberately uses independent execution; no companion is excused because another coin merely stores the same branch root. Static bounds ignore early exit and cache reuse.

## 5. Read-only state

A consuming payment input is paired with a reference input to an unspent oracle coin. The spending program checks the referenced state schema, publisher policy and application's freshness conditions. The reference contributes no spendable value. Expected post-state retains it. If an earlier transaction in the same block consumes that oracle coin, this transaction cannot resolve the reference and rejects. If a later transaction consumes it, the read was valid at its own transaction position.

An on-chain timestamp in oracle state does not itself prove real-world freshness or publisher truthfulness. Application trust assumptions must be stated.

## Completion contract

Deliver these examples in order. Each becomes executable only when it includes source, assembly, bytecode, canonical arguments, initial coin records, complete transaction bytes, commitments, signing data, final stack, static cost and post-state/undo result, produced by pinned tools. Pair each with focused local conformance cases for its requirements. The schema for those records and the outstanding evidence are in [validation](../validation.md).
