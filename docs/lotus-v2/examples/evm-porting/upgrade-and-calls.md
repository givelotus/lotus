# Upgrades, libraries and cross-contract execution

## Original behavior

An ERC1967 proxy delegates execution to an implementation selected through distinguished storage slots while retaining the proxy's address and storage. OpenZeppelin's proxy initializes through implementation code. Upgrade authority and compatible storage layouts belong to the surrounding proxy pattern. [ERC1967](https://eips.ethereum.org/EIPS/eip-1967), [OpenZeppelin ERC1967Proxy v5.0.2](https://github.com/OpenZeppelin/openzeppelin-contracts/blob/dbb6104ce834628e473d2173bbc9d47f81a9eec3/contracts/proxy/ERC1967/ERC1967Proxy.sol).

Lotus methods are committed leaves revealed to spend a coin. The output policy already commits to the available code, so changing its program normally changes its root. Importing a library, calling an inline helper, or inserting `contract_root(Other)` neither deploys a persistent instance nor transfers control to another script. Existing CABI-08 links prove build-time byte commitments; its positive/negative Python invocation tests pass, with native signed execution unavailable in this run.

## Proposed explicit migration

A stateful instance can include an authorized migration entry from its initial policy. That entry spends the actual instance and transfers its authority asset, value and state into a new, explicitly approved program/policy. The old code validates the transition and the approval; new code begins enforcing only on subsequent spends. There is no same-transaction constructor execution on the new output.

```text
entry migrate(next_policy: PolicyBytes, next_state: Bytes(8192),
              approval: Signature) terminal {
    require(singleton_input(this, instance_asset));
    require(checksig(approval, upgrade_authority));
    require(schema_migration_allowed(state_schema, next_policy, next_state));
    require(exact_successor(outputs[this.input_index], instance_asset, 1,
                            next_policy, next_state));
    require(preserve_reserves_and_mandatory_rules());
}
```

This is an LC-1 proposal. `next_policy` must be bounded canonical bytes and its state layout explicit. The signed transaction commits to exact successor outputs; any separate approval certificate also binds ChainID, instance identity, old state/nonce, destination policy and migration version. A successor with the correct asset but a bypass path is invalid. If migration needs a delay, schedule an authenticated migration ticket first and enforce its relative lock when consumed. Exact assets/reserves and user rights must survive according to the old contract's chosen migration rules. An upgrade authority able to approve arbitrary code remains a trusted administrator; terminology must not imply immutable guarantees.

A stable application identifier can be a unique authority TokenId or original seed plus verified transition lineage, resolved by an indexer. It is not a stable spend root. Migrating a token's mint tree changes its TokenId. A mint tree deliberately made generic can retain its identity while consulting a consumed authority/controller for policy state, but only within the capabilities originally encoded. A frozen root cannot gain a new opcode/call capability through a library update.

Test unauthorized upgrade, stale approval nonce, wrong chain/instance, state-layout mismatch, forged successor, lost mandatory token rules, changed assets/value, duplicate authority successor and downgrade to a previously revoked implementation. Indexers must follow authentic transitions and roll back on reorg; a registry announcement alone cannot identify the genuine instance.

## Calls and reentrancy

There is no EVM call stack, `msg.sender`, shared mutable storage between branches, fallback handler, return-data ABI, or delegatecall. Scripts inspect one immutable transaction/resolved-input view. Every selected branch must independently succeed; no script may assume another invocation executed a specific method. This removes synchronous call reentrancy as an execution mechanism, but it does not remove cross-input authorization bugs. Two inputs can still incorrectly count the same payout, accept forged state, or rely on mutually incompatible assumptions.

Compose protocols by assembling one transaction whose consuming inputs and outputs satisfy every independent covenant. Use typed role indices and complete policy/state checks. A participant can require another coin's mandatory policy and exact output effects, but that proves neither a particular leaf ran nor an arbitrary call returned a value. If method identity matters, encode the required effect/authorization in both participants or use an authenticated controller state that makes alternatives safe. Do not introduce an `invoked(other.method)` assertion with no enforceable lowering.

**Frontend/library:** explicit effects, migration codecs and full-policy comparison. **SDK:** artifact version pinning, approvals, role composition, honest signer displays. **Indexer:** stable application identity and lineage. **VM/transaction:** the migration/atomic-composition model uses existing operations; complete proofs and runtime measurements remain work. **Consensus:** exact delegatecall, callbacks or arbitrary dynamic code execution would require a new execution model, not a source-language convenience. This proposal rejects automatic addition of DEFINE/INVOKE or any claimed EVM compatibility shortcut.

---

## References

1. **[Lau & Wuille 2016a]** Johnson Lau and Pieter Wuille, *"BIP 114: Merkelized Abstract Syntax Tree"*, Bitcoin Improvement Proposals, April 2016.
2. **[Wuille, Nick, & Towns 2020a]** Pieter Wuille, Jonas Nick, and Anthony Towns, *"BIP 341: Taproot: SegWit version 1 spending rules"*, Bitcoin Improvement Proposals, January 2020.
3. **[O'Connor & Piekarska 2017]** Russell O'Connor and Marta Piekarska, *"Enhancing Bitcoin Transactions with Covenants"*, in *Financial Cryptography and Data Security (FC 2017)*, LNCS vol. 10323, pp. 191–198, 2017.
