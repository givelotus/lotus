"""Development-chain genesis fixture. Not mainnet and not a block connection."""

import unittest

from lotus_v2_reference.block import empty_utxo_root, state_root
from lotus_v2_reference.dev_genesis import (
    DEVELOPMENT_CHAIN_ID, DEVELOPMENT_GENESIS, HEADER_BITS, HEADER_SIZE,
    HEADER_TIME, HEADER_VERSION, MAX_TIME, DevelopmentGenesisFixture, Header,
    empty_transaction_root, make_development_genesis, parse_header,
    serialize_header,
)
from lotus_v2_reference.monetary import MonetaryState, advance, initialize_genesis

# Recorded by the native commitment test for TransactionRoot of no transactions.
RECORDED_EMPTY_TX_ROOT = bytes.fromhex(
    "eebdd2bf2b0f92f1764c36eaef67a3ba72195a4206f2ea225db80605833beadb")


def _height_one(state):
    """Same AdvanceMonetary arguments as the monetary test's height-one step."""
    return advance(
        DEVELOPMENT_GENESIS, state, work=9, transactions=(),
        coinbase_native_outputs=0, coinbase_native_burn=0,
        coinbase_bytes=1, tx_frame_prefix_bytes=1,
        account_block_cost=4, enforce_block_cost=4,
    )


