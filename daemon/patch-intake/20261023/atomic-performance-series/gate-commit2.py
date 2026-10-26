#!/usr/bin/env python3
"""Compile and gate the single shared relay executor change before commit."""
import fcntl,hashlib,importlib.util,json,os,re,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];OUT=Path(__file__).resolve().parent;SOURCE=ROOT/'daemon/worktrees/grok-progression-source';BUILD=ROOT/'daemon/.local-artifact-archive/grok-progression-build';DATA=ROOT/'benchmark-results/20261023/atomic-commit2-shared-gate'
spec=importlib.util.spec_from_file_location('audit',ROOT/'daemon/bench/commit-regressions/run.py');audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
def run(cmd,log,cwd=None):
 with log.open('w') as f:subprocess.run([str(x) for x in cmd],stdout=f,stderr=subprocess.STDOUT,cwd=cwd,check=True)
def sha(p):return hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
def warnings(path):
 return {(Path(m[1]).name,m[2]) for m in re.finditer(r'([^\n]+?):\d+:\d+: warning: ([^\n]+)',path.read_text(errors='replace')) if 'net_processing.cpp' in m[1]}
with (SOURCE/'.git/progression.lock').open('a') as sl,(ROOT/'daemon/.local-artifact-archive/benchmark-host.lock').open('a') as hl:
 for lock in (sl,hl):fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 assert not DATA.exists();DATA.mkdir(parents=True)
 assert subprocess.check_output(['git','-C',str(SOURCE),'rev-parse','HEAD'],text=True).strip()=='cbc4e72925652e3c8676ed0b24fce22874be0dc1'
 patch=subprocess.check_output(['git','-C',str(SOURCE),'diff','--binary']);(OUT/'COMMIT2-PROTOTYPE.diff').write_bytes(patch)
 fingerprint=dict(base='cbc4e72925652e3c8676ed0b24fce22874be0dc1',patch_sha256=hashlib.sha256(patch).hexdigest(),source_file_sha256=sha(SOURCE/'src/net_processing.cpp'),flags=audit.FLAGS,claim='Thread lifecycle change only; no throughput claim before3alternatingpairs')
 (DATA/'INPUT.json').write_text(json.dumps(fingerprint,indent=2)+'\n')
 print('CONFIGURE',flush=True);run(['cmake','-GNinja','-S',SOURCE,'-B',BUILD,*audit.FLAGS],DATA/'configure.log')
 print('BUILD -j10',flush=True);run(['ninja','-C',BUILD,'-j10','-k0','bitcoind','bitcoin-cli','test_bitcoin'],DATA/'build.log')
 baseline=ROOT/'benchmark-results/20261023/negotiated-relay-shared-gates/point-378-build.log';before=warnings(baseline);after=warnings(DATA/'build.log');new=after-before
 (DATA/'WARNINGS.json').write_text(json.dumps(dict(baseline=str(baseline.relative_to(ROOT)),before=sorted(before),after=sorted(after),new=sorted(new)),indent=2)+'\n');assert not new,new
 runtime=DATA/'unit-runtime';runtime.mkdir();test=BUILD/'src/test/test_bitcoin';print('TARGETED UNITS',flush=True);run([test,'--run_test=net_tests,txrelay_tests,mempool_admission_tests,v2_protocol_handler_tests,util_tests','--log_level=test_suite','--report_level=short'],DATA/'targeted-units.log',runtime)
 print('FUNCTIONAL mempool_parallel_admission.py',flush=True)
 run([sys.executable,SOURCE/'test/functional/mempool_parallel_admission.py','--configfile='+str(BUILD/'test/config.ini'),'--tmpdir='+str(DATA/'functional-runtime'),'--cachedir='+str(ROOT/'daemon/.local-artifact-archive/atomic-functional-cache'),'--portseed=2641'],DATA/'functional.log',ROOT)
 assert sha(SOURCE/'src/net_processing.cpp')==fingerprint['source_file_sha256']
 (DATA/'PASS.json').write_text(json.dumps(dict(status='PASS',source=fingerprint,test_binary_sha256=sha(test),daemon_sha256=sha(BUILD/'src/bitcoind'),targeted='net_tests,txrelay_tests,mempool_admission_tests,v2_protocol_handler_tests,util_tests',functional='mempool_parallel_admission.py',zero_new_warnings=True),indent=2)+'\n');print('PASS',flush=True)
