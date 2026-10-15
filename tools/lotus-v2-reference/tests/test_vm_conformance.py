"""Independent P03 context/tree semantics; no node acceptance claim."""
import unittest
from dataclasses import replace
from hashlib import sha256
from lotus_v2_reference.encoding import Output, Profile, encode_output
from lotus_v2_reference.signing import Input, Transaction, TxProfile, Witness, SigningError
from lotus_v2_reference.vm import ASSIGNED, VMError, VMProfile, branch_leaf_hash, evaluate, number
from lotus_v2_reference.vm_context import authenticated_context

PROFILE = VMProfile(8192, 32, 8192, 64, 64, 65536, 16, 10000000, 1, {op: 1 for op in ASSIGNED})
TP = TxProfile(32, 32, 8, 8192, 32, 8192, 64)
OP = Profile(16, 16, 812, 8192)
CHAIN = bytes(range(32))


def push(data):
    if not data:
        return b"\x4c\x00"
    return bytes([len(data)]) + data if len(data) <= 75 else b'\x4c' + bytes([len(data)]) + data


def n(value):
    return push(number(value))


class Conformance(unittest.TestCase):
    def execute(self, body, expected=None, *, lock=0, sequence=0xffffffff, outputs=None):
        # A postfix equality makes each introspection result independently visible
        # while satisfying clean-stack finalization.
        script = body + (push(expected) + b'\x91' if expected is not None else b'\x4e')
        root = branch_leaf_hash(script)
        coin = Output(0, 2000, None, (root, bytes([0x55])*32), ((0,), (0, 1)))
        tx = Transaction(lock, (Input(bytes([0x11])*32, 3, sequence, 1, 0, (Witness(script),)),),
                         tuple(outputs) if outputs is not None else (replace(coin, value=1000),))
        ctx, signing = authenticated_context(tx, TP, CHAIN, (coin,), 0, 0)
        return evaluate(script, (), PROFILE, invocation=ctx, signing=signing)

    def test_transaction_and_input_fields(self):
        for body, expected in ((b'\xc8', number(7)), (b'\xc9', number(1)),
            (b'\xca', number(1)), (b'\xcb', number(0)), (b'\xcc', number(10)),
            (b'\xcd', number(1)), (b'\xcf', CHAIN), (n(0)+b'\xd1', number(1)),
            (n(0)+b'\xd2', bytes([0x11])*32), (n(0)+b'\xd3', number(3)),
            (n(0)+b'\xd4', number(8)), (n(0)+b'\xd5', number(0)),
            (n(0)+b'\xd6', number(2000)), (n(0)+b'\xd7', bytes(32)),
            (n(0)+b'\xd8', number(2)), (n(0)+n(1)+b'\xd9', bytes([0x55])*32),
            (n(0)+b'\xda', number(2)), (n(0)+n(1)+b'\xdb', b'\x02\x00\x01'),
            (n(0)+b'\xe3', number(2)), (n(0)+n(1)+b'\xe4', bytes([0x55])*32),
            (n(0)+b'\xe5', number(2)), (n(0)+n(1)+b'\xe6', b'\x02\x00\x01')):
            with self.subTest(body=body.hex()):
                self.assertTrue(self.execute(body, expected, lock=10<<8|1, sequence=8).success)
        # Reads of exact record and script are compared to independent related reads.
        self.assertTrue(self.execute(n(0)+b'\xdc'+n(0)+b'\xe7\x79\x79').success)
        self.assertTrue(self.execute(b'\xf0\xbe\xf2\x91\x65').success)
        self.assertTrue(self.execute(b'\xce\x79').success)
        self.assertTrue(self.execute(n(0)+b'\xc2\x79').success)

    def test_lock_boundaries_and_indices(self):
        self.assertTrue(self.execute(n(1)+n(10)+b'\xf3', lock=10<<8|1).success)
        self.assertTrue(self.execute(n(2)+n(9)+b'\xf4', sequence=(1<<22)|9).success)
        for body, kwargs in ((n(1)+n(11)+b'\xf3', {'lock':10<<8|1}),
            (n(1)+n(1)+b'\xf4', {}), (n(2)+n(10)+b'\xf4', {'sequence':(1<<22)|9}),
            (n(-1)+b'\xd2', {}), (n(0)+n(2)+b'\xdb', {})):
            with self.subTest(body=body.hex()), self.assertRaises(VMError):
                self.execute(body, **kwargs)

    def test_tree_hash_algorithms_and_negative_shapes(self):
        leaf, sibling = bytes([1])*32, bytes([2])*32
        from blake3 import blake3
        from lotus_v2_reference.signing import _tagged
        for indexed in (False, True):
            for algorithm in range(4):
                pair = sibling+leaf if indexed else leaf+sibling
                if algorithm == 0:
                    expected = _tagged('Lotus/v2/merkleidx' if indexed else 'Lotus/v2/branch',
                        b'\x01'+(b'\x00\x00' if indexed else b'')+pair)
                elif algorithm == 1:
                    expected = blake3(pair).digest()
                else:
                    expected = sha256(pair).digest()
                    if algorithm == 3: expected = sha256(expected).digest()
                body = push(leaf)+(push(b'\x01') if indexed else b'')+push(sibling)+n(algorithm)+bytes([0xc1 if indexed else 0xc0])
                self.assertTrue(self.execute(body, expected).success)
        self.assertTrue(self.execute(push(leaf)+push(sibling)+b'\xbf',
            _tagged('Lotus/v2/branch', b'\x01'+leaf+sibling)).success)
        for body in (push(leaf)+push(b'x')+n(0)+b'\xc0',
                     push(leaf)+push(b'')+push(b'')+n(0)+b'\xc1',
                     push(leaf)+push(b'')+n(4)+b'\xc0'):
            with self.assertRaises(VMError): self.execute(body)

    def test_continuation_and_exclusive(self):
        # Root is the current authenticated script root, avoiding circular byte literals.
        self.assertTrue(self.execute(n(0)+b'\xf2\xea\x65').success)
        self.assertTrue(self.execute(n(0)+b'\xf2\xe9\x65').success)
        wrong = Output(0, 1000, None, (bytes([0x44])*32,), ((0,),))
        with self.assertRaises(VMError): self.execute(n(0)+b'\xf2\xea\x65', outputs=(wrong,))

    def test_factory_authenticates_before_success_scan(self):
        script = b'\x5e'
        coin = Output(0, 1, None, (bytes(32),), ((0,),))
        tx = Transaction(0, (Input(bytes(32), 0, 0xffffffff, 1, 0, (Witness(script),)),), ())
        with self.assertRaisesRegex(SigningError, 'membership'):
            authenticated_context(tx, TP, CHAIN, (coin,), 0, 0)

    def test_factory_rejects_noncanonical_indices(self):
        script = b"\x4e"
        coin = Output(0, 1, None, (branch_leaf_hash(script),), ((0,),))
        tx = Transaction(0, (Input(bytes(32), 0, 0xffffffff, 1, 0, (Witness(script),)),), ())
        for input_index, witness_index in ((-1, 0), (True, 0), (0, -1), (0, False), (1, 0), (0, 1)):
            with self.subTest(indices=(input_index, witness_index)), self.assertRaises(ValueError):
                authenticated_context(tx, TP, CHAIN, (coin,), input_index, witness_index)

    def test_byte_conversion_bitwise_and_shifts(self):
        cases = ((n(-128)+n(1)+b"\x8a", b"\x80"),
            (n(0)+n(0)+b"\x8a", b""), (push(b"\x80")+b"\x8b", number(-128)),
            (push(b"\x01\x80")+b"\x8d", b"\xfe\x7f"),
            (push(b"\x81")+push(b"\x01")+b"\x8e", b"\x01"),
            (push(b"\x80")+push(b"\x01")+b"\x8f", b"\x81"),
            (push(b"\x81")+push(b"\x01")+b"\x90", b"\x80"),
            (push(b"\x01\x01")+n(8)+b"\x94", b"\x00\x01"),
            (push(b"\x01\x01")+n(-8)+b"\x94", b"\x01\x00"),
            (push(b"\xff")+n(-(1<<127))+b"\x94", b"\x00"),
            (push(b"\x00\x00")+push(b"\x00")+b"\x93\x88", b"\x00\x00\x00"))
        for body, expected in cases:
            with self.subTest(body=body.hex()): self.assertTrue(self.execute(body, expected).success)
        for body in (n(128)+n(1)+b"\x8a", push(bytes(17))+b"\x8b",
                     push(b"x")+push(b"xx")+b"\x8e"):
            with self.assertRaises(VMError): self.execute(body)
