# Escrow, limit orders and a constant-product pool

## Hash escrow and refunds

The executable [HashEscrow](supported/escrow.lotus) coin has two entry leaves: a seller signature plus SHA256 preimage, or a buyer signature plus an absolute refund-height lower bound. [Evidence](evidence/cases.json) accepts the claim and a refund lock of 100, rejects a wrong secret and lock 99, and accepts a claim with lock 101. That last result matters: refund maturity enables a competing spend; it does not expire the seller's claim. The first mined spend wins. Outer block eligibility was not tested. This is a concrete escrow primitive, not a claim to reproduce every Solidity escrow.

A dispute escrow replaces the hash claim with explicit buyer/seller/arbitrator paths and checks recipient outputs where signatures alone should not choose them. The transaction holds funds in the consumed coin; another asset or fee sponsor needs another input. Test revealed-secret reuse across contracts, wrong owner, conflicting refund/claim, payout bypass and signatures bound to a different instance. Existing signature/hash/lock opcodes support this primitive; frontend state is unnecessary for the basic version.

## 0x-style limit orders

0x limit orders describe maker/taker assets and amounts, optional taker restrictions and fees, salt and expiry; partial fills update fill status, while fill-or-kill requires the requested quantity. [0x order documentation](https://docs.0xprotocol.org/en/latest/basics/orders.html?highlight=signature), [0x functions](https://github.com/0xProject/protocol/blob/development/docs/basics/functions.rst). These documentation links are mutable; this comparison does not claim a pinned full 0x source port.

For Lotus, escrow the maker asset in a genuine order coin. Bound terms include payee policy, offered/payment assets, original amount `Q`, price numerator/denominator and any taker key. Remaining quantity is the actual token amount; cumulative filled and cumulative paid are authenticated state if exact cumulative rounding is required. Cancellation is a maker-authorized competing spend. A partial fill consumes the order and creates a remainder plus payment. This reserves liquidity in advance and differs from an off-chain order backed by a revocable account allowance.

LC-1 proposal, with unimplemented typed helpers/effects:

```text
entry fill(quantity: Amount) transition {
    require(0 < quantity && quantity < this.coin.value);
    next.filled = filled + quantity;
    due_total = ceil_mul_div(next.filled, price_num, price_den);
    payment = due_total - paid;
    next.paid = due_total;
    payout maker at outputs[2 * this.input_index]
        asset = quote_asset, value = payment, policy = maker_policy;
    successor rest at outputs[2 * this.input_index + 1]
        asset = offered_asset, value = this.coin.value - quantity,
        policy = order_policy(next);
}
```

The terminal full-fill entry checks all remaining consideration without recreating zero remainder. A fill's acquired tokens go to a taker output checked by the taker's own signed intent; maker terms need not dictate it. Mandatory token restrictions remain on every remainder path. Fees require explicit extra roles and checked rounding. The injective index rule prevents two order inputs from claiming one maker payment. If flexible role indices are used, each covenant must enforce nonoverlap across participating orders, not trust a builder assertion. A unique batch coordinator or explicit input/output index proof can supply this obligation.

A true upper expiry is unavailable under C22a. A delayed cancellation/sweep method permits withdrawal after a date but does not invalidate an unspent order. A Dutch auction price may be a monotone function of the transaction's lower-bound lock with an explicit clock. It must not trust an unconstrained witness timestamp. Tests: partial fills whose separate rounding underpays, zero denominator, overflow, forged remainder, wrong payment asset/policy, output reuse across orders, unauthorized cancellation, late fill versus sweep conflict and mandatory-rule removal. **Gaps:** frontend state/roles/division, library rounding and exact policy, SDK discovery/transaction composition, indexer live orderbook/cancellation. The expiry difference is **consensus semantics**; no change is requested here.

## Uniswap V2 behavior and selected Lotus model

The pinned pair holds two reserves, mints/burns LP shares, checks a fee-adjusted product after swaps, optionally invokes a flash-swap callback, and accumulates timestamp-based prices. Protocol fees depend on growth in square-root liquidity. [Uniswap V2 pair v1.0.1](https://github.com/Uniswap/v2-core/blob/4dd59067c76dea4a0e8e4bfdda41877a6b16dedc/contracts/UniswapV2Pair.sol), [V2 whitepaper](https://docs.uniswap.org/whitepaper.pdf).

A Lotus output holds only one asset. Model a pool as one uniquely authenticated controller coin plus two reserve coins, one per asset, all consumed/recreated in each operation. Controller state commits to asset IDs, reserve amounts, LP supply, reserve policy version and nonce. Reserve covenants require the genuine one-unit controller and check the same exact successor effects independently. The controller verifies each old reserve's asset, amount and mandatory reserve policy, exact reserve input multiplicity, and each new reserve. It must exclude unrelated coins masquerading as reserves and prevent two pools sharing one output. These are obligations to implement, not effects supplied by `contract_root`.

A fixed reserve-program root plus controller authority ID avoids recursive commitments. Bootstrap creates a unique uninitialized pool controller from an explicit seed; initialization binds distinct assets, policies and reserves once. The controller token and LP mint program use the [two-phase enrollment pattern](../../script-abi.md#mint-authority-supply-and-libraries). The LP mint must independently verify the controller transition; it cannot infer that a specific controller method ran.

### Executable arithmetic slice

[supported/amm-kernel.lotus](supported/amm-kernel.lotus) checks a one-direction trade:

```text
require(nextX == oldX + inputX);
require(nextY < oldY);
require((nextX * 1000 - inputX * 3) * (nextY * 1000)
        >= oldX * oldY * 1000000);
```

It additionally requires positive quantities and every reserve/input below `2^50`, keeping both products below `2^120`, safely within signed int128. Starting at `(1000,1000)`, adding 100 X permits output 90 Y (`nextY=910`) and rejects 91 Y (`909`); negative values and out-of-range reserves reject. These VM checks authenticate no actual reserves, ownership, LP supply or payout. Do not use this kernel alone as a pool covenant.

### Proposed complete operation

```text
entry swap(plan: PoolTransition, proofs: StateProofs) transition {
    old = authenticate_pool_and_reserves(this, plan.inputs, proofs);
    require(plan.assets == old.assets && plan.controller_nonce == old.nonce);
    require(fee_adjusted_product_holds(old, plan));
    require(plan.lp_supply == old.lp_supply);
    require(distinct_roles(plan.inputs, plan.outputs));
    require(exact_reserve_outputs(plan));
    require(exact_controller_successor(plan, old.nonce + 1));
}
```

This is a proposed contract interface. Each helper needs a bounded implementation and adversarial fixtures. The transaction supplies every participating reserve input, output and fee coin. Atomic validation checks all their scripts without callbacks or shared mutable execution state. A multi-pool route can be composed as one transaction; no invocation temporarily borrows another invocation's stack/state. A flash-swap-like net settlement can be expressed when all required coins and repayment effects fit one transaction. It does not run a user-provided callback.

For initial liquidity, define share decimals and `L = floor(sqrt(X*Y)) - minimumLiquidity`; account for the minimum in a permanently nonredeemable share holding if total LP supply includes it. An explicit burn destroys supply under C14 and therefore is not automatically equivalent to Uniswap's locked but supply-counted minimum shares. Later deposits issue `min(floor(dx*L/X),floor(dy*L/Y))`; withdrawal burns LP units and pays floor-proportional reserves. Mint/burn programs must couple to the same controller/LP state transition, and implicit burns require a declared policy for whether they update circulating/redeemable supply. Native fee input is separate from reserve withdrawals.

P03 has MUL128_WIDE, carry/borrow, SQRT and ordinary division, but the frontend exposes neither general limb arithmetic nor division. Full u64 reserve products multiplied by fee scales exceed int128; checked wide library operations or proven narrower reserve limits are prerequisites. Uniswap's uint112 reserves/uint256 arithmetic are not preserved by the bounded executable slice. Fee-on `kLast`, donations, sync/skim, and rebasing/fee-on-transfer assets require separately stated semantics; the initial Lotus pool should reject unsupported assets/features explicitly in its interface.

A block-time TWAP accumulator is not equivalent under C22a. User-selected lower-bound locks can lag arbitrarily; a pool must not label their time average as the original on-chain TWAP. Use off-chain/indexer observations or authenticated oracle inputs with their own trust model. Transaction-level scripts cannot read arbitrary unspent oracle state without consuming it.

Required tests include spoofed controller/reserve coins, wrong asset, duplicate reserve output, one-reserve theft, LP inflation, unauthorized mint, incorrect burn attribution, division rounding, wide-math boundaries, state proof mutation, two pools sharing payouts, stale parallel swaps and reorg/restart behavior. **Frontend/library:** state/roles, wide math, proofs and full-policy checks. **SDK:** atomic multi-asset planning, exact slippage/minimum outputs and fee sponsorship. **Indexer:** pool discovery, reserves, LP history and prices. **VM/transaction:** existing primitives appear sufficient for this narrower atomic model pending compiled proof. **Consensus:** timestamp TWAP/callback equivalence is absent; no opcode or transaction extension is justified by this slice yet.
