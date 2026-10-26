#!/usr/bin/env python3
"""Fold preserved peer pipeline repairs; exact shared/native trees required."""
import fcntl,json,os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
OUT=Path(__file__).resolve().parent
SOURCE=ROOT/'daemon/worktrees/grok-progression-source'
GIT=['git','-C',str(SOURCE),'-c','user.email=213740+schancel@users.noreply.github.com']
ENV=dict(os.environ,GIT_EDITOR='true',GIT_SEQUENCE_EDITOR='true')
def git(*args):return subprocess.check_output(GIT+list(args),text=True).strip()
def change(*args):
    with (OUT/'PIPELINE-FOLD-GIT.log').open('a') as f:
        subprocess.run(GIT+list(args),env=ENV,stdout=f,stderr=subprocess.STDOUT,check=True)
def save(d):(OUT/'PIPELINE-FOLD-STATE.json').write_text(json.dumps(d,indent=2)+'\n')
def main():
    plan=json.loads((OUT/'PIPELINE-FOLD-PLAN.json').read_text())
    with (SOURCE/'.git/progression.lock').open('a') as source_lock, (ROOT/'daemon/.local-artifact-archive/benchmark-host.lock').open('a') as host_lock:
        for lock in (source_lock,host_lock):fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        state_path=OUT/'PIPELINE-FOLD-STATE.json'
        if not state_path.exists():
            assert not git('status','--porcelain')
            assert git('rev-parse','HEAD')==plan['input_head']
            gate=json.loads((ROOT/'benchmark-results/20261023/native-shorttx-retained-budget-lifetime-build/ALL-NATIVE-UNIT-RECEIPT.json').read_text())
            assert gate['exit']==0 and gate['source']==plan['input_head']
            change('bundle','verify',str(ROOT/plan['bundle']))
            change('switch','--no-overwrite-ignore','-c','consolidation/native-peer-pipeline-20261023',plan['input_head'])
            state=dict(status='running',phase='rebase',plan=plan)
            save(state)
            change('-c','rebase.updateRefs=false','rebase','-i','--autosquash','--no-update-refs',plan['shared_owner']+'^')
        else:
            state=json.loads(state_path.read_text())
            if state['status']!='running':print(state['status']);return
            assert not git('status','--porcelain'), 'Resolve conflict then continue the existing rebase; do not restart'
            assert not (SOURCE/'.git/rebase-merge').exists(), 'Continue the existing rebase before final audit'
        old=git('rev-list','--reverse','1fb7db17..'+plan['old_native']).splitlines()
        new=git('rev-list','--reverse','1fb7db17..HEAD').splitlines()
        assert len(old)==len(new)==531
        old_subjects=git('log','--reverse','--format=%s','1fb7db17..'+plan['old_native']).splitlines()
        new_subjects=git('log','--reverse','--format=%s','1fb7db17..HEAD').splitlines()
        assert old_subjects==new_subjects
        assert git('rev-parse','HEAD^{tree}')==plan['expected_native_tree']
        shared=new[377]
        assert git('rev-parse',shared+'^{tree}')==plan['expected_shared_tree']
        change('branch','consolidation/ecash-peer-pipeline-20261023',shared)
        mapping={a:dict(new_commit=b,disposition='retained logical owner') for a,b in zip(old,new)}
        for owner in [plan['shared_owner'],plan['native_fixture_owner'],plan['native_warm_owner']]:mapping[owner]['disposition']='retained owner plus explicitly listed pipeline repairs'
        state.update(status='exact endpoint trees PASS; boundary gates pending',phase='gates',shared_head=shared,native_head=git('rev-parse','HEAD'),mapping=mapping,shared_count=378,native_count=153)
        save(state);print(state['status'],state['shared_head'],state['native_head'])
if __name__=='__main__':main()
