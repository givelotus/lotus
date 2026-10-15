# Threshold wallets, recovery, timelock and vesting

## Safe-style authorization

Safe combines an owner threshold with nonce-bearing transaction authorization, optional modules/guards, and calls or delegatecalls. Our translation preserves only explicitly selected authorization and state behavior. [Safe v1.4.1](https://github.com/safe-global/safe-smart-account/blob/bf943f80fec5ac647159d26161446ac5d716a294/contracts/Safe.sol), [Safe architecture](https://docs.safe.global/advanced/smart-account-overview).

[supported/threshold.lotus](supported/threshold.lotus) implements 2-of-3 as three independently committed entry leaves: Alice+Bob, Alice+Carol, Bob+Carol. The coin needs one branch/path; the witness selects one entry. All three signature combinations execute successfully in [cases.json](evidence/cases.json); a corrupted signature fails. Each signature binds the complete transaction and its actual invocation selector. Spending the outpoint gives replay protection for this transaction; it is not a reusable Safe account nonce.

For larger thresholds, enumerating every subset is impractical and exceeds the current 16-method limit. Proposed `threshold(k, distinct_keys, signatures)` expands a bounded verifier in one leaf, with a canonical ordered signer-index list, uniqueness checks, domain/mode checks and at least `k` valid signatures. No CHECKMULTISIG or aggregate-signature consensus instruction is required by that design. Aggregated BIP340 signing is a separate signing protocol with its own review; ordinary CHECKSIG can verify the result, but the compiler cannot infer the participants' authorization from a key alone.

LC-1 policy sketch, not implemented:

```text
policy Treasury<owners: ContractRootHash, recovery: ContractRootHash,
                limits: ContractRootHash> {
    branch owner_quorum at 0 = owners;
    branch delayed_recovery at 1 = recovery;
    branch spending_limits at 2 = limits;
    path normal = all(owner_quorum, spending_limits);
    path recover = all(delayed_recovery, spending_limits);
    require every_path(spending_limits);
}
```

The recovery branch itself performs `check_sequence(1, delay)` and guardian authorization. Key rotation spends the actual treasury coin and creates an exact approved successor policy. A shared account controller can coordinate multiple holdings; its presence is mandatory on every relevant spend. Adding a module as an alternative path explicitly gives it independent spending power. Guards intended to be universal must be on every path, including recovery and module paths. Imported contracts/helpers do not become modules automatically.

Attacks to test: repeated signer key counted twice, insufficient quorum, wrong digest/mode, extra/missing branch witness, recovery bypassing limits, disabled/wrong-clock sequence, changed threshold without old authorization, and replay of an old controller state. **Frontend/library:** typed arrays or bounded threshold specialization, state/policy transitions. **SDK:** partial signature collection, deterministic input positions, coin conflicts. **Indexer:** pending proposals and state lineage. **VM/transaction:** existing branches/signatures/locks suffice for these restricted semantics; no call/delegatecall compatibility is claimed.

## Timelock controller

OpenZeppelin's TimelockController schedules identified operations, supports predecessor ordering and cancellation, and executes after a minimum delay. [TimelockController v5.0.2](https://github.com/OpenZeppelin/openzeppelin-contracts/blob/dbb6104ce834628e473d2173bbc9d47f81a9eec3/contracts/governance/TimelockController.sol).

Translate a scheduled operation into an authenticated ticket coin whose state commits to the intended output effects, salt, authority and predecessor. Creation spends an authorized scheduler coin or unique issuance capability. Execution consumes the ticket with an input-relative delay; cancellation consumes it through a separate authorized entry. A relative clock measures ticket creation, so it cannot be shortened by an arbitrarily backdated user lock. Height and 512-second relative time use distinct types. Maturity still requires outer node validation.

Proposed ticket source:

```text
contract Operation<delay: Int, canceller: PublicKey> {
    state separate { effects: Bytes32, predecessor: Bytes32 }
    entry execute(effect_witness: Bytes(8192)) terminal {
        require(check_sequence(1, delay));
        require(canonical_effects_hash(effect_witness) == effects);
        require(transaction_matches_effects(effect_witness));
        require(authenticated_predecessor_complete(predecessor));
    }
    entry cancel(sig: Signature) terminal {
        require(checksig(sig, canceller));
        require(no_reissued_ticket());
    }
}
```

These helper contracts are not implemented. Predecessor completion needs authenticated state or a unique completion capability, consumed and recreated if reusable. A witness saying “done” or a familiar receipt root without provenance is insufficient. Requiring a shared scheduler registry on completion/cancellation provides exact operation-status lookup but serializes unrelated operations. The application must choose this tradeoff. The ticket cannot invoke arbitrary EVM calldata; its approved transaction effects are checked as inputs/outputs. Test ticket duplication, forged predecessor, changed effects, cancellation/execution conflicts, reset-delay games and replayed operation salts.

## Linear vesting

OpenZeppelin VestingWallet releases native/ERC20 assets to its owner according to a schedule; later deposits are treated as if vested from the original start. [VestingWallet v5.0.2](https://github.com/OpenZeppelin/openzeppelin-contracts/blob/dbb6104ce834628e473d2173bbc9d47f81a9eec3/contracts/finance/VestingWallet.sol).

A first Lotus version should use a fixed allocation per vault, with state `released`, bound `total`, `start`, `duration`, asset and beneficiary policy. A release transaction selects a lower-bound lock `t` and proves `tx.lock_kind` matches the schedule. Compute `vested(t)=0` before start, `total` at/after end, otherwise `floor(total*(t-start)/duration)`. Require `0 < payout <= vested(t)-released`, exact beneficiary payment, `released'=released+payout`, and a successor carrying exactly the remainder. Use distinct output slots for payout and successor. At full release the explicit terminal entry checks no remainder; preserve other mandatory token branches where required.

Proposed expression/effects:

```text
entry release(t: Int, payout: Amount) transition {
    require(check_lock(2, t));
    require(payout <= vested(total, start, duration, t) - released);
    require(payout > 0);
    next.released = released + payout;
    successor remainder at outputs[2 * this.input_index]
        asset = asset, value = total - next.released,
        policy = vesting_policy(next);
    payout beneficiary at outputs[2 * this.input_index + 1]
        asset = asset, value = payout, policy = beneficiary_policy;
}
```

This is proposed syntax; typed absolute-time locks, division, state effects and full-policy output checking need implementation. Selecting an older `t` can release less, not more; selecting a future `t` delays contextual eligibility. It does not expose block time. Use checked wide multiplication/division or a proven bound; int128 multiplication of unrestricted u64 quantities can overflow. `duration=0` needs an explicit cliff rule, not division by zero.

For exact later-deposit behavior, additional funding must be enrolled by consuming the genuine controller and updating `total = prior deposited + new deposit`, preserving `released`; the newly enrolled amount follows the original schedule. Stray coins sent to a similar root do not silently alter authenticated allocation. Multi-asset vesting requires one vault per asset or an explicit controller and asset-specific reserve outputs. Test first/last unit rounding, late deposits, wrong asset, duplicate payout counting across two vault inputs, forged state, beneficiary changes, and remainder bypass paths. **Gaps:** frontend arithmetic/state/output effects, library codec/wide math, SDK slot allocation, indexer history. No new VM or consensus operation is requested.
