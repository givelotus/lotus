"""Reference genesis-profile payment and undo. Not a block accepted by lotusd."""

import unittest

from lotus_v2_reference.block import (
    OP_TRUE, OP_TRUE_COST, PAYMENT_VM, Coin, Parent, Payment, branch_leaf,
    connect_ordinary_block, disconnect, encode_native_output, encode_spend_core,
    empty_utxo_root, full_payment_bytes, state_root, tagged, transaction_id,
    transaction_root, utxo_root,
)
from lotus_v2_reference.block_seal import (
    HEADER_SIZE, Header, seal_child_header, serialize_header,
)
from lotus_v2_reference.dev_genesis import (
    DEVELOPMENT_CHAIN_ID, DEVELOPMENT_GENESIS, DevelopmentGenesisFixture,
    empty_transaction_root, make_development_genesis,
)
from lotus_v2_reference.encoding import encode_compact_size
from lotus_v2_reference.vm import VMError, evaluate

# Compact-target limit already accepted by the sealer for the genesis bits.
POW_LIMIT = bytes(31) + bytes([0xFF])
FUNDING = bytes([0x71]) + bytes(31)
BRANCH = branch_leaf(OP_TRUE)


class ChainParent:
    def __init__(self, header: Header, chain_id: bytes):
        self.header = header
        self.chain_id = chain_id


def _fail(script: bytes) -> str:
    try:
        evaluate(script, (), PAYMENT_VM, input_count=1, output_count=1)
    except VMError as exc:
        return str(exc)
    raise AssertionError("script succeeded")


