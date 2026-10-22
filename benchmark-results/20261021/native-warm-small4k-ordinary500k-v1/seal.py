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
  assert [n['mempool']['size'] for n in x['nodes']]==[500800]*3
  obs.append({'target_seconds':x['target_seconds_after_ingestion'],'actual_start_seconds':x['actual_started_seconds_after_ingestion'],'actual_finished_seconds':x['actual_finished_seconds_after_ingestion'],'counts':[n['mempool']['size'] for n in x['nodes']],'node_rss_bytes':[v*1024 for v in x['memory']['node_rss_kib'].values()],'client_current_rss_bytes':x['memory']['benchmark_client_current_rss_kib']*1024,'client_peak_rss_bytes':x['memory']['python_peak_rss_platform_units']})
 cp=m['completion_progress'];points[label]={'source_sha':p['source_sha'],'source_tree':p['source_tree'],'binary_sha256':p['binary_sha256'],'cache_sha256':p['cmake_cache_sha256'],'accepted':500000,'warmup':800,'final_node0_inventory':500800,'seconds':m['seconds'],'observed_average_accepted_per_second':500000/m['seconds'],'first50k_seconds':cp[4]['elapsed_seconds'],'last50k_seconds':cp[-1]['elapsed_seconds']-cp[-6]['elapsed_seconds'],'peak_owned_rss_bytes':e['peak_observed_owned_rss_bytes'],'post_ingestion':obs,'load_before':e['load_before'],'load_after':e['load_after'],'process_group':e['owned_group'],'process_group_absent':True,'fixture_sha256':m['fixture_sha256']}
 pn=0;pt=0
 for x in cp:n=x['completed_transactions'];t=x['elapsed_seconds'];rows.append({'point':label,'from':pn,'to':n,'seconds':t-pt,'observed_accepted_per_second':(n-pn)/(t-pt)});pn=n;pt=t
b=points['before'];a=points['after'];gain=(b['seconds']/a['seconds']-1)*100;saving=(1-a['seconds']/b['seconds'])*100
summary={'status':'PASS_FULL_DRAIN','scope':'Oneunsampledfinite500k source-matched4KiB pair, fullscopeEXCLUDED bothends','points':points,'observed_rate_change_percent':gain,'elapsed_reduction_percent':saving,'not_maximum_sustainable_tps':True,'peer_txid_sets_verified':False,'no_more_runtime':True}
(R/'COMPARISON.json').write_text(json.dumps(summary,indent=2)+'\n')
with (R/'completion-chunks.csv').open('w') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
diff=subprocess.check_output(['git','-C','/Users/shammah/repos/lotus-v2-benchmark-warm-small-definition','diff',b['source_sha'],a['source_sha']]);(R/'SOURCE-DELTA.json').write_text(json.dumps({'before':b['source_sha'],'after':a['source_sha'],'sha256':hashlib.sha256(diff).hexdigest(),'unified_diff':diff.decode()},indent=2)+'\n')
text=f'''# 4KiB native warmup cache: one matched500k pair

**Both PASS and fully drained.** Originalwarmup accepted500000 transactions in **{b['seconds']:.6f}s**; the4KiB candidate took **{a['seconds']:.6f}s**. That is **{gain:.2f}% higher observed average rate / {saving:.2f}% less elapsed** in ONE unsampled pair, not a certifiedmaximum or repeatedstatistical gain.

| | Warmupbefore |4KiBafter |
|---|---:|---:|
| Timed accepted |500000|500000|
| Untimed warmup |800|800|
| Exact final origin mempool |500800|500800|
| Finitecase elapsed seconds |{b['seconds']:.6f}|{a['seconds']:.6f}|
| Observed accepted/s |{b['observed_average_accepted_per_second']:.1f}|{a['observed_average_accepted_per_second']:.1f}|
| First50k seconds |{b['first50k_seconds']:.3f}|{a['first50k_seconds']:.3f}|
| Last50k seconds |{b['last50k_seconds']:.3f}|{a['last50k_seconds']:.3f}|
| Peak whole-owned-groupRSSGiB |{b['peak_owned_rss_bytes']/2**30:.3f}|{a['peak_owned_rss_bytes']/2**30:.3f}|

Both runs used8persistentwriters, JSONarrays50 independent sendrawtransaction calls,500800 distinct207B nativeBIP340 transactions/fee10000,800warmup excluded,2048MBmempool pernode andthreeconnectedloopbacknodes. Funding/signing, connection/threadstartup and4096pilot were outsideclock. No profiler was used. The genericfixed-work adapter label/stdout mentionsCPUdiagnostic, but actualsampler arrays are empty. Timer ends on originRPCacceptance; no networkceiling or peerTxId-set equality is claimed. Count500800 was independently read on allthree at0/5/15/30s after each ingestion. Fresh-funded fixture bytes differ, but shapes/counts/fees match. The publickey42/16reusednonce fixture distribution is unchanged.

## Exactpins and gate

Before source `{b['source_sha']}` / tree `{b['source_tree']}`, daemon `{b['binary_sha256']}`. After `{a['source_sha']}` / tree `{a['source_tree']}`, daemon `{a['binary_sha256']}`. Identical CMakecache `{b['cache_sha256']}`: jemallocON, Chronik/pluginsOFF, walletON, Release-O3/assertions, H2/WT OFF. Both include the same reviewedTLS chain-domain fix andnativewarmup. The newfullscope feature is **excluded at both ends**; this is not performance evidence for the joint526tree orfullscope525. Exactsource delta is durably captured inSOURCE-DELTA.json with hash.

N1 supplied actual4KiB normal288actionsPASS81.22s and pool/coinsFlush/reallocation/32input +sixnative/TLS checksPASS before launch. Actual preserved binaries andconfig/cache hashes were checked; source definitions remained clean. Existing authoritative validation is still performed; no stagedverdict reuse is inferred by the timing result.

## Post-ingestion memory observations

No newtx/mining/forcedinventory were sent during the bounded observation window. Naturalrelay/reconciliation work maycontinue. Actualoffsets andperprocessRSS are inCOMPARISON.json; each snapshot is outsideingestionelapsed.

| Endpoint | Targetseconds | Node0RSSGiB | Node1RSSGiB | Node2RSSGiB | ClientcurrentRSSMiB | All3counts |
|---|---:|---:|---:|---:|---:|---|
'''
for label in ['before','after']:
 for x in points[label]['post_ingestion']:text+=f'| {label} | {x["target_seconds"]} | '+' | '.join(f'{v/2**30:.3f}' for v in x['node_rss_bytes'])+f' | {x["client_current_rss_bytes"]/2**20:.1f} |500800/500800/500800|\n'
