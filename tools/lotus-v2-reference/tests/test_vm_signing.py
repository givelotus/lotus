"""BIP340 published vectors and P01 invocation framing for CHECKSIG."""

import unittest
from hashlib import sha256

from lotus_v2_reference.vm import (
    ASSIGNED, SigningContext, UnsupportedFeature, VMError, VMProfile,
    branch_leaf_hash, evaluate, number,
)
from lotus_v2_reference.vm_runner import run_invocation


# Bitcoin BIP340 official test-vectors.csv, index 0 (32-byte message).
KEY = bytes.fromhex("F9308A019258C31049344F85F89D5229B531C845836F99B08601F113BCE036F9")
MESSAGE = bytes(32)
SIGNATURE = bytes.fromhex(
    "E907831F80848D1069A5371B402410364BDF1C5F8307B0084C55F1CE2DCA8215"
    "25F66A4A85EA8B71E482A74F382D2CE5EBEEE8FDB2172F477DF4900D310536C0")
# BIP340 vector 5: x-only bytes that are not a curve point.
BAD_KEY = bytes.fromhex("EEFDEA4CDB677750A420FEE807EACF21EB9898AE79B9768766E4FAA04A2D4A34")
PROFILE = VMProfile(512, 4, 128, 8, 4, 512, 8, 100_000, 1,
                    {op: 1 for op in ASSIGNED})
SCRIPT = b"\x20" + KEY + b"\xbb"


def context(script=SCRIPT, messages=None, *, kind="spend", input_index=0, output_count=1):
    return SigningContext(branch_leaf_hash(script), messages or {0: MESSAGE},
                          kind, input_index, output_count)


