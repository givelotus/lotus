#!/usr/bin/env python3
"""Separate the cheap count fix and pair snapshot publication with its consumers.

Use preserved Git trees and a private index. No worktree, mailbox, source file,
active branch or submodule pin is modified. Final shared/native trees must match.
"""
import copy
import hashlib
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
SOURCE = ROOT/'daemon/worktrees/grok-progression-source'
ARCHIVE = ROOT/'daemon/.local-artifact-archive/commit-regressions'
CONTROL = 'e4332caa231961103cd1418d4327101bf0713992'


def git(*args, data=None, env=None):
    return subprocess.check_output(['git', '-C', str(SOURCE), *args], input=data, env=env)


def main():
    assert not git('status', '--porcelain').strip()
    plan = json.loads((OUT/'INPUT-STACK.json').read_text())
    entries = plan['stages']['ecash']['commits'] + plan['stages']['v2']['commits']
    assert len(entries) == 531
    assert plan['stages']['ecash']['reviewed_reference_tip'].startswith('4d07d836')
    preservation = []
    for name in ('snapshot-prefix-test-owner.bundle', 'unbroadcast-count-control.bundle'):
        path = ARCHIVE/name
        check = subprocess.run(['git', '-C', str(SOURCE), 'bundle', 'verify', str(path)],
                               capture_output=True, text=True, check=True)
        preservation.append(dict(bundle=str(path), sha256=hashlib.file_digest(path.open('rb'), 'sha256').hexdigest(),
                                 verification=check.stdout+check.stderr))

    # Reuse the tested control's exact bytes in each older prefix. These two
    # transformations must vanish completely at the original snapshot consumer.
    header, rpc = 'src/txmempool.h', 'src/rpc/mempool.cpp'
    supplied = git('show', CONTROL+':'+header)
    begin = b'    /** Returns the unbroadcast count without copying the transaction IDs. */'
    end = b'    /** Returns whether a txid is in the unbroadcast set */'
    getter = supplied[supplied.index(begin):supplied.index(end)]
    index_env = dict(os.environ, GIT_INDEX_FILE=str(ARCHIVE/'snapshot-count-order.index'))

    def count_tree(commit):
        git('read-tree', commit, env=index_env)
        contents = git('show', commit+':'+header)
        assert b'GetUnbroadcastTxCount' not in contents and contents.count(end) == 1
        modified = {header: contents.replace(end, getter+end)}
        contents = git('show', commit+':'+rpc)
        assert contents.count(b'pool.GetUnbroadcastTxs().size()') == 1
        modified[rpc] = contents.replace(b'pool.GetUnbroadcastTxs().size()', b'pool.GetUnbroadcastTxCount()')
        for path, contents in modified.items():
            blob = git('hash-object', '-w', '--stdin', data=contents).strip().decode()
            git('update-index', '--cacheinfo', f'100644,{blob},{path}', env=index_env)
        tree = git('write-tree', env=index_env).strip().decode()
        assert set(git('diff', '--name-only', commit, tree).decode().splitlines()) == {header, rpc}
        return tree

    result = copy.deepcopy(plan)
    outputs, ledger = [], []
    parent = plan['stages']['ecash']['input_commit']

    def emit(source, tree, old_positions, disposition, message=None):
        nonlocal parent
        headers, original_message = git('cat-file', 'commit', source).split(b'\n\n', 1)
        lines = headers.splitlines()
        assert sum(line.startswith(b'parent ') for line in lines) == 1
        assert not any(line.startswith((b'gpgsig ', b'mergetag ')) for line in lines)
        rewritten = [b'tree '+tree.encode() if line.startswith(b'tree ') else
                     b'parent '+parent.encode() if line.startswith(b'parent ') else line for line in lines]
        body = original_message if message is None else message
        commit = git('hash-object', '-t', 'commit', '-w', '--stdin',
                     data=b'\n'.join(rewritten)+b'\n\n'+body).strip().decode()
        outputs.append(dict(commit=commit, parents=[parent], subject=body.splitlines()[0].decode()))
        ledger.append(dict(new_position=len(outputs), old_positions=old_positions,
                           old_commits=[entries[n-1]['commit'] for n in old_positions],
                           candidate=commit, candidate_tree=tree, disposition=disposition))
        parent = commit

    for position, entry in enumerate(entries, 1):
        original = entry['commit']
        old_tree = git('rev-parse', original+'^{tree}').strip().decode()
        if position == 30:
            continue
        if position == 31:
            producer = git('show', '-s', '--format=%B', entries[29]['commit'])
            consumer = git('show', '-s', '--format=%B', original)
            body = (b'rpc: publish immutable snapshots and serve chain and mempool reads\n\n'
                    b'Keep publication and its read consumers in one independently useful feature. '
                    b'The count accessor is supplied by the earlier standalone RPC count fix. '
                    b'All source, tests, build and configuration changes from both owners survive.\n\n'
                    b'Original producer message:\n'+producer+b'\nOriginal consumer message:\n'+consumer)
            emit(original, old_tree, [30, 31], 'Complete producer/consumer union; tree identical to original31', body)
        else:
            tree = count_tree(original) if 3 <= position <= 29 else old_tree
            emit(original, tree, [position], 'Only exact count-control adaptation' if tree != old_tree else 'Tracked tree identical')
        if position == 2:
            emit(CONTROL, count_tree(original), [], 'Standalone count fix; exact accessor from original30 and tested legacy RPC adapter')
    assert len(outputs) == 531
    assert int(git('rev-list', '--count', plan['stages']['ecash']['input_commit']+'..'+parent)) == 531
    # Every original owner is accounted for once, including both merged owners.
    assert sorted(n for row in ledger for n in row['old_positions']) == list(range(1, 532))
    for position in range(31, 532):
        assert ledger[position-1]['candidate_tree'] == git('rev-parse', entries[position-1]['commit']+'^{tree}').strip().decode()
    assert ledger[29]['candidate_tree'] == git('rev-parse', CONTROL+'^{tree}').strip().decode()
    shared = outputs[377]['commit']
    for label, commits, tip in (('ecash', outputs[:378], shared), ('v2', outputs[378:], parent)):
        stage = result['stages'][label]
        stage.update(commits=commits, reviewed_reference_tip=tip, review_status='count/snapshot ownership candidate; gates pending')
        git('update-ref', f'refs/benchmark/snapshot-count-{label}-20261023', tip)
    result['stages']['v2']['input_commit'] = shared
    for position in (3, 30, 31):
        commit = outputs[position-1]['commit']
        (OUT/f'owner-{position:03}.diff').write_bytes(git('diff', commit+'^', commit))
    (OUT/'CANDIDATE-STACK.json').write_text(json.dumps(result, indent=2)+'\n')
    (OUT/'LEDGER.json').write_text(json.dumps(dict(status='candidate only; gates pending', preservation=preservation,
        intentional_exclusions=[], shared_tree_equal=True, native_tree_equal=True,
        transformations=['Count-only fix at new3; two-file explicit adaptations through new30',
                         'Original30+31 merged at new31, with all later trees identical'], commits=ledger), indent=2)+'\n')
    print(json.dumps(dict(shared=shared, native=parent, count_commit=outputs[2]['commit'],
                          snapshot_commit=outputs[30]['commit'], shared_tree=ledger[377]['candidate_tree'],
                          native_tree=ledger[-1]['candidate_tree'])))


if __name__ == '__main__':
    main()
