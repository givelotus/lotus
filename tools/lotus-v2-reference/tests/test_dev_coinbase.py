"""Development-profile coinbase. Candidate connector only, not ConnectTip.

The encoded flags-2 coinbase is 103 bytes. With a zero frame prefix the
monetary envelope adds 138, and 241 exceeds this genesis entitlement, so
advance rejects payout 0 before the overclaim check. No subsidy is invented.
"""

import unittest

from lotus_v2_reference.block import (
    OP_TRUE, OP_TRUE_COST, PAYMENT_TX_PROFILE, Parent, Payment, branch_leaf,
    connect_ordinary_block,
)
from lotus_v2_reference.block_seal import Header, block_id
from lotus_v2_reference.dev_genesis import (
    DEVELOPMENT_CHAIN_ID, DEVELOPMENT_GENESIS, DevelopmentGenesisFixture,
    make_development_genesis,
)
from lotus_v2_reference.encoding import Output
from lotus_v2_reference.monetary import advance
from lotus_v2_reference.signing import (
    Input, Transaction, encode_transaction, identity_digests,
)

BRANCH = branch_leaf(OP_TRUE)
DEDUCTION = "insufficient coinbase entitlement for mandatory deduction"


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


if __name__ == "__main__":
    unittest.main()
