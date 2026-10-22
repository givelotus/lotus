#!/usr/bin/env python3
"""Execute frozen historical workloads with recorded compatibility and measurement adapters.

No batch splitting and no inferred acceptance: thread failures abort the run.
L1's getfeerateinfo display falls back to an unavailable marker before /029.
"""
import argparse,hashlib,json,os,sys,threading,time,traceback,random,shutil,subprocess
from pathlib import Path
from batch_sweep_extension import run_extension
from native_workload_adapter import adapt as adapt_native, install as install_native, amount_to_sats
from steady_suite import run_suite as run_steady_suite
from fixture_hash_acceleration import install as install_fixture_hash
random.seed(20261018)
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--series',choices=['l1','v2'],required=True);p.add_argument('--daemon',required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--source',type=Path,required=True);p.add_argument('--smoke',action='store_true');p.add_argument('--steady',action='store_true');p.add_argument('--prepare-only',action='store_true');p.add_argument('--fixture-smoke',action='store_true');p.add_argument('--case');p.add_argument('--fixture-hash-site',type=Path);p.add_argument('--budget-only',action='store_true');p.add_argument('--max-fixture-transactions',type=int,default=1200000);p.add_argument('--exact-fixture-transactions',type=int);p.add_argument('--diagnostic-fixed-work',action='store_true');p.add_argument('--sample-node0-output',type=Path);p.add_argument('--fixture-fee-sats',type=int,default=1000);p.add_argument('--hierarchical-funding',action='store_true');p.add_argument('--network-observe',action='store_true');p.add_argument('--post-ingestion-observe',action='store_true');p.add_argument('--distributed-injection',action='store_true');p.add_argument('--maxmempool-mb',type=int,default=1024);p.add_argument('--progress-chunk-transactions',type=int,default=0);p.add_argument('--minimum-predicted-supply-seconds',type=float,default=7.5);p.add_argument('--port-base',type=int,default=35110);a=p.parse_args()
if not 128 <= a.maxmempool_mb <= 4096:
    raise ValueError('Bounded diagnostic mempool cap must be128..4096MB')
os.environ['LOTUSD_BIN']=a.daemon
os.environ['SRCDIR']=str(a.source)
if a.fixture_smoke and not a.steady:
    raise ValueError('Bounded fixture smoke requires the steady bootstrap')
if a.diagnostic_fixed_work and (not a.steady or a.fixture_smoke or a.budget_only or not a.exact_fixture_transactions or a.case not in ('signed_batch200_steady', 'json_rpc_batch50_steady')):
    raise ValueError('Fixed diagnostic mode requires existing signed batch200 or array50 case with exact bounded corpus')
if a.sample_node0_output and (not a.steady or a.fixture_smoke or a.budget_only or a.case not in ('single_tx_steady', 'json_rpc_batch50_steady', 'single_tx_loaded_steady', 'signed_batch200_steady')):
    raise ValueError('CPU sample requires one steady common diagnostic case')
script=ROOT/('harness/l1/test/functional/lotus_v2_loopback_tps_stress.py' if a.series=='l1' else 'harness/v2/lotus_v2_loopback_tps_stress.py')
sys.path.insert(0,str(script.parent if a.series=='l1' else script.parent/'test/functional'))
hash_acceleration = {'enabled': False}
if a.fixture_hash_site:
    if a.series != 'v2' or not a.steady:
        raise ValueError('Fixture hash acceleration is restricted to native steady preparation')
    hash_acceleration = install_fixture_hash(a.fixture_hash_site)
code=script.read_text();adaptations=[]
code=code.replace(chr(34)+'-highbandwidthtx=1'+chr(34),chr(34)+'-highbandwidthtx=1'+chr(34)+', '+chr(34)+'-txreconfull=1'+chr(34)+', '+chr(34)+'-avalanche=0'+chr(34))
adaptations.append('Explicit current527 full-membership reconciliation enabled; Avalanche disabled; timed core unchanged')
if not 1024 <= a.port_base <= 65530:
    raise ValueError('Invalid benchmark port range')
code=code.replace('def main():', 'NODES_CFG = [{"id": i, "p2p_port": '+str(a.port_base)+' + 2*i, "rpc_port": '+str(a.port_base+1)+' + 2*i} for i in range(3)]\n\ndef main():', 1)
adaptations.append({'owned_loopback_port_base':a.port_base})
if a.series=='v2':
    code, native_details = adapt_native(code, a.source)
    adaptations.append({'native_compatibility': native_details})
