import subprocess,os,json,hashlib,time
from pathlib import Path
R=Path(__file__).resolve().parents[4];P=Path(__file__).resolve().parent
store=R/'daemon/.local-artifact-archive/github-source-transfer.git'; index=P/'.release-source.index'
env=dict(os.environ,GIT_INDEX_FILE=str(index),GIT_ALTERNATE_OBJECT_DIRECTORIES='/Users/shammah/repos/bitcoin-abc/.git/objects')
def repo(*a,input=None):return subprocess.check_output(['git','--git-dir='+str(store),*a],input=input,env=env)
def host(path):return subprocess.check_output(['git','-C',str(R),'show','v11.6.1:'+path])
manifest=json.loads((P/'v11.6.1-published-manifest.json').read_bytes());base=manifest['upstream_commit'];repo('read-tree',base)
series=host('daemon/patches/v1/series').decode().splitlines();rows=[];t=time.monotonic()
for name in series:
 if not name.strip() or name.startswith('#'):continue
 payload=host('daemon/patches/v1/'+name);sha=hashlib.sha256(payload).hexdigest();assert manifest['patch_sha256'][name]==sha,name
 repo('apply','--cached','--whitespace=nowarn','-',input=payload);tree=repo('write-tree').decode().strip();rows.append({'patch':name,'sha256':sha,'tree':tree})
expected=manifest['source_tree'];assert rows[-1]['tree']==expected,(rows[-1]['tree'],expected)
for filename in ['v11.6.1-maintained-aggregate.commit','v11.6.1-metadata.commit','v11.6.1-archive-snapshot.commit']:
 b=(P/filename).read_bytes();print(filename,repo('hash-object','-t','commit','-w','--stdin',input=b).decode().strip(),flush=True)
head='bb4f75b44098b47eebfe4ea9e3f0aa338b0a9c50';assert repo('rev-parse',head+'^{tree}').decode().strip()==expected
repo('update-ref','refs/audit/releases/v11.6.1-exact-metadata',head)
result={'status':'PASS_EXACT_PUBLISHED_TREE_AND_ORIGINAL_DETERMINISTIC_COMMIT','source':head,'tree':expected,'base':base,'patch_count':len(rows),'seconds':time.monotonic()-t,'store':str(store),'alternate_readonly_source':'/Users/shammah/repos/bitcoin-abc/.git/objects','source_ref':'refs/audit/releases/v11.6.1-exact-metadata','rows':rows}
(P/'v11.6.1-reconstructed.json').write_text(json.dumps(result,indent=2)+'\n');index.unlink(missing_ok=True);print('PASS',head,expected,flush=True)
