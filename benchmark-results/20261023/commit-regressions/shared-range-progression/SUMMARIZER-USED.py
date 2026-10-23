#!/usr/bin/env python3
"""Summarize real prefix measurements and flag ranges needing paired bisection.

A flagged range is a screening observation, not attribution to its last commit.
RPC acceptance, reads and propagation must never be combined into one speedup.
"""
import argparse
import csv
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('results', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--notes', type=Path, help='Progression PLAN.json with exact source commits and range footnotes')
    args = parser.parse_args()
    data = json.loads(args.results.read_text())
    groups = defaultdict(list)
    for row in data['runs']:
        if row.get('diagnostic_net'):
            raise ValueError('Diagnostic logging runs are excluded from performance summaries')
        value = row['result']
        if value['seconds'] < 5 or value['tx_count'] <= 0:
            raise ValueError('Only sustained positive-count measurements qualify')
        identity = (row['point'], row['source_commit'])
        groups[(*identity, row['case'], 'tx/s')].append((row['round'], value['tx_count']/value['seconds']))
        if row['case'] == 'single_tx_loaded_steady':
            groups[(*identity, 'concurrent_reads', 'RPC/s')].append((row['round'], value['loaded_read']['rpc_per_second']))
    summaries = []
    previous = {}
    baseline = {}
    for (point, commit, workload, unit), observations in sorted(groups.items()):
        rounds = dict(observations)
        if len(rounds) != len(observations):
            raise ValueError('Duplicate point/workload/round; do not silently pool distinct studies')
        values = list(rounds.values())
        row = dict(point=point, commit=commit, workload=workload, unit=unit,
                   median=statistics.median(values), minimum=min(values), maximum=max(values), n=len(values))
        failure_case = 'single_tx_loaded_steady' if workload == 'concurrent_reads' else workload
        row['failed_samples'] = sum(f['point'] == point and f['case'] == failure_case for f in data.get('failures', []))
        if point == 0 and not row['failed_samples']:
            baseline[(workload, unit)] = row['median']
        if (workload, unit) in baseline:
            row['versus_abc_percent'] = 100*(row['median']/baseline[(workload, unit)]-1)
        prior = previous.get((workload, unit))
        if prior:
            change = 100*(row['median']/prior['median']-1)
            paired = [100*(rounds[n]/prior['rounds'][n]-1) for n in rounds.keys() & prior['rounds'].keys()]
            row.update(previous_point=prior['point'], change_percent=change,
                       paired_changes_percent=paired, ranges_overlap=not (
                           row['maximum'] < prior['minimum'] or prior['maximum'] < row['minimum']),
                       disposition='confirm and bisect range' if change <= -5 else 'screen only; no >=5% median loss')
        else:
            row['disposition'] = 'first measured prefix for workload'
        summaries.append(row)
        if row['failed_samples']:
            row['disposition'] = 'failed samples present; exclude this cell from performance conclusions'
        else:
            previous[(workload, unit)] = dict(**row, rounds=rounds)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output/'SUMMARY.json').write_text(json.dumps(dict(status=data['status'],
        semantics='RPC acceptance/read screen, not confirmed transactions or causal commit attribution',
        source_results=str(args.results.resolve()), summaries=summaries, failures=data.get('failures', [])), indent=2)+'\n')
    columns = ['point', 'commit', 'workload', 'unit', 'median', 'minimum', 'maximum', 'n',
               'failed_samples', 'previous_point', 'change_percent', 'versus_abc_percent', 'ranges_overlap', 'disposition']
    with (args.output/'SUMMARY.csv').open('w') as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(summaries)
    if args.notes:
        notes = json.loads(args.notes.read_text())
        cells = {(r['point'], r['workload']): r for r in summaries}
        lines = ['# ABC-anchored commit progression', '',
                 f"Study status: {data['status']}. Rates are RPC acceptance/read measurements. Each populated cell is a median; sample counts and ranges are in SUMMARY.csv. Failed samples contribute no rate.", '',
                 'Points identify the frozen shared ABC/eCash Git stack through378. This is not the native V2 endpoint.', '',
                 '| Point | Commit | Individual tx/s | Arrays50 tx/s | Loaded tx/s | Concurrent reads RPC/s |',
                 '|---:|---|---:|---:|---:|---:|']
        for entry in notes['points']:
            point = entry['point']
            def cell(case):
                failure_case = 'single_tx_loaded_steady' if case == 'concurrent_reads' else case
                if any(f['point'] == point and f['case'] == failure_case for f in data.get('failures', [])):
                    return 'FAIL'
                row = cells.get((point, case))
                return f"{row['median']:,.0f}" if row else 'N/A'
            lines.append(f"| {point}[^p{point}] | {entry['commit'][:10]} | "+' | '.join(cell(case) for case in (
                'single_tx_steady', 'json_rpc_batch50_steady', 'single_tx_loaded_steady', 'concurrent_reads'))+' |')
        lines += ['', 'Individual-owner attribution is pending for coarse intervals. A positive interval can conceal a regression inside it.', '']
        for entry in notes['points']:
            lines.append(f"[^p{entry['point']}]: {entry['footnote']}")
        if data.get('failures'):
            lines += ['', 'Failed samples (not throughput results):', '']
            for fail in data['failures']:
                lines.append(f"- Point {fail['point']}, round {fail['round']}, {fail['case']}: {fail['disposition']}. Evidence: {fail['evidence']}")
        (args.output/'TABLE.md').write_text('\n'.join(lines)+'\n')
    writer = csv.writer(sys.stdout)
    writer.writerow(['point', 'workload', 'median', 'unit', 'change from preceding measured prefix', 'n'])
    for row in summaries:
        writer.writerow([row['point'], row['workload'], round(row['median']), row['unit'],
                         round(row['change_percent'], 1) if 'change_percent' in row else '', row['n']])


if __name__ == '__main__':
    main()
