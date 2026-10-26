"""Derived P05 field sizes for output records and path reads."""

import unittest

from lotus_v2_reference.encoding import Output, Profile as OutputProfile, encode_output
from lotus_v2_reference.vm import ASSIGNED, VMError, VMProfile, decode, evaluate, number
from lotus_v2_reference.vm_context import InputView, InvocationContext
from lotus_v2_reference.vm_cost import (
    bind_authenticated_field_sizes, derive_field_sizes, static_size_cost)


def price(operands, results):
    return 1 + sum(operands) + sum(results)


def wide_profile():
    return VMProfile(512, 8, 8192, 16, 8, 16384, 8, 10_000_000, 1,
                     {op: price for op in ASSIGNED})


OUTPUT_PROFILE = OutputProfile(16, 16, 812, 8192)


def native_output(value, branch, paths=((0,),)):
    return Output(0, value, None, branch, paths)


def spend_context(coin, outputs):
    return InvocationContext((InputView(1, coin),), tuple(outputs), "spend", 0,
                             coin.branches[0], OUTPUT_PROFILE, 0, 0, None)


class DerivedFieldSizeTests(unittest.TestCase):
    def setUp(self):
        self.coin = native_output(1000, (b"\x55" * 32,))
        self.output = native_output(1000, (b"\x44" * 32,))
        self.ctx = spend_context(self.coin, (self.output,))
        self.vm = wide_profile()

    def test_canonical_output_and_path_sizes(self):
        self.assertEqual(len(encode_output(self.output, OUTPUT_PROFILE)), 45)
        sizes = derive_field_sizes(self.ctx)
        self.assertEqual(sizes[0xe7], (45,))
        self.assertEqual(sizes[0xdc], (45,))
        self.assertEqual(sizes[0xe6], (2,))
        self.assertEqual(sizes[0xdb], (2,))
        self.assertLess(45, self.vm.max_element_bytes)
        bound = bind_authenticated_field_sizes(None, self.ctx,
                                               max_element_bytes=self.vm.max_element_bytes)
        record = static_size_cost(decode(bytes.fromhex("00e7"), self.vm), self.vm,
                                  initial_sizes=(), script_length=2,
                                  input_count=1, output_count=1, field_sizes=bound)
        path = static_size_cost(decode(bytes.fromhex("00e6"), self.vm), self.vm,
                                initial_sizes=(16,), script_length=2,
                                input_count=1, output_count=1, field_sizes=bound)
        uncapped = static_size_cost(decode(bytes.fromhex("00e7"), self.vm), self.vm,
                                    initial_sizes=(), script_length=2,
                                    input_count=1, output_count=1)
        self.assertEqual(record.state.main, (45,))
        self.assertEqual(record.cost, 17 + (1 + 16 + 45))
        self.assertEqual(path.state.main, (2,))
        self.assertEqual(path.cost, 17 + (1 + 16 + 16 + 2))
        self.assertLess(record.cost, uncapped.cost)
        self.assertEqual(uncapped.state.main, (self.vm.max_element_bytes,))

    def test_absent_hint_matches_exact_and_larger_hint_stays(self):
        # The field read sits in the untaken arm, so execution still succeeds.
        script = bytes.fromhex("006100e7634e64")
        absent = evaluate(script, (), self.vm, invocation=self.ctx)
        exact = evaluate(script, (), self.vm, invocation=self.ctx,
                         field_sizes={0xe7: (45,)})
        larger = evaluate(script, (), self.vm, invocation=self.ctx,
                          field_sizes={0xe7: (60,)})
        free = evaluate(script, (), self.vm)
        self.assertTrue(absent.success and exact.success and larger.success and free.success)
        self.assertEqual(absent.charged_cost, exact.charged_cost)
        self.assertLess(exact.charged_cost, larger.charged_cost)
        self.assertLess(larger.charged_cost, free.charged_cost)
        with self.assertRaisesRegex(VMError, "field-size hint below authenticated field"):
            evaluate(script, (), self.vm, invocation=self.ctx, field_sizes={0xe7: (44,)})
        with self.assertRaisesRegex(VMError, "field-size hint count"):
            evaluate(script, (), self.vm, invocation=self.ctx, field_sizes={0xe7: (45, 45)})

    def test_path_slot_and_context_free_hint(self):
        script = bytes.fromhex("006100e663794e64")
        absent = evaluate(script, (number(0),), self.vm, invocation=self.ctx)
        exact = evaluate(script, (number(0),), self.vm, invocation=self.ctx,
                         field_sizes={0xe6: (2,)})
        larger = evaluate(script, (number(0),), self.vm, invocation=self.ctx,
                          field_sizes={0xe6: (9,)})
        self.assertEqual(absent.charged_cost, exact.charged_cost)
        self.assertLess(exact.charged_cost, larger.charged_cost)
        with self.assertRaisesRegex(VMError, "field-size hint below authenticated field"):
            evaluate(script, (number(0),), self.vm, invocation=self.ctx,
                     field_sizes={0xe6: (1,)})
        # No transaction: a caller hint is still the whole bound.
        self.assertEqual(bind_authenticated_field_sizes(None, None), {})
        self.assertEqual(bind_authenticated_field_sizes({0xe7: (1,)}, None), {0xe7: (1,)})
        free = static_size_cost(decode(bytes.fromhex("00e7"), self.vm), self.vm,
                                initial_sizes=(), script_length=2,
                                input_count=0, output_count=0, field_sizes={0xe7: (1,)})
        self.assertEqual(free.state.main, (1,))

    def test_second_path_slot_and_unresolved_coin(self):
        branched = native_output(1000, (b"\x44" * 32, b"\x22" * 32), ((0,), (0, 1)))
        ctx = spend_context(self.coin, (branched,))
        sizes = derive_field_sizes(ctx)
        self.assertEqual(sizes[0xe6], (2, 3))
        bound = bind_authenticated_field_sizes(None, ctx, max_element_bytes=8192)
        slot0 = static_size_cost(decode(bytes.fromhex("00e6"), self.vm), self.vm,
                                 initial_sizes=(16,), script_length=2,
                                 input_count=1, output_count=1, field_sizes=bound)
        slot1 = static_size_cost(decode(bytes.fromhex("4ee6"), self.vm), self.vm,
                                 initial_sizes=(16,), script_length=2,
                                 input_count=1, output_count=1, field_sizes=bound)
        self.assertEqual(slot0.state.main, (2,))
        self.assertEqual(slot1.state.main, (3,))
        self.assertEqual(slot0.cost, 17 + (1 + 16 + 16 + 2))
        self.assertEqual(slot1.cost, 17 + (1 + 16 + 16 + 3))
        mint = InvocationContext(
            (InputView(1, self.coin), InputView(3, mint_token_id=b"\x02" * 32)),
            (self.output,), "spend", 0, self.coin.branches[0], OUTPUT_PROFILE, 0, 0, None)
        self.assertEqual(derive_field_sizes(mint)[0xdc], (45, 0))


if __name__ == "__main__":
    unittest.main()
