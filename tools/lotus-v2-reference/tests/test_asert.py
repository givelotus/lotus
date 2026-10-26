"""Genesis-anchored ASERT candidate checks.

Spacing 120 and half-life 172800 are the unfrozen working candidate. Every
call passes them explicitly. They are not frozen mainnet constants. This is
not ConnectTip, and lotusd has not accepted a V2 block.
"""
import unittest

from lotus_v2_reference.asert import (
    Parent,
    clamped_target,
    compact_decode,
    compact_encode,
    exponent_parts,
    required_bits,
    schedule_drift,
)
from lotus_v2_reference.dev_genesis import HEADER_BITS

# Development genesis compact target. Not a pow_limit selected by this test.
GENESIS_BITS = 0x1D00FFFF
WIDE_LIMIT = (1 << 256) - 1
GENESIS_TIME = 1_700_000_000


def child_target(parent, genesis_target, pow_limit, t0=GENESIS_TIME):
    return clamped_target(
        parent,
        t0=t0,
        genesis_target=genesis_target,
        spacing=120,
        half_life=172800,
        pow_limit=pow_limit,
    )


def child_bits(parent, genesis_target, pow_limit, t0=GENESIS_TIME):
    return required_bits(
        parent,
        t0=t0,
        genesis_target=genesis_target,
        spacing=120,
        half_life=172800,
        pow_limit=pow_limit,
    )


