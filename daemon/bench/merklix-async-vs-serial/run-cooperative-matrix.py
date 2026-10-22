#!/usr/bin/env python3
"""Separate E study; never modifies completed A/B/C/D data. OUTDIR [smoke]."""
import json, os, pathlib, subprocess, sys, time
here=pathlib.Path(__file__).resolve().parent
out=pathlib.Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
smoke=len(sys.argv)>2 and sys.argv[2]=='smoke'
reps=1 if smoke else 8; duration='0.05' if smoke else '1.5'
env={**os.environ,'LOTUS_POOL_MAX':'72','LOTUS_POOL_E_WORKERS':str(os.cpu_count())}
cases=[(n,d,1) for n in (64,1000,5000,100000,500000) for d in ('random','prefix')]
cases += [(n,'random',c) for n in (5000,100000) for c in (4,16)]
orders=['ACDE','EDCA','CEAD','DAEC','CDEA','EACD','DECA','ACED']
def sample(exe,args,variant,rep,order,kind):
    start=time.monotonic()
    r=subprocess.run([str(exe),*map(str,args)],env=env,capture_output=True,text=True,timeout=45)
    if r.returncode: raise RuntimeError(f'{exe} {args}: rc={r.returncode}: {r.stderr}')
    s=json.loads(r.stdout);s.update(variant=variant,rep=rep,order=order,study=kind,
        process_wall_s=time.monotonic()-start,ts=time.time(),load=os.getloadavg())
    assert s['roots']>0 and s['caller_threads']==s['callers'],s
    if variant=='E':
        assert s['threads_created_timed']==0 and s['threads_created_before_timing']==os.cpu_count(),s
        assert s['pool_workers']==s['pool_budget']==os.cpu_count(),s
        assert s['pool_active_peak']<=s['pool_budget'],s
        assert s['pool_queue_peak']<=s['pool_queue_capacity'],s
        assert s['pool_callback_depth_peak']<=64,s
        if kind=='merklix':assert s['pool_outstanding_peak']<=s['pool_outstanding_limit'],s
    elif variant=='A':
        count=7 if kind=='mixed' else (1 if s['n']==64 else 15 if s['dist']=='random' else 3)
        assert s['threads_created_timed']==count*s['roots'],s
    elif variant=='C': assert s['threads_created_timed']==0,s
    elif variant=='D': assert s['threads_created_before_timing']+s['threads_created_timed']<=72,s
    return s
for kind in ('merklix','mixed'):
    path=out/f"{kind}-{'smoke' if smoke else 'raw'}.jsonl"
    count=0
    with path.open('x') as f:
        inputs=cases if kind=='merklix' else [(rounds,callers) for rounds in (4096,16384) for callers in (3,12,24)]
        for case in inputs:
            roots=set()
            for rep in range(reps):
                order=orders[rep] if kind=='merklix' else ('AE' if rep%2==0 else 'EA')
                for variant in order:
                    if kind=='merklix':
                        n,d,c=case;exe=here/'build-e'/f'bench_{variant}';args=[n,d,c,duration]
                    else:
                        rounds,c=case;exe=here/'build-e'/'mixed_pool_bench';args=[variant,c,rounds,duration]
                    s=sample(exe,args,variant,rep,order,kind)
                    roots.add(s['root'] if kind=='merklix' else tuple(s['reference']))
                    assert len(roots)==1,(case,roots)
                    f.write(json.dumps(s)+'\n');f.flush();count+=1
                status={'stage':kind,'case':case,'repetition_completed':rep+1,'samples_completed_in_stage':count,
                        'stage_samples_total':len(inputs)*reps*(4 if kind=='merklix' else 2),
                        'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
                (out/'STATUS.json').write_text(json.dumps(status,indent=2)+'\n')
                print(json.dumps(status),flush=True)
print('COMPLETE',flush=True)
