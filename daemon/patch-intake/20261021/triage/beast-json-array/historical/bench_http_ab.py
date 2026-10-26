#!/usr/bin/env python3
"""A/B benchmark: libevent evhttp (baseline) vs Boost.Beast HTTP server.

Targets
  A baseline : /private/tmp/bitcoind-baseline-evhttp-asio, plain HTTP
  B beast    : /private/tmp/build-beast-http-p2p/src/bitcoind, plain HTTP
  C beast-tls: same binary, https:// (TLS 1.3, async_detect_ssl)
  D beast-zstd: same binary, plain HTTP with Accept-Encoding: zstd

Both binaries are built from the same tree, same flags; the baseline is
Bitcoin ABC 1fb7db17 (evhttp + -rpcthreads worker queue). Every target runs
on an APFS clone of one prepared regtest datadir, with identical
-rpcthreads/-rpcworkqueue. Clients: one process per keep-alive connection.

Workloads (c = 1, 16, 64)
  1 getblockchaininfo
  2 getblock <1000-tx block> verbosity=2
  3 JSON-RPC batch of 50 getblockhash
  4 getrawmempool (c=16) while a fresh node syncs 3000 blocks from the
    server: over /p2p/ws on the RPC port (Beast) or TCP P2P (baseline).
"""

import base64
import json
import multiprocessing as mp
import os
import shutil
import socket
import ssl
import statistics
import subprocess
import sys
import time
import urllib.request

# evhttp + the -ecash caching fix (patch 0005), so the A/B differs only in
# the HTTP server. The original evhttp binary is BASELINE_ORIG.
BASELINE = "/private/tmp/bitcoind-baseline-evhttp-ecashfix"
BASELINE_ORIG = "/private/tmp/bitcoind-baseline-evhttp-asio"
LOAD = "/private/tmp/beast-http-p2p-bench/httpload"
NEW = "/private/tmp/build-beast-http-p2p/src/bitcoind"
WORK = "/private/tmp/beast-http-p2p-bench/http"
TEMPLATE = os.path.join(WORK, "template")
USER, PASSWORD = "bench", "bench"
RPC_PORT, P2P_PORT = 31443, 31444
SYNC_RPC_PORT, SYNC_P2P_PORT = 31445, 31446
COMMON_ARGS = [
    "-regtest", "-server=1", f"-rpcuser={USER}", f"-rpcpassword={PASSWORD}",
    "-rpcthreads=16", "-rpcworkqueue=256", "-listen=1", "-discover=0",
    "-dnsseed=0", "-fixedseeds=0", "-printtoconsole=0", "-persistmempool=1",
    "-maxmempool=300", "-txindex=0",
]
SMALL_REQUESTS = 10_000
LARGE_REQUESTS = 2_000
CONCURRENCY = [1, 16, 64]
AUTH = "Basic " + base64.b64encode(f"{USER}:{PASSWORD}".encode()).decode()


# ---------------------------------------------------------------- node helpers
def rpc(port, method, params=None, timeout=600):
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/",
        data=json.dumps({"method": method, "params": params or [], "id": 1}).encode(),
        headers={"Authorization": AUTH, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        out = json.loads(resp.read())
    if out.get("error"):
        raise RuntimeError(out["error"])
    return out["result"]


def wait_rpc(port, proc, timeout=120):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"node on {port} exited with {proc.returncode}")
        try:
            rpc(port, "getblockcount", timeout=5)
            return
        except Exception:
            time.sleep(0.2)
    raise TimeoutError(f"node on {port} did not start")


def start_node(binary, datadir, rpc_port, p2p_port, extra=()):
    os.makedirs(datadir, exist_ok=True)
    args = [binary, f"-datadir={datadir}", f"-rpcport={rpc_port}",
            f"-port={p2p_port}", f"-bind=127.0.0.1:{p2p_port}", *COMMON_ARGS,
            *extra]
    proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    wait_rpc(rpc_port, proc)
    return proc


def stop_node(port, proc):
    try:
        rpc(port, "stop", timeout=30)
    except Exception:
        pass
    try:
        proc.wait(timeout=120)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()


def clone_dir(src, dst):
    if os.path.exists(dst):
        shutil.rmtree(dst)
    subprocess.check_call(["cp", "-cR", src, dst])


