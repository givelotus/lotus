"""Cross-language check for explicit P01 spend/mint plans."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))
from lotus_v2_transaction_runtime import (
    prepare_transaction_call,
    finalize_transaction_call,
)

payload = json.load(sys.stdin)
intent = payload["intent"]
intent["dustLimitAtoms"] = int(intent["dustLimitAtoms"])


def convert_output(output):
    output["value"] = int(output["value"])


for output in intent["outputs"]:
    convert_output(output)
for item in intent["inputs"]:
    if item["kind"] == "spend":
        convert_output(item["coin"])

plan = prepare_transaction_call(intent)
signatures = {key: bytes.fromhex(value) for key, value in payload["signatures"].items()}
final = finalize_transaction_call(plan, signatures)
print(
    json.dumps(
        {
            "wire": final["wire"].hex(),
            "txid": final["txid"],
            "txhash": final["txhash"],
            "feeAtoms": str(plan.fee_atoms),
            "minimumFeeAtoms": str(plan.minimum_fee_atoms),
            "tokenDeltas": {
                key: str(value) for key, value in plan.token_deltas.items()
            },
            "tokenBurns": {key: str(value) for key, value in plan.token_burns.items()},
            "requests": [
                {
                    "key": request["key"],
                    "digest": request["digest"],
                    "leaf": request["leaf"],
                    "branchIndex": request.get("branchIndex"),
                    "tokenId": request.get("tokenId"),
                    "positiveDelta": (
                        str(request["positiveDelta"])
                        if "positiveDelta" in request
                        else None
                    ),
                }
                for request in plan.requests
            ],
        }
    )
)
