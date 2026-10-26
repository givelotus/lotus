"""Run at least three exclusive alternating >=5 second before/after pairs."""
import argparse
import hashlib
import json
import pathlib
import statistics
import subprocess
import time

parser = argparse.ArgumentParser()
parser.add_argument('--counts', default='100000')
parser.add_argument('--distributions', default='uniform')
parser.add_argument('--workloads', default='extraction,lookup,insert')
parser.add_argument('--pairs', type=int, default=3)
parser.add_argument('--seconds', type=float, default=5.0)
parser.add_argument('--seed', type=int, default=20261023)
args = parser.parse_args()
if args.pairs < 3 or args.seconds < 5: raise ValueError('Need >=3 alternating pairs, >=5 active seconds each')
here = pathlib.Path(__file__).resolve().parent
output = here / 'pairs'
output.mkdir(exist_ok=True)
records = []
for count in [int(value) for value in args.counts.split(',')]:
    for distribution in args.distributions.split(','):
        for workload in args.workloads.split(','):
            # Warm both variants before any reported pair in this group.
            for label in ['before', 'after']:
                command = [str(here / (label + '-bench')), label, workload,
                    distribution, str(count), '0.05', str(args.seed)]
                warm = subprocess.run(command, capture_output=True, text=True)
                (output / f'{count}-{distribution}-{workload}-{label}-warmup.log').write_text(warm.stdout + warm.stderr)
                if warm.returncode: raise RuntimeError('warmup failed')
            for pair in range(1, args.pairs + 1):
                for label in ['before', 'after']:
                    binary = here / (label + '-bench')
                    command = [str(binary), label, workload, distribution, str(count), str(args.seconds), str(args.seed)]
                    started = time.time()
                    result = subprocess.run(command, capture_output=True, text=True)
                    name = f'{count}-{distribution}-{workload}-pair{pair}-{label}'
                    (output / (name + '.log')).write_text(result.stdout + result.stderr)
                    if result.returncode: raise RuntimeError(name + ' failed')
                    record = json.loads(result.stdout)
                    if record['active_seconds'] < args.seconds: raise RuntimeError('short sample')
                    record.update(pair=pair, command=command, started_unix=started,
                        binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest())
                    records.append(record)
                    (output / (name + '.json')).write_text(json.dumps(record, indent=2) + '\n')
                    (here / 'RAW-RESULTS.json').write_text(json.dumps(records, indent=2) + '\n')
                    print(name, record['ns_per_operation'], flush=True)
summary = []
for count in [int(value) for value in args.counts.split(',')]:
    for distribution in args.distributions.split(','):
        for workload in args.workloads.split(','):
            group = [r for r in records if r['count'] == count and r['distribution'] == distribution and r['workload'] == workload]
            if len({r['dataset_sha256'] for r in group}) != 1: raise RuntimeError('dataset mismatch')
            row = {'count': count, 'distribution': distribution, 'workload': workload}
            for label in ['before', 'after']:
                values = [r['ns_per_operation'] for r in group if r['label'] == label]
                row[label] = {'median_ns': statistics.median(values), 'min_ns': min(values), 'max_ns': max(values), 'samples': values}
            row['median_ratio_before_over_after'] = row['before']['median_ns'] / row['after']['median_ns']
            summary.append(row)
(here / 'SUMMARY.json').write_text(json.dumps(summary, indent=2) + '\n')
print('Completed', len(records), 'samples; microbenchmark evidence only.', flush=True)
