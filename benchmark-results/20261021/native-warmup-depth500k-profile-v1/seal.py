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
 assert [n['mempool']['size'] for n in row['nodes']]==[500800]*3
 rss=row['memory']['node_rss_kib'];item={'target_seconds':row['target_seconds_after_ingestion'],'actual_started_seconds':row['actual_started_seconds_after_ingestion'],'actual_finished_seconds':row['actual_finished_seconds_after_ingestion'],'counts':[n['mempool']['size'] for n in row['nodes']],'node_rss_bytes':[v*1024 for v in rss.values()],'client_current_rss_bytes':row['memory']['benchmark_client_current_rss_kib']*1024,'client_peak_rss_bytes':row['memory']['python_peak_rss_platform_units']};memrows.append(item)
for d in [50000,250000,450000]:
 v=a[str(d)];worker=[];crypto_other=0;crypto_worker=0
 for thread,apps in v['active_application_ancestors_by_thread_NONADDITIVE'].items():
  crypto=sum(c for s,c in apps if s.startswith('lotus::v2::VerifyBip340Signature('))
  if 'rpcadmit' in thread:crypto_worker+=crypto;worker=apps;workerstate=v['threads'][thread]
  else:crypto_other+=crypto
 def cnt(token):return next((c for s,c in worker if token in s),0)
 points.append({'depth':d,'verify_bip340_worker_active_descendants':crypto_worker,'verify_bip340_other_precompute_workers_active_descendants':crypto_other,'worker_active_candidate_leaves':workerstate['active_candidate'],'worker_mutex_wait_leaves':workerstate.get('mutex_wait',0),'worker_finalize_active_descendants':cnt('MemPoolAccept::Finalize('),'worker_snapshot_active_descendants':cnt('node::PublishMempoolSnapshot('),'worker_capture_active_descendants':cnt('node::CaptureMempoolEntriesLocked('),'worker_add_unchecked_active_descendants':cnt('CTxMemPool::addUnchecked('),'worker_check_input_scripts_active_descendants':cnt('CheckInputScripts('),'precompute_mutex_wait_leaves':next((x['count'] for x in v['wait_callers'] if x['kind']=='mutex_wait' and x['caller'].startswith('PrecomputeMempoolAdmission(')),0)})
