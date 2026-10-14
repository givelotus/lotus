# Issuance, clocks and rejected protocol faucet: candidate monetary mechanics

Decision packet P06, October 9, 2026 (updated October 13, 2026). **Candidate structural formulas specified for D10** (additive continuous bootstrap $B_n$ + adaptive work-responsive tail $T_n$ from Block 1, backed by the canonical 56-byte `MonetaryState` record in [P02](commitments-and-state.md)); **initial monetary constants ($R_0, T_0, T_{\min}, T_{\max}, k_{\text{boot}}$) and economic simulation calibration remain open before genesis freeze**. D05's identity model, a token ID equal to the root of its mint scripts, was chosen by the maintainer on 2026-10-09; the lifecycle requirements below still need acceptance. D11 (protocol-level onboarding faucet and 50/50 block-subsidy split) was **rejected and removed by the maintainer on 2026-10-13**. This packet does not amend the monetary paper; it defines the exact integer candidate mechanics and the simulation evidence needed to freeze their constants.

## Token identity recommendation

Use program-derived identity as in C15/P01: `TokenID=mint_root`, nonzero, where mint_root is a branch root over the token's mint scripts. This identifies an immutable mint policy, not a unique invocation or organization. Two issuers wanting different assets with otherwise identical code must include distinct committed constants in their programs. A script constructor should make that discriminator explicit. Holder authorization and transfer-policy preservation remain separate obligations.

A supply cap requires an authenticated cumulative state or an exclusively consumed initial allocation/authority; a stateless repeated signature check does not remember past issuance. A one-time mint requires consumption of its unique anchor, and checks the asset-specific delta. New certificates do not revoke old ones. Accept this identity model only after reviewing these lifecycle requirements; the historical outpoint-derived design must then be marked superseded rather than left as another valid interpretation.

## Denomination and candidate genesis scale (`1 XPI = 10^6 atoms`)

- **Denomination (`1 XPI = 10^6 atoms`, 6 decimal places):** Consensus amounts (`value:u64`, `bootstrap_reserve:u64`, `tail_subsidy:u64`) are integer **atoms** where $\text{1 XPI} = 1{,}000{,}000\text{ atoms}$ ($10^6$). Standard wallet UIs display **2 decimal places (`1.00 XPI`, like dollars and cents)** and hide the lower 4 sub-cent decimal places (`0.00_0000`) by default. Ordinary transaction fees ($\sim 200\text{--}2{,}000\text{ atoms} = 0.0002\text{--}0.0020\text{ XPI}$) therefore sit entirely inside the hidden sub-cent precision as invisible rounding dust to human users, while consensus still has $10{,}000$ integer ticks per `0.01 XPI` for smooth parabolic fee-burn accounting ([P05](resources-and-parameters.md)) and micro-stamps.
- **Candidate genesis scale ($B_0, R_0, T_0$):**
  - **Initial bootstrap subsidy ($B_0$):** $B_0 = 250{,}000\text{ XPI/block} = 250{,}000{,}000{,}000\text{ atoms/block}$ ($2.5 \times 10^{11}\text{ atoms/block}$).
  - **Total bootstrap reserve ($R_0 = M_{\text{boot}}$):** $R_0 = 2^{20} \cdot B_0 = 262{,}144{,}000{,}000\text{ XPI} = 262{,}144{,}000{,}000{,}000{,}000\text{ atoms}$ ($\approx 2.62144 \times 10^{17}\text{ atoms}$).
  - **Initial adaptive tail subsidy ($T_0$ at genesis work $W_0$):** $T_0 = 250{,}000\text{ XPI/block} = 250{,}000{,}000{,}000\text{ atoms/block}$ ($2.5 \times 10^{11}\text{ atoms/block}$), so Block 1 emits $S_1 = B_1 + T_1 = 500{,}000\text{ XPI} = 5 \times 10^{11}\text{ atoms}$, and long-run supply lives in the $\sim 5 \times 10^{11}\text{--}10^{12}\text{ XPI}$ ($5 \times 10^{17}\text{--}10^{18}\text{ atoms}$) range—providing $18\times\text{--}36\times$ headroom below `u64::MAX` ($2^{64} - 1 \approx 1.84467 \times 10^{19}\text{ atoms}$).

## Additive block subsidy from Block 1: $S_n = B_n + T_n$

