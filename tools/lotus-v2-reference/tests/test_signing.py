"""Native payment-fixture sighash digests. Not a guessed preimage."""

import unittest
from dataclasses import replace

from coincurve import PublicKeyXOnly

from lotus_v2_reference.encoding import Output, Profile, decode_output
from lotus_v2_reference.signing import (
    Input, SigningError, Transaction, TxProfile, Witness, coins_root, decode_transaction,
    encode_transaction, identity_digests, own_input_hash, signing_message,
)
from lotus_v2_reference.vm import branch_leaf_hash

# test_signing.cpp PaymentFixture wire, profile, and chain.
WIRE = bytes.fromhex(
    "07000000000000000000000001000100"
    "1111111111111111111111111111111111111111111111111111111111111111"
    "00000000ffffffff0100012220f9308a019258c31049344f85f89d5229b531c845"
    "836f99b08601f113bce036f9bb000140"
    "170c710899dd02f994fe139b507662b88c0701019174aafa87329af0b65a9c0b84"
    "9c421cd740417ddeb4c6f70f4c1f50609b58c00fe8e41f9955a1091d5754aa"
    "00e80300000000000001d0c0707d9e50c9c3aedc8409e2df04bb920a3d9f669e80"
    "a36d2f68ea1e3f0d2a010100")
COIN_WIRE = bytes.fromhex(
    "00d00700000000000001d0c0707d9e50c9c3aedc8409e2df04bb920a3d9f669e80"
    "a36d2f68ea1e3f0d2a010100")
PROFILE = TxProfile(32, 32, 8, 8192, 16, 8192, 64)
OUTPUTS = Profile(16, 16, 812, 8192)
CHAIN = bytes(range(32))
PUBKEY = bytes.fromhex("f9308a019258c31049344f85f89d5229b531c845836f99b08601f113bce036f9")
EXPECTED = (
    "04a85123186ad1a571dc9878c2f2ae8e27329e6f409dcece4e47368428067ecd",
    "edd48a54efc1c6fb3a548525e570021b14c890bada1c0419a66cbdbd04c31c2a",
    "45d5a4af0c5a832acab582eb5b6fc5b5fadba6f0b670bd92e36256f6d5fd72e8",
)


class SighashFixtureTests(unittest.TestCase):
    def test_payment_fixture_modes_and_bip340(self):
        tx = decode_transaction(WIRE, PROFILE)
        coin = decode_output(COIN_WIRE, OUTPUTS)
        resolved = (coin,)
        identities = identity_digests(tx, PROFILE, CHAIN)
        self.assertEqual(identities.txid.hex(),
                         "6f097525dfa73f4c9eb428ed6e0e2e70efe63224479b8e0cede896a7e4caab2c")
        self.assertEqual(identities.txhash.hex(),
                         "b27873b6da521172796f7365a8b338e694879bc712d8d2ecabdb22d39378704d")
        self.assertEqual(coins_root(tx, resolved).hex(),
                         "deeba4111737eec866fe0d3998ca43ca4ab84b97afa2cc144e89e60f6dd3dd21")
        self.assertEqual(own_input_hash(tx, PROFILE, resolved, 0).hex(),
                         "e9c6f915cde3bab2ab260ddc74f007767042c4836b6c638b30d9e7397832e5f8")
        messages = tuple(
            signing_message(tx, PROFILE, CHAIN, resolved, 0, 0, mode).hex() for mode in range(3))
        self.assertEqual(messages, EXPECTED)
        signature = tx.inputs[0].witnesses[0].arguments[0]
        self.assertEqual(len(signature), 64)
        self.assertTrue(PublicKeyXOnly(PUBKEY).verify(signature, bytes.fromhex(messages[0])))
        other = bytearray(CHAIN)
        other[0] ^= 1
        cross = signing_message(tx, PROFILE, bytes(other), resolved, 0, 0, 0)
        self.assertNotEqual(cross, bytes.fromhex(messages[0]))
        self.assertFalse(PublicKeyXOnly(PUBKEY).verify(signature, cross))
        witness = replace(tx.inputs[0].witnesses[0], arguments=(b"x",))
        mutated = replace(tx, inputs=(replace(tx.inputs[0], witnesses=(witness,)),))
        mutated_ids = identity_digests(mutated, PROFILE, CHAIN)
        self.assertEqual(mutated_ids.txid, identities.txid)
        self.assertNotEqual(mutated_ids.txhash, identities.txhash)
        self.assertEqual(signing_message(mutated, PROFILE, CHAIN, resolved, 0, 0, 0),
                         bytes.fromhex(messages[0]))
        with self.assertRaises(SigningError):
            signing_message(tx, PROFILE, CHAIN, resolved, 0, 0, 3)

    def test_mint_mode0_width_and_rejected_partial_modes(self):
        tx = decode_transaction(WIRE, PROFILE)
        coin = decode_output(COIN_WIRE, OUTPUTS)
        mint_root = branch_leaf_hash(b"\x4e")
        mint = Input(mint_root, 0, 0xFFFFFFFF, 3, 0, (Witness(b"\x4e", (), (b"x",)),))
        minted = replace(tx, inputs=tx.inputs + (mint,))
        delta = bytes([1]) + bytes(15)
        resolved = (coin, None)
        message = signing_message(minted, PROFILE, CHAIN, resolved, 1, 0, 0, delta)
        self.assertEqual(message.hex(),
                         "e377de4d5eeef48cba47286c47dc88a1a61019c06f6f2f1e4ea2f263d60bb587")
        for mode in (1, 2):
            with self.assertRaises(SigningError):
                signing_message(minted, PROFILE, CHAIN, resolved, 1, 0, mode, delta)
        with self.assertRaises(SigningError):
            signing_message(minted, PROFILE, CHAIN, resolved, 1, 0, 0, None)
        with self.assertRaises(SigningError):
            signing_message(minted, PROFILE, CHAIN, resolved, 1, 0, 0, bytes(16))


