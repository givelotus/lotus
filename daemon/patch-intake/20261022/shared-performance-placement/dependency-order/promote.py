import importlib.util,sys,subprocess,json,hashlib,copy
from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[4];S=R/'daemon/worktrees/merklix-slab-source';A=R/'daemon/patch-audit/progression'
def git(*a,input=None):return subprocess.check_output(['git','-C',str(S),*a],input=input,text=True).strip()
def read(p):return json.loads(p.read_text())
def write(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def load(n,p):
 sp=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(sp);sys.modules[n]=m;sp.loader.exec_module(m);return m
D=read(P/'CANDIDATE.json');B=read(P/'PLAN.json')['baseline'];owners=read(P/'OWNER-MAPPING.json');assert read(P/'FULL530-REPLAY.json')['status']=='PASS_ALL530_INTERMEDIATE_TREES'
assert read(P/'GENERIC-PREFIX-BUILD-R2.json')['exit_code']==0 and read(P/'ADMISSION-PREFIX-BUILD.json')['exit_code']==0
assert all(x['exit_code']==0 for x in read(P/'GENERIC-TESTS.json')[:2]) and all(x['exit_code']==0 for x in read(P/'GENERIC-FOLLOWUP-TESTS.json')) and all(x['exit_code']==0 for x in read(P/'ADMISSION-TESTS.json'))
assert git('rev-parse',D['new_tip']+'^{tree}')==B['tree']==git('rev-parse',B['v2']+'^{tree}');assert git('rev-parse',D['new_shared']+'^{tree}')==B['shared_tree'];assert not git('status','--porcelain')
assert git('rev-parse','daemon/ecash')==B['ecash']and git('rev-parse','daemon/v2')==B['v2']
lotus=load('lotus_git_dependency_order',R/'daemon/scripts/lotus-git.py');assert lotus.verify_linear_and_no_fixups(S,'base/abc',D['new_shared'])==377;assert lotus.verify_linear_and_no_fixups(S,D['new_shared'],D['new_tip'])==153
m=read(A/'canonical-manifest.json');contracts=read(A/'contracts.json');write(P/'before-canonical-manifest.json',m);old={x['canonical_source_commit']:x for x in m['patches']};assert len(old)==530
git('update-ref','--stdin',input=f"start\nupdate refs/heads/daemon/ecash {D['new_shared']} {B['ecash']}\nupdate refs/heads/daemon/v2 {D['new_tip']} {B['v2']}\nprepare\ncommit\n");git('checkout','daemon/v2')
for name,sha in [('ecash',D['new_shared']),('v2',D['new_tip'])]:lotus.write_head_pin_sha(lotus.SERIES_SPECS[name],sha)
lotus.export_range_to_patches_dir(ws=S,start_sha='base/abc',end_sha=D['new_shared'],patches_dir=R/'daemon/patches/ecash')
lotus.export_range_to_patches_dir(ws=S,start_sha=D['new_shared'],end_sha=D['new_tip'],patches_dir=R/'daemon/patches/v2',include_directive='@include ../ecash/series')
paths=[]
for series in ['ecash','v2']:paths.extend((series,n+1,x)for n,x in enumerate(lotus.read_manifest_entries(R/f'daemon/patches/{series}/series')))
rows=[]
for i,(owner,(series,num,name))in enumerate(zip(owners,paths,strict=True),1):
 row=copy.deepcopy(old[owner['old_commit']]);sha=owner['new_commit'];tr=owner['tree'];parent=git('rev-parse',sha+'^');path=f'daemon/patches/{series}/{name}';files=owner['files'];row.update(global_number=i,series=series,layer=series,number=num,layer_number=num,file=name,canonical_patch_path=path,canonical_source_commit=sha,canonical_parent_commit=parent,canonical_source_tree=tr,files=files,mailbox_sha256=hashlib.sha256((R/path).read_bytes()).hexdigest(),placement_status='DEPENDENCY_ORDER_EXACT_TREE_20261022');co=contracts['patches'][str(row['contract_id'])];co.setdefault('canonical_source',{}).update(commit=sha,parent=parent,tree=tr,files=files);co.update(source_owner=path,source_series=series);rows.append(row)
m['patches']=rows;m['v2_boundary_global_number']=378;m['current_source']={'base':git('rev-parse','base/abc'),'ecash':D['new_shared'],'v2':D['new_tip'],'tree':D['tree']};m['dependency_priority_reorder']={'status':'PROMOTED_EXACT_TREES_PREFIX_GATES_GREEN','shared':377,'native':153,'total':530,'tree':D['tree'],'shared_tree':D['shared_tree'],'owner_ledger':str((P/'OWNER-MAPPING.json').relative_to(R)),'hunk_transfer':'Existing test-pause Flush call moves from MDBX to async logger owner where API exists; no other code behavior changes','interface_changes':'None; pool/fullrecon/tree adapter proposals remain explicit separate work'}
write(A/'contracts.json',contracts);write(A/'canonical-manifest.json',m);progression=load('patch_progression_dependency_order',R/'daemon/scripts/patch-progression.py');_,entries=progression.manifest(R);assert len(entries[1:])==530
for row,entry in zip(rows,entries[1:],strict=True):row['prefix_sha256']=entry['prefix_sha256']
write(A/'canonical-manifest.json',m);write(P/'PROMOTED.json',dict(m['dependency_priority_reorder'],source=m['current_source']));print('DEPENDENCY_ORDER_PROMOTED_EXACT_TREES')
