#!/usr/bin/env python3
"""Independent PSBT framing/schema fixtures; NOT a signer or consensus validator."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

MAGIC = b'psbt\xff'
PREFIX = b'\xfc\x08lotus-v2'
VERSION = bytes.fromhex('0100564c')
MAX_TOTAL, MAX_KEY, MAX_VALUE, MAX_RECORDS = 16777216, 1024, 8388608, 4096


def cs(n):
    if n < 253:
        return bytes([n])
    width, tag = (2, 253) if n <= 65535 else (4, 254) if n <= 0xffffffff else (8, 255)
    return bytes([tag]) + n.to_bytes(width, 'little')


def blob(b):
    return cs(len(b)) + b


def prop(n, data=b''):
    return PREFIX + cs(n) + data


class Reader:
    def __init__(self, raw):
        self.raw, self.pos = raw, 0

    def take(self, n):
        if n > len(self.raw) - self.pos:
            raise ValueError('truncated')
        b = self.raw[self.pos:self.pos+n]
        self.pos += n
        return b

    def number(self, width):
        return int.from_bytes(self.take(width), 'little')

    def compact(self, cap=MAX_TOTAL):
        tag = self.number(1)
        n = tag if tag < 253 else self.number({253: 2, 254: 4, 255: 8}[tag])
        if tag >= 253 and n < {253: 253, 254: 65536, 255: 2**32}[tag]:
            raise ValueError('nonminimal')
        if n > cap:
            raise ValueError('limit')
        return n

    def bytes(self, cap):
        return self.take(self.compact(cap))

    def done(self):
        if self.pos != len(self.raw):
            raise ValueError('trailing')


def key_parts(key):
    r = Reader(key)
    typ = r.compact()
    if typ != 252:
        return typ, None, key[r.pos:]
    identifier = r.bytes(MAX_KEY)
    subtype = r.compact()
    return typ, (identifier, subtype), key[r.pos:]


def read_map(r):
    result = {}
    while True:
        key = r.bytes(MAX_KEY)
        if not key:
            return result
        if key in result:
            raise ValueError('duplicate')
        if len(result) >= MAX_RECORDS:
            raise ValueError('records')
        key_parts(key)
        result[key] = r.bytes(MAX_VALUE)


def write_map(m):
    return b''.join(blob(k) + blob(v) for k, v in sorted(m.items())) + b'\0'


def encode(maps):
    return MAGIC + b''.join(write_map(m) for m in maps)


def vector(raw):
    r = Reader(raw)
    args = [r.bytes(8192) for _ in range(r.compact(65535))]
    r.done()
    return args


def native_output(r, legacy=False):
    flag = r.number(1)
    r.take(8)
    if legacy and flag == 128:
        r.bytes(10000)
        return
    if flag & ~7 or (flag & 2 and flag & 4):
        raise ValueError('output flags')
    for present in (flag & 1, flag & 4):
        if present and r.take(32) == bytes(32):
            raise ValueError('zero output commitment')
    branches = [r.take(32) for _ in range(r.compact(16))]
    if not branches or len(set(branches)) != len(branches):
        raise ValueError('branches')
    paths = []
    for _ in range(r.compact(16)):
        path = [r.compact(15) for _ in range(r.compact(16))]
        if not path or path != sorted(set(path)) or path[-1] >= len(branches):
            raise ValueError('path')
        paths.append(path)
    if paths != sorted(paths) or len({tuple(p) for p in paths}) != len(paths):
        raise ValueError('paths')
    if bool(flag & 2) == bool(paths):
        raise ValueError('burn paths')


def template(raw):
    r = Reader(raw)
    if r.number(4) != 7:
        raise ValueError('tx version')
    r.take(8)
    ni, no = r.number(2), r.number(2)
    if not 1 <= ni <= 256 or no > 256:
        raise ValueError('counts')
    inputs = []
    for _ in range(ni):
        outpoint = r.take(36)
        r.take(4)
        if r.number(1) != 1:
            raise ValueError('spend only')
        r.compact(15)
        nw = r.compact(16)
        if not nw:
            raise ValueError('witness count')
        for _ in range(nw):
            r.bytes(10000)
            r.take(32 * r.compact(64))
            if r.compact(65535):
                raise ValueError('template arguments')
        inputs.append((outpoint, nw))
    for _ in range(no):
        native_output(r)
    r.done()
    return inputs, no


def check_map(m, scope):
    widths = {'g': {1: (0, 32), 2: (0, None), 3: (0, 32)},
              'i': {1: (0, None), 2: (2, None), 3: (4, None),
                    4: (4, None), 5: (2, None), 6: (0, None), 7: (33, None)},
              'o': {1: (33, None)}}[scope]
    for key, value in m.items():
        typ, proprietary, data = key_parts(key)
        if typ != 252:
            if scope != 'g' or typ not in (4, 5, 251) or data:
                raise ValueError('standard key')
            continue
        identifier, sub = proprietary
        if identifier != b'lotus-v2':
            continue
        if sub not in widths:
            if sub < 128:
                raise ValueError('critical subtype')
            continue
        kd, vd = widths[sub]
        if len(data) != kd or (vd is not None and len(value) != vd):
            raise ValueError('field width')
        if (scope == 'i' and sub == 7) or (scope == 'o' and sub == 1):
            if data[0] not in (2, 3) or not 4 <= len(value) <= 1024 or len(value) % 4:
                raise ValueError('origin')


def decode(raw):
    if len(raw) > MAX_TOTAL:
        raise ValueError('total')
    r = Reader(raw)
    if r.take(5) != MAGIC:
        raise ValueError('magic')
    g = read_map(r)
    check_map(g, 'g')
    if g.get(b'\xfb') != VERSION or prop(1) not in g or prop(2) not in g:
        raise ValueError('required global')
    inputs, no = template(g[prop(2)])
    for key, expected in ((b'\x04', len(inputs)), (b'\x05', no)):
        if key not in g:
            raise ValueError('count missing')
        count = Reader(g[key])
        if count.compact(256) != expected:
            raise ValueError('count mismatch')
        count.done()
    maps = [g]
    for scope, count in (('i', len(inputs)), ('o', no)):
        for i in range(count):
            m = read_map(r)
            check_map(m, scope)
            maps.append(m)
            if scope != 'i':
                continue
            op, nw = inputs[i]
            for key, value in m.items():
                _, p, data = key_parts(key)
                if p is None or p[0] != b'lotus-v2' or p[1] >= 128:
                    continue
                sub = p[1]
                if sub == 1:
                    c = Reader(value)
                    if len(value) > 10085 or c.take(36) != op:
                        raise ValueError('coin outpoint')
                    output = c.bytes(10012)
                    if output[0] != 128 and output[0] & 2:
                        raise ValueError('burn coin')
                    oc = Reader(output)
                    native_output(oc, True)
                    oc.done()
                    c.take(16)
                    if c.number(1) > 1 or c.number(1) != 2:
                        raise ValueError('coin metadata')
                    c.take(16)
                    c.done()
                elif sub in (2, 3, 4, 5):
                    w = int.from_bytes(data[:2], 'little')
                    if w >= nw:
                        raise ValueError('witness position')
                    if sub in (2, 5):
                        vector(value)
                    elif sub == 3:
                        if len(value) < 2 or value[0] > 2 or value[1] > 2:
                            raise ValueError('request')
                        if len(value) not in ((34,) if value[0] == 0 else (35, 67)):
                            raise ValueError('request key')
                        baseline = m.get(prop(2, data[:2]))
                        args = vector(baseline) if baseline is not None else []
                        a = int.from_bytes(data[2:], 'little')
                        if a >= len(args) or args[a]:
                            raise ValueError('request slot')
                    else:
                        request = m.get(prop(3, data))
                        if request is None:
                            raise ValueError('signature request')
                        if len(request) < 2:
                            raise ValueError('request')
                        scheme, mode = request[:2]
                        if scheme == 0 and (len(value) != (64 if mode == 0 else 65) or
                                            (mode != 0 and value[-1] != mode)):
                            raise ValueError('signature encoding')
                        if scheme in (1, 2) and (not value or mode > 2 or
                                                value[-1] != (0x41, 0xc1, 0xc3)[mode]):
                            raise ValueError('bridge signature mode')
                        if scheme == 2 and len(value) != 65:
                            raise ValueError('bridge Schnorr encoding')
                elif sub == 6:
                    if prop(3) not in g:
                        raise ValueError('proof root')
                    if prop(1) not in m:
                        raise ValueError('proof coin')
                    proof = Reader(value)
                    bits = sum(b.bit_count() for b in proof.take(32))
                    if proof.compact(256) != bits:
                        raise ValueError('proof count')
                    proof.take(bits * 32)
                    proof.done()
    r.done()
    return maps


def combine(a, b):
    aa, bb = decode(a), decode(b)
    for key in (b'\xfb', prop(1), prop(2)):
        if aa[0][key] != bb[0][key]:
            raise ValueError('identity conflict')
    merged = []
    for left, right in zip(aa, bb):
        out = dict(left)
        for k, v in right.items():
            if k in out and out[k] != v:
                raise ValueError('key conflict')
            out[k] = v
        merged.append(out)
    encoded = encode(merged)
    decode(encoded)
    return encoded


def fixtures():
    # This script byte is merely a structural fixture; no VM success is claimed.
    op = bytes.fromhex('11' * 32) + bytes(4)
    tx = bytes.fromhex('07000000') + bytes(8) + b'\x01\0\0\0'
    tx += op + b'\xff' * 4 + b'\x01\0\x01\x01\x51\0\0'
    global_map = {b'\xfb': VERSION, b'\x04': b'\x01', b'\x05': b'\0',
                  prop(1): bytes(range(32)), prop(2): tx}
    positive, negative = [], []
    def good(name, maps):
        raw = encode(maps)
        assert encode(decode(raw)) == raw
        positive.append({'name': name, 'hex': raw.hex()})
        return raw
    def bad(name, raw):
        try:
            decode(raw)
        except (ValueError, IndexError):
            negative.append({'name': name, 'hex': raw.hex()})
            return
        raise AssertionError(name)
    base = good('incomplete-one-spend-zero-outputs', [global_map, {}])
    unknown = b'\xfc\x05other\x01key'
    good('unknown-vendor-and-noncritical-preserved', [global_map, {unknown: b'opaque', prop(128): b'future'}])
    arguments = {prop(2, bytes(2)): b'\x01\0',
                 prop(3, bytes(4)): b'\0\0' + bytes.fromhex('79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798')}
    good('native-signing-slot-unfunded', [global_map, arguments])
    output = b'\0' + (1000).to_bytes(8, 'little') + b'\x01' + b'\x22' * 32 + b'\x01\x01\0'
    # These exercise the full transaction output scanner, not only the standalone
    # output codec: HAS_STATE contributes 32 bytes before branch/path records.
    for name, flags, commitments in (
            ('state-bearing-output', 4, b'\x33' * 32),
            ('token-and-state-output', 5, b'\x44' * 32 + b'\x33' * 32)):
        state_output = bytes([flags]) + output[1:9] + commitments + output[9:]
        state_global = dict(global_map)
        state_global[b'\x05'] = b'\x01'
        state_global[prop(2)] = tx[:14] + b'\x01\0' + tx[16:] + state_output
        good(name, [state_global, {}, {}])
    coin = op + blob(output) + bytes(16) + b'\0\x02' + bytes(8) + (131400).to_bytes(8, 'little')
    funded = dict(arguments)
    funded[prop(1)] = coin
    good('full-coin-v2-metadata-framing', [global_map, funded])
    signed_shape = dict(funded)
    signed_shape[prop(4, bytes(4))] = bytes(64)
    good('mode-zero-signature-shape-not-cryptographic', [global_map, signed_shape])
    proof_global = dict(global_map)
    proof_global[prop(3)] = b'\x33' * 32
    proof_input = dict(funded)
    proof_input[prop(6)] = bytes(33)
    good('single-leaf-proof-framing-only', [proof_global, proof_input])
    # Reversed record order is legal and canonicalizes without dropping records.
    unordered = MAGIC + b''.join(blob(k) + blob(v) for k, v in reversed(sorted(global_map.items()))) + b'\0\0'
    assert encode(decode(unordered)) == base
    positive.append({'name': 'unordered-global-map', 'hex': unordered.hex(), 'canonical_hex': base.hex()})
    bad('duplicate-global-version', MAGIC + blob(b'\xfb') + blob(VERSION) + base[5:])
    bad('nonminimal-key-length', MAGIC + b'\xfd\x01\0\xfb\x04' + VERSION + b'\0')
    bad('nonminimal-key-type', MAGIC + blob(b'\xfd\xfb\0') + blob(VERSION) + b'\0')
    bad('trailing-byte', base + b'\0')
    bad('truncated-final-map', base[:-1])
    bad('wrong-magic', b'xxxxx' + base[5:])
    for name, key, value in [('bitcoin-version-two', b'\xfb', b'\x02\0\0\0'),
                             ('mismatched-input-count', b'\x04', b'\x02'),
                             ('nonminimal-count', b'\x04', b'\xfd\x01\0'),
                             ('short-chain-id', prop(1), bytes(31)),
                             ('forbidden-unsigned-tx', b'\0', tx),
                             ('unknown-critical-subtype', prop(127), b'')]:
        changed = dict(global_map)
        changed[key] = value
        bad(name, encode([changed, {}]))
    bad('forbidden-legacy-utxo', encode([global_map, {b'\0': b''}]))
    bad('out-of-range-witness', encode([global_map, {prop(2, b'\x01\0'): b'\0'}]))
    bad('orphan-signature', encode([global_map, {prop(4, bytes(4)): bytes(64)}]))
    bad('short-signature', encode([global_map, {**funded, prop(4, bytes(4)): bytes(63)}]))
    bad('explicit-zero-mode', encode([global_map, {**funded, prop(4, bytes(4)): bytes(65)}]))
    bad('nonempty-signature-slot', encode([global_map, {**arguments, prop(2, bytes(2)): b'\x01\x01x'}]))
    bad('coin-outpoint-mismatch', encode([global_map, {prop(1): b'\x12' + coin[1:]}]))
    bad('coin-provenance-truncated', encode([global_map, {prop(1): coin[:-1]}]))
    bad('proof-root-missing', encode([global_map, proof_input]))
    bad('proof-popcount-mismatch', encode([proof_global, {prop(1): coin, prop(6): bytes(32) + b'\x01' + bytes(32)}]))
    bad('proof-coin-missing', encode([proof_global, {prop(6): bytes(33)}]))
    bad('nonminimal-proprietary-subtype', encode([global_map, {PREFIX + b'\xfd\x80\0': b''}]))
    bad('oversized-key', encode([global_map, {b'\xfc\x05other\x01' + bytes(1024): b''}]))
    for name, at, byte in [('mint-unsupported', 56, 3), ('coinbase-unsupported', 56, 2),
                           ('nonempty-template-arguments', len(tx)-1, 1)]:
        changed = dict(global_map)
        changed[prop(2)] = tx[:at] + bytes([byte]) + tx[at+1:]
        bad(name, encode([changed, {}]))
    # Merge test fixes one conflict in an otherwise valid independently parsed map.
    left = encode([global_map, {unknown: b'a'}])
    right = encode([global_map, {unknown: b'b'}])
    assert combine(base, left) == left
    try:
        combine(left, right)
    except ValueError:
        pass
    else:
        raise AssertionError('unknown conflict accepted')
    return {'profile': 'Lotus native PSBT 0x4c560001',
            'scope': 'Independent container/schema fixtures only; no signatures, VM or authenticated roots.',
            'positive': positive, 'negative': negative,
            'merge': {'left_hex': left.hex(), 'right_hex': right.hex(), 'expected': 'key conflict'}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    path = Path(__file__).resolve().parents[1] / 'examples/psbt-profile-vectors.json'
    actual = fixtures()
    if args.write:
        path.write_text(json.dumps(actual, indent=2) + '\n')
    if json.loads(path.read_text()) != actual:
        raise SystemExit('PSBT fixture drift; review before --write')
    print(f"PSBT checks passed: {len(actual['positive'])} positive, {len(actual['negative'])} negative, merge preservation/conflict")


if __name__ == '__main__':
    main()
