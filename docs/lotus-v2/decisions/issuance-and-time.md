# Issuance, clocks and faucet: decision-ready questions

Decision packet P06, October 9, 2026. D05/D10/D11 economic/state choices remain **open**. This packet does not amend the monetary paper. It defines candidate mechanics and the evidence needed to accept them.

## Token identity recommendation

Use program-derived identity as in C15/P01: `TokenID=H_token(Bytes(mint_script))`, nonzero. This identifies an immutable mint policy, not a unique invocation or organization. Two issuers wanting different assets with otherwise identical code must include distinct committed constants in their programs. A script constructor should make that discriminator explicit. Holder authorization and transfer-policy preservation remain separate obligations.

A supply cap requires an authenticated cumulative state or an exclusively consumed initial allocation/authority; a stateless repeated signature check does not remember past issuance. A one-time mint requires consumption of its unique anchor, checks the asset-specific delta, and cannot accept a reference as that anchor. New certificates do not revoke old ones. Accept this identity model only after reviewing these lifecycle requirements; the historical outpoint-derived design must then be marked superseded rather than left as another valid interpretation.

## Tail recurrence candidate with exact integer meaning

The paper's gamma=1/2 recurrence can have an exact integer candidate, avoiding a floating-point sqrt or an approximate log interpolation. Let W_n be the exact per-block work from P04's selected target convention. Let S_n be the integer tail entitlement of block n, known before choosing that block's timestamp/nonce. After accepting block n, compute:

```text
Q = floor(S_n * S_n * W_n / W_(n-1))
S_(n+1) = min(S_max, max(S_min, isqrt(Q)))
```

This floors the unscaled recurrence once before clipping; `isqrt(floor(x))=floor(sqrt(x))` for nonnegative x. Compute the mathematical product before division with bounded sufficiently wide integers, not modular multiplication. With S≤u64 and W≤2^256, the numerator is below 2^384; intermediate width and target conventions must be reflected in the implementation contract. If sub-unit precision is desired, define a fixed-point state separately; it changes rounding behavior and needs different vectors.

Genesis must specify S_0 and W_(-1)>0 (or an explicit first-step rule). The monetary state envelope can carry next_tail and previous_work plus any bootstrap/faucet state. Reward lag is deliberate: current entitlement is established from prior accepted state; current work adjusts the next entitlement. Clipping and rounding make this state path-dependent and must be restored on reorg. This candidate is not identical to a direct `K*sqrt(W_n)` rule and may have rounding dead zones; analyze those before adopting it.

## Bootstrap clock alternatives

| Choice | Deterministic implementation requirement | Incentive question |
| --- | --- | --- |
| Height-based paper bootstrap | Exact decay/rounding as a function or recurrence; explicit initial value | No direct reward from changing a timestamp, but DAA incentives remain |
| Current-header timestamp decay | Exact function of time and origin, overflow/large-gap bounds | A smaller permitted timestamp can increase current reward while moving future difficulty costs to later miners |
| Parent-derived timestamp decay | Exact lag and ancestor definition | Removes the current miner's direct control of its own decay input, but does not prove honest timestamps or eliminate influence on future rewards |

Recommend using the paper's height-based model as the comparison baseline, **not silently adopting it over the user's timestamp proposal**. A per-block rational integer recurrence is easy to bound but differs from flooring a closed-form exponential; specify which one is intended. A timestamp exponential also needs a bounded deterministic algorithm for large gaps. No real-valued formula is a complete consensus implementation.

## Timestamp incentive objective and limits

The stated goal is a miner preferring a fresh, accurate timestamp at discovery. Use expected discounted profit for a miner able to vary hash allocation as the principal objective; also report the fixed-share special case. Include native reward, collectible fees, costs, orphan/eligibility risk, withheld blocks, timestamp granularity, and how later difficulty/reward effects accrue to that miner. Quantify the deviation benefit against honest-clock reporting over the same feasible history and horizon.

A narrow information limitation is already clear: chain bytes alone do not reveal the physical discovery time. The same valid header history can be observed after different real-time discovery/delivery histories. Thus a deterministic function of those bytes cannot *certify* exact discovery time. This does not prove approximate truthful incentives impossible under a specified network/clock model; it explains why such a claim needs assumptions beyond the reward equation.

Do not optimize reward/work over arbitrary independent difficulties. Difficulty is a function of permitted ancestor timestamps and the exact ASERT algorithm. Compare feasible timestamp histories and complete discounted outcomes. Current reward may depend on current/parent state while future work/reward effects accrue partly to other miners. A mobile miner's incentives cannot be inferred from a permanent 100%-share miner or a fixed-hashrate Jensen bound.

The analysis deliverable is: model/assumptions, feasible controls, honest baseline, best-response computation or a proved bound, sensitivity across miner share/discount/cost/fee regimes, and a narrowly stated conclusion. Candidate rules remain open if the model cannot support a freshness claim. Simulations must use the same integer DAA/reward semantics as the proposed consensus, not a continuous approximation substituted at the last step.

## Faucet allocation is a state-machine decision

A coinbase output paying a faucet policy is a concrete mechanism. “Credit the faucet” and “burn excess runway” are not sufficient rules. Identify which outputs count as reserve, how donations affect it, who authorizes spending, what constitutes valid onboarding and what happens on recipient/policy rotation. An off-chain relay's claim does not become an objective consensus fact without a specified authenticated policy.

Two possible implementations have different obligations:

- **Fixed allocation only:** require a portion of subsidy in a specified faucet policy; a covenant governs its spending. A global automatic reserve cap is not claimed. Application-controlled burns are separate spends.
- **Consensus-accounted reserve cap:** maintain an authenticated reserve accumulator tied to an exact class of faucet outputs; update it on creation/spend, specify donation behavior and cap units, and derive the required coinbase allocation/burn from that state. This adds consensus state and policy-classification rules; ordinary covenant introspection alone does not scan the global UTXO set.

Neither is adopted here. If the desired 50/50 split remains, specify miner entitlement as R−floor(R/2) and faucet allocation as floor(R/2), or explicitly choose another odd-unit rule. Specify separately how fee burn, underclaim and capped-away allocation affect spendable supply. Do not use “months of runway” as an integer threshold until the clock and expense definition exist.

## Decisions to accept before genesis

Choose token lifecycle/identity; bootstrap clock and exact integer function; tail precision/initialization/lag/clipping; native fee burn; faucet mechanism/policy/cap; underclaim rules; and every initial parameter. Then complete the canonical MonetaryState record and genesis vectors. Reference infrastructure and v1 work can start while these choices are analyzed; a production monetary implementation must not guess them.
