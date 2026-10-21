#!/usr/bin/env python3
"""Execute frozen historical workloads with recorded compatibility and measurement adapters.

No batch splitting and no inferred acceptance: thread failures abort the run.
L1's getfeerateinfo display falls back to an unavailable marker before /029.
"""
import argparse,hashlib,json,os,sys,threading,time,traceback,random,shutil,subprocess
from pathlib import Path
from batch_sweep_extension import run_extension
random.seed(20261018)
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--series',choices=['l1','v2'],required=True);p.add_argument('--daemon',required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--source',type=Path,required=True);a=p.parse_args()
os.environ['LOTUSD_BIN']=a.daemon
os.environ['SRCDIR']=str(a.source)
script=ROOT/('harness/l1/test/functional/lotus_v2_loopback_tps_stress.py' if a.series=='l1' else 'harness/v2/lotus_v2_loopback_tps_stress.py')
sys.path.insert(0,str(script.parent if a.series=='l1' else script.parent/'test/functional'))
code=script.read_text();adaptations=[]
code=code.replace('dir="/private/tmp"', 'dir=tempfile.gettempdir()')
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
code=code.replace('results = {}','results = PersistedMetrics()')
code=code.replace('results = {"supports_large_batch": supports_large_batch, "pure_v7_transactions": True}', 'results = PersistedMetrics({"supports_large_batch": supports_large_batch, "pure_v7_transactions": True})')
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
meta={'workload_seed':20261018,'script_sha256':hashlib.sha256(script.read_bytes()).hexdigest(),'adaptations':adaptations,'adapted_script_sha256':hashlib.sha256(code.encode()).hexdigest(),'wrapper_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'extension_sha256':hashlib.sha256((ROOT/'scripts/batch_sweep_extension.py').read_bytes()).hexdigest(),'status':'running'}
mp=a.output.with_suffix('.provenance.json');mp.write_text(json.dumps(meta,indent=2))
try:
    exec(compile(code,str(script),'exec'),{'__name__':'__main__','__file__':str(script),'PersistedMetrics':Metrics,'ExtendedBatchSweep':run_extension,'CaptureFailure':capture_failure})
    meta['status']='ok'
except BaseException as ex:
    meta['status']='failed';meta['error']=repr(ex);raise
finally:
    mp.write_text(json.dumps(meta,indent=2))
    if a.output.exists():
        data=json.loads(a.output.read_text())
        a.output.write_text(json.dumps({'metrics':data,'status':meta['status'],'workload':'historical-'+a.series,'provenance':meta},indent=2))
    time.sleep(1)
