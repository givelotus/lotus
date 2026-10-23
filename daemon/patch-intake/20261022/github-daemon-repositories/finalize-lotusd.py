#!/usr/bin/env python3
"""Verify daemon source publication before changing its default branch."""
import subprocess,json,time,pathlib,datetime
HERE=pathlib.Path(__file__).resolve().parent
URL='git@github.com:givelotus/lotusd.git'
MAIN='ef42f1ea59399923a57a9b813e3103c98cbcbc8d'
OLD='92a39c097559dcd73c510fc3a89405d28cfc9951'
def run(args):return subprocess.check_output(args,text=True)
def api(method,path,*args):return json.loads(run(['gh','api','--method',method,path,*args]))
desired=json.loads((HERE/'desired-lotusd-tags.json').read_text())
for attempt in range(720):
    refs={l.split()[1]:l.split()[0] for l in run(['git','ls-remote',URL]).splitlines()}
    missing={k:v for k,v in desired.items() if refs.get('refs/tags/'+k)!=v}
    if refs.get('refs/heads/main')==MAIN and not missing:break
    if attempt%12==0:print('Waiting: main=',refs.get('refs/heads/main'),'unverified tags=',len(missing),flush=True)
    time.sleep(5)
else:raise SystemExit('Publication incomplete; no default branch change')
assert refs['refs/heads/master']==OLD
v1=json.loads((HERE/'maintained-lotusv1-history.json').read_text())
store=pathlib.Path.cwd()/'daemon/.local-artifact-archive/github-source-transfer.git'
subprocess.run(['git','--git-dir='+str(store),'push',URL,'refs/publish/lotusd/lotusv1:refs/heads/lotusv1'],check=True)
assert api('GET','repos/givelotus/lotusd/git/ref/heads/lotusv1')['object']['sha']==v1['head']
# This migration created the archive at old master. Advance that archive to
# the exact latest published V1 source; original master stays preserved.
assert refs['refs/heads/archive/lotusv1'] in (OLD,desired['v11.6.1'])
if refs['refs/heads/archive/lotusv1']!=desired['v11.6.1']:
    api('PATCH','repos/givelotus/lotusd/git/refs/heads/archive/lotusv1','-f','sha='+desired['v11.6.1'],'-F','force=true')
assert api('GET','repos/givelotus/lotusd/git/ref/heads/archive/lotusv1')['object']['sha']==desired['v11.6.1']
meta=api('PATCH','repos/givelotus/lotusd','-f','default_branch=main')
assert meta['default_branch']=='main' and not meta['private']
receipt={'verified_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'repository':URL,'default_branch':'main','private':False,'main':MAIN,'main_tree':'591fb5e702dda0c70a94a7123dc1012ad6e2eace','archive/lotusv1':desired['v11.6.1'],'master':OLD,'lotusv1':v1['head'],'lotusv1_tree':v1['tree'],'lotusv1_commit_count':v1['patch_count'],'release_tags':desired,'release_assets_modified':False,'submodules_added':False}
(HERE/'lotusd-verified.json').write_text(json.dumps(receipt,indent=2)+'\n')
print('VERIFIED lotusd: main, archive, master and all '+str(len(desired))+' release tags',flush=True)
