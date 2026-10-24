#!/usr/bin/env python3
"""Move two instrumentation lines to their introducing metrics owner."""
import fcntl,json,os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];OUT=Path(__file__).resolve().parent;SOURCE=ROOT/'daemon/worktrees/grok-progression-source'
CMD=['git','-C',str(SOURCE),'-c','user.email=213740+schancel@users.noreply.github.com'];ENV=dict(os.environ,GIT_EDITOR='true',GIT_SEQUENCE_EDITOR='true')
def git(*a):return subprocess.check_output(CMD+list(a),text=True).strip()
def run(*a):
 with (OUT/'PIPELINE-TIMING-ADAPTER-GIT.log').open('a') as f:subprocess.run(CMD+list(a),env=ENV,stdout=f,stderr=subprocess.STDOUT,check=True)
def main():
 with (SOURCE/'.git/progression.lock').open('a') as lock,(ROOT/'daemon/.local-artifact-archive/benchmark-host.lock').open('a') as host:
  for f in (lock,host):fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
  path=OUT/'PIPELINE-TIMING-ADAPTER-STATE.json'
  if not path.exists():
   assert not git('status','--porcelain')
   native='b8239f40bb204e4d7a81984578f8fb16338fb9e6';shared='ff92ae16a8ee47b699d62821724c8497dd374550'
   assert git('rev-parse','HEAD^{tree}')==git('rev-parse',native+'^{tree}')
   ref='refs/backups/pipeline-timing-adapter-20261023/input';run('update-ref',ref,git('rev-parse','HEAD'),'0'*40)
   bundle=ROOT/'daemon/.local-artifact-archive/upstream-repair-consolidation-20261023/pipeline-timing-adapter-input.bundle';run('bundle','create',str(bundle),ref,'^50bfba9430^');run('bundle','verify',str(bundle))
   state=dict(status='running',old_native=native,old_shared=shared,input=git('rev-parse','HEAD'),expected_native_tree=git('rev-parse',native+'^{tree}'),expected_shared_tree=git('rev-parse',shared+'^{tree}'),review='Self-review: owner268 compile found AdmissionLockTimer absent until metrics owner98d864. Move waiting timestamp plus timer construction to that metrics owner. Pure context placement; final shared/native trees must remain exact. First-fold history and both adapter fixups bundled; no original refs/pins changed.')
   path.write_text(json.dumps(state,indent=2)+'\n')
   run('-c','rebase.updateRefs=false','rebase','-i','--autosquash','--no-update-refs','50bfba9430^')
  else:state=json.loads(path.read_text())
  assert not git('status','--porcelain') and not (SOURCE/'.git/rebase-merge').exists()
  old=git('rev-list','--reverse','1fb7db17..'+state['old_native']).splitlines();new=git('rev-list','--reverse','1fb7db17..HEAD').splitlines();assert len(old)==len(new)==531
  assert git('log','--reverse','--format=%s','1fb7db17..'+state['old_native'])==git('log','--reverse','--format=%s','1fb7db17..HEAD')
  assert git('rev-parse','HEAD^{tree}')==state['expected_native_tree'] and git('rev-parse',new[377]+'^{tree}')==state['expected_shared_tree']
  run('branch','consolidation/ecash-peer-timer-placement-20261023',new[377])
  state.update(status='exact shared/native trees PASS; owner/boundary gates pending',mapping=dict(zip(old,new)),shared_head=new[377],native_head=git('rev-parse','HEAD'),owner_head=new[267]);path.write_text(json.dumps(state,indent=2)+'\n');print(state['status'],state['owner_head'],state['shared_head'],state['native_head'])
if __name__=='__main__':main()
