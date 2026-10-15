"""Fixed P03 boundary vectors for the bounded VM slice."""

import hashlib
import unittest

from lotus_v2_reference.vm import (
    ASSIGNED, VMError, VMProfile, UnsupportedFeature, decode, evaluate,
    number, success_scan,
)


PROFILE = VMProfile(
    max_script_bytes=512, max_arguments=8, max_element_bytes=128,
    max_stack_items=16, max_altstack_items=8, max_vm_bytes=256,
    max_ast_depth=8, max_invocation_cost=100_000,
    structural_byte_cost=1, opcode_costs={op: 1 for op in ASSIGNED},
)
ONE = b"\x01" + bytes(15)
ZERO = bytes(16)


class VMTests(unittest.TestCase):
    def test_success_scan_boundaries_and_ignored_suffix(self):
        self.assertEqual(len(ASSIGNED), 215)
        self.assertEqual(sum(i not in ASSIGNED for i in range(256)), 41)
        self.assertTrue(success_scan(bytes.fromhex("66615e4c"), PROFILE))
        result = evaluate(bytes.fromhex("66615e4c"), (), PROFILE)
        self.assertTrue(result.automatic)
        self.assertIsNone(result.stack)
        self.assertEqual(result.charged_cost, 4)
        self.assertTrue(success_scan(bytes.fromhex("614e635e64"), PROFILE))
        self.assertFalse(success_scan(bytes.fromhex("015e4e91"), PROFILE))
        with self.assertRaises(VMError):
            success_scan(bytes.fromhex("4c015e4e91"), PROFILE)

    def test_malformed_before_success_rejects_after_success_ignored(self):
        for script in (bytes.fromhex("0244"), bytes.fromhex("4cfd01005e"),
                       bytes.fromhex("4c015e5e"), bytes.fromhex("4cfd")):
            with self.subTest(script=script.hex()), self.assertRaises(VMError):
                success_scan(script, PROFILE)
        self.assertTrue(success_scan(bytes.fromhex("5e4cfd"), PROFILE))
        self.assertTrue(evaluate(bytes.fromhex("5e4cfd"), (), PROFILE).automatic)

    def test_structured_decode_rejects_skipped_malformed_regions(self):
        for script in (bytes.fromhex("004e614e634c02ff64"),
                       bytes.fromhex("0064"), bytes.fromhex("616a64"),
                       bytes.fromhex("676167646a"), bytes.fromhex("6767676a6a6a")):
            with self.subTest(script=script.hex()), self.assertRaises(VMError):
                decode(script, PROFILE)
        # Runtime underflow in a skipped arm does not occur.
        self.assertFalse(evaluate(bytes.fromhex("006179634e64"), (), PROFILE).automatic)

    def test_boolean_and_arithmetic_boundaries(self):
        self.assertEqual(evaluate(bytes.fromhex("4d4e9e00a6"), (), PROFILE).stack, (ONE,))
        self.assertEqual(evaluate(bytes.fromhex("4d4fa10091"), (), PROFILE).stack, (ONE,))
        self.assertEqual(evaluate(bytes.fromhex("4d4fa24d91"), (), PROFILE).stack, (ONE,))
        for script, args in (
            (bytes.fromhex("61"), (number(2),)),
            (bytes.fromhex("65"), (number(-1),)),
            (bytes.fromhex("98"), (number(2**127-1),)),
            (bytes.fromhex("9a"), (number(-(2**127)),)),
            (bytes.fromhex("a1"), (number(-(2**127)), number(-1))),
            (bytes.fromhex("a2"), (number(1), ZERO)),
            (bytes.fromhex("a4"), (number(2), ONE)),
        ):
            with self.subTest(script=script.hex()), self.assertRaises(VMError):
                evaluate(script, args, PROFILE)
        with self.assertRaises(VMError):
            evaluate(bytes.fromhex("4e4e"), (), PROFILE)

    def test_limits_and_preexecution_charge(self):
        with self.assertRaises(VMError):
            evaluate(bytes.fromhex("4e7a91"), (), VMProfile(
                512, 8, 128, 1, 8, 256, 8, 100000, 1,
                {op: 1 for op in ASSIGNED}))
        with self.assertRaises(VMError):
            evaluate(bytes.fromhex("4e"), (), VMProfile(
                512, 8, 128, 16, 8, 256, 8, 1, 1,
                {op: 1 for op in ASSIGNED}))
        with self.assertRaisesRegex(VMError, "stack underflow"):
            evaluate(bytes.fromhex("bd"), (), PROFILE)
        with self.assertRaises(UnsupportedFeature):
            evaluate(bytes.fromhex("4e"), (), VMProfile(
                512, 8, 128, 16, 8, 256, 8, 100000, 1, {}))

    def test_bounded_loops_break_and_hash(self):
        self.assertEqual(evaluate(bytes.fromhex("00696a4e"), (), PROFILE).stack, (ONE,))
        self.assertEqual(evaluate(bytes.fromhex("4e69614e6b646a4e"), (), PROFILE).stack, (ONE,))
        self.assertEqual(evaluate(bytes.fromhex("677967794f6b6a666a4e"), (), PROFILE, input_count=1).stack, (ONE,))
        with self.assertRaises(VMError):
            evaluate(bytes.fromhex("4e6b"), (), PROFILE)
        digest = hashlib.sha256(b"abc").digest()
        self.assertEqual(evaluate(bytes.fromhex("03616263b820") + digest + bytes.fromhex("91"), (), PROFILE).stack, (ONE,))

    def test_push_framing_and_stack_operations(self):
        self.assertEqual(evaluate(bytes.fromhex("4c004c00914e91"), (), PROFILE).stack, (ONE,))
        self.assertEqual(evaluate(bytes.fromhex("036162630164888c51a68079"), (), PROFILE).stack, (ONE,))
        self.assertEqual(evaluate(bytes.fromhex("4e7a91"), (), PROFILE).stack, (ONE,))
        for script in (bytes.fromhex("4cfd4c00"), bytes.fromhex("4c4b") + b"a" * 75,
                       bytes.fromhex("4cfd4c00") + b"a" * 76):
            with self.subTest(script=script[:4].hex()), self.assertRaises(VMError):
                success_scan(script, PROFILE)
        long_push = bytes.fromhex("4c4c") + b"a" * 76
        self.assertFalse(success_scan(long_push, PROFILE))

    def test_static_charge_covers_unexecuted_arm_and_loop_bound(self):
        result = evaluate(bytes.fromhex("00614e634e64"), (), PROFILE)
        self.assertEqual(result.charged_cost, 6 + 5)
        result = evaluate(bytes.fromhex("00696a4e"), (), PROFILE)
        self.assertEqual(result.charged_cost, 4 + 1 + 1 + 256 + 1)
        result = evaluate(bytes.fromhex("67796a4e"), (), PROFILE, input_count=3)
        self.assertEqual(result.charged_cost, 4 + 1 + 3 * (1 + 1) + 1)


if __name__ == "__main__":
    unittest.main()
