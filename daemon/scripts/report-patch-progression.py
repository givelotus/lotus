#!/usr/bin/env python3
"""Render one global patch graph and raw/relative tables from validated records."""
import argparse
import csv
import html
import hashlib
import importlib.util
import json
from pathlib import Path
import statistics


def flatten(value, prefix=''):
    if isinstance(value, dict):
        for key, child in value.items():
            yield from flatten(child, prefix + ('.' if prefix else '') + key)
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        if prefix.endswith(('tps', 'rpc_per_second', '_ms', '_us', '_TPS', '_MBPS', '_HPS', '_US', '_MS', '_PS')):
            yield prefix, value


def measurements(record):
    groups = {}
    for run in record.get('metrics', {}).get('runs', []):
        identity = (run.get('workload', 'historical'), run.get('transaction_fixture_sha256', ''))
        for metric, value in flatten(run.get('metrics', {})):
            groups.setdefault((*identity, metric), []).append(value)
    kernel_runs = record.get('metrics', {}).get('kernel_runs', [])
    if not kernel_runs:
        return groups
    kernel_id = record.get('metrics', {}).get('kernel_workload_id')
    # Older fixtures did not declare their workload. Do not infer that matching
    # metric names make those results comparable across different source points.
    kernel_id = kernel_id or 'unidentified@' + record['prefix_sha256']
    for run in kernel_runs:
        for metric, value in flatten(run):
            groups.setdefault(('native-kernel:' + kernel_id,
                               hashlib.sha256(kernel_id.encode()).hexdigest(), metric), []).append(value)
    return groups


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    output = args.output or args.data / 'report'
    output.mkdir(parents=True, exist_ok=True)
    spec = importlib.util.spec_from_file_location('progression', Path(__file__).with_name('patch-progression.py'))
    driver = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(driver)
    base, entries = driver.manifest(args.candidate)
    environment = json.loads((args.data / 'environment.json').read_text())
    # A report cannot revive measurements invalidated by source or harness edits.
    harness, _ = driver.fingerprint(args.candidate, environment['repetitions'])
    rows, columns, references = [], set(), {}
    for entry in entries:
        index = entry['index']
        path = args.data / f'patch_{index:03}.json'
        record = json.loads(path.read_text()) if path.exists() else {}
        matching = record.get('prefix_sha256') == entry['prefix_sha256'] and driver.matching_harness(record, harness, args.data)
        status = record.get('status', 'pending') if matching else ('stale' if record else 'pending')
        layer = 'v2' if entry.get('series') == 'v2' else 'ecash'
        row = {'global_number': index, 'layer': layer, 'layer_number': entry.get('number', 0),
               'original_ids': entry.get('original_ids', [entry.get('original_patch', 'ABC baseline')]),
               'canonical_patch_path': entry.get('path'), 'patch_sha256': entry.get('sha256'),
               'prefix_sha256': entry['prefix_sha256'], 'status': status,
               'subject': entry.get('subject', 'Bitcoin ABC baseline'),
               'contract': entry.get('contract'), 'record_path': str(path), 'metrics': {}}
        if matching:
            for key in ('source_sha', 'source_tree', 'binary_sha256', 'harness_sha256', 'candidate_commit',
                        'build_passed', 'correctness_passed', 'chronik_compile_passed', 'failure_details'):
                row[key] = record.get(key)
            row['kernel_workload_id'] = record.get('metrics', {}).get('kernel_workload_id')
            row['kernel_benchmark_source_sha256'] = record.get('metrics', {}).get('kernel_benchmark_source_sha256')
        if status == 'ok' and record.get('correctness_passed'):
            for (workload, fixture, metric), values in measurements(record).items():
                column = workload + ' / ' + metric
                identity = (layer, workload, fixture, metric)
                median = statistics.median(values)
                reference_index, reference_value = references.setdefault(identity, (index, median))
                row['metrics'][column] = {'median': median, 'n': len(values), 'min': min(values),
                    'max': max(values), 'workload': workload, 'fixture_sha256': fixture,
                    'reference_global_number': reference_index,
                    'baseline_percent': 100 * median / reference_value if reference_value else None}
                columns.add(column)
        rows.append(row)
    columns = sorted(columns)
    original_map = {}
    for row in rows:
        for original in row['original_ids']:
            original_map.setdefault(original, []).append(row['global_number'])
    dataset = {'base': base, 'harness_sha256': harness, 'columns': columns, 'patches': rows,
               'original_to_canonical': original_map,
               'comparison_policy': 'ABC reference for available compatible Layer1 metrics; first measured compatible point for new workloads and V2. Kernel columns are separated by declared workload identity; unidentified historical kernel fixtures are isolated by source prefix. No line joins across the V2 boundary. Percent is raw/reference*100, not signed speedup.'}
    (output / 'progression.json').write_text(json.dumps(dataset, indent=2) + '\n')
    with (output / 'progression.csv').open('w', newline='') as stream:
        fields = ['global_number', 'layer', 'status', 'prefix_sha256', 'source_sha', 'harness_sha256',
                  'metric', 'median', 'n', 'min', 'max', 'reference_global_number', 'baseline_percent', 'fixture_sha256']
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            for metric, value in (row['metrics'] or {'': {}}).items():
                writer.writerow({**{key: row.get(key) for key in fields[:6]}, 'metric': metric,
                                 **{key: value.get(key) for key in fields[7:]}})
    def cell(value):
        return '—' if value is None else f'{value:,.3f}'
    header = ['Global patch / source', 'State / row'] + columns
    markdown = ['# Patch-by-patch benchmark table', '', dataset['comparison_policy'], '',
                '| ' + ' | '.join(header) + ' |', '| ' + ' | '.join(['---'] * len(header)) + ' |']
    table = ['<table><thead><tr>' + ''.join('<th>' + html.escape(x) + '</th>' for x in header) + '</tr></thead><tbody>']
    details = []
    for row in rows:
        index = row['global_number']
        for relative in (False, True):
            values = [cell(row['metrics'].get(column, {}).get('baseline_percent' if relative else 'median')) for column in columns]
            label = f'{index:03} {row["subject"]}'
            kind = 'baseline %' if relative else row['status'] + ' / raw'
            markdown.append('| ' + ' | '.join([f'[{index:03}][{index}]', kind] + values) + ' |')
            table.append('<tr><th><a href="#patch-' + str(index) + '">' + html.escape(label) + '</a></th><td>' + kind + '</td>' + ''.join('<td>' + x + '</td>' for x in values) + '</tr>')
        detail = '<details id="patch-' + str(index) + '"><summary>' + html.escape(f'{index:03} {row["subject"]} — {row["status"]}') + '</summary><pre>' + html.escape(json.dumps(row, indent=2)) + '</pre></details>'
        details.append(detail)
    table.append('</tbody></table>')
    markdown += ['', *[f'[{row["global_number"]}]: {row["record_path"]}' for row in rows]]
    (output / 'PATCH_BY_PATCH_BENCHMARK_TABLE.md').write_text('\n'.join(markdown) + '\n')
    payload = json.dumps(dataset).replace('<', '\\u003c')
    page = '''<!doctype html><meta charset="utf-8"><title>Canonical patch progression</title>
<style>body{font:15px system-ui;margin:24px;color:#18212b}select{max-width:80vw;padding:8px}svg{width:100%;height:360px;border:1px solid #ddd}.scroll{overflow:auto;max-height:70vh}table{border-collapse:collapse;white-space:nowrap;font-variant-numeric:tabular-nums}th,td{padding:7px;border:1px solid #ddd;text-align:right}th:first-child{position:sticky;left:0;background:#fff;max-width:420px;overflow:hidden;text-overflow:ellipsis;text-align:left}thead{position:sticky;top:0;background:#eee;z-index:2}pre{white-space:pre-wrap;overflow-wrap:anywhere}details{margin:12px 0}</style>
<h1>Canonical patch progression</h1><p>One global ABC → eCash → V2 sequence. Only completed correctness and runtime gates supply points. Pending, failed and stale entries remain visible. This is a candidate validation report, not a claim that the full stack passes.</p>
<p id="policy"></p><label>Metric <select id="metric"></select></label> <label><input type="checkbox" id="relative"> Baseline percent</label><svg id="graph" viewBox="0 0 1000 360"></svg>
<p><a href="progression.json">Full JSON with source identities and contracts</a> · <a href="progression.csv">CSV with n/min/max</a> · <a href="PATCH_BY_PATCH_BENCHMARK_TABLE.md">Markdown table</a></p><div class="scroll">TABLE</div><h2>Patch context and evidence</h2>DETAILS
<script>const data=PAYLOAD;document.getElementById('policy').textContent=data.comparison_policy;const select=document.getElementById('metric');for(const c of data.columns){const o=document.createElement('option');o.textContent=c;select.append(o)}
function draw(){const svg=document.getElementById('graph');svg.replaceChildren();const relative=document.getElementById('relative').checked;const field=relative?'baseline_percent':'median';const points=data.patches.filter(r=>r.metrics[select.value]?.[field]!=null);const max=Math.max(1,...points.map(r=>r.metrics[select.value][field]));const n=data.patches.length-1;const x=i=>55+900*i/Math.max(n,1),y=v=>305-270*v/max;const add=(tag,attrs,text)=>{const e=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const[k,v]of Object.entries(attrs))e.setAttribute(k,v);if(text)e.textContent=text;svg.append(e);return e};add('line',{x1:55,y1:305,x2:955,y2:305,stroke:'#888'});for(let i=0;i<5;i++){const v=max*i/4;add('text',{x:50,y:y(v)+4,'text-anchor':'end','font-size':11},v.toFixed(1));add('line',{x1:55,y1:y(v),x2:955,y2:y(v),stroke:'#eee'})}for(let i=0;i<=n;i+=Math.max(1,Math.ceil(n/12)))add('text',{x:x(i),y:325,'text-anchor':'middle','font-size':12},String(i));add('text',{x:500,y:348,'text-anchor':'middle'},'Global canonical patch number');const boundary=data.patches.find(r=>r.layer==='v2');if(boundary){add('line',{x1:x(boundary.global_number),y1:20,x2:x(boundary.global_number),y2:305,stroke:'#b65','stroke-dasharray':'5 4'});add('text',{x:x(boundary.global_number)+5,y:18,'font-size':12},'V2 consensus boundary')}
for(const layer of ['ecash','v2']){const rows=points.filter(r=>r.layer===layer);const color=layer==='ecash'?'#176fa6':'#ba6025';let last=null;for(const r of rows){const v=r.metrics[select.value][field];if(last&&last.global_number+1===r.global_number)add('line',{x1:x(last.global_number),y1:y(last.metrics[select.value][field]),x2:x(r.global_number),y2:y(v),stroke:color});const c=add('circle',{cx:x(r.global_number),cy:y(v),r:4,fill:color,style:'cursor:pointer'});const title=document.createElementNS(svg.namespaceURI,'title');title.textContent=`${r.global_number}: ${r.subject}\n${v}\n${r.prefix_sha256}`;c.append(title);c.onclick=()=>{const d=document.getElementById('patch-'+r.global_number);d.open=true;d.scrollIntoView()};last=r}}}select.onchange=draw;document.getElementById('relative').onchange=draw;draw();</script>'''
    (output / 'index.html').write_text(page.replace('TABLE', ''.join(table)).replace('DETAILS', ''.join(details)).replace('PAYLOAD', payload))
    print(json.dumps({'output': str(output), 'passed': sum(r['status'] == 'ok' for r in rows), 'total': len(rows), 'metrics': len(columns)}))


if __name__ == '__main__':
    main()
