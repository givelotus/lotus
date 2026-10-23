#!/usr/bin/env python3
"""Alternate preserved reference/candidate binaries through the same admission runner."""
import argparse
import json
from pathlib import Path
import statistics
import subprocess
import sys

import run as audit

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--candidate-ref', required=True)
    parser.add_argument('--variant', required=True)
    parser.add_argument('--point', type=int, default=376)
    parser.add_argument('--plan', type=Path, default=audit.ROOT/'daemon/stack-review.json')
    parser.add_argument('--reference-variant', default='reference')
    parser.add_argument('--cases', default='single_tx_steady,json_rpc_batch50_steady')
    parser.add_argument('--reference-ref')
    parser.add_argument('--candidate-point', type=int)
    args = parser.parse_args()
    data = args.data.resolve()
    data.mkdir(parents=True, exist_ok=False)
    rows = []
    for number, order in enumerate((('reference','candidate'), ('candidate','reference'), ('reference','candidate')), 1):
        for side in order:
            directory = data/f'round-{number}-{side}'
            point = args.candidate_point if side=='candidate' and args.candidate_point is not None else args.point
            command = [sys.executable, str(Path(audit.__file__)), '--skip-build', '--points', str(point),
                       '--rounds', '1', '--data', str(directory), '--plan',str(args.plan),'--cases',args.cases]
            if side == 'candidate':
                command += ['--variant', args.variant, '--override-ref', f'{point}={args.candidate_ref}']
            elif args.reference_variant != 'reference':
                command += ['--variant',args.reference_variant]
            if side=='reference' and args.reference_ref:
                command += ['--override-ref',f'{point}={args.reference_ref}']
            print('PAIR', number, side, flush=True)
            subprocess.run(command, check=True)
            payload = json.loads((directory/'RESULTS.json').read_text())
            assert payload['status'] == 'complete'
            rows.extend(dict(side=side, pair=number, **row) for row in payload['runs'])
            audit.write(data/'RESULTS.json', dict(status='partial', runs=rows))
    summary = []
    for case in args.cases.split(','):
        groups = []
        for side in ('reference', 'candidate'):
            values = [r['result']['tx_count']/r['result']['seconds'] for r in rows if r['case'] == case and r['side'] == side]
            groups.append(dict(side=side, median=statistics.median(values), min=min(values), max=max(values), n=len(values)))
        summary.append(dict(case=case, groups=groups, change_percent=100*(groups[1]['median']/groups[0]['median']-1)))
        if case == 'single_tx_loaded_steady':
            reads = []
            for side in ('reference','candidate'):
                values = [r['result']['loaded_read']['rpc_per_second'] for r in rows if r['case']==case and r['side']==side]
                reads.append(dict(side=side,median=statistics.median(values),min=min(values),max=max(values),n=len(values)))
            summary.append(dict(case='concurrent_read_rpc_per_second',groups=reads,change_percent=100*(reads[1]['median']/reads[0]['median']-1)))
    audit.write(data/'RESULTS.json', dict(status='complete', runs=rows, summary=summary))
    print(json.dumps(summary, indent=2))

if __name__ == '__main__':
    main()
