"""Optional real offline daemon integration gate; explicit environment required."""
import hashlib
import importlib.util
from unittest.mock import patch
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

def load_pilot():
    name='lotus_v2_development_chain_pilot'
    spec=importlib.util.spec_from_file_location(name,Path(__file__).with_name('run.py'))
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    spec.loader.exec_module(module)
    return module

class SignedChainPilot(unittest.TestCase):
    def test_import_has_no_process_or_filesystem_side_effects(self):
        with patch.object(subprocess,'run',side_effect=AssertionError('process launched on import')), patch.object(Path,'mkdir',side_effect=AssertionError('directory created on import')):
            module=load_pilot()
        self.assertTrue(callable(module.run_pilot))
        self.assertTrue(callable(module.main))

    @unittest.skipUnless(os.environ.get('LOTUS_V2_PILOT_MANIFEST') and os.environ.get('LOTUS_V2_PILOT_DAEMON'), 'explicit manifest and built daemon required')
    def test_configurable_method_source_options_arguments_and_helper(self):
        module=load_pilot()
        with tempfile.TemporaryDirectory(prefix='lotus-v2-pilot-api-') as base:
            config=module.PilotConfig(Path(os.environ['LOTUS_V2_PILOT_MANIFEST']),Path(os.environ['LOTUS_V2_PILOT_DAEMON']),Path(base)/'run',os.environ.get('LOTUS_V2_PILOT_DAEMON_SOURCE','caller-supplied test binary'),
                compiler_helper=Path(__file__).with_name('payment.mjs'),
                source='contract Payment<owner: PublicKey> { function release(sig: Signature, x: Int) { require(x == 1); require(checksig(sig, owner)); } }',
                options={'optimize':False},method='release',arguments={'x':'1'},signature_argument='sig',
                reference_negative_errors=('CHECKSIG','VERIFY'),native_negative_errors=('CHECKSIG','VERIFY'))
            result=module.run_pilot(config)
            self.assertTrue(result['accepted'])
            artifact=json.loads((config.output/'payment-artifact.json').read_text())
            self.assertEqual(artifact['artifact']['methods'][0]['name'],'release')
            records=json.loads((config.output/'evidence.json').read_text())
            self.assertTrue(any(r['label']=='bad-signature-reference' for r in records))

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
