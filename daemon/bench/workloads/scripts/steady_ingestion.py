"""Version 2 throughput measurement: warmed workers, bounded disk fixtures, >=5s.

Transaction construction/signing and fixture warming never run on the timed path.
The client and disk-read costs remain part of end-to-end RPC throughput and are
reported; an exhausted fixture is an error, never a shorter measurement.
"""
import array
import concurrent.futures
import hashlib
import json
import mmap
import os
from pathlib import Path
import struct
import threading
import time


class FixtureExhausted(RuntimeError):
    pass


def histogram_percentiles(histogram):
    total = sum(histogram)
    result = {'overflow_count': histogram[-1], 'overflow_min_ms': (len(histogram) - 1) * 0.01}
    for percentile in (50, 95, 99):
        target = max(1, (total * percentile + 99) // 100)
        cumulative = 0
        for index, count in enumerate(histogram):
            cumulative += count
            if cumulative >= target:
                result[f'p{percentile}_ms'] = None if index == len(histogram) - 1 else index * 0.01
                if index == len(histogram) - 1:
                    result[f'p{percentile}_ms_lower_bound'] = index * 0.01
                break
    return result


class DiskFixture:
    def __init__(self, path, max_bytes=512 * 1024 * 1024):
        self.path = Path(path)
        self.max_bytes = max_bytes
        self.offsets = array.array('Q')
        self.digest = hashlib.sha256()
        self.file = self.path.open('w+b')
        self.mapping = None
        self.index = 0
        self.lock = threading.Lock()
        self.read_seconds = 0.0

    def append(self, raw):
        encoded = raw.encode('ascii')
        if self.file.tell() + len(encoded) + 4 > self.max_bytes:
            raise ValueError('Fixture exceeds declared disk budget')
        self.offsets.append(self.file.tell())
        self.file.write(struct.pack('<I', len(encoded)))
        self.file.write(encoded)
        self.digest.update(encoded)

    def seal(self):
        self.file.flush()
        self.mapping = mmap.mmap(self.file.fileno(), 0, access=mmap.ACCESS_READ)
        # Touch every page outside the timer; OS eviction is still possible.
        for offset in range(0, len(self.mapping), 4096):
            self.mapping[offset]

    def take(self, count):
        started = time.perf_counter()
        with self.lock:
            if self.index >= len(self.offsets):
                raise FixtureExhausted('Distinct presigned fixture exhausted before deadline')
            begin = self.index
            self.index = min(self.index + count, len(self.offsets))
            offsets = self.offsets[begin:self.index]
        result = []
        for offset in offsets:
            length = struct.unpack_from('<I', self.mapping, offset)[0]
            result.append(self.mapping[offset + 4:offset + 4 + length].decode('ascii'))
        elapsed = time.perf_counter() - started
        with self.lock:
            self.read_seconds += elapsed
        return result

    def close(self):
        if self.mapping is not None:
            self.mapping.close()
        self.file.close()


def submit(client, mode, rows):
    if mode == 'individual':
        if len(rows) != 1:
            raise ValueError('Individual RPC means one transaction per call')
        return client.call('sendrawtransaction', [rows[0]])
    if mode == 'json_array':
        return client.request([{'jsonrpc': '2.0', 'id': i,
                                'method': 'sendrawtransaction', 'params': [raw]}
                               for i, raw in enumerate(rows)])
    if mode == 'dedicated_batch':
        reply = client.call('submitrawtxbatch', [rows])
        if not reply.get('accepted'):
            raise RuntimeError('Dedicated batch rejected: ' + json.dumps(reply))
        results, txids = reply.get('results', []), reply.get('txids', [])
        if (len(results) != len(rows) or len(txids) != len(rows)
                or len(set(txids)) != len(rows)
                or any(item.get('allowed') is not True for item in results)
                or [item.get('txid') for item in results] != txids):
            raise RuntimeError('Dedicated batch reply does not prove every requested transaction accepted')
        return reply
    raise ValueError('Unknown ingestion mode')


def measure(fixture, client_factory, mode, batch_size, seconds=5.0, workers=8,
            reader_workers=0, warmup_batches=2, clock=time.perf_counter, pilot=False,
            on_started=None, progress_every=0, before_started=None):
    if seconds < 5 and not pilot:
        raise ValueError('Throughput measurement must last at least five seconds')
    if not isinstance(progress_every, int) or progress_every < 0:
        raise ValueError('Progress interval must be a nonnegative transaction count')
    progress_lock = threading.Lock()
    progress_count = [0]
    progress_rows = []
    barrier = threading.Barrier(workers + reader_workers + 1)
    go = threading.Event()
    stop = threading.Event()
    timing = {}
    finish_lock = threading.Lock()
    remaining_writers = [workers]

    def writer(_):
        client = client_factory()
        try:
            client.call('getblockchaininfo')
            # Persistent worker threads and their actual ingestion connections.
            for _ in range(warmup_batches):
                submit(client, mode, fixture.take(batch_size))
            barrier.wait()
            go.wait()
            count = requests = 0
            while not stop.is_set() and clock() < timing['deadline']:
                try:
                    rows = fixture.take(batch_size)
                except FixtureExhausted:
                    if pilot:
                        break
                    raise
                submit(client, mode, rows)
                count += len(rows)
                requests += 1
                if progress_every:
                    with progress_lock:
                        previous = progress_count[0]
                        progress_count[0] += len(rows)
                        if progress_count[0] // progress_every > previous // progress_every:
                            progress_rows.append({'completed_transactions': progress_count[0],
                                                  'elapsed_seconds': clock() - timing['start']})
                            print('[completion-progress] '+json.dumps(progress_rows[-1]), flush=True)
            finished = clock()
            with finish_lock:
                remaining_writers[0] -= 1
                if remaining_writers[0] == 0:
                    stop.set()
            return count, requests, finished, getattr(client, 'node_index', None)
        except BaseException:
            barrier.abort()
            stop.set()
            go.set()
            raise

    def reader(_):
        client = client_factory()
        try:
            client.call('getmempoolinfo')
            client.call('getblockchaininfo')
            barrier.wait()
            go.wait()
            count = 0
            histogram = [0] * 10002
            while not stop.is_set():
                started = clock()
                client.call('getmempoolinfo')
                client.call('getblockchaininfo')
                elapsed = clock() - started
                if stop.is_set():
                    break
                histogram[min(10001, int(elapsed * 100000))] += 1
                count += 1
            return count, histogram
        except BaseException:
            barrier.abort()
            stop.set()
            go.set()
            raise

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers + reader_workers) as pool:
        writers = [pool.submit(writer, i) for i in range(workers)]
        readers = [pool.submit(reader, i) for i in range(reader_workers)]
        try:
            barrier.wait()
            if before_started is not None:
                before_started()
            host_before = {'utc_ns': time.time_ns(), 'load_average': os.getloadavg()}
            read_before = fixture.read_seconds
            cpu_before = time.process_time()
            warmup_fixture_count = getattr(fixture, 'index', None)
            timing['start'] = clock()
            timing['deadline'] = timing['start'] + seconds
            go.set()
            if on_started is not None:
                on_started(timing['start'], host_before['utc_ns'], warmup_fixture_count)
            values = [future.result() for future in writers]
        finally:
            stop.set()
            go.set()
        reader_values = [future.result() for future in readers]
    end = max(value[2] for value in values)
    client_cpu_seconds = time.process_time() - cpu_before
    elapsed = end - timing['start']
    if elapsed < seconds and not pilot:
        raise RuntimeError('Measured ingestion interval is shorter than requested')
    count = sum(value[0] for value in values)
    result = {'schema_version': 2, 'measurement': 'untimed-sizing-pilot' if pilot else 'steady-state-v2',
              'mode': mode, 'batch_size': batch_size, 'workers': workers,
              'warmup_fixture_count': warmup_fixture_count,
              'tx_count': count, 'request_count': sum(value[1] for value in values),
              'per_writer': [{'accepted_count': value[0], 'request_count': value[1],
                              'node_index': value[3]} for value in values],
              'seconds': elapsed, 'target_seconds': seconds, 'tps': count / elapsed,
              'started_monotonic': timing['start'], 'finished_monotonic': end,
              'warmup_batches_per_worker': warmup_batches,
              'fixture_count': len(fixture.offsets),
              'completion_progress': progress_rows,
              'completion_progress_interval': progress_every,
              'fixture_sha256': fixture.digest.hexdigest(),
              'fixture_index_bytes': len(fixture.offsets) * fixture.offsets.itemsize,
              'fixture_mapped_bytes': len(fixture.mapping),
              'fixture_read_worker_seconds': fixture.read_seconds - read_before,
              'client_cpu_seconds': client_cpu_seconds,
              'host_before': host_before,
              'host_after': {'utc_ns': time.time_ns(), 'load_average': os.getloadavg()},
              'client_scope': 'RPC plus client JSON, bounded mmap reads and scheduling; no signing/funding/thread or connection startup'}
    if readers:
        pairs = sum(value[0] for value in reader_values)
        bins = [sum(value[1][i] for value in reader_values) for i in range(10002)]
        result['loaded_read'] = {'workers': reader_workers, 'pairs': pairs,
                                 'rpc_calls': pairs * 2, 'writer_window_seconds': elapsed,
                                 'rpc_per_second': pairs * 2 / elapsed,
                                 'latency_unit': 'two sequential RPCs',
                                 'histogram_bin_ms': 0.01, 'histogram_overflow_ms': 100.01,
                                 'histogram': bins, **histogram_percentiles(bins)}
    return result


