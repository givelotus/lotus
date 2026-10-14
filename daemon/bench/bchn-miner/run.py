#!/usr/bin/env python3
"""Build and compare two immutable BCHN revisions with an identical benchmark overlay."""
import argparse
import hashlib
import json
import platform
import re
import statistics
import subprocess
from pathlib import Path

BASE = 'abd433abe04f74780744b9eac06731f3690ce68a'
PATCH = '640b8bd1c8e88107421a201828eaaf2b46802b28'
FLAGS = ['-GNinja', '-DCMAKE_BUILD_TYPE=Release', '-DBUILD_BITCOIN_QT=OFF',
         '-DBUILD_BITCOIN_ZMQ=OFF', '-DENABLE_MAN=OFF', '-DENABLE_UPNP=OFF',
         '-DENABLE_NATPMP=OFF']
HERE = Path(__file__).resolve().parent


def command(args, **kw):
    return subprocess.check_output([str(x) for x in args], text=True, **kw).strip()


def percentile(values, q):
    values = sorted(values)
    pos = (len(values) - 1) * q
    a = int(pos)
    return values[a] + (values[min(a + 1, len(values) - 1)] - values[a]) * (pos - a)


def summarize(output):
    records = {}
    for path in sorted(output.glob('run-*.log')):
        side = path.stem.split('-')[2]
        for line in path.read_text().splitlines():
            parts = line.split(',')
            if line.startswith('# fixture,'):
                name = parts[1]
                keys = ['transactions', 'dependency_edges', 'transaction_bytes', 'block_limit_bytes',
                        'selected_transactions', 'actual_fees_sats', 'modified_fees_sats', 'block_bytes']
                fixture = dict(zip(keys, map(int, parts[2:])))
                record = records.setdefault(name, {}).setdefault(side, {'samples_ns': [], 'fixtures': []})
                if fixture not in record['fixtures']:
                    record['fixtures'].append(fixture)
            elif line.startswith('# samples_ns,'):
                records.setdefault(parts[1], {}).setdefault(side, {'samples_ns': [], 'fixtures': []})['samples_ns'].extend(map(int, parts[2:]))
            elif re.match(r'^(AssembleBlock|GenerateBlock\d+ChainedTxs),', line):
                record = records.setdefault(parts[0], {}).setdefault(side, {'upstream_batches': []})
                record['upstream_batches'].append(dict(zip(['evals', 'iterations', 'total_seconds', 'min_seconds', 'max_seconds', 'median_seconds'], map(float, parts[1:]))))
    for name, pair in records.items():
        for side, record in pair.items():
            samples = record.get('samples_ns')
            if samples:
                record['summary_ms'] = {'count': len(samples), 'median': statistics.median(samples) / 1e6,
                                        'p10': percentile(samples, .1) / 1e6,
                                        'p90': percentile(samples, .9) / 1e6,
                                        'min': min(samples) / 1e6, 'max': max(samples) / 1e6}
            else:
                record['summary_ms'] = {'median': statistics.median(x['median_seconds'] for x in record['upstream_batches']) * 1000}
        if 'base' in pair and 'patch' in pair:
            pair['median_change_percent'] = 100 * (pair['patch']['summary_ms']['median'] / pair['base']['summary_ms']['median'] - 1)
    (output / 'results.json').write_text(json.dumps(records, indent=2) + '\n')
    return records


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source', type=Path, help='Local BCHN Git repository containing both exact revisions')
    ap.add_argument('--output', required=True, type=Path, help='Fresh artifact directory (or existing with --summarize)')
    ap.add_argument('--jobs', type=int, default=6)
    ap.add_argument('--rounds', type=int, default=3)
    ap.add_argument('--evals', type=int, default=3)
    ap.add_argument('--prepared-prefix', type=Path, help='Use prebuilt SOURCE_PREFIX-{base,patch}-20261014 and corresponding -build- paths')
    ap.add_argument('--summarize', action='store_true')
    args = ap.parse_args()
    if args.summarize:
        summarize(args.output)
        return
    if args.rounds < 1 or args.evals < 1:
        ap.error('rounds and evals must be positive')
    args.output.mkdir(parents=True, exist_ok=False)
    overlay = (HERE / 'ready_backlog.cpp').read_bytes()
    binaries = {}
    build_details = {}
    for side, revision in [('base', BASE), ('patch', PATCH)]:
        if args.prepared_prefix:
            src = Path(str(args.prepared_prefix) + f'-{side}-20261014')
            build = Path(str(args.prepared_prefix) + f'-{side}-build-20261014')
        else:
            if not args.source:
                ap.error('--source is required without --prepared-prefix')
            src, build = args.output / f'source-{side}', args.output / f'build-{side}'
            command(['git', 'clone', '--no-hardlinks', '--no-checkout', args.source, src])
            command(['git', '-C', src, 'checkout', '--detach', revision])
            (src / 'src/bench/ready_backlog.cpp').write_bytes(overlay)
            cmake = src / 'src/bench/CMakeLists.txt'
            cmake.write_text(cmake.read_text().replace('\tblock_assemble.cpp', '\tblock_assemble.cpp\n\tready_backlog.cpp'))
            with (args.output / f'build-{side}.log').open('w') as log:
                subprocess.run(['cmake', '-S', src, '-B', build, *FLAGS], stdout=log, stderr=subprocess.STDOUT, check=True)
                subprocess.run(['ninja', '-C', build, f'-j{args.jobs}', 'bench_bitcoin'], stdout=log, stderr=subprocess.STDOUT, check=True)
        if command(['git', '-C', src, 'rev-parse', 'HEAD']) != revision:
            raise RuntimeError('Source revision mismatch')
        if (src / 'src/bench/ready_backlog.cpp').read_bytes() != overlay:
            raise RuntimeError('Benchmark overlay mismatch')
        tracked_diff = command(['git', '-C', src, 'diff', '--name-only'])
        if tracked_diff != 'src/bench/CMakeLists.txt':
            raise RuntimeError('Unexpected tracked source changes: ' + tracked_diff)
        binaries[side] = build / 'src/bench/bench_bitcoin'
        build_details[side] = {'source': str(src), 'build': str(build), 'revision': revision,
                               'binary_sha256': hashlib.sha256(binaries[side].read_bytes()).hexdigest(),
                               'cmake_cache': (build / 'CMakeCache.txt').read_text(),
                               'benchmark_diff': command(['git', '-C', src, 'diff']),
                               'overlay_compile_command': command(['ninja', '-C', build, '-t', 'commands', 'src/bench/CMakeFiles/bench_bitcoin.dir/ready_backlog.cpp.o'])}
    environment = {'platform': platform.platform(), 'machine': platform.machine(),
                   'compiler': command(['/usr/bin/c++', '--version']), 'flags': FLAGS,
                   'overlay_sha256': hashlib.sha256(overlay).hexdigest(), 'builds': build_details,
                   'rounds': args.rounds, 'evaluations_per_round': args.evals,
                   'shared_host': True}
    if platform.system() == 'Darwin':
        environment['cpu'] = command(['sysctl', '-n', 'machdep.cpu.brand_string'])
        environment['logical_cpus'] = int(command(['sysctl', '-n', 'hw.logicalcpu']))
        environment['physical_cpus'] = int(command(['sysctl', '-n', 'hw.physicalcpu']))
        environment['memory_bytes'] = int(command(['sysctl', '-n', 'hw.memsize']))
        environment['os'] = command(['sw_vers'])
    (args.output / 'environment.json').write_text(json.dumps(environment, indent=2) + '\n')
    for r in range(args.rounds):
        order = ['base', 'patch'] if r % 2 == 0 else ['patch', 'base']
        for side in order:
            for family, regex, scaling in [('ready', 'Ready.*', '1'),
                                           ('upstream', '(AssembleBlock|GenerateBlock(50|500)ChainedTxs)', '.1')]:
                path = args.output / f'run-{r:02d}-{side}-{family}.log'
                with path.open('w') as log:
                    log.write('# Shared host load before process: ' + command(['uptime']) + '\n')
                    log.flush()
                    subprocess.run([binaries[side], '-filter=' + regex, '-evals=' + str(args.evals), '-scaling=' + scaling],
                                   stdout=log, stderr=subprocess.STDOUT, check=True)
                print(path.name, flush=True)
    summarize(args.output)


if __name__ == '__main__':
    main()
