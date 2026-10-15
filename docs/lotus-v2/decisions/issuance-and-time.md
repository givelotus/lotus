# Issuance, clocks and Avalanche-controlled payouts

Decision packet P06, October 9, 2026 (updated October 14, 2026). **Candidate structural formulas specified for D10** (additive continuous bootstrap $B_n$ + adaptive work-responsive tail $T_n$ from Block 1, backed by the canonical 56-byte `MonetaryState` record in [P02](commitments-and-state.md)); **initial monetary constants ($R_0, T_0, T_{\min}, T_{\max}, k_{\text{boot}}$) and economic simulation calibration remain open before genesis freeze**. D05's identity model, a token ID equal to the root of its mint scripts, was chosen by the maintainer on 2026-10-09; the lifecycle requirements below still need acceptance. D11 now selects Avalanche-controlled payouts using Bitcoin ABC machinery (maintainer direction 2026-10-14); treasury contracts and protocol faucet state are excluded. This packet does not amend the monetary paper; it defines the exact integer candidate mechanics and the simulation evidence needed to freeze their constants.

Monetary index convention: issuance step `n >= 0` means block height `n + 1`; genesis commits the initial state without advancing any recurrence. See P02's genesis/indexing rule.

## Token identity recommendation

Use program-derived identity as in C15/P01: `TokenID=mint_root`, nonzero, where mint_root is a branch root over the token's mint scripts. This identifies an immutable mint policy, not a unique invocation or organization. Two issuers wanting different assets with otherwise identical code must include distinct committed constants in their programs. A script constructor should make that discriminator explicit. Holder authorization and transfer-policy preservation remain separate obligations.

A supply cap requires an authenticated cumulative state or an exclusively consumed initial allocation/authority; a stateless repeated signature check does not remember past issuance. A one-time mint requires consumption of its unique anchor, and checks the asset-specific delta. New certificates do not revoke old ones. Accept this identity model only after reviewing these lifecycle requirements; the historical outpoint-derived design must then be marked superseded rather than left as another valid interpretation.

## Denomination and candidate genesis scale (`1 XPI = 10^6 atoms`)

- **Denomination (`1 XPI = 10^6 atoms`, 6 decimal places):** Consensus amounts (`value:u64`, `bootstrap_reserve:u64`, `tail_subsidy:u64`) are integer **atoms** where $\text{1 XPI} = 1{,}000{,}000\text{ atoms}$ ($10^6$). Standard wallet UIs display **2 decimal places (`1.00 XPI`, like dollars and cents)** and hide the lower 4 sub-cent decimal places (`0.00_0000`) by default. Ordinary transaction fees ($\sim 200\text{--}2{,}000\text{ atoms} = 0.0002\text{--}0.0020\text{ XPI}$) therefore sit entirely inside the hidden sub-cent precision as invisible rounding dust to human users, while consensus still has $10{,}000$ integer ticks per `0.01 XPI` for smooth parabolic fee-burn accounting ([P05](resources-and-parameters.md)) and micro-stamps.
- **Candidate genesis scale ($B_0, R_0, T_0$):**
  - **Initial bootstrap subsidy ($B_0$):** $B_0 = 250{,}000\text{ XPI/block} = 250{,}000{,}000{,}000\text{ atoms/block}$ ($2.5 \times 10^{11}\text{ atoms/block}$).
  - **Total bootstrap reserve ($R_0 = M_{\text{boot}}$):** $R_0 = 2^{20} \cdot B_0 = 262{,}144{,}000{,}000\text{ XPI} = 262{,}144{,}000{,}000{,}000{,}000\text{ atoms}$ ($\approx 2.62144 \times 10^{17}\text{ atoms}$).
  - **Initial adaptive tail subsidy ($T_0$ at genesis work $W_{-1}$):** $T_0 = 250{,}000\text{ XPI/block} = 250{,}000{,}000{,}000\text{ atoms/block}$ ($2.5 \times 10^{11}\text{ atoms/block}$), so Block 1 has gross entitlement $S_0 = B_0 + T_0 = 500{,}000\text{ XPI} = 5 \times 10^{11}\text{ atoms}$ before resource deductions. The finite bootstrap reserve does not bound cumulative tail issuance or guarantee a long-run aggregate supply range; `u64` bounds each amount/state field, not the aggregate supply across blocks.

