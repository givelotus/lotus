#!/usr/bin/env python3
"""Reference/cross-variant equivalence and thread-counter gate before timing."""
import json, os, pathlib, subprocess, sys
here = pathlib.Path(__file__).resolve().parent
out = pathlib.Path(sys.argv[1])
cases = [(n,d,1) for n in (64,1000,5000,100000,500000) for d in ('random','prefix')]
cases += [(n,'random',c) for n in (5000,100000) for c in (4,16)]
cap = int(os.environ.get('LOTUS_POOL_MAX',4*os.cpu_count()))
with (out/'correctness-smoke.jsonl').open('x') as f:
    for n,d,c in cases:
        roots = {}
        for v in 'ABCD':
            r = subprocess.run([str(here/'build'/f'bench_{v}'),str(n),d,str(c),'0.03'],
                               capture_output=True,text=True,timeout=45,check=True)
            j = json.loads(r.stdout)
            assert j['caller_threads']==c, j
            if v=='A': assert abs(j['threads_per_root']-(1 if n==64 else 15 if d=='random' else 3))<.001, j
            if v=='B': assert j['threads_created_before_timing']==j['threads_created_timed']==0, j
            if v=='C': assert j['threads_created_before_timing']==min(15,os.cpu_count()) and j['threads_created_timed']==0, j
            if v=='D': assert 1<=j['threads_created_before_timing']+j['threads_created_timed']<=cap, j
            j['variant']=v; f.write(json.dumps(j)+'\n'); f.flush(); roots[v]=j['root']
        assert len(set(roots.values()))==1,(n,d,c,roots)
        print('PASS reference and thread metrics',n,d,c,flush=True)