class DevelopmentGenesisTests(unittest.TestCase):
    def test_fixture_header_roundtrip_and_existing_monetary_step(self):
        self.assertEqual(HEADER_SIZE, 134)
        self.assertEqual(
            (DEVELOPMENT_GENESIS.boot_shift, DEVELOPMENT_GENESIS.tx_knee_shift,
             DEVELOPMENT_GENESIS.ema_shift, DEVELOPMENT_GENESIS.ema_min,
             DEVELOPMENT_GENESIS.linear_shift, DEVELOPMENT_GENESIS.quad_shift,
             DEVELOPMENT_GENESIS.tail_min, DEVELOPMENT_GENESIS.tail_max,
             DEVELOPMENT_GENESIS.dust_limit, DEVELOPMENT_GENESIS.min_fee_per_kb, DEVELOPMENT_GENESIS.genesis_tail,
             DEVELOPMENT_GENESIS.genesis_work),
            (2, 3, 2, 4, 3, 5, 2, 2000, 3, 1000, 200, 9),
        )
        fixture = DevelopmentGenesisFixture(header=Header(version=1))
        self.assertTrue(make_development_genesis(bytes(32), 0, fixture))
        self.assertEqual(fixture.chain_id, DEVELOPMENT_CHAIN_ID)
        self.assertEqual(fixture.chain_id, bytes(32))
        header = fixture.header
        self.assertIsNotNone(header)
        self.assertEqual(header.prev_id, bytes(32))
        self.assertEqual(header.nonce, 0)
        self.assertEqual(header.version, HEADER_VERSION)
        self.assertEqual(header.height, 0)
        self.assertLessEqual(header.time, MAX_TIME)
        self.assertEqual(header.time, HEADER_TIME)
        self.assertEqual(header.bits, HEADER_BITS)
        self.assertEqual(header.size, HEADER_SIZE)

        tx_root = empty_transaction_root()
        self.assertEqual(tx_root, RECORDED_EMPTY_TX_ROOT)
        self.assertEqual(header.tx_root, tx_root)

        recorded = initialize_genesis(
            DEVELOPMENT_GENESIS, bootstrap_reserve=9, tail_subsidy=200,
            genesis_work=9, ema_block_cost=4, coinbase_native_value=0,
        )
        self.assertEqual(fixture.state, recorded)
        self.assertEqual(fixture.state, MonetaryState(9, 200, 9, 4))
        wire = fixture.state.to_bytes()
        self.assertEqual(len(wire), 56)
        self.assertEqual((wire[0], wire[8], wire[16], wire[48]), (9, 200, 9, 4))
        with self.assertRaises(ValueError):
            initialize_genesis(
                DEVELOPMENT_GENESIS, bootstrap_reserve=9, tail_subsidy=200,
                genesis_work=9, ema_block_cost=4, coinbase_native_value=1,
            )

        utxo = empty_utxo_root()
        state_a = state_root(fixture.chain_id, 0, utxo, fixture.state)
        state_b = state_root(fixture.chain_id, 0, utxo, fixture.state)
        self.assertEqual(header.state_root, state_a)
        self.assertEqual(state_a, state_b)

        raw = serialize_header(header)
        self.assertIsNotNone(raw)
        self.assertEqual(len(raw), 134)
        prefix = bytes(32)
        prefix += HEADER_BITS.to_bytes(4, "little")
        prefix += HEADER_TIME.to_bytes(6, "little")
        prefix += (0).to_bytes(8, "little")
        prefix += HEADER_VERSION.to_bytes(4, "little")
        prefix += HEADER_SIZE.to_bytes(8, "little")
        prefix += (0).to_bytes(8, "little")
        self.assertEqual(len(prefix), 70)
        self.assertEqual(raw[:70], prefix)
        self.assertEqual(raw[70:102], RECORDED_EMPTY_TX_ROOT)
        self.assertEqual(raw[102:], state_a)
        parsed = parse_header(raw)
        self.assertEqual(parsed, header)
        self.assertEqual(serialize_header(parsed), raw)
        self.assertIsNone(parse_header(raw[:-1]))
        self.assertIsNone(parse_header(raw + b"\x00"))

        again = DevelopmentGenesisFixture()
        self.assertTrue(make_development_genesis(bytes(32), 0, again))
        self.assertEqual(again.header, header)
        self.assertEqual(again.state, fixture.state)

        self._reject(b"\x01" + bytes(31), 0)
        self._reject(bytes(31) + b"\x01", 0)
        self._reject(bytes(32), 1)
        self._reject(bytes(32), 2**64 - 1)
        self._reject(b"\x01" + bytes(31), 1)
        self._reject(bytes(31), 0)

        first = _height_one(fixture.state)
        second = _height_one(fixture.state)
        self.assertEqual(first.subsidy, 202)
        self.assertEqual(second.subsidy, 202)
        self.assertEqual(first.bootstrap_issued, 2)
        self.assertEqual(second.bootstrap_issued, 2)
        self.assertEqual(first.state.bootstrap_reserve, 7)
        self.assertEqual(second.state.bootstrap_reserve, 7)
        self.assertEqual(first.state.tail_subsidy, 200)
        self.assertEqual(second.state.tail_subsidy, 200)
        self.assertEqual(fixture.state.bootstrap_reserve, 9)
        transition_a = state_root(fixture.chain_id, 1, utxo, first.state)
        transition_b = state_root(fixture.chain_id, 1, utxo, second.state)
        self.assertEqual(transition_a, transition_b)
        self.assertNotEqual(transition_a, header.state_root)

    def _reject(self, prev_id, height):
        state = MonetaryState(123, 200, 9, 4)
        header = Header(version=0xDEADBEEF, nonce=7, height=99, prev_id=b"\xcd" * 32,
                        bits=1, time=2, size=3, tx_root=b"\x11" * 32,
                        state_root=b"\x22" * 32)
        chain_id = b"\xab" * 32
        rejected = DevelopmentGenesisFixture(chain_id=chain_id, state=state, header=header)
        self.assertFalse(make_development_genesis(prev_id, height, rejected))
        self.assertIs(rejected.chain_id, chain_id)
        self.assertIs(rejected.state, state)
        self.assertIs(rejected.header, header)
        self.assertEqual(rejected.header.version, 0xDEADBEEF)
        self.assertEqual(rejected.header.nonce, 7)
        self.assertEqual(rejected.header.height, 99)
        self.assertEqual(rejected.state.bootstrap_reserve, 123)
