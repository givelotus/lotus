#!/usr/bin/env python3
"""Small P01/P02/P03/P04 models, not a transaction validator or consensus oracle."""
from __future__ import annotations

import argparse
import hashlib
import json
from math import isqrt
from pathlib import Path

from blake3 import blake3

ROOT = Path(__file__).resolve().parents[1]
CHAIN = bytes(range(32))  # fixture-only; no production identity is selected


def u(value: int, width: int) -> bytes:
    return value.to_bytes(width, 'little')


def cs(n: int) -> bytes:
    if n < 253:
        return u(n, 1)
    if n <= 65535:
        return b'\xfd' + u(n, 2)
    if n <= 2**32 - 1:
        return b'\xfe' + u(n, 4)
    return b'\xff' + u(n, 8)


def blob(data: bytes) -> bytes:
    return cs(len(data)) + data


def h(name: str, data: bytes) -> bytes:
    return blake3(('Lotus/v2/' + name).encode('ascii') + b'\0' + data).digest()


def leaf(script: bytes) -> bytes:
    return h('branch', b'\0' + blob(script))


def branch(a: bytes, b: bytes) -> bytes:
    lo, hi = sorted((a, b), key=lambda x: x[::-1])  # unsigned little-endian order
    return h('branch', b'\1' + lo + hi)


def split(n: int) -> int:
    return 1 << ((n - 1).bit_length() - 1)


def tree(items: list[bytes]) -> bytes:
    if not items:
        return h('txroot', b'\2')
    if len(items) == 1:
        return h('txroot', b'\0' + items[0])
    k = split(len(items))
    return h('txroot', b'\1' + tree(items[:k]) + tree(items[k:]))


def txroot(items: list[bytes]) -> bytes:
    return h('txroot', b'\3' + u(len(items), 4) + tree(items))


def audit(items: list[bytes], index: int) -> list[bytes]:
    if len(items) == 1:
        return []
    k = split(len(items))
    if index < k:
        return audit(items[:k], index) + [tree(items[k:])]
    return audit(items[k:], index - k) + [tree(items[:k])]


def recover_txroot(count: int, index: int, witness_id: bytes, siblings: list[bytes]) -> bytes:
    route = []
    n, i = count, index
    assert 0 <= i < n
    while n > 1:
        k = split(n)
        left = i < k
        route.append(left)
        if left:
            n = k
        else:
            n, i = n - k, i - k
    assert len(route) == len(siblings)
    root = h('txroot', b'\0' + witness_id)
    for left, sibling in zip(reversed(route), siblings):
        a, b = (root, sibling) if left else (sibling, root)
        root = h('txroot', b'\1' + a + b)
    return h('txroot', b'\3' + u(count, 4) + root)


def node(depth: int, left: bytes, right: bytes) -> bytes:
    return h('utxo', b'\1' + u(depth, 2) + left + right)


EMPTY = [b''] * 257
EMPTY[256] = h('utxo', b'\2' + u(256, 2))
for depth in range(255, -1, -1):
    EMPTY[depth] = node(depth, EMPTY[depth + 1], EMPTY[depth + 1])