# ---------------------------------------------------------------- chain setup
def prepare_template():
    if os.path.exists(os.path.join(TEMPLATE, "done")):
        return json.load(open(os.path.join(TEMPLATE, "done")))
    if os.path.exists(TEMPLATE):
        shutil.rmtree(TEMPLATE)
    print("Preparing regtest datadir (once)...", flush=True)
    proc = start_node(NEW, TEMPLATE, RPC_PORT, P2P_PORT, ["-tlsephemeral=0"])
    try:
        rpc(RPC_PORT, "createwallet", ["bench"])
        addr = rpc(RPC_PORT, "getnewaddress")
        rpc(RPC_PORT, "generatetoaddress", [150, addr])
        # 1000 outputs to spend independently
        dests = {rpc(RPC_PORT, "getnewaddress"): 1000 for _ in range(1000)}
        rpc(RPC_PORT, "sendmany", ["", dests])
        rpc(RPC_PORT, "generatetoaddress", [1, addr])
        for _ in range(1000):
            rpc(RPC_PORT, "sendtoaddress", [rpc(RPC_PORT, "getnewaddress"), 500])
        big = rpc(RPC_PORT, "generatetoaddress", [1, addr])[0]
        assert len(rpc(RPC_PORT, "getblock", [big, 1])["tx"]) >= 1000
        # Extra blocks for the P2P sync workload
        for _ in range(28):
            rpc(RPC_PORT, "generatetoaddress", [100, addr])
        # A populated mempool for getrawmempool
        for _ in range(500):
            rpc(RPC_PORT, "sendtoaddress", [rpc(RPC_PORT, "getnewaddress"), 100])
        info = {
            "big_block": big,
            "height": rpc(RPC_PORT, "getblockcount"),
            "mempool": rpc(RPC_PORT, "getmempoolinfo")["size"],
            "big_block_v2_bytes": len(json.dumps(rpc(RPC_PORT, "getblock", [big, 2]))),
        }
        rpc(RPC_PORT, "unloadwallet", ["bench"])
    finally:
        stop_node(RPC_PORT, proc)
    json.dump(info, open(os.path.join(TEMPLATE, "done"), "w"))
    return info


# ---------------------------------------------------------------- HTTP client
def build_request(body, accept_zstd):
    payload = json.dumps(body).encode()
    hdrs = [
        "POST / HTTP/1.1",
        f"Host: 127.0.0.1:{RPC_PORT}",
        f"Authorization: {AUTH}",
        "Content-Type: application/json",
        "Connection: keep-alive",
        f"Content-Length: {len(payload)}",
    ]
    if accept_zstd:
        hdrs.append("Accept-Encoding: zstd")
    return ("\r\n".join(hdrs) + "\r\n\r\n").encode() + payload


def connect(tls):
    sock = socket.create_connection(("127.0.0.1", RPC_PORT))
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    if tls:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        sock = ctx.wrap_socket(sock)
    return sock


def read_response(sock, buf):
    while b"\r\n\r\n" not in buf:
        chunk = sock.recv(1 << 20)
        if not chunk:
            raise ConnectionError("closed")
        buf += chunk
    head, _, rest = buf.partition(b"\r\n\r\n")
    status = int(head.split(b" ", 2)[1])
    length = 0
    for line in head.split(b"\r\n")[1:]:
        k, _, v = line.partition(b":")
        if k.strip().lower() == b"content-length":
            length = int(v)
    while len(rest) < length:
        chunk = sock.recv(max(1 << 20, length - len(rest)))
        if not chunk:
            raise ConnectionError("closed")
        rest += chunk
    return status, len(head) + 4 + length, rest[length:]


def worker(args):
    request, n, tls, barrier, deadline_flag = args
    sock = connect(tls)
    buf = b""
    # warm up the connection (TLS handshake etc.)
    sock.sendall(request)
    _, _, buf = read_response(sock, buf)
    barrier.wait()
    lat, wire, errors = [], 0, 0
    start = time.perf_counter()
    i = 0
    while (n is not None and i < n) or (n is None and not deadline_flag.value):
        t0 = time.perf_counter_ns()
        sock.sendall(request)
        status, size, buf = read_response(sock, buf)
        lat.append(time.perf_counter_ns() - t0)
        wire += size
        errors += status != 200
        i += 1
    end = time.perf_counter()
    sock.close()
    return lat, wire, errors, start, end


_POOL_CTX = mp.get_context("fork")


def run_load(request, total, concurrency, tls, stop_file=None):
    """Run `total` requests (or until stop_file exists) over `concurrency`
    keep-alive connections, with the native client (one thread each)."""
    req_path = os.path.join(WORK, "request.bin")
    with open(req_path, "wb") as f:
        f.write(request)
    cmd = [LOAD]
    if tls:
        cmd.append("--tls")
    if stop_file:
        cmd += ["--until", stop_file]
    cmd += [str(RPC_PORT), str(concurrency), str(total or concurrency), req_path]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
    if out.returncode != 0:
        raise RuntimeError(f"httpload failed: {out.stderr}")
    return json.loads(out.stdout)


