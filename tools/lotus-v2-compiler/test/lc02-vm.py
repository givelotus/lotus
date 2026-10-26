"""LC02 emitted bytecode: real invocation contexts, including wrong-kind attacks."""
import json
import sys
from lotus_v2_reference.encoding import Output, Profile
from lotus_v2_reference.vm import ASSIGNED, VMError, VMProfile, evaluate, number
from lotus_v2_reference.vm_context import InputView, InvocationContext
profile = VMProfile(8192, 8, 8192, 128, 16, 16384, 32, 1_000_000, 1, {op: 1 for op in ASSIGNED})
output_profile = Profile(16, 16, 812, 8192)
count = 0
for case in json.load(sys.stdin):
    root = bytes.fromhex(case['method']['root'])
    script = bytes.fromhex(case['method']['scriptHex'])
    for kind in ('spend', 'mint'):
        for x in (0, 1):
            coin = Output(0, 1, None, (root,), ((0,),))
            inputs = (InputView(1, coin),) if kind == 'spend' else (InputView(3, None, root),)
            ctx = InvocationContext(inputs, (), kind, 0, root, output_profile,
                                    0 if kind == 'spend' else None,
                                    0 if kind == 'spend' else None,
                                    1 if kind == 'mint' else None)
            # A malicious untyped caller can supply enough stack items under either kind.
            args = (number(x),) + ((number(1),) if case['kind'] == 'mint' and kind == 'spend' else ())
            expected = kind == case['kind'] and x == 1
            try:
                result = evaluate(script, args, profile, invocation=ctx)
                accepted = result.success and result.stack == (number(1),)
            except VMError as exc:
                if kind != case['kind']:
                    assert str(exc) == 'VERIFY failed', str(exc)
                accepted = False
            assert accepted == expected, (case['kind'], kind, x, accepted)
            count += 1
print(f'{count} cases passed')
