"""Fixed P03 token rules and mint-invocation examples from examples/README.md."""

import unittest

from lotus_v2_reference.encoding import Output, Profile as OutputProfile
from lotus_v2_reference.vm import (ASSIGNED, SigningContext, VMError, VMProfile,
                                   branch_leaf_hash, evaluate, number)
from lotus_v2_reference.vm_context import InputView, InvocationContext
from lotus_v2_reference.vm_runner import run_invocation


RULES = bytes.fromhex("11" * 32)
WALLET = bytes.fromhex("22" * 32)
OLD = bytes.fromhex("33" * 32)
ISSUER = bytes.fromhex("F9308A019258C31049344F85F89D5229B531C845836F99B08601F113BCE036F9")
SIGNATURE = bytes.fromhex(
    "E907831F80848D1069A5371B402410364BDF1C5F8307B0084C55F1CE2DCA8215"
    "25F66A4A85EA8B71E482A74F382D2CE5EBEEE8FDB2172F477DF4900D310536C0")
COMPILED_WALLET = bytes.fromhex("843a62fb547cdf26e266a3c9143af56134644c103387ad6f0943e9d59a614b1a")
COMPILED_RULES = bytes.fromhex("fa95ca2bb2eba5626ab881662e9805f1451e9096302af48dee360eb47b69977e")
COMPILED_MINT = bytes.fromhex("1ab567acf7dac39958831a9a0312820c24dfdefa710a6b018edccef64b66cf88")
COMPILED_RULES_SCRIPT = bytes.fromhex("68007de2d0d79161007df2e8656364796a4e")
COMPILED_ISSUE_SCRIPT = bytes.fromhex(
    "4e7d20f9308a019258c31049344f85f89d5229b531c845836f99b08601f113bce036f9bc"
    "68007de2f29161007d20fa95ca2bb2eba5626ab881662e9805f1451e9096302af48dee36"
    "0eb47b69977ee8656364796a79794e")
OUTPUT_PROFILE = OutputProfile(16, 16, 812, 8192)
VM_PROFILE = VMProfile(512, 8, 128, 32, 8, 512, 8, 100_000, 1,
                       {op: 1 for op in ASSIGNED})

# Symbolic P03 transfer example, byte-for-byte hand assembly.
TRANSFER = bytes.fromhex("687ae2d0d79161f2e8656379646a4e")
# issue: DROP, issuer CHECKSIGVERIFY, minted_under_rules loop, ONE.
ISSUE = (bytes.fromhex("7920") + ISSUER + bytes.fromhex("bc687ae2f2916120") +
         RULES + bytes.fromhex("e8656379646a4e"))
UPGRADE = (bytes.fromhex("00677ad14ea6617ad720") + OLD +
           bytes.fromhex("9161d69e6379646379646a687ae220") + OLD +
           bytes.fromhex("9161e19f6379646a80ac65687ae2f2916120") + RULES +
           bytes.fromhex("e8656379646a4e"))


def token_output(value, token, *, paths=((0, 1),), branches=(WALLET, RULES)):
    return Output(1, value, token, branches, paths)


def native_output(value):
    return Output(0, value, None, (WALLET,), ((0,),))


def context(script, inputs, outputs, *, kind, index, root, path=None, branch=None, delta=None):
    return InvocationContext(tuple(inputs), tuple(outputs), kind, index, root,
                             OUTPUT_PROFILE, path, branch, delta)


def profile_json():
    values = {name: getattr(VM_PROFILE, name) for name in (
        "max_script_bytes", "max_arguments", "max_element_bytes", "max_stack_items",
        "max_altstack_items", "max_vm_bytes", "max_ast_depth",
        "max_invocation_cost", "structural_byte_cost")}
    values["opcode_costs"] = {f"{op:02x}": 1 for op in ASSIGNED}
    return values


