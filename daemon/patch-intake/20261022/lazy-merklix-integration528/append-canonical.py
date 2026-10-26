#!/usr/bin/env python3
"""Mechanically export the committed feature and append one canonical owner."""
import copy, hashlib, importlib.util, json, shutil, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
SOURCE = ROOT / 'daemon/worktrees/merklix-slab-source'
PARENT = '385b64d7e7e0666e2bfff9865ee831a3186795fd'
HEAD = 'c4d489d4826509013c982fa100e5e5de4a64ba5c'
NAME = '154-lotus_v2-slab-backed-persistent-merklix-snapshots-with-lazy-hashing-and-minhash.patch'
SID = 'slab-merklix-snapshots-20261022'
AUDIT = ROOT / 'daemon/patch-audit/progression'
def git(*args):
    return subprocess.check_output(['git','-C',str(SOURCE),*args],text=True).strip()
def read(path): return json.loads(path.read_text())
def write(path, value): path.write_text(json.dumps(value,indent=2)+'\n')
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
    return module
assert git('rev-parse','HEAD')==HEAD and git('rev-parse',HEAD+'^')==PARENT
assert not git('status','--porcelain')
proof=read(HERE/'baseline527-replay.json')
assert proof['count']==527 and proof['head']==PARENT
manifest_path=AUDIT/'canonical-manifest.json';manifest=read(manifest_path)
assert len(manifest['patches'])==527
progression=load('patch_progression',ROOT/'daemon/scripts/patch-progression.py')
_, old_entries=progression.manifest(ROOT)
old_prefixes=[e['prefix_sha256'] for e in old_entries]
(HERE/'append154.series').write_text(NAME+'\n')
subprocess.run([sys.executable,str(ROOT/'daemon/scripts/export-patch-series.py'),str(SOURCE),
               str(HERE/'append154.series'),'--base',PARENT,'--output-dir',str(HERE/'generated154')],check=True)
newpatch=ROOT/'daemon/patches/v2'/NAME
assert not newpatch.exists()
shutil.copy2(HERE/'generated154'/NAME,newpatch)
series=ROOT/'daemon/patches/v2/series'
series.write_text(series.read_text().rstrip()+'\n'+NAME+'\n')
for entry,actual in zip(manifest['patches'],proof['records']):
    assert entry['series']==actual['series'] and entry['file']==actual['file']
    entry.update(canonical_source_commit=actual['commit'],canonical_parent_commit=actual['parent'],
                 canonical_source_tree=actual['tree'],mailbox_sha256=actual['sha256'],
                 canonical_validation_status='ACTUAL_CORRECTED527_MAILBOX_REPLAY_ALL_INTERMEDIATE_TREES_PASS')
files=git('diff','--name-only',PARENT,HEAD).splitlines()
row={'sha':HEAD,'tree':git('rev-parse',HEAD+'^{tree}'),'parent':PARENT,'original_sha':HEAD,
     'original_patch':'new-slab-merklix-snapshots-20261022','concern':'whole',
     'build_status':'EXACT_SOURCE_1199_NATIVE_TSAN400_SCOPE5_PASS_JEMALLOC_ON_PROFILE',
     'canonical_id':SID,'contract_id':SID,'original_ids':[SID],
     'repair_ledger_ref':'repairs.json','series':'v2','number':154,'layer_number':154,
     'file':NAME,'subject':git('show','-s','--format=%s',HEAD),'files':files,
     'global_number':528,'layer':'v2','canonical_patch_path':'daemon/patches/v2/'+NAME,
     'mailbox_sha256':hashlib.sha256(newpatch.read_bytes()).hexdigest(),
     'contract_ref':'contracts.json#/patches/'+SID,'canonical_source_commit':HEAD,
     'canonical_parent_commit':PARENT,'canonical_source_tree':git('rev-parse',HEAD+'^{tree}'),
     'canonical_validation_status':'EXACT_SOURCE_1199_NATIVE_TSAN400_SCOPE5_PASS_JEMALLOC_ON_PROFILE'}
