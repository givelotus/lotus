"""Exercise generated Python binding with a test-only P01 wire adapter."""
import importlib.util
import json
import sys


def cs(n: int) -> bytes:
    if not 0 <= n < 253:
        raise ValueError("test adapter only supports small CompactSize")
    return bytes((n,))


def enc_bytes(data: bytes) -> bytes:
    return cs(len(data)) + data


def output(item: dict) -> bytes:
    value = int(item["valueAtoms"])
    raw = b"\x00" + value.to_bytes(8, "little")
    raw += cs(len(item["branches"]))
    raw += b"".join(bytes.fromhex(root) for root in item["branches"])
    raw += cs(len(item["paths"]))
    raw += b"".join(cs(len(path)) + b"".join(cs(i) for i in path) for path in item["paths"])
    return raw


class TestWireRuntime:
    def prepare_payment(self, artifact, context):
        if artifact["schema"] != "lotus-v2/payment-artifact/1":
            raise ValueError("artifact schema")
        return artifact, context

    def finalize_payment(self, plan, signature):
        artifact, context = plan
        script = bytes.fromhex(artifact["scriptHex"])
        header = (7).to_bytes(4, "little") + int(context["lock"]).to_bytes(8, "little")
        header += (1).to_bytes(2, "little") + len(context["outputs"]).to_bytes(2, "little")
        inp = bytes.fromhex(context["outpoint"]["txid"])
        inp += context["outpoint"]["index"].to_bytes(4, "little")
        inp += context["sequence"].to_bytes(4, "little")
        inp += b"\x01\x00\x01" + enc_bytes(script) + b"\x00\x01" + enc_bytes(signature)
        return header + inp + b"".join(output(item) for item in context["outputs"])


spec = importlib.util.spec_from_file_location("generated_payment", sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
fixture = json.loads(open(sys.argv[2], encoding="utf-8").read())
client = getattr(module, fixture["artifact"]["contract"])(fixture["artifact"], TestWireRuntime())
plan = client.prepare_spend(fixture["context"])
wire = client.finalize_spend(plan, bytes.fromhex(fixture["valid"]["signature"]))
if wire.hex() != fixture["valid"]["wire"]:
    raise SystemExit("Python generated binding witness bytes mismatch")
print("Python generated binding witness bytes match fixture")
