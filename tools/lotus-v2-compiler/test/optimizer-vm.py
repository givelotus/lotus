"""Independent Python P03 differential check for compiler optimizer fixtures."""
import json
import sys

from lotus_v2_reference.vm import ASSIGNED, SigningContext, VMProfile, branch_leaf_hash, evaluate


profile = VMProfile(8192, 8, 8192, 128, 16, 16384, 32, 1_000_000, 1,
                    {op: 1 for op in ASSIGNED})


def result(script_hex, args, signing=False):
    try:
        script = bytes.fromhex(script_hex)
        context = SigningContext(branch_leaf_hash(script), {0: bytes(32)}, 'spend', 0, 1) if signing else None
        value = evaluate(script, tuple(bytes.fromhex(arg) for arg in args), profile, signing=context)
        return ("ok", [item.hex() for item in value.stack or ()], value.success, value.charged_cost)
    except Exception as exc:
        return ("error", type(exc).__name__)


for case in json.load(sys.stdin):
    before = result(case["before"], case["args"], case.get("signing", False))
    after = result(case["after"], case["args"], case.get("signing", False))
    if before[:3] != after[:3]:
        raise AssertionError(f'{case["name"]}: {before} != {after}')
    if before[0] == "ok" and after[3] > before[3]:
        raise AssertionError(f'{case["name"]}: optimized cost rose: {before} -> {after}')
print("independent P03 VM optimizer differential passed")
