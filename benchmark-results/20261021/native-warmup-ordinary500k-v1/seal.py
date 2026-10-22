import csv,hashlib,json,os,subprocess,datetime
from pathlib import Path
R=Path(__file__).resolve().parent
points={};progress=[]
for d in ['before','after']:
 p=json.loads((R/d/'execution-plan.json').read_text());j=json.loads((R/d/'json_rpc_batch50_steady.json').read_text());m=j['metrics']['json_rpc_batch50_steady'];e=json.loads((R/d/'execution-results.json').read_text())['receipts'][0]
 assert j['status']=='ok' and e['returncode']==0 and m['tx_count']==500000 and m['post_measurement_mempool']['size']==500800
 assert sum(w['accepted_count'] for w in m['per_writer'])==500000 and m['warmup_fixture_count']==800 and not e.get('sample_windows')
 assert hashlib.sha256(Path(p['binary']).read_bytes()).hexdigest()==p['binary_sha256']
 assert hashlib.sha256(Path(p['binary']).with_name('CMakeCache.txt').read_bytes()).hexdigest()==p['cmake_cache_sha256']
 assert subprocess.check_output(['git','-C',p['source'],'rev-parse','HEAD'],text=True).strip()==p['source_sha']
 try:os.killpg(e['owned_group'],0);raise AssertionError('owned workload still exists')
 except ProcessLookupError:pass
 cp=m['completion_progress'];last50=cp[-1]['elapsed_seconds']-cp[-6]['elapsed_seconds'];checks=e['host_memory_checks'];swap0=checks[0]['swap_used_bytes']
 points[d]={'source_sha':p['source_sha'],'source_tree':p['source_tree'],'binary_sha256':p['binary_sha256'],'cmake_cache_sha256':p['cmake_cache_sha256'],'accepted':m['tx_count'],'warmup':800,'final_node0_inventory':m['post_measurement_mempool']['size'],'seconds':m['seconds'],'observed_average_accepted_per_second':500000/m['seconds'],'first50k_seconds':cp[4]['elapsed_seconds'],'last50k_seconds':last50,'fixture_sha256':m['fixture_sha256'],'peak_owned_rss_bytes':e['peak_observed_owned_rss_bytes'],'load_before':e['load_before'],'load_after':e['load_after'],'owned_group':e['owned_group'],'owned_group_absent':True,'min_free_indicator_bytes':min(c['free_indicator_bytes'] for c in checks),'max_pressure_level':max(c['pressure_level'] for c in checks),'max_global_swap_increase_bytes':max(c['swap_used_bytes']-swap0 for c in checks)}
 prevn=0;prevt=0
 for c in cp:
  n=c['completed_transactions'];t=c['elapsed_seconds'];progress.append({'point':d,'from':prevn,'to':n,'seconds':t-prevt,'observed_accepted_per_second':(n-prevn)/(t-prevt)});prevn=n;prevt=t
