"""Explicit native-wallet/full-block integration gate."""
import importlib.util
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

class WalletChainPilot(unittest.TestCase):
    def test_import_never_creates_wallet_or_launches_process(self):
        spec=importlib.util.spec_from_file_location('wallet_chain_pilot',Path(__file__).with_name('run.py'))
        module=importlib.util.module_from_spec(spec)
        with patch.object(subprocess,'run',side_effect=AssertionError('import launched process')),patch.object(Path,'mkdir',side_effect=AssertionError('import created wallet')):
            spec.loader.exec_module(module)
        self.assertTrue(callable(module.main))

    @unittest.skipUnless(all(os.environ.get(k) for k in ['LOTUS_V2_PILOT_MANIFEST','LOTUS_V2_PILOT_DAEMON','LOTUS_V2_WALLET_HELPER']), 'explicit manifest, daemon and native wallet helper required')
    def test_real_encrypted_wallet_bytes_accepted_by_both_complete_engines(self):
        with tempfile.TemporaryDirectory(prefix='lotus-v2-wallet-chain-test-') as base:
            output=Path(base)/'run'
            command=[sys.executable,str(Path(__file__).with_name('run.py')),
                '--manifest',os.environ['LOTUS_V2_PILOT_MANIFEST'],'--daemon',os.environ['LOTUS_V2_PILOT_DAEMON'],
                '--daemon-source',os.environ.get('LOTUS_V2_PILOT_DAEMON_SOURCE','explicit caller test daemon'),
                '--wallet-helper',os.environ['LOTUS_V2_WALLET_HELPER'],'--wallet-source',os.environ.get('LOTUS_V2_WALLET_SOURCE','explicit caller native helper'),
                '--output',str(output)]
            result=subprocess.run(command,capture_output=True,text=True,timeout=120)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertFalse((output/'temporary-passphrase').exists())
            self.assertTrue((output/'wallet/wallet.sqlite').exists())
            evidence=json.loads((output/'evidence.json').read_text())
            probe=next(item for item in evidence if item['label']=='immature-wallet-probe')
            self.assertFalse(probe['probe']['accepted'])
            signed=next(item for item in evidence if item['label']=='signed-spend-reference')
            self.assertGreater(int(signed['charges']['invocation']),0)
            self.assertEqual(int(signed['charges']['fees']),1000)
            native=next(item for item in evidence if item['label']=='signed-spend')
            self.assertEqual(json.loads(native['stdout'])['charges'],signed['charges'])
            self.assertEqual(next(item for item in evidence if item['label']=='bad-signature')['exit'],2)
            wallet_events=json.loads((output/'wallet-evidence.json').read_text())
            stale=next(item for item in wallet_events if item['operation']=='stale')
            self.assertEqual(stale['exit'],2)
            self.assertEqual(json.loads(stale['stdout'])['result'],'stale')
            self.assertNotIn('wire',json.loads(stale['stdout']))
            digest=hashlib.sha256((output/'wallet-evidence.json').read_bytes()).digest()
            repeated=subprocess.run(command,capture_output=True,text=True,timeout=10)
            self.assertNotEqual(repeated.returncode,0)
            self.assertEqual(hashlib.sha256((output/'wallet-evidence.json').read_bytes()).digest(),digest)

if __name__=='__main__':unittest.main()
