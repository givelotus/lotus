"""Reference two-block undo. Not a block accepted by lotusd, and not ConnectTip."""

import unittest

from lotus_v2_reference.block import (
    OP_TRUE, OP_TRUE_COST, Coin, Parent, Payment, branch_leaf,
    connect_ordinary_block, disconnect, encode_native_output, encode_spend_core,
    empty_utxo_root, state_root, tagged, transaction_id, transaction_root,
    utxo_root,
)
from lotus_v2_reference.block_seal import (
    HEADER_SIZE, Header, seal_child_header, serialize_header,
)
from lotus_v2_reference.dev_genesis import (
    DEVELOPMENT_CHAIN_ID, DEVELOPMENT_GENESIS, DevelopmentGenesisFixture,
    make_development_genesis,
)
from lotus_v2_reference.encoding import encode_compact_size

# Compact-target limit already accepted by the sealer for the genesis bits.
POW_LIMIT = bytes(31) + bytes([0xFF])
FUNDING = bytes([0x71]) + bytes(31)
BRANCH = branch_leaf(OP_TRUE)


class ChainParent:
    def __init__(self, header: Header, chain_id: bytes):
        self.header = header
        self.chain_id = chain_id


def _coin_bytes(coins):
    return tuple((key, coins[key].encode()) for key in sorted(coins))


def _payment_root(chain_id, spent_tx, spent_index, value, branch, script=OP_TRUE):
    core = encode_spend_core(spent_tx, spent_index, script)
    output = encode_native_output(value, branch)
    tx_id = transaction_id(chain_id, core, output)
    tx_header = (7).to_bytes(4, "little") + (0).to_bytes(8, "little")
    tx_header += (1).to_bytes(2, "little") + (1).to_bytes(2, "little")
    # Spend core omits the argument vector. This witness appends an empty one.
    full_input = core + b"\x00"
    outputs_root = tagged(
        "Lotus/v2/output", encode_compact_size(len(output)) + output,
    )
    tx_hash = tagged(
        "Lotus/v2/txhash",
        chain_id + tx_header + tagged("Lotus/v2/inputfull", full_input) + outputs_root,
    )
    return transaction_root(((tx_hash, tx_id),)), tx_id


