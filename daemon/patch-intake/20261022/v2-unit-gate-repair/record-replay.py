from pathlib import Path
import subprocess,json,os
root=Path.cwd(); repo=root/'daemon/worktrees/grok-progression-source';out=root/'daemon/patch-intake/20261022/v2-unit-gate-repair'
def git(*a,data=None,env=None):return subprocess.check_output(['git','-C',str(repo),*a],input=data,env=env).decode().strip()
old=git('rev-parse','HEAD');base='f14e7838966a651ee808e619e0c628fb5d9c90dd';commits=git('rev-list','--max-count=153','HEAD').splitlines()[::-1];rows=json.loads((out/'replay.json').read_text());assert len(commits)==len(rows)
parent=base
for orig,row in zip(commits,rows):
 raw=git('cat-file','commit',orig);headers,message=raw.split('\n\n',1);a=next(l[7:] for l in headers.splitlines() if l.startswith('author '));c=next(l[10:] for l in headers.splitlines() if l.startswith('committer '));
 content=f"tree {row['tree']}\nparent {parent}\nauthor {a}\ncommitter {c}\n\n{message}\n".encode()
 parent=git('hash-object','-t','commit','-w','--stdin',data=content);row['original_commit']=orig;row['replay_commit']=parent
assert git('rev-parse',parent+'^{tree}')==rows[-1]['tree']
# Verify all tracked working files agree with the replay before moving HEAD.
idx=out/'verify-final.index';env=dict(os.environ,GIT_INDEX_FILE=str(idx));git('read-tree',parent,env=env)
assert not git('diff','--name-only',env=env), 'working tree differs from replay'
idx.unlink();git('update-ref','refs/backup/grok-v2-unit-gate-before-20261022',old);git('update-ref','HEAD',parent,old);git('read-tree',parent)
(out/'replay-commits.json').write_text(json.dumps(rows,indent=2)+'\n');print(old,parent,rows[-1]['tree'])
