"""Bounded, pure P05/P06 monetary arithmetic; charges are supplied by a separate verifier.

All amounts are atoms. This module does not parse blocks, resolve UTXOs, compute
primitive costs, select Avalanche winners, or validate a genesis manifest.
"""

from dataclasses import dataclass
from math import isqrt

U64 = (1 << 64) - 1
U128 = (1 << 128) - 1
U256 = (1 << 256) - 1
U384 = (1 << 384) - 1
ABSOLUTE_TAIL_FORMULA_VERSION = 1


def uint(value: int, maximum: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= maximum:
        raise ValueError(f"{name} out of range")
    return value


def checked_sum(values, maximum: int, name: str) -> int:
    result = 0
    for value in values:
        result += uint(value, maximum, name)
        uint(result, maximum, name)
    return result


@dataclass(frozen=True)
class Profile:
    """Explicit illustrative or launch profile; no constants are selected here."""

    boot_shift: int
    tx_knee_shift: int
    ema_shift: int
    ema_min: int
    linear_shift: int
    quad_shift: int
    tail_min: int
    tail_max: int
    dust_limit: int
    min_fee_per_kb: int
    genesis_tail: int
    genesis_work: int

    def __post_init__(self):
        for name in ("boot_shift", "tx_knee_shift", "ema_shift",
                     "linear_shift", "quad_shift"):
            shift = getattr(self, name)
            if isinstance(shift, bool) or not isinstance(shift, int) or shift < 0:
                raise ValueError(f"{name} must be a nonnegative integer")
        for name in ("ema_min", "tail_min", "tail_max", "dust_limit", "min_fee_per_kb"):
            uint(getattr(self, name), U64, name)
        uint(self.genesis_tail, U64, "genesis_tail")
        uint(self.genesis_work, U256, "genesis_work")
        if self.genesis_work == 0 or not 0 < self.tail_min <= self.genesis_tail <= self.tail_max:
            raise ValueError("invalid absolute tail anchors")
        if self.tail_min > self.tail_max or self.min_fee_per_kb != 1000:
            raise ValueError("invalid tail bounds or P05 byte-fee constant")


@dataclass(frozen=True)
class MonetaryState:
    bootstrap_reserve: int
    tail_subsidy: int
    prev_work: int
    ema_block_cost: int

    def __post_init__(self):
        for name in ("bootstrap_reserve", "tail_subsidy", "ema_block_cost"):
            uint(getattr(self, name), U64, name)
        uint(self.prev_work, U256, "prev_work")
        if self.prev_work == 0:
            raise ValueError("prev_work must be positive")

    def to_bytes(self) -> bytes:
        return (self.bootstrap_reserve.to_bytes(8, "little") +
                self.tail_subsidy.to_bytes(8, "little") +
                self.prev_work.to_bytes(32, "little") +
                self.ema_block_cost.to_bytes(8, "little"))

    @classmethod
    def from_bytes(cls, wire: bytes) -> "MonetaryState":
        if not isinstance(wire, bytes) or len(wire) != 56:
            raise ValueError("MonetaryState must be exactly 56 bytes")
        return cls(int.from_bytes(wire[:8], "little"),
                   int.from_bytes(wire[8:16], "little"),
                   int.from_bytes(wire[16:48], "little"),
                   int.from_bytes(wire[48:], "little"))


def initialize_genesis(profile: Profile, *, bootstrap_reserve: int,
                       tail_subsidy: int, genesis_work: int,
                       ema_block_cost: int, coinbase_native_value: int = 0) -> MonetaryState:
    """Commit selected initial values without recurrence; zero native genesis issuance."""
    if not isinstance(profile, Profile):
        raise ValueError("explicit profile required")
    uint(coinbase_native_value, U64, "genesis coinbase native value")
    if coinbase_native_value != 0:
        raise ValueError("genesis has zero native issuance")
    state = MonetaryState(bootstrap_reserve, tail_subsidy, genesis_work, ema_block_cost)
    if not profile.tail_min <= state.tail_subsidy <= profile.tail_max:
        raise ValueError("initial tail outside profile bounds")
    if state.tail_subsidy != profile.genesis_tail or state.prev_work != profile.genesis_work:
        raise ValueError("genesis anchor mismatch")
    return state


def absolute_tail(profile: Profile, work: int) -> int:
    """Version 1: exact genesis-anchored square root, clamp before narrowing."""
    work = uint(work, U256, "work")
    if work == 0:
        raise ValueError("work must be positive")
    numerator = uint(profile.genesis_tail**2 * work, U384, "tail numerator")
    return min(profile.tail_max, max(profile.tail_min, isqrt(numerator // profile.genesis_work)))


def transaction_cost(linear_cost: int, profile: Profile) -> int:
    linear_cost = uint(linear_cost, U64, "linear_cost")
    product = uint(linear_cost * linear_cost, U128, "transaction square")
    return uint(linear_cost + (product >> profile.tx_knee_shift), U64, "transaction cost")


def block_cost(envelope_cost: int, tx_linear_costs: tuple[int, ...], profile: Profile) -> int:
    return checked_sum((uint(envelope_cost, U128, "envelope_cost"),
                        *(transaction_cost(v, profile) for v in tx_linear_costs)),
                       U128, "block_cost")


def required_block_burn(cost: int, ema: int, profile: Profile) -> int:
    cost = uint(cost, U128, "block_cost")
    ema = uint(ema, U64, "ema_block_cost")
    # Products are mathematical integers; no modular truncation. Cost itself is u128.
    return ((cost * max(ema, profile.ema_min)) >> profile.linear_shift) + \
           ((cost * cost) >> profile.quad_shift)


def byte_fee(size: int, profile: Profile) -> int:
    size = uint(size, U64, "serialized size")
    return uint((size * profile.min_fee_per_kb + 999) // 1000, U64, "byte fee")


@dataclass(frozen=True)
class OrdinaryTx:
    native_inputs: int
    native_outputs: int  # includes native IS_BURN outputs
    serialized_bytes: int
    token_outputs: int  # includes token IS_BURN outputs
    explicit_native_burn: int  # subset of native_outputs

    def accounting(self, profile: Profile) -> tuple[int, int]:
        incoming = uint(self.native_inputs, U128, "native_inputs")
        outgoing = uint(self.native_outputs, U128, "native_outputs")
        burned = uint(self.explicit_native_burn, U128, "explicit_native_burn")
        if outgoing > incoming or burned > outgoing:
            raise ValueError("native conservation or explicit burn invalid")
        fee = incoming - outgoing
        tokens = uint(self.token_outputs, 65535, "token_outputs")
        token_burn = uint(2 * profile.dust_limit * tokens, U128, "token burn")
        if fee < byte_fee(self.serialized_bytes, profile) or fee < token_burn:
            raise ValueError("ordinary fee below independent floor")
        return fee, token_burn


@dataclass(frozen=True)
class Transition:
    state: MonetaryState
    bootstrap_issued: int
    subsidy: int
    total_fees: int
    token_burn: int
    burned_fees: int
    required_underclaim: int
    actual_underclaim: int
    spendable_supply_delta: int


def advance(profile: Profile, parent: MonetaryState, *, work: int,
            transactions: tuple[OrdinaryTx, ...], coinbase_native_outputs: int,
            coinbase_native_burn: int, coinbase_bytes: int, tx_frame_prefix_bytes: int,
            account_block_cost: int, enforce_block_cost: int) -> Transition:
    """One non-genesis issuance step. Caller supplies independently checked costs/bytes."""
    if not isinstance(profile, Profile) or not isinstance(parent, MonetaryState):
        raise ValueError("explicit profile and parent state required")
    work = uint(work, U256, "work")
    if work == 0:
        raise ValueError("work must be positive")
    account = uint(account_block_cost, U128, "account_block_cost")
    enforce = uint(enforce_block_cost, U128, "enforce_block_cost")
    if not profile.tail_min <= parent.tail_subsidy <= profile.tail_max:
        raise ValueError("parent tail outside profile bounds")
    paid_tail = absolute_tail(profile, parent.prev_work)
    if parent.tail_subsidy != paid_tail:
        raise ValueError("parent cached tail mismatch")
    if enforce < account:
        raise ValueError("enforcement charge below frozen accounting charge")
    fees_and_tokens = tuple(tx.accounting(profile) for tx in transactions)
    fees = checked_sum((pair[0] for pair in fees_and_tokens), U128, "total fees")
    token_burn = checked_sum((pair[1] for pair in fees_and_tokens), U128, "token burn")
    remaining = fees - token_burn
    burned_fees = remaining - remaining // 2
    bootstrap = max(1, parent.bootstrap_reserve >> profile.boot_shift) if parent.bootstrap_reserve else 0
    reserve = parent.bootstrap_reserve - bootstrap
    subsidy = uint(bootstrap + paid_tail, U64, "subsidy")
    entitlement = uint(subsidy + remaining // 2, U128, "coinbase entitlement")
    # 134-byte header, 4-byte tx count, all CompactSize frame prefixes.
    overhead = checked_sum((134, 4, uint(tx_frame_prefix_bytes, U64, "frame prefixes")),
                           U64, "overhead bytes")
    charged_bytes = checked_sum((uint(coinbase_bytes, U64, "coinbase bytes"), overhead),
                                U64, "coinbase charged bytes")
    k = byte_fee(charged_bytes, profile)
    floor = required_block_burn(enforce, parent.ema_block_cost, profile)
    required = max(k, max(0, floor - burned_fees))
    if required > entitlement:
        raise ValueError("insufficient coinbase entitlement for mandatory deduction")
    payout = uint(coinbase_native_outputs, U128, "coinbase outputs")
    coinbase_burn = uint(coinbase_native_burn, U128, "coinbase native burn")
    if coinbase_burn > payout:
        raise ValueError("coinbase native burn exceeds its output sum")
    if payout > entitlement - required:
        raise ValueError("coinbase overclaims")
    underclaim = entitlement - payout
    tail = absolute_tail(profile, work)
    ema = uint(parent.ema_block_cost - (parent.ema_block_cost >> profile.ema_shift)
               + (account >> profile.ema_shift), U64, "next EMA")
    explicit = checked_sum((coinbase_burn, *(tx.explicit_native_burn for tx in transactions)),
                           U128, "explicit burn")
    # Signed mathematical supply delta, not serialized state.
    delta = subsidy - token_burn - burned_fees - underclaim - explicit
    return Transition(MonetaryState(reserve, tail, work, ema), bootstrap, subsidy,
                      fees, token_burn, burned_fees, required, underclaim, delta)
