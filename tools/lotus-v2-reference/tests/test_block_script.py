"""Witness success, failure, and rollback for ordinary block connect."""

import unittest

from lotus_v2_reference.block import (
    OP_TRUE, OP_TRUE_COST, PAYMENT_VM, Parent, Payment, branch_leaf, Coin,
    connect_ordinary_block, encode_native_output, encode_spend_core,
    state_root, transaction_id, utxo_root,
)
from lotus_v2_reference.monetary import MonetaryState, Profile
from lotus_v2_reference.vm import VMError, evaluate

CHAIN = bytes(range(32))
BRANCH = branch_leaf(OP_TRUE)
MONEY = MonetaryState(9, 200, 9, 4)
MONETARY = Profile(2, 3, 2, 4, 3, 5, 2, 2000, 3, 1000)
FUNDING = bytes([0x71]) + bytes(31)


def _world():
    coins = {
        coin.key(): coin
        for coin in (
            Coin(FUNDING, 3, 20000, BRANCH, 90, 49000),
            Coin(bytes([0x72]) + bytes(31), 1, 8000, BRANCH, 90, 49000),
        )
    }
    root = utxo_root(coins)
    parent = Parent(CHAIN, 99, 50000, state_root(CHAIN, 99, root, MONEY), MONEY)
    return coins, parent, root


def _fail(script: bytes) -> str:
    try:
        evaluate(script, (), PAYMENT_VM, input_count=1, output_count=1)
    except VMError as exc:
        return str(exc)
    raise AssertionError("script succeeded")


class OrdinaryScriptConnectTests(unittest.TestCase):
    def test_op_true_evaluate_cost_is_18_and_connects(self):
        result = evaluate(OP_TRUE, (), PAYMENT_VM, input_count=1, output_count=1)
        self.assertTrue(result.success)
        self.assertFalse(result.automatic)
        self.assertEqual(result.charged_cost, 18)
        self.assertEqual(result.charged_cost, OP_TRUE_COST)
        coins, parent, root = _world()
        connected = connect_ordinary_block(
            (Payment(FUNDING, 3, 15000),), parent, coins, MONEY, MONETARY,
            candidate_height=100, parent_mtp=50000, block_cap=OP_TRUE_COST,
        )
        self.assertEqual(connected.invocation_cost, 18)
        self.assertNotEqual(connected.utxo_root, root)
        self.assertNotIn((FUNDING, 3), coins)

    def test_push_zero_restores_parent_then_true_spend_connects(self):
        coins, parent, root = _world()
        parent_money = MONEY.to_bytes()
        script = b"\x00"
        with self.assertRaises(ValueError) as caught:
            connect_ordinary_block(
                (Payment(FUNDING, 3, 15000, script=script),), parent, coins, MONEY,
                MONETARY, candidate_height=100, parent_mtp=50000,
                block_cap=OP_TRUE_COST * 2,
            )
        self.assertEqual(str(caught.exception), _fail(script))
        self.assertEqual(str(caught.exception), "unclean final stacks")
        self.assertEqual(utxo_root(coins), root)
        self.assertEqual(MONEY.to_bytes(), parent_money)
        connected = connect_ordinary_block(
            (Payment(FUNDING, 3, 15000),), parent, coins, MONEY, MONETARY,
            candidate_height=100, parent_mtp=50000, block_cap=OP_TRUE_COST,
        )
        self.assertEqual(connected.invocation_cost, 18)
        self.assertNotEqual(utxo_root(coins), root)

    def test_verify_false_restores_parent_bytes(self):
        coins, parent, root = _world()
        parent_money = MONEY.to_bytes()
        script = b"\x00\x65"
        with self.assertRaises(ValueError) as caught:
            connect_ordinary_block(
                (Payment(FUNDING, 3, 15000, script=script),), parent, coins, MONEY,
                MONETARY, candidate_height=100, parent_mtp=50000,
                block_cap=OP_TRUE_COST * 2,
            )
        self.assertEqual(str(caught.exception), _fail(script))
        self.assertEqual(str(caught.exception), "VERIFY failed")
        self.assertNotEqual(str(caught.exception),
                            "reference block slice only prices OP_TRUE payments")
        self.assertEqual(utxo_root(coins), root)
        self.assertEqual(MONEY.to_bytes(), parent_money)
        self.assertIn((FUNDING, 3), coins)

    def test_second_false_script_drops_first_created_coin(self):
        coins, parent, root = _world()
        parent_money = MONEY.to_bytes()
        first = Payment(FUNDING, 3, 15000)
        created = transaction_id(
            parent.chain_id,
            encode_spend_core(first.spent_tx, first.spent_index, first.script),
            encode_native_output(first.value, BRANCH),
        )
        second = Payment(created, 0, 10000, script=b"\x00")
        with self.assertRaises(ValueError) as caught:
            connect_ordinary_block(
                (first, second), parent, coins, MONEY, MONETARY,
                candidate_height=100, parent_mtp=50000, block_cap=OP_TRUE_COST * 4,
            )
        self.assertEqual(str(caught.exception), "unclean final stacks")
        self.assertEqual(utxo_root(coins), root)
        self.assertEqual(MONEY.to_bytes(), parent_money)
        self.assertNotIn((created, 0), coins)
        self.assertIn((FUNDING, 3), coins)

    def test_vm_true_script_other_than_op_true_connects(self):
        # OP_1 OP_1 EQUAL is a true witness other than the one-byte OP_TRUE.
        script = b"\x4e\x4e\x91"
        result = evaluate(script, (), PAYMENT_VM, input_count=1, output_count=1)
        self.assertTrue(result.success)
        self.assertNotEqual(script, OP_TRUE)
        coins, parent, root = _world()
        connected = connect_ordinary_block(
            (Payment(FUNDING, 3, 15000, script=script),), parent, coins, MONEY,
            MONETARY, candidate_height=100, parent_mtp=50000,
            block_cap=result.charged_cost,
        )
        self.assertEqual(connected.invocation_cost, result.charged_cost)
        self.assertNotEqual(utxo_root(coins), root)


if __name__ == "__main__":
    unittest.main()