class DevelopmentChainPaymentTests(unittest.TestCase):
    def test_op_true_payment_seals_and_undoes(self):
        fixture = DevelopmentGenesisFixture()
        self.assertTrue(make_development_genesis(bytes(32), 0, fixture))
        monetary = fixture.state
        genesis = fixture.header
        self.assertEqual(fixture.chain_id, DEVELOPMENT_CHAIN_ID)
        self.assertEqual(genesis.height, 0)
        parent_time = genesis.time
        parent_money = monetary.to_bytes()

        # Candidate height is 1, so this coin cannot use the script tests'
        # height-90 funding coin. That coin would still be in the future.
        coin = Coin(FUNDING, 3, 20000, BRANCH, 0, parent_time, False)
        self.assertFalse(coin.coinbase)
        coins = {coin.key(): coin}
        parent_utxo = utxo_root(coins)
        parent_state = state_root(DEVELOPMENT_CHAIN_ID, 0, parent_utxo, monetary)
        empty_state = state_root(
            DEVELOPMENT_CHAIN_ID, 0, empty_utxo_root(), monetary,
        )
        self.assertEqual(empty_state, genesis.state_root)
        self.assertNotEqual(parent_state, genesis.state_root)
        parent = Parent(
            DEVELOPMENT_CHAIN_ID, 0, parent_time, parent_state, monetary,
        )
        self.assertEqual(parent.height, 0)
        self.assertEqual(parent.time, genesis.time)

        payment = Payment(coin.tx_id, coin.index, 15000)
        self.assertEqual(payment.script, b"\x4e")
        self.assertEqual(payment.script, OP_TRUE)
        self.assertEqual(OP_TRUE_COST, 18)
        payments = (payment,)
        self.assertEqual(len(payments), 1)
        connected = connect_ordinary_block(
            payments, parent, coins, monetary, DEVELOPMENT_GENESIS,
            candidate_height=1, parent_mtp=parent_time, block_cap=OP_TRUE_COST,
        )
        self.assertEqual(connected.invocation_cost, 18)
        self.assertNotEqual(connected.monetary_bytes, parent_money)
        self.assertNotEqual(connected.state_root, parent_state)
        self.assertNotIn(coin.key(), coins)
        created = next(iter(coins.values()))
        self.assertFalse(created.coinbase)
        self.assertEqual(created.creation_height, 1)
        self.assertEqual(created.creation_parent_mtp, parent_time)

        again_coins = {coin.key(): coin}
        again = connect_ordinary_block(
            (Payment(coin.tx_id, coin.index, payment.value),),
            parent, again_coins, monetary, DEVELOPMENT_GENESIS,
            candidate_height=1, parent_mtp=parent_time, block_cap=OP_TRUE_COST,
        )
        self.assertEqual(again.monetary_bytes, connected.monetary_bytes)
        self.assertEqual(again.state_root, connected.state_root)

        core = encode_spend_core(payment.spent_tx, payment.spent_index, payment.script)
        output = encode_native_output(payment.value, created.branch)
        tx_id = transaction_id(DEVELOPMENT_CHAIN_ID, core, output)
        self.assertEqual(created.tx_id, tx_id)
        tx_header = (7).to_bytes(4, "little") + (0).to_bytes(8, "little")
        tx_header += (1).to_bytes(2, "little") + (1).to_bytes(2, "little")
        # Spend core omits the argument vector. This witness appends an empty one.
        full_input = core + b"\x00"
        self.assertEqual(full_payment_bytes(core, output), tx_header + full_input + output)
        outputs_root = tagged(
            "Lotus/v2/output", encode_compact_size(len(output)) + output,
        )
        self.assertEqual(
            tagged(
                "Lotus/v2/txid",
                DEVELOPMENT_CHAIN_ID + tx_header
                + tagged("Lotus/v2/inputcore", core) + outputs_root,
            ),
            tx_id,
        )
        tx_hash = tagged(
            "Lotus/v2/txhash",
            DEVELOPMENT_CHAIN_ID + tx_header
            + tagged("Lotus/v2/inputfull", full_input) + outputs_root,
        )
        self.assertNotEqual(tx_hash, tx_id)
        tx_root = transaction_root(((tx_hash, tx_id),))
        self.assertNotEqual(tx_root, transaction_root(()))
        self.assertNotEqual(tx_root, empty_transaction_root())

        seal_header = Header(
            genesis.prev_id, genesis.bits, genesis.time, genesis.nonce,
            genesis.version, genesis.size, genesis.height, genesis.tx_root,
            parent_state,
        )
        self.assertEqual(seal_header.height, 0)
        self.assertEqual(seal_header.time, genesis.time)
        self.assertNotEqual(seal_header.state_root, genesis.state_root)
        sealed = seal_child_header(
            ChainParent(seal_header, DEVELOPMENT_CHAIN_ID), connected, tx_root,
            genesis.version, genesis.time, genesis.size, genesis.bits, POW_LIMIT,
        )
        raw = serialize_header(sealed)
        self.assertEqual(len(raw), 134)
        self.assertEqual(len(raw), HEADER_SIZE)
        self.assertEqual(sealed.nonce, 0)
        self.assertEqual(raw[42:50], bytes(8))
        self.assertEqual(sealed.height, 1)
        self.assertEqual(sealed.tx_root, tx_root)
        self.assertEqual(sealed.state_root, connected.state_root)
        self.assertNotEqual(sealed.state_root, parent_state)
        self.assertNotEqual(sealed.state_root, genesis.state_root)

        restored = disconnect(connected.undo, coins)
        self.assertEqual(restored.to_bytes(), parent_money)
        self.assertEqual(monetary.to_bytes(), parent_money)
        self.assertEqual(coins, {coin.key(): coin})
        self.assertEqual(coins[coin.key()].encode(), coin.encode())
        self.assertFalse(coins[coin.key()].coinbase)
        self.assertEqual(utxo_root(coins), parent_utxo)
        self.assertEqual(
            state_root(DEVELOPMENT_CHAIN_ID, 0, utxo_root(coins), restored),
            parent_state,
        )

        self._assert_parent_unchanged(
            Payment(coin.tx_id, coin.index, payment.value, script=b"\x00"),
            parent, parent_utxo, parent_money, "unclean final stacks",
        )
        self.assertEqual(_fail(b"\x00"), "unclean final stacks")
        self._assert_parent_unchanged(
            Payment(coin.tx_id, coin.index, payment.value, "coinbase"),
            parent, parent_utxo, parent_money,
            "coinbase is not an ordinary transaction",
        )
        self._assert_parent_unchanged(
            Payment(coin.tx_id, coin.index, payment.value, "mint"),
            parent, parent_utxo, parent_money,
            "mint without matching positive token delta",
        )

    def _assert_parent_unchanged(self, payment, parent, parent_utxo, parent_money,
                                 message):
        coin = Coin(FUNDING, 3, 20000, BRANCH, 0, parent.time, False)
        coins = {coin.key(): coin}
        with self.assertRaises(ValueError) as caught:
            connect_ordinary_block(
                (payment,), parent, coins, parent.monetary, DEVELOPMENT_GENESIS,
                candidate_height=1, parent_mtp=parent.time, block_cap=OP_TRUE_COST,
            )
        self.assertEqual(str(caught.exception), message)
        self.assertEqual(coins, {coin.key(): coin})
        self.assertEqual(coins[coin.key()].encode(), coin.encode())
        self.assertEqual(parent.monetary.to_bytes(), parent_money)
        self.assertEqual(utxo_root(coins), parent_utxo)
        self.assertEqual(
            state_root(DEVELOPMENT_CHAIN_ID, 0, utxo_root(coins), parent.monetary),
            parent.state_root,
        )


if __name__ == "__main__":
    unittest.main()
