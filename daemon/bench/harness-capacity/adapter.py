#!/usr/bin/env python3
"""Reuse the frozen node/fixture setup; explicitly replace only load generation."""
import json
import os
from pathlib import Path
import runpy
import struct
import sys
import time

from generator import ROOT, FROZEN, run_processes, core
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
    calibration = []
    if config.get('transport_calibration'):
        payload = []
        for offset in fixture.offsets[:batch_size]:
            length = struct.unpack_from('<I', fixture.mapping, offset)[0]
            payload.append(fixture.mapping[offset + 4:offset + 4 + length].decode('ascii'))
        for number in range(3):
            echo = {**settings, 'processes': 4, 'writers': 0, 'readers': 8,
                    'read_method': 'echo', 'echo_payload': [payload]}
            record = run_processes(echo, context['pids'],
                     Path(config['directory']) / f'transport-{number+1}')
            record.update(measurement='echo-transport-only-not-admission',
                          transaction_sized_items_per_request=len(payload),
                          transaction_equivalents_per_second=record['rpc_per_second'] * len(payload))
            calibration.append(record)
            print('TRANSPORT', number + 1, record['transaction_equivalents_per_second'], flush=True)
    if config.get('global_warmup'):
        # Keep a fixed16 transactions at every concurrency, including >16
        # submitters. Each child still warms its own HTTP connection/threads.
        client = client_factory()
        for _ in range(16):
            core.submit(client, mode, fixture.take(batch_size))
        client.connection.close()
        fixture.offsets = fixture.offsets[fixture.index:]
        settings['warmup_batches'] = 0
    elif settings['writers'] not in (8, 16):
        raise ValueError('Keep total warmup at16transactions/batches')
    before_started = None
    warmup = 16 * batch_size
    if config.get('network_completion'):
        from network_completion import wait_for_counts, verify_inventories
        def before_started():
            directory = Path(config['directory'])
            wait_for_counts(context['clients'], warmup, directory / 'NETWORK-WARMUP.json',
                            timeout=config['network_timeout'])
            rows = verify_inventories(context['clients'], warmup)
            (directory / 'NETWORK-WARMUP-VERIFIED.json').write_text(json.dumps(rows, indent=2)+'\n')
    result = run_processes(settings, context['pids'], Path(config['directory']) / 'ingestion', fixture,
                           on_started=kwargs.get('on_started'), before_started=before_started)
    if config.get('network_completion'):
        from network_completion import finish
        import subprocess
        sampler = None
        if config.get('profile_peer_completion'):
            sample_path = Path(config['directory']) / 'peer1.sample.txt'
            assert not sample_path.exists()
            sampler = subprocess.Popen(['/usr/bin/sample', str(context['pids'][1]), '4', '1',
                                        '-file', str(sample_path)],
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            result['network_completion'] = finish(context['clients'], result, warmup,
                config['directory'], timeout=config['network_timeout'])
        finally:
            if sampler is not None:
                code = sampler.wait(timeout=15)
                record = dict(pid=context['pids'][1], returncode=code,
                    phase='After timed RPC admission, during peer catch-up', duration_seconds=4,
                    interval_ms=1, throughput_publishable=False, path=str(sample_path))
                (Path(config['directory']) / 'PEER-PROFILE.json').write_text(json.dumps(record, indent=2)+'\n')
                assert code == 0 and sample_path.exists()
        if sampler is not None:
            result['throughput_publishable'] = False
            result['network_completion']['throughput_publishable'] = False
            result['network_completion']['profiled'] = True
            Path(config['directory'], 'NETWORK-COMPLETION.json').write_text(
                json.dumps(result['network_completion'], indent=2)+'\n')
        print('NETWORK-COMPLETION', json.dumps(result['network_completion']), flush=True)
    result['request_count'] = sum(row['request_count'] for row in result['children'])
    result['fixture_count'] = len(fixture.offsets)
    result['fixture_sha256'] = fixture.digest.hexdigest()
    if calibration:
        result['transport_calibration'] = calibration
    if config.get('global_warmup'):
        result['global_warmup_transactions'] = 16 * batch_size
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
    context.update(pids=[process.pid for process in context_arg['procs']],
                   clients=context_arg['clients'])
    config.update(port=context_arg['NODES_CFG'][0]['rpc_port'], auth=context_arg['AUTH_HEADER'])
    if 'rpc_workers' in config:
        for process in context_arg['procs']:
            assert f"-rpcthreads={config['rpc_workers']}" in process.args
    context_arg['results']['capacity_configuration'] = {
        **{k: v for k, v in config.items() if k != 'auth'},
        'node_pids': context['pids'], 'original_client_core': str(FROZEN / 'steady_ingestion.py'),
        'warmup_rule': '16total batches; child HTTP connections/threads warmed before common GO',
        'global_warmup': config.get('global_warmup', False)}
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
