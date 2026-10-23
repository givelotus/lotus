#!/usr/bin/env python3
"""Reuse the frozen node/fixture setup; explicitly replace only load generation."""
import json
import os
from pathlib import Path
import runpy
import sys
import time

from generator import ROOT, FROZEN, run_processes
sys.path.insert(0, str(FROZEN))
import steady_suite as suite

config = json.loads(Path(os.environ['CAPACITY_CONFIG']).read_text())
original_suite = suite.run_suite
original_measure = suite.measure
context = {}


def measured(fixture, client_factory, mode, batch_size, **kwargs):
    if kwargs.get('pilot'):
        return original_measure(fixture, client_factory, mode, batch_size, **kwargs)
    settings = {**config, 'mode': mode, 'batch_size': batch_size,
                'readers': config['readers'] if kwargs.get('reader_workers') else 0,
                'warmup_batches': 16 // config['writers']}
    if settings['writers'] not in (8, 16):
        raise ValueError('Keep total warmup at16transactions/batches')
    result = run_processes(settings, context['pids'], Path(config['directory']) / 'ingestion', fixture)
    result['request_count'] = sum(row['request_count'] for row in result['children'])
    result['fixture_count'] = len(fixture.offsets)
    result['fixture_sha256'] = fixture.digest.hexdigest()
    return result


def read_matrix(client_factory, **kwargs):
    rows = []
    for number in range(3):
        order = [1, 4] if number % 2 == 0 else [4, 1]
        for method in ('getmempoolinfo', 'getblockchaininfo'):
            for processes in order:
                settings = {**config, 'processes': processes, 'writers': 0,
                            'readers': 12, 'read_method': method}
                result = run_processes(settings, context['pids'],
                         Path(config['directory']) / f'reads-{number+1}-{method}-{processes}')
                rows.append({'round': number + 1, 'method': method, **result})
                print('READ', number + 1, method, processes, result['rpc_per_second'], flush=True)
                Path(config['directory'], 'READS.json').write_text(json.dumps(rows, indent=2))
    return {'measurement': 'separate-rpc-capacity', 'rows': rows}


def run(context_arg, *args, **kwargs):
    context.update(pids=[process.pid for process in context_arg['procs']])
    config.update(port=context_arg['NODES_CFG'][0]['rpc_port'], auth=context_arg['AUTH_HEADER'])
    if 'rpc_workers' in config:
        for process in context_arg['procs']:
            assert f"-rpcthreads={config['rpc_workers']}" in process.args
    context_arg['results']['capacity_configuration'] = {
        **{k: v for k, v in config.items() if k != 'auth'},
        'node_pids': context['pids'], 'original_client_core': str(FROZEN / 'steady_ingestion.py'),
        'warmup_rule': '16total batches, matching the frozen8writers×2warmup'}
    suite.measure = measured
    if config.get('read_matrix'):
        suite.measure_reads = read_matrix
    return original_suite(context_arg, *args, **kwargs)


suite.run_suite = run
# Insert the worker-count adjustment before the frozen wrapper hashes/executes
# its generated bootstrap. Do not edit the historical benchmark tools.
path = ROOT / 'daemon/bench/commit-regressions/steady_loopback.py'
body = path.read_text()
hook = '''
if 'rpc_workers' in config:
    anchor = "a.output.with_suffix('.adapted.py').write_text(code)"
    assert result.count(anchor) == 1
    position = result.index(anchor)
    old = '\\"-rpcthreads=16\\"'
    new = '\\"-rpcthreads=' + str(config['rpc_workers']) + '\\"'
    result.insert(position, 'assert code.count(' + repr(old) + ') == 1')
    result.insert(position + 1, 'code=code.replace(' + repr(old) + ', ' + repr(new) + ')')
    result.insert(position + 2, "adaptations.append({'capacity_rpc_workers': " + str(config['rpc_workers']) + "})")
'''
assert body.count('exec(compile(') == 1
body = body.replace('exec(compile(', hook + '\nexec(compile(', 1)
exec(compile(body, str(path), 'exec'), {'__name__': '__main__', '__file__': str(path), 'config': config})
