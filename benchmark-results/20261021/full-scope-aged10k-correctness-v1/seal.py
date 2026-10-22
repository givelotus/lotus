import hashlib,json,os,re,datetime
from pathlib import Path
R=Path(__file__).resolve().parent;A=R/'attempt2';e=json.loads((A/'evidence.json').read_text());run=json.loads((A/'RESULT.json').read_text());p=json.loads((A/'execution-plan.json').read_text())
assert e['status']=='PASS_AGED_FULL_SCOPE_RECOVERY_NOT_TPS' and run['exit_code']==0
try:os.killpg(run['owned_process_group'],0);raise AssertionError('ownedgroupstillactive')
except ProcessLookupError:pass
phases={x['phase']:x for x in e['completed_sets']};final=phases['reconnect-exact-10000-all-peers'];assert final['counts']==[10000]*3 and len(set(final['sorted_txid_sha256']))==1
assert e['aging']['completed_elapsed_monotonic_seconds']>=64 and e['aging']['completed_wall_seconds_since_last_admission']>60
for node in e['capability_proof']:assert len(node['received_sendinvshort_flags'])==2 and all(v&10==10 for v in node['received_sendinvshort_flags'].values())
assert all(x['raw_body_exact_matches']==10000 for x in e['raw_body_proof']);assert len({x['sorted_txhash_sha256'] for x in e['raw_body_proof']})==1
capture=[];raw={}
for i in range(3):
 log=A/f'data/node{i}/regtest/debug.log';raw[str(log.relative_to(R))]={'bytes':log.stat().st_size,'sha256':hashlib.file_digest(log.open('rb'),'sha256').hexdigest()}
 for line in log.read_text(errors='replace').splitlines():
  m=re.search(r'captured complete mempool count=(\d+) bytes=(\d+) duration_us=(\d+)',line)
  if m:capture.append({'node':i,'count':int(m[1]),'charged_bytes':int(m[2]),'capture_copy_lock_duration_us':int(m[3]),'line':line})
