import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'python'))
from lotus_v2_call_runtime import prepare_call, finalize_call

data = json.load(sys.stdin)
context = data['context']
context['coin']['value'] = int(context['coin']['value'])
for output in context['outputs']:
    output['value'] = int(output['value'])
plan = prepare_call(data['artifact'], data['method'], context, {'signature': None})
result = finalize_call(plan, {'signature': bytes.fromhex(data['signature'])})
print(json.dumps({'wire': result['wire'].hex(), 'txid': result['txid'], 'txhash': result['txhash'],
                  'digest': plan.requests[0]['digest'], 'leaf': plan.requests[0]['leaf']}))
