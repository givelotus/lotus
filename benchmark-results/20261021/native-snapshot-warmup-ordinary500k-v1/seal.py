import hashlib,json,os,csv,subprocess,datetime
from pathlib import Path
R=Path(__file__).resolve().parent;points={};rows=[]
for label in ['before','after']:
 r=R/label;p=json.loads((r/'execution-plan.json').read_text());d=json.loads((r/'json_rpc_batch50_steady.json').read_text());m=d['metrics']['json_rpc_batch50_steady'];e=json.loads((r/'execution-results.json').read_text())['receipts'][0]
 assert d['status']=='ok' and e['returncode']==0 and m['tx_count']==500000 and m['post_measurement_mempool']['size']==500800 and not e['sample_windows']
 assert sum(v['accepted_count'] for v in m['per_writer'])==500000
 try:os.killpg(e['owned_group'],0);raise AssertionError('ownedgroupactive')
 except ProcessLookupError:pass
 assert hashlib.sha256(Path(p['binary']).read_bytes()).hexdigest()==p['binary_sha256']
 obs=[]
 for x in m['post_ingestion_observations']:
  assert x['nodes'][0]['mempool']['size']==500800
  obs.append({'target_seconds':x['target_seconds_after_ingestion'],'actual_start_seconds':x['actual_started_seconds_after_ingestion'],'actual_finished_seconds':x['actual_finished_seconds_after_ingestion'],'counts':[n['mempool']['size'] for n in x['nodes']],'node_rss_bytes':[v*1024 for v in x['memory']['node_rss_kib'].values()],'client_current_rss_bytes':x['memory']['benchmark_client_current_rss_kib']*1024,'client_peak_rss_bytes':x['memory']['python_peak_rss_platform_units']})
 cp=m['completion_progress'];points[label]={'source_sha':p['source_sha'],'source_tree':p['source_tree'],'binary_sha256':p['binary_sha256'],'cache_sha256':p['cmake_cache_sha256'],'accepted':500000,'warmup':800,'final_node0_inventory':500800,'seconds':m['seconds'],'observed_average_accepted_per_second':500000/m['seconds'],'first50k_seconds':cp[4]['elapsed_seconds'],'last50k_seconds':cp[-1]['elapsed_seconds']-cp[-6]['elapsed_seconds'],'peak_owned_rss_bytes':e['peak_observed_owned_rss_bytes'],'post_ingestion':obs,'load_before':e['load_before'],'load_after':e['load_after'],'process_group':e['owned_group'],'process_group_absent':True,'fixture_sha256':m['fixture_sha256']}
 pn=0;pt=0
 for x in cp:n=x['completed_transactions'];t=x['elapsed_seconds'];rows.append({'point':label,'from':pn,'to':n,'seconds':t-pt,'observed_accepted_per_second':(n-pn)/(t-pt)});pn=n;pt=t
b=points['before'];a=points['after'];gain=(b['seconds']/a['seconds']-1)*100;saving=(1-a['seconds']/b['seconds'])*100
summary={'status':'PASS_FULL_DRAIN','scope':'One unsampled finite500k source-matched snapshot-warmup pair; fullscope present and original256KiB cache both ends','points':points,'observed_rate_change_percent':gain,'elapsed_reduction_percent':saving,'not_maximum_sustainable_tps':True,'peer_txid_sets_verified':False,'no_more_runtime':True}
(R/'COMPARISON.json').write_text(json.dumps(summary,indent=2)+'\n')
with (R/'completion-chunks.csv').open('w') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
diff=subprocess.check_output(['git','-C','/Users/shammah/repos/lotus-v2-benchmark-snapshot-warm-definition','diff',b['source_sha'],a['source_sha']]);(R/'SOURCE-DELTA.json').write_text(json.dumps({'before':b['source_sha'],'after':a['source_sha'],'sha256':hashlib.sha256(diff).hexdigest(),'unified_diff':diff.decode()},indent=2)+'\n')

