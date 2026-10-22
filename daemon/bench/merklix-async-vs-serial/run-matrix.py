#!/usr/bin/env python3
"""Alternating A/B matrix; one process per sample. Run only in an authorized
exclusive window. Writes raw.jsonl and summary.md next to this script's results dir.
usage: run-matrix.py OUTDIR [reps=7] [min_seconds=1.5]"""
import json, os, statistics as st, subprocess, sys, time
here = os.path.dirname(os.path.abspath(__file__))
out = sys.argv[1]; reps = int(sys.argv[2]) if len(sys.argv) > 2 else 7
min_s = sys.argv[3] if len(sys.argv) > 3 else "1.5"
os.makedirs(out, exist_ok=True)
sizes = [64, 1000, 5000, 100000, 500000]
cases = [(n, d, 1) for n in sizes for d in ("random", "prefix")]
cases += [(n, "random", c) for n in (5000, 100000) for c in (4, 16)]
raw = open(os.path.join(out, "raw.jsonl"), "a")
samples = {}
for (n, d, c) in cases:
    for rep in range(reps):
        order = "AB" if rep % 2 == 0 else "BA"   # alternate order each repetition
        for v in order:
            exe = os.path.join(here, "build", f"bench_{v}")
            r = subprocess.run([exe, str(n), d, str(c), min_s], capture_output=True, text=True)
            if r.returncode: sys.exit(f"{exe} {n} {d} {c} failed rc={r.returncode}")
            j = json.loads(r.stdout); j.update(variant=v, rep=rep, order=order, load=os.getloadavg(), ts=time.time())
            raw.write(json.dumps(j) + "\n"); raw.flush()
            samples.setdefault((n, d, c), {}).setdefault(v, []).append(j)
def cv(x): return 100 * st.pstdev(x) / st.mean(x)
rows = ["| workload | async ms/root | serial ms/root | async/serial | CV% async/serial | cpu ms/root a/s | rss MB a/s | threads/root a |", "|---|---|---|---|---|---|---|---|"]
for (n, d, c), v in samples.items():
    a = [s["wall_ms_per_root"] for s in v["A"]]; b = [s["wall_ms_per_root"] for s in v["B"]]
    ca = st.median(s["cpu_ms_per_root"] for s in v["A"]); cb = st.median(s["cpu_ms_per_root"] for s in v["B"])
    ra = max(s["maxrss_bytes"] for s in v["A"]) / 1e6; rb = max(s["maxrss_bytes"] for s in v["B"]) / 1e6
    rows.append(f"| {n} {d} x{c} caller(s) | {st.median(a):.4f} | {st.median(b):.4f} | {st.median(a)/st.median(b):.3f} | {cv(a):.1f}/{cv(b):.1f} | {ca:.3f}/{cb:.3f} | {ra:.0f}/{rb:.0f} | {st.median(s['threads_per_root'] for s in v['A']):.1f} |")
open(os.path.join(out, "summary.md"), "w").write("\n".join(rows) + "\n")
print("\n".join(rows))