class AsertTests(unittest.TestCase):
    def test_development_genesis_bits_round_trip(self):
        self.assertEqual(HEADER_BITS, GENESIS_BITS)
        genesis_target = 0xFFFF << 208
        self.assertEqual(compact_decode(GENESIS_BITS, WIDE_LIMIT), genesis_target)
        self.assertEqual(compact_decode(GENESIS_BITS, genesis_target), genesis_target)
        self.assertEqual(compact_encode(genesis_target), GENESIS_BITS)
        with self.assertRaises(ValueError):
            compact_decode(GENESIS_BITS, genesis_target - 1)
        for rejected in (0, 0x01800000, 0x1D800000, 0x01010001, 0xFF000001):
            with self.assertRaises(ValueError):
                compact_decode(rejected, WIDE_LIMIT)

    def test_on_schedule_parent_keeps_genesis_target(self):
        genesis_target = compact_decode(GENESIS_BITS, WIDE_LIMIT)
        for height in (0, 1, 9, 10_000):
            parent = Parent(GENESIS_TIME + 120 * height, height)
            self.assertEqual(schedule_drift(parent, t0=GENESIS_TIME, spacing=120), 0)
            # Historical aserti32d would subtract spacing * (height + 1).
            self.assertNotEqual(
                parent.time - GENESIS_TIME - 120 * (height + 1),
                0,
            )
            self.assertEqual(child_target(parent, genesis_target, WIDE_LIMIT), genesis_target)
            self.assertEqual(child_bits(parent, genesis_target, genesis_target), GENESIS_BITS)
            self.assertEqual(child_bits(parent, genesis_target, WIDE_LIMIT), GENESIS_BITS)

    def test_exact_half_life_doubles_and_halves_before_compact_or_clamp(self):
        genesis_target = compact_decode(GENESIS_BITS, WIDE_LIMIT)
        for height in (0, 9):
            slow = Parent(GENESIS_TIME + 120 * height + 172800, height)
            fast = Parent(GENESIS_TIME + 120 * height - 172800, height)
            doubled = child_target(slow, genesis_target, WIDE_LIMIT)
            halved = child_target(fast, genesis_target, WIDE_LIMIT)
            self.assertEqual(doubled, genesis_target * 2)
            self.assertEqual(halved, genesis_target // 2)
            self.assertEqual(child_bits(slow, genesis_target, WIDE_LIMIT), 0x1D01FFFE)
            self.assertEqual(child_bits(fast, genesis_target, WIDE_LIMIT), 0x1C7FFF80)
            self.assertEqual(compact_decode(0x1D01FFFE, WIDE_LIMIT), doubled)
            self.assertEqual(compact_decode(0x1C7FFF80, WIDE_LIMIT), halved)
            clamped = child_target(slow, genesis_target, genesis_target)
            self.assertEqual(clamped, genesis_target)
            self.assertLess(clamped, genesis_target * 2)

        low = (1 << 22) + 1
        self.assertEqual(compact_decode(compact_encode(low), WIDE_LIMIT), low)
        doubled = child_target(Parent(GENESIS_TIME + 172800, 0), low, WIDE_LIMIT)
        self.assertEqual(doubled, low * 2)
        rounded = compact_decode(child_bits(Parent(GENESIS_TIME + 172800, 0), low, WIDE_LIMIT), WIDE_LIMIT)
        self.assertLess(rounded, doubled)
        self.assertEqual(child_target(Parent(GENESIS_TIME - 172800, 0), low, WIDE_LIMIT), low // 2)

    def test_negative_non_multiple_exponent_keeps_fraction_in_range(self):
        exponent, quotient, fraction = exponent_parts(-3, 172800)
        self.assertEqual((exponent, quotient, fraction), (-1, -1, 65535))
        self.assertIn(fraction, range(65536))
        toward_zero_quotient = int(exponent / 65536)
        toward_zero_fraction = exponent - 65536 * toward_zero_quotient
        self.assertLess(toward_zero_fraction, 0)

        # f = 65535 selects the cubic near 2, then the radix shift q-16 = -17.
        # floor(131072 * 131071 / 131072) = 131071, not a plain halving.
        low = 131072
        got = child_target(Parent(GENESIS_TIME - 3, 0), low, WIDE_LIMIT)
        self.assertEqual(got, 131071)
        self.assertNotEqual(got, low // 2)

    def test_integer_division_does_not_follow_float(self):
        drift = 281475100167445
        exponent, quotient, fraction = exponent_parts(drift, 172800)
        self.assertEqual(exponent, 106752037989430)
        self.assertNotEqual(exponent, int(65536 * drift / 172800))
        self.assertEqual(fraction, exponent - 65536 * quotient)
        self.assertIn(fraction, range(65536))

    def test_pow_limit_saturation_and_raw_zero_clamps_to_one(self):
        genesis_target = compact_decode(GENESIS_BITS, WIDE_LIMIT)
        saturated = child_target(Parent(GENESIS_TIME + 172800, 0), genesis_target, genesis_target)
        self.assertEqual(saturated, genesis_target)
        self.assertEqual(child_bits(Parent(GENESIS_TIME + 172800, 0), genesis_target, genesis_target), GENESIS_BITS)

        # f = 0 and q = -(bit_length(genesis_target << 16) - 16) makes the
        # negative shift consume every bit of V = genesis_target * 65536.
        scaled_bits = (genesis_target << 16).bit_length()
        quotient = -(scaled_bits - 16)
        self.assertEqual(quotient, -224)
        raw_zero = child_target(Parent(GENESIS_TIME + quotient * 172800, 0), genesis_target, WIDE_LIMIT)
        self.assertEqual(raw_zero, 1)
        self.assertEqual(
            child_bits(Parent(GENESIS_TIME + quotient * 172800, 0), genesis_target, WIDE_LIMIT),
            compact_encode(1),
        )
        self.assertEqual(compact_encode(1), 0x01010000)
        self.assertEqual(compact_decode(0x01010000, WIDE_LIMIT), 1)

    def test_huge_drift_returns_pow_limit_without_giant_allocation(self):
        genesis_target = compact_decode(GENESIS_BITS, WIDE_LIMIT)
        pow_limit = (1 << 22) + 1
        huge_time = Parent(GENESIS_TIME + (1 << 80), 0)
        self.assertEqual(child_target(huge_time, genesis_target, pow_limit), pow_limit)
        self.assertEqual(child_bits(huge_time, genesis_target, pow_limit), compact_encode(pow_limit))
        self.assertEqual(compact_decode(child_bits(huge_time, genesis_target, pow_limit), pow_limit), pow_limit)

        wide = child_target(huge_time, genesis_target, WIDE_LIMIT)
        self.assertEqual(wide, WIDE_LIMIT)
        self.assertEqual(child_bits(huge_time, genesis_target, WIDE_LIMIT), compact_encode(WIDE_LIMIT))

        huge_height = Parent(GENESIS_TIME, 1 << 80)
        self.assertEqual(child_target(huge_height, genesis_target, pow_limit), 1)
        self.assertEqual(child_bits(huge_height, genesis_target, pow_limit), 0x01010000)
