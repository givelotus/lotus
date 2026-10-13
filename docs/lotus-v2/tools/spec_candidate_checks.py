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


EMPTY_ROOT = h('utxo', b'\2')


EMPTY_INDEXED_ROOT = h('merkleidx', b'\2')
ZERO32 = b'\0' * 32


def bit(key: bytes, depth: int) -> int:
    return (key[depth // 8] >> (depth % 8)) & 1  # little-endian bit order


def indexed_tree_root(leaves: list[bytes]) -> bytes:
    if not leaves:
        return EMPTY_INDEXED_ROOT
    if len(leaves) == 1:
        assert len(leaves[0]) == 32
        return leaves[0]
    cur = list(leaves)
    s = 0
    while len(cur) > 1:
        if len(cur) % 2 == 1:
            cur.append(ZERO32)
        cur = [h('merkleidx', b'\1' + u(s, 2) + cur[2 * j] + cur[2 * j + 1]) for j in range(len(cur) // 2)]
        s += 1
    return cur[0]


def indexed_tree_proof(leaves: list[bytes], index: int) -> bytes:
    assert 0 <= index < len(leaves)
    if len(leaves) == 1:
        return b''
    cur = list(leaves)
    idx = index
    s = 0
    siblings = []
    while len(cur) > 1:
        if len(cur) % 2 == 1:
            cur.append(ZERO32)
        siblings.append(cur[idx ^ 1])
        cur = [h('merkleidx', b'\1' + u(s, 2) + cur[2 * j] + cur[2 * j + 1]) for j in range(len(cur) // 2)]
        idx >>= 1
        s += 1
    return b''.join(siblings)


def merkle_sorted(leaf_hash: bytes, proof_bytes: bytes, hash_alg: int = 0) -> bytes:
    assert len(leaf_hash) == 32 and len(proof_bytes) % 32 == 0 and hash_alg in (0, 1, 2, 3)
    k = len(proof_bytes) // 32
    assert 0 <= k <= 64
    acc = leaf_hash
    for s in range(k):
        sib = proof_bytes[32 * s:32 * (s + 1)]
        lo, hi = sorted((acc, sib), key=lambda x: x[::-1])
        if hash_alg == 0:
            acc = h('branch', b'\1' + lo + hi)
        elif hash_alg == 1:
            acc = blake3(lo + hi).digest()
        elif hash_alg == 2:
            acc = hashlib.sha256(lo + hi).digest()
        else:
            acc = hashlib.sha256(hashlib.sha256(lo + hi).digest()).digest()
    return acc


def merkle_indexed(leaf_hash: bytes, key_bytes: bytes, proof_bytes: bytes, hash_alg: int = 0) -> bytes:
    assert len(leaf_hash) == 32 and 1 <= len(key_bytes) <= 32 and len(proof_bytes) % 32 == 0 and hash_alg in (0, 1, 2, 3)
    k = len(proof_bytes) // 32
    assert 0 <= k <= 8 * len(key_bytes)
    acc = leaf_hash
    for s in range(k):
        sib = proof_bytes[32 * s:32 * (s + 1)]
        left, right = (sib, acc) if bit(key_bytes, s) else (acc, sib)
        if hash_alg == 0:
            acc = h('merkleidx', b'\1' + u(s, 2) + left + right)
        elif hash_alg == 1:
            acc = blake3(left + right).digest()
        elif hash_alg == 2:
            acc = hashlib.sha256(left + right).digest()
        else:
            acc = hashlib.sha256(hashlib.sha256(left + right).digest()).digest()
    return acc


def smt(entries: dict[bytes, bytes], depth: int = 0) -> bytes:
    if not entries:
        return EMPTY_ROOT
    if len(entries) == 1:
        key, coin = next(iter(entries.items()))
        return h('utxo', b'\0' + key + blob(coin))
    assert depth < 256
    left = {k: v for k, v in entries.items() if bit(k, depth) == 0}
    right = {k: v for k, v in entries.items() if bit(k, depth) == 1}
    return node(depth, smt(left, depth + 1), smt(right, depth + 1))


def state_path(entries: dict[bytes, bytes], key: bytes, depth: int = 0) -> tuple[dict[bytes, bytes], list[tuple[int, bytes]]]:
    if len(entries) <= 1:
        return entries, []
    assert depth < 256
    selected = {k: v for k, v in entries.items() if bit(k, depth) == bit(key, depth)}
    other = {k: v for k, v in entries.items() if bit(k, depth) != bit(key, depth)}
    terminal, path = state_path(selected, key, depth + 1)
    return terminal, path + [(depth, smt(other, depth + 1))]


def state_proof(entries: dict[bytes, bytes], key: bytes) -> bytes:
    terminal, path = state_path(entries, key)
    if not terminal:
        start = b'\0'
    else:
        term_key, term_coin = next(iter(terminal.items()))
        start = (b'\1' if term_key == key else b'\2') + blob(term_coin)
    bitmap = bytearray(32)
    nondefault = []
    for depth, sibling in path:
        if sibling != EMPTY_ROOT:
            bitmap[depth // 8] |= 1 << (depth % 8)
            nondefault.append(sibling)
    return start + bytes(bitmap) + b''.join(nondefault)


def recover_compact(outpoint: bytes, proof: bytes) -> bytes:
    """Decode the generated P02 fixtures; this is not a hardened input parser."""
    key = h('outpointkey', outpoint)
    presence = proof[0]
    assert presence in (0, 1, 2)
    offset, coin = 1, None
    if presence in (1, 2):
        first = proof[offset]
        offset += 1
        if first < 253:
            size = first
        else:
            width = {253: 2, 254: 4, 255: 8}[first]
            size = int.from_bytes(proof[offset:offset + width], 'little')
            offset += width
        coin = proof[offset:offset + size]
        assert len(coin) == size
        assert proof[1:offset + size] == blob(coin)
        offset += size
    bitmap = proof[offset:offset + 32]
    assert len(bitmap) == 32
    offset += 32
    set_bits = [d for d in range(256) if bitmap[d // 8] & (1 << (d % 8))]
    k = 0 if not set_bits else max(set_bits) + 1
    if presence == 0:
        root = EMPTY_ROOT
    elif presence == 1:
        assert coin is not None and coin[:36] == outpoint
        root = h('utxo', b'\0' + key + blob(coin))
    else:
        assert coin is not None and coin[:36] != outpoint
        other_key = h('outpointkey', coin[:36])
        assert all(bit(other_key, d) == bit(key, d) for d in range(k))
        root = h('utxo', b'\0' + other_key + blob(coin))
    for depth in range(k - 1, -1, -1):
        sibling = EMPTY_ROOT
        if bitmap[depth // 8] & (1 << (depth % 8)):
            sibling = proof[offset:offset + 32]
            assert len(sibling) == 32 and sibling != EMPTY_ROOT
            offset += 32
        left, right = (sibling, root) if bit(key, depth) else (root, sibling)
        root = node(depth, left, right)
    assert offset == len(proof)
    return root


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


# Explicit P03 allocation, independent of the scanner's control flow.
ASSIGNED_OPCODES = set(range(1, 76)) | set(bytes.fromhex('''
00 4c 4f 51 52 53 54 55 56 57 58 59 5a 5b 5c 5d 5e 5f 60
61 63 64 67 68 69 6a 6b 6c 6d 6e 6f 70 71 72 74 75 76 77
78 79 7a 7b 7c 7d 7e 7f 80 81 82 83 84 85 86 87 88 8b 8c
8f 90 91 92 93 94 95 96 97 98 99 9a 9b 9c 9d 9e 9f a0 a1
a2 a3 a4 a5 a8 aa ac ad b1 b2 b4 b5 b6 ba bd be bf c0 c1
c2 c3 c4 c5 c6 c7 c8 c9 ca cb cc cd ce cf d0 d1 d2 d4 d5 d6 d7
d8 d9 da db dc dd de df e0 e1 e2 e3 e4 e5 e6 e7 e8 e9 ea eb ec ed ee ef
'''))
SUCCESS_OPCODES = set(range(256)) - ASSIGNED_OPCODES


def success_scan(script: bytes, max_element_bytes: int = 8192) -> bool:
    """P03 structural scan only; False still requires ordinary decode/evaluation.

    The caller must validate framing, outer limits and membership first.
    This helper is not a VM, transaction validator or relay implementation.
    """
    offset = 0
    while offset < len(script):
        op = script[offset]
        offset += 1
        if op in SUCCESS_OPCODES:
            return True
        if 1 <= op <= 75:
            size = op
        elif op == 0x4c:
            if offset == len(script):
                raise ValueError('missing push length')
            first = script[offset]
            offset += 1
            if first < 253:
                size = first
            else:
                width = {253: 2, 254: 4, 255: 8}[first]
                if width > len(script) - offset:
                    raise ValueError('truncated push length')
                size = int.from_bytes(script[offset:offset + width], 'little')
                offset += width
                if size < {253: 253, 254: 65536, 255: 2**32}[first]:
                    raise ValueError('nonminimal push length')
            if 1 <= size <= 75:
                raise ValueError('noncanonical PUSHDATA form')
        else:
            continue
        if size > max_element_bytes or size > len(script) - offset:
            raise ValueError('oversized or truncated push')
        offset += size
    return False


def success_scan_vectors() -> dict:
    assert len(ASSIGNED_OPCODES) == 215 and len(SUCCESS_OPCODES) == 41
    # Bind the explicit model allocation to the instruction rows, excluding
    # summary rows whose ranges also contain otherwise unassigned bytes.
    import re
    documented = set()
    packet = (ROOT / 'decisions' / 'vm-semantics.md').read_text()
    for token, name in re.findall(r'^\| ([0-9a-f]+(?:–[0-9a-f]+)?) \| ([^|]+) \|', packet, re.M):
        if 'allocation' in name or 'Invocation introspection' in name:
            continue
        bounds = token.split('–')
        documented.update(range(int(bounds[0], 16), int(bounds[-1], 16) + 1))
    assert documented == ASSIGNED_OPCODES

    rows = []
    cases = [(f'success_{op}', bytes([op]), True) for op in sorted(SUCCESS_OPCODES)]
    cases += [
        ('after_return', b'\x6a\xf0', True),
        ('skipped_arm', b'\x00\x63\xf0\x68', True),
        ('unmatched_conditional', b'\x63\xf0', True),
        ('ignored_truncated_suffix', b'\xf0\x01', True),
        ('fixed_push_payload', b'\x01\xf0', False),
        ('long_push_payload', b'\x4c\x4c' + b'\xf0' * 76, False),
        ('after_long_push', b'\x4c\x4c' + b'\xf0' * 76 + b'\xff', True),
        ('empty_push', b'\x4c\x00', False),
        ('ordinary_one', b'\x51', False),
        ('ordinary_return_needs_vm', b'\x6a', False),
        ('truncated_push_before_success', b'\x02\xf0', 'error'),
        ('noncanonical_push_before_success', b'\x4c\x01\xf0', 'error'),
        ('nonminimal_length_before_success', b'\x4c\xfd\x01\x00\xf0', 'error'),
        ('truncated_length_before_success', b'\x4c\xfe\xf0', 'error'),
        ('oversized_push_before_success', b'\x4c\xfd\x01\x20\xf0', 'error'),
    ]
    for name, script, expected in cases:
        try:
            result = success_scan(script)
        except ValueError:
            result = 'error'
        assert result == expected, (name, result, expected)
        rows.append({'id': name, 'script': script.hex(), 'scan_result': result})
    return {'note': 'Instruction-boundary scanning only; outer validation and ordinary VM execution are not modeled.',
            'success_bytes': bytes(sorted(SUCCESS_OPCODES)).hex(), 'cases': rows}


def make_vectors() -> dict:
    # Ordinary fixture uses OP_ONE, not a signature placeholder or payment claim.
    script = b'\x51'
    root = leaf(script)
    output = b'\0' + u(1000, 8) + b'\1' + root + b'\1\1\0'
    prev_output = b'\0' + u(2000, 8) + b'\1' + root + b'\1\1\0'
    outpoint = b'\x11' * 32 + u(0, 4)
    prefix = u(7, 4) + u(0, 8) + u(1, 2) + u(1, 2)
    core_witness = blob(script) + b'\0'  # Bytes(script) || Vec(h32 sibling)
    inp_core = outpoint + b'\xff' * 4 + b'\1\0\1' + core_witness  # flags 01 spend, path_index 0, 1 CoreWitness
    inp_wire = inp_core + b'\0'  # empty Vec(Bytes(arg))
    core = prefix + inp_core + output
    wire = prefix + inp_wire + output
    assert (len(prefix), len(output), len(core), len(wire)) == (16, 45, 107, 108)
    input_core_leaf = h('inputcore', inp_core)
    input_full_leaf = h('inputfull', inp_wire)
    output_leaf = h('output', blob(output))
    inputs_root = indexed_tree_root([input_core_leaf])
    full_inputs_root = indexed_tree_root([input_full_leaf])
    outputs_root = indexed_tree_root([output_leaf])
    assert (inputs_root, full_inputs_root, outputs_root) == (input_core_leaf, input_full_leaf, output_leaf)
    txid_preimage = CHAIN + prefix + inputs_root + outputs_root
    txhash_preimage = CHAIN + prefix + full_inputs_root + outputs_root
    assert len(txid_preimage) == 112 and len(txhash_preimage) == 112
    txid, wid = h('txid', txid_preimage), h('txhash', txhash_preimage)
    # C08 domain-tagged hashes are unkeyed BLAKE3 over ASCII(tag) || 0x00 || data, computable directly in script.
    assert blake3(b'Lotus/v2/txid\0' + txid_preimage).digest() == txid
    assert blake3(b'Lotus/v2/inputcore\0' + inp_core).digest() == input_core_leaf
    assert blake3(b'Lotus/v2/output\0' + blob(output)).digest() == output_leaf
    # Changing witness arguments changes TxHash only; changing script or proof changes InputCoreLeaf and TxID.
    inp_wire_with_arg = inp_core + b'\1' + blob(b'\xaa' * 64)
    assert h('txhash', CHAIN + prefix + indexed_tree_root([h('inputfull', inp_wire_with_arg)]) + outputs_root) != wid
    alt_inp_core = outpoint + b'\xff' * 4 + b'\1\0\1' + blob(b'\x52') + b'\0'
    sibling_inp_core = outpoint + b'\xff' * 4 + b'\1\0\1' + blob(script) + b'\1' + b'\x99' * 32
    assert h('txid', CHAIN + prefix + indexed_tree_root([h('inputcore', alt_inp_core)]) + outputs_root) != txid
    assert h('txid', CHAIN + prefix + indexed_tree_root([h('inputcore', sibling_inp_core)]) + outputs_root) != txid
    coin_leaf = h('coinentry', blob(prev_output))
    coins_root = indexed_tree_root([coin_leaf])
    assert coins_root == coin_leaf
    selector = b'\1' + u(0, 4) + u(0, 4) + root  # 01 || input_index:u32 || branch_index:u32 || Leaf(script)
    assert len(selector) == 41
    preimage = CHAIN + b'\0' + txid + coins_root + selector
    assert len(preimage) == 138
    # Partial signing modes use O(1) 32-byte digests: OwnInputHash(i) and OutputsRoot (01) or OutputLeaf(i) (02).
    own_input = inp_core + blob(prev_output)
    assert len(own_input) == 46 + 46
    own_input_hash = h('owninput', own_input)
    partial_head = u(7, 4) + u(0, 8) + own_input_hash
    preimage_mode_01 = CHAIN + b'\1' + partial_head + outputs_root + selector
    preimage_mode_02 = CHAIN + b'\2' + partial_head + output_leaf + selector
    assert len(preimage_mode_01) == 150 and len(preimage_mode_02) == 150
    msg_all_outputs = h('sighash', preimage_mode_01)
    msg_one_output = h('sighash', preimage_mode_02)
    # Mint input: token ID is the one-leaf mint root itself; Core retains CoreWitness and omits Vec(Bytes(arg)).
    token_id = root
    mint_core = token_id + u(0, 4) + b'\xff' * 4 + b'\3' + core_witness
    mint_wire = mint_core + b'\0'
    assert (len(mint_core), len(mint_wire)) == (44, 45)
    # Pruneable burn/commitment output (flags=0x02 IS_BURN): 1..16 branch roots and path_count == 0 (never enters UtxoRoot).
    burn_output = b'\2' + u(500, 8) + b'\1' + root + b'\0'
    assert len(burn_output) == 43

    # MERKLEROOT_SORTED (0xee) and MERKLEROOT_INDEXED (0xef) fixtures across hash_alg in 0..3 and IndexedTreeRoot.
    assert indexed_tree_root([]) == EMPTY_INDEXED_ROOT
    for n in range(1, 10):
        leaves = [h('output', u(j, 4)) for j in range(n)]
        expected_root = indexed_tree_root(leaves)
        for j in range(n):
            proof = indexed_tree_proof(leaves, j)
            assert merkle_indexed(leaves[j], u(j, 2), proof, 0) == expected_root
    # Parent transaction O(log N) input/output proof verification (3 inputs, 3 outputs).
    parent_in_leaves = [input_core_leaf, h('inputcore', alt_inp_core), h('inputcore', sibling_inp_core)]
    parent_out_leaves = [output_leaf, h('output', blob(prev_output)), h('output', blob(burn_output))]
    parent_header = u(7, 4) + u(0, 8) + u(3, 2) + u(3, 2)
    parent_in_root = indexed_tree_root(parent_in_leaves)
    parent_out_root = indexed_tree_root(parent_out_leaves)
    parent_txid = h('txid', CHAIN + parent_header + parent_in_root + parent_out_root)
    reconstructed_in_root = merkle_indexed(parent_in_leaves[2], u(2, 2), indexed_tree_proof(parent_in_leaves, 2), 0)
    reconstructed_out_root = merkle_indexed(parent_out_leaves[1], u(1, 2), indexed_tree_proof(parent_out_leaves, 1), 0)
    assert blake3(b'Lotus/v2/txid\0' + CHAIN + parent_header + reconstructed_in_root + reconstructed_out_root).digest() == parent_txid

    sib0, sib1 = leaf(b'\x52'), leaf(b'\x53')
    sorted_roots = {str(alg): merkle_sorted(root, sib0 + sib1, alg).hex() for alg in range(4)}
    assert bytes.fromhex(sorted_roots['0']) == branch(branch(root, sib0), sib1)
    idx_key = b'\x05'  # bits: s=0 -> 1, s=1 -> 0
    indexed_old_roots = {str(alg): merkle_indexed(root, idx_key, sib0 + sib1, alg).hex() for alg in range(4)}
    indexed_new_roots = {str(alg): merkle_indexed(leaf(b'\x54'), idx_key, sib0 + sib1, alg).hex() for alg in range(4)}
    for alg in range(4):
        assert merkle_sorted(root, b'', alg) == root and merkle_indexed(root, idx_key, b'', alg) == root
        assert indexed_old_roots[str(alg)] != indexed_new_roots[str(alg)]

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
    for query_outpoint in (outpoint, other_outpoint, absent_outpoint):
        query = h('outpointkey', query_outpoint)
        assert recover_compact(query_outpoint, state_proof(entries, query)) == state_root
    # Single-leaf map: root is UtxoLeaf directly (0 interior node hashes), and absence uses presence=2 at k=0.
    single_map = {key: coin}
    single_root = smt(single_map)
    assert single_root == h('utxo', b'\0' + key + blob(coin))
    assert recover_compact(outpoint, state_proof(single_map, key)) == single_root
    single_absence = state_proof(single_map, absent_key)
    assert single_absence[0] == 2 and recover_compact(absent_outpoint, single_absence) == single_root
    # Empty map: root is EMPTY_ROOT, and absence uses presence=0 at k=0.
    assert smt({}) == EMPTY_ROOT
    empty_absence = state_proof({}, absent_key)
    assert empty_absence == b'\0' + b'\0' * 32 and recover_compact(absent_outpoint, empty_absence) == EMPTY_ROOT
    assert single_root != state_root

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
        'success_scan': success_scan_vectors(),
        'chain_id_fixture_only': CHAIN.hex(),
        'ordinary_op_one_fixture': {
            'output': output.hex(), 'burn_output': burn_output.hex(),
            'core': core.hex(), 'wire': wire.hex(),
            'inputs_root': inputs_root.hex(), 'full_inputs_root': full_inputs_root.hex(),
            'outputs_root': outputs_root.hex(), 'coins_root': coins_root.hex(),
            'txid': txid.hex(), 'txhash': wid.hex(), 'branch_leaf': root.hex(),
            'selector': selector.hex(),
            'own_input_hash': own_input_hash.hex(), 'output_leaf': output_leaf.hex(),
            'signing_preimage': preimage.hex(), 'signing_message': h('sighash', preimage).hex(),
            'signing_message_mode_01': msg_all_outputs.hex(), 'signing_message_mode_02': msg_one_output.hex(),
            'note': 'No signature or full VM/block validation is asserted.'},
        'mint_input_fixture': {
            'mint_root': token_id.hex(), 'token_id': token_id.hex(),
            'input_core': mint_core.hex(), 'input_wire': mint_wire.hex(),
            'note': 'One-leaf OP_ONE mint policy; framing and token ID only.'},
        'merkle_opcode_fixtures': {
            'empty_indexed_root': EMPTY_INDEXED_ROOT.hex(),
            'parent_txid_3x3': parent_txid.hex(),
            'sorted_roots': sorted_roots,
            'indexed_key': idx_key.hex(),
            'indexed_old_roots': indexed_old_roots,
            'indexed_new_roots': indexed_new_roots},
        'ordered_transaction_roots': transaction_trees,
        'state': {'empty_root': EMPTY_ROOT.hex(), 'single_coin_root': single_root.hex(),
                  'two_coin_root': state_root.hex(),
                  'present_outpoint': outpoint.hex(), 'membership_proof': state_proof(entries, key).hex(),
                  'absent_outpoint': absent_outpoint.hex(), 'absence_proof': state_proof(entries, absent_key).hex(),
                  'empty_absence_proof': empty_absence.hex()},
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
    print('PASS: framing/signing inputs; 41 success opcodes and push-boundary scan cases; Merkle opcodes; 153 ordered-tree paths; compact sparse-map membership/absence/order; 134/82/64-byte header views; LOG power/monotonic checks; exact tail rounding; ASERT boundaries and compact targets.')


if __name__ == '__main__':
    main()
