from pathlib import Path
import subprocess,json,datetime,hashlib
root=Path.cwd(); out=root/'daemon/patch-intake/20261022/v2-unit-gate-repair';old=root/'benchmark-results/grok-progression-20261022/attempts/patch_527/20261022T180809937617Z/unit.log'
argv=json.loads(old.open().readline())['argv']; record={'argv':argv,'source_commit':subprocess.check_output(['git','-C','daemon/worktrees/grok-progression-source','rev-parse','HEAD']).decode().strip(),'source_tree':subprocess.check_output(['git','-C','daemon/worktrees/grok-progression-source','rev-parse','HEAD^{tree}']).decode().strip(),'binary_sha256':hashlib.sha256(Path(argv[0]).read_bytes()).hexdigest(),'cmake_cache_sha256':hashlib.sha256((root/'daemon/.local-artifact-archive/grok-progression-build/CMakeCache.txt').read_bytes()).hexdigest(),'status':'RUNNING','point527':'UNMEASURED'}
(out/'gate-result.json').write_text(json.dumps(record,indent=2)+'\n')
with (out/'unit-gate.log').open('w') as f:
 f.write(json.dumps(record)+'\n');f.flush();result=subprocess.run(argv,stdout=f,stderr=subprocess.STDOUT)
record.update(status='PASS' if result.returncode==0 else 'FAIL',exit_code=result.returncode)
(out/'gate-result.json').write_text(json.dumps(record,indent=2)+'\n');print(record['status'],result.returncode)
raise SystemExit(result.returncode)
