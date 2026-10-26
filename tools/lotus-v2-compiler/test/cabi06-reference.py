"""CABI06 preparation: independent VM observations, never rewrite fixtures."""
import json
import sys
from dataclasses import replace
from lotus_v2_reference.vm import (ASSIGNED, SigningContext, UnsupportedFeature,
    VMError, VMProfile, branch_leaf_hash, decode, evaluate, static_cost, success_scan)

request = json.load(sys.stdin)
p = dict(request['profile'])
unit = p.pop('assigned_opcode_cost')
profile = VMProfile(**p, opcode_costs={op: unit for op in ASSIGNED})

def observe(script_hex, args_hex, case, cap):
    script = bytes.fromhex(script_hex)
    args = tuple(bytes.fromhex(a) for a in args_hex)
    # Calculate pre-execution static charges even when execution rejects.
    # This current assigned-opcode profile has no extension repricing:
    # frozen accounting and enforcement use the same schedule.
    charge = len(script) * profile.structural_byte_cost
    try:
        if not success_scan(script, profile):
            charge += static_cost(decode(script, profile), profile,
                input_count=case.get('input_count', 1 if case.get('signing') else 0),
                output_count=1 if case.get('signing') else 0,
                initial_sizes=tuple(map(len, args)), script_length=len(script))
    except (VMError, UnsupportedFeature):
        charge = None
    result = dict(root=branch_leaf_hash(script).hex(), accounting=charge,
                  enforcement=charge, cap=cap)
    signing = SigningContext(branch_leaf_hash(script), {0: bytes(32)}, 'spend', 0, 1) if case.get('signing') else None
    try:
        r = evaluate(script, args, replace(profile, max_invocation_cost=cap),
            input_count=case.get('input_count', 1 if signing else 0),
            output_count=1 if signing else 0, signing=signing)
        result.update(status='ok', stack=None if r.stack is None else [a.hex() for a in r.stack],
                      success=r.success, automatic=r.automatic)
        assert r.charged_cost == charge
    except UnsupportedFeature as exc:
        result.update(status='unsupported', error=str(exc))
    except VMError as exc:
        result.update(status='error', error=str(exc))
    return result

out = []
for case in request['cases']:
    for args, expected in zip(case['args'], case['expected'], strict=True):
        a = observe(case['before'], args, case, profile.max_invocation_cost)
        b = observe(case['after'], args, case, profile.max_invocation_cost)
        assert a['status'] == b['status'] == expected, (case['name'], args, a, b)
        if expected == 'ok':
            assert (a['stack'], a['success'], a['automatic']) == (b['stack'], b['success'], b['automatic'])
        boundaries = []
        if a['accounting'] and b['accounting']:
            for cap in sorted({1, a['accounting']-1, a['accounting'], b['accounting']-1, b['accounting']} - {0}):
                boundaries.append([observe(case['before'], args, case, cap), observe(case['after'], args, case, cap)])
        out.append(dict(name=case['name'], args=args, before=a, after=b, boundaries=boundaries))
print(json.dumps(out, sort_keys=True))