(R/'CAPTURE-EVENTS.json').write_text(json.dumps(capture,indent=2)+'\n');(R/'RAW-LOG-HASHES.json').write_text(json.dumps(raw,indent=2)+'\n')
summary={'status':'PASS_FULL_DRAIN','actual_attempt':'attempt2','prior_attempt':'parentdirectory startup-only invalidschedulerflag; no protocolresult','source':p['source_sha'],'tree':p['source_tree'],'binary_sha256':p['binary_sha256'],'cache_sha256':p['cache_sha256'],'capability_flags':e['capability_proof'],'age_monotonic_seconds':e['aging']['completed_elapsed_monotonic_seconds'],'last_admission_wall_age_seconds':e['aging']['completed_wall_seconds_since_last_admission'],'final_counts':final['counts'],'final_txid_digests':final['sorted_txid_sha256'],'verified_raw_bodies_per_node':[x['raw_body_exact_matches'] for x in e['raw_body_proof']],'native_txhash_digests':[x['sorted_txhash_sha256'] for x in e['raw_body_proof']],'reconnect_seconds':final['seconds'],'wholecase_seconds':run['seconds'],'peak_owned_rss_bytes':run['peak_owned_rss_bytes'],'process_group':run['owned_process_group'],'process_group_absent':True,'coverage_event_proof':'attempt2/evidence.json full_scope_event_proof: node2 verifiedremote snapshot bodies10000 frombothpeers; exactinventoryindependentlychecked','no_performance_claim':True,'limits':['IndependentOPTRUE native transactions, no cross-prefix dependency/mixed-version/WAN/packetloss/500k coverage claim.','Functionaldebug/consistencychecking and localverification overhead; elapsed is correctness deadline evidence, not throughput.','Coverage proof is source-specificscope5Manager events plus exactIDs/rawbody equality; no rawwire-framecount/minimalbandwidth claim.','No manualP2Pfetch/BIP35/injectedbodies/proofs/Avalanche. LocalbodyRPCs onlyafterexactconvergence.']}
(R/'SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n');(R/'FULL-DRAIN.json').write_text(json.dumps({'status':'FULL_DRAIN','driver_session':39194,'exit_code':0,'owned_group':15477,'owned_group_absent':True},indent=2)+'\n')
text=f'''# Aged full-scope native recovery: PASS

The actual three-node gate **passed** on source `{p['source_sha']}` / tree `{p['source_tree']}`, preserved daemon `{p['binary_sha256']}`, samejemallocON/cache3c24 profile. All processes are drained (session39194 exit0; owned group15477 absent).

| Phase | Node0 | Node1 | Node2 |
|---|---:|---:|---:|
| Initial confirmed funding |0|0|0|
| First5000 accepted and propagated |5000|5000|5000|
| Isolatednode2,5000more submitted |10000|10000|5000|
| After64.003s real aging, still isolated |10000|10000|5000|
| Normal reconnect, exact recovery |10000|10000|10000|

Last-new-transaction source admission wall age was **{summary['last_admission_wall_age_seconds']:.3f}s** before reconnect, beyond the old30s live window. Exactall3sets converged **{final['seconds']:.3f}s** after reconnect within the predeclared180s deadline. Final sortedTxId digest is `{final['sorted_txid_sha256'][0]}` on allthree. Every localrawbody was then fetched by read-onlyRPC and byte-compared with its prepared body:10000exactmatches pernode. Existing nativeframework identities yield matching sortedTxHash digest `{summary['native_txhash_digests'][0]}`. These local reads happened after convergence and did not initiate recovery traffic.

Actual receivedsendinvshort flags are11 on both current peers of each node, containingRECONbit1 andFULL_MEMPOOLbit3. Avalanche was disabled, service/proof counters checked at snapshots, realclockaging used (`-mocktime=0`), and no manualBIP35/forcedinventory/injectedP2Pbodies/proofs were used. Receivernode2's scope-specificManager events show verified remote10000-body snapshots and admissionfinished unresolved0. Log events alone were not accepted as coverage: exactIDs and bodybytes were checked independently. No rawwirecount or minimalnetwork-transfer claim is made; duplicate remote snapshots are visible in logs.

Wholecase **{run['seconds']:.3f}s**, peak observed owned-groupRSS **{run['peak_owned_rss_bytes']/2**30:.3f}GiB**. This is a functional correctness test with debug output and repeated mempool consistency checks, **not a TPS benchmark**. Independent108B nativeOP_TRUE spends are tested; cross-prefixparent/child dependencies, mixedversions, loss/WAN,500k recovery and tipchange duringfetch are not established by this gate. The owner reports a separate focusedunit covers compatibletip-extension context.

Attempt1 (parentdirectory rawRESULT/gate.log/data stderr) stopped before daemon initialization because the derivedold scheduler test passed unsupportedtxrecontarget/margin flags. It is preserved as **harnessstartup failure, no protocolresult**. Root authorized the corrected prelaunch retry: removeonlythoseunusedflags and explicitlyenableexistingtxreconfull=1. Exactc6e205 help-debug validates all actualstartupflags. Source, binary, age/coverage/body assertions and deadlines were unchanged. ActualPASS is attempt2 only; no failed result is relabeled.

Evidence: attempt2/evidence.json; actualcommand/source/binary/config/script pins in attempt2/execution-plan.json; PGresource samples in attempt2/RESULT.json. CAPTURE-EVENTS.json retains actualcapturecount/chargedbytes/copy-lock durations, RAW-LOG-HASHES.json pins retainedrawlogs (large datadirs excluded fromGit). TxHashdigest rule is SHA256 of sortedlowercase nativeTxHashes, each followed bynewline; it is a diagnosticdigest, not a consensusroot. No further runtime was needed to seal this report.
'''
(R/'REPORT.md').write_text(text)
(R/'RESULT-READY.json').write_text(json.dumps({'status':'PASS_FULL_DRAIN','actual_attempt':'attempt2','report_sha256':hashlib.sha256((R/'REPORT.md').read_bytes()).hexdigest(),'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()},indent=2)+'\n')
print('REPORT',hashlib.sha256((R/'REPORT.md').read_bytes()).hexdigest())
