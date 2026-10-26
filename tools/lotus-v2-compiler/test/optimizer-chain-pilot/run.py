"""Explicit opt-in optimizer matrix over the shared complete-block pilot."""
import argparse
import importlib.util
from contextlib import redirect_stdout, redirect_stderr
import hashlib
import json
import os
from pathlib import Path
import sys


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--daemon',type=Path,required=True)
    parser.add_argument('--daemon-source',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    args.output.mkdir()  # Exclusive; failures and prior observations survive.
    here=Path(__file__).resolve().parent
    spec=importlib.util.spec_from_file_location('shared_development_pilot',here.parent/'development-chain-pilot'/'run.py')
    pilot=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=pilot
    spec.loader.exec_module(pilot)
    records=[]
    try:
        for family in ('payment','equal','literal'):
            pair=[]
            for optimized in (False,True):
                label=f'{family}-'+('optimized' if optimized else 'unoptimized')
                output=args.output/label
                os.environ['LOTUS_V2_OPTIMIZER_FAMILY']=family
                os.environ['LOTUS_V2_OPTIMIZER_ENABLED']=str(int(optimized))
                config=pilot.PilotConfig(manifest=args.manifest.resolve(),daemon=args.daemon.resolve(),
                    output=output.resolve(),daemon_source=args.daemon_source,
                    compiler_helper=here/'payment.mjs',
                    reference_negative_errors=('CHECKSIG','VERIFY'),
                    native_negative_errors=('CHECKSIG','VERIFY'))
                with (args.output/(label+'.stdout')).open('w') as stdout, (args.output/(label+'.stderr')).open('w') as stderr:
                    with redirect_stdout(stdout),redirect_stderr(stderr):
                        pilot.run_pilot(config)
                summary=json.loads((output/'summary.json').read_text())
                artifact=json.loads((output/'payment-artifact.json').read_text())['artifact']
                evidence=json.loads((output/'evidence.json').read_text())
                accepted=next(r for r in evidence if r['label']=='signed-spend-reference')
                negative=next(r for r in evidence if r['label']=='bad-signature')
                assert summary['accepted'] and negative['exit']==2
                if family=='equal':
                    assert next(r for r in evidence if r['label']=='wrong-integer')['exit']==2
                entry=dict(family=family,optimized=optimized,summary=summary,
                           script=artifact['methods'][0]['scriptHex'],policy=artifact['policy']['root'],
                           charges=accepted['charges'],transaction_ids=accepted['transaction_ids'],
                           transaction_hashes=accepted['transaction_hashes'],negative_exit=negative['exit'])
                records.append(entry);pair.append(entry)
                (args.output/'matrix.json').write_text(json.dumps(records,indent=2)+'\n')
            assert pair[0]['summary']['accepted']==pair[1]['summary']['accepted']
            assert pair[0]['negative_exit']==pair[1]['negative_exit']
            assert pair[0]['script']!=pair[1]['script']
            assert pair[0]['policy']!=pair[1]['policy']
            assert pair[0]['summary']['state_root']!=pair[1]['summary']['state_root']
            # Each native/reference charge check happens inside the shared pilot.
            # Changed byte commitments and charges are deliberately retained.
        corpus=here.parent.parent/'fixtures'/'optimizer-equivalence'/'observations.json'
        prior=json.loads(corpus.read_text())
        discrepancies=[o for o in prior['observations'] if any(a['status']!=b['status'] for a,b in o['boundaries'])]
        assert discrepancies,'retain original exact-cap acceptance discrepancies'
        (args.output/'cap-discrepancies.json').write_text(json.dumps(dict(
            source_sha256=hashlib.sha256(corpus.read_bytes()).hexdigest(),observations=discrepancies),indent=2)+'\n')
        print('Optimizer complete-block matrix passed:',args.output)
    except Exception as error:
        (args.output/'failure.json').write_text(json.dumps(dict(kind=type(error).__name__,error=str(error)),indent=2)+'\n')
        raise


if __name__=='__main__':main()
