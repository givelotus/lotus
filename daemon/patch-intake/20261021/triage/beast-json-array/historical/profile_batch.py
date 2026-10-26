#!/usr/bin/env python3
"""Profile single-connection batch RPCs on evhttp vs Beast."""
import json, os, subprocess, sys, time
sys.path.insert(0, "/private/tmp")
import bench_http_ab as b

OUT = "/private/tmp/beast-http-p2p-bench/profile-batch"
os.makedirs(OUT, exist_ok=True)
b.prepare_template()
body = [{"method": "getblockhash", "params": [h], "id": h} for h in range(50)]
req_path = os.path.join(OUT, "batch.req")
open(req_path, "wb").write(b.build_request(body, False))
small_path = os.path.join(OUT, "small.req")
open(small_path, "wb").write(b.build_request({"method": "getblockcount", "id": 1}, False))

configs = [(n, x, e) for n, x, e in [
    ("A-evhttp", b.BASELINE, []),
    ("B-beast", b.NEW, ["-tlsephemeral=0"] + sys.argv[2:]),
] if len(sys.argv) < 2 or sys.argv[1] in ("all", n)]
for name, binary, extra in configs:
    d = os.path.join(b.WORK, f"pb-{name}")
    b.clone_dir(b.TEMPLATE, d)
    proc = b.start_node(binary, d, b.RPC_PORT, b.P2P_PORT, extra)
    try:
        steps = [("batch", req_path, 40000), ("small", small_path, 80000)]
        if os.environ.get("PRELOAD"):
            big = os.path.join(OUT, "getblock.req")
            open(big, "wb").write(b.build_request(
                {"method": "getblock", "params": [b.prepare_template()["big_block"], 2],
                 "id": 1}, False))
            subprocess.run([b.LOAD, str(b.RPC_PORT), "64", "1600", big],
                           capture_output=True, timeout=900)
            print(f"{name:<9} preloaded with 1600 large getblock at c=64", flush=True)
            steps = [("batch-after", req_path, 40000), ("small-after", small_path, 80000)]
        for label, path, n in steps:
            sampler = subprocess.Popen(["sample", str(proc.pid), "5", "-file",
                                        os.path.join(OUT, f"{name}-{label}.sample.txt")],
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(0.3)
            out = subprocess.run([b.LOAD, str(b.RPC_PORT), "1", str(n), path],
                                 capture_output=True, text=True, timeout=600)
            sampler.wait()
            r = json.loads(out.stdout)
            print(f"{name:<9} {label:<6} c=1 {r['rps']:>8.0f}/s p50 {r['p50_us']:>6.1f}us "
                  f"p99 {r['p99_us']:>6.1f}us", flush=True)
    finally:
        b.stop_node(b.RPC_PORT, proc)
