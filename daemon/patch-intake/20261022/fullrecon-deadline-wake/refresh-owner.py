#!/usr/bin/env python3
"""Export the tested scheduler repair from its earliest logical owner."""
import gzip,hashlib,importlib.util,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];HERE=Path(__file__).resolve().parent
SOURCE=ROOT/'daemon/worktrees/merklix-slab-source';AUDIT=ROOT/'daemon/patch-audit/progression'
def git(*args):return subprocess.check_output(['git','-C',str(SOURCE),*args],text=True).strip()
def read(p):return json.loads(p.read_text())
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
base='1fb7db17c176cdea8a2c60d887891589382ee4e3'
lines=git('log','--reverse','--format=%H %T %P',base+'..HEAD').splitlines();assert len(lines)==528
assert git('rev-parse','HEAD^{tree}')=='cbc28b7066d27c2694ea0d9f7a1084ab174d9cf7'
p=AUDIT/'canonical-manifest.json';m=read(p);owner=m['patches'][524]
assert owner['file']=='151-net-reconcile-complete-pinned-mempool-snapshots.patch'
path=ROOT/owner['canonical_patch_path'];old=path.read_bytes();(HERE/'before-owner151.mailbox.gz').write_bytes(gzip.compress(old,mtime=0))
hashes={r['canonical_patch_path']:hashlib.sha256((ROOT/r['canonical_patch_path']).read_bytes()).hexdigest() for r in m['patches']}
commit=lines[524].split()[0]
raw=subprocess.check_output(['git','-C',str(SOURCE),'-c','format.signature=','format-patch','--stdout','--binary','--full-index','--no-stat','-1',commit]);path.write_bytes(raw)
assert [r['canonical_patch_path'] for r in m['patches'] if hashlib.sha256((ROOT/r['canonical_patch_path']).read_bytes()).hexdigest()!=hashes[r['canonical_patch_path']]]==[owner['canonical_patch_path']]
contracts=read(AUDIT/'contracts.json')
for index,(row,line) in enumerate(zip(m['patches'],lines)):
 sha,tr,pa=line.split();row.update(canonical_source_commit=sha,canonical_parent_commit=pa,canonical_source_tree=tr,mailbox_sha256=hashlib.sha256((ROOT/row['canonical_patch_path']).read_bytes()).hexdigest())
 if index>=524:row['canonical_validation_status']='EXACT_TESTED_TREE_FULL1200_PASS_DEADLINE_REPAIR_REPLAY_PENDING'
 contracts['patches'][str(row['contract_id'])].setdefault('canonical_source',{}).update(commit=sha,parent=pa,tree=tr)
contracts['patches'][str(owner['contract_id'])].setdefault('reviewed_repairs',{})['deadline_wake_20261022']={'cause':'125ms exchanges waited for100ms idle receive heartbeat, producing~210ms request gaps.','fix':'Expose useful fetch/admission deadline; existing relay scheduler wakes at deadline; bounded64-body admission avoids duplicate validation only for exact already-admitted TxHash bodies.','wire_delta':'none','limits_preserved':['125ms spacing','one inflight request','page64','frame/memory bounds','shared incoming rate limit','authenticated full coverage','normal validation'],'source_owner':commit,'full_native_cases':1200,'tested_tree':git('rev-parse','HEAD^{tree}'),'recovery_check1_seconds':[84.7598,59.8871],'production_profile_check0_seconds':36.7213,'admission_cost_correction':'check1 fullpool scan on every accepted transaction dominates24s; not scheduler sleep'}
head,tr,pa=lines[-1].split()
m['fullrecon_deadline_repair']={'owner_global':525,'owner_commit':commit,'source528':head,'tree528':tr,'source527':pa,'tested_candidate':'2a36522dc27ba4832ccfa48264291820e960d12c','logical_owner_count':528,'wire_delta':'none','status':'EXACT_TESTED_TREE_FULL1200_PASS_REPLAY_PENDING'}
m['slab-merklix-snapshots528_delivery'].update(head=head,tree=tr,parent=pa)
write(AUDIT/'contracts.json',contracts);write(p,m)
mod=load('patch_progression',ROOT/'daemon/scripts/patch-progression.py');_,entries=mod.manifest(ROOT)
for row,entry in zip(m['patches'],entries[1:]):row['prefix_sha256']=entry['prefix_sha256']
write(p,m)
lotus=load('lotus_git',ROOT/'daemon/scripts/lotus-git.py');lotus.write_head_pin_sha(lotus.SERIES_SPECS['v2'],head)
repairs=read(AUDIT/'repairs.json');repairs.append({'date':'2026-10-22','purpose':'Wake full reconciliation at useful continuation deadlines','first_responsible_global_number':525,'first_responsible_layer':'v2/151','contract_id':owner['contract_id'],'before_source_commit':'b94109e84276f6c60a0018240100ccdca456d3a2','after_source_commit':commit,'before_mailbox_sha256':hashlib.sha256(old).hexdigest(),'after_mailbox_sha256':hashlib.sha256(raw).hexdigest(),'production_code_changed':True,'assertions_weakened_deleted_or_skipped':False,'placement':'fixup folded into first scheduler owner;528 logical owners unchanged','invalidate_from_index':525,'status':'full1200 pass; exact tested tree; full replay pending'})
write(AUDIT/'repairs.json',repairs)
write(HERE/'integrated-source.json',m['fullrecon_deadline_repair'])
print(head,tr,pa,commit)
