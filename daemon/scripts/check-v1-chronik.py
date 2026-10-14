#!/usr/bin/env python3
"""Compare a running Lotus node's RPC data with its Chronik disk reads."""

import argparse
import json
import subprocess
import urllib.request


def protobuf_fields(data):
    """Decode wire fields without requiring generated protobuf bindings."""
    pos = 0

    def varint():
        nonlocal pos
        value = 0
        for shift in range(0, 70, 7):
            byte = data[pos]
            pos += 1
            value |= (byte & 127) << shift
            if byte < 128:
                return value
        raise ValueError("Invalid protobuf varint")

    fields = {}
    while pos < len(data):
        key = varint()
        wire = key & 7
        if wire == 0:
            value = varint()
        elif wire == 2:
            size = varint()
            value = data[pos : pos + size]
            if len(value) != size:
                raise ValueError("Truncated protobuf field")
            pos += size
        else:
            raise ValueError(f"Unexpected protobuf wire type {wire}")
        fields.setdefault(key >> 3, []).append(value)
    return fields


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cli", required=True)
    parser.add_argument("--datadir", required=True)
    parser.add_argument("--rpcport", type=int, default=10604)
    parser.add_argument("--chronik-url", default="http://127.0.0.1:8331")
    parser.add_argument("--heights", type=int, nargs="*", default=[0, 1])
    args = parser.parse_args()

    def rpc(*params):
        output = subprocess.check_output(
            [args.cli, f"-datadir={args.datadir}", f"-rpcport={args.rpcport}"]
            + [str(p) for p in params],
            text=True,
        ).strip()
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            return output

    def chronik(path):
        with urllib.request.urlopen(args.chronik_url.rstrip("/") + path, timeout=30) as response:
            return protobuf_fields(response.read())

    info = chronik("/blockchain-info")
    indexed_height = info.get(2, [0])[0]
    indexed_hash = info[1][0][::-1].hex()
    assert rpc("getblockhash", indexed_height) == indexed_hash, "Chronik tip differs from RPC"
    heights = sorted(set(args.heights + [indexed_height]))
    checked_txs = 0
    for height in heights:
        assert height <= indexed_height, f"Chronik has not indexed height {height}"
        block_hash = rpc("getblockhash", height)
        header = chronik(f"/block-header/{height}")[1][0]
        assert len(header) == 160, f"Wrong header length at {height}"
        assert header.hex() == rpc("getblockheader", block_hash, "false"), f"Header differs at {height}"
        block = rpc("getblock", block_hash, 1)
        for txid in dict.fromkeys([block["tx"][0], block["tx"][-1]]):
            tx = chronik(f"/tx/{txid}")
            assert tx[1][0][::-1].hex() == txid, f"Merkleized TxId differs: {txid}"
            raw = chronik(f"/raw-tx/{txid}")[1][0]
            expected = rpc("getrawtransaction", txid, "false", block_hash)
            assert raw.hex() == expected, f"Transaction disk bytes differ: {txid}"
            assert tx[11][0] == len(raw), f"Transaction size differs: {txid}"
            checked_txs += 1
        print(f"Height {height}: 160-byte header, TxIds and raw transaction disk reads match")
    print(f"PASS: {len(heights)} blocks, {checked_txs} transactions; Chronik tip {indexed_height} ({indexed_hash})")


if __name__ == "__main__":
    main()
