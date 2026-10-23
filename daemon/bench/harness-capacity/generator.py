#!/usr/bin/env python3
"""Process-isolated load around the unchanged warmed ingestion core."""
import array
import concurrent.futures
import http.client
import json
import mmap
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import types

ROOT = Path(__file__).resolve().parents[3]
FROZEN = ROOT / 'daemon/patch-audit/consolidation/20261022/benchmark-tools/scripts'
sys.path.insert(0, str(FROZEN))
import steady_ingestion as core


def process_cpu(pids):
    rows = subprocess.check_output(
        ['ps', '-o', 'pid=,time=', '-p', ','.join(map(str, pids))], text=True)
    result = {}
    for row in rows.splitlines():
        pid, clock = row.split()
        parts = clock.split(':')
        seconds = sum(float(part) * 60 ** i for i, part in enumerate(reversed(parts)))
        result[pid] = seconds
    return result


class Client:
    def __init__(self, config):
        self.config = config
        self.node_index = 0
        self.connection = http.client.HTTPConnection('127.0.0.1', config['port'], timeout=60)

    def request(self, payload):
        self.connection.request('POST', '/', json.dumps(payload), {
            'Authorization': self.config['auth'], 'Content-Type': 'application/json'})
        response = self.connection.getresponse()
        reply = json.loads(response.read())
        if response.status != 200:
            raise RuntimeError(f'HTTP {response.status}: {reply}')
        rows = reply if isinstance(reply, list) else [reply]
        expected = len(payload) if isinstance(payload, list) else 1
        if len(rows) != expected or any(row.get('error') or 'result' not in row for row in rows):
            raise RuntimeError(f'Incomplete/rejected response: {reply}')
        return reply

    def call(self, method, params=None):
        if method == 'echo' and 'echo_payload' in self.config:
            params = self.config['echo_payload']
        result = self.request({'jsonrpc': '2.0', 'id': 1, 'method': method,
                               'params': params or []})['result']
        if method == 'echo' and 'echo_payload' in self.config and result != params:
            raise RuntimeError('Echo did not return the full transaction-sized payload')
        return result


def synchronize():
    print(json.dumps({'ready': True, 'pid': os.getpid()}), flush=True)
    start = json.loads(sys.stdin.readline())['start']
    while (remaining := start - time.perf_counter()) > 0:
        time.sleep(min(remaining, .005))


def read_measure(factory, workers, method, seconds=5.0):
    barrier = threading.Barrier(workers + 1)
    go = threading.Event()
    timing = {}

    def reader():
        client = factory()
        try:
            for _ in range(2):
                client.call(method)
            barrier.wait()
            go.wait()
            count = 0
            while time.perf_counter() < timing['deadline']:
                client.call(method)
                count += 1
            return count, time.perf_counter()
        except BaseException:
            barrier.abort()
            go.set()
            raise
        finally:
            client.connection.close()

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(reader) for _ in range(workers)]
        barrier.wait(timeout=120)
        synchronize()
        cpu = time.process_time()
        timing.update(start=time.perf_counter())
        timing['deadline'] = timing['start'] + seconds
        go.set()
        try:
            rows = [future.result() for future in futures]
        finally:
            go.set()
    end = max(row[1] for row in rows)
    return {'tx_count': 0, 'rpc_calls': sum(row[0] for row in rows),
            'started_monotonic': timing['start'], 'finished_monotonic': end,
            'seconds': end - timing['start'], 'client_cpu_seconds': time.process_time() - cpu}


def child(path):
    config = json.loads(Path(path).read_text())
    factory = lambda: Client(config)
    if config.get('read_method'):
        result = read_measure(factory, config['readers'], config['read_method'])
    else:
        # Read-only shared corpus; each process receives disjoint offset ranges.
        fixture = object.__new__(core.DiskFixture)
        fixture.path = Path(config['fixture'])
        fixture.file = fixture.path.open('rb')
        fixture.mapping = mmap.mmap(fixture.file.fileno(), 0, access=mmap.ACCESS_READ)
        with open(config['index'], 'rb') as index:
            index.seek(config['begin'] * 8)
            fixture.offsets = array.array('Q')
            fixture.offsets.fromfile(index, config['end'] - config['begin'])
        fixture.index, fixture.read_seconds = 0, 0.0
        fixture.lock = threading.Lock()
        fixture.digest = types.SimpleNamespace(hexdigest=lambda: config['fixture_sha256'])
        for offset in range(0, len(fixture.mapping), 4096):
            fixture.mapping[offset]
        try:
            result = core.measure(fixture, factory, config['mode'], config['batch_size'],
                                  workers=config['writers'], reader_workers=config['readers'],
                                  warmup_batches=config['warmup_batches'], before_started=synchronize)
        finally:
            fixture.close()
    print(json.dumps({'result': result, 'pid': os.getpid()}), flush=True)