code=code.replace('dir="/private/tmp"', 'dir=tempfile.gettempdir()')
if a.steady:
    if a.smoke:
        raise ValueError('Steady and compatibility-smoke modes are distinct')
    anchor = '        block_hashes = clients[0].call('
    if code.count(anchor) != 1:
        raise ValueError('Frozen pre-funding bootstrap anchor changed')
    code = code.replace(anchor, '        results = PersistedMetrics()\n        SteadySuite({**globals(), **locals()}, '+repr(a.series)+', '+str(a.max_fixture_transactions)+', '+str(a.fixture_smoke)+', '+repr(a.case)+', '+str(a.budget_only)+', '+repr(a.exact_fixture_transactions)+', '+repr(str(a.sample_node0_output) if a.sample_node0_output else None)+', '+repr(a.diagnostic_fixed_work)+', '+repr(a.minimum_predicted_supply_seconds)+', '+repr(a.progress_chunk_transactions)+', '+repr(a.hierarchical_funding)+', '+repr(a.fixture_fee_sats)+', '+repr(a.network_observe)+', '+repr(a.distributed_injection)+', '+repr(a.post_ingestion_observe)+')\n        return\n\n'+anchor, 1)
    code = code.replace('"-maxmempool=500"', '"-maxmempool='+str(a.maxmempool_mb)+'"')
    adaptations.append('steady-state-v2: frozen bootstrap/builders only; bypass every historical short burst; >=5s warmed ingestion, distinct bounded disk fixtures; maxmempool='+str(a.maxmempool_mb)+'MB')
adaptations.append('use platform temporary directory; no historical worktree dependency')
# These flags were added after the batch API; remove only when source lacks them.
for option in ['adaptiveblocksize','highbandwidthtx']:
    present=any(option in f.read_text(errors='replace') for f in (a.source/'src').glob('*.cpp'))
    if not present:
        code=code.replace(f'                "-{option}=1",\n','');adaptations.append('removed unavailable startup flag '+option)
code=code.replace('out_json = Path("/private/tmp/lotus-v2-loopback-stress-results.json")','out_json = Path('+repr(str(a.output))+')')
# Fail closed on historical worker exceptions (Python Thread.join does not propagate).
original_run=threading.Thread.run
errors=[]
def guarded_run(self):
    try:original_run(self)
    except BaseException as ex:errors.append(repr(ex));traceback.print_exc()
threading.Thread.run=guarded_run
original_join=threading.Thread.join
def checked_join(self,*args,**kwargs):
    value=original_join(self,*args,**kwargs)
    if errors:raise RuntimeError('historical worker failure: '+str(errors))
    return value
threading.Thread.join=checked_join
if a.series=='l1' and not any('getfeerateinfo' in f.read_text(errors='replace') for f in (a.source/'src/rpc').glob('*.cpp')):
    code=code.replace('feerate_info = clients[0].call("getfeerateinfo")','feerate_info = {"adaptive_max_block_size": 0, "status": "unavailable at this revision; display placeholder only"}')
    adaptations.append('getfeerateinfo unavailable: display-only placeholder, excluded from measurements')
# Persist each metric assignment so later failures do not destroy earlier measurements.
class Metrics(dict):
    def __setitem__(self,k,v):
        super().__setitem__(k,v)
        a.output.write_text(json.dumps(dict(self),indent=2))
if a.smoke:
    if a.series != 'v2':
        raise ValueError('Smoke mode is defined only for native compatibility validation')
    anchor = '        results = {"supports_large_batch": supports_large_batch, "pure_v7_transactions": True}'
    if code.count(anchor) != 1:
        raise ValueError('Frozen native smoke anchor changed')
    smoke = """        smoke_result = clients[0].call("testrawtxbatch", [[prebuilt_op_true_hex[0], prebuilt_p2pkh_hex[0]]])
        assert smoke_result["allowed"], smoke_result
        SmokeOutput.write_text(json.dumps({"native_fixture_smoke": smoke_result, "native_adapter": NativeAdapterDetails}, indent=2))
        return
"""
    code = code.replace(anchor, smoke + anchor)
    adaptations.append('SMOKE ONLY: funding plus OP_TRUE/BIP340 admission validation; no throughput measurements')
