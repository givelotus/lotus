"""Promote verified branch-first rehome; generate archival mailboxes via lotus-git."""
import importlib.util,sys,subprocess,json,hashlib,copy
from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[3];S=R/'daemon/worktrees/merklix-slab-source';A=R/'daemon/patch-audit/progression'
OLD='a2af4764d116fa37fed463af1ffd3c6fb0514f76';OLD_E='47765534500efe516e9306a6426d9c9ad9d216a4';NEW='32573c721f1f31db5b67e8d1d7c31e2c4ec15f58';E='59cf9ad39a529449eba48dc9544bcac3c0538071';BASE='1fb7db17c176cdea8a2c60d887891589382ee4e3';TREE='f58bb4951d4431ab30f1b0363c7368f6969a5cb4'
def git(*a,input=None):return subprocess.check_output(['git','-C',str(S),*a],input=input,text=True).strip()
def read(p):return json.loads(p.read_text())
def write(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
def load(name,path):
 sp=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(sp);sys.modules[name]=m;sp.loader.exec_module(m);return m
assert read(P/'FULL529-REPLAY.json')['status']=='PASS_ALL529_INTERMEDIATE_TREES'
assert read(P/'native-final1203-result.json')['exit_code']==0
assert read(P/'shared376-build-result.json')['exit_code']==0
assert all(x['exit_code']==0 for x in read(P/'shared376-focused-results.json'))
assert git('rev-parse',NEW+'^{tree}')==TREE==git('rev-parse',OLD+'^{tree}')
assert git('rev-parse','daemon/ecash')==OLD_E and git('rev-parse','daemon/v2')==OLD
assert not git('status','--porcelain')
m=read(A/'canonical-manifest.json');contracts=read(A/'contracts.json');assert len(m['patches'])==529
write(P/'pre-rehome-canonical-manifest.json',m);write(P/'pre-rehome-contracts.json',contracts)
lotus=load('lotus_git_shared_rehome',R/'daemon/scripts/lotus-git.py')
assert lotus.verify_linear_and_no_fixups(S,BASE,E)==376
assert lotus.verify_linear_and_no_fixups(S,E,NEW)==153
# Atomic compare-and-swap; original backup refs and bundle remain unchanged.
git('update-ref','--stdin',input=f'start\nupdate refs/heads/daemon/ecash {E} {OLD_E}\nupdate refs/heads/daemon/v2 {NEW} {OLD}\nprepare\ncommit\n')
git('checkout','daemon/v2')
for name,sha in [('ecash',E),('v2',NEW)]:lotus.write_head_pin_sha(lotus.SERIES_SPECS[name],sha)
# Development authority remains Git; archival payloads are exported mechanically.
lotus.export_range_to_patches_dir(ws=S,start_sha=BASE,end_sha=E,patches_dir=R/'daemon/patches/ecash')
lotus.export_range_to_patches_dir(ws=S,start_sha=E,end_sha=NEW,patches_dir=R/'daemon/patches/v2',include_directive='@include ../ecash/series')
rows=m['patches'];fee=rows.pop(523);assert fee['canonical_id']=='node-owned-asynchronous-local-fee-policy-20261021';rows.insert(375,fee)
commits=git('log','--reverse','--format=%H %T %P',BASE+'..'+NEW).splitlines();assert len(commits)==529
paths=[]
for series in ['ecash','v2']:
 names=[x for x in (R/f'daemon/patches/{series}/series').read_text().splitlines()if x and not x.startswith(('#','@'))]
 paths += [(series,n+1,x)for n,x in enumerate(names)]
for idx,(row,line,(series,num,name))in enumerate(zip(rows,commits,paths,strict=True),1):
 sha,tree,parent=line.split();path=f'daemon/patches/{series}/{name}';row.update(global_number=idx,series=series,layer=series,number=num,layer_number=num,file=name,canonical_patch_path=path,canonical_source_commit=sha,canonical_parent_commit=parent,canonical_source_tree=tree,mailbox_sha256=hashlib.sha256((R/path).read_bytes()).hexdigest())
 row['placement_status']='IDENTICAL_FINAL_TREE_SHARED_FEE_REHOME_20261022'
 contracts['patches'][str(row['contract_id'])].setdefault('canonical_source',{}).update(commit=sha,parent=parent,tree=tree)
m['v2_boundary_global_number']=377;m['source_authority']='Maintained Git branches and pins;mailboxes are archival exports,not the development authority.'
m['shared_performance_first_rehome']={'status':'PROMOTED_EXACT_TREE_GATES_GREEN','old_tip':OLD,'new_tip':NEW,'shared_tip':E,'tree':TREE,'shared_count':376,'native_count':153,'total':529,'moved_logical_owner':fee['canonical_id'],'former_native_owner':149,'new_shared_owner':376,'hunk_mapping':'daemon/patch-intake/20261022/shared-performance-placement/FIRST-REHOME-HUNK-MAPPING.json','validation':'FULL529replay;sharedbuild+8fee/48assert+nodefunctional;nativefull1203exacttreebinary','pool134':'DEFERRED_missing_native059implementation_in_sharedprefix'}
write(A/'contracts.json',contracts);write(A/'canonical-manifest.json',m)
progression=load('patch_progression_shared_rehome',R/'daemon/scripts/patch-progression.py');_,entries=progression.manifest(R)
assert len(entries[1:])==529
for row,entry in zip(rows,entries[1:],strict=True):row['prefix_sha256']=entry['prefix_sha256']
write(A/'canonical-manifest.json',m);write(P/'PROMOTED-SOURCE.json',m['shared_performance_first_rehome'])
print('PROMOTED376+153=529_FINAL_TREE_EXACT')
