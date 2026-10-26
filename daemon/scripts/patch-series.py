#!/usr/bin/env python3
"""Replay a manifest in isolation; promote only a complete, validated series."""
import argparse
import email.policy
import email.parser
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile


def git(repo, *args, **kwargs):
    return subprocess.run(['git', '-C', str(repo), *args], check=True, **kwargs)


def output(repo, *args):
    return git(repo, *args, stdout=subprocess.PIPE).stdout.decode().strip()


def patches(manifest, allow_empty=False, _visited=None, _patches_root=None):
    manifest = manifest.resolve()
    root = manifest.parent.resolve()
    patches_root = _patches_root or root.parent.resolve()
    visited = set(_visited or ())
    if manifest in visited:
        raise ValueError(f'Cyclic manifest include: {manifest}')
    visited.add(manifest)
    result = []
    seen = set()
    for raw_line in manifest.read_text().splitlines():
        name = raw_line.strip()
        if not name or name.startswith('#'):
            continue
        if name.startswith('@include '):
            inc_rel = name[len('@include '):].strip()
            if not inc_rel:
                raise ValueError('Empty @include directive')
            inc_manifest = (root / inc_rel).resolve()
            if inc_manifest.name != 'series' or inc_manifest.parent.parent.resolve() != patches_root or not inc_manifest.is_file():
                raise ValueError(f'Invalid or out-of-bounds @include manifest: {inc_rel}')
            for inc_path, inc_mail in patches(inc_manifest, allow_empty=allow_empty, _visited=visited, _patches_root=patches_root):
                key = str(inc_path.resolve())
                if key in seen:
                    raise ValueError(f'Duplicate patch across included manifest: {inc_path.name}')
                seen.add(key)
                result.append((inc_path, inc_mail))
            continue
        path = root / name
        key = str(path.resolve())
        if name in seen or key in seen:
            raise ValueError(f'Duplicate manifest entry: {name}')
        seen.add(name)
        seen.add(key)
        if path.parent.resolve() != root or not path.is_file():
            raise ValueError(f'Invalid or missing patch: {name}')
        data = path.read_bytes()
        mail = data.startswith(b'From ')
        if mail:
            message = email.parser.BytesParser(policy=email.policy.default).parsebytes(data)
            for header in ('From', 'Date', 'Subject'):
                if len(message.get_all(header, [])) != 1 or not str(message[header]).strip():
                    raise ValueError(f'{name}: missing or duplicate {header}')
            sender = message['From']
            if not sender.addresses or not sender.addresses[0].username or not sender.addresses[0].domain:
                raise ValueError(f'{name}: invalid author address')
            if message['Date'].datetime is None or message['Date'].datetime.tzinfo is None:
                raise ValueError(f'{name}: invalid author date')
            if message.defects or any(message[h].defects for h in ('From', 'Date', 'Subject')):
                raise ValueError(f'{name}: malformed metadata')
            if not re.sub(r'^\[PATCH[^\]]*\]\s*', '', str(message['Subject'])).strip():
                raise ValueError(f'{name}: empty patch subject')
        elif root.name in ('v1', 'v2'):
            raise ValueError(f'{name}: {root.name.upper()} patches require git format-patch metadata')
        if b'\ndiff --git ' not in b'\n' + data:
            raise ValueError(f'{name}: missing patch diff')
        result.append((path, mail))
    if not result and not allow_empty:
        raise ValueError('Empty patch series')
    return result


