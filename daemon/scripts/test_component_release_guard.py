"""Execute the tag workflow's actual guard against synthetic CI artifacts."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import textwrap
import unittest


class ComponentWorkflowGuardTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('jq'), 'The workflow guard requires jq')
    def test_only_identical_component_validation_artifact_is_accepted(self):
        root = Path(__file__).resolve().parents[2]
        workflow = (root / '.github/workflows/release-components.yml').read_text()
        section = workflow.split('      - name: Check reviewed artifact validation and immutable release\n', 1)[1]
        block = section.split('        run: |\n', 1)[1].split('      - uses:', 1)[0]
        script = textwrap.dedent(block)
        with tempfile.TemporaryDirectory() as directory:
            checkout = Path(directory)
            (checkout / 'daemon/releases/bitcoin-core').mkdir(parents=True)
            shutil.copy2(root / 'daemon/components.json', checkout / 'daemon/components.json')
            manifest = {'component': 'bitcoin-core', 'tag': 'bitcoin-core-v1.0.0', 'source_tree': 'a' * 40}
            payload = (json.dumps(manifest, indent=2) + '\n').encode()
            (checkout / 'daemon/releases/bitcoin-core/manifest.json').write_bytes(payload)
            tools = checkout / 'bin'
            tools.mkdir()
            (tools / 'git').write_text('''#!/usr/bin/env python3
import sys
if sys.argv[1] == 'ls-remote':
    print('b'*40+'\\trefs/heads/main')
elif sys.argv[1] == 'for-each-ref':
    print('Validation run: 123')
else:
    raise SystemExit('Unexpected synthetic git call')
''')
            (tools / 'gh').write_text('''#!/usr/bin/env python3
import json, os, pathlib, shutil, sys
args=sys.argv[1:]
if args[:2] == ['run','view']:
    print(json.dumps({'headSha':'b'*40,'conclusion':'success','event':'workflow_dispatch','workflowName':'Daemon component artifacts and releases'}))
elif args[:2] == ['run','download']:
    assert args[args.index('--name')+1] == 'bitcoin-core-x86_64-linux-gnu'
    destination=pathlib.Path(args[args.index('--dir')+1])
    shutil.copy2(os.environ['SYNTHETIC_ARTIFACT'], destination/'manifest.json')
elif args[0] != 'api':
    raise SystemExit('Unexpected synthetic gh call')
''')
            for executable in tools.iterdir():
                executable.chmod(0o755)
            artifact = checkout / 'artifact.json'
            cases = {
                'identical': payload,
                'other-component': (json.dumps({**manifest, 'component': 'bchn'}) + '\n').encode(),
                'other-source': (json.dumps({**manifest, 'source_tree': 'c' * 40}) + '\n').encode(),
                'different-serialization': json.dumps(manifest).encode(),
            }
            for name, candidate in cases.items():
                with self.subTest(name=name):
                    artifact.write_bytes(candidate)
                    environment = {
                        **os.environ,
                        'PATH': str(tools) + os.pathsep + os.environ['PATH'],
                        'GITHUB_REF_NAME': manifest['tag'],
                        'GITHUB_SHA': 'b' * 40,
                        'GITHUB_ENV': str(checkout / 'github-env'),
                        'RUNNER_TEMP': str(checkout),
                        'SYNTHETIC_ARTIFACT': str(artifact),
                    }
                    result = subprocess.run(['bash', '-eo', 'pipefail', '-c', script],
                                            cwd=checkout, env=environment, capture_output=True, text=True)
                    if name == 'identical':
                        self.assertEqual(result.returncode, 0, result.stderr)
                    else:
                        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
