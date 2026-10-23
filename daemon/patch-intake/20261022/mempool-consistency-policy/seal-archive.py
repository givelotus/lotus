#!/usr/bin/env python3
"""Seal the branch-first source checkpoint with a legacy archival replay entry."""
import hashlib,importlib.util,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];HERE=Path(__file__).resolve().parent
SOURCE=ROOT/'daemon/worktrees/merklix-slab-source';AUDIT=ROOT/'daemon/patch-audit/progression'
BASE='1fb7db17c176cdea8a2c60d887891589382ee4e3';SHARED='47765534500efe516e9306a6426d9c9ad9d216a4'
HEAD='a2af4764d116fa37fed463af1ffd3c6fb0514f76';SID='mempool-consistency-policy-20261022'
NAME='374-mempool-make-topological-consistency-checking-optional-on-every-network.patch'
def git(*args):return subprocess.check_output(['git','-C',str(SOURCE),*args],text=True).strip()
def read(p):return json.loads(p.read_text())
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
assert git('rev-parse','HEAD')==HEAD and not git('status','--porcelain')
lines=git('log','--reverse','--format=%H %T %P',BASE+'..HEAD').splitlines();assert len(lines)==529
assert lines[374].split()[0]==SHARED
m=read(AUDIT/'canonical-manifest.json');assert len(m['patches'])==528
old_hashes={r['canonical_patch_path']:hashlib.sha256((ROOT/r['canonical_patch_path']).read_bytes()).hexdigest() for r in m['patches']}
write(HERE/'previous-mailbox-hashes.json',old_hashes)
raw=subprocess.check_output(['git','-C',str(SOURCE),'-c','format.signature=','format-patch','--stdout','--binary','--full-index','--no-stat','-1',SHARED])
path=ROOT/'daemon/patches/ecash'/NAME;assert not path.exists();path.write_bytes(raw)
series=ROOT/'daemon/patches/ecash/series';series.write_text(series.read_text().rstrip()+'\n'+NAME+'\n')
sha,tr,pa=lines[374].split();subject=git('show','-s','--format=%s',SHARED);files=git('diff','--name-only',pa,sha).splitlines()
row={'sha':sha,'tree':tr,'parent':pa,'original_sha':sha,'original_patch':'new-'+SID,'concern':'whole','build_status':'SHARED34_AND_FUNCTIONAL_PASS_FINAL_GATE_PENDING','canonical_id':SID,'contract_id':SID,'original_ids':[SID],'repair_ledger_ref':'repairs.json','series':'ecash','number':374,'layer_number':374,'file':NAME,'subject':subject,'files':files,'global_number':375,'layer':'ecash','canonical_patch_path':str(path.relative_to(ROOT)),'mailbox_sha256':hashlib.sha256(raw).hexdigest(),'contract_ref':'contracts.json#/patches/'+SID}
m['patches'].insert(374,row);m['v2_boundary_global_number']=376
contracts=read(AUDIT/'contracts.json');assert SID not in contracts['patches']
contracts['patches'][SID]={'contract_id':SID,'original_patch':'new-'+SID,'original_sha':sha,'author_recorded_subject':subject,'author_recorded_rationale':git('show','-s','--format=%B',SHARED),'concrete_problem':'Optional whole-pool checker redundantly walks all ancestors per entry;regtest implicitly scans every mutation even in production-profile workloads.','split_mechanism':'One ordinary shared Git commit combines optional diagnostic cost and explicit opt-in policy;154 V2 owners replayed unchanged.','source_files':files,'review_status':'SHARED34_AND_FUNCTIONAL_PASS_FINAL_GATE_PENDING','semantic_invariants':['All graph/coin/pointer/fee/size/cached-memory assertions preserved;direct-parent entryId induction proves transitive ordering.','Normal admission,transaction validation,consensus and checkblockindex defaults unchanged.','Native fixtures and functional framework explicitly enable checking;new policy test separately exercises node defaults.','Existing V2 flag3 input handling remains in later V2 layer.'],'required_native_suites':{'bitcoin':['mempool_tests','mempool_admission_tests']},'required_functional_tests':['feature_mempool_consistency.py'],'validation_limits':['No new throughput or checker timing claim;historical check1 and check0 recovery results remain frozen.'],'delivery':SID}
for index,(row,line) in enumerate(zip(m['patches'],lines),1):
 sha,tr,pa=line.split();row.update(global_number=index,canonical_source_commit=sha,canonical_parent_commit=pa,canonical_source_tree=tr,mailbox_sha256=hashlib.sha256((ROOT/row['canonical_patch_path']).read_bytes()).hexdigest())
 if index>=375:row['canonical_validation_status']='SHARED375_TESTED_FINAL529_GATE_AND_ARCHIVAL_REPLAY_PENDING'
 contracts['patches'][str(row['contract_id'])].setdefault('canonical_source',{}).update(commit=sha,parent=pa,tree=tr)
refs={'base/abc':BASE,'daemon/ecash':SHARED,'daemon/v2':HEAD}
m['source_authority']='Maintained Git branches and pins;mailboxes are archival exports,not the development authority.'
m['mempool_consistency_policy_delivery']={'source_refs':refs,'head':HEAD,'tree':git('rev-parse','HEAD^{tree}'),'shared_tree':lines[374].split()[1],'count':529,'shared_count':375,'native_count':154,'new_owner_global':375,'global_number_mapping':'Prior V2 globals375..528 are now376..529;historical frozen datasets retain their original labels.','previous_final528':'6e2c35541feaa4af13d91a227ac5a7c09797b2be','wire_delta':'none','status':'SHARED34_AND_FUNCTIONAL_PASS_FINAL_GATE_AND_REPLAY_PENDING'}
write(AUDIT/'contracts.json',contracts);write(AUDIT/'canonical-manifest.json',m)
progression=load('patch_progression',ROOT/'daemon/scripts/patch-progression.py');_,entries=progression.manifest(ROOT)
for row,entry in zip(m['patches'],entries[1:]):row['prefix_sha256']=entry['prefix_sha256']
write(AUDIT/'canonical-manifest.json',m)
lotus=load('lotus_git',ROOT/'daemon/scripts/lotus-git.py')
for name,sha in [('ecash',SHARED),('v2',HEAD)]:lotus.write_head_pin_sha(lotus.SERIES_SPECS[name],sha)
write(HERE/'source-identities.json',m['mempool_consistency_policy_delivery'])
assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in old_hashes.items())
print('Sealed one ordinary shared Git owner;all prior mailbox bytes unchanged;529 archival entries.')
