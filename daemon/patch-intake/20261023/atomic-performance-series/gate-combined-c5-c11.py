#!/usr/bin/env python3
"""Exclusive, fail-closed native combined candidate gate. Retains all attempts."""
from pathlib import Path
import fcntl, hashlib, json, os, shutil, subprocess, sys, time
ROOT=Path(__file__).resolve().parents[4]
OUT=Path(__file__).resolve().parent
SRC=ROOT/'daemon/worktrees/grok-progression-source'
BUILD=ROOT/'daemon/.local-artifact-archive/grok-progression-build'
ARCHIVE=ROOT/'daemon/.local-artifact-archive/combined-c5-c11-20261023'
DATA=ROOT/'benchmark-results/20261023/native-combined-c5-c11-correctness'
EXPECTED=json.loads((OUT/'COMBINED-C5-C11-RESULT.json').read_text())
FLAGS=json.loads((OUT/'C11-PAIRED-AFTER-BUILD.json').read_text())['flags']
def sha(p):
 with p.open('rb') as s:return hashlib.file_digest(s,'sha256').hexdigest()
def git(*args):return subprocess.check_output(['git','-C',str(SRC),*args],text=True).strip()
def save(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
env=os.environ.copy(); env.update(SCCACHE_DIR=str(ROOT/'daemon/.local-artifact-archive/c4-prefix-compiler-cache'),SCCACHE_SERVER_PORT='43107',SCCACHE_CACHE_SIZE='4G')
results=[]
def run(label,cmd,cwd=SRC,custom_env=env):
 start=time.monotonic();save(DATA/(label+'-command.json'),{'argv':list(map(str,cmd)),'cwd':str(cwd)})
 print('START',label,flush=True)
 with (DATA/(label+'.log')).open('w') as f:
  proc=subprocess.run(list(map(str,cmd)),cwd=cwd,env=custom_env,stdout=f,stderr=subprocess.STDOUT)
 result={'stage':label,'exit':proc.returncode,'seconds':time.monotonic()-start};results.append(result);save(DATA/'RESULTS.json',results)
 print(json.dumps(result),flush=True)
 if proc.returncode:raise RuntimeError('Failed '+label+'; original log retained')
with (SRC/'.git/progression.lock').open('a') as sl,(ROOT/'daemon/.local-artifact-archive/benchmark-host.lock').open('a') as hl:
 for lock in (sl,hl):fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 assert not DATA.exists(),'Preserve earlier attempt; do not overwrite'
 assert git('rev-parse','HEAD')==EXPECTED['head']
 assert git('rev-parse','HEAD^{tree}')==EXPECTED['tree']
 assert not git('status','--porcelain','--untracked-files=no')
 DATA.mkdir(parents=True)
 pre=ARCHIVE/'pre-combined-build';pre.mkdir(exist_ok=False)
 preserved={}
 for name,source in [('test_bitcoin',BUILD/'src/test/test_bitcoin'),('lotusd',BUILD/'src/lotusd'),('lotus-cli',BUILD/'src/lotus-cli'),('CMakeCache.txt',BUILD/'CMakeCache.txt')]:
  if source.exists():
   target=pre/name;shutil.copy2(source,target);assert sha(source)==sha(target);preserved[name]={'source':str(source),'copy':str(target),'sha256':sha(target)}
 save(DATA/'INPUTS.json',{'head':EXPECTED['head'],'tree':EXPECTED['tree'],'flags':FLAGS,'source_sha256':EXPECTED['source_sha256'],'prior_artifacts':preserved,'note':'prior common test binary is failing diagnostic prefix32; not a passing baseline','launcher':{'path':'/opt/homebrew/bin/sccache','sha256':sha(Path('/opt/homebrew/bin/sccache'))},'pid':os.getpid()})
 success=False
 try:
  run('configure',['cmake','-GNinja','-S',SRC,'-B',BUILD,*FLAGS,'-DCMAKE_C_COMPILER_LAUNCHER=/opt/homebrew/bin/sccache','-DCMAKE_CXX_COMPILER_LAUNCHER=/opt/homebrew/bin/sccache'])
  run('build',['cmake','--build',BUILD,'--target','lotusd','lotus-cli','test_bitcoin','-j10'])
  runtime=DATA/'unit-runtime';runtime.mkdir()
  run('full-native-unit',[BUILD/'src/test/test_bitcoin','--log_level=test_suite','--report_level=short'],cwd=runtime)
  fenv=env.copy();fenv.update(BITCOIND=str(BUILD/'src/lotusd'),BITCOINCLI=str(BUILD/'src/lotus-cli'),SRCDIR=str(SRC),PYTHONPATH=str(SRC/'test/functional'))
  for i,name in enumerate(['feature_miniwallet_native','mempool_parallel_admission','rpc_atomic_tx_batch']):
   run(name,[sys.executable,SRC/'test/functional'/(name+'.py'),'--configfile='+str(BUILD/'test/config.ini'),'--tmpdir='+str(DATA/(name+'-runtime')),'--cachedir='+str(DATA/'functional-cache'),'--portseed='+str(2831+i)],custom_env=fenv)
  assert not git('status','--porcelain','--untracked-files=no')
  assert git('rev-parse','HEAD')==EXPECTED['head']
  bins={p:sha(BUILD/p) for p in ['src/lotusd','src/lotus-cli','src/test/test_bitcoin','CMakeCache.txt']}
  save(DATA/'PASS.json',{'head':EXPECTED['head'],'tree':EXPECTED['tree'],'results':results,'binary_sha256':bins,'flags':FLAGS,'status':'Build/full-unit/functionals PASS; warning comparison and performance adoption separate'})
  success=True
 finally:
  with (DATA/'cache-stats.log').open('w') as f:subprocess.run(['/opt/homebrew/bin/sccache','--show-stats'],env=env,stdout=f,stderr=subprocess.STDOUT)
  with (DATA/'cache-stop.log').open('w') as f: cache_stop=subprocess.run(['/opt/homebrew/bin/sccache','--stop-server'],env=env,stdout=f,stderr=subprocess.STDOUT)
  save(DATA/'STATE.json',{'gates_passed':success,'source_head':git('rev-parse','HEAD'),'tracked_status':git('status','--porcelain','--untracked-files=no'),'cache_stop_exit':cache_stop.returncode,'performance_measured':False})
