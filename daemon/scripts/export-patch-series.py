#!/usr/bin/env python3
"""Export a linear committed series into a new review directory without overwrites."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args])


def _count_included(manifest, _visited=None):
    manifest = manifest.resolve()
    root = manifest.parent.resolve()
    patches_root = root.parent.resolve()
    visited = set(_visited or ())
    if manifest in visited:
        raise ValueError(f'Cyclic manifest include: {manifest}')
    visited.add(manifest)
    count = 0
    for raw_line in manifest.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('@include '):
            inc_rel = line[len('@include '):].strip()
            inc_manifest = (root / inc_rel).resolve()
            if inc_manifest.name != 'series' or inc_manifest.parent.parent.resolve() != patches_root or not inc_manifest.is_file():
                raise ValueError(f'Invalid or out-of-bounds @include manifest: {inc_rel}')
            count += _count_included(inc_manifest, visited)
        else:
            count += 1
    return count


def export(repo, base, manifest, destination):
    names = []
    included_count = 0
    for raw_line in manifest.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('@include '):
            inc_rel = line[len('@include '):].strip()
            inc_manifest = (manifest.parent.resolve() / inc_rel).resolve()
            included_count += _count_included(inc_manifest, {manifest.resolve()})
            continue
        names.append(line)
    if destination.exists():
        raise ValueError('Output directory already exists; refusing to overwrite a candidate')
    if git(repo, 'status', '--porcelain').strip():
        raise ValueError('Commit the intended changes before exporting a patch series')
    if not names or len(set(names)) != len(names) or any(Path(name).name != name or name.startswith('.') for name in names):
        raise ValueError('Invalid or duplicate patch names')
    base = git(repo, 'rev-parse', '--verify', base + '^{commit}').decode().strip()
    subprocess.run(['git', '-C', str(repo), 'merge-base', '--is-ancestor', base, 'HEAD'], check=True)
    commits = git(repo, 'rev-list', '--reverse', base + '..HEAD').decode().splitlines()
    if included_count and len(commits) == len(names) + included_count:
        parent = commits[included_count - 1]
        commits = commits[included_count:]
    else:
        parent = base
    if len(commits) != len(names):
        raise ValueError(f'{len(commits)} commits do not match {len(names)} manifest entries')
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(tempfile.mkdtemp(prefix='.lotus-patch-export-', dir=destination.parent))
    try:
        for name, commit in zip(names, commits):
            parents = git(repo, 'rev-list', '--parents', '-n', '1', commit).decode().split()
            if parents != [commit, parent]:
                raise ValueError('Series must be linear: merge commits cannot be exported')
            patch = git(repo, '-c', 'format.signature=', 'format-patch', '--stdout', '--binary', '--full-index', '--no-stat', '-1', commit)
            if b'\ndiff --git ' not in patch:
                raise ValueError(f'Empty commit cannot be exported: {commit}')
            (temp / name).write_bytes(patch)
            parent = commit
        (temp / 'series').write_text(manifest.read_text())
        os.rename(temp, destination)
    finally:
        if temp.exists():
            shutil.rmtree(temp)
    print(f'Exported {len(commits)} patches to {destination}; source tree ' + git(repo, 'rev-parse', 'HEAD^{tree}').decode().strip())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workspace', type=Path)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--base', required=True)
    parser.add_argument('--output-dir', required=True, type=Path)
    args = parser.parse_args()
    try:
        export(args.workspace.resolve(), args.base, args.manifest.resolve(), args.output_dir.resolve())
    except (ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, f'Patch export failed: {error}\n')


if __name__ == '__main__':
    main()
