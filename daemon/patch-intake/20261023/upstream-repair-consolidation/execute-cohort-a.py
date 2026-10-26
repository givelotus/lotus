#!/usr/bin/env python3
"""One reviewed fold, with resumable Git state and exact tree checkpoints."""
import fcntl
import json
import os
from pathlib import Path
import subprocess

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
SOURCE = ROOT / 'daemon/worktrees/grok-progression-source'
BRANCH = 'consolidation/http-body-repair-20261023'
SHARED = 'consolidation/ecash-http-body-repair-20261023'
ENV = dict(os.environ, GIT_EDITOR='true')
COMMAND = ['git', '-C', str(SOURCE), '-c', 'user.email=213740+schancel@users.noreply.github.com']


def git(*args):
    return subprocess.check_output(COMMAND + list(args), text=True).strip()


def mutate(*args):
    with (OUT / 'COHORT-A-GIT.log').open('a') as log:
        result = subprocess.run(COMMAND + list(args), env=ENV, stdout=log, stderr=subprocess.STDOUT)
    if result.returncode:
        raise RuntimeError(f'Git stopped safely at {args}; resolve the recorded conflict, then rerun this script')


def write(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


def main():
    source_lock = (SOURCE / '.git/progression.lock').open('a')
    host_lock = (ROOT / 'daemon/.local-artifact-archive/benchmark-host.lock').open('a')
    for lock in (source_lock, host_lock):
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    preservation = json.loads((OUT / 'PRESERVATION.json').read_text())
    assert preservation['bundle_status'] == 'verified full closure, no prerequisite exclusion'
    rows = json.loads((OUT / 'INVENTORY.json').read_text())['commits']
    assert len(rows) == 531 and rows[85]['original_number'] == 86 and rows[97]['original_number'] == 98
    state_file = OUT / 'COHORT-A-STATE.json'
    if state_file.exists():
        state = json.loads(state_file.read_text())
        assert git('branch', '--show-current') == BRANCH
        if state['status'] == 'tree proofs passed; owner gate pending':
            print(state['status'])
            return
    else:
        assert not git('status', '--porcelain')
        mutate('switch', '-c', BRANCH, rows[84]['commit'])
        state = {'status': 'running', 'next_index': 85, 'phase': 'pick',
                 'mapping': {r['commit']: {'new_commit': r['commit'], 'tree_equal': True}
                             for r in rows[:85]}, 'checkpoints': []}
        write(state_file, state)
    repair = rows[97]['commit']
    repair_diff = OUT / 'COHORT-A-REPAIR-098.diff'
    if not repair_diff.exists():
        repair_diff.write_bytes(subprocess.check_output(COMMAND + ['diff', '--binary', repair + '^', repair]))

    def checkpoint(name, old):
        actual = git('rev-parse', 'HEAD^{tree}')
        expected = git('rev-parse', old + '^{tree}')
        if actual != expected:
            (OUT / 'FAILED-CHECKPOINT.diff').write_bytes(subprocess.check_output(
                COMMAND + ['diff', old, 'HEAD']))
            raise RuntimeError(f'{name} tree mismatch; promotion stopped: {expected} != {actual}')
        state['checkpoints'].append({'name': name, 'original': old, 'new_commit': git('rev-parse', 'HEAD'),
                                     'tree': actual, 'equal': True})
        print('TREE PASS', name, actual, flush=True)

    while state['next_index'] < len(rows):
        index = state['next_index']
        row = rows[index]
        old = row['commit']
        if index == 97:
            checkpoint('original repair98 position', old)
        else:
            if state['phase'] == 'pick':
                pending = subprocess.run(COMMAND + ['rev-parse', '--verify', 'CHERRY_PICK_HEAD'],
                                         capture_output=True, text=True)
                if pending.returncode == 0:
                    assert pending.stdout.strip() == old
                    assert not git('diff', '--name-only', '--diff-filter=U')
                    mutate('cherry-pick', '--continue')
                else:
                    assert not git('status', '--porcelain')
                    mutate('cherry-pick', old)
                state['phase'] = 'apply repair' if index == 85 else 'record'
                write(state_file, state)
            if index == 85 and state['phase'] == 'apply repair':
                # git apply leaves conflict stages without a cherry-pick that
                # would prevent amending the newly copied introducing owner.
                state['phase'] = 'finish repair'
                write(state_file, state)
                mutate('apply', '--3way', '--index', str(repair_diff))
            if index == 85 and state['phase'] == 'finish repair':
                assert not git('diff', '--name-only', '--diff-filter=U')
                message = git('show', '-s', '--format=%B', 'HEAD')
                message += '\n\nFolded-Repair: ' + repair + '\nHTTP response ownership and move consumers are supplied with Beast.\n'
                path = OUT / 'COHORT-A-OWNER-MESSAGE.txt'
                path.write_text(message)
                mutate('commit', '--amend', '--file', str(path))
                state['phase'] = 'record'
                write(state_file, state)
            current = git('rev-parse', 'HEAD')
            equal = git('rev-parse', old + '^{tree}') == git('rev-parse', current + '^{tree}')
            state['mapping'][old] = {'new_commit': current, 'tree_equal': equal,
                                      'disposition': 'body repair supplied early' if not equal else 'same tracked tree'}
            if index == 85:
                state['mapping'][repair] = {'new_commit': current, 'disposition': 'folded into Beast owner86; all4files retained'}
            if row['tier'] == 'ecash' and row['original_number'] == 378:
                checkpoint('shared endpoint', old)
                mutate('update-ref', 'refs/heads/' + SHARED, current)
            if row['tier'] == 'v2' and row['original_number'] == 153:
                checkpoint('native endpoint', old)
        state['next_index'] += 1
        state['phase'] = 'pick'
        write(state_file, state)
        if state['next_index'] % 25 == 0:
            print('REPLAYED', state['next_index'], 'of', len(rows), flush=True)
    assert len(state['mapping']) == 531
    assert int(git('rev-list', '--count', '1fb7db17..HEAD')) == 530
    assert int(git('rev-list', '--count', '1fb7db17..' + SHARED)) == 377
    state.update(status='tree proofs passed; owner gate pending', head=git('rev-parse', 'HEAD'),
                 shared_head=git('rev-parse', SHARED), shared_count=377, native_count=153,
                 intentional_exclusions=[])
    write(state_file, state)
    print(state['status'], flush=True)


if __name__ == '__main__':
    main()
