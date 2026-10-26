#!/usr/bin/env python3
"""Prepare a tree-preserving candidate; never update active daemon branches."""
import copy
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / 'daemon/worktrees/grok-progression-source'
OUT = Path(__file__).resolve().parent
INDEX = ROOT / 'daemon/.local-artifact-archive/commit-regressions/template-test-order.index'
FILE = 'src/test/mempool_tests.cpp'
EDITS = [
    (b'        const auto before_template = before->GetMiningTemplate().template_id;\n', b''),
    (b'            overlay.GetSpeculativeOverlay().GetTxCount(), after->mempool_size,\n'
     b'            after->GetMiningTemplate().template_id - before_template);',
     b'            overlay.GetSpeculativeOverlay().GetTxCount(), after->mempool_size);'),
]

def git(*args, data=None, env=None):
    return subprocess.check_output(['git', '-C', str(SOURCE), *args], input=data, env=env)

def main():
    plan = json.loads((OUT / 'INPUT-STACK.json').read_text())
    stages = plan['stages']
    commits = stages['ecash']['commits'] + stages['v2']['commits']
    assert len(stages['ecash']['commits']) == 378 and len(commits) == 531
    assert commits[43]['commit'].startswith('e3b996512777')
    assert commits[87]['commit'].startswith('6374e98f81e5')
    assert commits[-1]['commit'] == 'ef42f1ea59399923a57a9b813e3103c98cbcbc8d'
    assert not git('status', '--porcelain').strip()
    bundle = ROOT / 'daemon/.local-artifact-archive/lotusd-published-source-20261023-full.bundle'
    verification = git('bundle', 'verify', str(bundle)).decode()
    assert commits[-1]['commit'].encode() in git('bundle', 'list-heads', str(bundle))
    candidate = copy.deepcopy(plan)
    dest = candidate['stages']['ecash']['commits'] + candidate['stages']['v2']['commits']
    parent = stages['ecash']['input_commit']
    ledger = []
    env = dict(os.environ, GIT_INDEX_FILE=str(INDEX))
    for position, (original, output) in enumerate(zip(commits, dest), 1):
        old = original['commit']
        raw = git('cat-file', 'commit', old)
        headers, message = raw.split(b'\n\n', 1)
        lines = headers.splitlines()
        assert sum(line.startswith(b'parent ') for line in lines) == 1
        assert not any(line.startswith((b'gpgsig ', b'mergetag ')) for line in lines)
        old_tree = lines[0].split()[1].decode()
        tree = old_tree
        if 44 <= position < 88:
            contents = git('show', f'{old}:{FILE}')
            for before, after in EDITS:
                assert contents.count(before) == 1, (position, before)
                contents = contents.replace(before, after)
            blob = git('hash-object', '-w', '--stdin', data=contents).strip().decode()
            git('read-tree', old_tree, env=env)
            git('update-index', '--cacheinfo', f'100644,{blob},{FILE}', env=env)
            tree = git('write-tree', env=env).strip().decode()
            assert git('diff', '--name-only', old_tree, tree).decode().strip() == FILE
        rewritten = [b'tree ' + tree.encode() if line.startswith(b'tree ') else
                     b'parent ' + parent.encode() if line.startswith(b'parent ') else line
                     for line in lines]
        new = git('hash-object', '-t', 'commit', '-w', '--stdin',
                  data=b'\n'.join(rewritten)+b'\n\n'+message).strip().decode()
        output['commit'] = new
        output['parents'] = [parent]
        ledger.append(dict(position=position, original=old, candidate=new,
                           original_tree=old_tree, candidate_tree=tree,
                           disposition='template-id assertions deferred to owner88' if 44 <= position < 88
                           else 'all tracked source, tests, build, configuration and documentation identical'))
        parent = new
    assert ledger[377]['candidate_tree'] == ledger[377]['original_tree']
    assert ledger[-1]['candidate_tree'] == ledger[-1]['original_tree']
    git('update-ref', 'refs/benchmark/template-test-order-ecash-20261023', ledger[377]['candidate'])
    git('update-ref', 'refs/benchmark/template-test-order-v2-20261023', parent)
    candidate['stages']['ecash']['reviewed_reference_tip'] = ledger[377]['candidate']
    candidate['stages']['v2']['input_commit'] = ledger[377]['candidate']
    candidate['stages']['v2']['reviewed_reference_tip'] = parent
    for stage in ('ecash', 'v2'):
        candidate['stages'][stage]['review_status'] = 'test-order candidate; not promoted'
    for position in (44, 88):
        item = ledger[position-1]
        (OUT / f'owner-{position:03}-candidate.diff').write_bytes(
            git('diff', item['candidate']+'^', item['candidate'], '--', FILE))
    (OUT / 'CANDIDATE-STACK.json').write_text(json.dumps(candidate, indent=2)+'\n')
    (OUT / 'LEDGER.json').write_text(json.dumps(dict(
        status='candidate only; not integrated', preservation_bundle=str(bundle),
        bundle_verification=verification, source_changes='No production changes; two template-specific expressions moved44→88',
        shared_tree_equal=True, full_tree_equal=True, commits=ledger), indent=2)+'\n')
    print(json.dumps(dict(shared=ledger[377]['candidate'], native=parent,
                          shared_tree=ledger[377]['candidate_tree'], full_tree=ledger[-1]['candidate_tree'])))

if __name__ == '__main__':
    main()