def measure_reads(client_factory, seconds=5.0, workers=12):
    if seconds < 5:
        raise ValueError('Read measurement must last at least five seconds')
    barrier = threading.Barrier(workers + 1)
    go = threading.Event()
    timing = {}

    def reader(_):
        client = client_factory()
        try:
            client.call('getmempoolinfo')
            client.call('getblockchaininfo')
            barrier.wait()
            go.wait()
            bins = [0] * 10002
            pairs = 0
            while time.perf_counter() < timing['deadline']:
                started = time.perf_counter()
                client.call('getmempoolinfo')
                client.call('getblockchaininfo')
                elapsed = time.perf_counter() - started
                bins[min(10001, int(elapsed * 100000))] += 1
                pairs += 1
            return pairs, bins, time.perf_counter()
        except BaseException:
            barrier.abort()
            go.set()
            raise

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(reader, i) for i in range(workers)]
        barrier.wait()
        host_before = {'utc_ns': time.time_ns(), 'load_average': os.getloadavg()}
        timing['start'] = time.perf_counter()
        timing['deadline'] = timing['start'] + seconds
        go.set()
        values = [future.result() for future in futures]
    elapsed = max(value[2] for value in values) - timing['start']
    count = sum(value[0] for value in values)
    bins = [sum(value[1][i] for value in values) for i in range(10002)]
    return {'seconds': elapsed, 'workers': workers, 'pairs': count, 'rpc_calls': 2 * count,
            'rpc_per_second': 2 * count / elapsed, 'latency_unit': 'two sequential RPCs',
            'histogram_bin_ms': 0.01, 'histogram_overflow_ms': 100.01,
            'histogram': bins, **histogram_percentiles(bins), 'host_before': host_before,
            'host_after': {'utc_ns': time.time_ns(), 'load_average': os.getloadavg()}}
