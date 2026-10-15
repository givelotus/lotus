import copy
import importlib.util
import json
from pathlib import Path
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

SPEC = importlib.util.spec_from_file_location('chronik_discovery', Path(__file__).parents[1] / 'chronik_discovery.py')
m = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = m
SPEC.loader.exec_module(m)
H = lambda i: f'{i:02x}' * 32
STATUS = dict(version=2, confirmed_only=True, pool_indexed=False, ready=True,
              generation='1', snapshot=dict(chain_id=H(1), profile_id=H(2), tip=H(3), height='5'))
COIN = dict(txid=H(4), out_idx=0, flags=0, value=str(2**64-1), token_id=H(0),
            branches=[H(9), H(10)], paths=[[0]], spend=None,
            creation=dict(txid=H(4), txhash=H(5), block_id=H(3), height='5', tx_index=0))


def page(coins=None, cursor=None):
    return dict(STATUS, outputs=[dict(record=c, matching_positions=[0]) for c in (coins if coins is not None else [COIN])], cursor=cursor)


class Queue:
    def __init__(self, *items):
        self.items, self.calls = list(items), []
    def __call__(self, path, payload):
        self.calls.append((path, payload))
        item = self.items.pop(0)
        if isinstance(item, Exception):
            raise item
        return copy.deepcopy(item)


class Tests(unittest.TestCase):
    def client(self, transport, **kwargs):
        return m.Client(transport, H(1), H(2), **kwargs)

    def test_paging_all_roots_dedup_and_native_authority(self):
        q = Queue(STATUS, page(cursor='aa'*174), page(), STATUS)
        tracked = []
        discovery, state = m.discover_and_reconcile(self.client(q), [H(9), H(10), H(9)], tracked.append, lambda: {'coins': 'native'})
        self.assertEqual(len(discovery.candidates), 1)
        self.assertEqual(discovery.candidates[0].value, 2**64-1)
        self.assertEqual(tracked, [m.Outpoint(H(4), 0)])
        self.assertEqual(state, {'coins': 'native'})
        self.assertEqual(q.calls[1][1]['any_branch'], (H(9), H(10)))
        self.assertEqual(q.calls[2][1]['cursor'], 'aa'*174)

    def test_stale_and_unavailable_restart_whole_scan(self):
        q = Queue(STATUS, page(cursor='aa'*174), m.RetryDiscovery('409'),
                  m.RetryDiscovery('503'), STATUS, page([]), STATUS)
        result = self.client(q).discover([H(9)])
        self.assertEqual(result.candidates, ())
        self.assertIsNone(q.calls[4][1])
        self.assertIsNone(q.calls[5][1]['cursor'])

    def test_generation_aba_and_tip_change_restart(self):
        for changed in [dict(STATUS, generation='2'), dict(STATUS, snapshot=dict(STATUS['snapshot'], tip=H(8)))]:
            q = Queue(STATUS, page(), changed, STATUS, page([]), STATUS)
            self.assertEqual(self.client(q).discover([H(9)]).candidates, ())

    def test_fail_closed_and_no_native_mutation(self):
        mutations = [dict(COIN, value=1), dict(COIN, value='01'), dict(COIN, value=str(2**64)),
                     dict(COIN, txid=H(4).upper()), dict(COIN, branches=[H(8)]),
                     dict(COIN, out_idx=True), dict(COIN, spend={}), dict(COIN, token_id='00')]
        # H(4) contains digits only, so use a genuinely uppercase native ID.
        mutations[3]['txid'] = 'AB'*32
        for coin in mutations:
            tracked = []
            with self.assertRaises(m.DiscoveryError):
                m.discover_and_reconcile(self.client(Queue(STATUS, page([coin]))), [H(9)], tracked.append, lambda: None)
            self.assertEqual(tracked, [])
        with self.assertRaises(m.DiscoveryError):
            self.client(Queue(dict(STATUS, snapshot=dict(STATUS['snapshot'], chain_id=H(8))))).discover([H(9)])

    def test_limits_duplicates_retry_exhaustion(self):
        for q, kwargs in [
            (Queue(STATUS, page(cursor='aa'*174)), dict(max_pages=1)),
            (Queue(STATUS, page(cursor='aa'*174), page(cursor='aa'*174)), {}),
            (Queue(STATUS, page([COIN, dict(COIN, value='2')])), {}),
            (Queue(m.RetryDiscovery('503')), dict(retries=0)),
        ]:
            with self.assertRaises(m.DiscoveryError):
                self.client(q, **kwargs).discover([H(9)])

    def test_native_rejection_stops_reconcile(self):
        calls = []
        def reject(point):
            raise RuntimeError('native proof or ownership rejected')
        with self.assertRaises(RuntimeError):
            m.discover_and_reconcile(self.client(Queue(STATUS, page(), STATUS)), [H(9)], reject, lambda: calls.append('reconcile'))
        self.assertEqual(calls, [])

    def test_real_http_transport_fixture(self):
        # Actual local HTTP transport, synthetic API responses; no daemon claim.
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def do_GET(self):
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps(STATUS).encode())
            def do_POST(self):
                request = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                self.server.received = request
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps(page()).encode())
        server = HTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            result = self.client(m.HttpTransport(f'http://127.0.0.1:{server.server_port}')).discover([H(9)])
            self.assertEqual(len(result.candidates), 1)
            self.assertEqual(server.received['any_branch'], [H(9)])
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_http_errors_size_invalid_json_and_redirect(self):
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def do_GET(self):
                code, body = self.server.reply
                self.send_response(code)
                self.send_header('Location', '/v2/status')
                self.end_headers()
                self.wfile.write(body)
        server = HTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            transport = m.HttpTransport(f'http://127.0.0.1:{server.server_port}', response_cap=50)
            for code, body, error in [(409,b'{}',m.RetryDiscovery), (503,b'{}',m.RetryDiscovery), (302,b'',m.DiscoveryError), (400,b'{}',m.DiscoveryError), (200,b'x'*51,m.DiscoveryError), (200,b'{',m.DiscoveryError), (200,b'{"x":1,"x":2}',m.DiscoveryError)]:
                server.reply = code, body
                with self.assertRaises(error):
                    transport('/v2/status', None)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == '__main__':
    unittest.main()
