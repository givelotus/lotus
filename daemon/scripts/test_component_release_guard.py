"""Exercise the tag workflow's exact-manifest and same-run artifact guards."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import textwrap
import unittest


class ComponentWorkflowGuardTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('jq'), 'The workflow guard requires jq')
    def test_release_requires_matching_tag_manifest_and_both_artifact_targets(self):
        root = Path(__file__).resolve().parents[2]
        workflow = (root / '.github/workflows/release-components.yml').read_text()
        section = workflow.split('      - name: Verify mainline tag and immutable release\n', 1)[1]
        guard = textwrap.dedent(section.split('        run: |\n', 1)[1].split('      - uses:', 1)[0])
        assets_section = workflow.split('      - name: Verify same-run component assets and checksums\n', 1)[1]
        assets = textwrap.dedent(assets_section.split('        run: |\n', 1)[1].split('      - uses:', 1)[0])

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            release_dir = root / 'daemon/releases/bitcoin-core'
            release_dir.mkdir(parents=True)
            shutil.copy2(Path(__file__).resolve().parents[2] / 'daemon/components.json',
                         root / 'daemon/components.json')
            manifest = {'component': 'bitcoin-core', 'tag': 'bitcoin-core-v1.0.0',
                        'source_tree': 'a' * 40}
            payload = (json.dumps(manifest, indent=2) + '\n').encode()
            (release_dir / 'manifest.json').write_bytes(payload)
            tools = root / 'bin'
            tools.mkdir()
            (tools / 'git').write_text('''#!/bin/sh
case "$1" in
  fetch|merge-base) exit 0 ;;
  *) echo "unexpected git command: $*" >&2; exit 2 ;;
esac
''')
            (tools / 'gh').write_text('''#!/bin/sh
case "$1" in
  api) exit 0 ;;
  *) echo "unexpected gh command: $*" >&2; exit 2 ;;
esac
''')
            for executable in tools.iterdir():
                executable.chmod(0o755)
            env = {'PATH': str(tools) + ':' + __import__('os').environ['PATH'],
                   'GITHUB_REF_NAME': manifest['tag'], 'GITHUB_SHA': 'b' * 40,
                   'GITHUB_ENV': str(root / 'github-env'), 'GH_TOKEN': 'test'}
            result = subprocess.run(['bash', '-eo', 'pipefail', '-c', guard],
                                    cwd=root, env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('RELEASE_COMPONENT=bitcoin-core', (root / 'github-env').read_text())

            assets_dir = root / 'release-assets'
            assets_dir.mkdir()
            (assets_dir / 'manifest.json').write_bytes(payload)
            (assets_dir / 'NOTES.md').write_text('candidate release\n')
            for target in ('x86_64-linux-gnu', 'arm64-apple-darwin'):
                (assets_dir / f'{manifest["tag"]}-{target}.tar.gz').write_bytes(target.encode())
                (assets_dir / f'build-info-{target}.json').write_text('{}\n')
            checksummed = list(assets_dir.glob('*.tar.gz'))
            with (assets_dir / 'candidate.sha256').open('w') as checksum_file:
                for path in checksummed:
                    import hashlib
                    checksum_file.write(f'{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n')
            asset_env = {**env, 'RELEASE_COMPONENT': 'bitcoin-core'}
            result = subprocess.run(['bash', '-eo', 'pipefail', '-c', assets],
                                    cwd=root, env=asset_env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            (assets_dir / 'manifest.json').write_text('{}\n')
            result = subprocess.run(['bash', '-eo', 'pipefail', '-c', assets],
                                    cwd=root, env=asset_env, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)


if __name__ == '__main__':
    unittest.main()