def run_load_python(request, total, concurrency, tls, stop_flag=None):
    """Original Python client (kept for reference; unreliable for large
    replies at high concurrency)."""
    manager = _POOL_CTX.Manager()
    barrier = manager.Barrier(concurrency)
    flag = stop_flag if stop_flag is not None else manager.Value("b", False)
    per = None if total is None else max(1, total // concurrency)
    with _POOL_CTX.Pool(concurrency) as pool:
        results = pool.map(
            worker, [(request, per, tls, barrier, flag)] * concurrency
        )
    lat = sorted(x for r in results for x in r[0])
    wire = sum(r[1] for r in results)
    errors = sum(r[2] for r in results)
    elapsed = max(r[4] for r in results) - min(r[3] for r in results)
    manager.shutdown()
    q = statistics.quantiles(lat, n=100) if len(lat) > 1 else [lat[0]] * 99
    return {
        "requests": len(lat),
        "errors": errors,
        "seconds": elapsed,
        "rps": len(lat) / elapsed,
        "p50_us": q[49] / 1000,
        "p99_us": q[98] / 1000,
        "wire_MBps": wire / elapsed / 1e6,
        "wire_bytes_per_req": wire / len(lat),
    }


# ---------------------------------------------------------------- workloads
def run_target(name, binary, tls, accept_zstd, info):
    datadir = os.path.join(WORK, f"run-{name}")
    clone_dir(TEMPLATE, datadir)
    extra = ["-tlsephemeral=1"] if binary == NEW else []
    proc = start_node(binary, datadir, RPC_PORT, P2P_PORT, extra)
    results = {}
    try:
        big = info["big_block"]
        workloads = {
            "getblockchaininfo": ({"method": "getblockchaininfo", "id": 1},
                                  SMALL_REQUESTS),
            "getblock_v2_1000tx": ({"method": "getblock", "params": [big, 2],
                                    "id": 1}, LARGE_REQUESTS),
            "batch50_getblockhash": ([{"method": "getblockhash", "params": [h],
                                       "id": h} for h in range(50)],
                                     SMALL_REQUESTS),
        }
        for wname, (body, total) in workloads.items():
            req = build_request(body, accept_zstd)
            for c in CONCURRENCY:
                r = run_load(req, total, c, tls)
                results[f"{wname}/c={c}"] = r
                print(f"  {name:<11} {wname:<21} c={c:<3} {r['rps']:>9.1f}/s "
                      f"p50 {r['p50_us']:>9.1f}us p99 {r['p99_us']:>9.1f}us "
                      f"{r['wire_MBps']:>8.2f} MB/s {r['wire_bytes_per_req']:>10.0f} B/req"
                      f" err={r['errors']}", flush=True)

        # 4: getrawmempool while a fresh node syncs from this server
        req = build_request({"method": "getrawmempool", "id": 1}, accept_zstd)
        results["getrawmempool_idle/c=16"] = run_load(req, SMALL_REQUESTS, 16, tls)
        sync_dir = os.path.join(WORK, f"sync-{name}")
        if os.path.exists(sync_dir):
            shutil.rmtree(sync_dir)
        if binary == NEW:
            peer = [f"-connect=wss://127.0.0.1:{RPC_PORT}/p2p/ws"]
            transport = "wss /p2p/ws (RPC port)"
        else:
            peer = [f"-connect=127.0.0.1:{P2P_PORT}"]
            transport = "tcp P2P port"
        stop_file = os.path.join(WORK, "sync-done")
        if os.path.exists(stop_file):
            os.remove(stop_file)
        sync_proc = start_node(NEW, sync_dir, SYNC_RPC_PORT, SYNC_P2P_PORT,
                               ["-tlsephemeral=0", *peer])
        t0 = time.time()
        pool_result = {}

        def load():
            pool_result["r"] = run_load(req, None, 16, tls, stop_file=stop_file)

        import threading
        th = threading.Thread(target=load)
        th.start()
        while rpc(SYNC_RPC_PORT, "getblockcount") < info["height"]:
            time.sleep(0.05)
        sync_seconds = time.time() - t0
        open(stop_file, "w").close()
        th.join()
        stop_node(SYNC_RPC_PORT, sync_proc)
        r = pool_result["r"]
        r["sync_seconds"] = sync_seconds
        r["sync_transport"] = transport
        results["getrawmempool_during_sync/c=16"] = r
        for k in ("getrawmempool_idle/c=16", "getrawmempool_during_sync/c=16"):
            r = results[k]
            print(f"  {name:<11} {k:<32} {r['rps']:>9.1f}/s p50 {r['p50_us']:>9.1f}us "
                  f"p99 {r['p99_us']:>9.1f}us err={r['errors']}"
                  + (f" sync {r['sync_seconds']:.2f}s via {r['sync_transport']}"
                     if "sync_seconds" in r else ""), flush=True)
    finally:
        stop_node(RPC_PORT, proc)
    return results


def main():
    os.makedirs(WORK, exist_ok=True)
    info = prepare_template()
    print(f"Chain: height {info['height']}, big block {info['big_block']} "
          f"({info['big_block_v2_bytes']:,} B verbosity-2 JSON), "
          f"mempool {info['mempool']} txs", flush=True)
    targets = [
        ("A-evhttp", BASELINE, False, False),
        ("B-beast", NEW, False, False),
        ("C-beast-tls", NEW, True, False),
        ("D-beast-zstd", NEW, False, True),
    ]
    only = sys.argv[1:]
    all_results = {"chain": info}
    for name, binary, tls, zstd in targets:
        if only and name not in only:
            continue
        print(f"Target {name} ({binary})", flush=True)
        all_results[name] = run_target(name, binary, tls, zstd, info)
        json.dump(all_results, open(os.path.join(WORK, "..", "http_ab.json"), "w"),
                  indent=2)


if __name__ == "__main__":
    main()
