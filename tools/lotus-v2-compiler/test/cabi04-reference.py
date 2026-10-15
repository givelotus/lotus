"""CABI04 exact-transaction invocation harness; no enclosing validity verdict."""
import json
import sys
from lotus_v2_reference.encoding import Output
from lotus_v2_reference.signing import Input, Transaction, TxProfile, Witness, encode_transaction, identity_digests
from lotus_v2_reference.vm import ASSIGNED, VMProfile, VMError, UnsupportedFeature, evaluate
from lotus_v2_reference.vm_context import authenticated_context

case = json.load(sys.stdin)
profile = TxProfile(16, 16, 16, 8192, 16, 8192, 64)
vm_profile = VMProfile(8192, 16, 8192, 128, 64, 65536, 32, 1000000, 1, {op: 1 for op in ASSIGNED})

def output(item):
    return Output(item['flags'], item['value'], None if item.get('token_id') is None else bytes.fromhex(item['token_id']),
                  tuple(bytes.fromhex(root) for root in item['branches']), tuple(tuple(path) for path in item['paths']))

try:
    script = bytes.fromhex(case['script'])
    arguments = tuple(bytes.fromhex(arg) for arg in case['args'])
    witness = Witness(script, tuple(bytes.fromhex(x) for x in case['proof']), arguments)
    tx = Transaction(case.get('lock', 0),
        (Input(bytes.fromhex('55' * 32), 0, case.get('sequence', 0xffffffff), 1, 0, (witness,)),),
        tuple(output(item) for item in case['outputs']))
    resolved = (output(case['coin']),)
    chain = bytes.fromhex('66' * 32)
    invocation, signing = authenticated_context(tx, profile, chain, resolved, 0, 0)
    identities = identity_digests(tx, profile, chain)
    evidence = {'wire': encode_transaction(tx, profile).hex(), 'txid': identities.txid.hex(),
                'txhash': identities.txhash.hex(), 'message': signing.messages[0].hex()}
    if case.get('prepare'):
        print(json.dumps(evidence))
    else:
        result = evaluate(script, arguments, vm_profile, invocation=invocation, signing=signing,
                          input_count=1, output_count=len(tx.outputs))
        print(json.dumps({**evidence, 'status': 'accepted', 'stack': [x.hex() for x in result.stack],
                          'charged_cost': result.charged_cost}))
except UnsupportedFeature as exc:
    print(json.dumps({'status': 'unsupported', 'error': str(exc)}))
except (VMError, ValueError) as exc:
    print(json.dumps({'status': 'rejected', 'error_kind': type(exc).__name__, 'error': str(exc)}))
