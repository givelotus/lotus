#!/usr/bin/env python3
"""Actual native BTC/Chronik parity in new private regtest data only."""

import argparse
import base64
import hashlib
import json
import struct
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

p = argparse.ArgumentParser()
for name in ["node", "datadir", "protobuf-dir", "evidence"]:
    p.add_argument("--" + name, required=True, type=Path)
p.add_argument("--rpc-port", type=int, default=35443)
p.add_argument("--chronik-port", type=int, default=35331)
a = p.parse_args()
if a.datadir.exists():
    raise SystemExit("Refusing existing datadir")
a.datadir.mkdir(parents=True)
sys.path.insert(0, str(a.protobuf_dir))
import chronik_pb2 as pb
import websocket

process = None
ws = None
checks = []


def rpc(method, *params):
    cookie = (a.datadir / "regtest/.cookie").read_bytes().strip()
    req = urllib.request.Request(
        f"http://127.0.0.1:{a.rpc_port}",
        json.dumps(
            {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
        ).encode(),
        {"Authorization": "Basic " + base64.b64encode(cookie).decode()},
    )
    try:
        data = urllib.request.urlopen(req, timeout=30).read()
    except urllib.error.HTTPError as e:
        data = e.read()
    result = json.loads(data)
    if result.get("error"):
        raise RuntimeError(result["error"])
    return result["result"]


def http(path, kind, request=None):
    req = urllib.request.Request(
        f"http://127.0.0.1:{a.chronik_port}{path}",
        None if request is None else request.SerializeToString(),
        {"Content-Type": "application/x-protobuf"},
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        assert response.headers["Content-Type"] == "application/x-protobuf"
        return kind.FromString(response.read())


def until(fn):
    end = time.monotonic() + 30
    last = None
    while time.monotonic() < end:
        try:
            if fn():
                return
        except (OSError, RuntimeError, ValueError) as e:
            last = e
        time.sleep(0.05)
    raise AssertionError(f"timed out: {last}")


def sync():
    def match():
        info = http("/blockchain-info", pb.BlockchainInfo)
        return info.tip_height == rpc("getblockcount") and info.tip_hash[
            ::-1
        ].hex() == rpc("getbestblockhash")

    until(match)


def start(reindex=False):
    global process
    with (a.datadir / "process.log").open("ab") as log:
        process = subprocess.Popen(
            [
                str(a.node),
                f"-datadir={a.datadir}",
                "-regtest",
                "-chronik=1",
                f"-chronikbind=127.0.0.1:{a.chronik_port}",
                f"-rpcport={a.rpc_port}",
                "-listen=0",
                "-connect=0",
                "-fallbackfee=0.00001",
                "-fastprune=1",  # small files for rollover testing, no pruning enabled
            ]
            + (["-chronikreindex=1"] if reindex else []),
            stdout=log,
            stderr=log,
        )
    until(lambda: rpc("getblockcount") >= 0)
    sync()


def stop(crash=False):
    global ws
    if crash:
        process.kill()
    else:
        rpc("stop")
    process.wait(timeout=30)
    if ws is not None:
        ws.close(timeout=1)
        ws = None


def subscribe():
    socket = websocket.create_connection(
        f"ws://127.0.0.1:{a.chronik_port}/ws", timeout=5
    )
    socket.send_binary(
        pb.WsSub(
            script=pb.WsSubScript(script_type="other", payload=script)
        ).SerializeToString()
    )
    # Frames are handled in order; receiving this pong fences subscription setup.
    socket.ping(b"subscribed")
    frame = socket.recv_frame()
    assert frame.opcode == websocket.ABNF.OPCODE_PONG and frame.data == b"subscribed"
    return socket


def ws_tx(txid, kind):
    while True:
        message = pb.WsMsg.FromString(ws.recv())
        assert not message.HasField("error")
        if message.HasField("tx") and message.tx.txid[::-1].hex() == txid:
            assert message.tx.msg_type == kind, message
            return


def transaction(prev, amount, script):
    txin = bytes.fromhex(prev)[::-1] + struct.pack("<I", 0) + b"\x00" + b"\xff" * 4
    txout = struct.pack("<q", amount) + bytes([len(script)]) + script
    stripped = struct.pack("<I", 2) + b"\x01" + txin + b"\x01" + txout + b"\x00" * 4
    raw = (
        struct.pack("<I", 2)
        + b"\x00\x01\x01"
        + txin
        + b"\x01"
        + txout
        + b"\x01\x01\x51"
        + b"\x00" * 4
    )
    return hashlib.sha256(hashlib.sha256(stripped).digest()).digest()[::-1].hex(), raw


def parity(txid, raw, confirmed, value):
    until(lambda: http("/raw-tx/" + txid, pb.RawTx).raw_tx == raw)
    tx = http("/tx/" + txid, pb.Tx)
    native = rpc("decoderawtransaction", raw.hex())
    assert tx.txid[::-1].hex() == native["txid"] == txid and native["hash"] != txid
    assert tx.size == native["size"] == len(raw)
    assert tx.HasField("block") == confirmed and not tx.is_final
    assert tx.inputs[0].sats == value and tx.inputs[0].output_script == script
    return tx


try:
    start()
    try:
        rpc("loadtxoutset", "not-opened-while-chronik-enabled.dat")
        raise AssertionError("Unvalidated snapshot handoff was permitted")
    except RuntimeError as error:
        assert "unsupported while Chronik is enabled" in str(error)
    checks.append("unsupported snapshot handoff rejected explicitly")
    script = b"\x00\x20" + hashlib.sha256(b"\x51").digest()
    descriptor = rpc("getdescriptorinfo", "raw(" + script.hex() + ")")["descriptor"]
    blocks = rpc("generatetodescriptor", 101, descriptor)
    sync()
    for height in [0, 1, 100, 101]:
        h = rpc("getblockhash", height)
        header = http("/block-header/" + h, pb.BlockHeader).raw_header
        assert len(header) == 80 and header.hex() == rpc("getblockheader", h, False)
    checks.append("80-byte headers/genesis/tip RPC parity")
    ws = subscribe()
    coinbase = rpc("getblock", blocks[0], 2)["tx"][0]
    txid, raw = transaction(coinbase["txid"], 5_000_000_000 - 1000, script)
    assert rpc("sendrawtransaction", raw.hex()) == txid
    ws_tx(txid, pb.TX_ADDED_TO_MEMPOOL)
    first = parity(txid, raw, False, 5_000_000_000).time_first_seen
    assert first > 0
    checks.append(
        "native witness admission, full mempool raw/size/txid/spent coins/time"
    )
    childid, child = transaction(txid, 5_000_000_000 - 2000, script)
    response = http(
        "/broadcast-tx", pb.BroadcastTxResponse, pb.BroadcastTxRequest(raw_tx=child)
    )
    assert response.txid[::-1].hex() == childid
    ws_tx(childid, pb.TX_ADDED_TO_MEMPOOL)
    parity(childid, child, False, 5_000_000_000 - 1000)
    assert set(rpc("getrawmempool")) == {txid, childid}
    checks.append("Chronik witness broadcast and unconfirmed parent coins")
    utxos = http("/script/other/" + script.hex() + "/utxos", pb.ScriptUtxos)
    assert utxos.script == script
    assert any(u.outpoint.txid[::-1].hex() == childid for u in utxos.utxos)
    assert not any(u.outpoint.txid[::-1].hex() == txid for u in utxos.utxos)
    checks.append("other/full-script witness indexing and spent-output removal")
    mined = rpc("generatetodescriptor", 1, descriptor)[0]
    sync()
    assert rpc("getrawmempool") == []
    ws_tx(txid, pb.TX_CONFIRMED)
    ws_tx(childid, pb.TX_CONFIRMED)
    checks.append("existing WebSocket witness additions and confirmations")
    assert parity(txid, raw, True, 5_000_000_000).time_first_seen == first
    parity(childid, child, True, 5_000_000_000 - 1000)
    assert any((a.datadir / "regtest/blocks/xor.dat").read_bytes())
    assert http("/raw-tx/" + coinbase["txid"], pb.RawTx).raw_tx.hex() == coinbase["hex"]
    checks.append("confirmed full witness XOR blk reads and undo coins")
    rpc("invalidateblock", mined)
    sync()
    until(lambda: set(rpc("getrawmempool")) == {txid, childid})
    parity(txid, raw, False, 5_000_000_000)
    parity(childid, child, False, 5_000_000_000 - 1000)
    rpc("reconsiderblock", mined)
    sync()
    parity(childid, child, True, 5_000_000_000 - 1000)
    checks.append("disconnect/reconnect and witness resurrection")
    stop()
    start()
    parity(txid, raw, True, 5_000_000_000)
    parity(childid, child, True, 5_000_000_000 - 1000)
    checks.append("clean restart index/raw/undo parity")
    rpc("generatetodescriptor", 300, descriptor)
    sync()
    assert len(list((a.datadir / "regtest/blocks").glob("blk*.dat"))) >= 2
    rollover_coinbase = rpc("getblock", rpc("getbestblockhash"), 2)["tx"][0]
    assert (
        http("/raw-tx/" + rollover_coinbase["txid"], pb.RawTx).raw_tx.hex()
        == rollover_coinbase["hex"]
    )
    checks.append(
        "small-file native block/undo rollover and full raw parity before crash"
    )
    stop(crash=True)
    start()
    parity(childid, child, True, 5_000_000_000 - 1000)
    checks.append("SIGKILL restart tip reconciliation (not power-loss proof)")
    package_coinbase = rpc("getblock", blocks[1], 2)["tx"][0]
    package_parent, parent_raw = transaction(
        package_coinbase["txid"], 5_000_000_000 - 1000, script
    )
    p2wpkh = bytes.fromhex("0014" + "11" * 20)
    package_child, child_raw = transaction(package_parent, 5_000_000_000 - 2000, p2wpkh)
    package = rpc("submitpackage", [parent_raw.hex(), child_raw.hex()])
    assert package["package_msg"] == "success", package
    parity(package_parent, parent_raw, False, 5_000_000_000)
    parity(package_child, child_raw, False, 5_000_000_000 - 1000)
    assert any(
        u.outpoint.txid[::-1].hex() == package_child
        for u in http("/script/other/" + p2wpkh.hex() + "/utxos", pb.ScriptUtxos).utxos
    )
    p2tr = bytes.fromhex(
        "512079be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798"
    )
    taproot_txid, taproot_raw = transaction(childid, 5_000_000_000 - 3000, p2tr)
    assert rpc("sendrawtransaction", taproot_raw.hex()) == taproot_txid
    parity(taproot_txid, taproot_raw, False, 5_000_000_000 - 2000)
    assert any(
        u.outpoint.txid[::-1].hex() == taproot_txid
        for u in http("/script/other/" + p2tr.hex() + "/utxos", pb.ScriptUtxos).utxos
    )
    checks.append(
        "package admission coin snapshots plus P2WPKH/P2TR full-script indexing"
    )
    validated = http("/validate-tx", pb.Tx, pb.RawTx(raw_tx=taproot_raw))
    assert validated.txid[::-1].hex() == taproot_txid and validated.size == len(
        taproot_raw
    )
    for request in [
        pb.BroadcastTxRequest(raw_tx=b"\x00"),
        pb.BroadcastTxRequest(raw_tx=taproot_raw, finalization_timeout_secs=1),
    ]:
        try:
            http("/broadcast-tx", pb.BroadcastTxResponse, request)
            raise AssertionError("Expected HTTP 400")
        except urllib.error.HTTPError as error:
            assert error.code == 400
    checks.append("witness validate-tx, malformed HTTP400 and unsupported finality")
    stop()
    start()
    parity(package_parent, parent_raw, False, 5_000_000_000)
    parity(package_child, child_raw, False, 5_000_000_000 - 1000)
    parity(taproot_txid, taproot_raw, False, 5_000_000_000 - 2000)
    checks.append("persisted witness mempool bootstrap/restart parity")
    ws = subscribe()
    conflict_coinbase = rpc("getblock", blocks[2], 2)["tx"][0]
    conflict_parent, conflict_raw = transaction(
        conflict_coinbase["txid"], 5_000_000_000 - 1000, script
    )
    conflict_child, conflict_child_raw = transaction(
        conflict_parent, 5_000_000_000 - 2000, script
    )
    conflict_grandchild, conflict_grandchild_raw = transaction(
        conflict_child, 5_000_000_000 - 3000, script
    )
    for txid_to_add, wire in [
        (conflict_parent, conflict_raw),
        (conflict_child, conflict_child_raw),
        (conflict_grandchild, conflict_grandchild_raw),
    ]:
        assert rpc("sendrawtransaction", wire.hex()) == txid_to_add
        ws_tx(txid_to_add, pb.TX_ADDED_TO_MEMPOOL)
    parity(conflict_grandchild, conflict_grandchild_raw, False, 5_000_000_000 - 2000)
    replacement_id, replacement_raw = transaction(
        conflict_coinbase["txid"], 5_000_000_000 - 10000, script
    )
    assert rpc("sendrawtransaction", replacement_raw.hex()) == replacement_id
    ws_tx(conflict_grandchild, pb.TX_REMOVED_FROM_MEMPOOL)
    ws_tx(conflict_child, pb.TX_REMOVED_FROM_MEMPOOL)
    ws_tx(conflict_parent, pb.TX_REMOVED_FROM_MEMPOOL)
    ws_tx(replacement_id, pb.TX_ADDED_TO_MEMPOOL)
    checks.append("WebSocket child-first RBF removals and replacement addition")
    parity(replacement_id, replacement_raw, False, 5_000_000_000)
    for removed in [conflict_parent, conflict_child, conflict_grandchild]:
        assert removed not in rpc("getrawmempool")
        try:
            http("/tx/" + removed, pb.Tx)
            raise AssertionError("Removed transaction still indexed")
        except urllib.error.HTTPError as error:
            assert error.code == 404
    checks.append("RBF descendant eviction with native unordered removal callbacks")
    observed_rss_kib = int(
        subprocess.check_output(
            ["ps", "-o", "rss=", "-p", str(process.pid)], text=True
        ).strip()
    )
    rpc("generatetodescriptor", 1, descriptor)
    sync()
    parity(package_child, child_raw, True, 5_000_000_000 - 1000)
    parity(taproot_txid, taproot_raw, True, 5_000_000_000 - 2000)
    # Keep native HTTP handlers active while shutdown interrupts them. Only the
    # process created by this test is stopped, and requests have finite timeouts.
    finished = threading.Event()
    started = threading.Event()
    reader_errors = []
    completed_requests = []

    def query_during_shutdown():
        while not finished.is_set():
            try:
                http("/raw-tx/" + childid, pb.RawTx)
                completed_requests.append(1)
                started.set()
            except OSError:
                return
            except Exception as error:
                reader_errors.append(str(error))
                started.set()
                return

    reader = threading.Thread(target=query_during_shutdown)
    reader.start()
    assert started.wait(timeout=5) and completed_requests and not reader_errors
    stop()
    finished.set()
    reader.join(timeout=10)
    assert not reader.is_alive() and process.returncode == 0 and not reader_errors
    start()
    parity(childid, child, True, 5_000_000_000 - 1000)
    checks.append("active HTTP shutdown/drain and restart without deadlock")
    stop()
    start(reindex=True)
    parity(childid, child, True, 5_000_000_000 - 1000)
    parity(package_child, child_raw, True, 5_000_000_000 - 1000)
    checks.append(
        "Chronik-only reindex/bootstrap across existing native witness blocks"
    )
    assert rpc("verifychain", 4, 0)
    checks.append("native verifychain level4 all blocks")
    result = {
        "status": "PASS",
        "checks": checks,
        "height": rpc("getblockcount"),
        "datadir": str(a.datadir),
        "observed_rss_kib": observed_rss_kib,
        "http_requests_during_shutdown_test": len(completed_requests),
        "resource_scope": "One small regtest process; no load/leak scaling claim",
        "parent": txid,
        "child": childid,
    }
    a.evidence.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
finally:
    if process is not None and process.poll() is None:
        stop()
