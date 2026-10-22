import collections,csv,hashlib,json,os,datetime
from pathlib import Path
R=Path(__file__).resolve().parent;data=json.loads((R/'json_rpc_batch50_steady.json').read_text());m=data['metrics']['json_rpc_batch50_steady'];receipt=json.loads((R/'execution-results.json').read_text())['receipts'][0];plan=json.loads((R/'execution-plan.json').read_text());a=json.loads((R/'hotspot-analysis.json').read_text())
assert data['status']=='ok' and m['tx_count']==500000 and m['post_measurement_mempool']['size']==500800
assert sum(x['accepted_count'] for x in m['per_writer'])==500000
assert len(receipt['sample_windows'])==3
for w in receipt['sample_windows']:assert w['returncode']==0 and m['started_monotonic']<w['launch_monotonic']<w['exit_observed_monotonic']<m['finished_monotonic']
try:os.killpg(receipt['owned_group'],0);raise AssertionError('ownedgroupstillactive')
except ProcessLookupError:pass
points=[];memrows=[]
for row in m['post_ingestion_observations']:
 assert row['nodes'][0]['mempool']['size']==500800
 rss=row['memory']['node_rss_kib'];item={'target_seconds':row['target_seconds_after_ingestion'],'actual_started_seconds':row['actual_started_seconds_after_ingestion'],'actual_finished_seconds':row['actual_finished_seconds_after_ingestion'],'counts':[n['mempool']['size'] for n in row['nodes']],'node_rss_bytes':[v*1024 for v in rss.values()],'client_current_rss_bytes':row['memory']['benchmark_client_current_rss_kib']*1024,'client_peak_rss_bytes':row['memory']['python_peak_rss_platform_units']};memrows.append(item)
for d in [50000,250000,450000]:
 v=a[str(d)];worker=[];crypto_other=0;crypto_worker=0
 for thread,apps in v['active_application_ancestors_by_thread_NONADDITIVE'].items():
  crypto=sum(c for s,c in apps if s.startswith('lotus::v2::VerifyBip340Signature('))
  if 'rpcadmit' in thread:crypto_worker+=crypto;worker=apps;workerstate=v['threads'][thread]
  else:crypto_other+=crypto
 def cnt(token):return next((c for s,c in worker if token in s),0)
 points.append({'depth':d,'verify_bip340_worker_active_descendants':crypto_worker,'verify_bip340_other_precompute_workers_active_descendants':crypto_other,'worker_active_candidate_leaves':workerstate['active_candidate'],'worker_mutex_wait_leaves':workerstate.get('mutex_wait',0),'worker_finalize_active_descendants':cnt('MemPoolAccept::Finalize('),'worker_snapshot_active_descendants':cnt('node::PublishMempoolSnapshot('),'worker_capture_active_descendants':cnt('node::CaptureMempoolEntriesLocked('),'worker_add_unchecked_active_descendants':cnt('CTxMemPool::addUnchecked('),'worker_check_input_scripts_active_descendants':cnt('CheckInputScripts('),'precompute_mutex_wait_leaves':next((x['count'] for x in v['wait_callers'] if x['kind']=='mutex_wait' and x['caller'].startswith('PrecomputeMempoolAdmission(')),0)})
progress=m['completion_progress'];first=progress[4]['elapsed_seconds'];last=progress[-1]['elapsed_seconds']-progress[-6]['elapsed_seconds'];summary={'status':'PASS_FULL_DRAIN','source':plan['source_sha'],'tree':plan['source_tree'],'binary_sha256':plan['binary_sha256'],'profile_cache_sha256':plan['cmake_cache_sha256'],'sampled_fixed_work_seconds':m['seconds'],'accepted':500000,'warmup':800,'final_origin_inventory':500800,'first50k_seconds':first,'last50k_seconds':last,'peak_owned_group_rss_bytes':receipt['peak_observed_owned_rss_bytes'],'depth_thread_mechanisms':points,'post_ingestion_count_rss':memrows,'no_cpu_percentages':True,'no_max_tps_claim':True,'peer_exact_id_sets_verified':False,'fullscope_source_present':True}
(R/'SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n');(R/'POST-INGESTION-MEMORY.json').write_text(json.dumps(memrows,indent=2)+'\n');(R/'FULL-DRAIN.json').write_text(json.dumps({'status':'FULL_DRAIN','driver_session':68244,'returncode':0,'owned_process_group':57246,'group_absent':True},indent=2)+'\n')

