"""Explicit P01 spend/mint planner; no script or chain-context validation."""

from __future__ import annotations
from dataclasses import dataclass
import json
from typing import Any
from lotus_v2_call_runtime import (
    TARGET,
    cs,
    encode_value,
    hx,
    indexed_root,
    selected,
    sized,
    tagged,
    ui,
)

U128_MAX = (1 << 128) - 1
I128_MAX = (1 << 127) - 1


def _checked_add(a: int, b: int) -> int:
    result = a + b
    if result > U128_MAX:
        raise ValueError("u128 aggregate overflow")
    return result


def _seal(value: Any) -> str:
    def convert(obj: Any) -> Any:
        if type(obj) is bytes:
            return {"bytes": obj.hex()}
        raise TypeError(f"unsupported plan value {type(obj).__name__}")

    return json.dumps(value, default=convert, separators=(",", ":"), sort_keys=True)


def encode_asset_output(output: dict) -> bytes:
    flags = output["flags"]
    if type(flags) is not int or flags not in (0, 1, 2, 3):
        raise ValueError("output flags or policy")
    token, burn = bool(flags & 1), bool(flags & 2)
    token_id = output.get("tokenId")
    if token:
        if token_id is None or hx(token_id, 32) == bytes(32):
            raise ValueError("token ID required")
    elif token_id is not None:
        raise ValueError("native output has token ID")
    branches, paths = output["branches"], output["paths"]
    if not 1 <= len(branches) <= 16 or len(set(branches)) != len(branches):
        raise ValueError("output branch count or duplicate")
    if burn:
        if paths:
            raise ValueError("output path count")
    elif not 1 <= len(paths) <= 16:
        raise ValueError("output path count")
    previous = None
    for path in paths:
        if (
            not 1 <= len(path) <= 16
            or any(type(v) is not int or v < 0 or v >= len(branches) for v in path)
            or path != sorted(set(path))
        ):
            raise ValueError("invalid output path")
        if previous is not None and previous >= path:
            raise ValueError("output path order")
        previous = path
    return (
        bytes([flags])
        + ui(output["value"], 8)
        + (hx(token_id, 32) if token else b"")
        + cs(len(branches))
        + b"".join(hx(x, 32) for x in branches)
        + cs(len(paths))
        + b"".join(cs(len(path)) + b"".join(cs(v) for v in path) for path in paths)
    )


def _witnesses(item: dict) -> list[dict]:
    if item["kind"] == "mint":
        return [
            {
                "artifact": item["artifact"],
                "methodName": item["methodName"],
                "args": item["args"],
            }
        ]
    return item["witnesses"]


def _method(witness: dict, root: str, kind: str) -> dict:
    artifact = witness["artifact"]
    method = selected(artifact, witness["methodName"], allow_mint=True)
    if kind == "mint":
        if artifact.get("kind") != "token" or method.get("invocation") != "mint":
            raise ValueError("wrong artifact or method invocation kind")
    elif artifact.get("kind") == "token" or method.get("invocation") == "mint":
        raise ValueError("wrong artifact or method invocation kind")
    if artifact["policy"]["root"] != root or method["root"] != root:
        raise ValueError("witness branch root mismatch")
    arguments = witness["args"]
    if set(arguments) != {a["name"] for a in method["args"]}:
        raise ValueError("argument names mismatch")
    if len(method["args"]) > 32:
        raise ValueError("candidate call argument cap")
    for arg in method["args"]:
        value = arguments[arg["name"]]
        if arg["type"] == "Signature":
            if value is not None:
                raise ValueError("Signature argument must be empty signing slot")
        else:
            encode_value(arg["type"], value)
    return method


def _core_witness(witness: dict) -> bytes:
    method = next(
        m for m in witness["artifact"]["methods"] if m["name"] == witness["methodName"]
    )
    return (
        sized(hx(method["scriptHex"]))
        + cs(len(method["proof"]))
        + b"".join(hx(x, 32) for x in method["proof"])
    )


def _values(
    item: dict,
    index: int,
    signatures: dict[str, bytes] | None = None,
    projected: bool = False,
) -> list[list[bytes]]:
    values = []
    for j, witness in enumerate(_witnesses(item)):
        method = next(
            m
            for m in witness["artifact"]["methods"]
            if m["name"] == witness["methodName"]
        )
        args = []
        for arg in method["args"]:
            if arg["type"] == "Signature":
                key = f"{index}:{j}:{arg['name']}"
                value = (
                    bytes(64)
                    if projected
                    else (
                        encode_value("Signature", signatures[key])
                        if signatures is not None
                        else b""
                    )
                )
            else:
                value = encode_value(arg["type"], witness["args"][arg["name"]])
            args.append(value)
        values.append(args)
    return values


