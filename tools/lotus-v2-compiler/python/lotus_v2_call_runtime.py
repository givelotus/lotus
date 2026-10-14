"""Offline one-input Lotus V2 contract calls for artifact schema 2.

This module frames P01 bytes and hashes P02 proofs; it does not execute scripts,
verify generic signature arguments, or perform contextual validation.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import re
from blake3 import blake3

TARGET = 'P01-P02-P03-candidate-2026-10-14'


def hx(value: str, length: int | None = None) -> bytes:
    if not isinstance(value, str) or len(value) % 2 or value.lower() != value or any(c not in '0123456789abcdef' for c in value):
        raise ValueError('expected lowercase hex')
    result = bytes.fromhex(value)
    if length is not None and len(result) != length:
        raise ValueError('hex width')
    return result


def ui(value: int, width: int) -> bytes:
    if type(value) is not int or value < 0 or value >= 1 << (8 * width):
        raise ValueError(f'u{width * 8} range')
    return value.to_bytes(width, 'little')


def cs(n: int) -> bytes:
    if type(n) is not int or n < 0 or n > 0xffffffffffffffff:
        raise ValueError('CompactSize range')
    if n < 253: return bytes([n])
    if n <= 0xffff: return b'\xfd' + ui(n, 2)
    if n <= 0xffffffff: return b'\xfe' + ui(n, 4)
    return b'\xff' + ui(n, 8)


def sized(value: bytes) -> bytes:
    return cs(len(value)) + value


def tagged(name: str, payload: bytes) -> bytes:
    return blake3(f'Lotus/v2/{name}\0'.encode() + payload).digest()


def node(a: bytes, b: bytes) -> bytes:
    low, high = sorted((a, b), key=lambda h: int.from_bytes(h, 'little'))
    return tagged('branch', b'\x01' + low + high)


def method_root(script_hex: str, proof: list[str]) -> str:
    if len(proof) > 64: raise ValueError('proof depth')
    result = tagged('branch', b'\x00' + sized(hx(script_hex)))
    for sibling in proof: result = node(result, hx(sibling, 32))
    return result.hex()


def encode_value(kind: str, value: Any) -> bytes:
    if kind == 'Signature':
        if type(value) is not bytes or len(value) != 64: raise ValueError('FULL signature must be 64 bytes')
        return value
    if kind == 'Int':
        if type(value) is not int or not -(1 << 127) <= value < (1 << 127): raise ValueError('int128 range')
        return value.to_bytes(16, 'little', signed=True)
    if kind == 'Bool':
        if type(value) is not bool: raise ValueError('Bool required')
        return ui(int(value), 16)
    if type(value) is not bytes: raise ValueError('byte value required')
    if kind in ('PublicKey', 'Bytes32', 'MethodLeafHash', 'ContractRootHash'): expected, bound = 32, None
    elif kind.startswith('Bytes(') and kind.endswith(')') and kind[6:-1].isdigit(): expected, bound = None, int(kind[6:-1])
    elif kind == 'Bytes': expected, bound = None, None
    else: raise ValueError('unsupported argument type')
    if expected is not None and len(value) != expected: raise ValueError(f'{kind} length')
    if bound is not None and len(value) > bound: raise ValueError(f'{kind} length')
    if len(value) > 8192: raise ValueError('argument too large')
    return value


def encode_output(output: dict) -> bytes:
    flags = output.get('flags', 0)
    if flags != 0: raise ValueError('only native spendable output supported')
    branches, paths = output['branches'], output['paths']
    if not 1 <= len(branches) <= 16 or not 1 <= len(paths) <= 16: raise ValueError('output branch/path count')
    if len(set(branches)) != len(branches): raise ValueError('duplicate branches')
    previous = None
    encoded_paths = []
    for path in paths:
        if not 1 <= len(path) <= 16 or any(type(x) is not int or x < 0 or x >= len(branches) for x in path) or path != sorted(set(path)):
            raise ValueError('invalid path')
        if previous is not None and not previous < path: raise ValueError('path order')
        previous = path
        encoded_paths.append(cs(len(path)) + b''.join(cs(x) for x in path))
    return b'\x00' + ui(output['value'], 8) + cs(len(branches)) + b''.join(hx(x, 32) for x in branches) + cs(len(paths)) + b''.join(encoded_paths)


def indexed_root(leaves: list[bytes]) -> bytes:
    if not leaves: return tagged('merkleidx', b'\x02')
    nodes, level = leaves, 0
    while len(nodes) > 1:
        if len(nodes) % 2: nodes = nodes + [bytes(32)]
        nodes = [tagged('merkleidx', b'\x01' + ui(level, 2) + nodes[i] + nodes[i+1]) for i in range(0, len(nodes), 2)]
        level += 1
    return nodes[0]


def selected(artifact: dict, method_name: str) -> dict:
    if artifact.get('schema') != 'lotus-v2/contract-artifact/2' or artifact.get('target') != TARGET: raise ValueError('unsupported artifact')
    policy = artifact['policy']
    if policy.get('treeRecipe') != 'sorted-leaves-largest-power-split-v1' or policy['branches'] != [policy['root']] or policy['paths'] != [[0]]:
        raise ValueError('unsupported policy')
    hx(policy['root'], 32)
    declared, bound = artifact['constructor'], artifact['bindings']
    if len(declared) != len(bound) or len({x['name'] for x in declared}) != len(declared): raise ValueError('constructor/binding mismatch')
    for dec, val in zip(declared, bound):
        if not re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*', dec['name']) or dec['name'] != val['name'] or dec['type'] != val['type']:
            raise ValueError('constructor/binding mismatch')
        kind, value = val['type'], val['value']
        if kind == 'Bool':
            if type(value) is not bool: raise ValueError('noncanonical Bool binding')
        elif kind == 'Int':
            if type(value) is not str or not re.fullmatch(r'0|-[1-9][0-9]*|[1-9][0-9]*', value): raise ValueError('noncanonical Int binding')
            encode_value(kind, int(value))
        elif kind == 'Signature':
            raw = hx(value)
            if len(raw) != 64 and not (len(raw) == 65 and raw[-1] in (1, 2)): raise ValueError('noncanonical Signature binding')
        else: encode_value(kind, hx(value))
    methods = artifact['methods']
    if not 1 <= len(methods) <= 16 or len({m['name'] for m in methods}) != len(methods): raise ValueError('invalid methods')
    leaves = []
    for entry in methods:
        if not re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*', entry['name']) or len({x['name'] for x in entry['args']}) != len(entry['args']): raise ValueError('invalid method arguments')
        script = hx(entry['scriptHex'])
        if not 1 <= len(script) <= 8192: raise ValueError('script width')
        leaf = tagged('branch', b'\x00' + sized(script))
        if entry['leaf'] != leaf.hex() or method_root(entry['scriptHex'], entry['proof']) != entry['root'] or entry['root'] != policy['root']:
            raise ValueError('method proof or root mismatch')
        leaves.append(leaf)
    ordered = sorted(leaves, key=lambda h: int.from_bytes(h, 'little'))
    if len(set(ordered)) != len(ordered): raise ValueError('duplicate method leaf')
    def tree(items):
        if len(items) == 1: return items[0]
        k = 1
        while k * 2 < len(items): k *= 2
        return node(tree(items[:k]), tree(items[k:]))
    if tree(ordered).hex() != policy['root']: raise ValueError('method tree recipe mismatch')
    method = next((m for m in methods if m['name'] == method_name), None)
    if method is None: raise ValueError('unknown method')
    leaf = tagged('branch', b'\x00' + sized(hx(method['scriptHex']))).hex()
    if method['leaf'] != leaf or method_root(method['scriptHex'], method['proof']) != method['root'] or method['root'] != policy['root']:
        raise ValueError('method proof or root mismatch')
    if len({a['name'] for a in method['args']}) != len(method['args']): raise ValueError('duplicate argument names')
    return method


def core(context: dict, method: dict) -> bytes:
    return hx(context['prevTxid'], 32) + ui(context['prevIndex'], 4) + ui(context['sequence'], 4) + b'\x01' + cs(0) + cs(1) + sized(hx(method['scriptHex'])) + cs(len(method['proof'])) + b''.join(hx(x, 32) for x in method['proof'])


def encoded_args(method: dict, arguments: dict, signatures: dict | None = None) -> list[bytes]:
    if set(arguments) != {x['name'] for x in method['args']}: raise ValueError('argument names mismatch')
    result = []
    for arg in method['args']:
        name, kind = arg['name'], arg['type']
        if kind == 'Signature':
            if arguments[name] is not None: raise ValueError('Signature argument must be an empty signing slot')
            result.append(encode_value(kind, signatures[name]) if signatures is not None else b'')
        else: result.append(encode_value(kind, arguments[name]))
    return result


def hashes(context: dict, method: dict, values: list[bytes]) -> dict:
    header = ui(7, 4) + ui(context.get('lock', 0), 8) + ui(1, 2) + ui(len(context['outputs']), 2)
    input_core = core(context, method)
    input_full = input_core + cs(len(values)) + b''.join(sized(x) for x in values)
    outputs = [encode_output(x) for x in context['outputs']]
    out_root = indexed_root([tagged('output', sized(x)) for x in outputs])
    chain = hx(context['chainId'], 32)
    txid = tagged('txid', chain + header + indexed_root([tagged('inputcore', input_core)]) + out_root)
    txhash = tagged('txhash', chain + header + indexed_root([tagged('inputfull', input_full)]) + out_root)
    coin_root = indexed_root([tagged('coinentry', sized(encode_output(context['coin'])))])
    selector = b'\x01' + ui(0, 4) + ui(0, 4) + hx(method['leaf'], 32)
    message = tagged('sighash', chain + b'\x00' + txid + coin_root + selector)
    return {'wire': header + input_full + b''.join(outputs), 'txid': txid.hex(), 'txhash': txhash.hex(), 'message': message.hex()}


@dataclass(frozen=True)
class CallPlan:
    artifact: dict
    method_name: str
    context: dict
    arguments: dict
    unsigned_wire: bytes
    txid: str
    requests: tuple[dict, ...]


def prepare_call(artifact: dict, method_name: str, context: dict, arguments: dict) -> CallPlan:
    method = selected(artifact, method_name)
    if context.get('profile') != TARGET: raise ValueError('unsupported profile')
    hx(context['chainId'], 32); hx(context['prevTxid'], 32); ui(context['prevIndex'], 4); ui(context['sequence'], 4)
    lock = context.get('lock', 0)
    ui(lock, 8)
    if lock & 255 > 2 or (lock & 255 == 0 and lock != 0): raise ValueError('invalid P01 lock encoding')
    if context['sequence'] != 0xffffffff and context['sequence'] & ~0x40ffff: raise ValueError('invalid P01 sequence bits')
    if context['coin']['paths'] != [[0]] or context['coin']['branches'] != [artifact['policy']['root']]: raise ValueError('resolved coin policy mismatch')
    values = encoded_args(method, arguments)
    fee = context['coin']['value'] - sum(x['value'] for x in context['outputs'])
    if fee < 0: raise ValueError('negative fee')
    result = hashes(context, method, values)
    requests = tuple({'argument': x['name'], 'mode': 0, 'digest': result['message'], 'chainId': context['chainId'],
                      'txid': result['txid'], 'inputIndex': 0, 'branchIndex': 0, 'leaf': method['leaf'], 'feeAtoms': fee}
                     for x in method['args'] if x['type'] == 'Signature')
    return CallPlan(artifact, method_name, context, arguments, result['wire'], result['txid'], requests)


def finalize_call(plan: CallPlan, signatures: dict[str, bytes]) -> dict:
    fresh = prepare_call(plan.artifact, plan.method_name, plan.context, plan.arguments)
    if fresh.txid != plan.txid or fresh.unsigned_wire != plan.unsigned_wire or fresh.requests != plan.requests: raise ValueError('stale signing plan')
    if set(signatures) != {x['argument'] for x in fresh.requests}: raise ValueError('signature slots mismatch')
    result = hashes(plan.context, selected(plan.artifact, plan.method_name), encoded_args(selected(plan.artifact, plan.method_name), plan.arguments, signatures))
    return {'wire': result['wire'], 'txid': result['txid'], 'txhash': result['txhash'],
            'stages': {'assembly': 'passed', 'framing': 'passed', 'signature': 'unavailable', 'invocation': 'unavailable', 'contextual': 'unavailable', 'block': 'unavailable'}}
