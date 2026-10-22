#!/usr/bin/env python3
"""Alternating A/B matrix; one process per sample. Run only in an authorized
exclusive window. Writes raw.jsonl and summary.md next to this script's results dir.
usage: run-matrix.py OUTDIR [reps=7] [min_seconds=1.5]"""
import json, os, statistics as st, subprocess, sys, time
here = os.path.dirname(os.path.abspath(__file__))
out = sys.argv[1]; reps = int(sys.argv[2]) if len(sys.argv) > 2 else 8
min_s = sys.argv[3] if len(sys.argv) > 3 else "1.5"
os.makedirs(out, exist_ok=True)
sizes = [64, 1000, 5000, 100000, 500000]
cases = [(n, d, 1) for n in sizes for d in ("random", "prefix")]
cases += [(n, "random", c) for n in (5000, 100000) for c in (4, 16)]
raw = open(os.path.join(out, "raw.jsonl"), "a")
samples = {}
for (n, d, c) in cases:
    for rep in range(reps):
        order = ["ABCD","DCBA","BDAC","CADB","BCDA","DABC","CDBA","ADCB"][rep % 8]   # rotate order each repetition
        for v in order:
            exe = os.path.join(here, "build", f"bench_{v}")
            process_start = time.monotonic()
            r = subprocess.run([exe, str(n), d, str(c), min_s], capture_output=True, text=True)
            process_wall_s = time.monotonic() - process_start
            if r.returncode: sys.exit(f"{exe} {n} {d} {c} failed rc={r.returncode}")
            j = json.loads(r.stdout); j.update(process_wall_s=process_wall_s, variant=v, rep=rep, order=order, load=os.getloadavg(), ts=time.time())
            raw.write(json.dumps(j) + "\n"); raw.flush()
            samples.setdefault((n, d, c), {}).setdefault(v, []).append(j)
def cv(x): return 100 * st.pstdev(x) / st.mean(x)
rows = ["| workload | A async ms | B serial ms | C pool ms | A/B | C/B | C/A | D/B | D/C | D pool ms | CV% A/B/C/D | cpu ms A/B/C/D | process peak rss MB A/B/C/D | threads/root A/B/C/D |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
for (n, d, c), v in samples.items():
    w = {k: [s["wall_ms_per_root"] for s in v[k]] for k in "ABCD"}
    m = {k: st.median(w[k]) for k in "ABCD"}
    cp = {k: st.median(s["cpu_ms_per_root"] for s in v[k]) for k in "ABCD"}
    rs = {k: max(s["maxrss_bytes"] for s in v[k]) / 1e6 for k in "ABCD"}
    thread_counts = '/'.join(format(st.median(s['threads_per_root'] for s in v[k]), '.2f') for k in 'ABCD')
    rows.append(f"| {n} {d} x{c} | {m['A']:.4f} | {m['B']:.4f} | {m['C']:.4f} | {m['A']/m['B']:.3f} | {m['C']/m['B']:.3f} | {m['C']/m['A']:.3f} | {m['D']/m['B']:.3f} | {m['D']/m['C']:.3f} | {m['D']:.4f} | {cv(w['A']):.1f}/{cv(w['B']):.1f}/{cv(w['C']):.1f}/{cv(w['D']):.1f} | {cp['A']:.3f}/{cp['B']:.3f}/{cp['C']:.3f}/{cp['D']:.3f} | {rs['A']:.0f}/{rs['B']:.0f}/{rs['C']:.0f}/{rs['D']:.0f} | {thread_counts} |")
open(os.path.join(out, "summary.md"), "w").write("\n".join(rows) + "\n")
print("\n".join(rows))
