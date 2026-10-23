#!/usr/bin/env python3
"""Fold a verified fee-test precondition repair into its introducing owner."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
SOURCE = ROOT/'daemon/worktrees/grok-progression-source'
OLD_SHARED = '11d5c3a8d5888005900db0be2b9a03810d9a3046'
OLD_NATIVE = '303d41cae085b82a096aef54f6b88c855202337e'
OWNER = '2e735ad1bdbdb2e2d20ee92dd174e2bf1ca109c8'
SHARED = 'consolidation/ecash-relay-fee-precondition-20261023'
NATIVE = 'consolidation/native-relay-fee-precondition-20261023'
CMD = ['git','-C',str(SOURCE),'-c','user.email=213740+schancel@users.noreply.github.com']
ENV = dict(os.environ,GIT_EDITOR='true',GIT_SEQUENCE_EDITOR='true')
NATIVE_FIX_OWNER = '4371511fafee8c57b927a74b5cd4409cd381a5ac'
SHARED_PRECONDITION = '''        // A successful admission can update local policy. Each rejection
        // scenario must establish its own congestion-rate precondition.
        controller.SetRpcAdmissionRatePerKCu(9000, now);
        BOOST_REQUIRE_EQUAL(controller.GetRpcAdmissionRatePerKCu(now), 9000);
'''
NATIVE_DUPLICATE = '''        // Native mempool publication recomputes pressure after the prior RPC.
        // Re-establish this admission's deliberately congested policy sample.
        controller.SetRpcAdmissionRatePerKCu(9000, now);
'''


def git(*args, env=None):
    return subprocess.check_output(CMD+list(args),text=True,env=env).strip()


def change(*args):
    with (OUT/'FEE-PRECONDITION-GIT.log').open('a') as f:
        result=subprocess.run(CMD+list(args),env=ENV,stdout=f,stderr=subprocess.STDOUT)
    if result.returncode:
        raise RuntimeError(f'Stopped at{args}; inspect and resolve recorded conflicts before resume')


def save(state):
    path=OUT/'FEE-PRECONDITION-STATE.json'
    temporary=path.with_suffix('.tmp')
    temporary.write_text(json.dumps(state,indent=2)+'\n');temporary.replace(path)


def main():
    with (SOURCE/'.git/progression.lock').open('a') as source_lock, \
            (ROOT/'daemon/.local-artifact-archive/benchmark-host.lock').open('a') as host_lock:
        for lock in (source_lock,host_lock):fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        path=OUT/'FEE-PRECONDITION-STATE.json'
        if path.exists():
            state=json.loads(path.read_text())
            if state['status']!='running':print(state['status']);return
        else:
            receipt=json.loads((ROOT/'benchmark-results/20261023/relay-rank-shared-build/FEE-PRECONDITION-UNIT-RECEIPT.json').read_text())
            assert receipt['exit']==0 and not git('status','--porcelain')
            assert git('branch','--show-current')==SHARED
            assert git('rev-parse','HEAD')==receipt['source']
            ref='refs/backups/fee-precondition-20261023/fixup'
            existing=subprocess.run(CMD+['rev-parse','--verify',ref],capture_output=True,text=True)
            if existing.returncode==0:assert existing.stdout.strip()==receipt['source']
            else:change('update-ref',ref,receipt['source'],'0'*40)
            bundle=ROOT/'daemon/.local-artifact-archive/upstream-repair-consolidation-20261023/fee-precondition-fixup.bundle'
            if not bundle.exists():
                change('bundle','create',str(bundle),ref,'refs/backups/fee-precondition-20261023/native',
                       '^591a5fff70691a1d0c4eca54589b39f580e94e54')
            verify=subprocess.run(CMD+['bundle','verify',str(bundle)],capture_output=True,text=True,check=True)
            (OUT/'FEE-PRECONDITION-FIXUP-BUNDLE-VERIFY.txt').write_text(verify.stdout+verify.stderr)
            index=ROOT/'daemon/.local-artifact-archive/upstream-repair-consolidation-20261023/fee-native-expected.index'
            env=dict(os.environ,GIT_INDEX_FILE=str(index))
            git('read-tree',OLD_NATIVE,env=env)
            native=git('show',OLD_NATIVE+':src/test/policy_fee_tests.cpp')+'\n'
            anchor='    auto reject_without_insertion = [&](const char *id, Amount fee, bool cap_maximum) {\n'
            assert native.count(anchor)==1 and native.count(NATIVE_DUPLICATE)==1
            projected=native.replace(anchor,anchor+SHARED_PRECONDITION).replace(NATIVE_DUPLICATE,'')
            blob=subprocess.check_output(CMD+['hash-object','-w','--stdin'],input=projected,text=True).strip()
            git('update-index','--cacheinfo','100644,'+blob+',src/test/policy_fee_tests.cpp',env=env)
            expected_native=git('write-tree',env=env)
            state=dict(status='running',phase='squash',next_index=0,mapping={},
                       fixup_source=receipt['source'],expected_shared_tree=receipt['tree'],
                       expected_native_tree=expected_native,bundle=str(bundle.relative_to(ROOT)),
                       bundle_sha256=hashlib.file_digest(bundle.open('rb'),'sha256').hexdigest(),
                       closure_prerequisite='PRESERVATION.json full input bundle',intentional_exclusions=[])
            save(state)
        if state['phase']=='squash':
            assert git('branch','--show-current')==SHARED
            if git('rev-parse','HEAD')==state['fixup_source']:
                change('-c','rebase.updateRefs=false','rebase','-i','--autosquash','--no-update-refs',OWNER+'^')
            assert git('rev-parse','HEAD^{tree}')==state['expected_shared_tree']
            before=git('rev-list','--reverse','1fb7db17..'+OLD_SHARED).splitlines()
            after=git('rev-list','--reverse','1fb7db17..HEAD').splitlines()
            assert len(before)==len(after)==378
            for old,new in zip(before,after):
                assert git('show','-s','--format=%s',old)==git('show','-s','--format=%s',new)
                state['mapping'][old]=dict(new_commit=new,disposition='same owner; fee-test precondition belongs to introducing RPC feature')
            assert not any(s.startswith('fixup! ') for s in git('log','--format=%s','1fb7db17..HEAD').splitlines())
            state.update(shared_head=git('rev-parse','HEAD'),phase='native');save(state)
            change('switch','--no-overwrite-ignore','-c',NATIVE,state['shared_head'])
        assert git('branch','--show-current')==NATIVE
        tail=git('rev-list','--reverse',OLD_SHARED+'..'+OLD_NATIVE).splitlines()
        assert len(tail)==153
        while state['next_index']<len(tail):
            old=tail[state['next_index']]
            pending=subprocess.run(CMD+['rev-parse','--verify','CHERRY_PICK_HEAD'],capture_output=True,text=True)
            if pending.returncode==0:
                assert pending.stdout.strip()==old and not git('diff','--name-only','--diff-filter=U')
                change('cherry-pick','--continue')
            else:
                assert not git('status','--porcelain');change('cherry-pick',old)
            if old==NATIVE_FIX_OWNER:
                file=SOURCE/'src/test/policy_fee_tests.cpp'
                text=file.read_text()
                assert text.count(NATIVE_DUPLICATE)==1 and text.count(SHARED_PRECONDITION)==1
                file.write_text(text.replace(NATIVE_DUPLICATE,''))
                change('add','src/test/policy_fee_tests.cpp')
                change('commit','--amend','--no-edit')
            state['mapping'][old]=dict(new_commit=git('rev-parse','HEAD'),disposition=
                'native fixture retained; congestion precondition now supplied by shared RPC owner' if old==NATIVE_FIX_OWNER else 'native adapter retained')
            state['next_index']+=1;save(state)
        assert git('rev-parse','HEAD^{tree}')==state['expected_native_tree']
        assert git('diff','--name-only',OLD_NATIVE,'HEAD')=='src/test/policy_fee_tests.cpp'
        state.update(status='shared full gate retained by exact tree; native test gate pending',
                     native_head=git('rev-parse','HEAD'),native_tree=git('rev-parse','HEAD^{tree}'),
                     production_unchanged=True,shared_count=378,native_count=153)
        save(state);print(state['status'],state['native_head'],flush=True)


if __name__=='__main__':main()
