"""JSON runner for one bounded P03 invocation; not transaction validation."""

import argparse
import json
import sys
from typing import Any

from .encoding import Output, Profile as OutputProfile
from .vm import (SigningContext, UnsupportedFeature, VMError, VMProfile,
                 decode, evaluate, static_cost, success_scan,
                 validate_invocation_inputs)
from .vm_context import InputView, InvocationContext


def _hex(value: Any, name: str) -> bytes:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a hex string")
    try:
        return bytes.fromhex(value)
    except ValueError as exc:
        raise ValueError(f"{name} is not hex") from exc


def _cost_formula(value: Any):
    if type(value) is int and value > 0:
        return value
    if not isinstance(value, dict) or set(value) != {"base", "operand_byte", "result_byte"}:
        raise ValueError("cost must be positive integer or base/operand_byte/result_byte formula")
    base, operand, result = (value[name] for name in ("base", "operand_byte", "result_byte"))
    if any(type(x) is not int or x < 0 for x in (base, operand, result)) or base == 0:
        raise ValueError("cost coefficients must be nonnegative with positive base")
    return lambda operands, results: base + operand * sum(operands) + result * sum(results)


def _profile(raw: Any) -> VMProfile:
    if not isinstance(raw, dict):
        raise ValueError("profile object required")
    keys = ("max_script_bytes", "max_arguments", "max_element_bytes",
            "max_stack_items", "max_altstack_items", "max_vm_bytes",
            "max_ast_depth", "max_invocation_cost", "structural_byte_cost")
    try:
        params = {name: raw[name] for name in keys}
        schedule = raw["opcode_costs"]
    except KeyError as exc:
        raise ValueError(f"missing explicit profile field {exc.args[0]}") from exc
    if not isinstance(schedule, dict):
        raise ValueError("opcode_costs must be an object")
    costs = {}
    for key, value in schedule.items():
        if not isinstance(key, str) or len(key) != 2:
            raise ValueError("opcode cost keys must be two hex digits")
        try:
            op = int(key, 16)
        except ValueError as exc:
            raise ValueError("opcode cost key is not hex") from exc
        if op in costs:
            raise ValueError("duplicate opcode cost")
        costs[op] = _cost_formula(value)
    return VMProfile(**params, opcode_costs=costs)


def _signing(raw: Any) -> SigningContext | None:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ValueError("signing must be an object")
    try:
        if not isinstance(raw["messages"], dict) or any(
            mode not in ("0", "1", "2") for mode in raw["messages"]
        ):
            raise ValueError("signing messages must use decimal mode keys 0..2")
        messages = {int(mode): _hex(digest, f"message {mode}")
                    for mode, digest in raw["messages"].items()}
        return SigningContext(_hex(raw["selected_leaf_hash"], "selected_leaf_hash"),
                              messages, raw["invocation_kind"],
                              raw["input_index"], raw["output_count"])
    except KeyError as exc:
        raise ValueError(f"missing signing field {exc.args[0]}") from exc


def _output(raw: Any) -> Output:
    if not isinstance(raw, dict):
        raise ValueError("output must be object")
    try:
        return Output(raw["flags"], raw["value"],
                      None if raw.get("token_id") is None else _hex(raw["token_id"], "token_id"),
                      tuple(_hex(root, "branch root") for root in raw["branches"]),
                      tuple(tuple(path) for path in raw["paths"]))
    except KeyError as exc:
        raise ValueError(f"missing output field {exc.args[0]}") from exc


def _invocation(raw: Any) -> InvocationContext | None:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ValueError("invocation must be object")
    try:
        profile = OutputProfile(**raw["output_profile"])
        inputs = tuple(InputView(item["flags"],
                                 None if item.get("coin") is None else _output(item["coin"]),
                                 None if item.get("mint_token_id") is None else
                                 _hex(item["mint_token_id"], "mint_token_id"))
                       for item in raw["inputs"])
        outputs = tuple(_output(item) for item in raw["outputs"])
        return InvocationContext(inputs, outputs, raw["invocation_kind"],
                                 raw["input_index"], _hex(raw["branch_root"], "branch_root"),
                                 profile, raw.get("selected_path_index"),
                                 raw.get("selected_branch_index"), raw.get("mint_delta"))
    except KeyError as exc:
        raise ValueError(f"missing invocation field {exc.args[0]}") from exc


