"""Hand-derived arithmetic checks; intentionally independent of structural fixtures."""
import unittest

from lotus_v2_reference.monetary import (
    absolute_tail, U64, U128, U256, MonetaryState, OrdinaryTx, Profile, advance, block_cost,
    initialize_genesis, required_block_burn, transaction_cost,
)


# Small illustrative values make every rounding boundary auditable by hand.
P = Profile(boot_shift=2, tx_knee_shift=3, ema_shift=2, ema_min=4,
            linear_shift=3, quad_shift=5, tail_min=2, tail_max=2000,
            dust_limit=3, min_fee_per_kb=1000, genesis_tail=200, genesis_work=9)


def step(parent, **kwargs):
    options = dict(work=9, transactions=(), coinbase_native_outputs=0,
                   coinbase_native_burn=0,
                   coinbase_bytes=1, tx_frame_prefix_bytes=1,
                   account_block_cost=4, enforce_block_cost=4)
    options.update(kwargs)
    return advance(P, parent, **options)


class MonetaryTests(unittest.TestCase):
    def test_genesis_record_and_no_advance(self):
        state = initialize_genesis(P, bootstrap_reserve=9, tail_subsidy=200,
                                   genesis_work=9, ema_block_cost=4)
        self.assertEqual(state, MonetaryState(9, 200, 9, 4))
        self.assertEqual(len(state.to_bytes()), 56)
        self.assertEqual(state.to_bytes(), bytes([9]) + bytes(7) + bytes([200]) + bytes(7)
                         + bytes([9]) + bytes(31) + bytes([4]) + bytes(7))
        self.assertEqual(MonetaryState.from_bytes(state.to_bytes()), state)
        top = MonetaryState(U64, U64, U256, U64)
        self.assertEqual(MonetaryState.from_bytes(top.to_bytes()), top)
        self.assertEqual(step(state).bootstrap_issued, 2)  # block 1, step 0
        with self.assertRaises(ValueError):
            initialize_genesis(P, bootstrap_reserve=9, tail_subsidy=200,
                               genesis_work=9, ema_block_cost=4, coinbase_native_value=1)
        for wire in (b"", bytes(55), bytes(57), bytes(16) + bytes(32) + bytes(8)):
            with self.assertRaises(ValueError):
                MonetaryState.from_bytes(wire)

    def test_reserve_conservation_and_zero_reserve(self):
        reserve = 9
        issued = 0
        for _ in range(9):
            b = max(1, reserve // 4) if reserve else 0
            reserve -= b
            issued += b
        self.assertEqual((reserve, issued), (0, 9))
        out = step(MonetaryState(0, 200, 9, 4))
        self.assertEqual((out.bootstrap_issued, out.subsidy, out.state.bootstrap_reserve),
                         (0, 200, 0))
        self.assertEqual(step(MonetaryState(1, 200, 9, 4)).bootstrap_issued, 1)

    def test_work_ratio_rounding_clamps_and_lag(self):
        parent = MonetaryState(9, 200, 9, 4)
        low = step(parent, work=1)
        self.assertEqual((low.subsidy, low.state.tail_subsidy), (202, 66))
        high = step(parent, work=U256)
        self.assertEqual((high.subsidy, high.state.tail_subsidy), (202, 2000))
        same = step(parent, work=9)
        self.assertEqual(same.state.tail_subsidy, 200)
        self.assertEqual(step(parent, work=18).state.tail_subsidy, 282)  # isqrt(80000)
        self.assertEqual(step(MonetaryState(9, 282, 18, 4), work=36).state.tail_subsidy, 400)

    def test_absolute_anchor_return_clamp_and_cache(self):
        from dataclasses import replace
        self.assertEqual([absolute_tail(P, w) for w in (9, 10, 9)], [200, 210, 200])
        upper = replace(P, tail_max=300)
        self.assertEqual([absolute_tail(upper, w) for w in (36, 9)], [300, 200])
        lower = replace(P, tail_min=180)
        self.assertEqual([absolute_tail(lower, w) for w in (1, 9)], [180, 200])
        smallest = replace(P, tail_min=1, genesis_tail=1, genesis_work=1)
        self.assertEqual(absolute_tail(smallest, 1), 1)
        wide = replace(P, genesis_tail=U64, genesis_work=1, tail_max=U64)
        self.assertEqual(absolute_tail(wide, U256), U64)
        for changes in ({"genesis_work": 0}, {"genesis_work": U256+1},
                        {"genesis_tail": 2001}, {"genesis_tail": 0},
                        {"tail_min": 0}, {"tail_min": 0, "genesis_tail": 0}):
            with self.assertRaises(ValueError):
                replace(P, **changes)
        with self.assertRaises(ValueError):
            step(MonetaryState(9, 199, 9, 4))
        with self.assertRaises(ValueError):
            initialize_genesis(P, bootstrap_reserve=9, tail_subsidy=201,
                               genesis_work=9, ema_block_cost=4)
        # Returning from saturation uses the original anchor, never the clamped cache.
        saturated = step(MonetaryState(9, 200, 9, 4), work=U256)
        returned = step(saturated.state, work=9)
        self.assertEqual((returned.subsidy, returned.state.tail_subsidy), (2001, 200))

    def test_costs_ema_and_extension_state_invariance(self):
        self.assertEqual(transaction_cost(3, P), 4)
        self.assertEqual(transaction_cost(4, P), 6)
        self.assertEqual(block_cost(5, (3, 4), P), 15)
        self.assertEqual(required_block_burn(8, 4, P), 6)  # 8*4/8 + 64/32
        parent = MonetaryState(9, 200, 9, 8)
        base = step(parent, account_block_cost=8, enforce_block_cost=8)
        strict = step(parent, account_block_cost=8, enforce_block_cost=64)
        self.assertEqual(base.state, strict.state)
        self.assertEqual(base.state.ema_block_cost, 8)  # 8-2+2
        self.assertGreater(strict.required_underclaim, base.required_underclaim)
        with self.assertRaises(ValueError):
            step(parent, account_block_cost=8, enforce_block_cost=7)

    def test_odd_fee_token_burn_explicit_burn_and_underclaim(self):
        parent = MonetaryState(9, 200, 9, 4)
        # Fee 13; one token output burns 6; remaining 7 splits 4 burn / 3 miner.
        tx = OrdinaryTx(100, 87, 10, 1, 2)
        out = step(parent, transactions=(tx,), coinbase_native_outputs=60)
        self.assertEqual((out.subsidy, out.total_fees, out.token_burn,
                          out.burned_fees), (202, 13, 6, 4))
        self.assertEqual(out.required_underclaim, 140)  # 1+134+4+1 bytes
        self.assertEqual(out.actual_underclaim, 145)  # entitlement 205 - 60
        self.assertEqual(out.spendable_supply_delta, 45)  # 202-6-4-145-2
        with self.assertRaises(ValueError):
            step(parent, transactions=(tx,), coinbase_native_outputs=66)
        burned_coinbase = step(parent, transactions=(tx,), coinbase_native_outputs=60,
                               coinbase_native_burn=10)
        extra_underclaim = step(parent, transactions=(tx,), coinbase_native_outputs=50)
        self.assertEqual(burned_coinbase.spendable_supply_delta,
                         extra_underclaim.spendable_supply_delta)
        self.assertEqual(burned_coinbase.actual_underclaim, 145)
        with self.assertRaises(ValueError):
            step(parent, transactions=(tx,), coinbase_native_outputs=60,
                 coinbase_native_burn=61)
        with self.assertRaises(ValueError):
            step(parent, transactions=(tx,), coinbase_native_outputs=66,
                 coinbase_native_burn=66)  # explicit burn cannot fund required U
        # Token and byte minima are independent lower bounds on the same fee.
        with self.assertRaises(ValueError):
            step(parent, transactions=(OrdinaryTx(10, 5, 1, 1, 0),))
        with self.assertRaises(ValueError):
            step(parent, transactions=(OrdinaryTx(10, 9, 2, 0, 0),))
        with self.assertRaises(ValueError):
            step(parent, transactions=(OrdinaryTx(10, 11, 1, 0, 0),))

    def test_widths_invalid_profile_and_insufficient_entitlement(self):
        with self.assertRaises(ValueError):
            Profile(2, 3, 2, 4, 3, 5, 20, 2, 3, 1000, 200, 9)
        with self.assertRaises(ValueError):
            Profile(2, 3, 2, 4, 3, 5, 2, 20, 3, 999, 2, 9)
        with self.assertRaises(ValueError):
            MonetaryState(0, 2, 0, 0)
        with self.assertRaises(ValueError):
            step(MonetaryState(0, 2001, 1, 0))
        with self.assertRaises(ValueError):
            transaction_cost(U64, P)
        with self.assertRaises(ValueError):
            block_cost(U128, (1,), P)
        with self.assertRaises(ValueError):
            step(MonetaryState(0, 2, 1, 0))  # 2 atoms cannot fund 140-byte charge
        with self.assertRaises(ValueError):
            step(MonetaryState(0, 2, 1, U64), account_block_cost=U128)
        # P01/C04 allow aggregate u128 even when each output value is u64.
        large = OrdinaryTx(2 * U64, 0, 1, 0, 0)
        result = step(MonetaryState(0, 66, 1, 0), transactions=(large,))
        self.assertEqual(result.total_fees, 2 * U64)
        self.assertGreater(result.actual_underclaim, U64)
        with self.assertRaises(ValueError):
            step(MonetaryState(0, 66, 1, 0),
                 transactions=(OrdinaryTx(U128, 0, 1, 0, 0),
                               OrdinaryTx(U128, 0, 1, 0, 0)))
        self.assertEqual(transaction_cost(1, Profile(2, 10000, 2, 4, 3,
                                                    10000, 2, 2000, 3, 1000, 200, 9)), 1)
        with self.assertRaises(ValueError):
            step(MonetaryState(0, 4, 1, 0), work=0)


if __name__ == "__main__":
    unittest.main()
