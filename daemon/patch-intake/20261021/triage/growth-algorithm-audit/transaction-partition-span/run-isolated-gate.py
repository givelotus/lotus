#!/usr/bin/env python3
"""Run only after N1 grants exclusive compiler/runtime lease; fixed one A/B."""
import hashlib, json, os, pathlib, subprocess, time
P=pathlib.Path(__file__).resolve().parent
S=pathlib.Path('/Users/shammah/repos/lotus-v2-transaction-partition-span')
BASE='9f04419037a5527b498188c3a81f1cac259cc9c5'
HEAD='f418debf52ada8964e7fa58da36b5fef7b361ae2'
LIB=pathlib.Path('/Users/shammah/repos/lotus-v2-repair-work/recon-storage-latest-source/build/src/lotus_v2/liblotus_v2_blake3.a')
assert os.environ.get('PARTITION_EXCLUSIVE_LEASE') == 'N1_GRANTED', 'Explicit exclusive lease required'
assert subprocess.check_output(['git','-C',str(S),'rev-parse','HEAD'],text=True).strip()==HEAD
assert not subprocess.check_output(['git','-C',str(S),'status','--porcelain'],text=True).strip()
R={'base':BASE,'head':HEAD,'profile':'standalone -O3 C++20 pthread; system allocator; same BLAKE3 library','scope':'kernel mechanism; not daemon endpoint throughput','stages':[],'blake3_sha256':hashlib.sha256(LIB.read_bytes()).hexdigest(),'status':'RUNNING'}
def save(): (P/'isolated-result.json').write_text(json.dumps(R,indent=2)+'\n')
def run(name,cmd,timeout=120):
 start=time.monotonic(); before=os.getloadavg()
 x=subprocess.run([str(v) for v in cmd],capture_output=True,text=True,timeout=timeout)
 (P/(name+'.stdout.log')).write_text(x.stdout); (P/(name+'.stderr.log')).write_text(x.stderr)
 st={'name':name,'command':[str(v) for v in cmd],'exit':x.returncode,'seconds':time.monotonic()-start,'host_load_before':before,'host_load_after':os.getloadavg()}
 R['stages'].append(st);save()
 if x.returncode: raise RuntimeError(name+' failed')
 return x
try:
 before=P/'before-commitment.cpp'
 before.write_bytes(subprocess.check_output(['git','-C',str(S),'show',BASE+':src/lotus_v2/commitment.cpp']))
 assert subprocess.check_output(['git','-C',str(S),'show',BASE+':src/lotus_v2/tagged_hash.cpp'])==(S/'src/lotus_v2/tagged_hash.cpp').read_bytes()
 flags=['/usr/bin/c++','-std=c++20','-O3','-pthread','-Wall','-Wextra','-I'+str(S/'src'),'-I'+str(S/'src/lotus_v2')]
 tagged=S/'src/lotus_v2/tagged_hash.cpp'
 for side,commitment in [('before',before),('after',S/'src/lotus_v2/commitment.cpp')]:
  run(side+'-kernel-compile',flags+[P/'kernel.cpp',commitment,tagged,LIB,'-o',P/('kernel-'+side)])
  run(side+'-oracle',[P/('kernel-'+side)])
 run('normal-commitment-compile',flags+[S/'src/lotus_v2/test_commitment.cpp',S/'src/lotus_v2/commitment.cpp',tagged,LIB,'-o',P/'normal-commitment'])
 run('normal-commitment-vectors',[P/'normal-commitment'])
 # One matched pair, fixed500k identities, at least3seconds per side. No matrix.
 b=run('before-fixed500k',[P/'kernel-before','500000'])
 a=run('after-fixed500k',[P/'kernel-after','500000'])
 assert b.stderr==a.stderr, 'Root mismatch across actual500k pair'
 bm=json.loads(b.stdout);am=json.loads(a.stdout)
 R.update(status='PASS_ORACLES_VECTORS_AND_ONE_FIXED500K_PAIR',before=bm,after=am,root=b.stderr.strip(),latency_ratio_after_over_before=am['ms_per_root']/bm['ms_per_root'])
 save()
except BaseException as e:
 R.update(status='FAILED',error=repr(e));save();raise