def run_invocation(case: dict[str, Any]) -> dict[str, Any]:
    """Return a stage-only trace with explicit tool errors, never a tx verdict."""
    stage = "input"
    trace: list[str] = []
    charge: int | None = None
    try:
        if not isinstance(case, dict):
            raise ValueError("invocation must be an object")
        script = _hex(case["script"], "script")
        if not isinstance(case["args"], list):
            raise ValueError("args must be a list of hex strings")
        args = tuple(_hex(item, "argument") for item in case["args"])
        profile = _profile(case["profile"])
        signing = _signing(case.get("signing"))
        invocation = _invocation(case.get("invocation"))
        if "transaction_context" in case:
            if signing is not None or invocation is not None:
                raise ValueError("exact transaction context excludes supplied VM/signing views")
            from .signing import TxProfile, decode_transaction
            from .encoding import decode_output
            from .vm_context import authenticated_context
            raw = case["transaction_context"]
            tx_profile = TxProfile(**raw["profile"])
            tx = decode_transaction(_hex(raw["full_tx"], "full_tx"), tx_profile)
            chain = _hex(raw["chain_id"], "chain_id")
            output_profile = OutputProfile(16, 16, 812, 8192)
            coins = tuple(None if item is None else decode_output(_hex(item, "coin"), output_profile)
                          for item in raw["coins"])
            invocation, signing = authenticated_context(tx, tx_profile, chain, coins,
                raw["input_index"], raw["witness_index"])
            active = tx.inputs[raw["input_index"]].witnesses[raw["witness_index"]]
            if script != active.script or args != active.arguments:
                raise ValueError("script/arguments differ from exact transaction witness")
        input_count = case.get("input_count", invocation.input_count if invocation else None)
        output_count = case.get("output_count", invocation.output_count if invocation else None)
        if any(type(count) is not int or not 0 <= count <= 65535
               for count in (input_count, output_count)):
            raise ValueError("transaction counts must be u16")
        initial = validate_invocation_inputs(script, args, profile, input_count=input_count,
                                             output_count=output_count, signing=signing,
                                             invocation=invocation)
        trace.append("input_framed")
        stage = "success_scan"
        automatic = success_scan(script, profile)
        trace.append("success_scanned")
        if not automatic:
            stage = "decode"
            ast = decode(script, profile)
            trace.append("decoded")
            stage = "static_charge"
            from .vm_cost import bind_authenticated_field_sizes
            bound_fields = (bind_authenticated_field_sizes(
                None, invocation, max_element_bytes=profile.max_element_bytes)
                if invocation is not None else None)
            charge = static_cost(ast, profile, input_count=input_count,
                                 output_count=output_count,
                                 initial_sizes=tuple(map(len, initial)),
                                 script_length=len(script),
                                 field_sizes=bound_fields)
            charge += len(script) * profile.structural_byte_cost
            if charge > profile.max_invocation_cost:
                raise VMError("static cost exceeds bound")
            trace.append("charged")
        stage = "execution"
        result = evaluate(script, args, profile, input_count=input_count,
                          output_count=output_count, signing=signing,
                          invocation=invocation)
        trace.append("automatic_success" if result.automatic else "executed")
        return {"accepted_invocation": True, "automatic_success": result.automatic,
                "charged_cost": result.charged_cost, "final_stack": None if result.stack is None
                else [item.hex() for item in result.stack], "trace": trace}
    except (KeyError, TypeError, ValueError, VMError, UnsupportedFeature) as exc:
        return {"accepted_invocation": False, "error_kind": type(exc).__name__,
                "error": str(exc), "stage": stage, "charged_cost": charge,
                "trace": trace}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", nargs="?", help="JSON case file; default is stdin")
    args = parser.parse_args()
    try:
        with open(args.case, encoding="utf-8") if args.case else sys.stdin as source:
            case = json.load(source)
        result = run_invocation(case)
    except (OSError, json.JSONDecodeError) as exc:
        result = {"accepted_invocation": False, "error_kind": type(exc).__name__,
                  "error": str(exc), "stage": "input", "trace": []}
    print(json.dumps(result, sort_keys=True))
    return 0 if result["accepted_invocation"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
