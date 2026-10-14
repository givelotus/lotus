"""Independent Python P03 differential check for compiler optimizer fixtures."""
import json
import sys

from lotus_v2_reference.vm import ASSIGNED, SigningContext, UnsupportedFeature, VMError, VMProfile, branch_leaf_hash, evaluate


profile = VMProfile(8192, 8, 8192, 128, 16, 16384, 32, 1_000_000, 1,
                    {op: 1 for op in ASSIGNED})


def result(script_hex, args, signing=False, input_count=None, output_count=None):
    try:
        script = bytes.fromhex(script_hex)
        context = SigningContext(branch_leaf_hash(script), {0: bytes(32)}, 'spend', 0, 1) if signing else None
        value = evaluate(script, tuple(bytes.fromhex(arg) for arg in args), profile,
                         input_count=input_count if input_count is not None else (1 if signing else 0),
                         output_count=output_count if output_count is not None else (1 if signing else 0),
                         signing=context)
        return ("ok", [item.hex() for item in value.stack or ()], value.success, value.charged_cost)
    except UnsupportedFeature:
        raise
    except VMError as exc:
        return ("error", type(exc).__name__, str(exc))


for case in json.load(sys.stdin):
    before = result(case["before"], case["args"], case.get("signing", False), case.get("input_count"), case.get("output_count"))
    after = result(case["after"], case["args"], case.get("signing", False), case.get("input_count"), case.get("output_count"))
    if before[0] != case["expected"] or after[0] != case["expected"]:
        raise AssertionError(f'{case["name"]}: expected {case["expected"]}, got {before}, {after}')
    if before[:2] != after[:2] or (before[0] == "ok" and before[2] != after[2]):
        raise AssertionError(f'{case["name"]}: {before} != {after}')
    if before[0] == "ok" and after[3] > before[3]:
        raise AssertionError(f'{case["name"]}: optimized cost rose: {before} -> {after}')
print("independent P03 VM optimizer differential passed")
