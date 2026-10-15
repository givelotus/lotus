"""Genesis-anchored ASERT candidate for the child of a validated parent.

Working candidate, not a consensus freeze and not ConnectTip. lotusd has not
accepted a V2 block. Spacing of 120 seconds and a half-life of 172800 seconds
are the unfrozen working values. They are arguments. This module does not store
them as constants a node can import as law, and it does not give them defaults.

The anchor is the genesis target T0 and timestamp t0. Drift is
``parent.time - t0 - spacing * parent.height``. Historical aserti32d anchors on
the first post-genesis block and adds one to the height difference. This
candidate does neither.
"""

from __future__ import annotations

from dataclasses import dataclass

# Compact targets reject values past 256 bits. This is the codec width, not a
# chain pow_limit.
_MAX_TARGET = (1 << 256) - 1


@dataclass(frozen=True)
class Parent:
    """Validated parent. Only its timestamp and height enter the schedule."""

    time: int
    height: int


def _integer(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    return value


def _target_bound(value: int, name: str) -> int:
    value = _integer(value, name)
    if not 1 <= value <= _MAX_TARGET:
        raise ValueError(f"{name} out of range")
    return value


def compact_encode(target: int) -> int:
    """Canonical compact bits of a positive target.

    Exponent ``e`` is ``ceil(bit_length(target) / 8)``. The 23-bit mantissa is
    ``target`` shifted into the low 24 bits. If bit 23 is set, the mantissa
    shifts right eight bits and ``e`` increments. The sign bit stays clear.
    """
    target = _target_bound(target, "target")
    exponent = (target.bit_length() + 7) // 8
    if exponent <= 3:
        mantissa = target << (8 * (3 - exponent))
    else:
        mantissa = target >> (8 * (exponent - 3))
    if mantissa & 0x800000:
        mantissa >>= 8
        exponent += 1
    if not 0 <= mantissa <= 0x7FFFFF or not 0 <= exponent <= 0xFF:
        raise ValueError("compact encoding failed")
    return (exponent << 24) | mantissa


def compact_decode(bits: int, pow_limit: int) -> int:
    """Decode canonical compact bits.

    Unsigned exponent in the high byte, 23-bit mantissa, sign bit clear.
    ``T = m >> (8*(3-e))`` when ``e <= 3``, else ``m << (8*(e-3))``. Rejects
    zero, a shift past 256 bits, ``T > pow_limit``, and a non-canonical encoding.
    """
    bits = _integer(bits, "bits")
    pow_limit = _target_bound(pow_limit, "pow_limit")
    if not 0 <= bits <= 0xFFFFFFFF:
        raise ValueError("compact bits are not an unsigned 32-bit value")
    if bits & 0x00800000:
        raise ValueError("compact target sign bit must be zero")
    exponent = bits >> 24
    mantissa = bits & 0x007FFFFF
    if exponent <= 3:
        target = mantissa >> (8 * (3 - exponent))
    else:
        shift = 8 * (exponent - 3)
        if mantissa and (shift >= 256 or mantissa.bit_length() + shift > 256):
            raise ValueError("compact target overflows 256 bits")
        target = mantissa << shift if mantissa else 0
    if target == 0:
        raise ValueError("compact target is zero")
    if target > pow_limit:
        raise ValueError("compact target exceeds pow_limit")
    if compact_encode(target) != bits:
        raise ValueError("compact target is not canonical")
    return target


def schedule_drift(parent: Parent, *, t0: int, spacing: int) -> int:
    """Signed drift of ``parent`` from the genesis schedule.

    ``parent.time - t0 - spacing * parent.height``. Height is not increased
    by one. The result is a signed integer, not an unsigned wrap.
    """
    if not isinstance(parent, Parent):
        raise ValueError("parent must be a Parent")
    time = _integer(parent.time, "parent.time")
    height = _integer(parent.height, "parent.height")
    t0 = _integer(t0, "t0")
    spacing = _integer(spacing, "spacing")
    if height < 0 or spacing <= 0:
        raise ValueError("height and spacing must describe a forward schedule")
    return time - t0 - spacing * height


def exponent_parts(drift: int, half_life: int) -> tuple[int, int, int]:
    """Return ``(E, q, f)`` for a signed drift and a positive half-life.

    ``E`` divides ``65536 * drift`` by ``half_life`` toward zero. ``q`` is the
    floor of ``E / 65536``, so a negative non-multiple still yields ``f`` in
    ``0 .. 65535``. Floor and truncation are different on that path.
    """
    drift = _integer(drift, "drift")
    half_life = _integer(half_life, "half_life")
    if half_life <= 0:
        raise ValueError("half_life must be positive")
    numerator = 65536 * drift
    if numerator < 0:
        exponent = -((-numerator) // half_life)
    else:
        exponent = numerator // half_life
    quotient = exponent // 65536
    fraction = exponent - 65536 * quotient
    return exponent, quotient, fraction


def _approximation_factor(fraction: int) -> int:
    """``65536 * 2^(f/65536)`` as the specified 48-bit cubic, ``f`` in range."""
    if not 0 <= fraction < 65536:
        raise ValueError("ASERT fraction out of range")
    square = fraction * fraction
    cube = square * fraction
    polynomial = (
        195766423245049 * fraction
        + 971821376 * square
        + 5127 * cube
        + (1 << 47)
    )
    return 65536 + polynomial // (1 << 48)


def _bounded_pow2(value: int, shift: int, pow_limit: int) -> int:
    """``floor(value * 2**shift)`` capped at ``pow_limit``, without ``2**shift``.

    A nonnegative shift of 256 or more saturates when ``pow_limit`` fits in 256
    bits. A negative shift whose magnitude is at least ``bit_length(value)``
    is zero. Any shift that is actually performed stays within ``pow_limit``.
    """
    if value < 0:
        raise ValueError("scaled value must be nonnegative")
    if value == 0:
        return 0
    if shift >= 0:
        limit_bits = pow_limit.bit_length()
        if (shift >= 256 and limit_bits <= 256) or shift >= limit_bits:
            return pow_limit
        quotient = pow_limit >> shift
        if value > quotient:
            return pow_limit
        return value << shift
    magnitude = -shift
    if magnitude >= value.bit_length():
        return 0
    return value >> magnitude


def clamped_target(
    parent: Parent,
    *,
    t0: int,
    genesis_target: int,
    spacing: int,
    half_life: int,
    pow_limit: int,
) -> int:
    """Clamped absolute child target, before compact rounding.

    Spacing and half-life have no default. The unfrozen working candidate is
    spacing 120 and half-life 172800; pass both explicitly. This is not chain
    law and not ConnectTip.
    """
    genesis_target = _target_bound(genesis_target, "genesis_target")
    pow_limit = _target_bound(pow_limit, "pow_limit")
    _integer(half_life, "half_life")
    drift = schedule_drift(parent, t0=t0, spacing=spacing)
    _exponent, quotient, fraction = exponent_parts(drift, half_life)
    factor = _approximation_factor(fraction)
    scaled = genesis_target * factor
    raw = _bounded_pow2(scaled, quotient - 16, pow_limit)
    if raw < 0:
        raise ValueError("ASERT raw target wrapped")
    return min(pow_limit, max(1, raw))


def required_bits(
    parent: Parent,
    *,
    t0: int,
    genesis_target: int,
    spacing: int,
    half_life: int,
    pow_limit: int,
) -> int:
    """Canonical compact bits of the clamped child target.

    No default spacing or half-life is applied. The unfrozen working candidate,
    not a frozen mainnet constant, is spacing 120 and half-life 172800.
    """
    return compact_encode(
        clamped_target(
            parent,
            t0=t0,
            genesis_target=genesis_target,
            spacing=spacing,
            half_life=half_life,
            pow_limit=pow_limit,
        )
    )
