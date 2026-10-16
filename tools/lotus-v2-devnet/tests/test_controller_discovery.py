"""Synthetic HTTP/native controller boundary checks; no live node evidence."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('controller_discovery_test', Path(__file__).parents[1] / 'controller.py')
c = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = c
SPEC.loader.exec_module(c)
d = c.discovery_api
H = lambda n: f'{n:02x}' * 32
STATUS = dict(version=2, confirmed_only=True, pool_indexed=False, ready=True,
              generation='1', snapshot=dict(chain_id=H(1), profile_id=H(2), tip=H(3), height='5'))
COIN = dict(txid=H(4), out_idx=7, flags=0, value='999999', token_id=H(0),
            branches=[H(9)], paths=[[0]], spend=None,
            creation=dict(txid=H(4), txhash=H(5), block_id=H(3), height='5', tx_index=0))
PAGE = dict(STATUS, outputs=[dict(record=COIN)], cursor=None)


class Tests(unittest.TestCase):
    def controller(self, reject=False):
        binding = dict(url='http://127.0.0.1:18332', chain_id=H(1), profile_id=H(2))
        ctl = c.Controller(dict(nodes=[dict(name='alice', chronik=binding)],
                                limits=dict(deadline_ms=1000)), '/tmp/synthetic-controller-only')
        ctl.started = True
        ctl.wallet_nodes = {"alice": "alice", "bob": "alice"}
        node = SimpleNamespace(name='alice', ready=dict(chain_id=H(1), profile_digest=H(2)))
        ctl._wallet = lambda name: SimpleNamespace(node=node)
        ctl.calls = []
        ctl.tracked = set()
        def invoke(name, command, request, deadline, secret=False):
            c.remaining(deadline)
            ctl.calls.append((command, request, deadline, secret))
            if command == 'info':
                return dict(result='success', chain_id=H(1), profile_digest=H(2),
                            payment_policy_registered=True,
                            payment_output=dict(branches=[H(9), H(10)]))
            if command == 'track':
                if reject:
                    raise c.ControllerError('unowned', 'native ownership rejected')
                ctl.tracked.add((request['prev_txid'], request['prev_index']))
            return dict(result='success', coins=[dict(value='17', present=True)], pending=['native-pending'])
        ctl._invoke = invoke
        return ctl

    def transport(self, items, requests):
        def factory(binding, deadline):
            def request(path, payload):
                c.remaining(deadline)
                requests.append((path, payload, deadline))
                return copy.deepcopy(items.pop(0))
            return request
        return factory

    def test_normal_discovery_native_authority_and_restart_idempotence(self):
        ctl, requests = self.controller(), []
        items = [STATUS, PAGE, STATUS] * 2
        with patch.object(c, 'DiscoveryTransport', self.transport(items, requests)):
            for attempt in range(2):
                if attempt:
                    # Recreate the controller around synthetic native durable state.
                    previous = ctl
                    ctl = self.controller()
                    ctl.tracked = previous.tracked
                # Fresh public operation, native tracking persists between invocations.
                value = ctl.execute('wallet balance alice')
                self.assertTrue(value['ok'], value)
                self.assertEqual(value['data']['coins'][0]['value'], '17')
                self.assertEqual(value['data']['pending'], ['native-pending'])
                self.assertTrue(value['data']['confirmed_discovery']['confirmed_only'])
        self.assertEqual(ctl.tracked, {(H(4), 7)})
        self.assertEqual([x[0] for x in ctl.calls], ['info', 'track', 'reconcile'])
        self.assertEqual(requests[1][1]['any_branch'], (H(9), H(10)))
        self.assertTrue(all(not x[3] for x in ctl.calls))
        self.assertEqual(ctl.calls[1][1], dict(prev_txid=H(4), prev_index=7))

    def test_stale_scan_restarts_without_native_partial_import(self):
        ctl, requests = self.controller(), []
        changed = dict(STATUS, generation='2')
        with patch.object(c, 'DiscoveryTransport', self.transport(
                [STATUS, PAGE, changed, STATUS, dict(PAGE, outputs=[]), STATUS], requests)):
            result = ctl.execute('wallet reconcile alice')
        self.assertTrue(result['ok'], result)
        self.assertEqual([x[0] for x in ctl.calls], ['info', 'reconcile'])
        self.assertEqual(result['data']['confirmed_discovery']['candidate_count'], 0)

    def test_unowned_candidate_rejected_by_native(self):
        ctl = self.controller(reject=True)
        with patch.object(c, 'DiscoveryTransport', self.transport([STATUS, PAGE, STATUS], [])):
            result = ctl.execute('wallet discover alice')
        self.assertEqual(result['result'], 'unowned')
        self.assertEqual([x[0] for x in ctl.calls], ['info', 'track'])

    def test_malformed_and_foreign_results_fail_before_track(self):
        for page in [dict(PAGE, outputs=[dict(record=dict(COIN, value='01'))]),
                     dict(PAGE, snapshot=dict(STATUS['snapshot'], chain_id=H(8)))]:
            ctl = self.controller()
            with patch.object(c, 'DiscoveryTransport', self.transport([STATUS, page], [])):
                result = ctl.execute('wallet reconcile alice')
            self.assertEqual(result['result'], 'discovery_failed')
            self.assertEqual([x[0] for x in ctl.calls], ['info'])

    def test_pending_status_do_not_query_confirmed_index(self):
        ctl = self.controller()
        with patch.object(c, 'DiscoveryTransport', side_effect=AssertionError('HTTP forbidden')):
            self.assertTrue(ctl.execute('wallet pending alice')['ok'])
            self.assertTrue(ctl.execute('wallet status alice ' + H(6))['ok'])
        self.assertEqual([x[0] for x in ctl.calls], ['pending', 'status'])

    def test_binding_and_registration_checked_before_http(self):
        for mutation in ['binding', 'registered']:
            ctl = self.controller()
            invoke = ctl._invoke
            def altered(*args, **kwargs):
                result = invoke(*args, **kwargs)
                if args[1] == 'info':
                    result['chain_id' if mutation == 'binding' else 'payment_policy_registered'] = H(8) if mutation == 'binding' else False
                return result
            ctl._invoke = altered
            with patch.object(c, 'DiscoveryTransport', side_effect=AssertionError('HTTP forbidden')):
                self.assertFalse(ctl.execute('wallet reconcile alice')['ok'])

    def test_prepare_discovers_before_native_preparation_same_deadline(self):
        ctl = self.controller()
        with patch.object(c, 'DiscoveryTransport', self.transport([STATUS, PAGE, STATUS], [])):
            result = ctl.execute('wallet prepare alice --to bob --amount 1 --fee 0')
        self.assertTrue(result['ok'], result)
        self.assertEqual([x[0] for x in ctl.calls], ['info', 'info', 'track', 'reconcile', 'prepare'])
        self.assertEqual(len({x[2] for x in ctl.calls}), 1)

    def test_trickling_http_obeys_overall_deadline(self):
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def do_GET(self):
                self.send_response(200)
                self.send_header('Content-Length', '1000')
                self.end_headers()
                try:
                    for _ in range(30):
                        self.wfile.write(b' ')
                        self.wfile.flush()
                        time.sleep(.02)
                except (BrokenPipeError, ConnectionResetError):
                    pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        server.daemon_threads = True
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        binding = dict(url=f'http://127.0.0.1:{server.server_port}', chain_id=H(1), profile_id=H(2))
        start = time.monotonic()
        try:
            with self.assertRaises(c.ControllerError) as caught:
                c.DiscoveryTransport(binding, start + .12)('/v2/status', None)
            self.assertEqual(caught.exception.code, 'timeout')
            self.assertLess(time.monotonic() - start, .5)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_deep_http_json_returns_failure_without_native_tracking(self):
        raw = b'[' * 100000 + b'0' + b']' * 100000
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def do_GET(self):
                self.send_response(200)
                self.send_header('Content-Length', str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        server.daemon_threads = True
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        ctl = self.controller()
        ctl.config['nodes'][0]['chronik']['url'] = f'http://127.0.0.1:{server.server_port}'
        try:
            result = ctl.execute('wallet balance alice')
            self.assertFalse(result['ok'], result)
            self.assertEqual(result['result'], 'protocol_error')
            self.assertEqual([x[0] for x in ctl.calls], ['info'])
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_json_depth_bound_ignores_escaped_string_delimiters(self):
        leaf = json.dumps('"' + '[' * 100 + '\\' + ']' * 100)
        self.assertIsInstance(c.decode_json('[' * 32 + leaf + ']' * 32, max_depth=32), list)
        with self.assertRaises(c.ControllerError) as caught:
            c.decode_json('[' * 33 + '0' + ']' * 33, max_depth=32)
        self.assertEqual(caught.exception.code, 'protocol_error')
        with self.assertRaises(c.ControllerError) as caught:
            c.decode_json('[' * 100000 + '0' + ']' * 100000)
        self.assertEqual(caught.exception.code, 'protocol_error')

    def test_real_http_busy_then_stale_cursor_recovers_before_native_tracking(self):
        ctl = self.controller()
        requests, times = [], []
        responses = [(503, {}), (200, STATUS), (409, {}),
                     (200, STATUS), (200, PAGE), (200, STATUS)]
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def answer(self):
                requests.append(self.path)
                times.append(time.monotonic())
                code, row = responses.pop(0)
                data = json.dumps(row).encode()
                self.send_response(code)
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            def do_GET(self):
                self.answer()
            def do_POST(self):
                self.rfile.read(int(self.headers['Content-Length']))
                self.answer()
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        server.daemon_threads = True
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        ctl.config['nodes'][0]['chronik']['url'] = f'http://127.0.0.1:{server.server_port}'
        try:
            result = ctl.execute('wallet balance alice')
            self.assertTrue(result['ok'], result)
            self.assertEqual([x[0] for x in ctl.calls], ['info', 'track', 'reconcile'])
            self.assertEqual(requests, ['/v2/status', '/v2/status', '/v2/branches/utxos',
                                        '/v2/status', '/v2/branches/utxos', '/v2/status'])
            self.assertGreaterEqual(times[1] - times[0], .04)
            self.assertGreaterEqual(times[3] - times[2], .09)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_retry_wait_respects_deadline_and_close_cancellation(self):
        ctl = self.controller()
        ctl.config['limits']['deadline_ms'] = 20
        calls = []
        def factory(binding, deadline):
            def busy(path, payload):
                calls.append(path)
                raise d.RetryDiscovery('busy')
            return busy
        with patch.object(c, 'DiscoveryTransport', factory):
            result = ctl.execute('wallet balance alice')
        self.assertEqual(result['result'], 'timeout')
        self.assertEqual(calls, ['/v2/status'])
        self.assertEqual([x[0] for x in ctl.calls], ['info'])
        ctl._discovery_cancel.set()
        with self.assertRaises(c.ControllerError) as caught:
            ctl._wait_discovery_retry(.5, time.monotonic() + 1)
        self.assertEqual(caught.exception.code, 'closed')

    def test_native_tracking_never_starts_after_deadline(self):
        ctl = self.controller()
        ctl.config['limits']['deadline_ms'] = 10
        def factory(binding, deadline):
            items = [STATUS, PAGE, STATUS]
            def slow(path, payload):
                if len(items) == 1:
                    time.sleep(.02)
                return copy.deepcopy(items.pop(0))
            return slow
        with patch.object(c, 'DiscoveryTransport', factory):
            result = ctl.execute('wallet reconcile alice')
        self.assertEqual(result['result'], 'timeout')
        self.assertEqual([x[0] for x in ctl.calls], ['info'])

    def test_operation_lock_wait_uses_command_deadline(self):
        ctl = self.controller()
        ctl.config['limits']['deadline_ms'] = 10
        ctl._operation_lock.acquire()
        try:
            self.assertEqual(ctl.execute('wallet pending alice')['result'], 'timeout')
            self.assertEqual(ctl.calls, [])
        finally:
            ctl._operation_lock.release()

    def test_endpoint_rejects_dns_credentials_redirect_paths_and_remote_hosts(self):
        for url in ['http://localhost:18332', 'http://user@127.0.0.1:18332',
                    'http://127.0.0.1', 'http://127.0.0.1:18332/path',
                    'http://192.0.2.1:18332', 'https://127.0.0.1:18332']:
            with self.assertRaises((c.ControllerError, ValueError)):
                c.discovery_endpoint(dict(url=url, chain_id=H(1), profile_id=H(2)))


if __name__ == '__main__':
    unittest.main()
