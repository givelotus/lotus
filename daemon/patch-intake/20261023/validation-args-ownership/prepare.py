#!/usr/bin/env python3
"""Repair two early prerequisite placements without changing endpoint source trees."""
import copy
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
SOURCE = ROOT/'daemon/worktrees/grok-progression-source'
ARCHIVE = ROOT/'daemon/.local-artifact-archive/commit-regressions'
FILE = 'src/validation.cpp'
TEST = 'src/test/mempool_overlay_tests.cpp'
LEGACY_CASE = b'BOOST_AUTO_TEST_CASE(utxo_arena_reuses_imported_subtrees_and_invalidates_mutations) {'
NEXT_CASE = b'BOOST_AUTO_TEST_CASE(stacked_cow_overlays_and_chained_lookup)'

def git(*args, data=None, env=None):
    return subprocess.check_output(['git','-C',str(SOURCE),*args],input=data,env=env)

def main():
    assert not git('status','--porcelain').strip()
    bundles = [ROOT/'daemon/.local-artifact-archive/lotusd-published-source-20261023-full.bundle',
               ARCHIVE/'template-test-order-candidate.bundle', ARCHIVE/'perf-repaired-stack-candidate.bundle']
    preservation = []
    for bundle in bundles:
        p = subprocess.run(['git','-C',str(SOURCE),'bundle','verify',str(bundle)],capture_output=True,text=True,check=True)
        preservation.append(dict(bundle=str(bundle),verification=p.stdout+p.stderr))
    plan = json.loads((OUT/'INPUT-STACK.json').read_text())
    stages = plan['stages']
    assert stages['v2']['reviewed_reference_tip'] == '3cfb703183eb4134d3fbebfe862127450cd4c199'
    entries = stages['ecash']['commits'] + stages['v2']['commits']
    assert len(entries) == 531 and len(stages['ecash']['commits']) == 378
    assert entries[14]['commit'].startswith('695a294d38ea')
    candidate = copy.deepcopy(plan)
    outputs = candidate['stages']['ecash']['commits'] + candidate['stages']['v2']['commits']
    parent = stages['ecash']['input_commit']
    env = dict(os.environ,GIT_INDEX_FILE=str(ARCHIVE/'validation-args.index'))
    ledger = []
    for position,(entry,output) in enumerate(zip(entries,outputs),1):
        original = entry['commit']
        headers,message = git('cat-file','commit',original).split(b'\n\n',1)
        lines = headers.splitlines()
        assert sum(line.startswith(b'parent ') for line in lines) == 1
        assert not any(line.startswith((b'gpgsig ',b'mergetag ')) for line in lines)
        old_tree = lines[0].split()[1].decode()
        tree = old_tree
        if 15 <= position < 34:
            contents = git('show',original+':'+FILE)
            assert b'#include <common/args.h>' not in contents
            assert b'gArgs.GetIntArg("-testblockconnectpauseheight"' in contents
            blob = git('hash-object','-w','--stdin',data=b'#include <common/args.h>\n'+contents).strip().decode()
            git('read-tree',old_tree,env=env)
            git('update-index','--cacheinfo',f'100644,{blob},{FILE}',env=env)
            if position >= 19:
                contents = git('show',original+':'+TEST)
                assert contents.count(LEGACY_CASE) == 1 and contents.count(NEXT_CASE) == 1
                start,end = contents.index(LEGACY_CASE),contents.index(NEXT_CASE)
                # The entire regression requires the legacy SMT representation
                # introduced34. Restore identical test bytes there, not a
                # different native-coin fixture at an earlier boundary.
                contents = contents[:start]+contents[end:]
                blob = git('hash-object','-w','--stdin',data=contents).strip().decode()
                git('update-index','--cacheinfo',f'100644,{blob},{TEST}',env=env)
            tree = git('write-tree',env=env).strip().decode()
            expected_files = {FILE}
            if position >= 19:
                expected_files.add(TEST)
            assert set(git('diff','--name-only',old_tree,tree).decode().splitlines()) == expected_files
        if position == 15:
            message += b'\nOwnership repair: move the explicit common/args.h include from34 to this first regtest block-connect pause-hook caller. No endpoint source change.\n'
        if position == 19:
            message += b'\nOwnership repair: restore the intact imported-legacy-SMT regression at34 where its Output representation and state import support first exist. Other arena regressions remain here.\n'
        rewritten = [b'tree '+tree.encode() if line.startswith(b'tree ') else
                     b'parent '+parent.encode() if line.startswith(b'parent ') else line for line in lines]
        new = git('hash-object','-t','commit','-w','--stdin',data=b'\n'.join(rewritten)+b'\n\n'+message).strip().decode()
        output.update(commit=new,parents=[parent])
        ledger.append(dict(position=position,original=original,candidate=new,original_tree=old_tree,candidate_tree=tree,
                           disposition='Args include34→15; intact legacy SMT import test19→34; final assertions preserved' if 15 <= position < 34 else
                           'All tracked source, tests, build, configuration and documentation byte-identical'))
        parent = new
    assert ledger[377]['candidate_tree'] == ledger[377]['original_tree']
    assert ledger[-1]['candidate_tree'] == ledger[-1]['original_tree']
    assert int(git('rev-list','--count',stages['ecash']['input_commit']+'..'+parent)) == 531
    shared = ledger[377]['candidate']
    git('merge-base','--is-ancestor',shared,parent)
    for label,tip in (('ecash',shared),('v2',parent)):
        candidate['stages'][label]['reviewed_reference_tip'] = tip
        candidate['stages'][label]['review_status'] = 'include ownership candidate; prefix gate pending'
        git('update-ref',f'refs/benchmark/validation-args-{label}-20261023',tip)
    candidate['stages']['v2']['input_commit'] = shared
    for position in (15,19,34):
        commit = ledger[position-1]['candidate']
        (OUT/f'owner-{position:03}.diff').write_bytes(git('diff',commit+'^',commit,'--',FILE,TEST))
    (OUT/'CANDIDATE-STACK.json').write_text(json.dumps(candidate,indent=2)+'\n')
    (OUT/'LEDGER.json').write_text(json.dumps(dict(status='candidate only; endpoint trees identical; prefix gates pending',
        ownership_transfer=['Existing common/args.h include34→15 at first gArgs use',
                            'Whole legacy SMT import test19→34 at representation introduction; identical final test bytes and assertions'],preservation=preservation,
        shared_tree_equal=True,native_tree_equal=True,commits=ledger),indent=2)+'\n')
    print(json.dumps(dict(shared=shared,native=parent,shared_tree=ledger[377]['candidate_tree'],native_tree=ledger[-1]['candidate_tree'])))

if __name__ == '__main__':
    main()