code=code.replace('results = {}','results = PersistedMetrics()')
code=code.replace('results = {"supports_large_batch": supports_large_batch, "pure_v7_transactions": True}', 'results = PersistedMetrics({"supports_large_batch": supports_large_batch, "pure_v7_transactions": True, "transaction_fixture_sha256": hashlib.sha256("".join(prebuilt_op_true_hex + prebuilt_op_true_r2_hex + prebuilt_p2pkh_hex + prebuilt_chained_v7_hex).encode()).hexdigest(), "workload_definition": {"track": "native-v7-optrue-bip340-v1", "pool_counts": [len(prebuilt_op_true_hex), len(prebuilt_op_true_r2_hex), len(prebuilt_p2pkh_hex), len(prebuilt_chained_v7_hex)], "transaction_sizes": [sorted({len(h)//2 for h in pool}) for pool in [prebuilt_op_true_hex, prebuilt_op_true_r2_hex, prebuilt_p2pkh_hex, prebuilt_chained_v7_hex]]}})')
code=code.replace('eff_batch_size = min(batch_size, 50) if not supports_large_batch else batch_size', 'eff_batch_size = batch_size')
code=code.replace('if not sample_out.exists():', 'if False: # Profiling is excluded from the reproducible timing workload.')
code=code.replace('        gbt_tx_count = len(full_gbt["transactions"])', '        gbt_tx_count = len(full_gbt["transactions"])\n        results["bench_d_gbt_compact"] = {"mempool_tx_count": gbt_tx_count, "sample_count": len(gbt_lats_ms), "p50_ms": percentile(gbt_lats_ms,50), "p95_ms": percentile(gbt_lats_ms,95), "p99_ms": percentile(gbt_lats_ms,99), "latencies_ms": gbt_lats_ms}')
code=code.replace('        out_json = Path(', '        ExtendedBatchSweep({**globals(), **locals()}, '+repr(a.series)+')\n        out_json = Path(',1)
# Capture only owned nodes after a failure, outside every timed workload.
def capture_failure(base_dir, procs):
    if sys.exc_info()[0] is None:
        return
    destination=a.output.with_suffix('.diagnostics')
    destination.mkdir(exist_ok=True)
    for source in Path(base_dir).rglob('debug.log'):
        shutil.copy2(source,destination/('_'.join(source.relative_to(base_dir).parts)))
    for index,proc in enumerate(procs):
        if proc.poll() is None:
            try:
                subprocess.run(['/usr/bin/sample',str(proc.pid),'1','1','-file',str(destination/f'node{index}.sample.txt')],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=8)
            except (OSError,subprocess.TimeoutExpired):
                pass
code=code.replace('    finally:\n        for p in procs:', '    finally:\n        CaptureFailure(base_dir, procs)\n        for p in procs:')
adaptations.append('retain owned-node debug logs and post-failure stack samples before cleanup')
adaptations.extend(['persist full-precision D1 latency samples', 'append 6000-tx OP_TRUE sweeps for b=1,50,100,200,250,500,1000 after historical measurements', 'disable automatic batch splitting and optional CPU profiling'])
a.output.with_suffix('.adapted.py').write_text(code)
meta={'native_fixture_hash_acceleration': hash_acceleration, 'workload_seed':20261018,'script_sha256':hashlib.sha256(script.read_bytes()).hexdigest(),'adaptations':adaptations,'adapted_script_sha256':hashlib.sha256(code.encode()).hexdigest(),'wrapper_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'extension_sha256':hashlib.sha256((ROOT/'scripts/batch_sweep_extension.py').read_bytes()).hexdigest(),'native_adapter_sha256':hashlib.sha256((ROOT/'scripts/native_workload_adapter.py').read_bytes()).hexdigest(),'status':'running'}
mp=a.output.with_suffix('.provenance.json');mp.write_text(json.dumps(meta,indent=2))
meta['steady_suite_sha256']=hashlib.sha256((ROOT/'scripts/steady_suite.py').read_bytes()).hexdigest()
meta['steady_core_sha256']=hashlib.sha256((ROOT/'scripts/steady_ingestion.py').read_bytes()).hexdigest()
meta['network_observation_sha256']=hashlib.sha256((ROOT/'scripts/network_observation.py').read_bytes()).hexdigest()
if a.prepare_only:
    compile(code,str(script),'exec')
    meta['status']='prepared_only_no_processes'
    mp.write_text(json.dumps(meta,indent=2))
    raise SystemExit(0)
try:
    exec(compile(code,str(script),'exec'),{'__name__':'__main__','__file__':str(script),'PersistedMetrics':Metrics,'ExtendedBatchSweep':run_extension,'CaptureFailure':capture_failure,'NativeAmountToSats':amount_to_sats,'InstallNativeAdapter':install_native,'NativeSource':a.source,'SmokeOutput':a.output,'SteadySuite':run_steady_suite})
    meta['status']='ok'
except BaseException as ex:
    meta['status']='failed';meta['error']=repr(ex);raise
finally:
    mp.write_text(json.dumps(meta,indent=2))
    if a.output.exists():
        data=json.loads(a.output.read_text())
        definition=data.get('workload_definition', {'historical_script_sha256':meta['script_sha256'],'track':a.series})
        a.output.write_text(json.dumps({'metrics':data,'status':meta['status'],'workload':('native-compatibility-smoke' if a.smoke else ('fixture-compatibility-smoke-v2-' if a.fixture_smoke else 'budget-only-v2-' if a.budget_only else 'fixed-work-diagnostic-v2-' if a.diagnostic_fixed_work else 'steady-v2-' if a.steady else 'historical-')+a.series),'workload_id':hashlib.sha256(json.dumps(definition,sort_keys=True).encode()).hexdigest(),'workload_definition':definition,'transaction_fixture_sha256':data.get('transaction_fixture_sha256'),'provenance':meta},indent=2))
    time.sleep(1)