manifest['patches'].append(row)
manifest['slab-merklix-snapshots528_delivery']={'head':HEAD,'tree':row['tree'],'parent':PARENT,
    'count':528,'shared_count':374,'native_count':154,
    'scope':'Only slab snapshot tree appended; cooperative/generic pool excluded',
    'report':'benchmark-results/20261022/slab-merklix-v1/REPORT.txt',
    'endpoint_benchmark':'pending matched allocator-OFF benchmark; previous test profile allocator-ON'}
contracts_path=AUDIT/'contracts.json';contracts=read(contracts_path)
assert SID not in contracts['patches']
new_contract=read(ROOT/'daemon/patch-intake/20261021/exports/slab-merklix-snapshots528-prepared/contracts-additions.template.json')['patches'][SID]
new_contract['review_status']='INTEGRATED_CANONICAL528_EXACT_SOURCE_TESTS_PASS_MATCHED_ENDPOINT_BENCHMARK_PENDING'
new_contract['validation_limits']=['Source1199 tests/TSAN400/scope5 acceptance used jemalloc-ON profile; matched527/528 allocator-OFF endpoint benchmark pending.','500k microbenchmarks are not500k all-peer node completion.','First cold hash and synchronous reclamation limitations remain explicit in source report.']
new_contract['canonical_source']={'commit':HEAD,'parent':PARENT,'tree':row['tree'],'files':files,
 'subject':row['subject'],'rationale':git('show','-s','--format=%B',HEAD),'delivery':'slab-merklix-snapshots528'}
contracts['patches'][SID]=new_contract
for entry,actual in zip(manifest['patches'][:-1],proof['records']):
    contract=contracts['patches'][str(entry.get('contract_id',entry.get('split_index',actual['global_number'])))]
    old=contract.get('canonical_source',{})
    old.update(commit=actual['commit'],parent=actual['parent'],tree=actual['tree'],delivery='corrected527-verified-prefix-for528')
    contract['canonical_source']=old
write(contracts_path,contracts);write(manifest_path,manifest)
_, updated=progression.manifest(ROOT)
assert [e['prefix_sha256'] for e in updated[:528]]==old_prefixes
for entry,checked in zip(manifest['patches'],updated[1:]):entry['prefix_sha256']=checked['prefix_sha256']
write(manifest_path,manifest)
# Use the existing pin writer; committed source refs exist in this assigned repo.
lotus=load('lotus_git',ROOT/'daemon/scripts/lotus-git.py')
boundary=proof['records'][373]['commit']
for ref,target in [('refs/heads/daemon/ecash',boundary),('refs/heads/daemon/v2',HEAD)]:
    exists=subprocess.run(['git','-C',str(SOURCE),'show-ref','--verify','--quiet',ref]).returncode==0
    if exists:assert git('rev-parse',ref)==target
    else:subprocess.run(['git','-C',str(SOURCE),'update-ref',ref,target,'0'*40],check=True)
lotus.write_head_pin_sha(lotus.SERIES_SPECS['ecash'],boundary)
lotus.write_head_pin_sha(lotus.SERIES_SPECS['v2'],HEAD)
write(HERE/'append-checkpoint.json',{'status':'APPENDED_ONE_OWNER_PENDING_FULL528_REPLAY','parent':PARENT,
 'head':HEAD,'tree':row['tree'],'count':528,'shared_count':374,'native_count':154,
 'all_527_prefix_bytes_unchanged':True,'all_527_gate_prefix_fingerprints_unchanged':True,
 'baseline527_prefix_sha256':old_prefixes[-1],'endpoint528_prefix_sha256':updated[-1]['prefix_sha256'],
 'shared_source':boundary,'shared_tree':proof['records'][373]['tree'],'new_patch':str(newpatch.relative_to(ROOT)),
 'new_patch_sha256':row['mailbox_sha256'],'pool_included':False})
print('Appended one generated owner;527 mailbox bytes and gate fingerprints unchanged.')
