"""Optional optimizer complete-block gate; evidence remains after failures."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class OptimizerChainPilot(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('LOTUS_V2_PILOT_MANIFEST') and os.environ.get('LOTUS_V2_PILOT_DAEMON'),
                         'explicit caller manifest and exact daemon required')
    def test_matrix(self):
        base=Path(tempfile.mkdtemp(prefix='lotus-v2-optimizer-pilot-'))
        output=base/'evidence'
        command=[sys.executable,str(Path(__file__).with_name('run.py')),
                 '--manifest',os.environ['LOTUS_V2_PILOT_MANIFEST'],
                 '--daemon',os.environ['LOTUS_V2_PILOT_DAEMON'],
                 '--daemon-source',os.environ.get('LOTUS_V2_PILOT_DAEMON_SOURCE','caller-supplied binary'),
                 '--output',str(output)]
        run=subprocess.run(command,capture_output=True,text=True,timeout=180)
        self.assertEqual(run.returncode,0,f'evidence: {output}\n{run.stdout}\n{run.stderr}')
        matrix=json.loads((output/'matrix.json').read_text())
        self.assertEqual(len(matrix),6)
        self.assertTrue(all(r['summary']['accepted'] for r in matrix))
        retained=json.loads((output/'cap-discrepancies.json').read_text())
        self.assertTrue(retained['observations'])
        previous=(output/'matrix.json').read_bytes()
        repeated=subprocess.run(command,capture_output=True,text=True,timeout=10)
        self.assertNotEqual(repeated.returncode,0)
        self.assertEqual((output/'matrix.json').read_bytes(),previous)
        print('Retained optimizer pilot evidence:',output)


if __name__=='__main__':unittest.main()
