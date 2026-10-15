"""Witness success, failure, and rollback for ordinary block connect."""

import unittest

from coincurve import PrivateKey, PublicKeyXOnly

from lotus_v2_reference.block import (
    OP_TRUE, OP_TRUE_COST, PAYMENT_TX_PROFILE, PAYMENT_VM, Parent, Payment,
    branch_leaf, Coin, connect_ordinary_block, encode_native_output,
    encode_spend_core, state_root, transaction_id, utxo_root,
)
from lotus_v2_reference.encoding import Output
from lotus_v2_reference.monetary import MonetaryState, Profile
from lotus_v2_reference.signing import Input, Transaction, Witness, identity_digests, signing_message
from lotus_v2_reference.vm import UnsupportedFeature, VMError, branch_leaf_hash, evaluate

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

    def test_checksig_spend_connects_and_flipped_signature_rolls_back(self):
        pubkey = bytes.fromhex(
            "f9308a019258c31049344f85f89d5229b531c845836f99b08601f113bce036f9")
        secret = bytes(31) + bytes([3])
        self.assertEqual(PrivateKey(secret).public_key_xonly.format(), pubkey)
        script = b"\x20" + pubkey + b"\xbb"
        self.assertEqual(branch_leaf(script), branch_leaf_hash(script))
        branch = branch_leaf(script)
        coins = {
            coin.key(): coin
            for coin in (
                Coin(FUNDING, 3, 20000, branch, 90, 49000),
                Coin(bytes([0x72]) + bytes(31), 1, 8000, BRANCH, 90, 49000),
            )
        }
        root = utxo_root(coins)
        parent = Parent(CHAIN, 99, 50000, state_root(CHAIN, 99, root, MONEY), MONEY)
        parent_money = MONEY.to_bytes()
        parent_coins = tuple(coins[key].encode() for key in sorted(coins))
        created = Output(0, 15000, None, (branch,), ((0,),))
        resolved = Output(0, 20000, None, (branch,), ((0,),))
        blank = Transaction(
            0,
            (Input(FUNDING, 3, 0xFFFFFFFF, 1, 0, (Witness(script, (), (bytes(64),)),)),),
            (created,),
        )
        message = signing_message(blank, PAYMENT_TX_PROFILE, CHAIN, (resolved,), 0, 0, 0)
        signature = PrivateKey(secret).sign_schnorr(message, aux_randomness=bytes(32))
        self.assertEqual(len(signature), 64)
        self.assertTrue(PublicKeyXOnly(pubkey).verify(signature, message))
        signed = Transaction(
            0,
            (Input(FUNDING, 3, 0xFFFFFFFF, 1, 0, (Witness(script, (), (signature,)),)),),
            (created,),
        )
        self.assertEqual(signing_message(signed, PAYMENT_TX_PROFILE, CHAIN, (resolved,), 0, 0, 0),
                         message)
        self.assertEqual(
            identity_digests(signed, PAYMENT_TX_PROFILE, CHAIN).txid,
            transaction_id(CHAIN, encode_spend_core(FUNDING, 3, script),
                           encode_native_output(15000, branch)),
        )
        with self.assertRaises(UnsupportedFeature) as missing:
            evaluate(script, (signature,), PAYMENT_VM, input_count=1, output_count=1)
        self.assertEqual(str(missing.exception), "CHECKSIG requires an authenticated signing context")
        flipped = bytes([signature[0] ^ 1]) + signature[1:]
        self.assertFalse(PublicKeyXOnly(pubkey).verify(flipped, message))
        with self.assertRaises(ValueError) as caught:
            connect_ordinary_block(
                (Payment(FUNDING, 3, 15000, script=script, arguments=(flipped,)),),
                parent, coins, MONEY, MONETARY, candidate_height=100, parent_mtp=50000,
                block_cap=1_000_000,
            )
        self.assertEqual(str(caught.exception), "unclean final stacks")
        self.assertEqual(utxo_root(coins), root)
        self.assertEqual(MONEY.to_bytes(), parent_money)
        self.assertEqual(tuple(coins[key].encode() for key in sorted(coins)), parent_coins)
        self.assertIn((FUNDING, 3), coins)
        connected = connect_ordinary_block(
            (Payment(FUNDING, 3, 15000, script=script, arguments=(signature,)),),
            parent, coins, MONEY, MONETARY, candidate_height=100, parent_mtp=50000,
            block_cap=1_000_000,
        )
        self.assertGreater(connected.invocation_cost, 0)
        self.assertNotEqual(connected.utxo_root, root)
        self.assertNotEqual(connected.monetary_bytes, parent_money)
        self.assertNotIn((FUNDING, 3), coins)
        self.assertEqual(utxo_root(coins), connected.utxo_root)


if __name__ == "__main__":
    unittest.main()
