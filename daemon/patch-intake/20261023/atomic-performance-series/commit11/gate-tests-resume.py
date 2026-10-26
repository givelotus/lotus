#!/usr/bin/env python3
import collections,fcntl,hashlib,importlib.util,json,re,subprocess,time,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5]
OUT=Path(__file__).resolve().parent
SOURCE=ROOT/'daemon/worktrees/atomic-commit3-subtree-a'
BUILD=ROOT/'daemon/.local-artifact-archive/atomic-native-verdict-reuse-build'
spec=importlib.util.spec_from_file_location('audit',ROOT/'daemon/bench/commit-regressions/run.py');audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def run(cmd,name,cwd=None):
 (OUT/(name+'-command.json')).write_text(json.dumps(list(map(str,cmd)),indent=2)+'\n')
 start=time.monotonic()
 with (OUT/(name+'.log')).open('w') as f:r=subprocess.run(list(map(str,cmd)),stdout=f,stderr=subprocess.STDOUT,cwd=cwd)
 (OUT/(name+'-result.json')).write_text(json.dumps(dict(returncode=r.returncode,seconds=time.monotonic()-start),indent=2)+'\n')
 if r.returncode:raise RuntimeError(name+' failed: '+str(r.returncode))
def warnings(path):
 files={'validation.cpp','validation.h','lotus_v2_tests.cpp'}
 return collections.Counter((Path(m[1]).name,m[2]) for m in re.finditer(r'([^\n]+?):\d+:\d+: warning: ([^\n]+)',path.read_text(errors='replace')) if Path(m[1]).name in files)
with (ROOT/'daemon/.local-artifact-archive/benchmark-host.lock').open('a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 proto=json.loads((OUT/'PROTOTYPE.json').read_text())
 assert BUILD.exists(), 'Resume uses exact preserved compiled candidate'
 for path,digest in proto['source_files'].items():assert sha(SOURCE/path)==digest,path
 print('RESUME EXACT COMPILED CANDIDATE; prior setup-filter failure preserved',flush=True)
 baseline=ROOT/'benchmark-results/20261023/atomic-through4-native-gate/build.log'
 before=warnings(baseline);after=warnings(OUT/'build.log');new=after-before
 (OUT/'WARNINGS.json').write_text(json.dumps(dict(baseline=str(baseline.relative_to(ROOT)),before=[dict(file=k[0],message=k[1],count=v) for k,v in sorted(before.items())],after=[dict(file=k[0],message=k[1],count=v) for k,v in sorted(after.items())],new=[dict(file=k[0],message=k[1],count=v) for k,v in sorted(new.items())]),indent=2)+'\n')
 assert not new,new
 runtime=OUT/'unit-runtime';runtime.mkdir(exist_ok=True)
 binary=BUILD/'src/test/test_bitcoin'
 print('NEW TESTS',flush=True)
 run([binary,'--run_test=lotus_v2_tests/v2_staged_native_*','--log_level=test_suite','--report_level=short'],'new-tests',runtime)
 print('AFFECTED SUITES',flush=True)
 run([binary,'--run_test=lotus_v2_tests,mempool_admission_tests,txvalidationcache_tests,v2_legacy_bridge_tests,v2_deferred_block_tests,native_batch_admission_tests,mempool_tests','--log_level=test_suite','--report_level=short'],'affected-tests',runtime)
 print('FUNCTIONAL NATIVE MINIWALLET',flush=True)
 run([sys.executable,SOURCE/'test/functional/feature_miniwallet_native.py','--configfile='+str(BUILD/'test/config.ini'),'--tmpdir='+str(BUILD/'native-miniwallet-runtime'),'--cachedir='+str(ROOT/'daemon/.local-artifact-archive/atomic-functional-cache'),'--portseed=2678'],'native-functional',ROOT)
 for path,digest in proto['source_files'].items():assert sha(SOURCE/path)==digest,path
 (OUT/'GATE-PASS.json').write_text(json.dumps(dict(status='PASS',prototype_sha256=proto['patch_sha256'],source_files=proto['source_files'],flags=audit.FLAGS,build_dir=str(BUILD.relative_to(ROOT)),test_binary_sha256=sha(binary),daemon_sha256=sha(BUILD/'src/lotusd'),zero_new_changed_file_warnings=True,performance_claim=None),indent=2)+'\n')
 print('PASS; HOST RELEASED',flush=True)
