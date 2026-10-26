#!/usr/bin/env python3
"""Pinned source submodules. Initialization and inspection never apply stacks."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
ALIASES = {'ecashd': 'ecash', 'lotusd': 'v2', 'lotus': 'v2', 'lotusv1': 'v1',
           'bitcoincashd': 'bchn', 'bitcoind': 'bitcoin'}

def git(repo, *args):
    p = subprocess.run(['git', '-C', str(repo), *args], text=True, capture_output=True)
    if p.returncode:
        raise RuntimeError(p.stderr.strip() or 'git command failed')
    return p.stdout.strip()

def identity(url):
    url = re.sub(r'^git@github.com:', 'https://github.com/', url)
    return url.rstrip('/').removesuffix('.git')

class Project:
    def __init__(self, root=ROOT):
        self.root = Path(root).resolve()
        self.model = json.loads((self.root / 'daemon/sources.json').read_text())
        self.sources = self.model['sources']
        self.review_path = self.root / self.model['stack_review']
        payload = self.review_path.read_bytes()
        if hashlib.sha256(payload).hexdigest() != self.model['stack_review_sha256']:
            raise RuntimeError('Stack review changed: review its new order and update its recorded digest explicitly.')
        self.review = json.loads(payload)
        for name, source in self.sources.items():
            path = Path(source['path'])
            if path.parts[:1] != ('daemon',) or len(path.parts) != 2 or '..' in path.parts:
                raise RuntimeError(f'Invalid source path: {path}')
            if not re.fullmatch('[0-9a-f]{40}', source['pin']):
                raise RuntimeError(f'Invalid source pin: {name}')
            if source['parent_series'] and source['parent_series'] not in self.sources:
                raise RuntimeError(f'Unknown source dependency: {name}')
            stage = self.review['stages'][name]
            if stage['destination'] != source['path'] or stage['repository'] != source['url']:
                raise RuntimeError(f'Stack destination does not match source repository: {name}')
            if stage['depends_on'] != source['parent_series']:
                raise RuntimeError(f'Stack dependency differs from source dependency: {name}')
            parent = stage.get('input_commit')
            for row in stage.get('commits', []):
                if row['parents'] != [parent] or row['subject'].startswith(('fixup!', 'squash!')):
                    raise RuntimeError(f'Nonlinear, reordered or unsquashed review history: {name}')
                parent = row['commit']
            if 'commits' in stage and parent != stage['reviewed_reference_tip']:
                raise RuntimeError(f'Review tip differs from ordered commits: {name}')
        for name, source in self.sources.items():
            parent = source['parent_series']
            if parent:
                stage = self.review['stages'][name]
                if stage['input_commit'] != self.review['stages'][parent]['reviewed_reference_tip']:
                    raise RuntimeError(f'{name} must start at the exact reviewed {parent} tip')

    def names(self, name=None):
        if not name or name == 'all':
            return list(self.sources)
        name = ALIASES.get(name, name)
        if name not in self.sources:
            raise RuntimeError(f'Unknown source: {name}')
        return [name]

    def source(self, name):
        name = self.names(name)[0]
        return name, self.sources[name], self.root / self.sources[name]['path']

    def verify(self, name):
        name, source, path = self.source(name)
        if not (path / '.git').exists():
            raise RuntimeError(f'{source["path"]} is not initialized; run make -C daemon setup SERIES={name}')
        if Path(git(path, 'rev-parse', '--show-toplevel')).resolve() != path.resolve():
            raise RuntimeError(f'Wrong Git repository at {path}')
        expected = source['url']
        if identity(git(path, 'remote', 'get-url', 'origin')) != identity(expected):
            raise RuntimeError(f'Wrong origin for {source["path"]}; expected {expected}')
        registered = git(self.root, 'config', '-f', '.gitmodules', '--get', f'submodule.{source["path"]}.url')
        if identity(registered) != identity(expected):
            raise RuntimeError(f'.gitmodules URL differs from source model: {name}')
        entry = git(self.root, 'ls-files', '--stage', '--', source['path']).split()
        if len(entry) < 3 or entry[0] != '160000' or entry[1] != source['pin']:
            raise RuntimeError(f'Gitlink differs from locked source pin: {name}')
        if git(path, 'rev-parse', 'HEAD') != source['pin']:
            raise RuntimeError(f'{name} HEAD differs from pinned source; preserve the change rather than resetting it.')
        if git(path, 'rev-parse', 'HEAD^{tree}') != source['tree']:
            raise RuntimeError(f'Source tree differs from recorded tree: {name}')
        if git(path, 'status', '--porcelain'):
            raise RuntimeError(f'{name} contains source changes; preserve them before setup/sync.')
        return name, source, path

    def setup(self, name):
        for key in self.names(name):
            _, source, path = self.source(key)
            if (path / '.git').exists():
                self.verify(key)  # Never overwrite a changed checkout, even if clean.
            else:
                git(self.root, 'submodule', 'update', '--init', '--checkout', '--', source['path'])
                self.verify(key)
            git(path, 'config', 'rebase.autoSquash', 'true')
            git(path, 'config', 'rerere.enabled', 'true')
            for remote_name, remote_url in [('upstream', source.get('upstream_url')), ('export', source.get('export_url'))]:
                if not remote_url:
                    continue
                remotes = git(path, 'remote').splitlines()
                if remote_name not in remotes:
                    git(path, 'remote', 'add', remote_name, remote_url)
                elif identity(git(path, 'remote', 'get-url', remote_name)) != identity(remote_url):
                    raise RuntimeError(f'{key} {remote_name} remote points to the wrong repository')
            if key == 'v2':
                engine = self.sources['ecash']['url']
                remotes = git(path, 'remote').splitlines()
                if 'engine' not in remotes:
                    git(path, 'remote', 'add', 'engine', engine)
                elif identity(git(path, 'remote', 'get-url', 'engine')) != identity(engine):
                    raise RuntimeError('Lotus engine remote points to the wrong repository')
            print(f'{key}: {source["path"]} at {source["pin"][:12]} ({source["state"]}); no patches applied')

    def require_ready(self, name):
        name, source, path = self.verify(name)
        if source['state'] != 'stacked':
            raise RuntimeError(f'{name}: base-only scaffold. Review make -C daemon source-plan SERIES={name}; stack application/build/release is deferred.')
        if source['parent_series']:
            _, engine, engine_path = self.verify(source['parent_series'])
            if engine['state'] != 'stacked':
                raise RuntimeError('Shared engine has not been promoted')
            git(path, 'merge-base', '--is-ancestor', engine['pin'], source['pin'])
        return name, source, path

    def plan(self, name):
        result = []
        for key in self.names(name):
            if self.sources[key]['parent_series']:
                parent = self.sources[key]['parent_series']
                if parent not in result:
                    result.append(parent)
            if key not in result:
                result.append(key)
        return {key: self.review['stages'][key] for key in result}

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='cmd', required=True)
    for cmd in ['setup', 'init', 'status', 'verify', 'plan', 'path', 'canonical', 'require-ready', 'release-check']:
        p = sub.add_parser(cmd)
        p.add_argument('series', nargs='?', default='all')
        if cmd == 'plan':
            p.add_argument('--json', action='store_true')
            p.add_argument('--commits', action='store_true')
    for cmd in ['sync', 'autosquash', 'sink-to-ecash', 'rebase-upstream', 'extract-pr']:
        p = sub.add_parser(cmd, help='Deferred until stack-order review and submodule promotion')
        p.add_argument('rest', nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    try:
        project = Project()
        if args.cmd in ['sync', 'autosquash', 'sink-to-ecash', 'rebase-upstream', 'extract-pr']:
            raise RuntimeError('Stack mutations are deferred in the submodule scaffold; use plan/status. Legacy workspaces will not be modified.')
        if args.cmd in ['setup', 'init']:
            project.setup(args.series)
        elif args.cmd == 'canonical':
            print(project.names(args.series)[0])
        elif args.cmd == 'path':
            print(project.source(args.series)[2])
        elif args.cmd == 'release-check':
            if project.model.get('phase') == 'submodule-scaffold':
                raise RuntimeError('Source scaffold: stack application is deferred; legacy replay/release workflows are disabled until reviewed promotion.')
            for name in project.names(args.series):
                project.require_ready(name)
        elif args.cmd == 'require-ready':
            for name in project.names(args.series):
                project.require_ready(name)
        elif args.cmd in ['status', 'verify']:
            errors = []
            for name in project.names(args.series):
                try:
                    _, source, path = project.verify(name)
                    print(f'{name:8} {source["path"]:23} {source["pin"][:12]} {source["state"]} {source["url"]}')
                except RuntimeError as error:
                    errors.append(str(error))
                    print(f'{name}: ERROR {error}')
            if errors:
                return 1
        elif args.cmd == 'plan':
            stages = project.plan(args.series)
            if args.json:
                print(json.dumps({'application': 'deferred', 'stages': stages}, indent=2))
            else:
                for name, stage in stages.items():
                    count = len(stage.get('commits', stage.get('migration_mailboxes', [])))
                    print(f'{name}: {count} ordered inputs -> {stage["destination"]} ({stage["repository"]})')
                    print(f'  starts at {stage.get("input_commit", stage["upstream_base"])}; depends on {stage["depends_on"] or "upstream"}; NOT APPLIED')
                    if stage.get('review_note'):
                        print('  REVIEW: '+stage['review_note'])
                    if args.commits:
                        for i, row in enumerate(stage.get('commits', stage.get('migration_mailboxes', [])), 1):
                            print(f'  {i:03} {row.get("commit", row.get("file"))} {row.get("subject", "")}')
        return 0
    except (RuntimeError, KeyError, ValueError) as error:
        print(f'daemon-sources: {error}', file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())
