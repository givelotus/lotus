"""Exercise a generated Python schema-2 wrapper against a public fixture."""
import importlib.util
import json
import sys

generated_path, fixture_path = sys.argv[1:]
spec = importlib.util.spec_from_file_location('generated_contract_payment', generated_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
with open(fixture_path, encoding='utf-8') as file:
    fixture = json.load(file)
context = fixture['context'].copy()
context['coin'] = context['coin'].copy()
context['coin']['value'] = int(context['coin'].pop('valueAtoms'))
context['outputs'] = [dict(value=int(o['valueAtoms']), branches=o['branches'], paths=o['paths']) for o in context['outputs']]
context.pop('coinWire')
client = module.Payment(fixture['artifact'])
plan = client.prepareSpend(context, {'signature': None})
result = client.finalizeSpend(plan, {'signature': bytes.fromhex(fixture['valid']['signature'])})
try:
    client.finalizeSpend(plan.__class__(plan.artifact, 'other', plan.context, plan.arguments,
                                       plan.unsigned_wire, plan.txid, plan.requests),
                         {'signature': bytes.fromhex(fixture['valid']['signature'])})
except ValueError as error:
    if str(error) != 'method plan mismatch':
        raise
else:
    raise AssertionError('generated method guard did not reject another method plan')
print(json.dumps({'wire': result['wire'].hex(), 'txid': result['txid'], 'txhash': result['txhash'],
                  'digest': plan.requests[0]['digest'], 'leaf': plan.requests[0]['leaf'],
                  'feeAtoms': str(plan.requests[0]['feeAtoms'])}))
