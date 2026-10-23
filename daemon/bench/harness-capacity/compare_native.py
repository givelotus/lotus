#!/usr/bin/env python3
"""Three alternating native batch pairs with fixed generator concurrency."""
import argparse
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location('audit', ROOT / 'daemon/bench/commit-regressions/run.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--before', type=Path, required=True)
    parser.add_argument('--after', type=Path, required=True)
    parser.add_argument('--fixture-transactions', type=int, default=1000000)
    parser.add_argument('--owned-rss-limit-gib', type=int, choices=(12,18), default=12)
    args = parser.parse_args()
    if not 800000 <= args.fixture_transactions <= 1200000:
        parser.error('Use800K..1.2M distinct transactions within the recorded memory envelope')
    data = args.data.resolve()
    data.mkdir(parents=True, exist_ok=False)
    receipts = {name: json.loads(getattr(args, name).read_text()) for name in ('before', 'after')}
    assert receipts['before']['flags'] == receipts['after']['flags'], 'Build flags differ'
    for receipt in receipts.values():
        assert audit.sha(receipt['binary']) == receipt['binary_sha256']
    with (ROOT / 'daemon/.local-artifact-archive/benchmark-host.lock').open('a') as host_lock, \
            (audit.SOURCE / '.git/progression.lock').open('a') as source_lock:
        for lock in (host_lock, source_lock):
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        previous = audit.git('rev-parse', 'HEAD')
        audit.write(data / 'INPUTS.json', dict(receipts=receipts,
            tools={str(p.relative_to(ROOT)): audit.sha(p) for p in [*Path(__file__).parent.glob('*.py'), ROOT / 'daemon/bench/commit-regressions/run.py']},
            policy='Three alternating pairs; 4 generator processes, 8 writers, 0 readers, batch200, fixed distinct signed native fixtures, fixed3200 warmup; >=5s; no profiler/build during timing; exact source inventory required',
            fixture_transactions=args.fixture_transactions, owned_rss_limit_gib=args.owned_rss_limit_gib,
            scope='Validated native V2 acceptance, not peer convergence, block confirmation or Avalanche finality'))
        rows = []
        try:
            for round_number in range(1, 4):
                for side in (('before', 'after') if round_number % 2 else ('after', 'before')):
                    receipt = receipts[side]
                    audit.checkout(receipt['commit'])
                    directory = data / f'round-{round_number}' / side
                    directory.mkdir(parents=True)
                    config = directory / 'CONFIG.json'
                    audit.write(config, dict(processes=4, writers=8, readers=0,
                        directory=str(directory), read_matrix=False, transport_calibration=False))
                    command = [sys.executable, Path(__file__).with_name('adapter.py'), '--series', 'v2',
                        '--daemon', receipt['binary'], '--source', audit.SOURCE,
                        '--output', directory / 'result.json', '--steady', '--case', 'signed_batch200_steady',
                        '--max-fixture-transactions', '1200000', '--exact-fixture-transactions', str(args.fixture_transactions),
                        '--fixture-hash-site', ROOT / 'daemon/.local-artifact-archive/fixture-hash-site',
                        '--fixture-fee-sats', '10000', '--hierarchical-funding',
                        '--maxmempool-mb', '4096', '--port-base', '39110']
                    print('RUN', round_number, side, flush=True)
                    resources = audit.guarded(command, directory / 'stdout.log', dict(os.environ,
                        CAPACITY_CONFIG=str(config),
                        TMPDIR=str(ROOT / 'daemon/.local-artifact-archive/commit-regressions/runtime')),
                        owned_rss_limit_gib=args.owned_rss_limit_gib)
                    audit.write(directory / 'RESOURCES.json', resources)
                    payload = json.loads((directory / 'result.json').read_text())
                    assert payload['status'] == 'ok'
                    metric = payload['metrics']['signed_batch200_steady']
                    assert metric['seconds'] >= 5 and metric['tx_count'] > 0
                    rows.append(dict(round=round_number, side=side, result=metric))
                    audit.write(data / 'RESULTS.json', dict(status='partial', runs=rows))
                    print('RESULT', round_number, side, metric['tps'], flush=True)
            medians = {side: statistics.median(row['result']['tps'] for row in rows if row['side'] == side)
                       for side in receipts}
            audit.write(data / 'RESULTS.json', dict(status='complete', runs=rows, medians=medians,
                ratio=medians['after']/medians['before']))
        finally:
            audit.checkout(previous)


if __name__ == '__main__':
    main()
