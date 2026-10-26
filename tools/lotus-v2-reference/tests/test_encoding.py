import json
import unittest
from pathlib import Path

from lotus_v2_reference.encoding import (
    DecodeError, Output, Profile, Reader, decode_output, encode_bytes,
    encode_compact_size, encode_int, encode_output, encode_vec,
)


FIXTURES = json.loads((Path(__file__).resolve().parents[1] / "fixtures/outputs-v1.json").read_text())
PROFILE = Profile(**FIXTURES["profile"])
ZERO = bytes(32)
ONE = b"\x01" + bytes(31)


def obj(row):
    return Output(row["flags"], row["value"], bytes.fromhex(row["token_id"]) if row["token_id"] else None,
                  tuple(bytes.fromhex(b) for b in row["branches"]), tuple(tuple(p) for p in row["paths"]))


class PrimitiveTests(unittest.TestCase):
    def test_integer_endianness_and_widths(self):
        for width in (1, 2, 4, 8, 16):
            for value in (0, 1, (1 << (width * 8)) - 1):
                wire = encode_int(value, width)
                reader = Reader(wire)
                self.assertEqual(reader.integer(width), value)
                reader.finish()
            with self.assertRaises(ValueError):
                encode_int(1 << (width * 8), width)
        self.assertEqual(encode_int(-1, 16, signed=True), b"\xff" * 16)
        self.assertEqual(Reader(b"\xff" * 16).integer(16, signed=True), -1)

    def test_compact_size_boundaries_and_nonminimal(self):
        for n in (0, 252, 253, 65535, 65536, 2**32 - 1, 2**32, 2**64 - 1):
            reader = Reader(encode_compact_size(n))
            self.assertEqual(reader.compact_size(max_value=2**64 - 1), n)
            reader.finish()
        for wire in (b"\xfd\xfc\x00", b"\xfe\xff\xff\x00\x00", b"\xff\xff\xff\xff\xff\x00\x00\x00\x00"):
            with self.assertRaises(DecodeError):
                Reader(wire).compact_size(max_value=2**64 - 1)
        with self.assertRaises(DecodeError):
            Reader(b"\xfd\xfd\x00").compact_size(max_value=252)
        with self.assertRaises(DecodeError):
            Reader(b"\xfd\xfd").compact_size(max_value=65535)

    def test_bytes_and_vec_bounds(self):
        payload = bytes(range(256))
        reader = Reader(encode_bytes(payload, max_length=256))
        self.assertEqual(reader.bytes_field(max_length=256), payload)
        reader.finish()
        with self.assertRaises(DecodeError):
            Reader(encode_compact_size(10)).bytes_field(max_length=9)
        with self.assertRaises(DecodeError):
            Reader(b"\x10\x00").bytes_field(max_length=16)
        with self.assertRaises(DecodeError):
            Reader(b"\x10\x00").vec(lambda: 0, max_count=16, min_item_bytes=1)
        self.assertEqual(encode_vec((1, 2), lambda i: bytes([i]), max_count=2), b"\x02\x01\x02")


class OutputTests(unittest.TestCase):
    def test_versioned_vectors_roundtrip(self):
        self.assertEqual(FIXTURES["schema"], "lotus-v2-reference/outputs/v1")
        for row in FIXTURES["valid"]:
            with self.subTest(row=row["name"]):
                expected = bytes.fromhex(row["wire"])
                self.assertEqual(encode_output(obj(row), PROFILE), expected)
                self.assertEqual(decode_output(expected, PROFILE), obj(row))

    def test_reject_malformed_frames(self):
        good = bytes.fromhex(FIXTURES["valid"][0]["wire"])
        bad = [good + b"\x00", good[:-1], b"\x04" + good[1:],
               good[:9] + b"\x00" + good[10:],  # no branch
               good[:9] + b"\x11" + good[10:],  # branch cap before allocation
               good[:-1] + b"\x01",  # index outside only branch
               good[:-2] + b"\x00\x00",  # empty path
               good[:9] + b"\xfd\x01\x00" + good[10:],  # nonminimal branch count
               good[:9] + b"\x01" + ZERO + b"\x00",  # spendable with zero paths
               b"\x01" + good[1:9] + ZERO + good[9:],  # zero token ID
               b"\x02" + good[1:-2] + b"\x01\x01\x00",  # burn with path
               good[:9] + b"\x02" + ZERO + ZERO + b"\x01\x01\x00"]  # repeated roots
        for wire in bad:
            with self.subTest(wire=wire.hex()), self.assertRaises(DecodeError):
                decode_output(wire, PROFILE)

    def test_reject_noncanonical_paths_and_profile(self):
        cases = [((0, 0),), ((1, 0),), ((2,),), ((0,), (0,)),
                 ((1,), (0,)), ((),), tuple()]
        for paths in cases:
            with self.subTest(paths=paths), self.assertRaises(ValueError):
                encode_output(Output(0, 0, None, (ZERO, ONE), paths), PROFILE)
        with self.assertRaises(ValueError):
            encode_output(Output(0, 0, None, (ZERO, ZERO), ((0,),)), PROFILE)
        with self.assertRaises(ValueError):
            encode_output(Output(0, 0, None, (ZERO,), ((0,),)), Profile(1, 1, 44, 8192))
        with self.assertRaises(ValueError):
            Profile(17, 16, 812, 8192)


if __name__ == "__main__":
    unittest.main()
