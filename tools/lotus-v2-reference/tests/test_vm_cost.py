"""P05 size-bound charge vectors independent of VM execution."""

import unittest

from lotus_v2_reference.vm import ASSIGNED, VMError, VMProfile, U128_MAX, decode, evaluate, static_cost
from lotus_v2_reference.vm_cost import UNKNOWN, static_size_cost


def price(operands, results):
    return 1 + sum(operands) + sum(results)


def profile(costs=None):
    return VMProfile(512, 8, 128, 16, 8, 256, 8, 10_000_000, 1,
                     costs if costs is not None else {op: price for op in ASSIGNED})


def sized(script, *, initial=(), inputs=0, outputs=0, fields=None, selected=None):
    vm_profile = selected or profile()
    return static_size_cost(decode(bytes.fromhex(script), vm_profile), vm_profile,
                            initial_sizes=initial, script_length=len(bytes.fromhex(script)),
                            input_count=inputs, output_count=outputs, field_sizes=fields)


class SizeCostTests(unittest.TestCase):
    def test_profile_copies_and_freezes_charge_schedule(self):
        mutable = {op: 1 for op in ASSIGNED}
        vm_profile = profile(mutable)
        mutable[0x4e] = 900
        self.assertEqual(vm_profile.opcode_costs[0x4e], 1)
        with self.assertRaises(TypeError):
            vm_profile.opcode_costs[0x4e] = 900

    def test_exact_push_hash_and_underflow_fallback(self):
        # PUSH_3 costs 1+3; SHA256 costs 1+3+32.
        self.assertEqual(sized("03616263b8").cost, 40)
        underflow = sized("b8")
        self.assertEqual(underflow.state, UNKNOWN)
        self.assertEqual(underflow.cost, 1 + 6*128 + 4*128)

    def test_condition_merge_uses_larger_arm_and_skipped_underflow(self):
        # ZERO IF PUSH_1 ELSE PUSH_8 ENDIF SHA256
        script = "006101616308" + "62"*8 + "64b8"
        self.assertEqual(sized(script).cost, 86)
        self.assertEqual(sized("006179634e64").state, UNKNOWN)
        # Underflow in the skipped arm charges at the maximum, without rejecting.
        self.assertGreater(sized("0061b8634e64").cost, 128)

    def test_pick_and_field_specific_bounds(self):
        direct = sized("007d", initial=(3, 100))
        self.assertEqual(direct.state.main, (3, 100, 100))
        variable = sized("7d", initial=(3, 100, 16))
        self.assertEqual(variable.state.main, (3, 100, 100))
        wide_profile = VMProfile(512, 8, 1024, 16, 8, 2048, 8, 10_000_000, 1,
                                 {op: price for op in ASSIGNED})
        self.assertEqual(sized("00e7", fields={0xe7: (45, 812)}, selected=wide_profile).cost,
                         17 + (1 + 16 + 45))
        self.assertEqual(sized("e7", initial=(16,), fields={0xe7: (45, 812)},
                               selected=wide_profile).cost, 1 + 16 + 812)
        self.assertEqual(sized("f0").state.main, (1,))

    def test_loop_bounds_and_break_height(self):
        no_growth = sized("4e69796a4e")
        self.assertEqual(no_growth.cost, 17 + 17 + 256*(1+17) + 17)
        growing = sized("4e697a6a")
        self.assertEqual(growing.state, UNKNOWN)
        self.assertGreater(growing.cost, no_growth.cost)
        equal_break = sized("67794e6b6a", inputs=1)
        self.assertEqual(equal_break.state.main, ())
        unequal_break = sized("674e6b6a", inputs=1)
        self.assertEqual(unequal_break.state, UNKNOWN)
        # Even with one runtime input, I×O nested loops charge full I×O.
        flat_profile = profile({op: 1 for op in ASSIGNED})
        nested = sized("6768796a796a", inputs=3, outputs=4, selected=flat_profile)
        self.assertEqual(nested.cost, 34)

    def test_static_cost_matches_size_pass(self):
        vm_profile = profile()
        ast = decode(bytes.fromhex("03616263b8"), vm_profile)
        self.assertEqual(static_cost(ast, vm_profile, input_count=0, output_count=0,
                                     script_length=5), 40)

    def test_zero_bound_body_above_cap_and_positive_bound(self):
        script = bytes.fromhex("67794e796a4e")
        limited = VMProfile(512, 8, 128, 16, 8, 256, 8, 24, 1,
                            {op: price for op in ASSIGNED})
        result = evaluate(script, (), limited, input_count=0)
        self.assertTrue(result.success)
        self.assertEqual(result.charged_cost, 24)
        with self.assertRaises(VMError):
            evaluate(script, (), limited, input_count=1)
        enough = VMProfile(512, 8, 128, 16, 8, 256, 8, 76, 1,
                           {op: price for op in ASSIGNED})
        self.assertEqual(evaluate(script, (), enough, input_count=1).charged_cost, 76)

    def test_zero_bound_does_not_hide_u128_overflow(self):
        overflow_control = VMProfile(512, 8, 128, 16, 8, 256, 8,
                                     U128_MAX, 1,
                                     {op: U128_MAX if op == 0x6a else 1
                                      for op in ASSIGNED})
        with self.assertRaisesRegex(VMError, "static cost exceeds bound"):
            evaluate(bytes.fromhex("67796a4e"), (), overflow_control, input_count=0)
        worst_overflow = VMProfile(512, 8, 128, 16, 8, 256, 8,
                                   U128_MAX, 1,
                                   {op: (lambda a, b: U128_MAX + 1 if 128 in (*a, *b) else 1)
                                    if op == 0xb8 else 1 for op in ASSIGNED})
        with self.assertRaisesRegex(VMError, "static cost exceeds bound"):
            evaluate(bytes.fromhex("677ab86a4e"), (), worst_overflow, input_count=0)
        huge = VMProfile(512, 8, (1 << 64) - 1, 16, 8, 256, 8,
                         U128_MAX, 1,
                         {op: (lambda a, b: 1 + sum(a) * ((1 << 64) - 1)
                               + sum(b)) if op == 0xb8 else 1
                          for op in ASSIGNED})
        with self.assertRaisesRegex(VMError, "static cost exceeds bound"):
            evaluate(bytes.fromhex("6779b86a4e"), (), huge, input_count=0)

    def test_break_in_skipped_code_is_runtime_only(self):
        selected = profile()
        self.assertTrue(evaluate(bytes.fromhex("00614e6b634e64"), (), selected).success)
        self.assertTrue(evaluate(bytes.fromhex("00696b6a4e"), (), selected).success)
        with self.assertRaisesRegex(VMError, "BREAK depth outside"):
            evaluate(bytes.fromhex("4e614e6b634e64"), (), selected)
        for malformed in ("00616b", "006b6a"):
            with self.assertRaises(VMError):
                evaluate(bytes.fromhex(malformed), (), selected)

    def test_constant_path_index_uses_that_slot(self):
        # 00 is the path slot. The input index is already on the stack.
        slot0 = sized("00db", initial=(16,), fields={0xdb: (4, 50)})
        slot1 = sized("4edb", initial=(16,), fields={0xdb: (4, 50)})
        any_slot = sized("db", initial=(16, 16), fields={0xdb: (4, 50)})
        out0 = sized("00e6", initial=(16,), fields={0xe6: (4, 50)})
        self.assertEqual(slot0.state.main, (4,))
        self.assertEqual(slot1.state.main, (50,))
        self.assertEqual(any_slot.state.main, (50,))
        self.assertEqual(out0.state.main, (4,))
        self.assertEqual(slot0.cost, 17 + (1 + 16 + 16 + 4))
        self.assertEqual(slot1.cost, 17 + (1 + 16 + 16 + 50))
        self.assertEqual(any_slot.cost, 1 + 16 + 16 + 50)
        self.assertEqual(out0.cost, slot0.cost)
        self.assertLess(slot0.cost, any_slot.cost)
        # A constant past the hint vector still pays the widest slot.
        self.assertEqual(sized("52db", initial=(16,), fields={0xdb: (4, 50)}).state.main,
                         (50,))

    def test_merkle_step_charges_four_algorithms(self):
        def step(script, tail, selected=None):
            zero = sized(script, initial=(32, 0) + tail, selected=selected)
            wide = sized(script, initial=(32, 64) + tail, selected=selected)
            # Two proof steps, plus the 64-byte operand bound itself.
            return (wide.cost - zero.cost - 64) // 2

        blake_tagged = 1 + 96 + 32
        pair = 1 + 64 + 32
        self.assertEqual(step("00c0", ()), blake_tagged)
        self.assertNotEqual(step("00c0", ()), pair)
        self.assertEqual(step("4ec0", ()), pair)
        self.assertEqual(step("4fc0", ()), pair)
        self.assertEqual(step("50c0", ()), pair)
        nonconstant = step("c0", (16,))
        for selector in ("00c0", "4ec0", "4fc0", "50c0"):
            self.assertGreaterEqual(nonconstant, step(selector, ()))
        self.assertEqual(nonconstant, blake_tagged)
        # Unknown proofs pay the full step cap, and algorithm 0 dominates.
        base = 1 + 6 * 128 + 4 * 128
        self.assertEqual(sized("c0").cost, base + 64 * blake_tagged)
        self.assertEqual(sized("c1").cost, base + 4 * blake_tagged)
        iteration = 1 + base + 64 * blake_tagged
        self.assertEqual(sized("67c06a", inputs=0).cost, 1)
        self.assertEqual(sized("67c06a", inputs=1).cost, 1 + iteration)
        self.assertEqual(sized("67c06a", inputs=2).cost, 1 + 2 * iteration)

        def sha_heavy(op):
            per = 100 if op == 0xb8 else 1
            return lambda operands, results, per=per: 1 + per * sum(operands) + sum(results)

        heavy = profile({op: sha_heavy(op) for op in ASSIGNED})
        sha_step = 1 + 100 * 64 + 32
        self.assertEqual(step("4fc0", (), heavy), sha_step)
        self.assertGreater(sha_step, step("00c0", (), heavy))
        self.assertGreater(sha_step, step("50c0", (), heavy))
        self.assertEqual(step("c0", (16,), heavy), sha_step)


if __name__ == "__main__":
    unittest.main()