def _input_bytes(item: dict, values: list[list[bytes]], full: bool) -> bytes:
    witnesses = _witnesses(item)

    def encoded(witness: dict, j: int) -> bytes:
        core = _core_witness(witness)
        if not full:
            return core
        return core + cs(len(values[j])) + b"".join(sized(v) for v in values[j])

    if item["kind"] == "mint":
        return (
            hx(item["artifact"]["policy"]["root"], 32)
            + ui(0, 4)
            + ui(0xFFFFFFFF, 4)
            + b"\x03"
            + encoded(witnesses[0], 0)
        )
    return (
        hx(item["prevTxid"], 32)
        + ui(item["prevIndex"], 4)
        + ui(item["sequence"], 4)
        + b"\x01"
        + cs(item["pathIndex"])
        + cs(len(witnesses))
        + b"".join(encoded(w, j) for j, w in enumerate(witnesses))
    )


def _hash_parts(intent: dict, values: list[list[list[bytes]]]) -> dict:
    inputs, outputs = intent["inputs"], [
        encode_asset_output(o) for o in intent["outputs"]
    ]
    header = (
        ui(7, 4)
        + ui(intent.get("lock", 0), 8)
        + ui(len(inputs), 2)
        + ui(len(outputs), 2)
    )
    core = [_input_bytes(item, values[i], False) for i, item in enumerate(inputs)]
    full = [_input_bytes(item, values[i], True) for i, item in enumerate(inputs)]
    outputs_root = indexed_root([tagged("output", sized(o)) for o in outputs])
    chain = hx(intent["chainId"], 32)
    txid = tagged(
        "txid",
        chain
        + header
        + indexed_root([tagged("inputcore", x) for x in core])
        + outputs_root,
    )
    txhash = tagged(
        "txhash",
        chain
        + header
        + indexed_root([tagged("inputfull", x) for x in full])
        + outputs_root,
    )
    coins_root = indexed_root(
        [
            tagged(
                "coinentry",
                (
                    b"\x00"
                    if item["kind"] == "mint"
                    else sized(encode_asset_output(item["coin"]))
                ),
            )
            for item in inputs
        ]
    )
    return {
        "wire": header + b"".join(full) + b"".join(outputs),
        "txid": txid.hex(),
        "txhash": txhash.hex(),
        "coinsRoot": coins_root,
    }


def _accounting(intent: dict) -> tuple[int, dict[str, int], dict[str, int], int]:
    incoming: dict[str, int] = {}
    outgoing: dict[str, int] = {}
    explicit: dict[str, int] = {}
    native_in = native_out = token_outputs = 0

    def record(table: dict[str, int], token_id: str, value: int) -> None:
        table[token_id] = _checked_add(table.get(token_id, 0), value)

    for item in intent["inputs"]:
        if item["kind"] != "spend":
            continue
        coin = item["coin"]
        if coin["flags"] & 2:
            raise ValueError("burn output cannot be spent")
        if coin["flags"] & 1:
            record(incoming, coin["tokenId"], coin["value"])
        else:
            native_in = _checked_add(native_in, coin["value"])
    for output in intent["outputs"]:
        if output["flags"] & 1:
            record(outgoing, output["tokenId"], output["value"])
            token_outputs += 1
            if output["flags"] & 2:
                record(explicit, output["tokenId"], output["value"])
        else:
            native_out = _checked_add(native_out, output["value"])
    if native_out > native_in:
        raise ValueError("negative native fee")
    deltas, burns = {}, {}
    for token_id in incoming.keys() | outgoing.keys():
        input_amount, output_amount = incoming.get(token_id, 0), outgoing.get(
            token_id, 0
        )
        if output_amount > input_amount:
            delta = output_amount - input_amount
            if delta > I128_MAX:
                raise ValueError("mint delta exceeds VM int128")
            deltas[token_id] = delta
        burn = max(0, input_amount - output_amount) + explicit.get(token_id, 0)
        if burn:
            burns[token_id] = burn
    return native_in - native_out, deltas, burns, token_outputs


@dataclass(frozen=True)
class TransactionPlan:
    intent: dict
    seal: str
    unsigned_wire: bytes
    projected_full_bytes: int
    txid: str
    fee_atoms: int
    minimum_fee_atoms: int
    token_deltas: dict[str, int]
    token_burns: dict[str, int]
    requests: tuple[dict, ...]
    stages: dict


