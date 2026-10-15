# Absolute evaluation of the V2 tail reward

Research date: 2026-10-15. Specification baseline: `8914db5177d7b97fa7aa7d04172f71ead633775c`. This report evaluates [issue 22](https://github.com/givelotus/lotus/issues/22); it changes no consensus rule, source implementation, launch parameter, or published artifact. D10–D14 remain open for their recorded calibration, integration, and acceptance requirements.

**Recommendation:** prefer the genesis-anchored absolute work formula for the next monetary-policy review. Keep the existing one-block reward lag, constant clamp bounds, bootstrap rule, fee accounting, and state commitment while reviewing that change. Adopt it only through an explicit subsequent decision and corresponding specification/vector changes. The current candidate remains the recurrence in P06.

The absolute formula is practical and preserves the intended square-root response to work. Its principal benefit is that an earlier clamp or rounding event cannot permanently alter the reward associated with a given work level. It also makes the tail computable from one validated parent header and immutable genesis parameters. It does **not** prescribe future issuance by date or height, eliminate the UTXO/EMA state commitment, or establish timestamp honesty or price stability.

## Evidence and terminology

The full issue body and comments were fetched read-only with `gh issue view 22 --repo givelotus/lotus --json number,title,body,comments,url,state,updatedAt`. At retrieval the ticket was OPEN, updated `2026-10-15T14:59:03Z`, with zero comments. Its requested comparison is between the paper's recurrence and an absolute evaluation from genesis; bootstrap is outside its requested change. It expressly requests analysis without a patch or launch-constant selection. [Issue 22](https://github.com/givelotus/lotus/issues/22)

Primary local sources, all read without modification:

- [Consensus C16, C25–C28](../lotus-v2/consensus.md) and the [decision register](../lotus-v2/decisions.md).
- [P01: encoding, coinbase and clocks](../lotus-v2/decisions/encoding-and-signatures.md), [P02: state commitments and indexing](../lotus-v2/decisions/commitments-and-state.md), and [P03: VM semantics](../lotus-v2/decisions/vm-semantics.md). Reward calculation is a block-validation rule; it does not require a new script opcode or block-context introspection.
- [P04: headers, target/work and ASERT](../lotus-v2/decisions/header-and-mining.md), [P05: costs and EMA](../lotus-v2/decisions/resources-and-parameters.md), and [P06: issuance](../lotus-v2/decisions/issuance-and-time.md).
- *Adaptive PoW Monetary Policy Without Oracles*, Version 1.1, local source `/Users/shammah/repos/latex/papers/adaptive-pow-monetary-policy/main.tex`; SHA-256 `60f845adc6b3645722e97cad3b7f8e315cc557d4ab4b27f851eba0770ef4dacd`. This matches the source provenance in [V2 rationale](../lotus-v2/rationale.md). Relevant sections are “Sublinear homomorphic update,” “Manipulation resistance of the work ratio signal,” “Formal Stability Analysis under Linearized Dynamics,” and “Implementation Notes.” The paper's `R^tail` is this report's `T`; its PoW target `T` is this report's `D`.

The derivations, counterexamples, design alternatives, and recommendation below are this review's analysis. They are not additional claims made by the issue or accepted specifications.

Use the specification's issuance index: step `n >= 0` is block height `n+1`. Let `D_n` be that block's decoded PoW target and `W_n = floor(2^256 / (D_n+1))` its **per-block** work. `W_g = W_-1 > 0` is genesis work. `T_g = T_0` is the selected genesis tail in atoms. `R_n` denotes the separate remaining bootstrap reserve. `clip(x) = min(T_max, max(T_min, x))`, with constant bounds and `0 < T_min <= T_g <= T_max`. No numerical launch bounds are selected here.

## A precise absolute construction

The paper defines, in its own notation:

```text
R_(n+1)^tail = clip(R_n^tail * (W_n / W_(n-1))^gamma, R_min, R_max)
```

P06's precise integer realization at `gamma = 1/2` is:

```text
recursive_next = clip(isqrt((T_n * T_n * W_n) // W_(n-1)))
```

The alternative under review is:

```text
F(work) = clip(isqrt((T_g * T_g * work) // W_g))
T_n_absolute = F(W_(n-1))
S_n_absolute = B_n + T_n_absolute
```

For height 1, the parent is genesis, so `F(W_g) = T_g` exactly. For height `h > 1`, decode the validated parent header's target, calculate its per-block work, and evaluate `F`. Equivalently, after step `n`, calculate the next entitlement as `F(W_n)`. The previous reward is never an input. A node may cache this value, but it is derived data.

This retains the candidate's lag: the block pays a tail determined by its parent's work, while its own work determines the next block's tail. Choosing `F(W_n)` for the reward paid **in** step `n` is a separate timing change. P04 derives the current required target from the parent, so even that alternative would not directly depend on the current timestamp, but it changes rewards during difficulty transitions and needs separate evaluation. There is no reason to combine that decision with issue 22.

Use mathematical wide arithmetic. `T_g < 2^64` and `W < 2^256` imply a numerator below `2^384`; the quotient and square root must remain wide until clipping, then narrow to `u64`. Do not narrow the unclipped square root first, use floating point, or approximate the ratio before multiplication. `isqrt(floor(x)) = floor(sqrt(x))` for nonnegative `x`. `W_g` is a fixed positive denominator, with no dynamic divide-by-zero possibility.

Units are consistent: `(atoms)^2 * work/work` has units `atoms^2`, and its square root has units atoms. Equivalently the ideal formula is `K sqrt(W)` with `K = T_g/sqrt(W_g)`, but the two-integer anchor avoids representing an irrational `K`. Monetary denomination remains `1 XPI = 10^6 atoms`. Exact common rescaling of all work quantities cancels; replacing the specified floored work with another difficulty convention is nevertheless a consensus change.

## Equality, rounding, and clipping

Without clipping or rounding, adjacent work ratios telescope:

```text
T_N = T_g * product[i=0..N-1] sqrt(W_i / W_(i-1))
    = T_g * sqrt(W_(N-1) / W_g).
```

Thus the absolute formula is an exact re-evaluation of the same ideal curve. The actual integer/clipped recurrence is a different policy because it feeds each rounded and clipped result into the next step.

The following are arithmetic examples, not claimed feasible one-block ASERT histories. Bounds and small numbers are chosen only to expose behavior; they are not network parameters. Every row below was reproduced by the Python listing at the end.

| Case | Initial tail/work; work sequence | Recurrence tails | Absolute tails |
| --- | --- | --- | --- |
| Exact interior cancellation | `100 / 10`; `40, 90, 10` | `200, 300, 100` | `200, 300, 100` |
| Upper clamp, then original work | `100 / 10`; `40, 10`; maximum `150` | `150, 75` | `150, 100` |
| Lower clamp, then original work | `100 / 4`; `1, 4`; minimum `80` | `80, 160` | `80, 100` |
| Rounding without clipping | `100 / 10`; `11, 10` | `104, 99` | `104, 100` |

In the upper-clamp case, the recurrence discards the growth from 150 to 200 and then halves the retained 150. At work 10 thereafter, its tail stays 75 forever unless work changes again. In the lower-clamp case, it retains 80 instead of the unconstrained 50, then doubles that retained amount to 160. Absolute evaluation returns to 100 in both cases. A clamp can therefore create a persistent downward **or upward** normalization offset in the recurrence.

There is a real saturation tradeoff. Absolute evaluation remains at the upper bound while work stays above its genesis-defined threshold; a small work decline in that region can leave its reward unchanged. The recurrence can leave its upper bound immediately on a work decline, because it scales the already-clipped value. The corresponding statement holds at the lower bound. Absolute evaluation preserves the curve's normalization; it does not preserve every response of the clipped controller.

Rounding also accumulates. With no active clamp, write each step as

```text
T_(i+1) = T_i sqrt(W_i/W_(i-1)) - epsilon_i,  0 <= epsilon_i < 1.
T_N / sqrt(W_(N-1))
    = T_g / sqrt(W_g) - sum[i=0..N-1] epsilon_i / sqrt(W_i).
```

The work-normalized reward can only drift downward from rounding in this regime. The recurrence is at most the once-rounded absolute result for the same terminal work, but their difference is not bounded by one atom over the entire history. A later work increase can amplify an earlier absolute error. Constant work itself creates no new loss: `isqrt(T_n^2) = T_n` for integer `T_n`.

At the existing candidate starting scale `T_g = 250,000,000,000` atoms, repeating work `10 -> 11 -> 10` 1,000 times ends at `249,999,999,000` under the recurrence and `250,000,000,000` under absolute evaluation. The 1,000-atom difference is only `0.001 XPI`; this demonstrates accumulation, not economic significance or a profitable attack. Whether rounding matters over realistic work histories requires exact-target simulation.

## What “absolute schedule” can mean

The recommended candidate is an **absolute work curve**, not a predetermined chronological issuance schedule. Future difficulties, block arrival times, fees, burns, and underclaims remain unknown.

| Construction | Concrete form | What it achieves and changes |
| --- | --- | --- |
| Genesis-anchored per-block work | `T_n = F(W_(n-1))` above | Preserves the ideal square-root work response and existing lag. Same parent work gives the same tail on every branch. Recommended for review. |
| Direct target ratio | `clip(isqrt(floor(T_g^2 * (D_g+1)/(D_parent+1))))` | A plausible inverse-target curve, but generally differs from the ratio of separately floored `W` values. Using `D_g/D_parent` also omits the `+1`. Neither is an exact rewrite of the candidate integer-work convention. |
| Height-only tail | `T_n = T_g`, or a specified integer function `f(n)` | A fixed amount per height requires no reward state. It deliberately removes adaptive work coupling; constant perpetual tail is the simplest such alternative. It does not fix issuance per wall-clock year. |
| Time-only tail | `T_n = f(MTP(parent))`, or `f(header.time)` | Defines a calendar-indexed per-block amount using a chain clock, not an observed physical discovery time. Different block counts still produce different total issuance over an interval. Current-header time permits direct control over one's own reward input. |
| Cumulative calendar allowance | `S_n = C(c_n)-C(c_(n-1))`, for a nondecreasing chain clock `c` and integer cumulative allowance `C` | Telescopes issuance to the allowance released by that clock. Requires exact clock/lag rules and gap handling; can concentrate a long interval's allowance into one block and changes mining incentives. This is a substantially different policy. |
| Cumulative-chainwork curve | For example `T_n = clip(isqrt(floor(T_g^2 * A_parent/A_g)))`, with `A` accumulated chainwork | Even at unchanged difficulty, accumulated work grows every block, so the tail grows roughly as the square root of height until capped. It is not the paper's response to per-block work. Header ancestry or an authenticated cumulative-work value is required. |

For a genuine known-height bootstrap schedule there are two distinct choices:

1. **Keep P06 exactly.** The current `R_n` recurrence is already a deterministic function of `n`, `R_0`, and `k_boot`; it does not depend on work, time, transactions, or underclaims. Equal-height forks have the same reserve. A node can derive it by replay or cache it. Removing its commitment is possible as a separate design choice, but naively calculating it from scratch costs `O(n)`. It is not equal to simply rounding a real exponential once.
2. **Select a new cumulative schedule.** Choose an exactly defined nonincreasing integer remainder `G(n)` with `G(0)=R_0` and eventual zero, then set `B_n=G(n)-G(n+1)`. This proves `sum B_n=R_0` without a mutable reserve. For example, `G(n)=floor(R_0*((q-1)/q)^n)` gives an absolute geometric schedule, but direct arbitrary-precision powers grow with `n`; a bounded exact evaluator or an explicitly different fixed-precision schedule must be specified before adoption. Zero-payout steps can occur near exhaustion. A finite polynomial alternative, `G(n)=floor(R_0*max(N-n,0)^p/N^p)` for fixed positive integer `p`, is straightforward to bound and evaluate, but changes the decay shape and requires selection of `N,p`.

For a small counterexample to treating those bootstrap forms as identical, take `R_0=10`, `k_boot=2`. The recurrence's first post-state is `10-floor(10/4)=8`; an absolute geometric remainder is `floor(10*3/4)=7`. Neither an exponential schedule nor removing reserve storage is required to adopt the absolute **tail**.

Actual circulating supply remains governed by C16:

```text
Delta M_n = S_n - B_fee,n - U_n - Burn_explicit,n.
```

The miner-paid fee share transfers existing coins; it is not issuance. Scheduled entitlement and claimed/spendable supply must not be conflated. The tail must never be inferred from the previous coinbase payout, which can include fees, redistribution, explicit burns, and voluntary or required underclaims.

## State commitments, verification, and reorganizations

The existing P04 header is 134 bytes and contains one 32-byte `state_root`. It does **not** contain separate wire fields for reserve, tail, previous work, or EMA. P02 hashes the UTXO root together with the canonical 56-byte monetary envelope:

```text
bootstrap_reserve:u64 || tail_subsidy:u64 || prev_work:u256 || ema_block_cost:u64
```

| Value | After absolute tail evaluation | Commitment/storage implication |
| --- | --- | --- |
| `tail_subsidy` (8 bytes) | Derived from the validated parent target and genesis anchor | No independent consensus state is needed. Keeping a checked redundant field/cache is possible; removing it changes P02's schema and roots. |
| `prev_work` (32 bytes) | Unneeded as reward recurrence state; work remains needed for PoW/chain selection | Already derivable from the header at the state being committed, even for the existing recurrence. Removing this redundancy is a separate schema cleanup, not a novel benefit exclusive to absolute rewards. |
| `bootstrap_reserve` (8 bytes) | Current recurrence still used | Keep for efficient continuation and snapshot validation unless a separate height-derivation contract is accepted. |
| `ema_block_cost` (8 bytes) | Still evolves from historical block accounting costs | Cannot be recovered from the latest target/height. Keep authenticated state or require replay/proof of the necessary historical transitions. |
| `UtxoRoot` | Still represents all unspent coins and their consensus metadata | Remains necessary for the selected UTXO commitment/proof/snapshot design. |

A deliberate reduced envelope could therefore be 16 bytes (`reserve || EMA`) rather than 56, or 8 bytes if the reserve is also derived under an accepted rule. The header would **still be 134 bytes**. Savings would be in the envelope, proofs, snapshot metadata, and associated hashing, not 40 bytes per header. Omitting all monetary commitments while retaining an EMA that affects future validity would need a different snapshot/verification contract; this report does not recommend that change.

Even the current tail recurrence can be reconstructed from the header history and initial parameters. A header commitment is not required merely to make a deterministic recurrence executable. Its practical role is to authenticate a continuation state without replaying all inputs, alongside the UTXO map. Conversely, an absolute tail does not make a header-only client capable of checking transaction validity, resource costs, or the state root. PoW inclusion is not proof of correct transition execution.

On a reorganization, the current recurrence must restore the exact old tail before applying the new branch; its rounded/clipped mapping cannot generally be inverted. The absolute formula needs no tail undo: recompute from the new parent. Reserve/EMA/UTXO undo and validated target ancestry are still required. Two forks of equal height and equal latest work have the same absolute next tail, but can have different current recurrence tails, EMA values, UTXOs, and cumulative issuance. Absolute evaluation removes terminal-tail path dependence; the sum of rewards along different work histories remains path dependent.

At genesis, require an explicit positive work anchor and an in-range tail anchor; the absolute first payment then agrees with the current initialization. A later change of the anchor redefines the monetary curve and cannot be treated as an implementation optimization. P01's coinbase identity, zero genesis issuance, resource deductions, and P02's no-current-block-hash dependency order remain relevant under either formula.

## Work shocks and mining incentives

For an interior permanent fourfold work increase, both ideal rules eventually double the tail. With the retained lag, the first high-work block still receives the old entitlement; the following block receives the adjusted amount. Absolute evaluation prevents earlier rounding or clipping from changing that final relationship. It does not avoid DAA lag, mobile-miner behavior, or the effect of a lower reward at a returning work level than under a history-inflated recurrence.

At approximately steady work, ignoring bootstrap, fees, clipping, lag, and orphan costs, the absolute tail's coin reward per unit work is `K/sqrt(W)`. That illustrates sublinearity. It is not a profitability theorem: external coin price, energy costs, miner share, timing, and the exact feasible DAA path matter. Per-block work is a target-derived expected-work proxy, not actual hashes spent on a lucky block, measured energy, or observed hashrate. No nonce can improve this proxy by being exceptionally lucky once the required target is fixed.

P04 computes the current target from the parent's timestamp and height relative to a fixed ASERT anchor. The current miner's timestamp changes future required targets, not its own. With the existing lag it first changes a later block's work, which then changes the tail paid one block after that. This removes a direct own-timestamp/own-tail input, but a miner can still affect later blocks, return at favorable times, influence eligibility, or withhold blocks. MTP permits timestamps earlier than the parent, and the future-time eligibility profile is still open. Economic tests must use those exact rules.

The ideal recurrence also completely cancels a temporary work excursion once work returns to its original value. It would be incorrect to treat every inflated adjacent ratio as a permanent unopposed reward increase. Persistent normalization changes arise from rounding/clipping or from a work level that does not return. Absolute evaluation removes the former mechanism. A claim that it prevents profitable timestamp or hash-allocation manipulation would still require a feasible-history analysis with costs and benefits accruing to the same modeled miner.

## What carries over from the monetary paper

The paper's local model assumes inactive clipping, immediate mining adjustment, persistent external-currency burn budgets, and a chosen price-response coefficient. Using its log deviations, its reward recurrence gives the exact invariant in the ideal model:

```text
r_(n+1) - gamma*w_n = r_n - gamma*w_(n-1) = c.
```

For the absolute rule,

```text
r_(n+1) = c_g + gamma*w_n
c_g = log(T_g/T_star) + gamma*log(W_star/W_g).
```

Taking differences yields the same local reward equation. With the paper's other assumptions, both yield

```text
w_(n+1) = (1 - phi + gamma)*w_n - gamma*w_(n-1).
```

The paper's characteristic-root condition `0 < phi < 2+2*gamma`, for `0 < gamma < 1`, therefore applies to this same idealized work recurrence. It does not prove stability of either exact integer/clipped ASERT economy. The actual DAA, hash response delays, resource deductions, and changing burn demand remain outside that derivation.

There is a qualification to the ticket's discussion of the paper's path-dependent price level. In the unclipped, unrounded model, `c = r_0 - gamma*w_-1` is already fixed by the initial anchor: the intermediate path cannot independently change it. If `w_n -> 0`, the recurrence gives `r_infinity=c`, and `p_infinity=-c`. Absolute evaluation fixes that constant to `c_g` and prevents earlier clipping/rounding from changing it. It does not force `c_g=0` relative to an arbitrarily chosen reference equilibrium, force the eventual work to genesis work, or fix an external price.

For example, under the paper's simplified steady-state assumptions alone, let `A` be persistent external-currency burn spending per block and `k` the marginal external-currency cost per work unit. Supply balance and mining balance give `P*T=A=k*W`, hence `W_star=A/k`. Absolute evaluation then selects `T_star=F(W_star)` and `P_star=A/T_star`. Those are conditional relationships, not consensus observations or a peg; changing `A` or `k` changes the equilibrium. Within a fixed anchor and without rounding/clipping, the recurrent ideal curve selects the same pair.

A small independent proof-detail issue in the paper should not be copied into a new analysis: from `A^T P A-P=-I` and `V=x^T P x`, the guaranteed bound is `Delta V <= -V/lambda_max(P)`, not the printed `-V/lambda_min(P)`. Positive-definite `P` still proves decay; the coefficient correction does not invalidate the characteristic-root result. This is a source-review observation, not a paper edit.

## Decision and validation needed before adoption

Prefer the absolute formula if the intended policy is “a fixed reward curve against validated per-block work.” Retain the recurrence only if permanently changing its normalization after clipping is an intentional monetary feature, or if exact continuity with an already accepted recurrent history is required. Increased fractional precision can reduce recurrence rounding drift, but does not remove clamp hysteresis. Maintaining an unclipped hidden accumulator would add state and arithmetic complexity while reconstructing an invariant that genesis-anchored evaluation already provides directly.

The narrow next decision should concern only the tail formula and its unchanged lag. Keep `T_min,T_max` as constant bounds applied to the absolute result; review their anchored saturation thresholds and block-affordability implications. Do not invent bounds, use the ticket's development values as launch constants, or silently reset an anchor after saturation. Bootstrap scheduling and reducing the state-envelope schema should be separate explicit decisions so their behavior and verification costs are reviewable.

Before any implementation is authorized, the acceptance record should require:

1. Independent exact arithmetic vectors: genesis and height indexing; perfect/nonperfect squares; division boundaries; work extremes; clipping thresholds; wide-product and pre-narrowing cases; retained clamp/rounding counterexamples.
2. Complete block accounting and undo vectors: fees, required/voluntary underclaims, explicit burns, branch switches, snapshot continuation, and optional redundant-field equality checks. An envelope change also needs updated hash domains/schema/version decisions, proof encodings, fixture digests, and all state-root vectors.
3. Exact P04/P05/P06 joint simulations: timestamp constraints/eligibility, target compact rounding, mobile and fixed-share miners, delayed hash response, work/energy/demand shocks, prolonged saturation, and repeated small work changes. Compare discounted miner profit and circulation/security outcomes separately.
4. Launch feasibility: minimally populated blocks must remain affordable from the resource-adjusted entitlement at the chosen tail minimum and reachable EMA values. The nominal tail is not wholly available to the miner.

This recommendation is an architectural preference supported by algebra and arithmetic examples. It is not a measured attack-resistance result, an economic calibration, a full consensus implementation, or acceptance of the open network parameters.

## Reproducing the arithmetic examples

The following Python uses only the standard library and exact integers. It exercises formulas in isolation, not compact target encodings, ASERT feasibility, or block validation.

```python
from math import isqrt


def compare(t0, w0, works, lo=1, hi=(1 << 64) - 1):
    t, w = t0, w0
    rows = []
    for current_work in works:
        t = min(hi, max(lo, isqrt(t * t * current_work // w)))
        absolute = min(hi, max(lo, isqrt(t0 * t0 * current_work // w0)))
        rows.append((current_work, t, absolute))
        w = current_work
    return rows


assert compare(100, 10, [40, 90, 10]) == [
    (40, 200, 200), (90, 300, 300), (10, 100, 100)
]
assert compare(100, 10, [40, 10], hi=150) == [
    (40, 150, 150), (10, 75, 100)
]
assert compare(100, 4, [1, 4], lo=80, hi=1000) == [
    (1, 80, 80), (4, 160, 100)
]
assert compare(100, 10, [11, 10]) == [(11, 104, 104), (10, 99, 100)]
assert compare(250_000_000_000, 10, [11, 10] * 1000)[-1] == (
    10, 249_999_999_000, 250_000_000_000
)
assert 10 - max(1, 10 >> 2) == 8
assert 10 * 3 // 4 == 7
print("Absolute/recurrent reward examples and bootstrap counterexample: PASS")
```
