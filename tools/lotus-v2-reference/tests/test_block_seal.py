"""Child-header seal. The 134-byte vector is the native serialization."""

import unittest

from lotus_v2_reference.block import Connected, Undo, state_root
from lotus_v2_reference.block_seal import (
    HEADER_SIZE, MAX_TIME, Header, block_id, decode_target, meets_target,
    parse_header, seal_child_header, serialize_header,
)
from lotus_v2_reference.monetary import MonetaryState

# lotus_v2_block_seal_test serialization for this same parent, connect result,
# tx root, version, time, size, and bits. state_root is StateRoot, not utxo_root.
NATIVE_HEADER = (
    "097e8dc58f4a3e803318cb94ba94b61e9aeeb1ccf25dd480e70c9c260d201729"
    "ffff001dc8c30000000000000000000000000200000090010000000000006400000000000000"
    "808182838485868788898a8b8c8d8e8f909192939495969798999a9b9c9d9e9f"
    "446219abb2c014b44d72ed377c0e3453e7d8099e2b039c2075a4958248f78b7f"
)


def _pattern(start: int) -> bytes:
    return bytes((start + i) & 0xFF for i in range(32))


MONEY = MonetaryState(9, 200, 9, 4)
POW_LIMIT = bytes(31) + bytes([0xFF])


class Parent:
    def __init__(self, header: Header, chain_id: bytes):
        self.header = header
        self.chain_id = chain_id


def _sample():
    chain_id = _pattern(0)
    parent = Parent(Header(
        _pattern(32), 0x1D00FFFF, 50000, 7, 1, HEADER_SIZE, 99, _pattern(64), _pattern(96),
    ), chain_id)
    utxo = _pattern(192)
    connected = Connected(
        utxo, state_root(chain_id, 100, utxo, MONEY), MONEY.to_bytes(),
        type("Transition", (), {"state": MONEY})(), Undo(), 0,
    )
    return parent, connected, _pattern(128)


class BlockSealTests(unittest.TestCase):
    def test_sealed_header_matches_native_bytes(self):
        parent, connected, tx_root = _sample()
        sealed = seal_child_header(
            parent, connected, tx_root, 2, 50120, 400, 0x1D00FFFF, POW_LIMIT,
        )
        raw = serialize_header(sealed)
        self.assertEqual(len(raw), 134)
        self.assertEqual(parse_header(raw), sealed)
        self.assertEqual(sealed.prev_id, block_id(parent.chain_id, parent.header))
        self.assertNotEqual(sealed.prev_id, parent.header.prev_id)
        self.assertEqual(sealed.height, 100)
        self.assertEqual(sealed.nonce, 0)
        self.assertEqual(sealed.version, 2)
        self.assertEqual(sealed.time, 50120)
        self.assertEqual(sealed.size, 400)
        self.assertEqual(sealed.bits, 0x1D00FFFF)
        self.assertEqual(sealed.tx_root, tx_root)
        self.assertNotEqual(sealed.tx_root, connected.utxo_root)
        self.assertEqual(sealed.state_root, connected.state_root)
        self.assertEqual(
            sealed.state_root, state_root(parent.chain_id, 100, connected.utxo_root, MONEY),
        )
        self.assertNotEqual(sealed.state_root, connected.utxo_root)
        self.assertEqual(raw[36:42], (50120).to_bytes(6, "little"))
        self.assertEqual(raw[42:50], bytes(8))
        self.assertEqual(raw[50:54], (2).to_bytes(4, "little"))
        self.assertEqual(raw[54:62], (400).to_bytes(8, "little"))
        self.assertEqual(raw[62:70], (100).to_bytes(8, "little"))
        self.assertEqual(raw[70:102], tx_root)
        self.assertEqual(raw[102:134], sealed.state_root)
        self.assertEqual(len(NATIVE_HEADER), 268)
        self.assertEqual(raw.hex(), NATIVE_HEADER)

        hard = decode_target(0x01010000, POW_LIMIT)
        self.assertEqual(hard, bytes([1]) + bytes(31))
        child = block_id(parent.chain_id, sealed)
        self.assertFalse(meets_target(child, hard))
        self.assertTrue(meets_target(child, bytes([0xFF]) * 32))
        self.assertTrue(meets_target(child, child))
        below = bytearray(child)
        for index in range(31, -1, -1):
            if below[index]:
                below[index] -= 1
                break
        self.assertFalse(meets_target(child, bytes(below)))
        self.assertEqual(sealed.nonce, 0)

    def test_rejections_match_native_reasons(self):
        parent, connected, tx_root = _sample()
        with self.assertRaisesRegex(ValueError, "timestamp above MAX_TIME"):
            seal_child_header(parent, connected, tx_root, 2, MAX_TIME + 1, 400, 0x1D00FFFF, POW_LIMIT)
        for bits in (0x1D80FFFF, 0x1D000000, 0x03000001):
            with self.assertRaisesRegex(ValueError, "compact target rejected"):
                seal_child_header(parent, connected, tx_root, 2, 50120, 400, bits, POW_LIMIT)
        with self.assertRaisesRegex(ValueError, "compact target rejected"):
            seal_child_header(
                parent, connected, tx_root, 2, 50120, 400, 0x1D00FFFF, bytes([1]) + bytes(31),
            )
        wrong = Connected(
            connected.utxo_root,
            state_root(parent.chain_id, 101, connected.utxo_root, MONEY),
            connected.monetary_bytes, connected.transition, Undo(), 0,
        )
        with self.assertRaisesRegex(ValueError, "connect result height"):
            seal_child_header(parent, wrong, tx_root, 2, 50120, 400, 0x1D00FFFF, POW_LIMIT)
        bad_bytes = bytearray(connected.monetary_bytes)
        bad_bytes[0] ^= 0xFF
        mismatched = Connected(
            connected.utxo_root, connected.state_root, bytes(bad_bytes),
            connected.transition, Undo(), 0,
        )
        with self.assertRaisesRegex(ValueError, "connect result monetary bytes"):
            seal_child_header(parent, mismatched, tx_root, 2, 50120, 400, 0x1D00FFFF, POW_LIMIT)
        tall = Parent(Header(
            parent.header.prev_id, parent.header.bits, parent.header.time, parent.header.nonce,
            parent.header.version, parent.header.size, 0xFFFFFFFFFFFFFFFF,
            parent.header.tx_root, parent.header.state_root,
        ), parent.chain_id)
        with self.assertRaisesRegex(ValueError, "parent header height"):
            seal_child_header(tall, connected, tx_root, 2, 50120, 400, 0x1D00FFFF, POW_LIMIT)
        stale = Parent(Header(
            parent.header.prev_id, parent.header.bits, MAX_TIME + 1, parent.header.nonce,
            parent.header.version, parent.header.size, parent.header.height,
            parent.header.tx_root, parent.header.state_root,
        ), parent.chain_id)
        with self.assertRaisesRegex(ValueError, "parent block id"):
            seal_child_header(stale, connected, tx_root, 2, 50120, 400, 0x1D00FFFF, POW_LIMIT)


if __name__ == "__main__":
    unittest.main()
