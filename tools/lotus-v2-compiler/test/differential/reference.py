"""One invocation only; missing separate enforcement charge is explicit."""
import json, sys
from lotus_v2_reference.vm_runner import run_invocation
from lotus_v2_reference.vm import branch_leaf_hash
case = json.load(sys.stdin)
r = run_invocation(case)
r['leaf'] = branch_leaf_hash(bytes.fromhex(case['script'])).hex()
r['status'] = 'unsupported' if r.get('error_kind') == 'UnsupportedFeature' else 'accept' if r['accepted_invocation'] else 'reject'
r['accounting_charge'] = r.get('charged_cost')
r['enforcement_charge'] = None
print(json.dumps(r))