text=f"""# Snapshot-based native warmup: matched 500,000-transaction pair

Both runs passed and fully drained. Origin RPC acceptance took **{b['seconds']:.6f}s before → {a['seconds']:.6f}s after**: **{gain:.2f}% higher observed average acceptance rate**, or {saving:.2f}% less elapsed, in one unsampled pair.

| Metric | Before | After |
|---|---:|---:|
| Timed distinct accepted |500000|500000|
| Untimed warmup |800|800|
| Final origin inventory |500800|500800|
| Seconds |{b['seconds']:.6f}|{a['seconds']:.6f}|
| Observed accepted/s |{b['observed_average_accepted_per_second']:.2f}|{a['observed_average_accepted_per_second']:.2f}|
| First50k seconds |{b['first50k_seconds']:.3f}|{a['first50k_seconds']:.3f}|
| Last50k seconds |{b['last50k_seconds']:.3f}|{a['last50k_seconds']:.3f}|
| Peak whole-owned-group RSS GiB |{b['peak_owned_rss_bytes']/2**30:.3f}|{a['peak_owned_rss_bytes']/2**30:.3f}|

Eight persistent writers used JSON arrays of50 independent sendrawtransaction calls, native207B BIP340 transactions, fee10000 and three connected loopback nodes. Funding/signing, startup, warmup and preparation pilot were outside the clock. Fixture bytes differ between fresh funding instances; shape/count/fee and publickey42/16-reused-nonce signing distribution match. No sampling profiler was used. This is finite origin acceptance, not maximum sustainable TPS or all-peer throughput. Exact per-writer acceptance and completion chunks are retained.

## Source and validation

Before ordered definition `{b['source_sha']}` / tree `{b['source_tree']}` is byte-identical to actual compiled source `6a2782e6c7a2b3fe2fba3b14525345f0b3b1111f`; daemon SHA `{b['binary_sha256']}`. After actual source `{a['source_sha']}` / tree `{a['source_tree']}`, daemon SHA `{a['binary_sha256']}`. Candidate production matches reviewed01822776; its final test namespace repair is included. Exact source delta is in SOURCE-DELTA.json.

Both use original256KiB cache, fullscope enabled source, identical cache `{b['cache_sha256']}`, jemallocON, Chronik/pluginsOFF, walletON, Release-O3 with assertions, H2/WT OFF. The optional4KiB experiment is excluded. Actual normal builds and meaningful snapshot/native/context/TLS checks passed before launch; BINARY-READY receipts remain at the preserved binary locations named in execution plans.

The change prepares advisory native crypto from immutable snapshot coin facts instead of repeating locked PreChecks/capture. Authoritative admission still performs current checks; no staged verdict is reused. The corpus is eligible under normal published SMT context, with fallback for missing/lagging coverage. No runtime hit counter was measured, so this report assigns no observed fast-path percentage.

## Memory and peer progress

Observations are outside ingestion timing, without extra transaction/mining traffic. Natural relay continues. Actual offsets, client RSS, per-daemon RSS and resource samples remain in COMPARISON.json and execution-results.json.

| Endpoint | Target seconds | Node0 RSS GiB | Node1 RSS GiB | Node2 RSS GiB | Actual peer inventories |
|---|---:|---:|---:|---:|---|
"""
for label in ['before','after']:
 for x in points[label]['post_ingestion']:
  text+=f'| {label} | {x["target_seconds"]} | '+' | '.join(f'{v/2**30:.3f}' for v in x['node_rss_bytes'])+' | '+ '/'.join(map(str,x['counts']))+' |\n'
text+=f"""
Before already had500800 transactions on all three nodes at the first poll. After had500800/499701/499708; all three reached500800 by the next poll near5s. This is counts-only evidence: peer TxId-set equality and exact convergence time were not measured. The26.8% origin gain must not be presented as a network throughput gain.

The candidate has a material observed RSS tradeoff: group peak rose from {b['peak_owned_rss_bytes']/2**30:.3f} to {a['peak_owned_rss_bytes']/2**30:.3f}GiB; origin RSS at30s was {b['post_ingestion'][-1]['node_rss_bytes'][0]/2**30:.3f} versus {a['post_ingestion'][-1]['node_rss_bytes'][0]/2**30:.3f}GiB. Peer progress differs at ingestion end. Allocator residency/fragmentation, phase history and variation remain unresolved; these observations prove neither a leak nor a sole intrinsic retention cause. No jemalloc live/resident API was added.

Host loads before/after each case: before `{b['load_before']}` / `{b['load_after']}`; after `{a['load_before']}` / `{a['load_after']}`. No quiet-host or statistical confidence claim. Fixed before→after order, one observation each. No historical ABC run is substituted as a paired control.

Driver session35130 exited0. Owned process groups47532/49067 are absent. Both fully drained; no binaries or large fixtures are committed. Root approved adoption with this memory limitation explicit. A final depth-profile plan is separate and has not been executed.
"""
(R/'REPORT.md').write_text(text)
(R/'FULL-DRAIN.json').write_text(json.dumps({'status':'FULL_DRAIN','driver_session':35130,'returncode':0,'owned_groups':{str(points[k]['process_group']):'ABSENT' for k in points}},indent=2)+'\n')
(R/'RESULT-READY.json').write_text(json.dumps({'status':'PASS_FULL_DRAIN','report_sha256':hashlib.sha256((R/'REPORT.md').read_bytes()).hexdigest(),'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()},indent=2)+'\n')
logs={}
for f in sorted(R.rglob('*.log')):
 logs[str(f.relative_to(R))]={'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'utf8_text':f.read_text()}
(R/'RAW-RUN-LOGS.json').write_text(json.dumps(logs,indent=2)+'\n')
files=[f for f in R.rglob('*') if f.is_file() and f.suffix in {'.json','.py','.csv','.md'} and f.name!='artifact-hashes.json']
(R/'artifact-hashes.json').write_text(json.dumps({str(f.relative_to(R)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(files)},indent=2)+'\n')
print('REPORT',hashlib.sha256((R/'REPORT.md').read_bytes()).hexdigest())
