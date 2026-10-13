# Issuance, clocks and rejected protocol faucet: decision-ready questions

Decision packet P06, October 9, 2026 (updated October 13, 2026). D10 economic/state choices remain **open**. D05's identity model, a token ID equal to the root of its mint scripts, was chosen by the maintainer on 2026-10-09; the lifecycle requirements below still need acceptance. D11 (protocol-level onboarding faucet and 50/50 block-subsidy split) was **rejected and removed by the maintainer on 2026-10-13**. This packet does not amend the monetary paper. It defines candidate mechanics and the evidence needed to accept them.

## Token identity recommendation

Use program-derived identity as in C15/P01: `TokenID=mint_root`, nonzero, where mint_root is a branch root over the token's mint scripts. This identifies an immutable mint policy, not a unique invocation or organization. Two issuers wanting different assets with otherwise identical code must include distinct committed constants in their programs. A script constructor should make that discriminator explicit. Holder authorization and transfer-policy preservation remain separate obligations.

A supply cap requires an authenticated cumulative state or an exclusively consumed initial allocation/authority; a stateless repeated signature check does not remember past issuance. A one-time mint requires consumption of its unique anchor, and checks the asset-specific delta. New certificates do not revoke old ones. Accept this identity model only after reviewing these lifecycle requirements; the historical outpoint-derived design must then be marked superseded rather than left as another valid interpretation.

## Tail recurrence candidate with exact integer meaning

The paper's gamma=1/2 recurrence can have an exact integer candidate, avoiding a floating-point sqrt or an approximate log interpolation. Let W_n be the exact per-block work from P04's selected target convention. Let S_n be the integer tail entitlement of block n, known before choosing that block's timestamp/nonce. After accepting block n, compute:

```text
Q = floor(S_n * S_n * W_n / W_(n-1))
S_(n+1) = min(S_max, max(S_min, isqrt(Q)))
```

This floors the unscaled recurrence once before clipping; `isqrt(floor(x))=floor(sqrt(x))` for nonnegative x. Compute the mathematical product before division with bounded sufficiently wide integers, not modular multiplication. With S≤u64 and W≤2^256, the numerator is below 2^384; intermediate width and target conventions must be reflected in the implementation contract. If sub-unit precision is desired, define a fixed-point state separately; it changes rounding behavior and needs different vectors.

Genesis must specify S_0 and W_(-1)>0 (or an explicit first-step rule). The monetary state envelope carries next_tail and previous_work plus any bootstrap state (no faucet state exists under D11's rejection). Reward lag is deliberate: current entitlement is established from prior accepted state; current work adjusts the next entitlement. Clipping and rounding make this state path-dependent and must be restored on reorg. This candidate is not identical to a direct `K*sqrt(W_n)` rule and may have rounding dead zones; analyze those before adopting it.

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

## Rejected protocol faucet and 50/50 subsidy split (D11)

Earlier drafts proposed diverting 50% of block subsidy into a protocol-level onboarding faucet with a consensus-tracked reserve cap. On 2026-10-13 the maintainer rejected D11 and removed all protocol-level faucet rules from Lotus v2:

- **Consensus simplicity and provenance:** Protocol-enforced subsidy splits require either a hardcoded coinbase policy or a consensus-accounted reserve accumulator in `StateRoot` with output-classification rules. Lotus v1 explicitly removed the Infrastructure Funding Plan (`28-ifp-removal.patch`); Lotus v2 likewise keeps base-layer issuance free of mandatory non-miner diversions.
- **Miner entitlement (`C16`):** Miners may claim up to `100%` of the block subsidy `R` (`S(h)`) plus `floor((F - T) / 2)` of remaining transaction fees after the mandatory token-output burn `T` (`C14a`), with the other half of remaining fees `G - floor(G / 2)` (`G = F - T`) burned.
- **User-space faucet covenants:** Any donor, application, or miner can deploy a voluntary onboarding faucet in user space as an ordinary covenant coin using `OUTPUTCONTINUESBRANCH` (`0xcf`), per-claim drip limits (`OUTPUTVALUE`), relative timelock rate-limiting (`CHECKSEQUENCEVERIFY`), and voucher signatures (`CHECKDATASIG`); see [rationale](../rationale.md#5-protocol-level-onboarding-faucet-and-50-50-subsidy-splits-d11).

## Decisions to accept before genesis

Choose token lifecycle/identity; bootstrap clock and exact integer function; tail precision/initialization/lag/clipping; underclaim rules; and every initial parameter. Then complete the canonical MonetaryState record and genesis vectors. Reference infrastructure and v1 work can start while these choices are analyzed; a production monetary implementation must not guess them.
