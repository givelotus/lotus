#!/usr/bin/env python3
"""Fresh native three-node sealed relay proof, with observed frames and outcomes."""
import hashlib
import io
import json
import os
from pathlib import Path
import socket
import struct
import sys
import threading
import time

SOURCE = Path(os.environ.get('LOTUS_TEST_SOURCE', '/Users/shammah/repos/lotus-v2-benchmark-recon-after-definition'))
sys.path.insert(0, str(SOURCE / 'test/functional'))
os.environ.setdefault('SRCDIR', str(SOURCE))
from test_framework.messages import CBlockHeader, lotus_v2_branch_leaf
from test_framework.metrics import m, scrape
from test_framework.test_framework import BitcoinTestFramework
from test_framework.util import assert_equal
from test_framework.wallet import NativeMiniWallet, MiniWalletMode
from test_framework.xpiaddr import encode
from test_framework.ws_transport import P2P_V2_MESSAGE_TYPES, P2PV2Converter, WebSocketLayer

OUT = Path(os.environ['SEALED_PROOF_OUTPUT'])


class FrameProxy:
    """Decode p2p-v2 WebSocket messages; suppress tx relay and forward plain frames."""
    def __init__(self, destination):
        self.destination = destination
        self.listener = socket.socket()
        self.listener.bind(('127.0.0.1', 0))
        self.listener.listen(1)
        self.port = self.listener.getsockname()[1]
        self.records, self.errors, self.sockets = [], [], []
        self.lock = threading.Lock()
        self.phase = 'setup'
        self.drop_transactions = False
        self.stopping = False
        self.thread = threading.Thread(target=self.accept, daemon=True)
        self.thread.start()

    def accept(self):
        try:
            client, _ = self.listener.accept()
            upstream = socket.create_connection(self.destination, timeout=10)
            # Native peers negotiate p2p-v2, including its stream dictionary.
            # The payload proxy decodes that stream before selective dropping.
            request = self.http_header(client)
            lines = request.decode('latin1').split('\r\n')
            lines = [line for line in lines if not line.lower().startswith('sec-websocket-protocol:')]
            request = ('\r\n'.join(lines).rstrip('\r\n') +
                       '\r\nSec-WebSocket-Protocol: p2p-v2\r\n\r\n').encode('latin1')
            upstream.sendall(request)
            response = self.http_header(upstream)
            if not response.startswith(b'HTTP/1.1 101'):
                raise ValueError('WebSocket upgrade rejected: '+repr(response[:100]))
            if b'sec-websocket-protocol: p2p-v2' not in response.lower():
                raise ValueError('Plain p2p-v2 not negotiated')
            client.sendall(response)
            upstream.settimeout(None)
            self.sockets = [client, upstream]
            threads = [threading.Thread(target=self.forward, args=(client, upstream, '0_to_2'), daemon=True),
                       threading.Thread(target=self.forward, args=(upstream, client, '2_to_0'), daemon=True)]
            for thread in threads: thread.start()
            for thread in threads: thread.join()
        except BaseException as error:
            if not self.stopping: self.errors.append(repr(error))

    @staticmethod
    def exact(sock, size):
        data = bytearray()
        while len(data) < size:
            part = sock.recv(size-len(data))
            if not part: raise EOFError('P2P connection closed')
            data.extend(part)
        return bytes(data)

    @classmethod
    def http_header(cls, sock):
        data = bytearray()
        while not data.endswith(b'\r\n\r\n'):
            data.extend(cls.exact(sock, 1))
            if len(data) > 16384: raise ValueError('Oversize HTTP upgrade')
        return bytes(data)

    def forward(self, incoming, outgoing, direction):
        try:
            pieces, wire_pieces = [], []
            message_rsv = 0
            converter = P2PV2Converter(b'PROF')
            encoder = WebSocketLayer(client=direction=='0_to_2', v2_magic=b'PROF')
            while not self.stopping:
                prefix = self.exact(incoming, 2)
                final, opcode = bool(prefix[0]&128), prefix[0]&15
                rsv = prefix[0]&112
                if rsv not in (0,32,64): raise ValueError('Unexpected WebSocket reserved bits')
                masked, size = bool(prefix[1]&128), prefix[1]&127
                header = prefix
                if size == 126:
                    ext = self.exact(incoming, 2); header += ext
                    size = int.from_bytes(ext, 'big')
                elif size == 127:
                    ext = self.exact(incoming, 8); header += ext
                    size = int.from_bytes(ext, 'big')
                if size > 32*1024*1024: raise ValueError('Oversize WebSocket frame')
                mask = self.exact(incoming, 4) if masked else b''
                header += mask
                raw = self.exact(incoming, size)
                wire = header+raw
                if opcode >= 8:
                    outgoing.sendall(wire)
                    if opcode == 8: return
                    continue
                if opcode not in (0, 2): raise ValueError('Non-binary P2P frame')
                if opcode == 2: message_rsv = rsv
                decoded = bytes(byte ^ mask[i%4] for i,byte in enumerate(raw)) if masked else raw
                pieces.append(decoded); wire_pieces.append(wire)
                if not final: continue
                message = b''.join(pieces)
                wire_message = b''.join(wire_pieces)
                pieces, wire_pieces = [], []
                # Decode every ingress message, including suppressed ones,
                # so its zstd stream remains synchronized. Forward uncompressed
                # p2p-v2 frames: downstream never depends on a dropped message's
                # compressor history. This is a payload proxy, not a latency or
                # wire-compression benchmark.
                v1 = converter.from_wire(message, message_rsv==64, message_rsv==32)
                # The framework's synthetic V1 shim does not truncate known
                # names longer than twelve bytes (getmerklixbuck). Do not feed
                # that shim through its fixed-24-byte V1 encoder: construct the
                # native p2p-v2 body directly, preserving the actual name.
                command = next((name for name in P2P_V2_MESSAGE_TYPES
                                if len(name)>12 and v1[4:].startswith(name.encode())),
                               v1[4:16].rstrip(b'\x00').decode('ascii'))
                payload = v1[24+max(0,len(command)-12):]
                if command in P2P_V2_MESSAGE_TYPES:
                    prefix = bytes([P2P_V2_MESSAGE_TYPES.index(command)+1])
                else:
                    prefix = b'\x00'+bytes([len(command)])+command.encode()
                forwarded = encoder._frame(2, prefix+payload)
                with self.lock:
                    dropped = self.drop_transactions and direction == '0_to_2' and command in ('tx', 'shorttx', 'txbatch')
                    record = {'phase': self.phase, 'direction': direction, 'command': command,
                              'payload_bytes': len(payload), 'ingress_wire_bytes': len(wire_message), 'forwarded_wire_bytes': len(forwarded), 'dropped': dropped,
                              'ingress_rsv': message_rsv,
                              'monotonic': time.monotonic(), 'payload_sha256': hashlib.sha256(payload).hexdigest()}
                    if command == 'sealedheader':
                        blockheader = CBlockHeader()
                        blockheader.deserialize(io.BytesIO(payload))
                        record['block_hash'] = blockheader.hash_hex
                    self.records.append(record)
                if not dropped: outgoing.sendall(forwarded)
        except (EOFError, ConnectionError, OSError) as error:
            if not self.stopping and not isinstance(error, EOFError): self.errors.append(repr(error))
        except BaseException as error:
            self.errors.append(repr(error))

    def set_phase(self, phase, drop=False):
        with self.lock:
            self.phase, self.drop_transactions = phase, drop

    def phase_records(self, phase):
        with self.lock: return [dict(r) for r in self.records if r['phase'] == phase]

    def close(self):
        self.stopping = True
        for sock in self.sockets + [self.listener]:
            try: sock.shutdown(socket.SHUT_RDWR)
            except OSError: pass
            sock.close()
        self.thread.join(timeout=5)


