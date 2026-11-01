#!/usr/bin/env python3
"""List commits on non-archival daemon refs that are absent from the pinned stacks."""
from __future__ import annotations
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
REPOS = {'ecash': 'daemon/ecashd', 'v2': 'daemon/lotusd'}
# Branches whose commits this ledger accounts for; older refs predate the stacks.
REFS = re.compile(r'^origin/(perf/|consolidation/|archive/perf-review|archive/merklix-snowball|archive/consolidation-|snowstorm/)')

def git(repo, *args, stdin=None):
    p = subprocess.run(['git', '-C', str(repo), *args], input=stdin, text=True, capture_output=True, errors='replace')
    if p.returncode:
        raise RuntimeError(p.stderr.strip())
    return p.stdout

def patch_ids(repo, revs):
    """Map commit to patch id, in one pass."""
    if not revs:
        return {}
    diff = git(repo, 'log', '--no-walk', '--no-merges', '-p', '--format=commit %H', '--stdin', stdin='\n'.join(revs) + '\n')
    out = git(repo, 'patch-id', '--stable', stdin=diff)
    return {commit: pid for pid, commit in (line.split() for line in out.splitlines())}

def collect(key):
    repo = ROOT / REPOS[key]
    pin = json.loads((ROOT / 'daemon/sources.json').read_text())['sources'][key]['pin']
    base = json.loads((ROOT / 'daemon/stack-review.json').read_text())['stages'][key]['upstream_base']
    pinned = git(repo, 'log', '--first-parent', '--no-merges', '--format=%H%x00%s', f'{base}..{pin}').splitlines()
    pinned_subject = {row.split('\0')[1]: row.split('\0')[0] for row in pinned}
    pinned_ids = set(patch_ids(repo, [row.split('\0')[0] for row in pinned]).values())
    rows = {}
    refs = [r for r in git(repo, 'for-each-ref', '--format=%(refname:short)', 'refs/remotes/origin').split() if REFS.match(r)]
    for ref in refs:
        for row in git(repo, 'log', '--no-merges', '--format=%H%x00%ad%x00%s', '--date=short', f'{pin}..{ref}').splitlines():
            commit, date, subject = row.split('\0')
            rows.setdefault(commit, {'commit': commit, 'repo': key, 'date': date, 'subject': subject, 'refs': []})['refs'].append(ref.removeprefix('origin/'))
    ids = patch_ids(repo, list(rows))
    unique = {}
    for commit, row in rows.items():
        pid = ids.get(commit, commit)
        row['patch_id'] = pid
        if pid in pinned_ids:
            row['pin_match'] = 'identical patch in the pinned stack'
        elif row['subject'] in pinned_subject:
            row['pin_match'] = 'older revision of ' + pinned_subject[row['subject']]
        if pid in unique:
            unique[pid]['refs'] = sorted(set(unique[pid]['refs']) | set(row['refs']))
            unique[pid].setdefault('same_patch', []).append(commit)
        else:
            unique[pid] = row
    return list(unique.values())

if __name__ == '__main__':
    json.dump({key: collect(key) for key in REPOS}, sys.stdout, indent=2)
    print()
