#!/usr/bin/env python3
"""Private-index tree proof; no refs/worktrees/builds/runtimes changed."""
import csv, importlib.util, json, os, pathlib, subprocess, tempfile
P=pathlib.Path(__file__).resolve().parent
S='/Users/shammah/repos/lotus-v2-transaction-partition-span'
BASE='1fb7db17';END='9f04419037a5527b498188c3a81f1cac259cc9c5'
EXPECTED='14e035afc396308ec0809e6007cdb1f331d9301f'
spec=importlib.util.spec_from_file_location('adapter',P/'transform.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def git(*args,input=None,env=None):
 return subprocess.check_output(['git','-C',S,*args],input=input,env=env)
commits=git('rev-list','--reverse',BASE+'..'+END).decode().splitlines()
assert len(commits)==523
rows=[]
with tempfile.TemporaryDirectory(prefix='partition-prefix-proof-') as tmp:
 env=dict(os.environ,GIT_INDEX_FILE=tmp+'/index')
 for ordinal,sha in enumerate(commits,1):
  files={}
  for path in [m.PRODUCTION,m.TEST]:
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
  assert bool(changed)==(ordinal>=10)
  rows.append({'ordinal':ordinal,'original_commit':sha,'original_tree':oldtree,'adapted_tree':tree,'changed_paths':changed})
assert rows[-1]['adapted_tree']==EXPECTED
with (P/'prefix-map.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=['ordinal','original_commit','original_tree','adapted_tree','changed_paths']);w.writeheader();w.writerows(rows)
(P/'prefix-ledger.json').write_text(json.dumps(rows,indent=2)+'\n')
(P/'RESULT.json').write_text(json.dumps({'status':'PASS_ALL523_PURE_TRANSFORMS_IDEMPOTENT_EXACT_ENDPOINT','original_endpoint':END,'expected_tested_tree':EXPECTED,'actual_endpoint_tree':rows[-1]['adapted_tree'],'unchanged_before_owner':9,'transformed_prefixes':514,'insert_new_purpose_after_owner':'c4d405c3f6e27b0dc83d81c46d6ef05a67fb6b8d','metadata_policy':'Do not change any original purpose metadata; insert distinct optimization after owner10, reconstruct later purpose trees with this adapter','limitations':'Source-tree proof, not all-prefix compile or protocol behavior. No maintained ref/pin/worktree mutation.'},indent=2)+'\n')
print('PASS all523prefixes;9unchanged,514transformed;exactf418endpoint '+EXPECTED)
