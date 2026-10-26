#!/usr/bin/env python3
"""Pinned source submodules and mechanistic two-tier stack operations."""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
ALIASES = {'ecashd': 'ecash', 'lotusd': 'v2', 'lotus': 'v2', 'lotusv1': 'v1',
           'bitcoincashd': 'bchn', 'bitcoind': 'bitcoin',
           'bitcoin-abc': 'ecash', 'bitcoin-core': 'bitcoin', 'doged-reference': 'doged'}
DEFAULT_BRANCHES = {
    'ecash': 'master',
    'v2': 'main',
    'v1': 'lotusv1',
    'doged': 'master',
    'bchn': 'master',
    'bitcoin': 'master',
}

def git(repo, *args):
    p = subprocess.run(['git', '-C', str(repo), *args], text=True, capture_output=True)
    if p.returncode:
        raise RuntimeError(p.stderr.strip() or 'git command failed')
    return p.stdout.strip()

def ref_exists(repo, ref):
    p = subprocess.run(
        ['git', '-C', str(repo), 'rev-parse', '--verify', '--quiet', f'{ref}^{{commit}}'],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return p.returncode == 0

def is_ancestor(repo, ancestor, descendant):
    p = subprocess.run(
        ['git', '-C', str(repo), 'merge-base', '--is-ancestor', ancestor, descendant],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return p.returncode == 0

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
                valid_parents = (row['parents'] == [parent]) or (
                    row.get('bridge_ours') and len(row['parents']) == 2 and row['parents'][0] == parent
                )
                if not valid_parents or row['subject'].startswith(('fixup!', 'squash!')):
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

    def save_model_and_review(self):
        review_bytes = (json.dumps(self.review, indent=2) + '\n').encode('utf-8')
        self.review_path.write_bytes(review_bytes)
        self.model['stack_review_sha256'] = hashlib.sha256(review_bytes).hexdigest()
        (self.root / 'daemon/sources.json').write_text(json.dumps(self.model, indent=2) + '\n')

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

    def base_sha(self, name):
        name, source, _ = self.source(name)
        stage = self.review['stages'][name]
        if stage.get('upstream_base'):
            return stage['upstream_base']
        pin_file = source.get('base_pin_file')
        if pin_file and (self.root / pin_file).is_file():
            for line in (self.root / pin_file).read_text().splitlines():
                s = line.strip()
                if s and not s.startswith('#'):
                    return s
        return source['pin']

    def input_sha(self, name):
        name, source, _ = self.source(name)
        if source['parent_series']:
            return self.sources[source['parent_series']]['pin']
        return self.base_sha(name)

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
        if source['state'] not in ('stacked', 'upstream'):
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

    def verify_linear_and_no_fixups(self, path, start_sha, end_sha='HEAD', allow_bridge_merge=True):
        start_commit = git(path, 'rev-parse', f'{start_sha}^{{commit}}')
        end_commit = git(path, 'rev-parse', f'{end_sha}^{{commit}}')
        if start_commit == end_commit:
            return []
        if not is_ancestor(path, start_commit, end_commit):
            raise RuntimeError(f'{end_commit[:12]} is not a descendant of {start_commit[:12]} in {path}')
        commits = git(path, 'rev-list', '--first-parent', '--reverse', f'{start_commit}..{end_commit}').splitlines()
        parent = start_commit
        rows = []
        for c in commits:
            parts = git(path, 'rev-list', '--parents', '-n', '1', c).split()
            commit_sha, parents = parts[0], parts[1:]
            subj = git(path, 'log', '-1', '--format=%s', commit_sha)
            if subj.startswith(('fixup!', 'squash!')):
                raise RuntimeError(
                    f'Unsquashed fixup/squash commit at {commit_sha[:12]} ("{subj}"). '
                    f'Run `make -C daemon autosquash` before syncing.'
                )
            is_bridge = False
            if parents != [parent]:
                if (
                    allow_bridge_merge
                    and len(parents) == 2
                    and parents[0] == parent
                    and git(path, 'rev-parse', f'{commit_sha}^{{tree}}') == git(path, 'rev-parse', f'{parent}^{{tree}}')
                ):
                    is_bridge = True
                else:
                    raise RuntimeError(
                        f'Non-linear history at {commit_sha[:12]} (parents {parents}, expected [{parent[:12]}]). '
                        f'Only linear commits or `-s ours` tree-preserving bridge merges are permitted.'
                    )
            row = {'commit': commit_sha, 'parents': parents, 'subject': subj}
            if is_bridge:
                row['bridge_ours'] = True
            rows.append(row)
            parent = commit_sha
        return rows

    def bridge_ours(self, name, old_ref=None, message=None):
        """Record `old_ref` as merged into `HEAD` using `git merge -s ours` while keeping `HEAD^{tree}` verbatim."""
        name, source, path = self.source(name)
        if git(path, 'status', '--porcelain'):
            raise RuntimeError(f'{name} has uncommitted changes; commit or stash before bridging.')
        target_ref = old_ref or source['pin']
        target_sha = git(path, 'rev-parse', f'{target_ref}^{{commit}}')
        head_sha = git(path, 'rev-parse', 'HEAD')
        if is_ancestor(path, target_sha, head_sha):
            return head_sha
        before_tree = git(path, 'rev-parse', 'HEAD^{tree}')
        msg = message or f'chore({name}): bridge historical pin {target_sha[:12]} via -s ours'
        git(path, 'merge', '-s', 'ours', '--no-edit', '-m', msg, target_sha)
        after_tree = git(path, 'rev-parse', 'HEAD^{tree}')
        if after_tree != before_tree:
            raise RuntimeError(f'Tree changed unexpectedly during -s ours merge in {name}')
        return git(path, 'rev-parse', 'HEAD')

    def _cascade_children(self, parent_name, old_parent_tip, new_parent_tip):
        """When `ecash` advances or rebases from `old_parent_tip` to `new_parent_tip`, cascade dependent submodules (`v2`)."""
        if old_parent_tip == new_parent_tip:
            return
        for child_name, child_src in self.sources.items():
            if child_src['parent_series'] != parent_name:
                continue
            _, _, child_path = self.source(child_name)
            _, _, parent_path = self.source(parent_name)
            if not (child_path / '.git').exists():
                # Update review stage metadata if child submodule is not checked out
                stage = self.review['stages'][child_name]
                if stage.get('input_commit') == old_parent_tip and not stage.get('commits'):
                    stage['input_commit'] = new_parent_tip
                    stage['reviewed_reference_tip'] = new_parent_tip
                continue
            if git(child_path, 'status', '--porcelain'):
                raise RuntimeError(f'Dependent submodule {child_name} has uncommitted changes; cannot cascade {parent_name} update.')
            git(child_path, 'fetch', str(parent_path), new_parent_tip)
            child_base = old_parent_tip
            if not (ref_exists(child_path, child_base) and is_ancestor(child_path, child_base, 'HEAD')):
                recorded_input = self.review['stages'][child_name].get('input_commit')
                if recorded_input and ref_exists(child_path, recorded_input) and is_ancestor(child_path, recorded_input, 'HEAD'):
                    child_base = recorded_input
            if ref_exists(child_path, child_base) and is_ancestor(child_path, child_base, 'HEAD'):
                if child_base != new_parent_tip:
                    git(child_path, 'rebase', '--onto', new_parent_tip, child_base, 'HEAD')
                    self.review['stages'][child_name]['input_commit'] = new_parent_tip

    def sync(self, name, bridge_ours=False, push=False):
        """Verify linear history and no fixups, optionally bridge prior pin with `git merge -s ours`, and update pins/gitlinks."""
        ordered = []
        for key in self.names(name):
            parent = self.sources[key]['parent_series']
            if parent and parent not in ordered:
                ordered.append(parent)
            if key not in ordered:
                ordered.append(key)
        # Also include any child series whose parent is in `ordered` so `stack-review.json` boundary stays aligned
        for child_key, child_src in self.sources.items():
            if child_src['parent_series'] in ordered and child_key not in ordered:
                ordered.append(child_key)

        for key in ordered:
            _, source, path = self.source(key)
            if not (path / '.git').exists():
                continue
            if git(path, 'status', '--porcelain'):
                raise RuntimeError(f'{key} contains uncommitted changes; commit or stash before sync.')
            old_pin = source['pin']
            if source['parent_series']:
                parent_key = source['parent_series']
                _, parent_src, parent_path = self.source(parent_key)
                start_sha = parent_src['pin']
                if not ref_exists(path, start_sha):
                    git(path, 'fetch', str(parent_path), start_sha)
                if not is_ancestor(path, start_sha, 'HEAD'):
                    old_input = self.review['stages'][key].get('input_commit')
                    if old_input and ref_exists(path, old_input) and is_ancestor(path, old_input, 'HEAD'):
                        git(path, 'rebase', '--onto', start_sha, old_input, 'HEAD')
                    else:
                        raise RuntimeError(f'{key} HEAD is not based on {parent_key} tip {start_sha[:12]}')
            else:
                start_sha = self.base_sha(key)
                if not is_ancestor(path, start_sha, 'HEAD'):
                    raise RuntimeError(f'{key} HEAD is not a descendant of base {start_sha[:12]}')

            # First verify the code commits before any optional -s ours bridge
            self.verify_linear_and_no_fixups(path, start_sha, 'HEAD', allow_bridge_merge=True)
            if bridge_ours and ref_exists(path, old_pin) and not is_ancestor(path, old_pin, 'HEAD'):
                self.bridge_ours(key, old_pin)

            rows = self.verify_linear_and_no_fixups(path, start_sha, 'HEAD', allow_bridge_merge=True)
            head_sha = git(path, 'rev-parse', 'HEAD')
            tree_sha = git(path, 'rev-parse', 'HEAD^{tree}')

            old_tip = self.review['stages'][key].get('reviewed_reference_tip', old_pin)
            source['pin'] = head_sha
            source['tree'] = tree_sha
            if head_sha != self.base_sha(key) or rows:
                source['state'] = 'stacked'

            stage = self.review['stages'][key]
            stage['input_commit'] = start_sha
            stage['reviewed_reference_tip'] = head_sha
            stage['commits'] = rows

            git(self.root, 'update-index', '--add', '--cacheinfo', f'160000,{head_sha},{source["path"]}')
            if old_tip != head_sha:
                self._cascade_children(key, old_tip, head_sha)

            if push:
                branch = source.get('branch') or DEFAULT_BRANCHES.get(key, 'main')
                push_args = ['push', 'origin', f'HEAD:refs/heads/{branch}']
                if not bridge_ours:
                    push_args.insert(1, '--force-with-lease')
                git(path, *push_args)
            print(f'synced {key}: {source["path"]} -> {head_sha[:12]} ({len(rows)} commits, state={source["state"]})')

        if any(s['state'] == 'stacked' for s in self.sources.values()):
            self.model['phase'] = 'promoted'
        self.save_model_and_review()

    def autosquash(self, name='v2', no_sync=False):
        """Non-interactively fold all `fixup!` and `squash!` commits across the selected submodule stack."""
        ordered = []
        for key in self.names(name):
            parent = self.sources[key]['parent_series']
            if parent and parent not in ordered:
                ordered.append(parent)
            if key not in ordered:
                ordered.append(key)

        env = dict(os.environ)
        env['GIT_SEQUENCE_EDITOR'] = 'true'
        env['GIT_EDITOR'] = 'true'

        for key in ordered:
            _, source, path = self.source(key)
            if git(path, 'status', '--porcelain'):
                raise RuntimeError(f'{key} contains uncommitted changes; commit or stash before autosquash.')
            if source['parent_series']:
                parent_key = source['parent_series']
                _, parent_src, parent_path = self.source(parent_key)
                start_sha = git(parent_path, 'rev-parse', 'HEAD')
                if not ref_exists(path, start_sha):
                    git(path, 'fetch', str(parent_path), start_sha)
            else:
                start_sha = self.base_sha(key)

            old_head = git(path, 'rev-parse', 'HEAD')
            ts = dt.datetime.now().strftime('%Y%m%d-%H%M%S')
            git(path, 'update-ref', f'refs/backups/pre-autosquash-{key}-{ts}', old_head)
            p = subprocess.run(
                ['git', '-C', str(path), 'rebase', '-i', '--autosquash', start_sha],
                env=env,
                text=True,
                capture_output=True,
            )
            if p.returncode:
                subprocess.run(['git', '-C', str(path), 'rebase', '--abort'], capture_output=True)
                raise RuntimeError(p.stderr.strip() or f'autosquash failed in {key}')
            new_head = git(path, 'rev-parse', 'HEAD')
            if new_head != old_head or new_head != source['pin']:
                self._cascade_children(key, old_head, new_head)

        if not no_sync:
            self.sync(name)

    def sink_to_ecash(self, commit='HEAD', no_sync=False):
        """Cherry-pick a chain-agnostic commit from `daemon/lotusd` (`v2`) down to `daemon/ecashd` (`ecash`) and rebase `v2`."""
        _, ecash_src, ecash_path = self.source('ecash')
        _, v2_src, v2_path = self.source('v2')
        if git(ecash_path, 'status', '--porcelain') or git(v2_path, 'status', '--porcelain'):
            raise RuntimeError('Both daemon/ecashd and daemon/lotusd must be clean before sink-to-ecash.')

        ecash_head = git(ecash_path, 'rev-parse', 'HEAD')
        v2_head = git(v2_path, 'rev-parse', 'HEAD')
        target_sha = git(v2_path, 'rev-parse', f'{commit}^{{commit}}')
        if not ref_exists(v2_path, ecash_head):
            git(v2_path, 'fetch', str(ecash_path), ecash_head)
        v2_commits = git(v2_path, 'rev-list', '--first-parent', '--reverse', f'{ecash_head}..{v2_head}').splitlines()
        if target_sha not in v2_commits:
            raise RuntimeError(f'Commit {target_sha[:12]} is not in the native v2 range ({ecash_head[:12]}..{v2_head[:12]})')

        remaining_v2 = [c for c in v2_commits if c != target_sha]
        ts = dt.datetime.now().strftime('%Y%m%d-%H%M%S')
        git(ecash_path, 'update-ref', f'refs/backups/pre-sink-ecash-{ts}', ecash_head)
        git(v2_path, 'update-ref', f'refs/backups/pre-sink-v2-{ts}', v2_head)
        ecash_branch = git(ecash_path, 'rev-parse', '--abbrev-ref', 'HEAD')
        v2_branch = git(v2_path, 'rev-parse', '--abbrev-ref', 'HEAD')

        try:
            git(ecash_path, 'fetch', str(v2_path), target_sha)
            git(ecash_path, 'cherry-pick', target_sha)
            new_ecash_head = git(ecash_path, 'rev-parse', 'HEAD')

            git(v2_path, 'fetch', str(ecash_path), new_ecash_head)
            if v2_branch != 'HEAD':
                git(v2_path, 'checkout', '-B', v2_branch, new_ecash_head)
            else:
                git(v2_path, 'checkout', '--detach', new_ecash_head)
            for c in remaining_v2:
                git(v2_path, 'cherry-pick', c)
        except Exception as exc:
            subprocess.run(['git', '-C', str(ecash_path), 'cherry-pick', '--abort'], capture_output=True)
            subprocess.run(['git', '-C', str(v2_path), 'cherry-pick', '--abort'], capture_output=True)
            git(ecash_path, 'reset', '--hard', ecash_head)
            git(v2_path, 'reset', '--hard', v2_head)
            raise RuntimeError(f'Failed to sink commit {target_sha[:12]} to ecash: {exc}') from exc

        if not no_sync:
            self.sync('v2')

    def rebase_upstream(self, name, onto, bridge_ours=False, no_sync=False):
        """Rebase a submodule stack (and any dependent child submodule) onto a new upstream base commit."""
        name, source, path = self.source(name)
        target_key = source['parent_series'] or name
        _, target_src, target_path = self.source(target_key)
        if git(target_path, 'status', '--porcelain'):
            raise RuntimeError(f'{target_key} has uncommitted changes; commit or stash first.')

        old_base = self.base_sha(target_key)
        old_head = git(target_path, 'rev-parse', 'HEAD')
        if onto == 'latest':
            upstream_url = target_src.get('upstream_url')
            if not upstream_url:
                raise RuntimeError(f'No upstream_url configured for {target_key}')
            git(target_path, 'fetch', upstream_url, 'HEAD')
            new_base = git(target_path, 'rev-parse', 'FETCH_HEAD^{commit}')
        else:
            if not ref_exists(target_path, onto) and target_src.get('upstream_url'):
                git(target_path, 'fetch', target_src['upstream_url'], onto)
            new_base = git(target_path, 'rev-parse', f'{onto}^{{commit}}')

        if new_base != old_base:
            ts = dt.datetime.now().strftime('%Y%m%d-%H%M%S')
            git(target_path, 'update-ref', f'refs/backups/pre-rebase-{target_key}-{ts}', old_head)
            git(target_path, 'rebase', '--onto', new_base, old_base, 'HEAD')
            new_head = git(target_path, 'rev-parse', 'HEAD')
            self.review['stages'][target_key]['upstream_base'] = new_base
            pin_file = target_src.get('base_pin_file')
            if pin_file and (self.root / pin_file).is_file():
                (self.root / pin_file).write_text(new_base + '\n')
            self._cascade_children(target_key, old_head, new_head)

        if not no_sync:
            self.sync(name, bridge_ours=bridge_ours)

    def extract_pr(self, name, branch, commits):
        """Cherry-pick selected commit(s) onto a clean branch based directly on upstream_base."""
        name, source, path = self.source(name)
        if git(path, 'status', '--porcelain'):
            raise RuntimeError(f'{name} has uncommitted changes; commit or stash first.')
        base = self.base_sha(name)
        orig_head = git(path, 'rev-parse', 'HEAD')
        orig_branch = git(path, 'rev-parse', '--abbrev-ref', 'HEAD')
        resolved = []
        for item in commits:
            if '..' in item:
                resolved.extend(git(path, 'rev-list', '--reverse', item).splitlines())
            else:
                resolved.append(git(path, 'rev-parse', f'{item}^{{commit}}'))
        if not resolved:
            raise RuntimeError('No commits specified to extract.')
        try:
            git(path, 'checkout', '-B', branch, base)
            for c in resolved:
                git(path, 'cherry-pick', c)
            pr_tip = git(path, 'rev-parse', 'HEAD')
        finally:
            if orig_branch != 'HEAD':
                git(path, 'checkout', orig_branch)
            else:
                git(path, 'checkout', '--detach', orig_head)
        print(f'Extracted {len(resolved)} commit(s) onto {branch} ({pr_tip[:12]}) in {source["path"]}')
        return pr_tip

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='cmd', required=True)
    for cmd in ['setup', 'init', 'status', 'verify', 'plan', 'path', 'canonical', 'require-ready', 'release-check']:
        p = sub.add_parser(cmd)
        p.add_argument('series', nargs='?', default='all')
        if cmd == 'plan':
            p.add_argument('--json', action='store_true')
            p.add_argument('--commits', action='store_true')
        if cmd == 'init':
            p.add_argument('--ecash-tip', default=None)

    p_sync = sub.add_parser('sync', help='Verify linear history, optionally bridge prior pin via -s ours, and update pins/gitlinks')
    p_sync.add_argument('series', nargs='?', default='v2')
    p_sync.add_argument('--bridge-ours', action='store_true', help='Record previous pin as merged via `git merge -s ours` for fast-forward history')
    p_sync.add_argument('--push', action='store_true', help='Push updated branch to submodule origin')
    p_sync.add_argument('--export-patches', action='store_true', help='Accepted for CLI compatibility')
    p_sync.add_argument('--verify-replay', action='store_true', help='Accepted for CLI compatibility')

    p_bridge = sub.add_parser('bridge-ours', help='Record a historical commit as merged via `git merge -s ours` while preserving HEAD^{tree}')
    p_bridge.add_argument('series', nargs='?', default='v2')
    p_bridge.add_argument('--ref', default=None, help='Commit or ref to bridge (defaults to current recorded pin)')
    p_bridge.add_argument('--message', default=None, help='Custom merge commit message')

    p_auto = sub.add_parser('autosquash', help='Non-interactively autosquash fixup!/squash! commits and cascade across submodules')
    p_auto.add_argument('series', nargs='?', default='v2')
    p_auto.add_argument('--no-sync', action='store_true')
    p_auto.add_argument('--export-patches', action='store_true')

    p_sink = sub.add_parser('sink-to-ecash', help='Move a chain-agnostic commit from daemon/lotusd down to daemon/ecashd and rebase v2')
    p_sink.add_argument('commit', nargs='?', default='HEAD')
    p_sink.add_argument('--no-sync', action='store_true')
    p_sink.add_argument('--export-patches', action='store_true')

    p_rebase = sub.add_parser('rebase-upstream', help='Rebase submodule stack onto a new upstream commit and cascade to children')
    p_rebase.add_argument('series', nargs='?', default='v2')
    p_rebase.add_argument('--onto', required=True)
    p_rebase.add_argument('--bridge-ours', action='store_true')
    p_rebase.add_argument('--no-sync', action='store_true')
    p_rebase.add_argument('--export-patches', action='store_true')

    p_pr = sub.add_parser('extract-pr', help='Cherry-pick selected commits onto a clean branch off upstream_base')
    p_pr.add_argument('series')
    p_pr.add_argument('--branch', required=True)
    p_pr.add_argument('commits', nargs='+')

    args = parser.parse_args(argv)
    try:
        project = Project()
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
        elif args.cmd == 'sync':
            project.sync(args.series, bridge_ours=args.bridge_ours, push=args.push)
        elif args.cmd == 'bridge-ours':
            sha = project.bridge_ours(args.series, old_ref=args.ref, message=args.message)
            print(f'{args.series}: bridged onto {sha[:12]} via -s ours')
        elif args.cmd == 'autosquash':
            project.autosquash(args.series, no_sync=args.no_sync)
        elif args.cmd == 'sink-to-ecash':
            project.sink_to_ecash(args.commit, no_sync=args.no_sync)
        elif args.cmd == 'rebase-upstream':
            project.rebase_upstream(args.series, onto=args.onto, bridge_ours=args.bridge_ours, no_sync=args.no_sync)
        elif args.cmd == 'extract-pr':
            project.extract_pr(args.series, args.branch, args.commits)
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
