"""Exercise default-branch resolution used by daemon/scripts/refresh.sh."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[3]
RESOLVER = ROOT / 'daemon/scripts/upstream-ref.sh'


class UpstreamRefreshTests(unittest.TestCase):
    def git(self, cwd, *args, env=None):
        return subprocess.check_output(['git', '-C', str(cwd), *args], env=env)

    def test_latest_resolves_advertised_default_branch_after_fetch(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / 'source'
            remote = root / 'remote.git'
            workspace = root / 'workspace'
            subprocess.run(['git', 'init', '-q', '-b', 'main', str(source)], check=True)
            env = {**os.environ, 'GIT_AUTHOR_NAME': 'Fixture', 'GIT_AUTHOR_EMAIL': 'fixture@example.invalid',
                   'GIT_COMMITTER_NAME': 'Fixture', 'GIT_COMMITTER_EMAIL': 'fixture@example.invalid'}
            (source / 'state.txt').write_text('first\n')
            self.git(source, 'add', '.')
            subprocess.run(['git', '-C', str(source), 'commit', '-qm', 'first'], check=True, env=env)
            first = self.git(source, 'rev-parse', 'HEAD').decode().strip()
            subprocess.run(['git', 'clone', '-q', '--bare', str(source), str(remote)], check=True)
            self.git(remote, 'symbolic-ref', 'HEAD', 'refs/heads/main')
            subprocess.run(['git', 'clone', '-q', str(remote), str(workspace)], check=True)
            (source / 'state.txt').write_text('second\n')
            self.git(source, 'add', '.')
            subprocess.run(['git', '-C', str(source), 'commit', '-qm', 'second'], check=True, env=env)
            second = self.git(source, 'rev-parse', 'HEAD').decode().strip()
            subprocess.run(['git', '-C', str(source), 'push', '-q', str(remote), 'main'], check=True)

            resolved = subprocess.check_output(
                ['bash', '-c', 'source "$1"; resolve_upstream_ref "$2" latest',
                 'test', str(RESOLVER), str(workspace)], text=True).strip()
            self.assertEqual(resolved, second)
            self.assertNotEqual(resolved, first)

    def test_explicit_commit_stays_exact(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            subprocess.run(['git', 'init', '-q', '-b', 'main', str(root / 'source')], check=True)
            env = {**os.environ, 'GIT_AUTHOR_NAME': 'Fixture', 'GIT_AUTHOR_EMAIL': 'fixture@example.invalid',
                   'GIT_COMMITTER_NAME': 'Fixture', 'GIT_COMMITTER_EMAIL': 'fixture@example.invalid'}
            (root / 'source/state.txt').write_text('exact\n')
            self.git(root / 'source', 'add', '.')
            subprocess.run(['git', '-C', str(root / 'source'), 'commit', '-qm', 'exact'], check=True, env=env)
            subprocess.run(['git', 'clone', '-q', '--bare', str(root / 'source'), str(root / 'remote.git')], check=True)
            self.git(root / 'remote.git', 'symbolic-ref', 'HEAD', 'refs/heads/main')
            subprocess.run(['git', 'clone', '-q', str(root / 'remote.git'), str(root / 'workspace')], check=True)
            commit = self.git(root / 'workspace', 'rev-parse', 'HEAD').decode().strip()
            resolved = subprocess.check_output(
                ['bash', '-c', 'source "$1"; resolve_upstream_ref "$2" "$3"',
                 'test', str(RESOLVER), str(root / 'workspace'), commit], text=True).strip()
            self.assertEqual(resolved, commit)


if __name__ == '__main__':
    unittest.main()
