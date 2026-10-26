"""Opt-in finite-ingestion observation; RPC replies and peer convergence differ."""
import hashlib
import json
import re
import threading
import time


def inventory_digest(txids, expected):
    if len(txids) != expected or len(set(txids)) != expected:
        raise RuntimeError('Final mempool transaction IDs are not the exact unique count')
    digest = hashlib.sha256()
    for txid in sorted(txids):
        if not isinstance(txid, str) or not re.fullmatch('[0-9a-f]{64}', txid):
            raise RuntimeError('Malformed final mempool transaction ID')
        digest.update(txid.encode('ascii') + b'\n')
    return digest.hexdigest()


def wait_for_sizes(clients, expected, timeout=120):
    deadline = time.monotonic() + timeout
    while True:
        sizes = [client.call('getmempoolinfo')['size'] for client in clients]
        if any(size > expected for size in sizes):
            raise RuntimeError('Unexpected extra transactions before network timing')
        if all(size == expected for size in sizes):
            return sizes
        if time.monotonic() >= deadline:
            raise TimeoutError('Peers did not converge before the timed phase: ' + repr(sizes))
        time.sleep(.05)


class NetworkObservation:
    def __init__(self, clients, expected, interval=.25):
        self.clients = clients
        self.expected = expected
        self.interval = interval
        self.start = None
        self.records = []
        self.errors = []
        self.first_complete = {}
        self.stop = threading.Event()
        self.go = threading.Event()
        self.changed = threading.Event()
        self.thread = threading.Thread(target=self._observe, name='network-inventory-observer')
        self.thread.start()

    def begin(self, started_monotonic, *_):
        self.start = started_monotonic
        self.go.set()

    def _observe(self):
        try:
            self.go.wait()
            if self.stop.is_set():
                return
            while not self.stop.is_set():
                row = {'elapsed_seconds': time.perf_counter() - self.start,
                       'utc_ns': time.time_ns(), 'nodes': []}
                for index, client in enumerate(self.clients):
                    info = client.call('getmempoolinfo')
                    finished = time.perf_counter() - self.start
                    row['nodes'].append({'node': index, 'size': info['size'],
                                         'bytes': info['bytes'], 'usage': info['usage'],
                                         'response_elapsed_seconds': finished})
                    if info['size'] > self.expected:
                        raise RuntimeError('Observer found unexpected extra mempool entries')
                    if info['size'] == self.expected:
                        self.first_complete.setdefault(index, finished)
                self.records.append(row)
                print('[network-progress] ' + json.dumps(row), flush=True)
                self.changed.set()
                self.stop.wait(self.interval)
        except BaseException as error:
            self.errors.append(repr(error))
            self.changed.set()

    def finish(self, injection_finished, timeout=600):
        deadline = time.monotonic() + timeout
        try:
            while len(self.first_complete) != len(self.clients) and not self.errors:
                if time.monotonic() >= deadline:
                    raise TimeoutError('Not all peers reached the final inventory within the convergence bound')
                self.changed.wait(.25)
                self.changed.clear()
            if self.errors:
                raise RuntimeError('Network observer failed: ' + repr(self.errors))
            return {'clock': 'successful ingress RPC replies versus separately observed all-peer inventory',
                    'expected_per_node': self.expected,
                    'ingress_finished_seconds': injection_finished - self.start,
                    'first_observed_full_inventory_seconds': dict(self.first_complete),
                    'all_peers_observed_full_seconds': max(self.first_complete.values()),
                    'poll_interval_seconds': self.interval,
                    'polling_is_intrusive': True, 'progress': self.records}
        finally:
            self.close()

    def close(self):
        self.stop.set()
        self.go.set()
        if self.thread.ident is not None:
            self.thread.join(timeout=185)
            if self.thread.is_alive():
                raise RuntimeError('Network inventory observer did not drain')
