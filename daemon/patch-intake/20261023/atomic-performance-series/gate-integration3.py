#!/usr/bin/env python3
"""Immediately gate staged native C3 on the exact C2 shared prefix."""
import fcntl,hashlib,importlib.util,json,re,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];OUT=Path(__file__).resolve().parent;SOURCE=ROOT/'daemon/worktrees/grok-progression-source';BUILD=ROOT/'daemon/.local-artifact-archive/grok-progression-build';DATA=ROOT/'benchmark-results/20261023/atomic-through3-native-gate'
spec=importlib.util.spec_from_file_location('audit',ROOT/'daemon/bench/commit-regressions/run.py');audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
def run(cmd,log,cwd=None):
 with log.open('w') as f:subprocess.run([str(x) for x in cmd],stdout=f,stderr=subprocess.STDOUT,cwd=cwd,check=True)
def sha(p):return hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
def warn(path):
 files={'net_processing.cpp','commitment.cpp','lotus_v2_tests.cpp'}
 return {(Path(m[1]).name,m[2]) for m in re.finditer(r'([^\n]+?):\d+:\d+: warning: ([^\n]+)',path.read_text(errors='replace')) if Path(m[1]).name in files}
with (SOURCE/'.git/progression.lock').open('a') as sl,(ROOT/'daemon/.local-artifact-archive/benchmark-host.lock').open('a') as hl:
 for lock in (sl,hl):fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 state=json.loads((OUT/'COMMIT3-INTEGRATION-STATE.json').read_text());assert not DATA.exists();DATA.mkdir(parents=True)
 assert subprocess.check_output(['git','-C',str(SOURCE),'write-tree'],text=True).strip()==state['expected_tree']
 print('CONFIGURE',flush=True);run(['cmake','-GNinja','-S',SOURCE,'-B',BUILD,*audit.FLAGS],DATA/'configure.log');print('BUILD -j10',flush=True);run(['ninja','-C',BUILD,'-j10','-k0','lotusd','lotus-cli','test_bitcoin'],DATA/'build.log')
 baseline=ROOT/'benchmark-results/20261023/negotiated-relay-native-gates/point-531-build.log';before=warn(baseline);after=warn(DATA/'build.log');new=after-before;(DATA/'WARNINGS.json').write_text(json.dumps(dict(baseline=str(baseline.relative_to(ROOT)),before=sorted(before),after=sorted(after),new=sorted(new)),indent=2)+'\n');assert not new,new
 runtime=DATA/'unit-runtime';runtime.mkdir();binary=BUILD/'src/test/test_bitcoin';print('C3 TARGETED lotus_v2_tests,util_tests',flush=True);run([binary,'--run_test=lotus_v2_tests,util_tests','--log_level=test_suite','--report_level=short'],DATA/'targeted-units.log',runtime)
 print('FULL NATIVE INTEGRATION',flush=True);run([binary,'--log_level=test_suite','--report_level=short'],DATA/'all-units.log',runtime)
 assert subprocess.check_output(['git','-C',str(SOURCE),'write-tree'],text=True).strip()==state['expected_tree']
 (DATA/'PASS.json').write_text(json.dumps(dict(status='PASS',staged_tree=state['expected_tree'],base=state['base'],agent_commit=state['agent_commit'],test_binary_sha256=sha(binary),daemon_sha256=sha(BUILD/'src/lotusd'),flags=audit.FLAGS,zero_new_changed_file_warnings=True),indent=2)+'\n');print('PASS',flush=True)
