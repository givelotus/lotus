#!/usr/bin/env python3
"""Isolate the unbroadcast count fix without adding snapshot publication or readers."""
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
SOURCE = ROOT/'daemon/worktrees/grok-progression-source'
ARCHIVE = ROOT/'daemon/.local-artifact-archive/commit-regressions'

def git(*args, data=None, env=None):
    return subprocess.check_output(['git','-C',str(SOURCE),*args],input=data,env=env)

def main():
    assert not git('status','--porcelain').strip()
    plan = json.loads((OUT/'INPUT-STACK.json').read_text())
    entries = plan['stages']['ecash']['commits']
    base, getter_source = entries[28]['commit'],entries[29]['commit']
    header = 'src/txmempool.h'
    old = git('show',base+':'+header)
    supplied = git('show',getter_source+':'+header)
    begin = b'    /** Returns the unbroadcast count without copying the transaction IDs. */'
    end = b'    /** Returns whether a txid is in the unbroadcast set */'
    getter = supplied[supplied.index(begin):supplied.index(end)]
    assert b'GetUnbroadcastTxCount' not in old and old.count(end) == 1
    modified = {header:old.replace(end,getter+end)}
    rpc = 'src/rpc/mempool.cpp'
    old = git('show',base+':'+rpc)
    assert old.count(b'pool.GetUnbroadcastTxs().size()') == 1
    modified[rpc] = old.replace(b'pool.GetUnbroadcastTxs().size()',b'pool.GetUnbroadcastTxCount()')
    env = dict(os.environ,GIT_INDEX_FILE=str(ARCHIVE/'unbroadcast-count.index'))
    git('read-tree',base,env=env)
    for path,contents in modified.items():
        blob = git('hash-object','-w','--stdin',data=contents).strip().decode()
        git('update-index','--cacheinfo',f'100644,{blob},{path}',env=env)
    tree = git('write-tree',env=env).strip().decode()
    assert set(git('diff','--name-only',base,tree).decode().splitlines()) == set(modified)
    commit = git('-c','user.email=213740+schancel@users.noreply.github.com','commit-tree',tree,'-p',base,
                 '-m','rpc: count unbroadcast transactions without copying their IDs',
                 '-m','Reuse the exact caller-locked count accessor supplied by snapshot owner30 in the ordinary mempool-info RPC. This isolated control adds neither snapshot publication nor snapshot-backed reads. Preserve the full-set API for callers that need IDs.').strip().decode()
    git('update-ref','refs/heads/perf/unbroadcast-count-control-20261023',commit)
    (OUT/'CONTROL.diff').write_bytes(git('diff',base,commit))
    (OUT/'CONTROL.json').write_text(json.dumps(dict(status='isolated performance control, unintegrated',base=base,commit=commit,tree=tree,
        getter_source=getter_source,changes='Only count accessor and count-only RPC use; no snapshot machinery'),indent=2)+'\n')
    print(commit)

if __name__ == '__main__':
    main()
