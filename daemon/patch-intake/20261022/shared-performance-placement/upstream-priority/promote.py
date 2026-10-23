import importlib.util,sys,subprocess,json,hashlib,copy
from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[4];S=R/'daemon/worktrees/merklix-slab-source';A=R/'daemon/patch-audit/progression'
def git(*a,input=None):return subprocess.check_output(['git','-C',str(S),*a],input=input,text=True).strip()
def read(p):return json.loads(p.read_text())
def write(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
def load(n,p):
 sp=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(sp);sys.modules[n]=m;sp.loader.exec_module(m);return m
D=read(P/'CANDIDATE.json');before=read(P/'ORDER-PLAN.json');mapping=read(P/'FINAL-OWNER-MAPPING.json')
assert read(P/'FULL530-REPLAY.json')['status']=='PASS_ALL530_INTERMEDIATE_TREES'
assert read(P/'EARLY-CHECKER-BUILD.json')['exit_code']==0 and all(x['exit_code']==0 for x in read(P/'EARLY-CHECKER-TESTS.json')['results'])
assert git('rev-parse',D['new_tip']+'^{tree}')==before['tree']==git('rev-parse',before['old_v2']+'^{tree}')
assert git('rev-parse',D['new_shared']+'^{tree}')==git('rev-parse',before['old_shared']+'^{tree}')
assert git('rev-parse','daemon/ecash')==before['old_shared'] and git('rev-parse','daemon/v2')==before['old_v2'];assert not git('status','--porcelain')
lotus=load('lotus_git_priority',R/'daemon/scripts/lotus-git.py');assert lotus.verify_linear_and_no_fixups(S,'base/abc',D['new_shared'])==377;assert lotus.verify_linear_and_no_fixups(S,D['new_shared'],D['new_tip'])==153
m=read(A/'canonical-manifest.json');contracts=read(A/'contracts.json');write(P/'before-canonical-manifest.json',m);oldrows={x['canonical_source_commit']:x for x in m['patches']};assert len(oldrows)==529
newid='build-linked-worktree-git-metadata';newrow={'canonical_id':newid,'contract_id':newid,'original_ids':['extracted-generic-build-from-adaptive-policy'],'original_sha':D['build_prerequisite'],'original_patch':'source-history-build-prerequisite-extraction','concern':'build compatibility','subject':'build: resolve Git metadata paths in linked worktrees','repair_ledger_ref':'upstream-priority/FINAL-OWNER-MAPPING.json','contract_ref':'contracts.json#/patches/'+newid,'build_status':'PASS_EARLY_PREFIX'}
contracts['patches'][newid]={'contract_id':newid,'scope':'Only Git metadata discovery for linked worktree builds','concrete_problem':'ABC assumes .git is a directory, preventing linked worktree CMake configuration','semantic_invariants':['No policy, consensus, runtime or source endpoint behavior changes','Exact original CMake hunk extracted from adaptive-policy owner'],'required_native_suites':{'bitcoin':[]},'required_functional_tests':[],'review_status':'Early prefix daemon/core build PASS; full final tree unchanged'}
git('update-ref','--stdin',input=f"start\nupdate refs/heads/daemon/ecash {D['new_shared']} {before['old_shared']}\nupdate refs/heads/daemon/v2 {D['new_tip']} {before['old_v2']}\nprepare\ncommit\n");git('checkout','daemon/v2')
for name,sha in [('ecash',D['new_shared']),('v2',D['new_tip'])]:lotus.write_head_pin_sha(lotus.SERIES_SPECS[name],sha)
lotus.export_range_to_patches_dir(ws=S,start_sha='base/abc',end_sha=D['new_shared'],patches_dir=R/'daemon/patches/ecash')
lotus.export_range_to_patches_dir(ws=S,start_sha=D['new_shared'],end_sha=D['new_tip'],patches_dir=R/'daemon/patches/v2',include_directive='@include ../ecash/series')
paths=[]
for series in ['ecash','v2']:paths.extend((series,n+1,x)for n,x in enumerate(lotus.read_manifest_entries(R/f'daemon/patches/{series}/series')))
rows=[]
for idx,(owner,(series,num,name))in enumerate(zip(mapping,paths,strict=True),1):
 row=copy.deepcopy(oldrows[owner['old_commit']] if owner['old_commit'] else newrow);sha=owner['new_commit'];tr=owner['tree'];parent=git('rev-parse',sha+'^');
 if not owner['old_commit']:row.update(sha=sha,tree=tr,parent=parent)
 path=f'daemon/patches/{series}/{name}';files=owner['files'];row.update(global_number=idx,series=series,layer=series,number=num,layer_number=num,file=name,canonical_patch_path=path,canonical_source_commit=sha,canonical_parent_commit=parent,canonical_source_tree=tr,files=files,mailbox_sha256=hashlib.sha256((R/path).read_bytes()).hexdigest(),placement_status='UPSTREAM_SMALL_FIRST_EXACT_TREE_20261022');co=contracts['patches'][str(row['contract_id'])];co.setdefault('canonical_source',{}).update(commit=sha,parent=parent,tree=tr,files=files);co.update(source_owner=path,source_series=series);rows.append(row)
m['patches']=rows;m['v2_boundary_global_number']=378;m['current_source']={'base':before['base'],'ecash':D['new_shared'],'v2':D['new_tip'],'tree':D['tree']};m['upstream_priority_reorder']={'status':'PROMOTED_EXACT_TREE_EARLY_PREFIX_GATES_GREEN','shared':377,'native':153,'total':530,'tree':D['tree'],'ledger':str(P.relative_to(R)/'FINAL-OWNER-MAPPING.json'),'early_order':[x['subject']for x in mapping[:11]],'new_build_owner':'Generic CMake hunk extracted from former adaptive-policy owner; distinct purpose retained','functional_companion':'Checker functional file mapped byte-identically to class-attribute framework prerequisite'}
write(A/'contracts.json',contracts);write(A/'canonical-manifest.json',m);progression=load('patch_progression_priority',R/'daemon/scripts/patch-progression.py');_,entries=progression.manifest(R);assert len(entries[1:])==530
for row,entry in zip(rows,entries[1:],strict=True):row['prefix_sha256']=entry['prefix_sha256']
write(A/'canonical-manifest.json',m);write(P/'PROMOTED.json',dict(m['upstream_priority_reorder'],source=m['current_source']));print('UPSTREAM_PRIORITY_PROMOTED_EXACT_TREE')
