#!/usr/bin/env python3
"""Run one ABC-anchored matrix, retaining failed samples as explicit N/A.

Every sample still uses run.py's unmodified build receipts, startup/sync checks,
resource guards and measured workload. A failed sample contributes no rate.
"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import run as audit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--variant', required=True)
    parser.add_argument('--points', default='0,3,14,24,31,44,78,94,378')
    parser.add_argument('--rounds', type=int, default=3)
    parser.add_argument('--override-ref', action='append', default=[], metavar='POINT=REF')
    parser.add_argument('--point-variant', action='append', default=[], metavar='POINT=VARIANT')
    args = parser.parse_args()
    data = args.data.resolve()
    data.mkdir(parents=True, exist_ok=True)
    if (data/'RESULTS.json').exists() or any(data.glob('round-*')):
        raise RuntimeError('Existing attempts are immutable; choose a fresh study directory')
    plan_bytes = args.plan.read_bytes()
    plan_sha = hashlib.sha256(plan_bytes).hexdigest()
    points = [int(n) for n in args.points.split(',')]
    overrides = {int(n): ref for n, ref in (value.split('=', 1) for value in args.override_ref)}
    variants = {int(n): variant for n, variant in (value.split('=', 1) for value in args.point_variant)}
    assert set(overrides) <= set(points) and set(variants) <= set(points)
    assert points[0] == 0 and len(points) == len(set(points)) and args.rounds >= 1
    cases = ['single_tx_steady', 'json_rpc_batch50_steady', 'single_tx_loaded_steady']
    rows, failures = [], []
    for number in range(1, args.rounds+1):
        order = points if number % 2 else points[::-1]
        for point in order:
            for case in cases:
                assert hashlib.sha256(args.plan.read_bytes()).hexdigest() == plan_sha
                attempt = data/f'round-{number}'/f'point-{point:03}'/case
                attempt.mkdir(parents=True)
                command = [sys.executable, str(Path(audit.__file__)), '--skip-build', '--rounds', '1',
                           '--points', str(point), '--cases', case, '--variant', variants.get(point, args.variant),
                           '--plan', str(args.plan), '--data', str(attempt/'measurement')]
                if point in overrides:
                    command += ['--override-ref', f'{point}={overrides[point]}']
                audit.write(attempt/'COMMAND.json', dict(argv=command, history_plan_sha256=plan_sha,
                    outer_round=number, semantics='One independent fresh-node sample; failed synchronization is N/A'))
                print('SAMPLE', number, point, case, flush=True)
                with (attempt/'runner.log').open('w') as log:
                    outcome = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
                if outcome.returncode:
                    failures.append(dict(point=point, round=number, case=case,
                                         exit_code=outcome.returncode, evidence=str(attempt), disposition='N/A; no throughput credited'))
                    print('FAILED', number, point, case, flush=True)
                else:
                    payload = json.loads((attempt/'measurement/RESULTS.json').read_text())
                    assert payload['status'] == 'complete' and len(payload['runs']) == 1
                    row = payload['runs'][0]
                    row['round'] = number
                    row['outer_attempt'] = str(attempt)
                    rows.append(row)
                    print('MEASURED', number, point, case, round(row['result']['tx_count']/row['result']['seconds']), flush=True)
                audit.write(data/'RESULTS.json', dict(status='partial', history_plan_sha256=plan_sha,
                    runs=rows, failures=failures, source_overrides=overrides, cache_variants=variants,
                    semantics='ABC-anchored RPC acceptance/read progression; failed samples are N/A'))
    audit.write(data/'RESULTS.json', dict(status='complete_with_failures' if failures else 'complete',
        history_plan_sha256=plan_sha, runs=rows, failures=failures, source_overrides=overrides, cache_variants=variants,
        semantics='ABC-anchored RPC acceptance/read progression; ranges require individual-owner attribution'))


if __name__ == '__main__':
    main()
