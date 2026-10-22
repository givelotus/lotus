#!/usr/bin/env python3
"""Validate a complete matrix and report paired bootstrap ratios (fixed seed)."""
import collections, datetime, json, pathlib, random, statistics as st, sys
out=pathlib.Path(sys.argv[1]); raw=[json.loads(l) for l in (out/'raw.jsonl').read_text().splitlines()]
groups=collections.defaultdict(dict)
for s in raw:
    key=(s['n'],s['dist'],s['callers'])
    assert (s['rep'],s['variant']) not in groups[key]
    groups[key][s['rep'],s['variant']]=s
assert len(raw)==448 and len(groups)==14
rng=random.Random(20261022)
rows=[]; structured=[]
for (n,d,c),g in groups.items():
    assert len(g)==32 and len({s['root'] for s in g.values()})==1
    for rep in range(8): assert set(v for r,v in g if r==rep)==set('ABCD')
    x={v:[g[r,v]['wall_ms_per_root'] for r in range(8)] for v in 'ABCD'}
    med={v:st.median(x[v]) for v in 'ABCD'}
    boots={p:[] for p in ('A/B','C/B','D/B','D/C','D/A')}
    for _ in range(10000):
        ix=[rng.randrange(8) for _ in range(8)]
        m={v:st.median(x[v][i] for i in ix) for v in 'ABCD'}
        for pair,b in boots.items(): a,z=pair.split('/');b.append(m[a]/m[z])
    ci={}
    for pair,b in boots.items():
        b.sort();a,z=pair.split('/');ci[pair]={'ratio':med[a]/med[z],'lower95':b[249],'upper95':b[9749]}
    def show(pair):
        q=ci[pair];return f"{q['ratio']:.3f} [{q['lower95']:.3f}, {q['upper95']:.3f}]"
    rows.append(f"| {n:,} {d} x{c} | "+' / '.join(f'{med[v]:.4f}' for v in 'ABCD')+f" | {show('A/B')} | {show('D/B')} | {show('D/C')} |")
    ds=[s for s in g.values() if s['variant']=='D']
    structured.append({'n':n,'distribution':d,'callers':c,'medians_ms':med,'ratios':ci,
       'd_retained_workers_min':min(s['threads_created_before_timing']+s['threads_created_timed'] for s in ds),
       'd_retained_workers_max':max(s['threads_created_before_timing']+s['threads_created_timed'] for s in ds),
       'd_timed_worker_growth_min':min(s['threads_created_timed'] for s in ds),
       'd_timed_worker_growth_max':max(s['threads_created_timed'] for s in ds),
       'process_wall_s_median':{v:st.median(g[r,v]['process_wall_s'] for r in range(8)) for v in 'ABCD'},
       'first_root_wall_ms_median':{v:1000*st.median(g[r,v]['first_root_wall_s'] for r in range(8)) for v in 'ABCD'}})
(out/'analysis.json').write_text(json.dumps({'bootstrap_resamples':10000,'seed':20261022,'workloads':structured},indent=2)+'\n')
header='| workload | wall ms/root A / B / C / D | A/B [95% CI] | D/B [95% CI] | D/C [95% CI] |\n|---|---|---|---|---|\n'
(out/'confidence-table.md').write_text(header+'\n'.join(rows)+'\n')
print('Validated448 samples,14workloads,8paired repetitions; wrote analysis.json and confidence-table.md')
