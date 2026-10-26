import importlib.util,sys,subprocess,json,hashlib
from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[4];S=R/'daemon/worktrees/merklix-slab-source';A=R/'daemon/patch-audit/progression';D=json.loads((P/'BASELINE.json').read_text());NEW='5dcb81d975a654f8c36fa6e36f3605fa217fd084';TREE=D['tree']
def git(*a,input=None):return subprocess.check_output(['git','-C',str(S),*a],input=input,text=True).strip()
def read(p):return json.loads(p.read_text())
def write(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def load(n,p):
 sp=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(sp);sys.modules[n]=m;sp.loader.exec_module(m);return m
assert read(P/'FULL529-REPLAY.json')['status']=='PASS_ALL529_INTERMEDIATE_TREES'
assert read(P/'shared-build-result.json')['exit_code']==0 and all(x['exit_code']==0 for x in read(P/'shared-focused-results.json'))
assert git('rev-parse',NEW+'^{tree}')==TREE==git('rev-parse',D['old_v2']+'^{tree}')
assert git('rev-parse','daemon/ecash')==D['old_shared']and git('rev-parse','daemon/v2')==D['old_v2']
assert not git('status','--porcelain')
lotus=load('lotus_git_snapshot_rehome',R/'daemon/scripts/lotus-git.py');assert lotus.verify_linear_and_no_fixups(S,'base/abc',D['new_shared'])==376;assert lotus.verify_linear_and_no_fixups(S,D['new_shared'],NEW)==153
m=read(A/'canonical-manifest.json');contracts=read(A/'contracts.json');write(P/'before-canonical-manifest.json',m)
git('update-ref','--stdin',input=f"start\nupdate refs/heads/daemon/ecash {D['new_shared']} {D['old_shared']}\nupdate refs/heads/daemon/v2 {NEW} {D['old_v2']}\nprepare\ncommit\n");git('checkout','daemon/v2')
for name,sha in [('ecash',D['new_shared']),('v2',NEW)]:lotus.write_head_pin_sha(lotus.SERIES_SPECS[name],sha)
lotus.export_range_to_patches_dir(ws=S,start_sha='base/abc',end_sha=D['new_shared'],patches_dir=R/'daemon/patches/ecash')
lotus.export_range_to_patches_dir(ws=S,start_sha=D['new_shared'],end_sha=NEW,patches_dir=R/'daemon/patches/v2',include_directive='@include ../ecash/series')
commits=git('log','--reverse','--format=%H %T %P','base/abc..'+NEW).splitlines();rows=m['patches'];assert len(rows)==len(commits)==529
paths=[]
for series in ['ecash','v2']:
 paths.extend((series,n+1,x)for n,x in enumerate(lotus.read_manifest_entries(R/f'daemon/patches/{series}/series')))
for idx,(row,line,(series,num,name))in enumerate(zip(rows,commits,paths,strict=True),1):
 sha,tr,parent=line.split();path=f'daemon/patches/{series}/{name}';files=git('diff','--name-only',parent,sha,'--').splitlines();row.update(global_number=idx,series=series,layer=series,number=num,layer_number=num,file=name,canonical_patch_path=path,canonical_source_commit=sha,canonical_parent_commit=parent,canonical_source_tree=tr,files=files,mailbox_sha256=hashlib.sha256((R/path).read_bytes()).hexdigest(),placement_status='SHARED_SNAPSHOT_RESET_DEFER_EXACT_TREE_20261022');contracts['patches'][str(row['contract_id'])].setdefault('canonical_source',{}).update(commit=sha,parent=parent,tree=tr,files=files)
m['v2_boundary_global_number']=377;m['snapshot_reset_defer_rehome']={'status':'PROMOTED_EXACT_TREE_GATES_GREEN','old_tip':D['old_v2'],'new_tip':NEW,'shared_tip':D['new_shared'],'tree':TREE,'shared_count':376,'native_count':153,'total':529,'from':'native041selected8txmempoolhunks','to':'shared371immutablepublication/deferlifetime','snapshot_owner':D['new_snapshot_owner'],'native_gate':'Reusefirstbatch1203onlybecausecompleteendpointtreeidentical','source_hunk_selection':'daemon/patch-intake/20261022/shared-performance-placement/snapshot-reset-defer/SOURCE-HUNK-SELECTION.json'};m['current_source']={'base':'1fb7db17c176cdea8a2c60d887891589382ee4e3','ecash':D['new_shared'],'v2':NEW,'tree':TREE}
write(A/'contracts.json',contracts);write(A/'canonical-manifest.json',m);progression=load('patch_progression_snapshot_rehome',R/'daemon/scripts/patch-progression.py');_,entries=progression.manifest(R);assert len(entries[1:])==529
for row,entry in zip(rows,entries[1:],strict=True):row['prefix_sha256']=entry['prefix_sha256']
write(A/'canonical-manifest.json',m);write(P/'PROMOTED.json',m['snapshot_reset_defer_rehome']);print('SNAPSHOT_BATCH_PROMOTED_EXACT_TREE')
