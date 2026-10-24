# Issuance, clocks and Avalanche-controlled payouts

Decision packet P06. **Candidate structural formulas specified for D10** (additive continuous bootstrap $B_n$ + adaptive work-responsive tail $T_n$ from Block 1, backed by the canonical 56-byte `MonetaryState` record in [P02](commitments-and-state.md)); **initial monetary constants ($R_0, T_0, T_{\min}, T_{\max}, k_{\text{boot}}$) and economic simulation calibration remain open before genesis freeze**. D05's identity model is selected: a token ID equals the root of its mint scripts; the lifecycle requirements below still need acceptance. D11 selects Avalanche-controlled payouts using Bitcoin ABC machinery; treasury contracts and protocol faucet state are excluded. This packet does not amend the monetary paper; it defines the exact integer candidate mechanics and the simulation evidence needed to freeze their constants.

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

### Absolute adaptive tail

The genesis-anchored formula is the candidate tail rule; its derivation is in the [absolute reward review](../../plans/lotus-v2-absolute-reward-research.md). It supersedes the recurrent tail formula; bootstrap scheduling, genesis native issuance (zero), fee/burn accounting and the one-block lag retain their defined rules. This selects a formula, not numerical mainnet constants or economic acceptance.

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

Coinbase payouts are Avalanche-controlled, using Bitcoin ABC's existing soft block-parking machinery (`ConnectTip` `ParkingPolicy`), extended to a **three-way coinbase split** (`~50% Miner / ~25% Staker Winner / ~25% Staker-Voted Treasury Winner`, exact ratios configurable in the network profile). Hard consensus treasury covenants, genesis vesting contracts, controller singleton coins and on-chain treasury state roots remain excluded; there is no protocol faucet balance or treasury field in `MonetaryState`.

The reviewed and planned integration points ([bulk pre-consensus & overlay plan](../../plans/lotus-v2-bulk-preconsensus-and-mempool-overlays.md)) are:

- **Staker reward winner (`MSG_AVA_STAKE_CONTENDER`, target `~25%` share):** `src/avalanche/processor.*` and `StakeContenderCache` select staking-reward winners relative to the parent block (`StakeContenderId = H(prevblockhash, proofid)`). `StakingRewardsPolicy` (`src/policy/block/stakingrewards.cpp`) verifies that `vtx[0]` pays at least `STAKER_REWARD_RATIO` (default `25%`, configurable) of the net claimable block reward to a finalized winner.
- **Staker-voted treasury payout script (`MSG_AVA_TREASURY_CONTENDER`, target `~25%` share):** Instead of the legacy hardcoded `MinerFundPolicy` whitelist (`src/minerfund.cpp`), `TreasuryContenderCache` (`src/avalanche/treasurycontendercache.*`) and `TreasuryPolicy` (`src/policy/block/treasurypolicy.*`) poll staker-endorsed treasury payout scripts via `MSG_AVA_TREASURY_CONTENDER` (`TreasuryContenderId = H(prevblockhash, payout_script_hash)`, resolved via `getdata(MSG_AVA_TREASURY_CONTENDER)` $\to$ `avatreasury` when unknown). `TreasuryPolicy` verifies that `vtx[0]` pays at least `TREASURY_REWARD_RATIO` (default `25%`, configurable) of the net claimable block reward to the finalized treasury script.
- **Miner share (target `~50%` share):** `BuildV2CoinbaseTx` (`src/node/miner.cpp`) allocates the remaining net claimable block reward (`100% - STAKER_REWARD_RATIO - TREASURY_REWARD_RATIO`, default `50%`) to the PoW miner's `scriptPubKeyIn` in `vtx[0]->vout[0]`. If staking or treasury winners are disabled or not yet finalized for `prevblockhash`, the corresponding policy returns `true` without parking the block and the unallocated share accrues to the miner.
- **Net claimable reward basis (`C16` / `P05`):** The amount available for the `50% / 25% / 25%` split is strictly the net claimable coinbase reward after mandatory `P05` fee-burn floor deductions (`S_n + total_claimable_fees - max(0, required_burn_floor - explicit_burns)`). Payouts are carved from that net amount, never added to `S_n`.

Winner selection, treasury script voting, and pre-consensus template enforcement (`PreConsensusPolicy`, `MSG_AVA_MEMPOOL_BATCH`) remain **Avalanche soft block-parking policies** in `Chainstate::ConnectTip` (`ParkBlock` / `UnparkBlock`), never hard consensus rules. They do not become inputs to deterministic block validation, `UtxoRoot`, `MonetaryState`, or historical IBD replay. Because all three payouts (`Miner`, `Staker`, `Treasury`) are outputs of `vtx[0]` (`CoinbaseTx`), and `vtx[0]`'s outputs are pipelined into `UtxoRoot` in Block $h+1$ ([P02](commitments-and-state.md)), adding the staker and treasury outputs to `vtx[0]` changes zero bytes of `Subtree A` or `UtxoRoot` in finalized pre-consensus mempool overlays $L_k$, and peers receiving a transaction-free `tmplblock` (`Header || CoinbaseTx`) verify both `StakingRewardsPolicy` and `TreasuryPolicy` directly from `tmplblock.coinbase_tx` before connecting the block.

Reward and voting weights remain linear in admitted stake. Use a bounded active-proof table (`AVALANCHE_MAX_ACTIVE_PROOFS`) to bound operational resources; admission/eviction must be tested separately. Linearity alone does not make a top-K admission rule pooling-neutral or prove quorum security. Reuse upstream proof validation, conflict handling and winner tests, then add V2 tests for absent winners, alternative winners, staker-voted treasury rotation, restart/replay, reorgs, fee burns and coinbase resource deductions.

## Decisions to confirm before genesis freeze

Confirm token lifecycle/identity (`D05`), the Avalanche payout integration/network profile, bootstrap shift and initial monetary parameters, exact integer economic simulations, and independent genesis/first-block/undo vectors. Treasury contracts are not an open architecture alternative.

## Economic interpretation (non-consensus)

How external burn demand, price and the work-responsive tail might interact is analysed in [research/burn-demand-economics.md](../research/burn-demand-economics.md). That analysis is conditional and selects no constant, peg or supply bound; [C16](../consensus.md) is the normative transfer/burn accounting.
