import subprocess,json,os,time
from pathlib import Path
P=Path(__file__).resolve().parent;S=Path('/Users/shammah/repos/lotus-v2-optimizations/daemon/worktrees/merklix-slab-source');ROOT=P.parents[3];I=ROOT/'daemon/.local-artifact-archive/shared-placement-replay.index';I.unlink(missing_ok=True);env=dict(os.environ,GIT_INDEX_FILE=str(I))
def git(*a,input=None):return subprocess.check_output(['git','-C',str(S),*a],input=input,env=env)
base='1fb7db17c176cdea8a2c60d887891589382ee4e3';tip='32573c721f1f31db5b67e8d1d7c31e2c4ec15f58';git('read-tree',base);cs=git('rev-list','--reverse',base+'..'+tip).decode().splitlines();assert len(cs)==529;rows=[];started=time.monotonic()
for n,c in enumerate(cs,1):
 diff=git('diff','--binary','--full-index',c+'^',c,'--');git('apply','--cached','--whitespace=nowarn','-',input=diff);tree=git('write-tree').decode().strip();expected=git('rev-parse',c+'^{tree}').decode().strip();assert tree==expected,(n,c,tree,expected);rows.append({'global':n,'commit':c,'tree':tree})
 if n%100==0:print('VERIFIED',n,flush=True)
assert rows[-1]['tree']=='f58bb4951d4431ab30f1b0363c7368f6969a5cb4';(P/'FULL529-REPLAY.json').write_text(json.dumps({'status':'PASS_ALL529_INTERMEDIATE_TREES','seconds':time.monotonic()-started,'tip':tip,'rows':rows},indent=2)+'\n');I.unlink();print('PASS_ALL529',flush=True)
