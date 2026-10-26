"""Development-profile coinbase. Candidate connector only, not ConnectTip.

The encoded flags-2 coinbase is 103 bytes. With a zero frame prefix the
monetary envelope adds 138, and 241 exceeds this genesis entitlement, so
advance rejects payout 0 before the overclaim check. No subsidy is invented.

One synthetic non-coinbase coin can fund an ordinary fee. The parent state
root is recomputed for that coin and is not the empty genesis root. The same
advance arguments then accept one coinbase output inside the resulting
entitlement. This Payment has no burn output, so the native burn of 10 is not
used.
"""

import unittest
from dataclasses import replace

from lotus_v2_reference.block import (
    OP_TRUE, OP_TRUE_COST, PAYMENT_TX_PROFILE, Coin, Parent, Payment, branch_leaf,
    connect_ordinary_block, disconnect, encode_native_output, encode_spend_core,
    empty_utxo_root, full_payment_bytes, state_root, utxo_root,
)
from lotus_v2_reference.block_seal import Header, block_id
from lotus_v2_reference.dev_genesis import (
    DEVELOPMENT_CHAIN_ID, DEVELOPMENT_GENESIS, DevelopmentGenesisFixture,
    make_development_genesis,
)
from lotus_v2_reference.encoding import Output
from lotus_v2_reference.monetary import OrdinaryTx, advance
from lotus_v2_reference.signing import (
    Input, Transaction, encode_transaction, identity_digests,
)

BRANCH = branch_leaf(OP_TRUE)
DEDUCTION = "insufficient coinbase entitlement for mandatory deduction"
FUNDING_TX = bytes([0x71]) + bytes(31)
FUNDING_VALUE = 50000
PAYMENT_VALUE = 1000


def _parent():
    fixture = DevelopmentGenesisFixture()
    if not make_development_genesis(bytes(32), 0, fixture) or fixture.header is None:
        raise AssertionError("development genesis")
    if fixture.state is None:
        raise AssertionError("development genesis state")
    return Parent(
        DEVELOPMENT_CHAIN_ID, 0, fixture.header.time, fixture.header.state_root,
        fixture.state, fixture.header,
    )


def _coinbase_tx(parent, value):
    raw = parent.header
    seal = raw if isinstance(raw, Header) else Header(
        raw.prev_id, raw.bits, raw.time, raw.nonce, raw.version, raw.size,
        raw.height, raw.tx_root, raw.state_root,
    )
    return Transaction(
        0,
        (Input(block_id(parent.chain_id, seal), 1, 0xFFFFFFFF, 2, 0, (), None),),
        (Output(0, value, None, (BRANCH,), ((0,),)),),
    )


def _advance(parent, value, wire_len):
    return advance(
        DEVELOPMENT_GENESIS, parent.monetary, work=parent.monetary.prev_work,
        transactions=(), coinbase_native_outputs=value, coinbase_native_burn=0,
        coinbase_bytes=wire_len, tx_frame_prefix_bytes=0,
        account_block_cost=0, enforce_block_cost=0,
    )


def _funded():
    fixture = DevelopmentGenesisFixture()
    if not make_development_genesis(bytes(32), 0, fixture) or fixture.header is None:
        raise AssertionError("development genesis")
    if fixture.state is None:
        raise AssertionError("development genesis state")
    monetary = fixture.state
    coin = Coin(
        FUNDING_TX, 3, FUNDING_VALUE, BRANCH, 0, fixture.header.time, False,
    )
    coins = {coin.key(): coin}
    recomputed = state_root(
        DEVELOPMENT_CHAIN_ID, 0, utxo_root(coins), monetary,
    )
    header = replace(fixture.header, state_root=recomputed)
    parent = Parent(
        DEVELOPMENT_CHAIN_ID, 0, fixture.header.time, recomputed, monetary, header,
    )
    return parent, coin, fixture.header.state_root


