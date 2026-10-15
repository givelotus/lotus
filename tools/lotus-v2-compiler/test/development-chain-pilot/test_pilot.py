"""Optional real offline daemon integration gate; explicit environment required."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

class SignedChainPilot(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('LOTUS_V2_PILOT_MANIFEST') and os.environ.get('LOTUS_V2_PILOT_DAEMON'), 'explicit manifest and built daemon required')
    def test_complete_signed_chain_and_exclusive_evidence(self):
        with tempfile.TemporaryDirectory(prefix='lotus-v2-pilot-test-') as base:
            output=Path(base)/'run'
            cmd=[sys.executable,str(Path(__file__).with_name('run.py')),
                '--manifest',os.environ['LOTUS_V2_PILOT_MANIFEST'],
                '--daemon',os.environ['LOTUS_V2_PILOT_DAEMON'],
                '--daemon-source',os.environ.get('LOTUS_V2_PILOT_DAEMON_SOURCE','caller-supplied test binary'),
                '--output',str(output)]
            first=subprocess.run(cmd,capture_output=True,text=True,timeout=60)
            self.assertEqual(first.returncode,0,first.stdout+first.stderr)
            summary=json.loads((output/'summary.json').read_text())
            self.assertTrue(summary['accepted'])
            records=json.loads((output/'evidence.json').read_text())
            signed=next(r for r in records if r['label']=='signed-spend-reference')
            self.assertGreater(int(signed['charges']['invocation']),0)
            self.assertEqual(int(signed['charges']['fees']),1000)
            for label in ['immature-spend','bad-signature']:
                self.assertEqual(next(r for r in records if r['label']==label)['exit'],2)
            end=next(r for r in records if r['label']=='reconnect-restart')
            self.assertEqual(json.loads(end['stdout'])['state_root'],summary['state_root'])
            evidence=hashlib.sha256((output/'evidence.json').read_bytes()).digest()
            repeated=subprocess.run(cmd,capture_output=True,text=True,timeout=10)
            self.assertNotEqual(repeated.returncode,0)
            self.assertEqual(hashlib.sha256((output/'evidence.json').read_bytes()).digest(),evidence)

if __name__=='__main__':unittest.main()