def prepare_transaction_call(intent: dict) -> TransactionPlan:
    if intent.get("profile") != TARGET:
        raise ValueError("unsupported profile")
    hx(intent["chainId"], 32)
    lock = intent.get("lock", 0)
    ui(lock, 8)
    if lock & 255 > 2 or (lock & 255 == 0 and lock != 0):
        raise ValueError("invalid P01 lock")
    dust = intent.get("dustLimitAtoms")
    if type(dust) is not int or dust < 0:
        raise ValueError("explicit dust limit required")
    inputs, outputs = intent["inputs"], intent["outputs"]
    if not 1 <= len(inputs) <= 65535 or len(outputs) > 65535:
        raise ValueError("input/output count")
    for output in outputs:
        encode_asset_output(output)
    seen, mint_ids, spends = set(), [], 0
    for item in inputs:
        kind = item["kind"]
        if kind == "mint":
            token_id = item["artifact"]["policy"]["root"]
            if hx(token_id, 32) == bytes(32):
                raise ValueError("zero mint token ID")
            _method(_witnesses(item)[0], token_id, "mint")
            key = token_id, 0
            mint_ids.append(token_id)
        elif kind == "spend":
            spends += 1
            hx(item["prevTxid"], 32)
            ui(item["prevIndex"], 4)
            ui(item["sequence"], 4)
            if item["sequence"] != 0xFFFFFFFF and item["sequence"] & ~0x40FFFF:
                raise ValueError("invalid P01 sequence")
            key = item["prevTxid"], item["prevIndex"]
            coin = item["coin"]
            encode_asset_output(coin)
            if coin["flags"] & 2:
                raise ValueError("burn output cannot be spent")
            path_index = item["pathIndex"]
            if (
                type(path_index) is not int
                or path_index < 0
                or path_index >= len(coin["paths"])
            ):
                raise ValueError("invalid path index")
            path = coin["paths"][path_index]
            if len(item["witnesses"]) != len(path):
                raise ValueError("required witness count")
            for j, witness in enumerate(item["witnesses"]):
                _method(witness, coin["branches"][path[j]], "spend")
        else:
            raise ValueError("unsupported input kind")
        if key in seen:
            raise ValueError("duplicate input outpoint")
        seen.add(key)
    if not spends:
        raise ValueError("ordinary transaction needs consuming input")
    fee, deltas, burns, token_outputs = _accounting(intent)
    if sorted(mint_ids) != sorted(deltas):
        raise ValueError("mint inputs do not match positive token deltas")
    empty = [_values(item, i) for i, item in enumerate(inputs)]
    projected = [_values(item, i, projected=True) for i, item in enumerate(inputs)]
    initial, predicted = _hash_parts(intent, empty), _hash_parts(intent, projected)
    minimum_fee = max(len(predicted["wire"]), 2 * dust * token_outputs)
    if fee < minimum_fee:
        raise ValueError("native fee below byte or token-output floor")
    requests = []
    for i, item in enumerate(inputs):
        for j, witness in enumerate(_witnesses(item)):
            method = next(
                m
                for m in witness["artifact"]["methods"]
                if m["name"] == witness["methodName"]
            )
            if item["kind"] == "mint":
                token_id = item["artifact"]["policy"]["root"]
                selector = (
                    b"\x03"
                    + hx(token_id, 32)
                    + ui(deltas[token_id], 16)
                    + hx(method["leaf"], 32)
                )
                invocation = {"tokenId": token_id, "positiveDelta": deltas[token_id]}
            else:
                branch_index = item["coin"]["paths"][item["pathIndex"]][j]
                selector = (
                    b"\x01" + ui(i, 4) + ui(branch_index, 4) + hx(method["leaf"], 32)
                )
                invocation = {"branchIndex": branch_index}
            digest = tagged(
                "sighash",
                hx(intent["chainId"], 32)
                + b"\x00"
                + hx(initial["txid"], 32)
                + initial["coinsRoot"]
                + selector,
            ).hex()
            for arg in method["args"]:
                if arg["type"] == "Signature":
                    requests.append(
                        {
                            "key": f"{i}:{j}:{arg['name']}",
                            "argument": arg["name"],
                            "mode": 0,
                            "digest": digest,
                            "inputIndex": i,
                            "witnessIndex": j,
                            "leaf": method["leaf"],
                            "feeAtoms": fee,
                            **invocation,
                        }
                    )
    stages = {
        "framing": "passed",
        "proof": "passed",
        "accounting": "passed",
        "signature": "unavailable",
        "invocation": "unavailable",
        "contextual": "unavailable",
        "block": "unavailable",
    }
    return TransactionPlan(
        intent,
        _seal(intent),
        initial["wire"],
        len(predicted["wire"]),
        initial["txid"],
        fee,
        minimum_fee,
        deltas,
        burns,
        tuple(requests),
        stages,
    )


def finalize_transaction_call(
    plan: TransactionPlan, signatures: dict[str, bytes]
) -> dict:
    if _seal(plan.intent) != plan.seal:
        raise ValueError("stale transaction plan")
    fresh = prepare_transaction_call(plan.intent)
    if (
        fresh.txid != plan.txid
        or fresh.unsigned_wire != plan.unsigned_wire
        or fresh.projected_full_bytes != plan.projected_full_bytes
        or fresh.fee_atoms != plan.fee_atoms
        or fresh.minimum_fee_atoms != plan.minimum_fee_atoms
        or fresh.token_deltas != plan.token_deltas
        or fresh.token_burns != plan.token_burns
        or fresh.requests != plan.requests
    ):
        raise ValueError("stale transaction plan")
    if set(signatures) != {r["key"] for r in fresh.requests}:
        raise ValueError("signature slots mismatch")
    values = [
        _values(item, i, signatures) for i, item in enumerate(plan.intent["inputs"])
    ]
    result = _hash_parts(plan.intent, values)
    if len(result["wire"]) != plan.projected_full_bytes:
        raise ValueError("projected wire length mismatch")
    if plan.fee_atoms < len(result["wire"]):
        raise ValueError("native fee below final byte floor")
    return {
        "wire": result["wire"],
        "txid": result["txid"],
        "txhash": result["txhash"],
        "stages": fresh.stages,
    }