text+=f'''
The memorytradeoff remains unresolved: the4KiBcase's grouppeak is higher and originRSS at30s is **{a['post_ingestion'][-1]['node_rss_bytes'][0]/2**30:.3f}GiB** versus **{b['post_ingestion'][-1]['node_rss_bytes'][0]/2**30:.3f}GiB** before. Its peers fall below thebeforecase'speerRSS by30s. This is stronger endpoint/countinformation than the earlierpeak-only comparison, but not liveallocated/residentjemallocstatistics, a long-term leaktest, or proof of a sole sourcecause. Allocatorresidency/fragmentation, phase history andsamplevariation remain confounds. The earlierwarmup7.85GiBpeak was not reproduced in itsfollowupprofile; do not extrapolate a deterministicretentionpenalty from onepeak here either. No additional experiments were run.

Hostload before/after: before `{b['load_before']}` / `{b['load_after']}`; after `{a['load_before']}` / `{a['load_after']}`. No quiet-host claim. WholePGpeaks stayed below12GiB and existinghostguards. The one valid observation perendpoint usesfixed before→after order; source/profiles differ fromolderABC/historicalruns, so none are silently substituted as paired controls.

Session33381exit0; ownedPG28832/29902 absent. N1/root/resourcecoordinator were notified fullcompiler/runtimeboundaryrelease. No binaries orlargefixtures are included incommittedreceipts. Exactcommands/modules, actual counts,postwindowoffsets andresource samples remain ineach executionplan/results/provenance; rawsmalllogs are preserved asJSON. This modestobservedgain andunresolvedmemorydifference should be reviewed together before adoption.
'''
(R/'REPORT.md').write_text(text);(R/'FULL-DRAIN.json').write_text(json.dumps({'status':'FULL_DRAIN','driver_session':33381,'returncode':0,'owned_groups':{'28832':'ABSENT','29902':'ABSENT'}},indent=2)+'\n');(R/'RESULT-READY.json').write_text(json.dumps({'status':'PASS_FULL_DRAIN','report_sha256':hashlib.sha256((R/'REPORT.md').read_bytes()).hexdigest(),'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()},indent=2)+'\n');print('REPORT',hashlib.sha256((R/'REPORT.md').read_bytes()).hexdigest())