def replay(workspace, manifest, base=None, check=False, provenance=None, expect_tree=None, allow_empty=False):
    entries = patches(manifest, allow_empty)  # Validate all inputs before any Git mutation.
    if output(workspace, 'status', '--porcelain', '--untracked-files=normal'):
        raise ValueError('Workspace has uncommitted changes; refusing to replace them')
    for state in ('rebase-apply', 'rebase-merge', 'MERGE_HEAD', 'CHERRY_PICK_HEAD'):
        if Path(output(workspace, 'rev-parse', '--path-format=absolute', '--git-path', state)).exists():
            raise ValueError(f'Workspace has an operation in progress: {state}')
    start = output(workspace, 'rev-parse', 'HEAD')
    target = output(workspace, 'rev-parse', '--verify', (base or start) + '^{commit}')
    recorded = None
    if provenance:
        recorded = json.loads(provenance.read_text())
        if recorded['base'] != target:
            raise ValueError('Provenance base does not match replay base')
        rows = recorded['patches']
        if [row['patch'] for row in rows] != [path.name for path, _ in entries[:len(rows)]]:
            raise ValueError('Manifest does not match recorded provenance prefix')
    with tempfile.TemporaryDirectory(prefix='lotus-patch-replay-') as temp:
        repo = Path(temp) / 'repo'
        subprocess.run(['git', 'clone', '--quiet', '--shared', '--no-checkout', str(workspace), str(repo)], check=True)
        git(repo, 'checkout', '--quiet', '--detach', target)
        for index, (path, mail) in enumerate(entries):
            config = ('-c', 'core.hooksPath=/dev/null', '-c', 'user.name=Lotus Builder', '-c', 'user.email=build@givelotus.org', '-c', 'commit.gpgsign=false')
            if mail:
                git(repo, *config, 'am', '--keep-non-patch', '--keep-cr', '--whitespace=nowarn', '--committer-date-is-author-date', str(path.resolve()))
            else:
                # Reference series retain their existing raw-diff format.
                git(repo, 'apply', '--index', '--whitespace=nowarn', str(path.resolve()))
                git(repo, *config, 'commit', '--quiet', '-m', f'Apply patch: {path.name}')
            if recorded and index < len(recorded['patches']):
                expected = recorded['patches'][index]['tree']
                actual = output(repo, 'rev-parse', 'HEAD^{tree}')
                if actual != expected:
                    raise ValueError(f'{path.name}: source tree changed: {actual} != {expected}')
                metadata_hash = recorded['patches'][index].get('metadata_sha256')
                if metadata_hash:
                    metadata = git(repo, 'show', '-s', '--format=%an%x00%ae%x00%aI%x00%B', 'HEAD', stdout=subprocess.PIPE).stdout
                    if hashlib.sha256(metadata).hexdigest() != metadata_hash:
                        raise ValueError(f'{path.name}: replay changed author, date or commit message')
        tip = output(repo, 'rev-parse', 'HEAD')
        tree = output(repo, 'rev-parse', 'HEAD^{tree}')
        if expect_tree and tree != expect_tree:
            raise ValueError(f'Final source tree changed: {tree} != {expect_tree}')
        print(f'Validated {len(entries)} patches; final source tree {tree}')
        if check:
            return tip
        if output(workspace, 'rev-parse', 'HEAD') != start or output(workspace, 'status', '--porcelain'):
            raise ValueError('Workspace changed during replay; refusing promotion')
        git(workspace, '-c', 'core.hooksPath=/dev/null', 'fetch', '--quiet', str(repo), tip)
        git(workspace, 'reset', '--hard', tip)
    return tip


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workspace', type=Path)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--base')
    parser.add_argument('--check', action='store_true', help='Replay in isolation without changing the workspace')
    parser.add_argument('--provenance', type=Path, help='Verify every recorded intermediate tree (allows appended release patches)')
    parser.add_argument('--expect-tree', help='Require an exact final source tree')
    parser.add_argument('--allow-empty', action='store_true', help='Explicit base-only reference series; otherwise empty manifests fail')
    args = parser.parse_args()
    try:
        replay(args.workspace.resolve(), args.manifest.resolve(), args.base, args.check, args.provenance, args.expect_tree, args.allow_empty)
    except (ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, f'Patch replay failed; workspace was not promoted: {error}\n')


if __name__ == '__main__':
    main()
