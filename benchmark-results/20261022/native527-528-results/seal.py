import csv,hashlib,json,os,datetime,statistics
from pathlib import Path
R=Path(__file__).resolve().parent
endpoints=json.loads((R/'ordinary/ENDPOINTS.json').read_text());summary={};drains=[]
for phase in ['ordinary','reads','batch','reconciliation']:
 root=R/phase;result=json.loads((root/'RESULTS.json').read_text());assert result['status']=='PASS_FULL_DRAIN'
 for item in result['cases']:
  case=Path(item['case_root']);receipts=json.loads((case/('RESULT.json' if phase=='reconciliation' else 'execution-results.json')).read_text())
  receipt=receipts if phase=='reconciliation' else receipts['receipts'][0];group=receipt.get('owned_process_group',receipt.get('owned_group'))
  try:os.killpg(group,0);raise AssertionError(('ownedgroupactive',group))
  except ProcessLookupError:pass
  drains.append({'phase':phase,'point':item['point'],'group':group,'absent':True})
 summary[phase]=result
logs=json.loads((R/'RAW-RUN-LOGS.json').read_text()) if (R/'RAW-RUN-LOGS.json').exists() else {}
for f in sorted(R.rglob('*.log')):logs[str(f.relative_to(R))]={'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'utf8_text':f.read_text(errors='replace')}
(R/'RAW-RUN-LOGS.json').write_text(json.dumps(logs,indent=2)+'\n')
recon=[]
for point in ['527','528']:
 root=R/'reconciliation'/('pair1-'+point);e=json.loads((root/'evidence.json').read_text());assert e['status']=='PASS_AGED_FULL_SCOPE_RECOVERY_NOT_TPS';assert e['completed_sets'][-1]['counts']==[10000]*3
 recon.append({'point':point,'reconnect_exact_set_seconds':e['completed_sets'][-1]['seconds'],'raw_body_proof':e['raw_body_proof'],'aging':e['aging'],'capability_proof':e['capability_proof'],'scope_events':e['full_scope_event_proof']})
(R/'RECONCILIATION.json').write_text(json.dumps(recon,indent=2)+'\n')
ordinary=json.loads((R/'ordinary/COMPARISON.json').read_text())['summary'];reads=summary['reads']['cases'];batch=summary['batch']['cases']
text=f'''# Corrected527 vs528: measured paired results

All requested core paths passed; **no active owned processes remain**. Both endpoints were rebuilt and passed full unfiltered gates before timing:5271187tests,5281200tests. The same signature-cache lifetime repair and exact-signed-transaction fixture repair are folded into both sides. Prior red-gate385b/c4 timing was never used. Canonical integration is528; evidence owner commit515550a8 supplies final frozen endpoints.

| Change/workload |527before |528after | Result / scope |
|---|---:|---:|---|
| Ordinary JSONarrays50,500k,4rotatedpairs: median origin accepts/s |{ordinary['527']['median_observed_accepted_per_second']:.1f}|{ordinary['528']['median_observed_accepted_per_second']:.1f}|Practical parity;8/8exact all-peer sets PASS|
| Same ordinary runs: median all-peer observed completion s |{ordinary['527']['median_allpeer_poll_seconds']:.3f}|{ordinary['528']['median_allpeer_poll_seconds']:.3f}|Poll upper bounds; no certified network gain|
|12loaded readers: read RPC/s during500k individual writes |{reads[0]['loaded_read']['rpc_per_second']:.2f}|{reads[1]['loaded_read']['rpc_per_second']:.2f}|Near parity; two sequential RPCs per measured read pair|
| Loaded writer500k seconds |{reads[0]['ingress_seconds']:.3f}|{reads[1]['ingress_seconds']:.3f}|Individual writes WITH12readers, not unloaded single-RPC throughput|
| Dedicated submitrawtxbatch200:500k origin seconds |{batch[0]['ingress_seconds']:.3f}|{batch[1]['ingress_seconds']:.3f}|One pair; about6.46% higher observed origin rate|
| Dedicated batch:500k all-peer completion seconds |{batch[0]['allpeer_seconds']:.3f}|{batch[1]['allpeer_seconds']:.3f}|No all-peer improvement; exact503200sets each|
| Aged full-scope recovery: reconnect→exact10k all3,seconds |{recon[0]['reconnect_exact_set_seconds']:.3f}|{recon[1]['reconnect_exact_set_seconds']:.3f}|Real64saging/noAVA; rawbody/TxHash and capability proof PASS|

The new Merklix implementation is integrated, but these endpoint observations **do not demonstrate a broad RPC or network-throughput gain**. Component gains are separate: existing three-repetition500k medians populate557.003→272.878ms; cached snapshot capture/rebuild273.759ms versus slab pin1.208us plus cached root0.166us. Cold first commitment REGRESSES17.263→24.807ms; long-lived slab snapshot release takes48.759ms. Preserve those tradeoffs; cached-root timing is not cold hashing. COMPONENT-MICROBENCH-REUSE.json proves subsequent endpoint repairs only changed signature-cache/test files, not Merklix component sources. StandaloneO2/NDEBUG component data are not daemonO3/assertions TPS.

## Meaning and limits

Eight persistent writers, native207B BIP340 transactions, fee10000, fresh confirmed funding. Ordinary batches are JSONarrays of independent sendrawtransaction requests; dedicated batch200 is a different RPC and bypasses the ordinary admission dispatcher. Unique500000 timed transactions are accepted percase;800ordinary/16individual/3200dedicated warmup transactions are excluded. Signing/funding/startup/pilot outside clock; network observer250ms adds declared overhead. Actual counts and same-endpoint all3sortedTxId digests pass independently. Fresh-funded raw fixtures differ across cases; shape/count/fees match.

All runs are one-host loopback, whitelist/highbandwidth/fullscope enabled, Avalanche disabled. Origin reply completion, all-peer mempool completion, block confirmation and Avalanche finalization are distinct. **No50k/s confirmed-block or network-wide sustained-capacity claim is established.** No actualblock confirmation stage ran here; small historical sealed-block correctness is separate. No standalone unloaded-individual500k or distributed3/3/2 injection result is inferred from loaded/single-ingress cases; those remain explicitly unmeasured in this latest matrix.

Ordinary uses initialpair plus3rotated repeats (527/528,528/527,527/528,528/527). Other paths have one observation perendpoint, not confidence-certified gains. External host work/thermal/clientJSON/GIL costs remain possible; receipts retain before/after loads and client CPU. No quiet-host/max-capacity claim. Whole-owned-group RSS/freeindicator/criticalpressure/newswap/time guards passed, no source/compiler overlap authorized. Wholecase memory includes funding/client/peer progress; do not call it live allocation or a leak test.

## Final exact endpoints

'''
for point,x in endpoints['points'].items():text+=f"{point}: source`{x['source_sha']}`, tree`{x['source_tree']}`, binary`{x['binary_sha256']}`, cache`{x['cache_sha256']}`. Actual files physically in canonical ignored artifact archive; registeredsourcepeer underdaemon/worktrees. BothjemallocOFF/walletOFF/ChronikOFF/Release-O3withassertions. These differ from older46df walletON/jemallocON datasets.\n\n"
text+='Perphase REPORT/RESULTS, inputENDPOINTS/toolhashes, exactcommands/adaptedworkload/provenance, resources/progress/fixturehashes and recovery evidence remain alongside. RAW-RUN-LOGS.json preserves exact small logs with original hashes. All owned groups are absent inFULL-DRAIN.json. No production nodes/data/release assets touched; no more runtime started by sealing.\n'
(R/'REPORT.md').write_text(text)
(R/'FULL-DRAIN.json').write_text(json.dumps({'status':'FULL_DRAIN','driver_sessions':[26157,87266,21912,4307],'groups':drains,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()},indent=2)+'\n')
(R/'RESULT-READY.json').write_text(json.dumps({'status':'ALL_REQUESTED_CORE_PHASES_PASS_FULL_DRAIN','report_sha256':hashlib.sha256((R/'REPORT.md').read_bytes()).hexdigest(),'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()},indent=2)+'\n')
files=[f for f in R.rglob('*') if f.is_file() and f.suffix in {'.py','.json','.md','.csv'} and f.name!='artifact-hashes.json' and not f.name.startswith('LIVE')]
(R/'artifact-hashes.json').write_text(json.dumps({str(f.relative_to(R)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(files)},indent=2)+'\n')
print('REPORT',hashlib.sha256((R/'REPORT.md').read_bytes()).hexdigest())