def run_processes(config, pids, directory, fixture=None, on_started=None, before_started=None):
    """Warm all workers before a common start; return only proven responses."""
    directory.mkdir(parents=True, exist_ok=False)
    count = config['processes']
    assert config['writers'] % count == config['readers'] % count == 0
    if fixture is not None:
        index = directory / 'fixture.index'
        with index.open('wb') as f:
            fixture.offsets.tofile(f)
    children, logs = [], []
    try:
        for number in range(count):
            settings = {**config, 'writers': config['writers'] // count,
                        'readers': config['readers'] // count}
            if fixture is not None:
                # Align partitions to batches. Refuse short/exhausted corpora.
                batches = len(fixture.offsets) // config['batch_size']
                begin = (batches * number // count) * config['batch_size']
                end = (batches * (number + 1) // count) * config['batch_size']
                settings.update(fixture=str(fixture.path), index=str(index), begin=begin,
                                end=end, fixture_sha256=fixture.digest.hexdigest())
            path = directory / f'process-{number}.json'
            path.write_text(json.dumps(settings, indent=2))
            log = (directory / f'process-{number}.stderr').open('w')
            logs.append(log)
            children.append(subprocess.Popen([sys.executable, __file__, str(path)],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=log, text=True))
        for proc in children:
            message = json.loads(proc.stdout.readline())
            assert message['ready'] and message['pid'] == proc.pid
        # All connection/thread setup and warmup have finished.
        if before_started is not None:
            before_started()
        before = process_cpu(pids)
        start = time.perf_counter() + .1
        for proc in children:
            proc.stdin.write(json.dumps({'start': start}) + '\n')
            proc.stdin.flush()
        if on_started is not None:
            while (remaining := start - time.perf_counter()) > 0:
                time.sleep(min(.005, remaining))
            warmup = (16 if config.get('global_warmup') else
                      config['writers'] * config['warmup_batches']) * config['batch_size']
            on_started(start, time.time_ns(), warmup)
        results = []
        for proc in children:
            message = json.loads(proc.stdout.readline())
            assert message['pid'] == proc.pid
            results.append(message['result'])
        after = process_cpu(pids)
        for proc in children:
            assert proc.wait(timeout=15) == 0
        began = min(row['started_monotonic'] for row in results)
        finished = max(row['finished_monotonic'] for row in results)
        skew = max(row['started_monotonic'] for row in results) - began
        if skew > .025 or min(row['seconds'] for row in results) < 5:
            raise RuntimeError(f'Invalid start skew/window: {skew}')
        elapsed = finished - began
        txs = sum(row['tx_count'] for row in results)
        result = {'measurement': 'process-isolated-capacity', 'seconds': elapsed,
                  'started_monotonic': began, 'finished_monotonic': finished,
                  'tx_count': txs, 'tps': txs / elapsed, 'processes': count,
                  'workers': config['writers'], 'reader_workers': config['readers'],
                  'start_skew_seconds': skew, 'children': results,
                  'client_cpu_seconds': sum(row['client_cpu_seconds'] for row in results),
                  'node_cpu_seconds': {pid: after[pid] - before[pid] for pid in before},
                  'cpu_counter_scope': 'ps process CPU, whole node; bracket includes 0.1s start lead and response drain'}
        if config.get('read_method'):
            result['rpc_calls'] = sum(row['rpc_calls'] for row in results)
            result['rpc_per_second'] = result['rpc_calls'] / elapsed
        if config['readers'] and not config.get('read_method'):
            calls = sum(row['loaded_read']['rpc_calls'] for row in results)
            result['loaded_read'] = {'rpc_calls': calls, 'rpc_per_second': calls / elapsed}
        (directory / 'RESULTS.json').write_text(json.dumps(result, indent=2))
        return result
    finally:
        for proc in children:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
        for log in logs:
            log.close()


if __name__ == '__main__':
    child(sys.argv[1])