Lotus v2 specifies a single smooth, **additive block subsidy** active from Block 1, with **no 4-year halving cliffs and no piecewise regime switch**:

$$S_n = B_n + T_n$$

where $B_n$ (`u64` atoms) is the height-decaying bootstrap issuance drawn from the unissued bootstrap reserve $R_n$, and $T_n$ (`u64` atoms) is the work-responsive adaptive tail subsidy. Both $R_n$ and $T_n$ are carried in the canonical 56-byte `MonetaryState` record (`bootstrap_reserve:u64 || tail_subsidy:u64 || prev_work:u256 || ema_block_cost:u64` in [P02](commitments-and-state.md)) and known before choosing block $n$'s timestamp or nonce.

### Telescoping bootstrap reserve recurrence ($R_n$, `u64` atoms)

Instead of evaluating a floating-point exponential or storing a separate fractional fixed-point accumulator, `MonetaryState` tracks the remaining unissued bootstrap reserve $R_n$ (`u64` atoms), initialized at genesis to $R_0 = M_{\text{boot}} = 2^{20} \cdot B_0 = 262{,}144{,}000{,}000{,}000{,}000\text{ atoms}$. At each block $n$, with candidate decay shift $k_{\text{boot}} = 20$ ($2^{20} = 1{,}048{,}576$ blocks $\approx 4.00$ years exponential mean lifetime $\tau$ at 2-minute blocks, matching Bitcoin's $\tau = 21\text{M}/50 = 420{,}000$ ten-minute blocks $= 4.00$ years within $0.3\%$, and continuous half-life $\tau \ln 2 \approx 2.76$ years):

$$B_n = \begin{cases} 0 & \text{if } R_n = 0 \\ \max\!\big(1,\, R_n \gg 20\big) & \text{if } R_n > 0 \end{cases}, \qquad R_{n+1} = R_n - B_n$$

This integer recurrence satisfies four foundational properties:

1. **Zero division / zero floating-point:** Every block's bootstrap emission is a pure unsigned bit-shift `R_n >> 20` (clamped to at least `1` atom while $R_n > 0$) and a checked `u64` subtraction.
2. **Exact telescoping conservation:** Because $B_n = R_n - R_{n+1}$ and $B_n \ge 1$ whenever $R_n > 0$, the sequence strictly decreases to $0$ in finite steps and telescopes to the exact atom:
   $$\sum_{n=0}^{\infty} B_n = \sum_{n=0}^{\infty} (R_n - R_{n+1}) = R_0 = M_{\text{boot}}$$
   No fractional fixed-point state is required and no rounding dust is ever lost or created; once $R_n = 0$, $B_n = 0$ permanently.
3. **Homomorphic scale invariance:** In the interior regime ($R_n \ge 2^{k_{\text{boot}}}$, $T_{\min} \le T_n \le T_{\max}$), both the bootstrap recurrence $B_n = R_n \gg k_{\text{boot}}$ and the tail recurrence $T_{n+1} = \text{isqrt}(\lfloor T_n^2 W_n / W_{n-1} \rfloor)$ are **homogeneous of degree 1 in currency units** (scaling initial parameters $R_0, T_0, T_{\min}, T_{\max} \mapsto \lambda R_0, \lambda T_0, \lambda T_{\min}, \lambda T_{\max}$ scales all block rewards by $\lambda$ up to integer floor rounding) and **homogeneous of degree 0 in work units** (rescaling $W_n \mapsto c W_n$ cancels identically in $W_n / W_{n-1}$).
4. **Long-run supply equilibrium:** Because $\sum_{n=0}^{\infty} B_n = R_0$ is strictly finite, long-run net issuance per block is governed by $\Delta M_n = T_n - \text{Burn}_n$ (where $\text{Burn}_n$ is the sum of mandatory native fee burns `B`, any coinbase underclaim `U`, and explicit `IS_BURN` `0x02` outputs under `C16`), so total circulating supply stabilizes smoothly where per-block burns match the adaptive tail $T_n$.

### Adaptive tail recurrence ($T_n$, `u64` atoms)

The paper's $\gamma = 1/2$ work-responsive tail recurrence is defined in exact integer arithmetic, avoiding floating-point `sqrt` or approximate log interpolation. Let $W_n$ be the exact 256-bit per-block chainwork (`floor(2^256 / (T + 1))`) from [P04](header-and-mining.md)'s decoded target convention, and let $T_n$ (`tail_subsidy:u64` in `MonetaryState`) be the integer tail entitlement of block $n$. After accepting block $n$, compute the post-state tail entitlement $T_{n+1}$ and work baseline $W'_n$:

```text
Q = floor(T_n * T_n * W_n / W_(n-1))
T_(n+1) = min(T_max, max(T_min, isqrt(Q)))
W'_n = W_n
```

This floors the unscaled recurrence once before clipping; `isqrt(floor(x)) = floor(sqrt(x))` for nonnegative $x$. Compute the mathematical product $T_n^2 \cdot W_n$ before division with bounded wide integers, not modular multiplication. With $T_n < 2^{64}$ and $W_n < 2^{256}$, the numerator $T_n^2 \cdot W_n < 2^{384}$ fits in 384 bits (`u384` / `u512`).

Genesis initializes $R_0 = M_{\text{boot}}$ (candidate $2^{20} \cdot B_0 = 2.62144 \times 10^{17}\text{ atoms}$), $T_0$ (candidate $2.5 \times 10^{11}\text{ atoms}$), $W_{-1} > 0$ (the genesis target's per-block work), and $E_0$ (`ema_block_cost:u64` in [P05](resources-and-parameters.md)). Reward lag is deliberate: block $n$'s subsidy entitlement $S_n = B_n + T_n$ is fixed by the parent block's `MonetaryState`, while block $n$'s target/work $W_n$ updates $T_{n+1}$ for block $n+1$. Clipping and integer rounding make `MonetaryState` path-dependent and it MUST be restored exactly on reorg. This recurrence is stateful and distinct from a memoryless $K\sqrt{W_n}$ rule; integer rounding dead zones when $\lfloor T_n^2 W_n / W_{n-1} \rfloor$ changes by less than $2 T_n + 1$ must be evaluated during parameter calibration before freezing $T_0, T_{\min}, T_{\max}$.

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

The analysis deliverable is: model/assumptions, feasible controls, honest baseline, best-response computation or a proved bound, sensitivity across miner share/discount/cost/fee regimes, and a narrowly stated conclusion. Simulations must use the exact integer ASERT and `MonetaryState` ($R_n, T_n, W_{n-1}, E_n$) recurrences specified in P04–P06, not a continuous approximation substituted at the last step.

## Rejected protocol faucet and 50/50 subsidy split (D11)

Earlier drafts proposed diverting 50% of block subsidy into a protocol-level onboarding faucet with a consensus-tracked reserve cap. On 2026-10-13 the maintainer rejected D11 and removed all protocol-level faucet rules from Lotus v2:

- **Consensus simplicity and provenance:** Protocol-enforced subsidy splits require either a hardcoded coinbase policy or a consensus-accounted reserve accumulator in `StateRoot` with output-classification rules. Lotus v1 explicitly removed the Infrastructure Funding Plan (`28-ifp-removal.patch`); Lotus v2 likewise keeps base-layer issuance free of mandatory non-miner diversions.
- **Miner entitlement (`C16`):** Miners may claim up to `100%` of the block subsidy $S_n = B_n + T_n$ plus `floor((F - T_tok) / 2)` of remaining transaction fees after the mandatory token-output burn $T_{\text{tok}}$ (`C14a`), with the other half of remaining fees `G - floor(G / 2)` (`G = F - T_tok`) burned (and `G - floor(G / 2)` additionally required to satisfy [P05](resources-and-parameters.md)'s parabolic block burn floor).
- **User-space faucet covenants:** Any donor, application, or miner can deploy a voluntary onboarding faucet in user space as an ordinary covenant coin using `OUTPUTCONTINUESBRANCH` (`0xcf`), per-claim drip limits (`OUTPUTVALUE`), relative timelock rate-limiting (`CHECKSEQUENCEVERIFY`), and voucher signatures (`CHECKDATASIG`); see [rationale](../rationale.md#5-protocol-level-onboarding-faucet-and-50-50-subsidy-splits-d11).

## Decisions to confirm by simulation before genesis freeze

Confirm token lifecycle/identity (`D05`); validate the candidate shift $k_{\text{boot}} = 20$ and initial constants $R_0 = M_{\text{boot}}$, $T_0$, $T_{\min}$, $T_{\max}$, and $W_{-1}$ against rounding dead-zone and economic simulations; and generate final genesis `MonetaryState` and `StateRoot` vectors.