def output_json(out):
    return {"flags": out.flags, "value": out.value,
            "token_id": None if out.token_id is None else out.token_id.hex(),
            "branches": [root.hex() for root in out.branches],
            "paths": [list(path) for path in out.paths]}


def invocation_json(ctx):
    return {"inputs": [{"flags": item.flags,
                        "coin": None if item.coin is None else output_json(item.coin),
                        "mint_token_id": None if item.mint_token_id is None else item.mint_token_id.hex()}
                       for item in ctx.inputs],
            "outputs": [output_json(out) for out in ctx.outputs],
            "invocation_kind": ctx.invocation_kind, "input_index": ctx.input_index,
            "branch_root": ctx.branch_root.hex(),
            "output_profile": dict(max_output_branches=16, max_output_paths=16,
                                   max_output_bytes=812, max_bytes_field=8192),
            "selected_path_index": ctx.selected_path_index,
            "selected_branch_index": ctx.selected_branch_index,
            "mint_delta": ctx.mint_delta}


class ContextTests(unittest.TestCase):
    def test_transfer_rules_and_bypass_paths(self):
        minted_token = bytes.fromhex("44"*32)
        coin = token_output(1000, minted_token)
        good = context(TRANSFER, (InputView(1, coin),),
                       (token_output(700, minted_token), token_output(250, minted_token)),
                       kind="spend", index=0, root=RULES, path=0, branch=1)
        self.assertEqual(evaluate(TRANSFER, (), VM_PROFILE, invocation=good).stack, (number(1),))
        # The root exists but one path omits it, so requires_branch is false.
        bypass = token_output(250, minted_token, paths=((0,), (0, 1)))
        for outputs in ((token_output(700, minted_token), bypass),
                        (token_output(700, minted_token),
                         Output(1, 250, minted_token, (WALLET,), ((0,),)))):
            bad = context(TRANSFER, (InputView(1, coin),), outputs,
                          kind="spend", index=0, root=RULES, path=0, branch=1)
            with self.subTest(output=outputs[1].branches), self.assertRaisesRegex(VMError, "VERIFY failed"):
                evaluate(TRANSFER, (), VM_PROFILE, invocation=bad)

    def test_mint_delta_stack_and_issue_signature(self):
        mint_root = branch_leaf_hash(ISSUE)
        good_output = token_output(1000, mint_root)
        mint = context(ISSUE, (InputView(3, mint_token_id=mint_root),), (good_output,),
                       kind="mint", index=0, root=mint_root, delta=1000)
        signing = SigningContext(branch_leaf_hash(ISSUE), {0: bytes(32)}, "mint", 0, 1)
        result = evaluate(ISSUE, (SIGNATURE,), VM_PROFILE, invocation=mint, signing=signing)
        self.assertEqual(result.stack, (number(1),))
        bad = context(ISSUE, (InputView(3, mint_token_id=mint_root),),
                      (token_output(1000, mint_root, paths=((0,), (0, 1))),),
                      kind="mint", index=0, root=mint_root, delta=1000)
        with self.assertRaisesRegex(VMError, "VERIFY failed"):
            evaluate(ISSUE, (SIGNATURE,), VM_PROFILE, invocation=bad, signing=signing)
        with self.assertRaisesRegex(VMError, "CHECKSIGVERIFY failed"):
            evaluate(ISSUE, (SIGNATURE,), VM_PROFILE, invocation=mint,
                     signing=SigningContext(branch_leaf_hash(ISSUE),
                                            {0: b"\x01" * 32}, "mint", 0, 1))
        # MAX_ARGUMENTS counts witness args; implicit minted N still counts for stack/memory.
        tight = VMProfile(512, 1, 128, 1, 8, 512, 8, 100_000, 1,
                          {op: 1 for op in ASSIGNED})
        with self.assertRaisesRegex(VMError, "initial stack"):
            evaluate(ISSUE, (SIGNATURE,), tight, invocation=mint, signing=signing)
        tiny_element = VMProfile(512, 1, 1, 8, 8, 512, 8, 100_000, 1,
                                 {op: 1 for op in ASSIGNED})
        with self.assertRaisesRegex(VMError, "initial element"):
            evaluate(b"\x4e", (), tiny_element, invocation=mint)

    def test_gallery_transaction_shape_uses_real_counts(self):
        mint_root = branch_leaf_hash(ISSUE)
        mint_inputs = (InputView(1, native_output(2000)),
                       InputView(3, mint_token_id=mint_root))
        minted = token_output(1000, mint_root)
        mint_outputs = (minted, native_output(500))
        mint = context(ISSUE, mint_inputs, mint_outputs, kind="mint", index=1,
                       root=mint_root, delta=1000)
        signing = SigningContext(mint_root, {0: bytes(32)}, "mint", 1, 2)
        self.assertEqual(evaluate(ISSUE, (SIGNATURE,), VM_PROFILE,
                                  invocation=mint, signing=signing).stack, (number(1),))
        transfer_inputs = (InputView(1, minted), InputView(1, native_output(500)))
        transfer_outputs = (token_output(700, mint_root),
                            token_output(250, mint_root), native_output(100))
        transfer = context(TRANSFER, transfer_inputs, transfer_outputs,
                           kind="spend", index=0, root=RULES, path=0, branch=1)
        self.assertEqual(evaluate(TRANSFER, (), VM_PROFILE,
                                  invocation=transfer).stack, (number(1),))
        bad_outputs = (transfer_outputs[0],
                       token_output(250, mint_root, paths=((0,), (0, 1))),
                       transfer_outputs[2])
        bypass = context(TRANSFER, transfer_inputs, bad_outputs,
                         kind="spend", index=0, root=RULES, path=0, branch=1)
        with self.assertRaisesRegex(VMError, "VERIFY failed"):
            evaluate(TRANSFER, (), VM_PROFILE, invocation=bypass)

    def test_exact_compiler_scripts_for_mint_and_transfer(self):
        self.assertEqual(branch_leaf_hash(COMPILED_ISSUE_SCRIPT), COMPILED_MINT)
        self.assertEqual(branch_leaf_hash(COMPILED_RULES_SCRIPT), COMPILED_RULES)
        funding = Output(0, 2000, None, (COMPILED_WALLET,), ((0,),))
        minted = Output(1, 1000, COMPILED_MINT,
                        (COMPILED_WALLET, COMPILED_RULES), ((0, 1),))
        issue = context(COMPILED_ISSUE_SCRIPT,
                        (InputView(1, funding), InputView(3, mint_token_id=COMPILED_MINT)),
                        (minted, funding), kind="mint", index=1,
                        root=COMPILED_MINT, delta=1000)
        signing = SigningContext(COMPILED_MINT, {0: bytes(32)}, "mint", 1, 2)
        self.assertEqual(evaluate(COMPILED_ISSUE_SCRIPT, (SIGNATURE,), VM_PROFILE,
                                  invocation=issue, signing=signing).stack, (number(1),))
        outputs = (Output(1, 700, COMPILED_MINT,
                          (COMPILED_WALLET, COMPILED_RULES), ((0, 1),)),
                   Output(1, 250, COMPILED_MINT,
                          (COMPILED_WALLET, COMPILED_RULES), ((0, 1),)),
                   funding)
        inputs = (InputView(1, minted), InputView(1, funding))
        transfer = context(COMPILED_RULES_SCRIPT, inputs, outputs, kind="spend",
                           index=0, root=COMPILED_RULES, path=0, branch=1)
        self.assertEqual(evaluate(COMPILED_RULES_SCRIPT, (), VM_PROFILE,
                                  invocation=transfer).stack, (number(1),))
        bypass = Output(1, 250, COMPILED_MINT,
                        (COMPILED_WALLET, COMPILED_RULES), ((0,), (0, 1)))
        bad = context(COMPILED_RULES_SCRIPT, inputs,
                      (outputs[0], bypass, funding), kind="spend", index=0,
                      root=COMPILED_RULES, path=0, branch=1)
        with self.assertRaisesRegex(VMError, "VERIFY failed"):
            evaluate(COMPILED_RULES_SCRIPT, (), VM_PROFILE, invocation=bad)

    def test_context_rejects_mismatch_and_unsafe_coin_reads(self):
        mint_root = branch_leaf_hash(ISSUE)
        with self.assertRaises(ValueError):
            context(ISSUE, (InputView(3, mint_token_id=mint_root),), (),
                    kind="mint", index=0, root=RULES, delta=1)
        mint = context(bytes.fromhex("4e"), (InputView(3, mint_token_id=mint_root),), (),
                       kind="mint", index=0, root=mint_root, delta=1)
        with self.assertRaisesRegex(VMError, "disagrees"):
            evaluate(bytes.fromhex("4e"), (), VM_PROFILE, input_count=2, invocation=mint)
        with self.assertRaisesRegex(VMError, "identities disagree"):
            evaluate(bytes.fromhex("4e"), (), VM_PROFILE, invocation=mint,
                     signing=SigningContext(branch_leaf_hash(b"\x4e"), {0: bytes(32)},
                                            "spend", 0, 0))
        # UTXO reads at a mint index are runtime errors after a valid context.
        read = bytes.fromhex("00d7")
        with self.assertRaisesRegex(VMError, "mint or coinbase"):
            evaluate(read, (), VM_PROFILE, invocation=mint)
        with self.assertRaises(ValueError):
            context(TRANSFER, (InputView(2),), (), kind="spend", index=0,
                    root=RULES, path=0, branch=1)

    def test_upgrade_accounts_old_token_burn_inside_mint_script(self):
        new_token = branch_leaf_hash(UPGRADE)
        old_coin = token_output(1000, OLD)
        outputs = (token_output(250, OLD), token_output(700, new_token))
        mint = context(UPGRADE, (InputView(1, old_coin),
                                 InputView(3, mint_token_id=new_token)), outputs,
                       kind="mint", index=1, root=new_token, delta=700)
        self.assertEqual(evaluate(UPGRADE, (), VM_PROFILE, invocation=mint).stack, (number(1),))
        excessive = context(UPGRADE, mint.inputs, outputs, kind="mint", index=1,
                            root=new_token, delta=800)
        with self.assertRaisesRegex(VMError, "VERIFY failed"):
            evaluate(UPGRADE, (), VM_PROFILE, invocation=excessive)
        bypass = context(UPGRADE, mint.inputs,
                         (token_output(250, OLD), token_output(700, new_token,
                                                              paths=((0,), (0, 1)))),
                         kind="mint", index=1, root=new_token, delta=700)
        with self.assertRaisesRegex(VMError, "VERIFY failed"):
            evaluate(UPGRADE, (), VM_PROFILE, invocation=bypass)

    def test_runner_uses_context_counts_and_reports_mint_cost(self):
        mint_root = branch_leaf_hash(ISSUE)
        mint = context(ISSUE, (InputView(3, mint_token_id=mint_root),),
                       (token_output(1000, mint_root),), kind="mint", index=0,
                       root=mint_root, delta=1000)
        case = {"script": ISSUE.hex(), "args": [SIGNATURE.hex()],
                "profile": profile_json(), "invocation": invocation_json(mint),
                "signing": {"selected_leaf_hash": branch_leaf_hash(ISSUE).hex(),
                            "messages": {"0": bytes(32).hex()},
                            "invocation_kind": "mint", "input_index": 0,
                            "output_count": 1}}
        accepted = run_invocation(case)
        self.assertTrue(accepted["accepted_invocation"], accepted)
        self.assertGreater(accepted["charged_cost"], len(ISSUE))
        case["output_count"] = 2
        self.assertFalse(run_invocation(case)["accepted_invocation"])


if __name__ == "__main__":
    unittest.main()
