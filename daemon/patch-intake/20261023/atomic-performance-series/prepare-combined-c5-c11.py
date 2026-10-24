#!/usr/bin/env python3
"""Preserve and append gated features; never rewrites an existing ref."""
from pathlib import Path
import fcntl, hashlib, json, os, subprocess, tempfile
ROOT = Path(__file__).resolve().parents[4]
SRC = ROOT / 'daemon/worktrees/grok-progression-source'
OUT = Path(__file__).resolve().parent
PLAN = json.loads((OUT/'COMBINED-C5-C11-PLAN.json').read_text())
def git(*args, data=None, env=None):
    return subprocess.check_output(['git','-C',str(SRC),*args],input=data,env=env)
def text(*args): return git(*args).decode().strip()
def record(name,value): (OUT/name).write_text(json.dumps(value,indent=2)+'\n')
lockpath = Path(text('rev-parse','--git-path','progression.lock'))
if not lockpath.is_absolute(): lockpath=SRC/lockpath
with lockpath.open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    assert not text('status','--porcelain','--untracked-files=no'), 'Dirty source'
    assert text('rev-parse','HEAD')==PLAN['base'], 'Unexpected HEAD'
    assert text('rev-parse','HEAD^{tree}')==PLAN['base_tree']
    assert text('rev-parse','8b55e7c8de373d2097da1ebacfcf14fd1098d046^{tree}')==PLAN['base_tree']
    fixture,c5,c11=PLAN['commits']
    duplicate=text('rev-parse',c11+'^')
    assert git('diff',fixture+'^',fixture,'--')==git('diff',duplicate+'^',duplicate,'--'), 'Fixture mismatch'
    branch='perf/native-combined-c5-c11-20261023'
    assert subprocess.run(['git','-C',str(SRC),'show-ref','--verify','--quiet','refs/heads/'+branch]).returncode==1, 'Branch exists; inspect prior state'
    archive=ROOT/'daemon/.local-artifact-archive/combined-c5-c11-20261023'
    archive.mkdir(parents=True,exist_ok=True)
    refs=[]
    for label,sha in [('base',PLAN['base']),('c5',c5),('c11',c11)]:
        ref='refs/backup/combined-c5-c11-20261023-'+label
        subprocess.check_call(['git','-C',str(SRC),'update-ref',ref,sha,'0'*40])
        refs.append(ref)
    bundle=archive/'complete-input-history.bundle'
    assert not bundle.exists(), 'Preservation output exists; inspect it'
    git('bundle','create',str(bundle),*refs)
    verification=git('bundle','verify',str(bundle)).decode()
    record('COMBINED-C5-C11-PRESERVATION.json',{'bundle':str(bundle.relative_to(ROOT)),'sha256':hashlib.sha256(bundle.read_bytes()).hexdigest(),'verification':verification,'input_refs':dict(zip(refs,[PLAN['base'],c5,c11])),'dirty_tracked_source':False})
    with tempfile.TemporaryDirectory(prefix='combined-index-',dir=archive) as td:
        env=os.environ.copy();env['GIT_INDEX_FILE']=str(Path(td)/'index')
        git('read-tree',c5,env=env)
        feature=git('diff','--binary',c11+'^',c11,'--')
        git('apply','--cached','--check','-',data=feature,env=env)
        git('apply','--cached','-',data=feature,env=env)
        expected=git('write-tree',env=env).decode().strip()
    record('COMBINED-C5-C11-EXPECTED.json',{'expected_tree':expected,'method':'isolated index: C5 tree + exact C11 parent-to-feature diff','c11_diff_sha256':hashlib.sha256(feature).hexdigest(),'duplicate_fixture':duplicate})
    git('switch','-c',branch)
    ledger=[]
    env=os.environ.copy(); env.update(GIT_COMMITTER_NAME='Shammah Chancellor',GIT_COMMITTER_EMAIL='213740+schancel@users.noreply.github.com')
    for old in [fixture,c5,c11]:
        git('cherry-pick',old,env=env)
        new=text('rev-parse','HEAD');tree=text('rev-parse','HEAD^{tree}')
        if old!=c11: assert tree==text('rev-parse',old+'^{tree}'), 'Unexpected intermediate tree'
        ledger.append({'original':old,'new':new,'tree':tree})
        record('COMBINED-C5-C11-LEDGER.json',ledger)
    assert text('rev-parse','HEAD^{tree}')==expected, 'Combined tree mismatch'
    assert not text('status','--porcelain','--untracked-files=no')
    files=text('diff','--name-only',PLAN['base'],'HEAD').splitlines()
    hashes={p:hashlib.sha256((SRC/p).read_bytes()).hexdigest() for p in files}
    result={'status':'APPEND/TREE CHECK PASS; combined build/tests/benchmark NOT RUN','branch':branch,'head':text('rev-parse','HEAD'),'tree':expected,'ledger':ledger,'source_sha256':hashes,'original_refs_preserved':refs,'pins_promoted':False}
    record('COMBINED-C5-C11-RESULT.json',result)
    print(json.dumps(result,indent=2))