def _ordinary(coin):
    payment = Payment(coin.tx_id, coin.index, PAYMENT_VALUE)
    output = encode_native_output(payment.value, coin.branch)
    core = encode_spend_core(payment.spent_tx, payment.spent_index, payment.script)
    wire = full_payment_bytes(core, output, payment.arguments)
    return payment, OrdinaryTx(coin.value, payment.value, len(wire), 0, 0)


def _advance_funded(parent, payout, coinbase_len, ordinary):
    return advance(
        DEVELOPMENT_GENESIS, parent.monetary, work=parent.monetary.prev_work,
        transactions=(ordinary,), coinbase_native_outputs=payout,
        coinbase_native_burn=0, coinbase_bytes=coinbase_len,
        tx_frame_prefix_bytes=0, account_block_cost=OP_TRUE_COST,
        enforce_block_cost=OP_TRUE_COST,
    )


class DevelopmentCoinbaseTests(unittest.TestCase):
    def test_real_wire_exceeds_genesis_entitlement_and_restores(self):
        parent = _parent()
        wire = encode_transaction(_coinbase_tx(parent, 0), PAYMENT_TX_PROFILE)
        self.assertEqual(len(wire), len(encode_transaction(
            _coinbase_tx(parent, 1), PAYMENT_TX_PROFILE)))
        genesis_money = parent.monetary.to_bytes()
        for value in (0, 1):
            with self.assertRaises(ValueError) as direct:
                _advance(parent, value, len(wire))
            self.assertEqual(str(direct.exception), DEDUCTION)
            coins = {}
            with self.assertRaises(ValueError) as connected:
                connect_ordinary_block(
                    (Payment(bytes(32), 0, value, "coinbase", BRANCH),),
                    parent, coins, parent.monetary, DEVELOPMENT_GENESIS,
                    candidate_height=1, parent_mtp=parent.time, block_cap=0,
                )
            self.assertEqual(str(connected.exception), DEDUCTION)
            self.assertEqual(coins, {})
            self.assertEqual(parent.monetary.to_bytes(), genesis_money)

    def test_non_first_coinbase_and_immature_spend_restore(self):
        parent = _parent()
        value = 1
        genesis_money = parent.monetary.to_bytes()
        coins = {}
        with self.assertRaises(ValueError) as caught:
            connect_ordinary_block(
                (Payment(bytes(32), 0, value, "coinbase", BRANCH),
                 Payment(bytes(32), 0, value, "coinbase", BRANCH)),
                parent, coins, parent.monetary, DEVELOPMENT_GENESIS,
                candidate_height=1, parent_mtp=parent.time, block_cap=0,
            )
        self.assertEqual(str(caught.exception), "coinbase is not an ordinary transaction")
        self.assertEqual(coins, {})
        self.assertEqual(parent.monetary.to_bytes(), genesis_money)

        txid = identity_digests(
            _coinbase_tx(parent, value), PAYMENT_TX_PROFILE, parent.chain_id,
        ).txid
        coins = {}
        with self.assertRaises(ValueError) as caught:
            connect_ordinary_block(
                (Payment(bytes(32), 0, value, "coinbase", BRANCH),
                 Payment(txid, 0, value)),
                parent, coins, parent.monetary, DEVELOPMENT_GENESIS,
                candidate_height=1, parent_mtp=parent.time, block_cap=OP_TRUE_COST,
            )
        self.assertEqual(str(caught.exception), "coinbase maturity or future coin")
        self.assertEqual(coins, {})
        self.assertEqual(parent.monetary.to_bytes(), genesis_money)

    def test_fee_funded_coinbase_is_payable_and_restores(self):
        parent, funding, empty_root = _funded()
        self.assertFalse(funding.coinbase)
        self.assertEqual(
            empty_root,
            state_root(DEVELOPMENT_CHAIN_ID, 0, empty_utxo_root(), parent.monetary),
        )
        self.assertNotEqual(parent.state_root, empty_root)
        self.assertEqual(parent.header.state_root, parent.state_root)
        self.assertNotEqual(utxo_root({funding.key(): funding}), empty_utxo_root())
        genesis_money = parent.monetary.to_bytes()
        parent_utxo = utxo_root({funding.key(): funding})
        payment, ordinary = _ordinary(funding)
        self.assertGreaterEqual(funding.value - payment.value, ordinary.serialized_bytes)
        coinbase_len = len(encode_transaction(
            _coinbase_tx(parent, 0), PAYMENT_TX_PROFILE,
        ))
        self.assertEqual(coinbase_len, len(encode_transaction(
            _coinbase_tx(parent, 1), PAYMENT_TX_PROFILE,
        )))
        probe = _advance_funded(parent, 0, coinbase_len, ordinary)
        allowed = probe.actual_underclaim - probe.required_underclaim
        self.assertGreater(allowed, 0)
        paid_len = len(encode_transaction(
            _coinbase_tx(parent, allowed), PAYMENT_TX_PROFILE,
        ))
        over_len = len(encode_transaction(
            _coinbase_tx(parent, allowed + 1), PAYMENT_TX_PROFILE,
        ))
        self.assertEqual(paid_len, coinbase_len)
        self.assertEqual(over_len, coinbase_len)
        direct = _advance_funded(parent, allowed, paid_len, ordinary)
        with self.assertRaises(ValueError) as direct_over:
            _advance_funded(parent, allowed + 1, over_len, ordinary)
        self.assertEqual(str(direct_over.exception), "coinbase overclaims")

        def connect(transactions, coins):
            return connect_ordinary_block(
                transactions, parent, coins, parent.monetary, DEVELOPMENT_GENESIS,
                candidate_height=1, parent_mtp=parent.time, block_cap=OP_TRUE_COST,
            )

        def assert_parent(coins):
            self.assertEqual(coins, {funding.key(): funding})
            self.assertFalse(coins[funding.key()].coinbase)
            self.assertEqual(parent.monetary.to_bytes(), genesis_money)
            self.assertEqual(utxo_root(coins), parent_utxo)
            self.assertEqual(
                state_root(DEVELOPMENT_CHAIN_ID, 0, utxo_root(coins), parent.monetary),
                parent.state_root,
            )

        live = {funding.key(): funding}
        connected = connect(
            (Payment(bytes(32), 0, allowed, "coinbase", BRANCH), payment), live,
        )
        created = [coin for coin in live.values() if coin.coinbase]
        self.assertEqual(len(created), 1)
        self.assertTrue(created[0].coinbase)
        self.assertEqual(created[0].value, allowed)
        self.assertEqual(connected.monetary_bytes, direct.state.to_bytes())
        self.assertEqual(connected.transition, direct)
        self.assertEqual(connected.invocation_cost, OP_TRUE_COST)
        restored = disconnect(connected.undo, live)
        self.assertEqual(restored.to_bytes(), genesis_money)
        assert_parent(live)

        over = {funding.key(): funding}
        with self.assertRaises(ValueError) as caught:
            connect(
                (Payment(bytes(32), 0, allowed + 1, "coinbase", BRANCH), payment),
                over,
            )
        self.assertEqual(str(caught.exception), "coinbase overclaims")
        assert_parent(over)

        txid = identity_digests(
            _coinbase_tx(parent, allowed), PAYMENT_TX_PROFILE, parent.chain_id,
        ).txid
        immature = {funding.key(): funding}
        with self.assertRaises(ValueError) as caught:
            connect(
                (Payment(bytes(32), 0, allowed, "coinbase", BRANCH),
                 payment,
                 Payment(txid, 0, PAYMENT_VALUE)),
                immature,
            )
        self.assertEqual(str(caught.exception), "coinbase maturity or future coin")
        assert_parent(immature)


if __name__ == "__main__":
    unittest.main()