def bit(key: bytes, depth: int) -> int:
    return (key[depth // 8] >> (7 - depth % 8)) & 1


def smt(entries: dict[bytes, bytes], depth: int = 0) -> bytes:
    if not entries:
        return EMPTY[depth]
    if depth == 256:
        assert len(entries) == 1
        key, coin = next(iter(entries.items()))
        return h('utxo', b'\0' + key + blob(coin))
    left = {k: v for k, v in entries.items() if bit(k, depth) == 0}
    right = {k: v for k, v in entries.items() if bit(k, depth) == 1}
    return node(depth, smt(left, depth + 1), smt(right, depth + 1))


def state_path(entries: dict[bytes, bytes], key: bytes, depth: int = 0) -> list[bytes]:
    if depth == 256:
        return []
    selected = {k: v for k, v in entries.items() if bit(k, depth) == bit(key, depth)}
    other = {k: v for k, v in entries.items() if bit(k, depth) != bit(key, depth)}
    return state_path(selected, key, depth + 1) + [smt(other, depth + 1)]


def state_proof(entries: dict[bytes, bytes], key: bytes) -> bytes:
    coin = entries.get(key)
    start = b'\0' if coin is None else b'\1' + blob(coin)
    bitmap = bytearray(32)
    nondefault = []
    for j, sibling in enumerate(state_path(entries, key)):
        if sibling != EMPTY[256 - j]:
            bitmap[j // 8] |= 1 << (j % 8)
            nondefault.append(sibling)
    return start + bytes(bitmap) + b''.join(nondefault)


def recover_state(key: bytes, coin: bytes | None, path: list[bytes]) -> bytes:
    root = EMPTY[256] if coin is None else h('utxo', b'\0' + key + blob(coin))
    assert len(path) == 256
    for j, sibling in enumerate(path):
        depth = 255 - j
        left, right = (sibling, root) if bit(key, depth) else (root, sibling)
        root = node(depth, left, right)
    return root


def recover_compact(outpoint: bytes, proof: bytes) -> bytes:
    """Decode the generated P02 fixtures; this is not a hardened input parser."""
    key = h('outpointkey', outpoint)
    assert proof[0] in (0, 1)
    offset, coin = 1, None
    if proof[0]:
        first = proof[offset]
        offset += 1
        if first < 253:
            size = first
        else:
            width = {253: 2, 254: 4, 255: 8}[first]
            size = int.from_bytes(proof[offset:offset + width], 'little')
            offset += width
        coin = proof[offset:offset + size]
        assert len(coin) == size and coin[:36] == outpoint
        assert proof[1:offset + size] == blob(coin)
        offset += size
    bitmap = proof[offset:offset + 32]
    assert len(bitmap) == 32
    offset += 32
    path = []
    for j in range(256):
        sibling = EMPTY[256 - j]
        if bitmap[j // 8] & (1 << (j % 8)):
            sibling = proof[offset:offset + 32]
            assert len(sibling) == 32 and sibling != EMPTY[256 - j]
            offset += 32
        path.append(sibling)
    assert offset == len(proof)
    return recover_state(key, coin, path)


def log_q64(x: int) -> int:
    assert 0 < x < 2**127
    e = x.bit_length() - 1
    z, frac = x << (127 - e), 0
    for _ in range(64):
        t = z * z >> 127
        high = int(t >= 2**128)
        z = t >> high
        frac = frac * 2 + high
    return (e << 64) + frac


def compact_encode(target: int) -> int:
    exponent = (target.bit_length() + 7) // 8
    mantissa = target << (8 * (3 - exponent)) if exponent <= 3 else target >> (8 * (exponent - 3))
    if mantissa & 0x800000:
        mantissa >>= 8
        exponent += 1
    return exponent << 24 | mantissa


def compact_decode(bits: int) -> int:
    exponent, mantissa = bits >> 24, bits & 0x7fffff
    return mantissa >> (8 * (3 - exponent)) if exponent <= 3 else mantissa << (8 * (exponent - 3))


def asert(target: int, drift: int, half_life: int, limit: int) -> int:
    exponent = (abs(drift) * 65536 // half_life) * (-1 if drift < 0 else 1)
    q, f = divmod(exponent, 65536)
    factor = 65536 + ((195766423245049*f + 971821376*f*f + 5127*f*f*f + 2**47) >> 48)
    value, shift = target * factor, q - 16
    if shift >= 0:
        raw = limit if shift >= 256 or value > (limit >> shift) else value << shift
    else:
        raw = 0 if -shift >= value.bit_length() else value >> -shift
    return min(limit, max(1, raw))


def make_vectors() -> dict:
    # Ordinary fixture uses OP_ONE, not a signature placeholder or payment claim.
    script = b'\x51'
    root = leaf(script)
    output = b'\0' + u(1000, 8) + b'\1' + root + b'\1\1\0'
    prev_output = b'\0' + u(2000, 8) + b'\1' + root + b'\1\1\0'
    outpoint = b'\x11' * 32 + u(0, 4)
    prefix = u(7, 4) + u(0, 8) + u(1, 2) + u(1, 2)
    inp = outpoint + b'\xff' * 4 + b'\1\0'  # flags 01 spend, path_index 0
    witness = b'\1' + blob(script) + b'\0\0'
    core = prefix + inp + output
    wire = prefix + inp + witness + output
    assert (len(prefix), len(output), len(core), len(wire)) == (16, 45, 103, 108)
    txid, wid = h('txid', CHAIN + core), h('txhash', CHAIN + wire)
    plan = u(1, 2) + b'\1\0\1\0' + root
    coins = u(1, 2) + blob(prev_output)
    selector = b'\1' + root
    preimage = CHAIN + b'\0' + txid + h('spentoutputs', coins) + h('authplan', plan) + selector
    assert len(preimage) == 162
    # Partial signing modes: own input plus all outputs (01) or the same-index output (02).
    own_input = inp + blob(prev_output) + b'\1\0\1\0' + root
    partial_head = u(7, 4) + u(0, 8) + own_input
    msg_all_outputs = h('sighash', CHAIN + b'\1' + partial_head + h('outputs', u(1, 2) + output) + selector)
    msg_one_output = h('sighash', CHAIN + b'\2' + partial_head + blob(output) + selector)
    assert len(own_input) == 42 + 46 + 36
    # Mint input: token ID is the one-leaf mint root itself; witness is one BranchWitness.
    token_id = root
    mint_core = token_id + u(0, 4) + b'\xff' * 4 + b'\3'
    mint_wire = mint_core + blob(script) + b'\0\0'
    assert (len(mint_core), len(mint_wire)) == (41, 45)

    transaction_trees = []
    for count in range(18):
        items = [h('txhash', u(i, 4)) + h('txid', u(i, 4)) for i in range(count)]  # leaf = TxHash || TxID
        expected = txroot(items)
        for i in range(count):
            assert recover_txroot(count, i, items[i], audit(items, i)) == expected
        transaction_trees.append({'count': count, 'root': expected.hex()})

    coin = outpoint + blob(prev_output) + u(100, 8) + u(1700000000, 8) + b'\0'
    key = h('outpointkey', outpoint)
    other_outpoint = b'\x22' * 32 + u(1, 4)
    other_coin = other_outpoint + blob(output) + u(101, 8) + u(1700000001, 8) + b'\0'
    other_key = h('outpointkey', other_outpoint)
    absent_outpoint = b'\x33' * 32 + u(2, 4)
    absent_key = h('outpointkey', absent_outpoint)
    entries = {key: coin, other_key: other_coin}
    state_root = smt(entries)
    assert state_root == smt(dict(reversed(list(entries.items()))))
    for query in (key, other_key, absent_key):
        assert recover_state(query, entries.get(query), state_path(entries, query)) == state_root
    for query_outpoint in (outpoint, other_outpoint, absent_outpoint):
        query = h('outpointkey', query_outpoint)
        assert recover_compact(query_outpoint, state_proof(entries, query)) == state_root
    assert smt({}) == EMPTY[0]
    assert smt({key: coin}) != state_root

    # Arbitrary root bytes below are header-hashing fixtures, not a valid mined block.
    body = u(2, 4) + u(1000, 8) + u(101, 8) + txroot([wid + txid]) + b'\x44' * 32
    body_hash = h('header/body', CHAIN + body)
    work_fields = u(0x1d00ffff, 4) + u(2**32, 6) + u(123, 8)
    work_hash = h('header/work', work_fields + body_hash)
    prev_id = b'\x55' * 32
    header = prev_id + work_fields + body
    block_id = h('blockid', prev_id + work_hash)
    assert (len(body), len(header), len(prev_id + work_fields + body_hash)) == (84, 134, 82)
    assert len(prev_id + work_hash) == 64
    assert branch(root, leaf(b'\x52')) == branch(leaf(b'\x52'), root)
    for e in range(127):
        assert log_q64(1 << e) == e << 64
    logs = [log_q64(x) for x in range(1, 1000)]
    assert logs == sorted(logs)
    tails = []
    for subsidy, work, prior in ((100, 4, 1), (100, 1, 4), (101, 2, 3), (2**64-1, 2**255, 1)):
        q = subsidy * subsidy * work // prior
        r = isqrt(q)
        assert r*r*prior <= subsidy*subsidy*work < (r+1)*(r+1)*prior
        tails.append({'tail': str(subsidy), 'work': str(work), 'prior_work': str(prior), 'unclipped_next': str(r)})

    target, half_life, limit = 2**200, 172800, 2**224 - 1
    assert asert(target, 0, half_life, limit) == target
    assert asert(target, half_life, half_life, limit) == 2*target
    assert asert(target, -half_life, half_life, limit) == target//2
    assert asert(target, 2**80, half_life, limit) == limit
    assert asert(target, -2**80, half_life, limit) == 1
    asert_rows = []
    for drift in (-345600, -172801, -172800, -1, 0, 1, 172799, 172800, 345600):
        raw = asert(target, drift, half_life, limit)
        bits = compact_encode(raw)
        encoded_target = compact_decode(bits)
        assert 0 < encoded_target <= raw and compact_encode(encoded_target) == bits
        asert_rows.append({'drift': drift, 'raw_target': str(raw), 'bits': f'{bits:08x}',
                           'decoded_target': str(encoded_target)})
    for raw in (1, 127, 128, 255, 256, 65535, 65536, 2**255, 2**256-1):
        bits = compact_encode(raw)
        assert compact_encode(compact_decode(bits)) == bits
        assert 0 < compact_decode(bits) <= raw

    packets = sorted((ROOT / 'decisions').glob('*.md'))
    return {
        'schema': 'lotus/spec-candidate-smoke/v1',
        'status': 'single-model structural fixtures; not independently verified conformance',
        'generator_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'packet_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in packets},
        'chain_id_fixture_only': CHAIN.hex(),
        'ordinary_op_one_fixture': {
            'output': output.hex(), 'core': core.hex(), 'wire': wire.hex(),
            'txid': txid.hex(), 'txhash': wid.hex(), 'branch_leaf': root.hex(),
            'coins': coins.hex(), 'auth_plan': plan.hex(), 'selector': selector.hex(),
            'signing_preimage': preimage.hex(), 'signing_message': h('sighash', preimage).hex(),
            'signing_message_mode_01': msg_all_outputs.hex(), 'signing_message_mode_02': msg_one_output.hex(),
            'note': 'No signature or full VM/block validation is asserted.'},
        'mint_input_fixture': {
            'mint_root': token_id.hex(), 'token_id': token_id.hex(),
            'input_core': mint_core.hex(), 'input_wire': mint_wire.hex(),
            'note': 'One-leaf OP_ONE mint policy; framing and token ID only.'},
        'ordered_transaction_roots': transaction_trees,
        'state': {'empty_root': EMPTY[0].hex(), 'two_coin_root': state_root.hex(),
                  'present_outpoint': outpoint.hex(), 'membership_proof': state_proof(entries,key).hex(),
                  'absent_outpoint': absent_outpoint.hex(), 'absence_proof': state_proof(entries,absent_key).hex()},
        'header_hash_fixture': {'wire': header.hex(), 'body_hash': body_hash.hex(),
                                'work_hash': work_hash.hex(), 'block_id': block_id.hex(),
                                'note': 'Size/state/transaction fields are hash inputs only; not a valid block.'},
        'tail_rounding_examples': tails,
        'asert_examples': {'note': 'Fixture parameters only, not production constants.',
                           'anchor_target': str(target), 'half_life': half_life,
                           'pow_limit': str(limit), 'rows': asert_rows},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true', help='explicitly regenerate candidate fixtures')
    args = parser.parse_args()
    if not __debug__:
        raise SystemExit('Run without -O: this smoke checker uses assertions.')
    actual = make_vectors()
    path = ROOT / 'examples' / 'candidate-smoke-vectors.json'
    if args.write:
        path.write_text(json.dumps(actual, indent=2) + '\n')
    else:
        assert json.loads(path.read_text()) == actual, 'Fixtures or packet digests changed; review before regenerating.'
    print('PASS: framing/signing inputs; 153 ordered-tree paths; sparse-map membership/absence/order; 134/82/64-byte header views; LOG power/monotonic checks; exact tail rounding; ASERT boundaries and compact targets.')


if __name__ == '__main__':
    main()
