"""Metadata and transactional replay checks; no daemon or live workspace required."""
import importlib.util
import hashlib
import json
import os
from pathlib import Path
import subprocess
import shutil
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('patch_series', SCRIPTS / 'patch-series.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
export_spec = importlib.util.spec_from_file_location('export_patch_series', SCRIPTS / 'export-patch-series.py')
export_module = importlib.util.module_from_spec(export_spec)
export_spec.loader.exec_module(export_module)


def git(repo, *args, **kwargs):
    return subprocess.check_output(['git', '-C', str(repo), *args], stderr=subprocess.PIPE, **kwargs)


class PatchMetadataTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='lotus-patch-tests-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / 'source'
        self.repo.mkdir()
        git(self.repo, 'init', '-q')
        git(self.repo, 'config', 'user.name', 'Fixture Committer')
        git(self.repo, 'config', 'user.email', 'committer@example.com')
        (self.repo / 'file').write_text('base\n')
        git(self.repo, 'add', 'file')
        git(self.repo, 'commit', '-qm', 'Base')
        self.base = git(self.repo, 'rev-parse', 'HEAD').decode().strip()
        self.patches = self.root / 'v1'
        self.patches.mkdir()
        self.manifest = self.patches / 'series'
        self.names = []
        self.metadata = []
        for number in range(2):
            (self.repo / 'file').write_text(f'change {number}\n')
            git(self.repo, 'add', 'file')
            env = dict(os.environ, GIT_AUTHOR_NAME='Historical Author', GIT_AUTHOR_EMAIL='history@example.com', GIT_AUTHOR_DATE='2021-02-24T11:40:51-05:00')
            git(self.repo, 'commit', '-qm', f'[backport#19601] Change {number}\n\nExplain why change {number} is required.\n\nQuoted historical example:\n    diff --git a/example b/example\n    --- a/example\n    +++ b/example', env=env)
            self.metadata.append(git(self.repo, 'show', '-s', '--format=%an%n%ae%n%aI%n%B%n%T', 'HEAD'))
            name = f'{number:03}.patch'
            self.names.append(name)
            (self.patches / name).write_bytes(git(self.repo, '-c', 'format.signature=', 'format-patch', '--stdout', '--binary', '-1'))
        self.manifest.write_text('\n'.join(self.names) + '\n')
        self.workspace = self.root / 'workspace'
        subprocess.run(['git', 'clone', '-q', '--shared', str(self.repo), str(self.workspace)], check=True)
        git(self.workspace, 'reset', '--hard', self.base)

    def assert_unchanged(self):
        self.assertEqual(git(self.workspace, 'rev-parse', 'HEAD').decode().strip(), self.base)
        self.assertEqual(git(self.workspace, 'status', '--porcelain'), b'')
        self.assertEqual((self.workspace / 'file').read_text(), 'base\n')

    def test_roundtrip_trees_authors_dates_and_messages(self):
        module.replay(self.workspace, self.manifest)
        commits = git(self.workspace, 'rev-list', '--reverse', f'{self.base}..HEAD').decode().splitlines()
        self.assertEqual(len(commits), 2)
        for commit, expected in zip(commits, self.metadata):
            self.assertEqual(git(self.workspace, 'show', '-s', '--format=%an%n%ae%n%aI%n%B%n%T', commit), expected)

    def test_base_only_series_requires_explicit_allow_empty(self):
        self.manifest.write_text('# Deliberately base only\n')
        with self.assertRaises(ValueError):
            module.replay(self.workspace, self.manifest)
        self.assert_unchanged()

        module.replay(self.workspace, self.manifest, base=self.base, allow_empty=True)
        self.assert_unchanged()

    def test_setup_base_only_uses_pin_and_refuses_reset(self):
        daemon = self.root / 'daemon'
        (daemon / 'scripts').mkdir(parents=True)
        for name in ('setup.sh', 'patch-series.py'):
            shutil.copy2(SCRIPTS / name, daemon / 'scripts' / name)
        series = daemon / 'patches/ecash'
        series.mkdir(parents=True)
        (series / 'series').write_text('# No experimental patches enabled\n')
        (daemon / 'bitcoin-abc-version').write_text(self.base + '\n')
        env = dict(os.environ, SERIES='ecash', BITCOIN_ABC_REMOTE=str(self.repo))
        subprocess.run(['bash', str(daemon / 'scripts/setup.sh')], env=env,
                       check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        workspace = daemon / 'workspace-ecash'
        self.assertEqual(git(workspace, 'rev-parse', 'HEAD').decode().strip(), self.base)
        sentinel = workspace / 'operator-data'
        sentinel.write_text('preserve\n')
        refused = subprocess.run(['bash', str(daemon / 'scripts/setup.sh'), '--reset'],
                                 env=env, capture_output=True)
        self.assertNotEqual(refused.returncode, 0)
        self.assertEqual(sentinel.read_text(), 'preserve\n')

    def test_setup_v1_works_with_system_bash(self):
        daemon = self.root / 'daemon-v1'
        (daemon / 'scripts').mkdir(parents=True)
        for name in ('setup.sh', 'patch-series.py'):
            shutil.copy2(SCRIPTS / name, daemon / 'scripts' / name)
        (daemon / 'patches').mkdir()
        shutil.copytree(self.patches, daemon / 'patches/v1')
        (daemon / 'bitcoin-abc-v1-version').write_text(self.base + '\n')
        env = dict(os.environ, SERIES='v1', BITCOIN_ABC_REMOTE=str(self.repo))
        subprocess.run(['/bin/bash', str(daemon / 'scripts/setup.sh')], env=env,
                       check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(git(daemon / 'workspace-v1', 'rev-parse', 'HEAD^{tree}'),
                         git(self.repo, 'rev-parse', 'HEAD^{tree}'))

    def test_late_conflict_does_not_leave_first_commit_or_am_state(self):
        patch = self.patches / self.names[1]
        patch.write_bytes(patch.read_bytes().replace(b'-change 0', b'-wrong base'))
        with self.assertRaises(subprocess.CalledProcessError):
            module.replay(self.workspace, self.manifest)
        self.assert_unchanged()
        self.assertFalse((self.workspace / '.git/rebase-apply').exists())

    def test_missing_duplicate_or_invalid_metadata_leaves_workspace_unchanged(self):
        patch = self.patches / self.names[1]
        original = patch.read_bytes()
        for invalid in (original.replace(b'Subject:', b'Not-Subject:'), original.replace(b'Subject:', b'Subject: duplicate\nSubject:'), original.replace(b'history@example.com', b'not-an-address'), original.replace(b'Date:', b'Date: invalid\nOriginal-Date:')):
            patch.write_bytes(invalid)
            with self.assertRaises(ValueError):
                module.replay(self.workspace, self.manifest)
            self.assert_unchanged()

    def test_dirty_workspace_rejected(self):
        (self.workspace / 'file').write_text('precious local changes\n')
        with self.assertRaises(ValueError):
            module.replay(self.workspace, self.manifest)
        self.assertEqual((self.workspace / 'file').read_text(), 'precious local changes\n')
        self.assertEqual(git(self.workspace, 'rev-parse', 'HEAD').decode().strip(), self.base)

    def test_manifest_traversal_rejected(self):
        self.manifest.write_text('../escape.patch\n')
        with self.assertRaises(ValueError):
            module.replay(self.workspace, self.manifest)
        self.assert_unchanged()

    def test_duplicate_manifest_rejected(self):
        self.manifest.write_text('\n'.join(self.names + self.names) + '\n')
        with self.assertRaises(ValueError):
            module.replay(self.workspace, self.manifest)
        self.assert_unchanged()

    def test_check_verifies_intermediate_trees_without_promotion(self):
        commits = git(self.repo, 'rev-list', '--reverse', f'{self.base}..HEAD').decode().splitlines()
        record = {'base': self.base, 'patches': [
            {'patch': name, 'tree': git(self.repo, 'rev-parse', commit + '^{tree}').decode().strip(),
             'metadata_sha256': hashlib.sha256(git(self.repo, 'show', '-s', '--format=%an%x00%ae%x00%aI%x00%B', commit)).hexdigest()}
            for name, commit in zip(self.names, commits)]}
        provenance = self.root / 'provenance.json'
        provenance.write_text(json.dumps(record))
        module.replay(self.workspace, self.manifest, check=True, provenance=provenance)
        self.assert_unchanged()
        recorded_hash = record['patches'][0]['metadata_sha256']
        record['patches'][0]['metadata_sha256'] = '0' * 64
        provenance.write_text(json.dumps(record))
        with self.assertRaises(ValueError):
            module.replay(self.workspace, self.manifest, provenance=provenance)
        self.assert_unchanged()
        record['patches'][0]['metadata_sha256'] = recorded_hash
        record['patches'][0]['tree'] = record['patches'][1]['tree']
        provenance.write_text(json.dumps(record))
        with self.assertRaises(ValueError):
            module.replay(self.workspace, self.manifest, provenance=provenance)
        self.assert_unchanged()

    def test_legacy_raw_reference_patch_supported(self):
        reference = self.root / 'reference'
        reference.mkdir()
        (reference / 'series').write_text('change.patch\n')
        (reference / 'change.patch').write_bytes(git(self.repo, 'diff', '--binary', self.base, 'HEAD'))
        module.replay(self.workspace, reference / 'series')
        self.assertEqual(git(self.workspace, 'rev-parse', 'HEAD^{tree}'), git(self.repo, 'rev-parse', 'HEAD^{tree}'))

    def test_binary_patch_roundtrip(self):
        (self.repo / 'binary').write_bytes(bytes(range(256)))
        git(self.repo, 'add', 'binary')
        git(self.repo, 'commit', '-qm', 'Add a binary fixture\n\nKeep binary patches intact.')
        (self.patches / 'binary.patch').write_bytes(git(self.repo, 'format-patch', '--stdout', '--binary', '-1'))
        self.manifest.write_text('\n'.join(self.names + ['binary.patch']) + '\n')
        module.replay(self.workspace, self.manifest)
        self.assertEqual(git(self.workspace, 'rev-parse', 'HEAD^{tree}'), git(self.repo, 'rev-parse', 'HEAD^{tree}'))

    def test_export_roundtrip_and_refusal_to_overwrite(self):
        destination = self.root / 'candidate'
        export_module.export(self.repo, self.base, self.manifest, destination)
        module.replay(self.workspace, destination / 'series')
        commits = git(self.workspace, 'rev-list', '--reverse', f'{self.base}..HEAD').decode().splitlines()
        for commit, expected in zip(commits, self.metadata):
            self.assertEqual(git(self.workspace, 'show', '-s', '--format=%an%n%ae%n%aI%n%B%n%T', commit), expected)
        with self.assertRaises(ValueError):
            export_module.export(self.repo, self.base, self.manifest, destination)

    def test_export_requires_exact_commit_count(self):
        self.manifest.write_text(self.names[0] + '\n')
        destination = self.root / 'candidate'
        with self.assertRaises(ValueError):
            export_module.export(self.repo, self.base, self.manifest, destination)
        self.assertFalse(destination.exists())


if __name__ == '__main__':
    unittest.main()
