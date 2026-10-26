#!/usr/bin/env python3
"""Validate/report the separate E dataset; fixed-seed paired bootstrap."""
import collections, json, pathlib, random, statistics as st, sys
out=pathlib.Path(sys.argv[1]);rng=random.Random(20261022)
result={}
for kind in ('merklix','mixed'):
    raw=[json.loads(l) for l in (out/f'{kind}-raw.jsonl').read_text().splitlines()]
    assert len(raw)==(448 if kind=='merklix' else 96)
    groups=collections.defaultdict(dict)
    for s in raw:
        key=(s['n'],s['dist'],s['callers']) if kind=='merklix' else (s['rounds'],s['callers'])
        assert (s['rep'],s['variant']) not in groups[key]
        groups[key][s['rep'],s['variant']]=s
    variants='ACDE' if kind=='merklix' else 'AE'
    pairs=('E/A','E/C','E/D') if kind=='merklix' else ('E/A',)
    rows=[];data=[]
    for key,g in groups.items():
        assert len(g)==8*len(variants)
        refs={s['root'] if kind=='merklix' else tuple(s['reference']) for s in g.values()}
        assert len(refs)==1
        x={v:[g[r,v]['wall_ms_per_root'] for r in range(8)] for v in variants}
        med={v:st.median(x[v]) for v in variants};boot={pair:[] for pair in pairs}
        for _ in range(10000):
            ix=[rng.randrange(8) for _ in range(8)]
            m={v:st.median(x[v][i] for i in ix) for v in variants}
            for pair,b in boot.items():a,z=pair.split('/');b.append(m[a]/m[z])
        ci={}
        for pair,b in boot.items():
            b.sort();a,z=pair.split('/');ci[pair]={'ratio':med[a]/med[z],'lower95':b[249],'upper95':b[9749]}
        def show(pair):
            q=ci[pair];return f"{q['ratio']:.3f} [{q['lower95']:.3f}, {q['upper95']:.3f}]"
        workload=(f'{key[0]:,} {key[1]} x{key[2]}' if kind=='merklix' else f'{key[0]:,} rounds x{key[1]} clients')
        rows.append('| '+workload+' | '+' / '.join(f'{med[v]:.5f}' for v in variants)+' | '+' | '.join(show(p) for p in pairs)+' |')
        resources={}
        for v in variants:
            samples=[g[r,v] for r in range(8)]
            resources[v]={'cpu_ms_per_root_median':st.median(s['cpu_ms_per_root'] for s in samples),
              'rss_peak_bytes':max(s['maxrss_bytes'] for s in samples),'wall_cv_percent':100*st.pstdev(x[v])/st.mean(x[v]),
              'timed_threads_min':min(s['threads_created_timed'] for s in samples),'timed_threads_max':max(s['threads_created_timed'] for s in samples),
              'first_root_wall_ms_median':1000*st.median(s.get('first_root_wall_s',0) for s in samples),
              'process_wall_s_median':st.median(s['process_wall_s'] for s in samples)}
            if v=='E':
                for s in samples:
                    assert s['pool_workers']==s['pool_budget']==18 and s['threads_created_timed']==0
                    assert s['pool_active_peak']<=18 and s['pool_queue_peak']<=s['pool_queue_capacity']
                    assert s['pool_callback_depth_peak']<=64
                resources[v].update({k+'_max':max(s[k] for s in samples) for k in
                   ('pool_workers','pool_active_peak','pool_queue_peak','pool_callback_depth_peak','pool_inline_backpressure')})
                resources[v]['help_other_jobs_min']=min(s['pool_help_jobs']-s['pool_own_reclaims'] for s in samples)
                resources[v]['help_other_jobs_max']=max(s['pool_help_jobs']-s['pool_own_reclaims'] for s in samples)
                if kind=='mixed':resources[v]['min_client_roots_min']=min(s['min_client_roots'] for s in samples)
        data.append({'workload':key,'medians_ms':med,'ratios':ci,'resources':resources})
    header='| workload | wall ms/root '+' / '.join(variants)+' | '+' | '.join(p+' [95% CI]' for p in pairs)+' |\n'
    header+='|'+'---|'*(2+len(pairs))+'\n'
    (out/f'{kind}-summary.md').write_text(header+'\n'.join(rows)+'\n')
    result[kind]={'samples':len(raw),'first_ts':min(s['ts'] for s in raw),'last_ts':max(s['ts'] for s in raw),
       'sum_process_wall_s':sum(s['process_wall_s'] for s in raw),'sum_timed_wall_s':sum(s['wall_s'] for s in raw),'workloads':data}
(out/'analysis.json').write_text(json.dumps({'seed':20261022,'bootstrap_resamples':10000,**result},indent=2)+'\n')
print('PASS:544 samples,14 Merklix and6 mixed workloads; strict E18 budget, zero timed growth')
