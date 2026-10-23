#!/usr/bin/env python3
"""Freeze one node binary and rotate process/concurrency capacity experiments."""
import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location('audit', ROOT / 'daemon/bench/commit-regressions/run.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--rounds', type=int, default=3)
    parser.add_argument('--cells', default='single_tx_steady:1:8:0,single_tx_steady:4:8:0,single_tx_loaded_steady:1:8:12,single_tx_loaded_steady:4:8:12')
    parser.add_argument('--reads', action='store_true')
    parser.add_argument('--smoke', action='store_true')
    parser.add_argument('--series', choices=['l1', 'v2'], default='l1')
    parser.add_argument('--build-receipt', type=Path)
    parser.add_argument('--fixture-transactions', type=int, default=500000)
    parser.add_argument('--transport-calibration', action='store_true')
    parser.add_argument('--fixture-hash-site', type=Path)
    parser.add_argument('--global-warmup', action='store_true')
    args = parser.parse_args()
    data = args.data.resolve()
    data.mkdir(parents=True, exist_ok=False)
    lock = (ROOT / 'daemon/.local-artifact-archive/benchmark-host.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    source_lock = (audit.SOURCE / '.git/progression.lock').open('a')
    fcntl.flock(source_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    receipt_path = args.build_receipt or ROOT / 'daemon/.local-artifact-archive/commit-regressions/async-admission-and-info/point-377/BUILD.json'
    receipt = json.loads(receipt_path.read_text())
    assert audit.sha(receipt['binary']) == receipt['binary_sha256']
    audit.checkout(receipt['commit'])
    tools = {str(p.relative_to(ROOT)): audit.sha(p) for p in Path(__file__).parent.glob('*.py')}
    audit.write(data / 'INPUTS.json', {'source': receipt, 'tools': tools, 'argv': sys.argv,
                'policy': 'One fixed node binary; same8writers/12readers when comparing process count; >=5s each; processes warmed before common GO; no timing during builds/profiling'})
    cells = [cell.split(':') for cell in args.cells.split(',')]
    rows = []
    for round_number in range(1, args.rounds + 1):
        order = cells if round_number % 2 else list(reversed(cells))
        for case, processes, writers, readers in order:
            processes, writers, readers = map(int, (processes, writers, readers))
            label = f'{case}-p{processes}-w{writers}-r{readers}'
            directory = data / f'round-{round_number}' / label
            directory.mkdir(parents=True)
            config = dict(processes=processes, writers=writers, readers=readers,
                          directory=str(directory), read_matrix=args.reads and not rows,
                          transport_calibration=args.transport_calibration and not rows,
                          global_warmup=args.global_warmup)
            path = directory / 'CONFIG.json'
            audit.write(path, config)
            output = directory / 'result.json'
            command = [sys.executable, Path(__file__).with_name('adapter.py'), '--series', args.series,
                       '--daemon', receipt['binary'], '--source', audit.SOURCE, '--output', output,
                       '--steady', '--case', case, '--max-fixture-transactions', '1200000',
                       '--fixture-fee-sats', '10000', '--hierarchical-funding',
                       '--maxmempool-mb', '4096', '--port-base', '39110']
            if not args.smoke:
                command += ['--exact-fixture-transactions', str(args.fixture_transactions)]
            if args.fixture_hash_site:
                assert args.series == 'v2'
                command += ['--fixture-hash-site', args.fixture_hash_site.resolve()]
            print('RUN', round_number, label, flush=True)
            env = dict(os.environ, CAPACITY_CONFIG=str(path),
                       TMPDIR=str(ROOT / 'daemon/.local-artifact-archive/commit-regressions/runtime'))
            resources = audit.guarded(command, directory / 'stdout.log', env)
            audit.write(directory / 'RESOURCES.json', resources)
            payload = json.loads(output.read_text())
            assert payload['status'] == 'ok'
            result = payload['metrics'][case]
            assert result['seconds'] >= 5 and result['tx_count'] > 0
            rows.append(dict(round=round_number, label=label, result=result, evidence=str(output)))
            audit.write(data / 'RESULTS.json', dict(status='partial', runs=rows))
            print('RESULT', round_number, label, result['tps'], result['client_cpu_seconds'], result['node_cpu_seconds'], flush=True)
    audit.write(data / 'RESULTS.json', dict(status='complete', runs=rows))


if __name__ == '__main__':
    main()
