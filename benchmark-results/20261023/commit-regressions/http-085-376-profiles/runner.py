#!/usr/bin/env python3
"""Run the preserved cheap-RPC control across two unit-gated HTTP boundaries."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import statistics
import subprocess
import sys

import run as audit

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--workers', type=int, choices=[1, 8], default=8)
    parser.add_argument('--points', default='85,86')
    parser.add_argument('--after-reference', action='store_true', help='Use the frozen original-history binary for the second point')
    parser.add_argument('--rounds', type=int, default=3)
    parser.add_argument('--sample', action='store_true', help='Diagnostic profiles; timings include sampler overhead')
    args = parser.parse_args()
    data = args.data.resolve()
    data.mkdir(parents=True, exist_ok=False)
    archive = audit.ROOT/'daemon/.local-artifact-archive/commit-regressions/template-test-order'
    probe = audit.ROOT/'daemon/patch-intake/20261021/triage/beast-json-array/size_probe.py'
    lock = (archive.parent/'benchmark-host.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    points = tuple(int(n) for n in args.points.split(','))
    assert len(points) == 2 and len(set(points)) == 2
    assert 1 <= args.rounds <= 8
    builds = {}
    for index, n in enumerate(points):
        cache = archive.parent if index == 1 and args.after_reference else archive
        builds[n] = json.loads((cache/f'point-{n:03}/BUILD.json').read_text())
    for n, build in builds.items():
        assert audit.sha(build['binary']) == build['binary_sha256']
        assert build['flags'] == audit.FLAGS
    audit.write(data/'INPUTS.json', dict(builds=builds, probe_sha256=audit.sha(probe),
                runner_sha256=audit.sha(__file__), seconds=5, workers=args.workers,
                method='echo', hex_bytes=207, sampling=args.sample, rounds=args.rounds,
                semantics='Cheap-RPC microbenchmark; not transaction acceptance or network completion. Sampled runs are diagnostics, not throughput claims.',
                cleanup='Fresh owned runtime data is ephemeral; copy results/logs, require daemon exit0, then remove'))
    shutil.copy2(__file__, data/'runner.py')
    rows = []
    for number in range(1, args.rounds+1):
        order = points if number % 2 else tuple(reversed(points))
        for point in order:
            name = f'round-{number}-point-{point:03}'
            runtime = archive/'transport-runtime'/data.name/name
            runtime.parent.mkdir(parents=True, exist_ok=True)
            assert not runtime.exists()
            directory = data/name
            directory.mkdir()
            command = [sys.executable, str(probe), '--binary', builds[point]['binary'],
                       '--output', str(runtime), '--port', '39201', '--duration', '5',
                       '--workers', str(args.workers), '--hex-bytes', '207']
            if args.sample:
                command.append('--sample')
            print('RUN', name, flush=True)
            resources = audit.guarded(command, directory/'stdout.log', dict(os.environ))
            result = json.loads((runtime/'results.json').read_text())
            assert result['status'] == 'PASS' and result['daemon_exit'] == 0 and not result.get('forced_kill')
            assert all(case['wall_seconds'] >= 5 for case in result['cases'])
            groups = subprocess.check_output(['ps','-axo','pgid='], text=True).split()
            assert str(resources['owned_group']) not in groups, 'Owned process group did not drain'
            audit.write(directory/'RESOURCES.json', resources)
            audit.write(directory/'result.json', result)
            shutil.copy2(runtime/'process.log', directory/'process.log')
            for path in runtime.rglob('debug.log'):
                shutil.copy2(path, directory/'debug.log')
            for path in runtime.glob('*.sample.txt'):
                shutil.copy2(path, directory/path.name)
            audit.write(directory/'CLEANUP.json', dict(runtime=str(runtime), disposition='remove generated datadir after clean exit and joined clients', daemon_exit=0))
            shutil.rmtree(runtime)
            rows.append(dict(point=point, round=number, result=result))
            audit.write(data/'RESULTS.json', dict(status='partial', runs=rows))
            print('RESULT', point, [(case['array_size'], round(case['calls_per_second'])) for case in result['cases']], flush=True)
    summary = []
    for size in (1, 50):
        groups = []
        for point in points:
            values = [case['calls_per_second'] for row in rows if row['point'] == point
                      for case in row['result']['cases'] if case['array_size'] == size]
            groups.append(dict(point=point, median=statistics.median(values), min=min(values), max=max(values), n=len(values)))
        summary.append(dict(array_size=size, groups=groups, change_percent=100*(groups[1]['median']/groups[0]['median']-1)))
    audit.write(data/'RESULTS.json', dict(status='complete', runs=rows, summary=summary))
    print(json.dumps(summary, indent=2))

if __name__ == '__main__':
    main()
