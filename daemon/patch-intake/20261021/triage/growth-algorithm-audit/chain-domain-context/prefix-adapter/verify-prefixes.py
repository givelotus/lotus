#!/usr/bin/env python3
"""Private-index tree proof; no refs/worktrees/builds/runtimes changed."""
import csv, importlib.util, json, os, pathlib, subprocess, tempfile
P=pathlib.Path(__file__).resolve().parent
S='/Users/shammah/repos/lotus-v2-chain-domain-context'
BASE='1fb7db17';END='23ff06e9fa8bd43ab77efc8a039d19c0a25142d2'
EXPECTED='3a9227011fce3a8e853ab9f8e7e7cb30108c9425'
spec=importlib.util.spec_from_file_location('adapter',P/'transform.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def git(*args,input=None,env=None):
 return subprocess.check_output(['git','-C',S,*args],input=input,env=env)
commits=git('rev-list','--reverse',BASE+'..'+END).decode().splitlines()
assert len(commits)==524
rows=[]
with tempfile.TemporaryDirectory(prefix='partition-prefix-proof-') as tmp:
 env=dict(os.environ,GIT_INDEX_FILE=tmp+'/index')
 for ordinal,sha in enumerate(commits,1):
  files={}
  for path in m.PATHS:
   x=subprocess.run(['git','-C',S,'show',sha+':'+path],capture_output=True)
   if x.returncode==0:files[path]=x.stdout
  adapted=m.transform(files)
  assert m.transform(adapted)==adapted
  git('read-tree',sha,env=env)
  changed=[]
  for path,content in adapted.items():
   if content!=files.get(path):
    blob=git('hash-object','-w','--stdin',input=content).decode().strip()
    git('update-index','--add','--cacheinfo','100644,'+blob+','+path,env=env)
    changed.append(path)
  tree=git('write-tree',env=env).decode().strip()
  oldtree=git('rev-parse',sha+'^{tree}').decode().strip()
  assert bool(changed)==(ordinal>=438)
  rows.append({'ordinal':ordinal,'original_commit':sha,'original_tree':oldtree,'adapted_tree':tree,'changed_paths':changed})
assert rows[-1]['adapted_tree']==EXPECTED
with (P/'prefix-map.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=['ordinal','original_commit','original_tree','adapted_tree','changed_paths']);w.writeheader();w.writerows(rows)
(P/'prefix-ledger.json').write_text(json.dumps(rows,indent=2)+'\n')
(P/'RESULT.json').write_text(json.dumps({'status':'PASS_ALL524_PURE_TRANSFORMS_IDEMPOTENT_EXACT_ENDPOINT','original_endpoint':END,'expected_subject_tree':EXPECTED,'actual_endpoint_tree':rows[-1]['adapted_tree'],'unchanged_before_owner':437,'transformed_prefixes':87,'causal_fixup_owner':'bf728caced8ad802fcf549f9db03a775bb266a37','metadata_policy':'Fold into original causalowner438 preserving its metadata; reconstruct later originalpurpose trees with this adapter; testtransform begins whenexistingfixturearrives439','limitations':'Source-tree proof, not all-prefix compile or protocol behavior. No maintained ref/pin/worktree mutation.'},indent=2)+'\n')
print('PASS all524prefixes;437unchanged,87transformed;exact306fendpoint '+EXPECTED)
