from pathlib import Path
import subprocess,os,json
root=Path.cwd();repo=root/'daemon/worktrees/grok-progression-source';out=root/'daemon/patch-intake/20261022/v2-unit-gate-repair';idx=out/'full527-replay.index';env=dict(os.environ,GIT_INDEX_FILE=str(idx))
def git(*a):return subprocess.check_output(['git','-C',str(repo),*a],env=env,stderr=subprocess.STDOUT).decode().strip()
git('read-tree','1fb7db17c176cdea8a2c60d887891589382ee4e3'); rows=[]
entries=[(series,line) for series in ['ecash','v2'] for line in (root/f'daemon/patches/{series}/series').read_text().splitlines() if line.strip() and not line.startswith(('#','@'))]
for i,(series,line) in enumerate(entries,1):
 if not line.strip() or line.startswith(('#','@')): continue
 p=root/f'daemon/patches/{series}'/line
 try:git('apply','--cached','--check',str(p));git('apply','--cached',str(p))
 except subprocess.CalledProcessError as e: print(i,line,e.output.decode());raise
 rows.append({'patch':line,'tree':git('write-tree')})
(out/'full527-replay.json').write_text(json.dumps(rows,indent=2)+'\n');print(len(rows),rows[-1]);idx.unlink()
