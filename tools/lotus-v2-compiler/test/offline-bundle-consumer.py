"""Offline invocation verifier. Does not import a compiler or validate blocks."""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'lotus-v2-reference'))
from lotus_v2_reference.vm_runner import run_invocation
from blake3 import blake3
from jsonschema import Draft202012Validator


def canonical(value):
    def check(x):
        if isinstance(x, float) or type(x) is int and abs(x) > 9007199254740991:
            raise ValueError('noncanonical numeric value')
        if isinstance(x, dict):
            for v in x.values(): check(v)
        if isinstance(x, list):
            for v in x: check(v)
    check(value)
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def execute(case):
    case = json.loads(json.dumps(case))
    invocation = case.get('invocation')
    if invocation:
        for output in invocation['outputs'] + [i['coin'] for i in invocation['inputs'] if i.get('coin')]:
            value = output['value']
            if not isinstance(value, str) or not value.isascii() or not value.isdecimal() or str(int(value)) != value:
                raise ValueError('amount must be canonical unsigned decimal string')
            output['value'] = int(value)
        if invocation.get('mint_delta') is not None:
            value = invocation['mint_delta']
            if not isinstance(value, str) or str(int(value)) != value:
                raise ValueError('noncanonical mint delta')
            invocation['mint_delta'] = int(value)
    return run_invocation(case)


def verify(bundle):
    schema = json.loads((Path(__file__).resolve().parents[1] / 'fixtures/offline/bundle-v1.schema.json').read_text())
    Draft202012Validator(schema).validate(bundle)
    if set(bundle) != {'schema', 'payload', 'sha256'} or bundle['schema'] != 'lotus-v2/offline-bundle/1':
        raise ValueError('unsupported bundle schema')
    payload = bundle['payload']
    if digest(payload) != bundle['sha256']: raise ValueError('bundle digest mismatch')
    for item in payload['files']:
        if hashlib.sha256(item['utf8'].encode()).hexdigest() != item['sha256']:
            raise ValueError('file digest mismatch')
    artifacts = payload['artifacts']
    for name, artifact in artifacts.items():
        recorded = payload['artifactBytes'][name]
        if recorded['utf8'].encode() != canonical(artifact) or hashlib.sha256(recorded['utf8'].encode()).hexdigest() != recorded['sha256']:
            raise ValueError('artifact bytes mismatch')
        for method in artifact['methods']:
            script = bytes.fromhex(method['scriptHex'])
            if len(script) >= 253: raise ValueError('bundle v1 supports short script proofs only')
            tag = lambda data: blake3(b'Lotus/v2/branch\0' + data).digest()
            root = tag(bytes([0, len(script)]) + script)
            if root.hex() != method['leaf']: raise ValueError('leaf mismatch')
            for sibling in method['proof']:
                pair = sorted([root, bytes.fromhex(sibling)], key=lambda x: int.from_bytes(x, 'little'))
                root = tag(b'\1' + b''.join(pair))
            if root.hex() != artifact['policy']['root']: raise ValueError('proof root mismatch')
    for case in payload['cases']:
        method = next(m for m in artifacts[case['artifact']]['methods'] if m['name'] == case['method'])
        if case['input']['script'] != method['scriptHex']: raise ValueError('case script mismatch')
        if execute(case['input']) != case['expected']: raise ValueError('VM result mismatch: ' + case['name'])
    return {'verified_invocations': len(payload['cases']), 'block_validation': 'unsupported'}


if __name__ == '__main__':
    data = json.load(sys.stdin)
    if sys.argv[1:] == ['--execute']: print(json.dumps(execute(data), sort_keys=True))
    else: print(json.dumps(verify(data), sort_keys=True))
