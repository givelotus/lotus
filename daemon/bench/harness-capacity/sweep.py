#!/usr/bin/env python3
"""Paired blocking-vs-co_await sweep, fixed generator and total concurrency."""
import argparse
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location('audit', ROOT / 'daemon/bench/commit-regressions/run.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--counts', default='1,2,4,8,16,32')
    parser.add_argument('--rounds', type=int, default=3)
    parser.add_argument('--fixture-transactions', type=int, default=150000)
    parser.add_argument('--seed-results', type=Path)
    parser.add_argument('--client-counts', help='Balanced submitter/reader totals; hold RPC workers at16')
    parser.add_argument('--profile', action='store_true', help='Diagnostic samples; exclude throughput')
    args = parser.parse_args()
    data = args.data.resolve()
    data.mkdir(parents=True, exist_ok=False)
    lock = (ROOT / 'daemon/.local-artifact-archive/benchmark-host.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    source_lock = (audit.SOURCE / '.git/progression.lock').open('a')
    fcntl.flock(source_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    sources = {}
    for side, variant in [('blocking', 'queue-only-fixture-corrected'),
                          ('co_await', 'async-admission-only')]:
        receipt = ROOT / 'daemon/.local-artifact-archive/commit-regressions' / variant / 'point-377/BUILD.json'
        sources[side] = json.loads(receipt.read_text())
        assert audit.sha(sources[side]['binary']) == sources[side]['binary_sha256']
    audit.write(data / 'INPUTS.json', {'sources': sources, 'argv': sys.argv,
                'tools': {str(p.relative_to(ROOT)): audit.sha(p) for p in Path(__file__).parent.glob('*.py')},
                'constant': {'generator_processes': 8 if args.client_counts else 4,
                             'submitters': 'half of client count' if args.client_counts else 8,
                             'readers': 'half of client count' if args.client_counts else 12,
                             'rpc_workers': 16 if args.client_counts else 'varied',
                             'methods': ['getmempoolinfo', 'getblockchaininfo'],
                             'seconds': 5, 'fixture_transactions': args.fixture_transactions},
                'diagnostic_profiles': args.profile,
                'isolation': 'Async-only vs blocking; no atomic-reader changes; same negotiated P2P behavior; fixed16total warmup transactions; no builds'})
    counts = list(map(int, (args.client_counts or args.counts).split(',')))
    if args.client_counts:
        assert all(n >= 16 and n % 16 == 0 for n in counts)
        assert args.seed_results is None
    rows = []
    if args.seed_results:
        seed = json.loads(args.seed_results.read_text())
        seed_inputs = json.loads(args.seed_results.with_name('INPUTS.json').read_text())
        inputs = json.loads((data / 'INPUTS.json').read_text())
        assert seed['status'] == 'complete'
        assert seed_inputs['constant'] == inputs['constant'] and seed_inputs['sources'] == sources
        rows = seed['runs']
        assert all(r['rpc_workers'] in counts and r['round'] <= args.rounds for r in rows)
        audit.write(data / 'SEED.json', {'path': str(args.seed_results.resolve()),
                    'sha256': audit.sha(args.seed_results), 'samples': len(rows)})
    completed = {(r['round'], r['rpc_workers'], r['side']) for r in rows}
    for number in range(1, args.rounds + 1):
        order = counts if number % 2 else list(reversed(counts))
        for index, axis_count in enumerate(order):
            workers = 16 if args.client_counts else axis_count
            sides = ['blocking', 'co_await'] if (number + index) % 2 else ['co_await', 'blocking']
            for side in sides:
                if (number, workers, side) in completed:
                    continue
                receipt = sources[side]
                audit.checkout(receipt['commit'])
                label = f'clients-{axis_count}' if args.client_counts else f'rpc-{workers}'
                directory = data / f'round-{number}' / f'{label}-{side}'
                directory.mkdir(parents=True)
                config = dict(processes=8 if args.client_counts else 4,
                              writers=axis_count // 2 if args.client_counts else 8,
                              readers=axis_count // 2 if args.client_counts else 12,
                              global_warmup=bool(args.client_counts), rpc_workers=workers,
                              directory=str(directory))
                path = directory / 'CONFIG.json'
                audit.write(path, config)
                output = directory / 'result.json'
                command = [sys.executable, Path(__file__).with_name('adapter.py'), '--series', 'l1',
                           '--daemon', receipt['binary'], '--source', audit.SOURCE, '--output', output,
                           '--steady', '--case', 'single_tx_loaded_steady',
                           '--max-fixture-transactions', '800000', '--fixture-fee-sats', '10000',
                           '--hierarchical-funding', '--maxmempool-mb', '4096', '--port-base', '39110',
                           '--exact-fixture-transactions', str(args.fixture_transactions)]
                if args.profile:
                    command += ['--sample-node0-output', directory / 'node0.sample.txt']
                print('RUN', number, label, side, flush=True)
                env = dict(os.environ, CAPACITY_CONFIG=str(path),
                           TMPDIR=str(ROOT / 'daemon/.local-artifact-archive/commit-regressions/runtime'))
                resources = audit.guarded(command, directory / 'stdout.log', env)
                audit.write(directory / 'RESOURCES.json', resources)
                payload = json.loads(output.read_text())
                assert payload['status'] == 'ok'
                result = payload['metrics']['single_tx_loaded_steady']
                if args.profile:
                    result['throughput_publishable'] = False
                assert result['seconds'] >= 5 and result['tx_count'] > 0
                rows.append(dict(round=number, rpc_workers=workers, side=side,
                                 axis_count=axis_count, client_workers=config['writers'] + config['readers'],
                                 result=result, source=receipt, evidence=str(output)))
                audit.write(data / 'RESULTS.json', dict(status='partial', runs=rows))
                if args.profile:
                    print('PROFILE DONE', number, label, side, flush=True)
                else:
                    print('RESULT', number, label, side, result['tps'],
                          result['loaded_read']['rpc_per_second'], flush=True)
    if args.profile:
        audit.write(data / 'RESULTS.json', dict(status='complete', runs=rows,
                    kind='diagnostic profiles; instrumented throughput excluded'))
        return
    summary = []
    for axis_count in counts:
        workers = 16 if args.client_counts else axis_count
        groups = {}
        for side in sources:
            selected = [r['result'] for r in rows if r.get('axis_count', r['rpc_workers']) == axis_count and r['side'] == side]
            groups[side] = {}
            for metric in ('tps', 'reads'):
                values = [r['tps'] if metric == 'tps' else r['loaded_read']['rpc_per_second'] for r in selected]
                groups[side][metric] = dict(median=statistics.median(values), min=min(values), max=max(values), n=len(values))
        summary.append(dict(rpc_workers=workers, groups=groups,
                       axis_count=axis_count, axis='client_workers' if args.client_counts else 'rpc_workers',
                       tps_change=100 * (groups['co_await']['tps']['median'] / groups['blocking']['tps']['median'] - 1),
                       read_change=100 * (groups['co_await']['reads']['median'] / groups['blocking']['reads']['median'] - 1)))
    audit.write(data / 'RESULTS.json', dict(status='complete', runs=rows, summary=summary))
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