b=points['before'];a=points['after'];gain=b['seconds']/a['seconds']-1;saving=1-a['seconds']/b['seconds']
comparison={'status':'PASS_FULL_DRAIN','measurement':'one-unsampled-source-matched500k-fixed-work-pair','points':points,'observed_rate_change_percent':gain*100,'elapsed_reduction_percent':saving*100,'limits':['One observation per endpoint, fixed before/after order; not statistically certified or maximum sustainableTPS.','Same reviewedTLS chain-domain correction at both ends; source delta only native warmup production+tests.','Different fresh funded fixture bytes, same207B/fee10000/nativeBIP340 shape and500800count.','Clock covers node0 successful ordinaryRPC replies only; no all-peer exactinventory/convergence measure.','Three connected loopback nodes/defaultrelay running; no sampler.','100k plans and original9518 baseline plans were never executed; historical HOLD receipts retained.']}
(R/'COMPARISON.json').write_text(json.dumps(comparison,indent=2)+'\n')
with (R/'completion-chunks.csv').open('w') as f:w=csv.DictWriter(f,fieldnames=list(progress[0]));w.writeheader();w.writerows(progress)
source=Path(json.loads((R/'after'/'execution-plan.json').read_text())['source']);diff=subprocess.check_output(['git','-C',str(source),'diff',b['source_sha'],a['source_sha']]);(R/'warmup-only.diff').write_bytes(diff)
text=f'''# Native signature warmup: matched ordinary RPC500k

**Both cases PASS and fully drained.** With the same reviewed TLS chain-domain correction at both endpoints, the native warmup candidate accepted500,000 transactions in **{a['seconds']:.5f}s**, versus **{b['seconds']:.5f}s** before: **{saving*100:.2f}% less elapsed / {gain*100:.2f}% higher observed average rate** in this single unsampled pair.

| | Before524+TLS | After524+TLS+nativewarmup |
|---|---:|---:|
| Timed accepted |500,000|500,000|
| Untimed warmup |800|800|
| Exact final node0 mempool |500,800|500,800|
| Elapsed seconds |{b['seconds']:.6f}|{a['seconds']:.6f}|
| Observed accepted/s over finite case |{b['observed_average_accepted_per_second']:.1f}|{a['observed_average_accepted_per_second']:.1f}|
| First50k seconds |{b['first50k_seconds']:.3f}|{a['first50k_seconds']:.3f}|
| Last50k seconds |{b['last50k_seconds']:.3f}|{a['last50k_seconds']:.3f}|
| Peak monitored owned-group RSS |{b['peak_owned_rss_bytes']/2**30:.3f}GiB|{a['peak_owned_rss_bytes']/2**30:.3f}GiB|

This is a modest measured improvement, not a large recovery claim or maximum sustainableTPS result. No profiler was running. Both endpoints used eight persistent writers, JSON arrays of50 independent sendrawtransaction calls,500800 distinct prepared207-byte nativeBIP340 transactions,800 untimed warmup,10,000-sat fee, and2048MB configured mempool per node. Funding/signing, connection/thread startup and the4096-row sizing pilot were excluded. Actual clock ends on node0 RPC acceptance, not peer convergence. Unique prepared fixture consumption and exact final counts were checked; the fresh-funded fixture bytes differ but shape/count/fees are matched. Public test key42 with16 reused deterministic nonce points remains fixture provenance.

## Pins and correctness

Before source `{b['source_sha']}` / tree `{b['source_tree']}`, binary `{b['binary_sha256']}`. Its tree equals imported ordered524TLS head2446653f. After source `{a['source_sha']}` / tree `{a['source_tree']}`, binary `{a['binary_sha256']}`. Production differences are native warmup in validation.cpp/h; two test files add/adjust regression intent. Exact source delta is warmup-only.diff (SHA `{hashlib.sha256(diff).hexdigest()}`). Both share the same reviewed thread-local chain-domain fix; the unsafe mutable-global control is not measured.

Both binary hashes and exact identical CMake cache `{b['cmake_cache_sha256']}` were independently checked before/after: jemallocON, Chronik/pluginsOFF, walletON, Release-O3/assertions, H2/WT OFF. N1 gates before timing: TLS baseline normal+genesis/identity cases PASS; candidate normal115 and six context/cache/TLS cases PASS. Correctness/build receipts remain owned by N1 at adaptive-reconciliation-gate. No staged consensus-verdict reuse is inferred from this benchmark.

## Limits and resource accounting

ONE observation per endpoint, fixed before→after order, no randomization or repeated statistics. Host loads before/after: baseline `{b['load_before']}` / `{b['load_after']}`; candidate `{a['load_before']}` / `{a['load_after']}`. No quiet-host or isolated hardware maximum claim. Candidate peak monitored RSS increased by{(a['peak_owned_rss_bytes']-b['peak_owned_rss_bytes'])/2**30:.3f}GiB; these whole-group peaks are one observation and do not establish a persistent memory leak or its cause. Both stayed below12GiB owned-group cap,6GiB free-indicator floor, critical pressure4 and4GiB new global-swap bounds. Per10k timings are in completion-chunks.csv; modest last-depth slowdown remains, without evidence proving quadratic behavior.

All driver and workload processes are drained (session75521 exit0; process groups97259/97759 absent). FULL-DRAIN.json records checks. Exact commands, source/binary/module hashes, preparation and actual counts are retained in each execution-plan/results/provenance. Original100k and stale9518 plans were never run; HOLD-NOT-RUN.json is historical, superseded by this report/RESULT-READY.json. No extra case or repeat was executed.
'''
(R/'REPORT.md').write_text(text)
(R/'FULL-DRAIN.json').write_text(json.dumps({'status':'FULL_DRAIN','driver_session':75521,'returncode':0,'groups':{str(p['owned_group']):'ABSENT' for p in points.values()}},indent=2)+'\n')
(R/'RESULT-READY.json').write_text(json.dumps({'status':'PASS_FULL_DRAIN','report':'REPORT.md','report_sha256':hashlib.sha256((R/'REPORT.md').read_bytes()).hexdigest(),'supersedes_historical_hold':True,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()},indent=2)+'\n')
hashes={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in R.rglob('*') if p.is_file() and '__pycache__' not in str(p) and p.name!='artifact-hashes.json'};(R/'artifact-hashes.json').write_text(json.dumps(hashes,indent=2)+'\n')
print(json.dumps({'gain_percent':gain*100,'elapsed_reduction_percent':saving*100,'report_sha256':hashes['REPORT.md']},indent=2))