class TwoBlockUndoTests(unittest.TestCase):
    def test_two_ordinary_blocks_undo_to_the_parent_seed(self):
        self.assertEqual(OP_TRUE, b"\x4e")
        self.assertEqual(OP_TRUE_COST, 18)
        fixture = DevelopmentGenesisFixture()
        self.assertTrue(make_development_genesis(bytes(32), 0, fixture))
        monetary = fixture.state
        genesis = fixture.header
        self.assertEqual(fixture.chain_id, DEVELOPMENT_CHAIN_ID)
        self.assertEqual(genesis.height, 0)
        parent_time = genesis.time
        parent_money = monetary.to_bytes()

        coin = Coin(FUNDING, 3, 20000, BRANCH, 0, parent_time, False)
        self.assertFalse(coin.coinbase)
        coins = {coin.key(): coin}
        seed_coins = _coin_bytes(coins)
        parent_utxo = utxo_root(coins)
        parent_state = state_root(DEVELOPMENT_CHAIN_ID, 0, parent_utxo, monetary)
        empty_state = state_root(
            DEVELOPMENT_CHAIN_ID, 0, empty_utxo_root(), monetary,
        )
        self.assertEqual(empty_state, genesis.state_root)
        self.assertNotEqual(parent_state, empty_state)
        self.assertNotEqual(parent_state, genesis.state_root)
        parent = Parent(
            DEVELOPMENT_CHAIN_ID, 0, parent_time, parent_state, monetary,
        )
        self.assertEqual(parent.height, 0)
        self.assertEqual(parent.monetary, monetary)
        self.assertEqual(parent.monetary.to_bytes(), parent_money)

        payment = Payment(coin.tx_id, coin.index, 15000)
        self.assertEqual(payment.script, b"\x4e")
        self.assertEqual(payment.script, OP_TRUE)
        first = connect_ordinary_block(
            (payment,), parent, coins, monetary, DEVELOPMENT_GENESIS,
            candidate_height=1, parent_mtp=parent_time, block_cap=OP_TRUE_COST,
        )
        self.assertEqual(first.invocation_cost, 18)
        self.assertNotEqual(first.monetary_bytes, parent_money)
        self.assertNotEqual(first.state_root, parent_state)
        self.assertNotIn(coin.key(), coins)
        self.assertEqual(len(coins), 1)
        created = next(iter(coins.values()))
        self.assertFalse(created.coinbase)
        self.assertEqual(created.creation_height, 1)
        self.assertEqual(created.value, payment.value)
        tx_root, tx_id = _payment_root(
            DEVELOPMENT_CHAIN_ID, payment.spent_tx, payment.spent_index,
            payment.value, created.branch,
        )
        self.assertEqual(created.tx_id, tx_id)

        seal_header = Header(
            genesis.prev_id, genesis.bits, genesis.time, genesis.nonce,
            genesis.version, genesis.size, genesis.height, genesis.tx_root,
            parent_state,
        )
        self.assertEqual(seal_header.height, 0)
        self.assertNotEqual(seal_header.state_root, genesis.state_root)
        sealed = seal_child_header(
            ChainParent(seal_header, DEVELOPMENT_CHAIN_ID), first, tx_root,
            genesis.version, genesis.time, genesis.size, genesis.bits, POW_LIMIT,
        )
        raw = serialize_header(sealed)
        self.assertEqual(len(raw), 134)
        self.assertEqual(len(raw), HEADER_SIZE)
        self.assertEqual(sealed.nonce, 0)
        self.assertEqual(raw[42:50], bytes(8))
        self.assertEqual(sealed.height, 1)
        self.assertEqual(sealed.tx_root, tx_root)
        self.assertEqual(sealed.state_root, first.state_root)

        block1_coins = _coin_bytes(coins)
        block1_money = first.monetary_bytes
        block1_state = first.transition.state
        self.assertEqual(block1_state.to_bytes(), block1_money)
        parent2 = Parent(
            DEVELOPMENT_CHAIN_ID, 1, sealed.time, first.state_root, block1_state,
        )
        self.assertEqual(parent2.height, 1)
        self.assertEqual(parent2.state_root, first.state_root)
        self.assertEqual(parent2.monetary.to_bytes(), block1_money)
        self.assertNotEqual(parent2.monetary.to_bytes(), parent_money)

        rejected = Payment(created.tx_id, created.index, 10000, script=b"\x00")
        with self.assertRaises(ValueError) as caught:
            connect_ordinary_block(
                (rejected,), parent2, coins, block1_state, DEVELOPMENT_GENESIS,
                candidate_height=2, parent_mtp=parent2.time, block_cap=OP_TRUE_COST,
            )
        self.assertEqual(str(caught.exception), "unclean final stacks")
        self.assertEqual(_coin_bytes(coins), block1_coins)
        self.assertEqual(block1_state.to_bytes(), block1_money)
        self.assertEqual(monetary.to_bytes(), parent_money)
        self.assertIn(created.key(), coins)
        self.assertNotIn(coin.key(), coins)

        second_payment = Payment(created.tx_id, created.index, 10000)
        self.assertEqual(second_payment.script, OP_TRUE)
        second = connect_ordinary_block(
            (second_payment,), parent2, coins, block1_state, DEVELOPMENT_GENESIS,
            candidate_height=2, parent_mtp=parent2.time, block_cap=OP_TRUE_COST,
        )
        self.assertEqual(second.invocation_cost, 18)
        self.assertNotEqual(second.monetary_bytes, block1_money)
        self.assertNotEqual(second.state_root, first.state_root)
        self.assertNotIn(created.key(), coins)
        self.assertNotIn(coin.key(), coins)
        self.assertEqual(len(coins), 1)
        spent_child = next(iter(coins.values()))
        self.assertFalse(spent_child.coinbase)
        self.assertEqual(spent_child.creation_height, 2)
        tx_root2, tx_id2 = _payment_root(
            DEVELOPMENT_CHAIN_ID, second_payment.spent_tx, second_payment.spent_index,
            second_payment.value, spent_child.branch,
        )
        self.assertEqual(spent_child.tx_id, tx_id2)
        sealed2 = seal_child_header(
            ChainParent(sealed, DEVELOPMENT_CHAIN_ID), second, tx_root2,
            genesis.version, sealed.time, genesis.size, genesis.bits, POW_LIMIT,
        )
        raw2 = serialize_header(sealed2)
        self.assertEqual(len(raw2), 134)
        self.assertEqual(len(raw2), HEADER_SIZE)
        self.assertEqual(sealed2.nonce, 0)
        self.assertEqual(raw2[42:50], bytes(8))
        self.assertEqual(sealed2.height, 2)
        self.assertEqual(sealed2.tx_root, tx_root2)
        self.assertEqual(sealed2.state_root, second.state_root)
        self.assertNotEqual(sealed2.state_root, sealed.state_root)

        restored = disconnect(second.undo, coins)
        self.assertEqual(restored.to_bytes(), block1_money)
        self.assertEqual(block1_state.to_bytes(), block1_money)
        self.assertEqual(_coin_bytes(coins), block1_coins)
        self.assertIn(created.key(), coins)
        self.assertNotIn(coin.key(), coins)
        self.assertNotIn(spent_child.key(), coins)
        self.assertEqual(
            state_root(DEVELOPMENT_CHAIN_ID, 1, utxo_root(coins), restored),
            first.state_root,
        )

        restored = disconnect(first.undo, coins)
        self.assertEqual(restored.to_bytes(), parent_money)
        self.assertEqual(monetary.to_bytes(), parent_money)
        self.assertEqual(_coin_bytes(coins), seed_coins)
        self.assertIn(coin.key(), coins)
        self.assertNotIn(created.key(), coins)
        self.assertFalse(coins[coin.key()].coinbase)
        self.assertEqual(coins[coin.key()].encode(), coin.encode())
        self.assertEqual(utxo_root(coins), parent_utxo)
        self.assertEqual(
            state_root(DEVELOPMENT_CHAIN_ID, 0, utxo_root(coins), restored),
            parent_state,
        )


if __name__ == "__main__":
    unittest.main()
