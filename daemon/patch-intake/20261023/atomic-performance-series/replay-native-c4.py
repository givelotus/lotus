#!/usr/bin/env python3
"""Replay native owners with explicit, hash-guarded shared executor adapters."""
import fcntl,hashlib,json,os,re,subprocess
from pathlib import Path
from native_c4_transform import validation
ROOT=Path(__file__).resolve().parents[4];OUT=Path(__file__).resolve().parent;SOURCE=ROOT/'daemon/worktrees/grok-progression-source';GIT=['git','-C',str(SOURCE),'-c','user.email=213740+schancel@users.noreply.github.com'];ENV=dict(os.environ,GIT_EDITOR='true',GIT_SEQUENCE_EDITOR='true')
def git(*a):return subprocess.check_output(GIT+list(a),text=True).strip()
def raw(ref,path):return subprocess.check_output(GIT+['show',ref+':'+path],text=True)
def run(*a,check=True):
 with (OUT/'COMMIT4-NATIVE-REPLAY-GIT.log').open('a') as f:return subprocess.run(GIT+list(a),env=ENV,stdout=f,stderr=subprocess.STDOUT,check=check)
def save(s):(OUT/'COMMIT4-NATIVE-REPLAY-STATE.json').write_text(json.dumps(s,indent=2)+'\n')
def subtree(text):
 a=text.index('Hash ParallelTransactionSubtreeA(');b=text.index('\nHash TransactionIdentity(',a);part=text[a:b];old='    static util::ParallelRangeExecutor executor;\n    executor.Run(count, 1,';assert part.count(old)==1;part=part.replace(old,'    util::GetParallelRangeExecutor().Run(count, 1,',1);part,n=re.subn(r'(?m)^    \}\);$','    }, /*max_participants=*/8);',part);assert n==1;return text[:a]+part+text[b:]
def project(old,paths):
 expected=validation(raw(old,'src/validation.cpp'));p=SOURCE/'src/validation.cpp'
 if p.read_text()!=expected:p.write_text(expected);paths.append('src/validation.cpp')
 if old=='c78796a2c7c5c3dc8166e6b68e0c9130ce0d0a64':
  p=SOURCE/'src/lotus_v2/commitment.cpp';expected=subtree(raw(old,'src/lotus_v2/commitment.cpp'))
  if p.read_text()!=expected:p.write_text(expected);paths.append('src/lotus_v2/commitment.cpp')
def main():
 with (SOURCE/'.git/progression.lock').open('a') as sl,(ROOT/'daemon/.local-artifact-archive/benchmark-host.lock').open('a') as hl:
  for lock in (sl,hl):fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  plan=json.loads((OUT/'COMMIT4-NATIVE-REPLAY-PLAN.json').read_text());path=OUT/'COMMIT4-NATIVE-REPLAY-STATE.json'
  if not path.exists():
   assert not git('status','--porcelain') and git('rev-parse','HEAD')==plan['new_shared'];run('bundle','verify',str(ROOT/plan['input_bundle']));run('switch','--no-overwrite-ignore','-c','perf/native-atomic-through4-20261023',plan['new_shared']);state=dict(status='running',index=0,phase='pick',plan=plan,mapping={},adapters=[]);save(state)
  else:state=json.loads(path.read_text())
  if state['status']!='running':print(state['status']);return
  old_commits=git('rev-list','--reverse',plan['old_shared']+'..'+plan['old_native']).splitlines();assert len(old_commits)==154
  while state['index']<len(old_commits):
   old=old_commits[state['index']];state['old']=old;save(state)
   if state['phase']=='pick':
    assert not git('status','--porcelain');result=run('cherry-pick',old,check=False)
    if result.returncode:
     assert git('rev-parse','CHERRY_PICK_HEAD')==old
     conflicts=git('diff','--name-only','--diff-filter=U').splitlines();assert conflicts and set(conflicts)<={'src/validation.cpp','src/rpc/mempool.cpp'},conflicts
     if 'src/validation.cpp' in conflicts:(SOURCE/'src/validation.cpp').write_text(validation(raw(old,'src/validation.cpp')))
     if 'src/rpc/mempool.cpp' in conflicts:
      assert old=='c6ec6c37f18c77e602939052bd77719049bcccdb';(SOURCE/'src/rpc/mempool.cpp').write_text(raw(old,'src/rpc/mempool.cpp'))
     run('add',*conflicts);assert not git('diff','--name-only','--diff-filter=U');run('cherry-pick','--continue');state['adapters'].append(dict(old=old,kind='three-way API conflict resolved from same-owner tree with reviewed runtime projection',files=conflicts))
    state['phase']='adapt';save(state)
   changed=[];project(old,changed)
   if changed:
    run('add',*changed);run('commit','--fixup='+git('rev-parse','HEAD'));run('-c','rebase.updateRefs=false','rebase','-i','--autosquash','--no-update-refs','HEAD~2');state['adapters'].append(dict(old=old,kind='native owner runtime API adapter, all other original source retained',files=changed))
   assert (SOURCE/'src/validation.cpp').read_text()==validation(raw(old,'src/validation.cpp'))
   state['mapping'][old]=dict(new_commit=git('rev-parse','HEAD'),validation_input_sha256=hashlib.sha256(raw(old,'src/validation.cpp').encode()).hexdigest(),validation_output_sha256=hashlib.sha256((SOURCE/'src/validation.cpp').read_bytes()).hexdigest())
   state['index']+=1;state['phase']='pick';save(state)
  assert git('rev-parse','HEAD^{tree}')==plan['expected_native_tree']
  assert len(git('rev-list',plan['new_shared']+'..HEAD').splitlines())==154
  assert git('log','--reverse','--format=%s',plan['new_shared']+'..HEAD')==git('log','--reverse','--format=%s',plan['old_shared']+'..'+plan['old_native'])
  assert git('diff','--name-only',plan['old_native'],'HEAD').splitlines()==plan['allowed_native_changes']
  state.update(status='exact reviewed nativeC4 tree PASS;154owners retained; prefix/endpoint gates pending',native=git('rev-parse','HEAD'),native_tree=git('rev-parse','HEAD^{tree}'));save(state);print(state['status'],state['native'])
if __name__=='__main__':main()