# Native Coinbase() vector. Profile matches test_transaction.cpp.
COINBASE_PROFILE = TxProfile(32, 32, 8, 8192, 16, 8192, 64)
COINBASE_WIRE = bytes.fromhex(
    "07000000000000000000000001000100"
    "0707070707070707070707070707070707070707070707070707070707070707"
    "0c000000ffffffff0201035e4c00"
    "00e80300000000000001a88cef369f758aec3e594eaa4e8d08c9f12ef3f11bea"
    "972ec53a416a148f0605010100")


class CoinbaseWireTests(unittest.TestCase):
    def test_native_frame_round_trip_and_absent_data(self):
        tx = decode_transaction(COINBASE_WIRE, COINBASE_PROFILE)
        self.assertEqual(encode_transaction(tx, COINBASE_PROFILE), COINBASE_WIRE)
        self.assertEqual(tx.lock, 0)
        self.assertEqual(len(tx.inputs), 1)
        self.assertEqual(tx.inputs[0].flags, 2)
        self.assertEqual(tx.inputs[0].prev_index, 12)
        self.assertEqual(tx.inputs[0].sequence, 0xFFFFFFFF)
        self.assertEqual(tx.inputs[0].coinbase_data, bytes.fromhex("5e4c00"))
        self.assertFalse(tx.inputs[0].witnesses)
        self.assertEqual(tx.outputs[0].flags & 1, 0)
        absent_input = replace(tx.inputs[0], coinbase_data=None)
        absent_tx = replace(tx, inputs=(absent_input,))
        absent = encode_transaction(absent_tx, COINBASE_PROFILE)
        self.assertEqual(absent[57], 0)
        self.assertNotEqual(absent, COINBASE_WIRE)
        self.assertEqual(encode_transaction(
            decode_transaction(absent, COINBASE_PROFILE), COINBASE_PROFILE), absent)
        full = encode_transaction(absent_tx, COINBASE_PROFILE)
        core_id = identity_digests(absent_tx, COINBASE_PROFILE, bytes(32))
        self.assertEqual(len(core_id.txid), 32)
        self.assertNotEqual(core_id.txid, core_id.txhash)
        self.assertEqual(full, absent)
        maximum = replace(absent_input, coinbase_data=bytes([0x5e]) * 8192)
        maximum_tx = replace(tx, inputs=(maximum,))
        maximum_wire = encode_transaction(maximum_tx, COINBASE_PROFILE)
        self.assertEqual(encode_transaction(
            decode_transaction(maximum_wire, COINBASE_PROFILE), COINBASE_PROFILE),
            maximum_wire)

    def test_empty_overlong_nonminimal_and_token_reject(self):
        tx = decode_transaction(COINBASE_WIRE, COINBASE_PROFILE)
        empty = replace(tx, inputs=(replace(tx.inputs[0], coinbase_data=b""),))
        with self.assertRaises(SigningError) as caught:
            encode_transaction(empty, COINBASE_PROFILE)
        self.assertEqual(str(caught.exception), "coinbase data")
        overlong = replace(tx, inputs=(replace(tx.inputs[0], coinbase_data=bytes(8193)),))
        with self.assertRaises(SigningError) as caught:
            encode_transaction(overlong, COINBASE_PROFILE)
        self.assertEqual(str(caught.exception), "coinbase data")
        absent = encode_transaction(
            replace(tx, inputs=(replace(tx.inputs[0], coinbase_data=None),)),
            COINBASE_PROFILE)
        present_empty = bytearray(absent)
        present_empty[57] = 1
        present_empty.insert(58, 0)
        with self.assertRaises(SigningError):
            decode_transaction(bytes(present_empty), COINBASE_PROFILE)
        nonminimal = bytearray(COINBASE_WIRE)
        nonminimal[58] = 253
        nonminimal[59:59] = bytes((3, 0))
        with self.assertRaises(SigningError):
            decode_transaction(bytes(nonminimal), COINBASE_PROFILE)
        token = Output(1, tx.outputs[0].value, bytes([1]) + bytes(31),
                       tx.outputs[0].branches, tx.outputs[0].paths)
        with self.assertRaises(SigningError) as caught:
            encode_transaction(replace(tx, outputs=(token,)), COINBASE_PROFILE)
        self.assertEqual(str(caught.exception), "coinbase shape")
        with self.assertRaises(SigningError) as caught:
            signing_message(tx, COINBASE_PROFILE, bytes(32), (None,), 0, 0, 0)
        self.assertEqual(str(caught.exception), "coinbase is not signed")


if __name__ == "__main__":
    unittest.main()
