#!/usr/bin/env python3
"""Export only the causal TLS owner; retain528 logical owners and all other bytes."""
import hashlib, importlib.util, json, shutil, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];HERE=Path(__file__).resolve().parent
SOURCE=ROOT/'daemon/worktrees/merklix-slab-source';AUDIT=ROOT/'daemon/patch-audit/progression'
def git(*args):return subprocess.check_output(['git','-C',str(SOURCE),*args],text=True).strip()
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);mod=importlib.util.module_from_spec(spec);sys.modules[name]=mod;spec.loader.exec_module(mod);return mod
def read(p):return json.loads(p.read_text())
def write(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
base='1fb7db17c176cdea8a2c60d887891589382ee4e3'
lines=git('log','--reverse','--format=%H %T %P',base+'..HEAD').splitlines();assert len(lines)==528
manifest_path=AUDIT/'canonical-manifest.json';m=read(manifest_path);assert len(m['patches'])==528
owner=m['patches'][25];assert owner['file']=='025-script-shard-the-signature-cache-and-add-bounded-tls-lookup.patch'
path=ROOT/owner['canonical_patch_path'];old=path.read_bytes();(HERE/'before-ecash025.mailbox').write_bytes(old)
old_hashes={str(ROOT/r['canonical_patch_path']):hashlib.sha256((ROOT/r['canonical_patch_path']).read_bytes()).hexdigest() for r in m['patches']}
commit=lines[25].split()[0]
raw=subprocess.check_output(['git','-C',str(SOURCE),'-c','format.signature=','format-patch','--stdout','--binary','--full-index','--no-stat','-1',commit])
path.write_bytes(raw)
assert [str(ROOT/r['canonical_patch_path']) for r in m['patches'] if hashlib.sha256((ROOT/r['canonical_patch_path']).read_bytes()).hexdigest()!=old_hashes[str(ROOT/r['canonical_patch_path'])]]==[str(path)]
for entry,line in zip(m['patches'],lines):
 sha,tree,parent=line.split();entry.update(canonical_source_commit=sha,canonical_parent_commit=parent,canonical_source_tree=tree,mailbox_sha256=hashlib.sha256((ROOT/entry['canonical_patch_path']).read_bytes()).hexdigest(),canonical_validation_status='TLS_LIFETIME_OWNER_REPAIRED_PENDING_FULL_REPLAY_AND_MATCHED_GATES')
head,tree,parent=lines[-1].split();shared,shared_tree,_=lines[373].split()
m['slab-merklix-snapshots528_delivery'].update(head=head,tree=tree,parent=parent,endpoint_benchmark='pending repaired matched gates; old385/c4 frozen and historical')
m['tls_cache_lifetime_repair']={'owner_global':26,'owner_layer':25,'owner_series':'ecash','old_owner':'4e5e8e9e43eb89701671b848a1c9875122aa1532','new_owner':commit,'source528':head,'source527':parent,'evidence':'daemon/patch-intake/20261022/tls-cache-lifetime-repair','scope':'Single cache-lifetime repair before both endpoints; no additional owner or pool'}
contracts_path=AUDIT/'contracts.json';c=read(contracts_path)
for entry,line in zip(m['patches'],lines):
 sha,tr,pa=line.split();contract=c['patches'][str(entry['contract_id'])];record=contract.setdefault('canonical_source',{});record.update(commit=sha,parent=pa,tree=tr,delivery='tls-cache-lifetime-repaired528')
contract=c['patches']['22'];contract.setdefault('semantic_invariants',[]).append('TLS signature-cache success belongs to a nonwrapping process-unique cache lifetime ID; cache address reuse cannot revive successes from an earlier lifetime, including on persistent worker threads.')
assert 'sigcache_sharding_tests' in contract['required_native_suites']['bitcoin']
contract.setdefault('reviewed_repairs',{})['tls_owner_lifetime_20261022']={'cause':'Raw cache pointer reused after destruction; deterministic test RNG repeats salts and signatures across fixtures. Direct placement-reconstruction reproducer fails main and persistent worker TLS even with opaque fixed key, independent of RNG.','fix':'Nonwrapping unique uint64 instance token generated once per cache constructor; TLS compares lifetime token. Existing erase semantics and warmup assertions untouched.','regression':'sigcache_sharding_tests/tls_entries_do_not_survive_cache_address_reuse','before':'two assertion failures main_hit/new_hit','status':'build and matched full gates pending'}
write(contracts_path,c);write(manifest_path,m)
progression=load('patch_progression',ROOT/'daemon/scripts/patch-progression.py');_,entries=progression.manifest(ROOT)
for entry,checked in zip(m['patches'],entries[1:]):entry['prefix_sha256']=checked['prefix_sha256']
write(manifest_path,m)
lotus=load('lotus_git',ROOT/'daemon/scripts/lotus-git.py')
for ref,target in [('refs/heads/daemon/ecash',shared),('refs/heads/daemon/v2',head)]:subprocess.run(['git','-C',str(SOURCE),'update-ref',ref,target],check=True)
lotus.write_head_pin_sha(lotus.SERIES_SPECS['ecash'],shared);lotus.write_head_pin_sha(lotus.SERIES_SPECS['v2'],head)
repairs=read(AUDIT/'repairs.json');repairs.append({'date':'2026-10-22','purpose':'Signature-cache TLS lifetime isolation','first_responsible_global_number':26,'first_responsible_layer':'ecash/025','contract_id':'22','before_source_commit':'4e5e8e9e43eb89701671b848a1c9875122aa1532','after_source_commit':commit,'before_mailbox_sha256':hashlib.sha256(old).hexdigest(),'after_mailbox_sha256':hashlib.sha256(raw).hexdigest(),'placement':'fixup folded into earliest TLS owner; no additional logical owner','invalidate_from_index':26,'old_endpoint527':'385b64d7e7e0666e2bfff9865ee831a3186795fd','old_endpoint528':'c4d489d4826509013c982fa100e5e5de4a64ba5c','new_endpoint527':parent,'new_endpoint528':head,'status':'before-regression two failures; repaired source builds/gates pending'})
write(AUDIT/'repairs.json',repairs)
write(HERE/'source-identities.json',{'status':'REPAIRED_OWNER_EXPORTED_PENDING_REPLAY_AND_GATES','count':528,'owner_commit':commit,'owner_global':26,'source527':parent,'tree527':git('rev-parse',parent+'^{tree}'),'source528':head,'tree528':tree,'source374':shared,'tree374':shared_tree,'old_endpoint527_preserved':'385b64d7e7e0666e2bfff9865ee831a3186795fd','old_endpoint528_preserved':'c4d489d4826509013c982fa100e5e5de4a64ba5c','only_changed_mailbox':str(path.relative_to(ROOT)),'before_mailbox_sha256':hashlib.sha256(old).hexdigest(),'after_mailbox_sha256':hashlib.sha256(raw).hexdigest(),'pool_included':False})
print(head,parent,commit)
