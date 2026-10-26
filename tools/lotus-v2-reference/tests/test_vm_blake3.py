"""Raw BLAKE3 opcode against the official unkeyed empty-input vector."""

import unittest

from lotus_v2_reference.vm import ASSIGNED, VMProfile, decode, evaluate, number, static_cost
from lotus_v2_reference.vm_cost import static_size_cost
from lotus_v2_reference.vm_runner import run_invocation


# BLAKE3-team/BLAKE3 test_vectors/test_vectors.json, input_len 0, hash mode.
EMPTY_DIGEST = bytes.fromhex("af1349b9f5f9a1a6a0404dea36dcc9499bcb25c9adc112b7cc9a93cae41f3262")
SCRIPT = bytes.fromhex("4c00ba20") + EMPTY_DIGEST + bytes.fromhex("91")
PROFILE = VMProfile(512, 4, 128, 8, 4, 512, 8, 100_000, 1,
                    {op: 1 for op in ASSIGNED})


class Blake3Tests(unittest.TestCase):
    def test_unkeyed_no_application_tag_and_clean_boolean(self):
        self.assertEqual(evaluate(SCRIPT, (), PROFILE).stack, (number(1),))
        ast = decode(bytes.fromhex("4c00ba"), PROFILE)
        self.assertEqual(static_cost(ast, PROFILE, input_count=0, output_count=0), 2)
        self.assertEqual(static_size_cost(ast, PROFILE, initial_sizes=(), script_length=3,
                                          input_count=0, output_count=0).state.main, (32,))

    def test_json_runner_with_explicit_hash_cost(self):
        profile = {name: getattr(PROFILE, name) for name in (
            "max_script_bytes", "max_arguments", "max_element_bytes", "max_stack_items",
            "max_altstack_items", "max_vm_bytes", "max_ast_depth",
            "max_invocation_cost", "structural_byte_cost")}
        profile["opcode_costs"] = {"4c": 1, "ba": {"base": 1,
                                                   "operand_byte": 1,
                                                   "result_byte": 1},
                                   "20": 33, "91": 10}
        case = {"script": SCRIPT.hex(), "args": [], "input_count": 0,
                "output_count": 0, "profile": profile}
        result = run_invocation(case)
        self.assertTrue(result["accepted_invocation"], result)
        self.assertEqual(result["charged_cost"], len(SCRIPT) + 1 + 33 + 33 + 10)
        bad = bytearray(SCRIPT)
        bad[4] ^= 1
        case["script"] = bytes(bad).hex()
        self.assertFalse(run_invocation(case)["accepted_invocation"])


if __name__ == "__main__":
    unittest.main()
