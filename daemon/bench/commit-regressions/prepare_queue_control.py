#!/usr/bin/env python3
"""Make an unintegrated queue-only control; preserve original networking bytes."""
import hashlib
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT/'daemon/worktrees/grok-progression-source'
OUT = ROOT/'daemon/patch-intake/20261023/queue-owner-audit'
ARCHIVE = ROOT/'daemon/.local-artifact-archive/commit-regressions'
RESTORE = ['src/net/txrelay_index.h', 'src/net_processing.cpp', 'src/net_processing.h',
           'src/protocol.h', 'src/test/txrelay_tests.cpp', 'src/test/v2_protocol_handler_tests.cpp']


def git(*args, data=None, env=None):
    return subprocess.check_output(['git', '-C', str(SOURCE), *args], input=data, env=env)


def main():
    assert not git('status', '--porcelain').strip()
    OUT.mkdir(parents=True, exist_ok=True)
    plan_path = ROOT/'daemon/patch-intake/20261023/snapshot-count-order/CANDIDATE-STACK.json'
    plan = json.loads(plan_path.read_text())
    entries = plan['stages']['ecash']['commits']
    parent, original = entries[375]['commit'], entries[376]['commit']
    assert original == '77bc9fb0c949479471c27079c0a911a9fc58b4b2'
    assert git('rev-parse', original+'^').strip().decode() == parent
    preserved = ARCHIVE/'snapshot-count-order.bundle'
    verification = subprocess.run(['git', '-C', str(SOURCE), 'bundle', 'verify', str(preserved)],
                                  capture_output=True, text=True, check=True)
    git('update-ref', 'refs/backup/queue-owner-input-20261023', original)
    env = dict(os.environ, GIT_INDEX_FILE=str(ARCHIVE/'queue-owner-control.index'))
    git('read-tree', original, env=env)
    ledger = []
    for path in RESTORE:
        metadata = git('ls-tree', parent, '--', path).decode().split()
        assert metadata[0] == '100644' and metadata[1] == 'blob'
        git('update-index', '--cacheinfo', f'100644,{metadata[2]},{path}', env=env)
        ledger.append(dict(path=path, parent_blob=metadata[2],
                           original_queue_blob=git('rev-parse', original+':'+path).strip().decode(),
                           control_blob=metadata[2], purpose='Hold peer capability behavior and its tests equal to parent376'))
    tree = git('write-tree', env=env).strip().decode()
    assert set(git('diff', '--name-only', original, tree).decode().splitlines()) == set(RESTORE)
    changed = set(git('diff', '--name-only', parent, original).decode().splitlines())
    assert set(git('diff', '--name-only', parent, tree).decode().splitlines()) == changed-set(RESTORE)
    commit = git('-c', 'user.email=213740+schancel@users.noreply.github.com', 'commit-tree', tree, '-p', parent,
                 '-m', 'rpc: isolate bounded commit owner without unrelated relay capability reversals',
                 '-m', 'Unintegrated experimental control from377. Preserve all nine RPC queue, lifetime, callback and queue-test files exactly; restore four peer capability files and two associated tests to parent376. This is not a promotion or a claim that performance is fixed.').strip().decode()
    git('update-ref', 'refs/heads/perf/queue-only-control-20261023', commit)
    (OUT/'INPUT-STACK.json').write_bytes(plan_path.read_bytes())
    (OUT/'ORIGINAL-377.patch').write_bytes(git('format-patch', '-1', '--stdout', original))
    (OUT/'CONTROL-RESTORATION.diff').write_bytes(git('diff', original, commit))
    (OUT/'QUEUE-ONLY.diff').write_bytes(git('diff', parent, commit))
    bundle = ARCHIVE/'queue-only-control.bundle'
    assert not bundle.exists(), 'Preserve existing control; do not overwrite it'
    git('bundle', 'create', str(bundle), 'refs/heads/perf/queue-only-control-20261023', '^'+parent)
    check = subprocess.run(['git', '-C', str(SOURCE), 'bundle', 'verify', str(bundle)], capture_output=True, text=True, check=True)
    receipt = dict(status='unintegrated control; builds and benchmark pending', parent=parent,
        original=original, control=commit, control_tree=tree, held_equal=ledger,
        retained_queue_files=sorted(changed-set(RESTORE)), input_bundle=str(preserved),
        input_bundle_verification=verification.stdout+verification.stderr, bundle=str(bundle),
        bundle_sha256=hashlib.file_digest(bundle.open('rb'), 'sha256').hexdigest(), verification=check.stdout+check.stderr)
    (OUT/'CONTROL.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(commit)


if __name__ == '__main__':
    main()