## Additive block subsidy from Block 1: $S_n = B_n + T_n$

Lotus v2 specifies a single smooth, **additive block subsidy** active from Block 1, with **no 4-year halving cliffs and no piecewise regime switch**:

$$S_n = B_n + T_n$$

where $B_n$ (`u64` atoms) is the height-decaying bootstrap issuance drawn from the unissued bootstrap reserve $R_n$, and $T_n$ (`u64` atoms) is the work-responsive adaptive tail subsidy. Both $R_n$ and $T_n$ are carried in the canonical 56-byte `MonetaryState` record (`bootstrap_reserve:u64 || tail_subsidy:u64 || prev_work:u256 || ema_block_cost:u64` in [P02](commitments-and-state.md)) and known before choosing issuance step $n$'s timestamp or nonce.

### Telescoping bootstrap reserve recurrence ($R_n$, `u64` atoms)

Instead of evaluating a floating-point exponential or storing a separate fractional fixed-point accumulator, `MonetaryState` tracks the remaining unissued bootstrap reserve $R_n$ (`u64` atoms), initialized at genesis to $R_0 = M_{\text{boot}} = 2^{20} \cdot B_0 = 262{,}144{,}000{,}000{,}000{,}000\text{ atoms}$. At each issuance step $n$, with candidate decay shift $k_{\text{boot}} = 20$ ($2^{20} = 1{,}048{,}576$ blocks $\approx 4.00$ years exponential mean lifetime $\tau$ at 2-minute blocks, matching Bitcoin's $\tau = 21\text{M}/50 = 420{,}000$ ten-minute blocks $= 4.00$ years within $0.3\%$, and continuous half-life $\tau \ln 2 \approx 2.76$ years):

$$B_n = \begin{cases} 0 & \text{if } R_n = 0 \\ \max\!\big(1,\, R_n \gg 20\big) & \text{if } R_n > 0 \end{cases}, \qquad R_{n+1} = R_n - B_n$$

This integer recurrence satisfies four foundational properties:

1. **Zero division / zero floating-point:** Every block's bootstrap emission is a pure unsigned bit-shift `R_n >> 20` (clamped to at least `1` atom while $R_n > 0$) and a checked `u64` subtraction.
2. **Exact telescoping conservation:** Because $B_n = R_n - R_{n+1}$ and $B_n \ge 1$ whenever $R_n > 0$, the sequence strictly decreases to $0$ in finite steps and telescopes to the exact atom:
   $$\sum_{n=0}^{\infty} B_n = \sum_{n=0}^{\infty} (R_n - R_{n+1}) = R_0 = M_{\text{boot}}$$
   No fractional fixed-point state is required and no rounding dust is ever lost or created; once $R_n = 0$, $B_n = 0$ permanently.
3. **Homomorphic scale invariance:** In the interior regime ($R_n \ge 2^{k_{\text{boot}}}$, $T_{\min} \le T_n \le T_{\max}$), both the bootstrap recurrence $B_n = R_n \gg k_{\text{boot}}$ and the absolute tail $T_{n+1} = \text{isqrt}(\lfloor T_g^2 W_n / W_g \rfloor)$ are **homogeneous of degree 1 in currency units** (scaling initial parameters $R_0, T_0, T_{\min}, T_{\max} \mapsto \lambda R_0, \lambda T_0, \lambda T_{\min}, \lambda T_{\max}$ scales all block rewards by $\lambda$ up to integer floor rounding) and **homogeneous of degree 0 in work units** (rescaling $W_n \mapsto c W_n$ cancels identically in $W_n / W_g$).
4. **Long-run supply equilibrium:** Because $\sum_{n=0}^{\infty} B_n = R_0$ is strictly finite, long-run net issuance per block is governed by $\Delta M_n = T_n - \text{Burn}_n$ (where $\text{Burn}_n$ is the sum of mandatory native fee burns `B`, any coinbase underclaim `U`, and explicit `IS_BURN` outputs under `C16`), so total circulating supply stabilizes smoothly where per-block burns match the adaptive tail $T_n$.

### Absolute adaptive tail (adopted October 15, 2026)

The maintainer authorized the genesis-anchored formula after the [absolute reward review](../../plans/lotus-v2-absolute-reward-research.md). This supersedes the recurrent tail formula; bootstrap scheduling, genesis native issuance (zero), fee/burn accounting and the one-block lag retain their defined rules. This selects a formula, not numerical mainnet constants or economic acceptance.

Immutable profile parameters are `genesis_tail` ($T_g$, an in-range `u64` amount) and `genesis_work` ($W_g$, positive `u256` per-block work from the genesis target). Define version 1:

```text
F(work) = min(T_max, max(T_min, isqrt((T_g * T_g * work) // W_g)))
T_n = F(W_(n-1))
S_n = B_n + T_n
T_(n+1) = F(W_n)
```

For issuance step `n` (height `n+1`), derive `W_(n-1)` from the authenticated parent header target. The current candidate's validated target gives `W_n`; it affects the next payment. A cached parent tail is never the formula input, and the parent is never substituted for a missing genesis anchor. At height 1, `F(W_g)=T_g` exactly.

Calculate the numerator as a checked mathematical `u384` integer, divide with floor rounding, then apply exact integer square root. Clamp the possibly wider-than-u64 result before narrowing to `u64`. Require `0 < W_g <= 2^256-1`, positive input work, and `T_min <= T_g <= T_max <= 2^64-1`. Zero work/anchors are invalid. Bind anchors and formula version 1 into the validation profile digest and manifest identity. Changing either anchor or formula requires explicit profile migration; incompatible existing homes fail closed and are not reset automatically.

Retain the 56-byte monetary envelope for this adoption. `tail_subsidy` and `prev_work` are checked redundancy: accepted parent state must have `prev_work` equal to authenticated parent work and `tail_subsidy == F(parent_work)`. Post-state stores `F(W_n)` and `W_n`. Reserve, EMA and UTXO transitions still require exact branch restoration on reorg; tail can be recomputed from the new authenticated parent. Schema removal is a separate decision.

Rounding and clipping differ from the superseded recurrence. With anchors 100/10, works 11 then 10 yield absolute tails 104 then 100, while the recurrence yields 104 then 99. With upper bound 150, works 40 then 10 yield absolute 150 then 100 versus recurrent 150 then75. With anchors 100/4 and lower bound 80, works 1 then 4 yield absolute 80 then 100 versus recurrent 80 then 160. Absolute evaluation removes terminal-tail history dependence; cumulative issuance still depends on work history.

The toy development fixture explicitly uses anchors 200/9. The independently tested private manifest uses 1000000/2. These are separate profiles and neither selects a mainnet anchor. Native manifest schema 2 explicitly records formula version 1 and both anchors; schema 1 is rejected. Simulation must use these exact integer rules with P04 ASERT and P05 accounting before constants are frozen.

## Bootstrap clock comparison and why height-based telescoping was selected

| Choice | Deterministic implementation requirement | Incentive and conservation behavior |
| --- | --- | --- |
| **Height-based telescoping reserve (selected candidate)** | `B_n = max(1, R_n >> 20)` when `R_n > 0`, `R_{n+1} = R_n - B_n` (`u64` state) | Exact conservation $\sum B_n = R_0$; zero direct reward from manipulating block timestamps; pure integer bit-shift |
| Current-header timestamp decay | Exact function of time and origin, overflow/large-gap bounds | A smaller permitted timestamp can increase current reward while moving future difficulty costs to later miners; does not telescope without separate cap |
| Parent-derived timestamp decay | Exact lag and ancestor definition | Removes the current miner's direct control of its own decay input, but does not prove honest timestamps or eliminate influence on future rewards |

The height-based telescoping reserve recurrence is selected as the candidate rule because it guarantees exact conservation ($\sum_{n=0}^{\infty} B_n = R_0$), requires only a single `u64` word (`bootstrap_reserve`) in `MonetaryState`, and prevents miners from directly inflating their current block's bootstrap emission by manipulating timestamps.

## Timestamp incentive objective and limits

The stated goal is a miner preferring a fresh, accurate timestamp at discovery. Use expected discounted profit for a miner able to vary hash allocation as the principal objective; also report the fixed-share special case. Include native reward, collectible fees, costs, orphan/eligibility risk, withheld blocks, timestamp granularity, and how later difficulty/reward effects accrue to that miner. Quantify the deviation benefit against honest-clock reporting over the same feasible history and horizon.

A narrow information limitation is already clear: chain bytes alone do not reveal the physical discovery time. The same valid header history can be observed after different real-time discovery/delivery histories. Thus a deterministic function of those bytes cannot *certify* exact discovery time. This does not prove approximate truthful incentives impossible under a specified network/clock model; it explains why such a claim needs assumptions beyond the reward equation.

Do not optimize reward/work over arbitrary independent difficulties. Difficulty is a function of permitted ancestor timestamps and the exact ASERT algorithm. Compare feasible timestamp histories and complete discounted outcomes. Current reward may depend on current/parent state while future work/reward effects accrue partly to other miners. A mobile miner's incentives cannot be inferred from a permanent 100%-share miner or a fixed-hashrate Jensen bound.

The analysis deliverable is: model/assumptions, feasible controls, honest baseline, best-response computation or a proved bound, sensitivity across miner share/discount/cost/fee regimes, and a narrowly stated conclusion. Simulations must use the exact integer ASERT and bootstrap/EMA recurrences and absolute tail with checked `MonetaryState` ($R_n, T_n, W_{n-1}, E_n$) specified in P04–P06, not a continuous approximation substituted at the last step.

## Avalanche-controlled payouts (D11)

Maintainer direction, October 14, 2026: select Avalanche-controlled coinbase payouts using Bitcoin ABC's existing machinery. Treasury covenants, genesis vesting contracts, controller singleton coins and on-chain treasury roots are removed from this proposal. There is no protocol faucet balance or treasury field in `MonetaryState`.

The earlier payout review checked Bitcoin ABC `8c67fe1e85a602204a2ce65aa3b643469c2c3a1d`; the current V2 integration base is `1fb7db17c176cdea8a2c60d887891589382ee4e3`. The reviewed integration points are:

- `src/avalanche/processor.*` and `StakeContenderCache`: select staking-reward winners relative to the parent block.
- `src/node/miner.cpp`: obtain `getStakingRewardWinners(parent_hash, winners)` and construct the payout to the first returned script.
- `src/policy/block/stakingrewards.cpp`: `StakingRewardsPolicy`, a `ParkingPolicy`, accepts a sufficiently funded output to any returned winner. If staking rewards are disabled or winners are unavailable, it returns success without requiring a payout. `GetStakingRewardsAmount` currently computes 10% of the supplied block reward, rounded down.

These are reusable source mechanisms, not proof that V2 payouts are implemented. In particular, the existing policy does **not** implement a fixed 50% treasury share, arbitrary governance-selected charity address, or a mandatory pay-or-burn fallback. V2 selects this winner-based payout mechanism; the payout fraction, activation, quorum parameters and adaptation from upstream scripts to V2 output policies remain named integration choices before launch. Do not silently import an eCash fee/subsidy formula: the amount available for distribution is C16's `S + floor(G/2) - U_required`, after all mandatory resource deductions. Any payout is carved from that amount, never added to it. The default candidate follows the existing 10% helper over that distributable amount; the final value must be recorded in the network profile.

Winner selection and parking remain Avalanche coordination policy. They do not become inputs to deterministic block validation, the UTXO/monetary state root, or historical replay. Nodes may have different live polling knowledge; adding a hard-consensus requirement based on that local knowledge would not define a reproducible validity function. C16 independently enforces total issuance and burns. The October 15 maintainer decision selects the pinned Bitcoin ABC Avalanche/PoW chain-selection behavior and defaults, as recorded in P04. This supersedes the earlier advisory-only greatest-work proposal; V2 integration and its behavioral tests remain pending.

Reward and voting weights remain linear in admitted stake. Use a bounded active-proof table (`AVALANCHE_MAX_ACTIVE_PROOFS`) to bound operational resources; admission/eviction must be tested separately. Linearity alone does not make a top-K admission rule pooling-neutral or prove quorum security. Reuse upstream proof validation, conflict handling and winner tests, then add V2 tests for absent winners, alternative winners, restart/replay, reorgs, fee burns and coinbase resource deductions.

## Decisions to confirm before genesis freeze

Confirm token lifecycle/identity (`D05`), the Avalanche payout integration/network profile, bootstrap shift and initial monetary parameters, exact integer economic simulations, and independent genesis/first-block/undo vectors. Treasury contracts are not an open architecture alternative.

## Economic interpretation and burn-demand appendix (non-consensus)

Let $A_n$ be the **actual** external-currency budget spent on verifiable native burns during an interval and $P_n>0$ the market price in that currency per XPI. The corresponding purchased-and-burned amount is $A_n/P_n$ XPI, subject to atom rounding and transaction costs. A falling $P_n$ raises the coin-denominated burn **only if** the budget and access to XPI persist. Adoption, attention value, and budgets may fall with price; a demand collapse can reduce $A_n$ faster than $P_n$, eliminating the proposed negative feedback. Neither $A_n$ nor $P_n$ is a consensus input or an observed control target.

For the candidate tail held at $250{,}000$ XPI per 120-second block, 365 days contain 262,800 target-spaced blocks and tail issuance is $65.7$ billion XPI/year. After bootstrap emission becomes negligible, balancing **that tail alone** with voluntary burns at a reference price of $1/XPI would require about $65.7$ billion/year of external burn spending if fees, other burns, underclaims, and tail variation are ignored. This is a steady-supply scenario, not a launch assumption, price peg, guaranteed burn budget, or aggregate supply bound. Actual blocks are stochastic and the tail responds to work.

Count native supply destruction once under [C16](../consensus.md): $\Delta M_n=S_n-B-U-\text{Burn\_explicit}$, where $B$ includes C14a's token-output burn and the mandatory share of remaining native fees, $U$ is coinbase underclaim (including required resource deductions), and $\text{Burn\_explicit}$ is native `IS_BURN` output value. Fees paid to miners, including optional tips, are transfers and are excluded from burn demand; do not add the fee amount to issuance or count an explicit burn output again as a fee. A CashWeb-style proof of payment can verify a message-linked native `IS_BURN` output and reuse its on-chain burn as an application receipt. The application decides access and receipt reuse; it adds no consensus burn rule or second monetary sink.

The adaptive PoW paper's local stability result concerns a linearized equilibrium under persistent fiat budgets, immediate hashrate adjustment, an assumed price-response coefficient and inactive clipping. It does not establish those assumptions for V2 or prove convergence to a chosen fiat price. Before fixing genesis constants, simulate adoption and budget persistence, price elasticity, mining adjustment lag, energy and hardware cost changes, clipping and atom rounding, correlated demand/price/work shocks, and miner security payout after burns and resource underclaim. Report supply paths and security expenditure as conditional outcomes, including a cold start with little or no application burn.

Paper provenance for this interpretation (read-only local sources, SHA-256 of `main.tex` on 2026-10-14): *Adaptive PoW Monetary Policy Without Oracles: A Constructive Mechanism for Pseudo-Stability via Work-Coupled Tail Emission and Burn*, `60f845adc6b3645722e97cad3b7f8e315cc557d4ab4b27f851eba0770ef4dacd`; *CashWeb: A Cryptocurrency-Integrated Protocol for Federated Anti-Spam Messaging and Publish-Subscribe Systems*, `29b71351f2a6558d721b90cc44fafb59bca4c19a7d3db5b928112d4cb08a79e4`. The monetary paper writes an aggregate expectation with a fee term; C16 above is V2's normative transfer/burn accounting. Its CashWeb citation describes an application proof-of-payment construction using an unspendable output; V2 uses `IS_BURN` for the corresponding native receipt.
