#!/usr/bin/env python3
"""Place the measured relay optimization below V2, preserving its native tree."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
SOURCE = ROOT / 'daemon/worktrees/grok-progression-source'
SHARED_INPUT = '8267586b0d74d4bc4a32a5f0282f299ecbeaef5e'
NATIVE_INPUT = '4c2007d09211113f9d2ce459e1787aa5b582b4bb'
FEATURE = '4278a1fbb9ac0f90ef6ce9dbcdc783761010230a'
SHARED = 'consolidation/ecash-relay-rank-20261023'
NATIVE = 'consolidation/relay-rank-shared-20261023'
COMMAND = ['git', '-C', str(SOURCE), '-c', 'user.email=213740+schancel@users.noreply.github.com']


def git(*args):
    return subprocess.check_output(COMMAND + list(args), text=True).strip()


def mutate(*args):
    with (OUT / 'RELAY-SHARED-GIT.log').open('a') as log:
        result = subprocess.run(COMMAND + list(args), stdout=log, stderr=subprocess.STDOUT,
                                env=dict(os.environ, GIT_EDITOR='true'))
    if result.returncode:
        raise RuntimeError(f'Stopped safely at {args}; inspect the conflict, preserve all owners, then resume')


def write(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2)+'\n')
    temporary.replace(path)


def main():
    with (SOURCE / '.git/progression.lock').open('a') as source_lock, \
            (ROOT / 'daemon/.local-artifact-archive/benchmark-host.lock').open('a') as host_lock:
        for lock in (source_lock, host_lock):
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        state_path = OUT / 'RELAY-SHARED-STATE.json'
        if state_path.exists():
            state = json.loads(state_path.read_text())
            if state['status'] != 'running':
                print(state['status'])
                return
        else:
            assert not git('status', '--porcelain')
            for name, sha in [('shared', SHARED_INPUT), ('native', NATIVE_INPUT), ('feature', FEATURE)]:
                ref = 'refs/backups/relay-shared-placement-20261023/' + name
                old = subprocess.run(COMMAND + ['rev-parse', '--verify', ref], capture_output=True, text=True)
                if old.returncode == 0:
                    assert old.stdout.strip() == sha
                else:
                    mutate('update-ref', ref, sha, '0'*40)
            bundle = ROOT / 'daemon/.local-artifact-archive/upstream-repair-consolidation-20261023/relay-placement-input.bundle'
            assert not bundle.exists()
            mutate('bundle', 'create', str(bundle),
                   'refs/backups/relay-shared-placement-20261023/feature',
                   'refs/backups/relay-shared-placement-20261023/shared',
                   '^591a5fff70691a1d0c4eca54589b39f580e94e54')
            check = subprocess.run(COMMAND + ['bundle', 'verify', str(bundle)], capture_output=True, text=True, check=True)
            (OUT / 'RELAY-SHARED-BUNDLE-VERIFY.txt').write_text(check.stdout + check.stderr)
            # The excluded ancestor and its full closure are in the already
            # verified input-full.bundle, retained unchanged with original refs.
            original = json.loads((OUT / 'PRESERVATION.json').read_text())
            assert original['bundle_status'] == 'verified full closure, no prerequisite exclusion'
            original_bundle = ROOT / original['full_bundle']
            with original_bundle.open('rb') as stream:
                assert hashlib.file_digest(stream, 'sha256').hexdigest() == original['full_bundle_sha256']
            (OUT / 'relay-rank-native.mbox').write_bytes(subprocess.check_output(
                COMMAND + ['format-patch', '--stdout', '-1', FEATURE]))
            state = dict(status='running', phase='shared', next_index=0, mapping={},
                         inputs=dict(shared=SHARED_INPUT, native=NATIVE_INPUT, feature=FEATURE),
                         bundle=str(bundle.relative_to(ROOT)),
                         bundle_sha256=hashlib.file_digest(bundle.open('rb'), 'sha256').hexdigest(),
                         full_closure_prerequisite=original['full_bundle'], intentional_exclusions=[])
            write(state_path, state)
            mutate('switch', '--no-overwrite-ignore', '-c', SHARED, SHARED_INPUT)
        if state['phase'] == 'shared':
            assert git('branch', '--show-current') == SHARED
            pending = subprocess.run(COMMAND + ['rev-parse', '--verify', 'CHERRY_PICK_HEAD'], capture_output=True, text=True)
            if pending.returncode == 0:
                assert pending.stdout.strip() == FEATURE
                assert not git('diff', '--name-only', '--diff-filter=U')
                mutate('cherry-pick', '--continue')
            else:
                assert not git('status', '--porcelain')
                mutate('cherry-pick', FEATURE)
            shared = git('rev-parse', 'HEAD')
            assert git('diff', '--name-only', SHARED_INPUT, shared).splitlines() == [
                'src/net_processing.cpp', 'src/test/v2_protocol_handler_tests.cpp']
            (OUT / 'RELAY-SHARED-CHANGE.diff').write_bytes(subprocess.check_output(COMMAND + [
                'diff', '--binary', SHARED_INPUT, shared]))
            state.update(shared_head=shared, shared_tree=git('rev-parse', 'HEAD^{tree}'), phase='native')
            state['mapping'][FEATURE] = dict(new_commit=shared, disposition='same relay feature placed in shared tier')
            write(state_path, state)
            mutate('switch', '--no-overwrite-ignore', '-c', NATIVE, shared)
        tail = git('rev-list', '--reverse', SHARED_INPUT+'..'+NATIVE_INPUT).splitlines()
        assert len(tail) == 153
        assert git('branch', '--show-current') == NATIVE
        while state['next_index'] < len(tail):
            old = tail[state['next_index']]
            pending = subprocess.run(COMMAND + ['rev-parse', '--verify', 'CHERRY_PICK_HEAD'], capture_output=True, text=True)
            if pending.returncode == 0:
                assert pending.stdout.strip() == old
                assert not git('diff', '--name-only', '--diff-filter=U')
                mutate('cherry-pick', '--continue')
            else:
                assert not git('status', '--porcelain')
                mutate('cherry-pick', old)
            state['mapping'][old] = dict(new_commit=git('rev-parse', 'HEAD'), disposition='native adapter replayed above shared feature')
            state['next_index'] += 1
            write(state_path, state)
        expected = git('rev-parse', FEATURE+'^{tree}')
        actual = git('rev-parse', 'HEAD^{tree}')
        if expected != actual:
            (OUT / 'RELAY-SHARED-FAILED-TREE.diff').write_bytes(subprocess.check_output(COMMAND + ['diff', FEATURE, 'HEAD']))
            raise RuntimeError('Native tracked tree changed during shared placement; promotion forbidden')
        assert int(git('rev-list', '--count', '1fb7db17..'+SHARED)) == 378
        assert int(git('rev-list', '--count', SHARED+'..HEAD')) == 153
        state.update(status='native tree exact; shared boundary gate pending', native_head=git('rev-parse', 'HEAD'),
                     native_tree=actual, native_tree_equal=True, shared_count=378, native_count=153)
        write(state_path, state)
        print(state['status'], state['native_head'], flush=True)


if __name__ == '__main__':
    main()
