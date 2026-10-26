import subprocess,json,os,time,hashlib
from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[4];S=R/'daemon/worktrees/merklix-slab-source';I=R/'daemon/.local-artifact-archive/upstream-priority-mailbox.index';I.unlink(missing_ok=True);env=dict(os.environ,GIT_INDEX_FILE=str(I));m=json.loads((R/'daemon/patch-audit/progression/canonical-manifest.json').read_text());rows=m['patches'];assert len(rows)==530

def git(*a,input=None):return subprocess.check_output(['git','-C',str(S),*a],input=input,env=env)
git('read-tree',m['base']);result=[];start=time.monotonic()
for n,row in enumerate(rows,1):
 path=R/row['canonical_patch_path'];raw=path.read_bytes();assert hashlib.sha256(raw).hexdigest()==row['mailbox_sha256'];git('apply','--cached','--whitespace=nowarn','-',input=raw);tree=git('write-tree').decode().strip();assert tree==row['canonical_source_tree'],(n,path,tree,row['canonical_source_tree']);result.append({'global':n,'canonical_id':row['canonical_id'],'path':str(path.relative_to(R)),'source_commit':row['canonical_source_commit'],'tree':tree,'mailbox_sha256':row['mailbox_sha256']})
 if n%100==0:print('MAILBOX_VERIFIED',n,flush=True)
assert result[-1]['tree']=='f58bb4951d4431ab30f1b0363c7368f6969a5cb4';(P/'FULL530-MAILBOX-REPLAY.json').write_text(json.dumps({'status':'PASS_ALL530_ACTUAL_MAILBOX_INTERMEDIATE_TREES','seconds':time.monotonic()-start,'rows':result},indent=2)+'\n');I.unlink();print('ALL530_MAILBOX_PASS',flush=True)