progress=m['completion_progress'];first=progress[4]['elapsed_seconds'];last=progress[-1]['elapsed_seconds']-progress[-6]['elapsed_seconds'];summary={'status':'PASS_FULL_DRAIN','source':plan['source_sha'],'tree':plan['source_tree'],'binary_sha256':plan['binary_sha256'],'profile_cache_sha256':plan['cmake_cache_sha256'],'sampled_fixed_work_seconds':m['seconds'],'accepted':500000,'warmup':800,'final_origin_inventory':500800,'first50k_seconds':first,'last50k_seconds':last,'peak_owned_group_rss_bytes':receipt['peak_observed_owned_rss_bytes'],'depth_thread_mechanisms':points,'post_ingestion_count_rss':memrows,'no_cpu_percentages':True,'no_max_tps_claim':True,'peer_exact_id_sets_verified':False,'fullscope_protocol_excluded':True}
(R/'SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n');(R/'POST-INGESTION-MEMORY.json').write_text(json.dumps(memrows,indent=2)+'\n');(R/'FULL-DRAIN.json').write_text(json.dumps({'status':'FULL_DRAIN','driver_session':70316,'returncode':0,'owned_process_group':17494,'group_absent':True},indent=2)+'\n')
text=f'''# Native warmup: depth profile and post-ingestion memory

**PASS and fully drained.** Exactcandidate source `{plan['source_sha']}` / tree `{plan['source_tree']}`, daemon `{plan['binary_sha256']}`, cache3c24jemallocON.500000 distincttimed native207B transactions accepted in **{m['seconds']:.5f}s**,800untimedwarmup, finalnode0500800. Three ownednode0 depth samples(1ms/1s) have observed lifetimes wholly inside the post-warmup GO interval. This one sampled fixed-work run is diagnostic, not a clean/max/sustainableTPS result. No new comparison pair is inferred from its elapsedtime.

## Crypto moved out of the serialized worker

| Active leaf descendants at depth |50k|250k|450k|
|---|---:|---:|---:|
'''
for label,key in [('BIP340 inrpcadmit','verify_bip340_worker_active_descendants'),('BIP340 inHTTP/precomputeworkers','verify_bip340_other_precompute_workers_active_descendants'),('rpcadmit activecandidateleaves','worker_active_candidate_leaves'),('rpcadmit Finalize','worker_finalize_active_descendants'),('rpcadmit snapshotpublication','worker_snapshot_active_descendants'),('rpcadmit changedentrycapture','worker_capture_active_descendants'),('rpcadmit addUnchecked','worker_add_unchecked_active_descendants'),('rpcadmit noncryptoCheckInputScripts','worker_check_input_scripts_active_descendants'),('Precompute mutexwaitleaves (notCPU)','precompute_mutex_wait_leaves')]:text+='| '+label+' | '+' | '.join(str(p[key]) for p in points)+' |\n'
text+='''
Counts are sampled non-idle **active candidates**, excluding recognized waiting/idle/unresolved leaves. Ancestor rows are **nonadditive** and are not CPU percentages. Every thread's exclusive leafsum equals its root tickcount. Zero sampled BIP340 onrpcadmit in these windows is evidence of the intended placement, not a measured100%cachehit guarantee or proof that verification is absent at every instant. Sourcevalidation.cpp:3237/3266 warms the ordinaryVM/cache oncopiedcoins outsidecs_main; the worker still derives/executes authoritative checks. Source/nativecache context tests remain N1's separate correctness evidence.

The next serialized costs are concrete: Finalize plus immutable publication/capture/addUnchecked under validation.cpp:1883 pool.cs/cs_main and snapshot.cpp:1235. NoncryptoVM/script work remains. No zero-allocation-under-lock claim is justified. Full details and exclusive top20 perdepth are HOTSPOTS.md/hotspot-analysis.json; thread-specific ancestors are retained for reproduction.

A second pipeline limit is visible: validation.cpp:3275 PrecomputeMempoolAdmission first acquirescs_main, calls PrepareNativeCrypto at3205 underpool.cs, which calls PreChecks with deferredscripts. Only then does it release locks forcrypto. Authoritative admission later repeats PreChecks. This produces1583/1626/1656 recognized mutex-wait leafobservations at the precompute callsite. These are wall-thread waits, not CPU cost; background/producer waits must not be summed as utilization. It is a plausible reason moving crypto yielded only a modest matchedpair gain, not a proof of causal share.

Narrow followup ideas only: capture the minimum owned primitivecoin/rulecontext needed for advisory crypto rather than repeating fullPreChecks, or reuse alreadyknown immutable primitives under an exactcontext/lifetime check. Authoritative currentcoin/rule/fee/conflict checks must still run; no staged execution verdict or unsafepointeridentity reuse is proposed. Further source gating belongs to the existing admissionowner; no broader redesign/newexperiment was started here.

## Bounded post-ingestion observation

Allthree reportedmempoolcounts are500800 at0/5/15/30s. This run recorded **counts, not peerTxId-set equality**; it is not a fullscope/WAN/recovery proof. No newtransactions/mining/manualinventory were sent during the window, but naturalrelay/reconciliation work could continue. Read-onlyRPC/ps observation overhead is outside ingestion elapsed.

| Targetoffsets | Actualstartoffsets | Node0RSSGiB | Node1RSSGiB | Node2RSSGiB | ClientcurrentRSSMiB |
|---:|---:|---:|---:|---:|---:|
'''
for row in memrows:text+=f'| {row["target_seconds"]} | {row["actual_started_seconds"]:.3f} | '+' | '.join(f'{b/2**30:.3f}' for b in row['node_rss_bytes'])+f' | {row["client_current_rss_bytes"]/2**20:.1f} |\n'
text+=f'''
Peak monitored whole-owned-groupRSS **{receipt['peak_observed_owned_rss_bytes']/2**30:.3f}GiB**. Node0RSS declines1.955→1.894GiB while allthreecounts stay500800. The prior unsampledaftercase's7.85GiB grouppeak and2.655GiB immediateoriginRSS were not reproduced here. This weakens a claim of an intrinsic/deterministic warmupretention penalty; it does **not** invalidate that earlier observation or isolate its cause. There is no pairedbaseline idlewindow, livejemallocallocated/resident RPC or stablelongterm leakmeasurement. Existing getmemoryinfo reportslocked-wallet-memory only andDarwinmallocinfo is unavailable; no daemon/API change was made to obtainallocatorstatistics.

First50k **{first:.3f}s**, last50k **{last:.3f}s**; profilers perturb adjacentchunks, marked incompletion-chunks.csv. No quadratic-complexity claim follows. Exactcommands/modulehashes/fixtures/resourceguard data remain inexecution-plan/results/provenance. Same8writers/JSONarrays50/native207B/fee10000 andstreamed500800fixture; funding/signing/startup/pilot excluded. Fullscope5fa was deliberately excluded from this82cc profile, and no newfeature's correctness/performance is inherited across those sources.

Both this runtime and the precedingfullscopegate are drained. No extraexperiments started. The earlier matchedunsampled500k pair remains the only source-matched warmupperformance comparison(26.78097→25.44687s,5.24%observedrate increase,onepair).
'''
(R/'REPORT.md').write_text(text);(R/'RESULT-READY.json').write_text(json.dumps({'status':'PASS_FULL_DRAIN','report_sha256':hashlib.sha256((R/'REPORT.md').read_bytes()).hexdigest(),'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()},indent=2)+'\n');print('REPORT',hashlib.sha256((R/'REPORT.md').read_bytes()).hexdigest())