class SigningTests(unittest.TestCase):
    def test_p02_fixed_branch_leaf(self):
        # The existing independent ordinary_op_one fixture reveals script 4e.
        self.assertEqual(branch_leaf_hash(b"\x4e").hex(),
                         "a88cef369f758aec3e594eaa4e8d08c9f12ef3f11bea972ec53a416a148f0605")

    def test_official_bip340_vector_and_verify_form(self):
        result = evaluate(SCRIPT, (SIGNATURE,), PROFILE, input_count=1,
                          output_count=1, signing=context())
        self.assertEqual(result.stack, (number(1),))
        self.assertFalse(result.automatic)
        verify = SCRIPT[:-1] + b"\xbc\x4e"
        self.assertEqual(evaluate(verify, (SIGNATURE,), PROFILE, input_count=1,
                                  output_count=1, signing=context(verify)).stack, (number(1),))

    def test_bad_signature_is_false_and_bad_key_is_error(self):
        # NOT proves the correctly sized wrong-digest signature yielded N(0).
        script = SCRIPT + b"\x9c"
        wrong = context(script, {0: bytes([1])*32})
        self.assertEqual(evaluate(script, (SIGNATURE,), PROFILE, input_count=1,
                                  output_count=1, signing=wrong).stack, (number(1),))
        with self.assertRaisesRegex(VMError, "CHECKSIGVERIFY failed"):
            verify = SCRIPT[:-1] + b"\xbc\x4e"
            evaluate(verify, (SIGNATURE,), PROFILE, input_count=1,
                     output_count=1, signing=context(verify, {0: bytes([1])*32}))
        invalid_key_script = b"\x20" + BAD_KEY + b"\xbb"
        with self.assertRaisesRegex(VMError, "malformed CHECKSIG x-only key"):
            evaluate(invalid_key_script, (SIGNATURE,), PROFILE, input_count=1,
                     output_count=1, signing=context(invalid_key_script))

    def test_mode_and_context_errors(self):
        for sig in (b"", SIGNATURE[:-1], SIGNATURE + b"\x00", SIGNATURE + b"\x03"):
            with self.subTest(sig=sig.hex()[:8]), self.assertRaises(VMError):
                evaluate(SCRIPT, (sig,), PROFILE, input_count=1, output_count=1,
                         signing=context())
        with self.assertRaises(UnsupportedFeature):
            evaluate(SCRIPT, (SIGNATURE,), PROFILE, input_count=1, output_count=1)
        with self.assertRaisesRegex(VMError, "selected leaf"):
            evaluate(SCRIPT, (SIGNATURE,), PROFILE, input_count=1, output_count=1,
                     signing=context(SCRIPT+b"\x60"))
        partial = SIGNATURE + b"\x01"
        self.assertEqual(evaluate(SCRIPT, (partial,), PROFILE, input_count=1,
                                  output_count=1, signing=context(messages={1: MESSAGE})).stack,
                         (number(1),))
        with self.assertRaisesRegex(VMError, "spend-only"):
            evaluate(SCRIPT, (partial,), PROFILE, input_count=1, output_count=1,
                     signing=context(messages={1: MESSAGE}, kind="mint"))
        with self.assertRaisesRegex(UnsupportedFeature, "unavailable"):
            evaluate(SCRIPT, (partial,), PROFILE, input_count=1, output_count=1,
                     signing=context())
        with self.assertRaisesRegex(VMError, "paired output"):
            evaluate(SCRIPT, (SIGNATURE+b"\x02",), PROFILE, input_count=1,
                     output_count=0, signing=context(messages={2: MESSAGE}, output_count=0))

    def test_json_runner_stages_and_explicit_costs(self):
        values = {name: getattr(PROFILE, name) for name in (
            "max_script_bytes", "max_arguments", "max_element_bytes", "max_stack_items",
            "max_altstack_items", "max_vm_bytes", "max_ast_depth",
            "max_invocation_cost", "structural_byte_cost")}
        values["opcode_costs"] = {"20": {"base": 1, "operand_byte": 0,
                                          "result_byte": 1}, "bb": 1000}
        case = {"script": SCRIPT.hex(), "args": [SIGNATURE.hex()],
                "input_count": 1, "output_count": 1, "profile": values,
                "signing": {"selected_leaf_hash": branch_leaf_hash(SCRIPT).hex(),
                            "messages": {"0": MESSAGE.hex()},
                            "invocation_kind": "spend", "input_index": 0,
                            "output_count": 1}}
        result = run_invocation(case)
        self.assertTrue(result["accepted_invocation"], result)
        self.assertEqual(result["trace"], ["input_framed", "success_scanned",
                                            "decoded", "charged", "executed"])
        self.assertEqual(result["charged_cost"], 34 + 33 + 1000)
        case["signing"]["messages"]["0"] = (b"\x01"*32).hex()
        denied = run_invocation(case)
        self.assertFalse(denied["accepted_invocation"])
        self.assertEqual(denied["stage"], "execution")
        self.assertEqual(denied["charged_cost"], result["charged_cost"])
        del case["profile"]["max_invocation_cost"]
        self.assertEqual(run_invocation(case)["stage"], "input")

    def test_hashlock_invocation_without_signing_context(self):
        preimage = b"gallery hashlock preimage"
        script = b"\xb8\x20" + sha256(preimage).digest() + b"\x91"
        profile = {name: getattr(PROFILE, name) for name in (
            "max_script_bytes", "max_arguments", "max_element_bytes", "max_stack_items",
            "max_altstack_items", "max_vm_bytes", "max_ast_depth",
            "max_invocation_cost", "structural_byte_cost")}
        profile["opcode_costs"] = {"b8": 100, "20": 33, "91": 10}
        case = {"script": script.hex(), "args": [preimage.hex()],
                "input_count": 1, "output_count": 1, "profile": profile}
        result = run_invocation(case)
        self.assertTrue(result["accepted_invocation"], result)
        self.assertEqual(result["charged_cost"], len(script) + 100 + 33 + 10)
        case["args"] = [b"wrong".hex()]
        self.assertFalse(run_invocation(case)["accepted_invocation"])


if __name__ == "__main__":
    unittest.main()