class NativeSealedRelayProof(BitcoinTestFramework):
    num_nodes = 3
    setup_clean_chain = True
    extra_args = [[ '-metrics', '-highbandwidthtx=1', '-testdisablehighbandwidthshorttx=0',
                    '-gbtwithoutpeers=1', '-debug=net'] for _ in range(3)]

    def setup_network(self):
        self.setup_nodes()
        self.connect_nodes(0, 1)
        self.proxy = FrameProxy(('127.0.0.1', self.nodes[2].p2p_port))
        self.nodes[0].addnode(f'127.0.0.1:{self.proxy.port}', 'onetry')
        def ready():
            if self.proxy.errors: raise RuntimeError(str(self.proxy.errors))
            return len(self.nodes[0].getpeerinfo()) == 2 and len(self.nodes[2].getpeerinfo()) == 1
        self.wait_until(ready, timeout=20)
        self.wait_until(lambda: all(p['version'] > 0 for n in self.nodes for p in n.getpeerinfo()))

    def metrics(self):
        time.sleep(1.1)
        return [{outcome: scrape(node).total(m('sealed_headers_total'), outcome=outcome)
                 for outcome in ('rebuilt','already_have','fallback','invalid','rejected')} for node in self.nodes]

    def run_test(self):
        self.result = {'status': 'running', 'transport': 'WebSocket p2p-v2; proxy decodes ingress compression and forwards uncompressed payload frames', 'cases': [], 'semantics': 'correctness proof, not throughput benchmark'}
        try:
            wallet = NativeMiniWallet(self.nodes[0], mode=MiniWalletMode.RAW_P2PK)
            address = encode('rxpi', lotus_v2_branch_leaf(wallet.get_scriptPubKey()))
            self.generate(wallet, 101)
            funding = wallet.send_self_transfer_multi(from_node=self.nodes[0], num_outputs=256)
            self.generate(wallet, 1)
            assert all(not n.getrawmempool() for n in self.nodes)
            for index, (case, missing) in enumerate([('shared_mempool', False), ('missing_transactions', True)]):
                self.proxy.set_phase(case+'_ingest', missing)
                coins = funding['new_utxos'][index*128:(index+1)*128]
                expected = set()
                for coin in coins:
                    tx = wallet.create_self_transfer(utxo_to_spend=coin, fee=wallet._currency.from_atoms(10000))
                    # Seed exact inventories through RPC to isolate sealed
                    # block reconstruction from transaction-gossip behavior.
                    for node in (self.nodes[:2] if missing else self.nodes):
                        assert_equal(node.sendrawtransaction(tx['hex']), tx['txid'])
                    expected.add(tx['txid'])
                assert_equal(len(expected), 128)
                target_nodes = self.nodes[:2] if missing else self.nodes
                self.wait_until(lambda: all(set(n.getrawmempool()) == expected for n in target_nodes), timeout=30)
                if missing:
                    time.sleep(1)
                    assert_equal(self.nodes[2].getrawmempool(), [])
                inventories = [n.getrawmempool() for n in self.nodes]
                before = self.metrics()
                self.proxy.set_phase(case, missing)
                started = time.monotonic()
                block_hash = self.nodes[0].generatetoaddress(1, address, coinbase_version=7, invalid_call=False)[0]
                self.wait_until(lambda: all(n.getbestblockhash() == block_hash for n in self.nodes), timeout=30)
                observed_seconds = time.monotonic()-started
                after = self.metrics()
                blocks = [n.getblock(block_hash, 1) for n in self.nodes]
                headers = [n.getblockheader(block_hash) for n in self.nodes]
                for block in blocks:
                    assert_equal(len(block['tx']), 129)
                    assert_equal(set(block['tx'][1:]), expected)
                assert_equal(headers[0], headers[1])
                assert_equal(headers[1], headers[2])
                deltas = [{k: after[i][k]-before[i][k] for k in before[i]} for i in range(3)]
                records = self.proxy.phase_records(case)
                sealed = [r for r in records if r['direction']=='0_to_2' and r['command']=='sealedheader' and r.get('block_hash')==block_hash and not r['dropped']]
                assert sealed, records
                assert deltas[1]['rebuilt'] >= 1, deltas
                assert_equal(deltas[1]['fallback'], 0)
                for delta in deltas:
                    assert_equal(delta['invalid'], 0)
                    assert_equal(delta['rejected'], 0)
                body = [r for r in records if r['direction']=='0_to_2' and r['command'] in ('block','cmpctblock','blocktxn') and not r['dropped']]
                if missing:
                    assert deltas[2]['fallback'] >= 1, deltas
                    assert body, records
                else:
                    assert deltas[2]['rebuilt'] >= 1, deltas
                    assert_equal(deltas[2]['fallback'], 0)
                    assert_equal(body, [])
                assert_equal(self.proxy.errors, [])
                for node in self.nodes: assert node.verifychain(4, 1)
                self.result['cases'].append({'name':case,'status':'ok','block_hash':block_hash,
                    'block_tx_count':129,'expected_txids':sorted(expected),'mempool_before':inventories,
                    'metrics_before':before,'metrics_after':after,'metric_deltas':deltas,
                    'proxy_frames':records,'accepted_headers':headers,
                    'observed_completion_seconds':observed_seconds,'not_a_tps_measurement':True})
                OUT.write_text(json.dumps(self.result,indent=2,default=str)+'\n')
            self.result['status']='ok'
        except BaseException as error:
            self.result['status']='failed'
            self.result['exception']=repr(error)
            raise
        finally:
            if hasattr(self,'proxy'):
                self.proxy.close()
                self.result['proxy_errors']=self.proxy.errors
                self.result['all_proxy_frames']=self.proxy.records
            OUT.write_text(json.dumps(self.result,indent=2,default=str)+'\n')


if __name__ == '__main__':
    NativeSealedRelayProof().main()
