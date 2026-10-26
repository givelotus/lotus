#!/usr/bin/env python3
"""Bounded, deterministic native storage measurements in new temporary homes."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import tempfile
import time


def capture(argv):
    result = subprocess.run(argv, text=True, capture_output=True, check=True)
    return result.stdout.strip()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--binary', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--native', type=Path, required=True)
    p.add_argument('--trials', type=int, default=3)
    p.add_argument('--sizes', type=int, nargs='+', default=[1000, 10000, 50000])
    p.add_argument('--contention', required=True, help='Observed host work and whether timing was coordinated')
    p.add_argument('--smoke', action='store_true')
    a = p.parse_args()
    if not a.binary.is_file() or not 1 <= a.trials <= 10:
        p.error('existing binary and 1..10 trials required')
    if any(n < 100 or n > 100000 for n in a.sizes):
        p.error('sizes must be 100..100000 for this bounded baseline')
    if a.output.exists():
        p.error('output directory must be new; failures and earlier evidence are preserved')
    a.output.mkdir(parents=True)
    meta = {
        'schema': 1, 'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'platform': platform.platform(), 'machine': platform.machine(),
        'cpu': capture(['sysctl', '-n', 'machdep.cpu.brand_string']) if platform.system() == 'Darwin' else platform.processor(),
        'logical_cpu_count': os.cpu_count(),
        'memory_bytes': capture(['sysctl', '-n', 'hw.memsize']) if platform.system() == 'Darwin' else None,
        'native_base': capture(['git', '-C', str(a.native), 'rev-parse', 'HEAD']),
        'native_diff_sha256': hashlib.sha256(capture(['git', '-C', str(a.native), 'diff', 'HEAD']).encode()).hexdigest(),
        'binary': str(a.binary.resolve()), 'binary_sha256': hashlib.sha256(a.binary.read_bytes()).hexdigest(),
        'harness_sources': {str(f.relative_to(a.native)): hashlib.sha256(f.read_bytes()).hexdigest() for f in (a.native / 'src/lotus_v2/perf_test').glob('*') if f.is_file()},
        'cmake_cache': {line.split('=',1)[0]: line.split('=',1)[1] for line in (a.binary.parent / 'CMakeCache.txt').read_text().splitlines() if line.startswith(('CMAKE_BUILD_TYPE:', 'CMAKE_CXX_FLAGS', 'CMAKE_C_FLAGS', 'LOTUS_SECP_LIBRARY:'))},
        'compiler': capture(['c++', '--version']), 'contention': a.contention,
        'cache_policy': 'fresh process/LevelDB cache where labeled; OS caches uncontrolled, never flushed',
        'metric_policy': 'Env bytes are engine file API bytes, not physical device I/O; process RSS is lifetime high-water',
        'trials': a.trials, 'sizes': a.sizes, 'calls': [],
    }
    (a.output / 'host-before.txt').write_text(capture(['ps', '-axo', 'pid,pcpu,comm']))
    records = []
    def invoke(mode, n, batch, trial, cache=8<<20, home=None):
        if home is None:
            parent = Path(tempfile.mkdtemp(prefix='lotus-v2-perf-run-', dir='/private/tmp'))
            home = parent / 'db'
        argv = [str(a.binary.resolve()), mode, str(home), str(n), str(batch), str(cache), 'ephemeral-benchmark']
        start = time.time()
        r = subprocess.run(argv, text=True, capture_output=True)
        key = f'{trial}-{mode}-{n}-{batch}-{cache}'
        (a.output / f'{key}.stdout.jsonl').write_text(r.stdout)
        (a.output / f'{key}.stderr.txt').write_text(r.stderr)
        meta['calls'].append({'argv': argv, 'trial': trial, 'returncode': r.returncode,
                              'process_wall_s': time.time()-start})
        (a.output / 'provenance.json').write_text(json.dumps(meta, indent=2)+'\n')
        if r.returncode:
            raise RuntimeError(f'{key} failed; see preserved stderr')
        for line in r.stdout.splitlines():
            row = json.loads(line); row.update(trial=trial, mode=mode, cache_bytes=cache, batch=batch)
            records.append(row)
        print(f'{key}: completed', flush=True)
        return home
    for trial in range(a.trials):
        for n in a.sizes:
            home = invoke('disk', n, 100, trial)
            invoke('reader', n, 100, trial, home=home)
            invoke('floor', n, 100, trial)
        if not a.smoke:
            # Fixed UTXO count, batch sensitivity, and cache sensitivity.
            invoke('disk', 10000, 1000, trial)
            home = invoke('disk', 10000, 100, trial, cache=64<<10)
            invoke('reader', 10000, 100, trial, cache=64<<10, home=home)
            for height in (100, 1000):
                invoke('height', height, 100, trial)
            for blocks in (100, 1000):
                invoke('history', blocks, 100, trial)
            for n in (100, 1000):
                invoke('prototype', n, 100, trial)
            for n in (1, 100, 1000):
                invoke('decode', n, 1, trial)
    (a.output / 'records.json').write_text(json.dumps(records, indent=2)+'\n')
    groups = {}
    for row in records:
        if 'wall_s' in row:
            key = (row['phase'], row['n'], row['batch'], row['cache_bytes'])
            groups.setdefault(key, []).append(row)
    summaries = []
    for (phase,n,batch,cache), rows in groups.items():
        summary = dict(phase=phase,n=n,batch=batch,cache_bytes=cache,trials=len(rows))
        for metric in ('wall_s','user_s','system_s','process_peak_rss_bytes','env_reads','env_read_bytes','env_write_bytes','env_syncs','env_sync_s','minor_faults','major_faults','logical_gets','batch_payload_bytes','dirty_nodes','dirty_coins'):
            values = [r[metric] for r in rows]
            summary[metric] = {'min': min(values), 'median': statistics.median(values), 'max': max(values)}
        summaries.append(summary)
    (a.output / 'summary.json').write_text(json.dumps(summaries, indent=2)+'\n')
    (a.output / 'host-after.txt').write_text(capture(['ps', '-axo', 'pid,pcpu,comm']))

if __name__ == '__main__':
    main()
