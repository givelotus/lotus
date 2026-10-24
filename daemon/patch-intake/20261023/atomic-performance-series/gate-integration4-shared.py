#!/usr/bin/env python3
"""Gate single shared C4 feature plus cap-preserving ownership adapters."""
import collections,fcntl,hashlib,importlib.util,json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];OUT=Path(__file__).resolve().parent;SOURCE=ROOT/'daemon/worktrees/grok-progression-source';BUILD=ROOT/'daemon/.local-artifact-archive/grok-progression-build';DATA=ROOT/'benchmark-results/20261023/atomic-through4-shared-gate'
spec=importlib.util.spec_from_file_location('audit',ROOT/'daemon/bench/commit-regressions/run.py');audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
def run(cmd,log,cwd=None):
 with log.open('w') as f:subprocess.run([str(x) for x in cmd],stdout=f,stderr=subprocess.STDOUT,cwd=cwd,check=True)
def sha(p):return hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
def warnings(path):
 files={'net_processing.cpp','mempool.cpp','validation.cpp','parallel_range.h','util_tests.cpp'}
 return collections.Counter((Path(m[1]).name,m[2]) for m in re.finditer(r'([^\n]+?):\d+:\d+: warning: ([^\n]+)',path.read_text(errors='replace')) if Path(m[1]).name in files)
with (SOURCE/'.git/progression.lock').open('a') as sl,(ROOT/'daemon/.local-artifact-archive/benchmark-host.lock').open('a') as hl:
 for lock in (sl,hl):fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 assert not DATA.exists();DATA.mkdir(parents=True)
 tree=subprocess.check_output(['git','-C',str(SOURCE),'write-tree'],text=True).strip();patch=subprocess.check_output(['git','-C',str(SOURCE),'diff','--binary','HEAD']);(OUT/'COMMIT4-INTEGRATION-PROTOTYPE.diff').write_bytes(patch)
 print('CONFIGURE',flush=True);run(['cmake','-GNinja','-S',SOURCE,'-B',BUILD,*audit.FLAGS],DATA/'configure.log');print('BUILD -j10',flush=True);run(['ninja','-C',BUILD,'-j10','-k0','bitcoind','bitcoin-cli','test_bitcoin'],DATA/'build.log')
 baselines=list((ROOT/'benchmark-results/20261023/negotiated-relay-shared-gates').glob('point-*-build.log'));base=collections.Counter()
 for f in baselines:
  for key,n in warnings(f).items():base[key]=max(base[key],n)
 after=warnings(DATA/'build.log');new=after-base
 (DATA/'WARNINGS.json').write_text(json.dumps(dict(baselines=[str(p.relative_to(ROOT)) for p in baselines],before=[dict(file=k[0],message=k[1],count=v) for k,v in sorted(base.items())],after=[dict(file=k[0],message=k[1],count=v) for k,v in sorted(after.items())],new=[dict(file=k[0],message=k[1],count=v) for k,v in sorted(new.items())]),indent=2)+'\n');assert not new,new
 runtime=DATA/'unit-runtime';runtime.mkdir();test=BUILD/'src/test/test_bitcoin';print('TARGETED',flush=True);run([test,'--run_test=util_tests,validation_tests,mempool_admission_tests,txvalidationcache_tests,net_tests,txrelay_tests,v2_protocol_handler_tests','--log_level=test_suite','--report_level=short'],DATA/'targeted-units.log',runtime)
 print('FULL SHARED',flush=True);run([test,'--log_level=test_suite','--report_level=short'],DATA/'all-units.log',runtime)
 print('FUNCTIONAL',flush=True);run([sys.executable,SOURCE/'test/functional/mempool_parallel_admission.py','--configfile='+str(BUILD/'test/config.ini'),'--tmpdir='+str(DATA/'functional-runtime'),'--cachedir='+str(ROOT/'daemon/.local-artifact-archive/atomic-functional-cache'),'--portseed=2647'],DATA/'functional.log',ROOT)
 assert subprocess.check_output(['git','-C',str(SOURCE),'write-tree'],text=True).strip()==tree
 (DATA/'PASS.json').write_text(json.dumps(dict(status='PASS',staged_tree=tree,patch_sha256=hashlib.sha256(patch).hexdigest(),daemon_sha256=sha(BUILD/'src/bitcoind'),test_binary_sha256=sha(test),flags=audit.FLAGS,zero_new_changed_file_warnings=True),indent=2)+'\n');print('PASS',flush=True)
