#!/usr/bin/env python3
"""Attribute actual post-coverage admission wall time from retained daemon logs."""
import datetime,json,statistics,sys
from pathlib import Path
pending={};accepted=[];elapsed=[];checks=0;active=False
for line in Path(sys.argv[1]).open():
    if "verified remote snapshot" in line: active=True
    if not active or "[msghand]" not in line: continue
    now=datetime.datetime.fromisoformat(line.split()[0].replace("Z","+00:00")).timestamp()
    if "tx-admission-precheck txid=" in line:
        pending[line.split("txid=")[1].split()[0]]=now
    if "Checking mempool with" in line: checks+=1
    if "AcceptToMemoryPool: peer=" in line and ": accepted " in line:
        txid=line.split(": accepted ")[1].split()[0]
        accepted.append(now)
        if txid in pending: elapsed.append(now-pending.pop(txid))
assert len(accepted)>1 and len(elapsed)==len(accepted)
print(json.dumps({"source_log":sys.argv[1],"accepted":len(accepted),"full_mempool_scans":checks,
    "admission_span_seconds":accepted[-1]-accepted[0],
    "precheck_to_accepted_sum_seconds":sum(elapsed),
    "precheck_to_accepted_median_seconds":statistics.median(elapsed),
    "max_interaccepted_gap_seconds":max(b-a for a,b in zip(accepted,accepted[1:]))},indent=2))
