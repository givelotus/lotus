#!/usr/bin/env python3
"""Verify maintained series with existing parser and a private index, no clone."""
import argparse, hashlib, importlib.util, json, os, subprocess, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
parser = argparse.ArgumentParser()
parser.add_argument('--expect-count', type=int, required=True)
parser.add_argument('--expect-head', required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
source = ROOT / 'daemon/worktrees/merklix-slab-source'
spec = importlib.util.spec_from_file_location('patch_series', ROOT / 'daemon/scripts/patch-series.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
entries = mod.patches(ROOT / 'daemon/patches/v2/series')
assert len(entries) == args.expect_count
base = '1fb7db17c176cdea8a2c60d887891589382ee4e3'
def git(*arguments, env=None, raw=False):
    result = subprocess.check_output(['git', '-C', str(source), *arguments], env=env)
    return result if raw else result.decode().strip()
actual = git('log', '--reverse', '--format=%H %T %P', base + '..' + args.expect_head).splitlines()
assert len(actual) == len(entries)
fd, index = tempfile.mkstemp(prefix='private-replay-', dir=Path(__file__).parent)
os.close(fd)
os.unlink(index)
env = dict(os.environ, GIT_INDEX_FILE=index)
records = []
try:
    git('read-tree', base, env=env)
    previous = base
    for ordinal, ((patch, _), line) in enumerate(zip(entries, actual), 1):
        commit, expected_tree, parent = line.split()
        assert parent == previous
        data = patch.read_bytes()
        subprocess.run(['git', '-C', str(source), 'apply', '--cached', '--binary',
                        '--whitespace=nowarn', '-'], input=data, env=env, check=True,
                       stdout=subprocess.DEVNULL)
        tree = git('write-tree', env=env)
        assert tree == expected_tree, (ordinal, patch.name, tree, expected_tree)
        records.append({'global_number': ordinal, 'series': patch.parent.name,
                        'file': patch.name, 'sha256': hashlib.sha256(data).hexdigest(),
                        'commit': commit, 'parent': parent, 'tree': tree})
        previous = commit
finally:
    if os.path.exists(index): os.unlink(index)
result = {'status': 'PASS_ALL_MAILBOXES_ALL_INTERMEDIATE_TREES', 'method':
          'Existing patch-series parser plus private-index actual mailbox replay; no clone/worktree mutation',
          'base': base, 'head': args.expect_head, 'tree': records[-1]['tree'],
          'count': len(records), 'records': records}
args.output.write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({key: value for key, value in result.items() if key != 'records'}))
