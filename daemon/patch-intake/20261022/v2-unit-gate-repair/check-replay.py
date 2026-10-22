from pathlib import Path
import subprocess,os,json
root=Path.cwd();repo=root/'daemon/worktrees/grok-progression-source';out=root/'daemon/patch-intake/20261022/v2-unit-gate-repair';idx=out/'replay.index';env=dict(os.environ,GIT_INDEX_FILE=str(idx))
def git(*a):return subprocess.check_output(['git','-C',str(repo),*a],env=env,stderr=subprocess.STDOUT).decode().strip()
git('read-tree','f14e7838966a651ee808e619e0c628fb5d9c90dd'); rows=[]
for i,line in enumerate((root/'daemon/patches/v2/series').read_text().splitlines(),375):
 if not line.strip() or line.startswith(('#','@')): continue
 p=root/'daemon/patches/v2'/line
 try:git('apply','--cached','--check',str(p));git('apply','--cached',str(p))
 except subprocess.CalledProcessError as e: print(i,line,e.output.decode());raise
 rows.append({'patch':line,'tree':git('write-tree')})
(out/'replay.json').write_text(json.dumps(rows,indent=2)+'\n');print(len(rows),rows[-1]);idx.unlink()