text=f"""# Final527 snapshot-warmup depth profile

PASS, fully drained. One sampled diagnostic accepted500000 distinct timed native207B transactions in **{m['seconds']:.6f}s**, plus800 untimed warmup; final origin inventory500800. Exactbuilt source `{plan['source_sha']}` / tree `{plan['source_tree']}`, daemon `{plan['binary_sha256']}` is tree-equivalent to imported527 `657edc0133cac8d54c5570506dad57bf10e300b5`. Original256KiB cache, jemallocON, fullscope source; samecache3c24/config024a. Eight persistent writers/ordinaryJSONarrays50, fee10000. Funding/signing/startup/pilot excluded. Sampled elapsed is diagnostic, not a clean comparison/max sustainable TPS result.

All three1ms/1s ownednode0 samplers overlap actual ingestion, proven by retained monotonic launch/exit/GO intervals. No compiler/heavyGit overlap was authorized. Fullsymbols are losslessly preserved in RAW-PROFILES.json. HOTSPOTS.md contains top20 exclusive active-candidate leaves perdepth, nonadditive application ancestors and separate waits. Recognized waits/idle/unresolved leaves are excluded from active candidates; per-thread leafsum equals root ticks. These are sample observations, not CPU percentages.

## Serialized path evidence

| Active leaf descendants / wait observations |50k|250k|450k|
|---|---:|---:|---:|
"""
for label,key in [('BIP340 on rpcadmit','verify_bip340_worker_active_descendants'),('BIP340 on other precompute threads','verify_bip340_other_precompute_workers_active_descendants'),('rpcadmit active candidates','worker_active_candidate_leaves'),('Finalize','worker_finalize_active_descendants'),('snapshot publication','worker_snapshot_active_descendants'),('changed-entry capture','worker_capture_active_descendants'),('addUnchecked','worker_add_unchecked_active_descendants'),('noncrypto CheckInputScripts','worker_check_input_scripts_active_descendants'),('Precompute mutex waits (not CPU)','precompute_mutex_wait_leaves')]:text+='| '+label+' | '+' | '.join(str(x[key]) for x in points)+' |\n'
text+="""
The intended advisory preparation lock is no longer prominent: Precompute mutex-wait leaves are3/5/1, versus1583/1626/1656 in the older82cc profile. Different windows/source histories make this corroboration, not a numerical causal CPU-share comparison. validation.cpp:3333 now first uses PrepareNativeCryptoFromSnapshot(:3269); only fallback acquires cs_main and performs old PrepareNativeCrypto. No hit counter was collected, so no exact fast-path percentage is asserted.

The next serialized mechanisms are authoritative admission and immutable publication: validation.cpp:1280 PreChecks, :1726 Finalize; node/transaction.cpp:51 AdmitBroadcastLocked; node/snapshot.cpp:1237 PublishMempoolSnapshot asserts mempool.cs, clones shared state, updates changed entries(:177/:1248), then publishes. Persistent radix copy/remove and RCU destruction appear in actual stacks. This is changed-entry work, not evidence of a complete mempool-copy regression. Noncrypto VM/context/input checks remain authoritative. No zero-allocation-under-lock or unnecessary-consensus-check claim follows.

Worker mutex-wait leaves100/117/124 are separate from active work. Producer condition waits reflect queue completion; sampled secp leaves remain mainly on precompute threads. Required reconciliation/commitment work is retained but is not the dominant serialized worker mechanism in these three windows. The bounded next direction is source-level review of publication frequency/RCU lifetime and authoritative per-request allocation/check costs, preserving snapshot and consensus semantics; no major CoW rewrite or new runtime is proposed here.

## Post-ingestion memory and counts

| Target seconds | Actual start | Node0 GiB | Node1 GiB | Node2 GiB | Inventories |
|---|---:|---:|---:|---:|---|
"""
for x in memrows:text+=f'| {x["target_seconds"]} | {x["actual_started_seconds"]:.3f} | '+' | '.join(f'{v/2**30:.3f}' for v in x['node_rss_bytes'])+' | '+ '/'.join(map(str,x['counts']))+' |\n'
text+=f"""
Whole-owned-group peak **{receipt['peak_observed_owned_rss_bytes']/2**30:.3f}GiB**. Node0 RSS declines from{memrows[0]['node_rss_bytes'][0]/2**30:.3f} to{memrows[-1]['node_rss_bytes'][0]/2**30:.3f}GiB. Peers lag at0 and reach500800 by the next poll near5s; exact convergence time/TxId-set equality were not measured. Natural relay may continue; no extra transaction/mining traffic was introduced. RSS is not jemalloc live allocation/residency or a leak test. This lower peak does not erase the paired run's7.741GiB observation or resolve its cause.

First50k{first:.3f}s; last50k{last:.3f}s. Sample-overlapping chunks are marked in completion-chunks.csv. No quadratic or statistical claim. Source/binary/profile/tool/commands/fixtures/hostloads/resource guards remain in execution-plan/results/provenance. Driver68244 exited0; ownedPG57246 absent. All500k and exactorigin inventory checks pass. No additional runtime will follow without a concrete new failure or explicit task.
"""
(R/'REPORT.md').write_text(text)
(R/'RESULT-READY.json').write_text(json.dumps({'status':'PASS_FULL_DRAIN','report_sha256':hashlib.sha256((R/'REPORT.md').read_bytes()).hexdigest(),'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()},indent=2)+'\n')
import base64,zlib
raw={}
for f in sorted(R.glob('*.sample.txt')):raw[f.name]={'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'encoding':'zlib+base64','data':base64.b64encode(zlib.compress(f.read_bytes(),9)).decode()}
(R/'RAW-PROFILES.json').write_text(json.dumps(raw,indent=2)+'\n')
f=R/'json_rpc_batch50_steady.log';(R/'RAW-RUN-LOG.json').write_text(json.dumps({'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'utf8_text':f.read_text()},indent=2)+'\n')
files=[f for f in R.iterdir() if f.is_file() and f.suffix in {'.json','.py','.csv','.md'} and f.name!='artifact-hashes.json']
(R/'artifact-hashes.json').write_text(json.dumps({f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(files)},indent=2)+'\n')
print('REPORT',hashlib.sha256((R/'REPORT.md').read_bytes()).hexdigest());print('MECHANISMS',points)
