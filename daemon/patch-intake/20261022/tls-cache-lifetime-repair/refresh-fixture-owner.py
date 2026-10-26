#!/usr/bin/env python3
"""Fold the exact-transaction test repair into its first responsible owner."""
import hashlib,importlib.util,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];HERE=Path(__file__).resolve().parent
SOURCE=ROOT/'daemon/worktrees/merklix-slab-source';AUDIT=ROOT/'daemon/patch-audit/progression'
def git(*args):return subprocess.check_output(['git','-C',str(SOURCE),*args],text=True).strip()
def read(p):return json.loads(p.read_text())
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
base='1fb7db17c176cdea8a2c60d887891589382ee4e3';lines=git('log','--reverse','--format=%H %T %P',base+'..HEAD').splitlines();assert len(lines)==528
p=AUDIT/'canonical-manifest.json';m=read(p);owner=m['patches'][348];assert owner['file']=='348-validation-net-split-admission-into-reusable-phases-no-behavior-change.patch'
path=ROOT/owner['canonical_patch_path'];old=path.read_bytes();(HERE/'before-ecash348.mailbox').write_bytes(old);hashes={r['canonical_patch_path']:hashlib.sha256((ROOT/r['canonical_patch_path']).read_bytes()).hexdigest() for r in m['patches']}
commit=lines[348].split()[0];raw=subprocess.check_output(['git','-C',str(SOURCE),'-c','format.signature=','format-patch','--stdout','--binary','--full-index','--no-stat','-1',commit]);path.write_bytes(raw)
assert [r['canonical_patch_path'] for r in m['patches'] if hashlib.sha256((ROOT/r['canonical_patch_path']).read_bytes()).hexdigest()!=hashes[r['canonical_patch_path']]]==[owner['canonical_patch_path']]
contracts=read(AUDIT/'contracts.json')
for row,line in zip(m['patches'],lines):
 sha,tr,pa=line.split();row.update(canonical_source_commit=sha,canonical_parent_commit=pa,canonical_source_tree=tr,mailbox_sha256=hashlib.sha256((ROOT/row['canonical_patch_path']).read_bytes()).hexdigest(),canonical_validation_status='TLS_LIFETIME_AND_EXACT_TX_FIXTURE_REPAIRED_FULL_GATES_PENDING')
 contracts['patches'][str(row['contract_id'])].setdefault('canonical_source',{}).update(commit=sha,parent=pa,tree=tr,delivery='tls-lifetime-and-exact-tx-repaired528')
contract=contracts['patches'][str(owner['contract_id'])];contract.setdefault('reviewed_repairs',{})['exact_tx_admission_fixture_20261022']={'cause':'The purported identical-transaction precompute/serial comparison signed different funding outpoints; ECDSA DER signature lengths can differ, so valid transaction sizes need not match.','fix':'Compare exact same signed transaction before/after normal recursive mempool removal; preserve result, rejection, vsize and fee equality assertions and add removal assertion.','production_admission_changed':False,'before_failure':'m_vsize equality in precomputed_checks_give_serial_verdicts','source_owner':commit}
write(AUDIT/'contracts.json',contracts)
head,tr,pa=lines[-1].split();m['slab-merklix-snapshots528_delivery'].update(head=head,tree=tr,parent=pa,endpoint_benchmark='pending final identical-repair matched full gates');m['tls_cache_lifetime_repair'].update(source528=head,source527=pa,fixture_owner_global=349,fixture_owner_commit=commit)
write(p,m);mod=load('patch_progression',ROOT/'daemon/scripts/patch-progression.py');_,entries=mod.manifest(ROOT)
for row,entry in zip(m['patches'],entries[1:]):row['prefix_sha256']=entry['prefix_sha256']
write(p,m)
lotus=load('lotus_git',ROOT/'daemon/scripts/lotus-git.py');shared=lines[373].split()[0]
for ref,target in [('refs/heads/daemon/ecash',shared),('refs/heads/daemon/v2',head)]:subprocess.run(['git','-C',str(SOURCE),'update-ref',ref,target],check=True)
lotus.write_head_pin_sha(lotus.SERIES_SPECS['ecash'],shared);lotus.write_head_pin_sha(lotus.SERIES_SPECS['v2'],head)
repairs=read(AUDIT/'repairs.json');repairs.append({'date':'2026-10-22','purpose':'Compare identical signed transaction in precomputed/serial admission fixture','first_responsible_global_number':349,'first_responsible_layer':'ecash/348','contract_id':owner['contract_id'],'before_source_commit':'6385b40f9b5b2f6bf69f0d555cf551a65078179b','after_source_commit':commit,'before_mailbox_sha256':hashlib.sha256(old).hexdigest(),'after_mailbox_sha256':hashlib.sha256(raw).hexdigest(),'production_code_changed':False,'assertions_weakened_deleted_or_skipped':False,'placement':'fixup folded into first fixture owner;528 logical owners unchanged','invalidate_from_index':349,'status':'focused mempool, signature cache and lotus_v2 suites pass; final full gates pending'})
write(AUDIT/'repairs.json',repairs)
previous=read(HERE/'source-identities.json');previous['cache_only_intermediate527']=previous['source527'];previous['cache_only_intermediate528']=previous['source528'];previous.update(status='TWO_CAUSAL_OWNERS_REPAIRED_FINAL_GATES_PENDING',source527=pa,tree527=git('rev-parse',pa+'^{tree}'),source528=head,tree528=tr,source374=shared,tree374=lines[373].split()[1],fixture_owner_global=349,fixture_owner_commit=commit,changed_mailboxes=['daemon/patches/ecash/025-script-shard-the-signature-cache-and-add-bounded-tls-lookup.patch',str(path.relative_to(ROOT))]);write(HERE/'source-identities.json',previous)
print(head,pa,commit)
