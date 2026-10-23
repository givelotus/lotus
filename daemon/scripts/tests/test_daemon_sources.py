"""Behavioral checks for source routing, frozen order and non-destructive setup."""
import hashlib
import json
from pathlib import Path
import subprocess
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from daemon_sources import Project, git

class SourceRoutingTests(unittest.TestCase):
    def setUp(self):
        scratch = Path(__file__).resolve().parents[2] / '.local-artifact-archive'
        scratch.mkdir(exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(prefix='source-tool-tests-', dir=scratch)
        self.root = Path(self.tmp.name)
        git(self.root, 'init', '-b', 'test')
        self.sources = {}
        stages = {}
        for name, directory in [('ecash', 'ecashd'), ('v2', 'lotusd')]:
            p = self.root / 'daemon' / directory
            p.mkdir(parents=True)
            git(p, 'init', '-b', 'test')
            git(p, 'config', 'user.name', 'Test Author')
            git(p, 'config', 'user.email', 'test@example.invalid')
            (p / 'base').write_text('upstream\n')
            git(p, 'add', 'base')
            git(p, 'commit', '-m', 'upstream')
            sha = git(p, 'rev-parse', 'HEAD')
            url = 'git@github.com:example/' + directory + '.git'
            git(p, 'remote', 'add', 'origin', url)
            s = {'path': 'daemon/' + directory, 'url': url, 'pin': sha,
                 'tree': git(p, 'rev-parse', 'HEAD^{tree}'), 'state': 'base',
                 'parent_series': 'ecash' if name == 'v2' else None}
            self.sources[name] = s
            git(self.root, 'config', '-f', '.gitmodules', 'submodule.'+s['path']+'.url', url)
            git(self.root, 'config', '-f', '.gitmodules', 'submodule.'+s['path']+'.path', s['path'])
            git(self.root, 'update-index', '--add', '--cacheinfo', '160000,'+sha+','+s['path'])
            d = self.root / 'daemon/patches' / name
            d.mkdir(parents=True)
            (d / 'one.patch').write_text('frozen review input\n')
            (d / 'series').write_text(('@include ../ecash/series\n' if name == 'v2' else '')+'one.patch\n')
            start = '1'*40 if name == 'v2' else sha
            tip = '2'*40 if name == 'v2' else '1'*40
            stages[name] = {'destination': s['path'], 'repository': url,
                'depends_on': s['parent_series'], 'historical_manifest': str((d/'series').relative_to(self.root)),
                'historical_manifest_sha256': hashlib.sha256((d/'series').read_bytes()).hexdigest(),
                'historical_mailboxes': [{'file': 'one.patch', 'sha256': hashlib.sha256((d/'one.patch').read_bytes()).hexdigest()}],
                'upstream_base': sha, 'input_commit': start, 'reviewed_reference_tip': tip,
                'commits': [{'commit': tip, 'parents': [start], 'subject': name+' change'}]}
        self.review = {'stages': stages}
        self.model = {'sources': self.sources, 'stack_review': 'daemon/stack-review.json'}
        self.write()

    def tearDown(self):
        self.tmp.cleanup()

    def write(self):
        p = self.root / self.model['stack_review']
        p.write_text(json.dumps(self.review))
        self.model['stack_review_sha256'] = hashlib.sha256(p.read_bytes()).hexdigest()
        (self.root / 'daemon/sources.json').write_text(json.dumps(self.model))

    def test_correct_repositories_and_exact_pins(self):
        p = Project(self.root)
        for key in self.sources:
            p.verify(key)
        self.assertEqual(list(p.plan('lotusd')), ['ecash', 'v2'])
        self.assertNotEqual(p.source('ecashd')[2], p.source('lotusd')[2])

    def test_setup_configures_engine_without_changing_source(self):
        p = Project(self.root)
        before = {k: git(p.source(k)[2], 'rev-parse', 'HEAD') for k in self.sources}
        p.setup('all')
        self.assertEqual(git(p.source('v2')[2], 'remote', 'get-url', 'engine'), self.sources['ecash']['url'])
        self.assertEqual(before, {k: git(p.source(k)[2], 'rev-parse', 'HEAD') for k in self.sources})

    def test_wrong_origin_is_rejected(self):
        p = Project(self.root)
        git(p.source('v2')[2], 'remote', 'set-url', 'origin', self.sources['ecash']['url'])
        with self.assertRaisesRegex(RuntimeError, 'Wrong origin'):
            p.verify('v2')

    def test_wrong_registered_url_is_rejected(self):
        git(self.root, 'config', '-f', '.gitmodules', 'submodule.daemon/lotusd.url', 'wrong')
        with self.assertRaisesRegex(RuntimeError, '.gitmodules URL'):
            Project(self.root).verify('v2')

    def test_clean_advanced_head_is_preserved(self):
        p = Project(self.root); repo = p.source('ecash')[2]
        git(repo, 'commit', '--allow-empty', '-m', 'local work')
        head = git(repo, 'rev-parse', 'HEAD')
        with self.assertRaisesRegex(RuntimeError, 'preserve'):
            p.setup('ecash')
        self.assertEqual(git(repo, 'rev-parse', 'HEAD'), head)

    def test_dirty_source_is_preserved(self):
        p = Project(self.root); file = p.source('ecash')[2] / 'base'
        file.write_text('important uncommitted work\n')
        with self.assertRaisesRegex(RuntimeError, 'source changes'):
            p.setup('ecash')
        self.assertEqual(file.read_text(), 'important uncommitted work\n')

    def test_base_only_cannot_build_or_release(self):
        with self.assertRaisesRegex(RuntimeError, 'base-only scaffold'):
            Project(self.root).require_ready('v2')

    def test_reordered_native_parent_is_rejected(self):
        self.review['stages']['v2']['commits'][0]['parents'] = ['9'*40]
        self.write()
        with self.assertRaisesRegex(RuntimeError, 'Nonlinear, reordered'):
            Project(self.root)

    def test_native_boundary_must_equal_engine_tip(self):
        s = self.review['stages']['v2']
        s['input_commit'] = '9'*40
        s['commits'][0]['parents'] = ['9'*40]
        self.write()
        with self.assertRaisesRegex(RuntimeError, 'exact reviewed ecash tip'):
            Project(self.root)

    def test_archival_patch_series_are_not_required_for_setup(self):
        before = Project(self.root).plan('v2')
        shutil.rmtree(self.root / 'daemon/patches')
        project = Project(self.root)
        project.setup('all')
        self.assertEqual(project.plan('v2'), before)

    def test_unreviewed_commit_order_digest_is_rejected(self):
        p = self.root / self.model['stack_review']
        p.write_text(p.read_text()+' ')
        with self.assertRaisesRegex(RuntimeError, 'Stack review changed'):
            Project(self.root)

    def test_source_path_cannot_escape_daemon(self):
        self.sources['ecash']['path'] = '../external'
        self.write()
        with self.assertRaisesRegex(RuntimeError, 'Invalid source path'):
            Project(self.root)

    def test_wrong_gitlink_is_rejected(self):
        p = Project(self.root); repo = p.source('ecash')[2]
        git(repo, 'commit', '--allow-empty', '-m', 'other pin')
        sha = git(repo, 'rev-parse', 'HEAD')
        git(self.root, 'update-index', '--cacheinfo', '160000,'+sha+',daemon/ecashd')
        with self.assertRaisesRegex(RuntimeError, 'Gitlink differs'):
            p.verify('ecash')

if __name__ == '__main__':
    unittest.main()
