"""P05 size-bound charge vectors independent of VM execution."""

import unittest

from lotus_v2_reference.vm import ASSIGNED, VMProfile, decode, static_cost
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


if __name__ == "__main__":
    unittest.main()
