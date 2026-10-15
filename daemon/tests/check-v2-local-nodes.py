#!/usr/bin/env python3
"""Two real isolated development-node processes; caller-pinned offline corpus."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import queue
import re
import socket
import subprocess
import sys
import threading
import time

STATE_FIELDS = ('tip', 'height', 'utxo_root', 'state_root', 'monetary_bytes')
IDENTITY_FIELDS = ('chain_id', 'genesis_id', 'profile_digest')
FORBIDDEN_PORTS = {10604, 10605, 8331}


def digest(path):
    with path.open('rb') as source:
        value = hashlib.file_digest(source, 'sha256').hexdigest()
    return value


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def hex_string(value, size=None):
    return isinstance(value, str) and re.fullmatch(r'(?:[0-9a-f]{2})*', value) is not None and (size is None or len(value) == 2*size)


def check_state(value):
    require(isinstance(value, dict), 'expected state object required')
    for field in ('tip', 'utxo_root', 'state_root'):
        require(hex_string(value.get(field), 32), 'invalid expected '+field)
    require(type(value.get('height')) is int and value['height'] >= 0, 'invalid expected height')
    require(hex_string(value.get('monetary_bytes'), 56), 'explicit reference monetary bytes required')


def load_corpus(path, read_limit):
    data = json.loads(path.read_text())
    require(data.get('schema') == 'lotus-v2/local-node-corpus/1', 'unsupported corpus schema')
    check_state(data['genesis'])
    require(data['genesis']['height'] == 0, 'reference genesis height must be zero')
    require(isinstance(data.get('blocks'), list) and 2 <= len(data['blocks']) <= 32, '2..32 ordered reference blocks required')
    previous = 0
    for block in data['blocks']:
        check_state(block)
        require(block['height'] == previous+1, 'reference block heights must be contiguous')
        previous = block['height']
    for block in [*data['blocks'], data['invalid']]:
        file = (path.parent / block['path']).resolve()
        require(file.is_file() and 0 < file.stat().st_size <= read_limit, 'body missing or exceeds explicit read limit')
        block['file'] = file
        block['body'] = file.read_bytes()
        require(0<len(block['body'])<=read_limit,'body changed or exceeds explicit bound')
        block['body_sha256']=hashlib.sha256(block['body']).hexdigest()
    require(hex_string(data['invalid'].get('block_id'),32) and hex_string(data['invalid'].get('invalid_root'),32), 'independent invalid body ID/causal root required')
    require(type(data.get('initial_height')) is int and 1 <= data['initial_height'] < len(data['blocks']), 'initial sync must precede a newer block')
    require(isinstance(data.get('queries'), list) and data['queries'], 'explicit membership/nonmembership queries required')
    require(len(data['queries']) <= 32, 'query count exceeds local test bound')
    for query in data['queries']:
        require(hex_string(query.get('txid'), 32) and type(query.get('index')) is int and 0 <= query['index'] <= 0xffffffff, 'invalid outpoint query')
        require(query.get('stage') in ('initial', 'final'), 'query stage must be initial or final')
    return data


class Node:
    """Exact child ownership, JSONL correlation and durable raw output."""
    def __init__(self, label, daemon, manifest, home, network, evidence, timeout):
        self.label, self.timeout, self.evidence = label, timeout, evidence
        self.messages, self.sequence = queue.Queue(), 0
        self.command = [str(daemon), '-lotusv2node', str(manifest), str(home), str(network)]
        self.process = subprocess.Popen(self.command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE, text=True, bufsize=1)
        os.set_blocking(self.process.stdin.fileno(),False)
        self.threads = []
        for stream, suffix in ((self.process.stdout, 'stdout'), (self.process.stderr, 'stderr')):
            thread = threading.Thread(target=self.read, args=(stream, evidence / (label+'.'+suffix+'.jsonl'), suffix == 'stdout'), daemon=True)
            thread.start()
            self.threads.append(thread)
        self.ready = None

    def await_ready(self):
        self.ready = self.wait(lambda value: value.get('event') == 'ready')
        listen = self.ready['listen']
        require(listen.get('address') == '127.0.0.1' and type(listen.get('port')) is int and 0 < listen['port'] <= 65535 and listen['port'] not in FORBIDDEN_PORTS, 'node did not bind an allowed ephemeral loopback endpoint')

    def read(self, stream, path, parse):
        with path.open('x') as output:
            for line in stream:
                output.write(line)
                output.flush()
                if parse:
                    try:
                        value = json.loads(line)
                        require(isinstance(value, dict), 'JSONL object required')
                        self.messages.put(value)
                    except Exception as error:
                        self.messages.put({'_protocol_error': str(error), '_raw': line})

    def wait(self, predicate, timeout=None):
        deadline = time.monotonic()+(self.timeout if timeout is None else timeout)
        while True:
            remaining = deadline-time.monotonic()
            require(remaining > 0, self.label+' timed out waiting for native JSONL result')
            try:
                message = self.messages.get(timeout=min(remaining, 0.25))
            except queue.Empty:
                require(self.process.poll() is None, self.label+' exited before its response')
                continue
            require('_protocol_error' not in message, self.label+' malformed stdout: '+str(message))
            if predicate(message):
                return message

    def request(self, command, wait_timeout=None, **fields):
        self.sequence += 1
        identity = self.label+'-'+str(self.sequence)
        value = dict(id=identity, command=command, **fields)
        with (self.evidence / (self.label+'.requests.jsonl')).open('a') as output:
            output.write(json.dumps(value, separators=(',', ':'))+'\n')
        deadline=time.monotonic()+(self.timeout if wait_timeout is None else wait_timeout)
        pending=memoryview((json.dumps(value,separators=(',',':'))+'\n').encode())
        while pending:
            require(time.monotonic()<deadline,self.label+' timed out writing local command')
            require(self.process.poll() is None,self.label+' exited during command write')
            try:sent=os.write(self.process.stdin.fileno(),pending[:65536])
            except BlockingIOError:
                time.sleep(0.01);continue
            require(sent>0,self.label+' local command pipe closed')
            pending=pending[sent:]
        remaining=deadline-time.monotonic()
        require(remaining>0,self.label+' command deadline expired')
        return self.wait(lambda response: response.get('id') == identity,remaining)

    def stop(self):
        if self.process.poll() is None:
            try:
                self.request('stop',wait_timeout=3)
                self.process.wait(timeout=3)
            except Exception:
                self.process.terminate()
                try:
                    self.process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=3)
        for thread in self.threads:
            thread.join(timeout=2)
        require(not any(thread.is_alive() for thread in self.threads),self.label+' raw-output collector failed cleanup')
        for stream in (self.process.stdin,self.process.stdout,self.process.stderr):
            try:stream.close()
            except OSError:pass


class DelayRelay:
    """Transparent bounded TCP relay: two 16KiB pending chunks per connection."""
    def __init__(self, target, delay, evidence):
        self.target, self.delay, self.evidence = target, delay, evidence
        self.stopping, self.lock = threading.Event(), threading.Lock()
        self.listener = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.listener.bind(('127.0.0.1',0))
        self.listener.listen(4)
        self.listener.settimeout(0.1)
        self.endpoint = dict(address='127.0.0.1',port=self.listener.getsockname()[1])
        require(self.endpoint['port'] not in FORBIDDEN_PORTS,'relay ephemeral port collided with forbidden port')
        self.sockets, self.threads = [], []
        self.stats = dict(delay_seconds=delay,max_connections=4,pending_chunk_bytes_per_direction=16384,
            connections=0,chunks=0,bytes=0,events=[])
        thread=threading.Thread(target=self.accept,daemon=True)
        self.threads.append(thread)
        thread.start()

    def event(self, **event):
        with self.lock:
            self.stats['events'].append(event)
            # Corpus traffic is bounded; limit metadata independently of native buffers.
            require(len(self.stats['events'])<=65536,'relay event capacity exceeded')
            with (self.evidence/'relay.jsonl').open('a') as output:
                output.write(json.dumps(event,separators=(',',':'))+'\n')

    def accept(self):
        while not self.stopping.is_set():
            try:incoming,_=self.listener.accept()
            except socket.timeout:continue
            except OSError:return
            with self.lock:
                self.stats['connections']+=1
                identity=self.stats['connections']
            if identity>4:
                incoming.close()
                self.event(event='capacity-refused',connection=identity)
                continue
            try:upstream=socket.create_connection((self.target['address'],self.target['port']),timeout=2)
            except OSError as error:
                incoming.close();self.event(event='upstream-error',error=str(error));continue
            for endpoint in (incoming,upstream):
                endpoint.setsockopt(socket.SOL_SOCKET,socket.SO_SNDBUF,65536)
                endpoint.setsockopt(socket.SOL_SOCKET,socket.SO_RCVBUF,65536)
                endpoint.settimeout(0.1)
            with self.lock:self.sockets.extend((incoming,upstream))
            self.event(event='connection',connection=identity)
            closed=threading.Event()
            for source,destination,direction in ((incoming,upstream,'b-to-a'),(upstream,incoming,'a-to-b')):
                thread=threading.Thread(target=self.forward,args=(source,destination,direction,identity,closed),daemon=True)
                with self.lock:self.threads.append(thread)
                thread.start()

    def forward(self, source, destination, direction, identity, closed):
        stream_hash=hashlib.sha256()
        try:
            while not self.stopping.is_set() and not closed.is_set():
                try:chunk=source.recv(16384)
                except socket.timeout:continue
                if not chunk:break
                if self.stopping.wait(self.delay):break
                # One chunk remains pending until sent; stop reading upstream to
                # impose backpressure rather than grow an unbounded relay queue.
                pending=memoryview(chunk)
                deadline=time.monotonic()+2
                while pending and not self.stopping.is_set() and not closed.is_set():
                    require(time.monotonic()<deadline,'relay destination blocked beyond two seconds')
                    try:sent=destination.send(pending)
                    except socket.timeout:continue
                    require(sent>0,'relay destination closed during send')
                    pending=pending[sent:]
                forwarded=len(chunk)-len(pending)
                stream_hash.update(chunk[:forwarded])
                with self.lock:
                    self.stats['chunks']+=1;self.stats['bytes']+=forwarded
                self.event(event='chunk',connection=identity,direction=direction,bytes=forwarded,pending_bytes=len(pending),delayed_seconds=self.delay)
        except (OSError,AssertionError) as error:
            if not closed.is_set() and not self.stopping.is_set():self.event(event='stream-error',connection=identity,direction=direction,error=str(error))
        finally:
            closed.set()
            for endpoint in (source,destination):
                try:endpoint.shutdown(socket.SHUT_RDWR)
                except OSError:pass
                endpoint.close()
            self.event(event='stream-closed',connection=identity,direction=direction,sha256=stream_hash.hexdigest())

    def stop(self):
        self.stopping.set()
        self.listener.close()
        with self.lock:sockets=list(self.sockets)
        for endpoint in sockets:
            try:endpoint.shutdown(socket.SHUT_RDWR)
            except OSError:pass
            endpoint.close()
        # The accept thread stops first so the worker set cannot grow afterward.
        self.threads[0].join(timeout=3)
        for thread in self.threads[1:]:thread.join(timeout=3)
        require(not any(thread.is_alive() for thread in self.threads),'relay thread failed bounded cleanup')


def state_matches(actual, expected):
    return all(actual.get(field) == expected[field] for field in STATE_FIELDS)


def wait_state(node, expected, timeout):
    deadline = time.monotonic()+timeout
    latest = None
    while time.monotonic() < deadline:
        latest = node.request('status',wait_timeout=max(0.001,deadline-time.monotonic()))
        if state_matches(latest, expected):
            return latest
        time.sleep(0.05)
    raise AssertionError(node.label+' authoritative state did not converge: '+json.dumps(latest))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--daemon', type=Path, required=True)
    parser.add_argument('--daemon-source', required=True, help='exact reviewed native Git commit')
    parser.add_argument('--expected-daemon-sha256', required=True, help='approved built executable digest')
    parser.add_argument('--build-command', required=True, help='exact caller build command/provenance')
    parser.add_argument('--corpus', type=Path, required=True)
    parser.add_argument('--corpus-source', required=True, help='exact independent reference/compiler Git commit')
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--network-magic', required=True, help='explicit development magic, eight lowercase hex digits')
    parser.add_argument('--receive-limit', type=int, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--timeout', type=float, default=30)
    parser.add_argument('--relay-delay',type=float,default=0.05,help='transparent per-chunk delay seconds; zero disables regression delay')
    args = parser.parse_args(argv)
    for pin in (args.daemon_source, args.corpus_source):
        require(re.fullmatch(r'[0-9a-f]{40}', pin) is not None, 'full source commit required')
    require(re.fullmatch(r'[0-9a-f]{64}', args.expected_daemon_sha256) is not None, 'approved binary SHA256 required')
    require(re.fullmatch(r'[0-9a-f]{8}', args.network_magic) is not None, 'explicit lowercase network magic required')
    require(0 <= args.relay_delay <= 0.5,'relay delay outside local 0..0.5 second bound')
    require(1 <= args.timeout <= 120, 'timeout outside local 1..120 second bound')
    daemon = args.daemon.resolve()
    require(digest(daemon) == args.expected_daemon_sha256, 'binary differs from approved build')
    manifest = args.manifest.resolve()
    profile = json.loads(manifest.read_text())
    require(type(args.receive_limit) is int and profile['block_read_limit'] <= args.receive_limit <= 16*1024*1024, 'receive capacity must cover explicit manifest read bound and be <=16MiB')
    corpus = load_corpus(args.corpus.resolve(), profile['block_read_limit'])
    root = args.output.resolve()
    root.mkdir()  # Never reuse/reset prior homes or evidence.
    (root/'manifest.json').write_bytes(manifest.read_bytes())
    (root/'corpus.json').write_bytes(args.corpus.read_bytes())
    record = dict(schema='lotus-v2/local-node-check/1', harness_sha256=digest(Path(__file__)),python=sys.executable,python_version=sys.version,daemon=str(daemon), daemon_source=args.daemon_source,
        daemon_sha256=digest(daemon), build_command=args.build_command, corpus_source=args.corpus_source,
        manifest_sha256=digest(manifest), corpus_sha256=digest(args.corpus), network_magic=args.network_magic,
        receive_limit=args.receive_limit, timeout=args.timeout, checks=[], processes=[])
    (root/'bodies').mkdir()
    record['bodies']=[]
    for index,block in enumerate([*corpus['blocks'],corpus['invalid']]):
        copied=root/'bodies'/str(index)
        copied.write_bytes(block['body'])
        record['bodies'].append(dict(original=str(block['file']),copied=str(copied),sha256=block['body_sha256'],bytes=len(block['body'])))
        block['file']=copied
    nodes = []
    relay = None
    def save():
        (root/'evidence.json').write_text(json.dumps(record, indent=2)+'\n')
    def launch(label, home, connects):
        config = root/(label+'.network.json')
        config.write_text(json.dumps(dict(schema=1, magic=args.network_magic, listen=dict(address='127.0.0.1', port=0),
            connect=connects, receive_limit=args.receive_limit, local_policy='bounded-local-v1'), indent=2)+'\n')
        node = Node(label, daemon, root/'manifest.json', home, config, root, args.timeout)
        nodes.append(node)
        node.await_ready()
        record['processes'].append(dict(label=label, pid=node.process.pid, command=node.command, ready=node.ready))
        save()
        return node
    try:
        a = launch('a', root/'home-a', [])
        first = a.request('status')
        require(state_matches(first, corpus['genesis']), 'node A genesis differs from independent reference')
        identity = {field:first[field] for field in IDENTITY_FIELDS}
        require(identity['chain_id'] == profile['header']['chain_id'] and identity['genesis_id'] == profile['header']['genesis_id'], 'node chain identity differs from explicit manifest')
        def authoritative(node, expected):
            actual = wait_state(node, expected, args.timeout)
            require(all(actual.get(field) == value for field,value in identity.items()), 'authoritative profile/chain identity drift')
            return actual
        def submit(node, block):
            response = node.request('submitblock', block=block['body'].hex())
            require(response.get('retained_authenticated') is True and response.get('pending_validation') is True and response.get('accepted') is False, 'submit response must only acknowledge pending ingestion')
            record['checks'].append(dict(check='submit-pending', node=node.label, block_id=block.get('tip',block.get('block_id')), response=response))
            save()
        initial = corpus['blocks'][corpus['initial_height']-1]
        for block in corpus['blocks'][:corpus['initial_height']]:
            submit(a, block)
            status = authoritative(a, block)
            record['checks'].append(dict(check='seed-accepted', status=status))
            save()
        relay = DelayRelay(a.ready['listen'],args.relay_delay,root) if args.relay_delay else None
        peer_endpoint=relay.endpoint if relay else a.ready['listen']
        b = launch('b', root/'home-b', [peer_endpoint])
        b_sync = authoritative(b, initial)
        require(b_sync['peer_active'] > 0,'initial synchronization lost its active peer')
        require(b_sync['download_full_requests'] > 0, 'initial synchronization did not demonstrate the full-block request path')
        record['checks'].append(dict(check='initial-full-sync', status=b_sync))
        save()
        def queries(stage, expected):
            count = 0
            for query in (q for q in corpus['queries'] if q['stage'] == stage):
                pair = []
                for node in (a,b):
                    coin = node.request('coin', txid=query['txid'], index=query['index'])
                    proof = node.request('proof', txid=query['txid'], index=query['index'])
                    require(coin.get('peer_active',0)>0 and proof.get('peer_active',0)>0,'coin/proof query observed a dropped native peer')
                    require(state_matches(coin, expected) and state_matches(proof, expected), 'coin/proof snapshot differs from authoritative reference state')
                    require(all(coin.get(field) == value and proof.get(field) == value for field,value in identity.items()), 'coin/proof identity mismatch')
                    value = proof['proof']
                    require(type(value['presence']) is int and value['presence'] in (0,1,2) and hex_string(value['bitmap'],32) and isinstance(value['siblings'],list) and len(value['siblings']) <= 256 and all(hex_string(sibling,32) for sibling in value['siblings']), 'malformed proof response')
                    require(int(value['bitmap'],16).bit_count() == len(value['siblings']), 'proof bitmap/sibling cardinality mismatch')
                    require(coin['coin'] is None or hex_string(coin['coin']), 'malformed coin frame')
                    require(value['coin'] is None or hex_string(value['coin']), 'malformed proof coin frame')
                    if value['presence'] == 1:
                        require(value['coin'] == coin['coin'] and coin['coin'] is not None, 'membership proof differs from authenticated coin lookup')
                    else:
                        require(coin['coin'] is None, 'nonmembership proof has an active queried coin')
                        require((value['coin'] is None) == (value['presence'] == 0), 'empty/other-leaf proof encoding mismatch')
                    pair.append(dict(coin=coin['coin'],proof=value))
                require(pair[0] == pair[1], 'two authoritative stores disagree on coin/proof')
                if 'expected_coin' in query:
                    require(pair[0]['coin'] == query['expected_coin'], 'coin differs from independent supplied expectation')
                if 'expected' in query:
                    require(pair[0] == query['expected'], 'coin/proof differs from independent supplied expectation')
                record['checks'].append(dict(check='coin-proof-'+stage, outpoint=dict(txid=query['txid'],index=query['index']), result=pair[0], independent_proof_expectation='expected' in query, independent_coin_expectation='expected_coin' in query))
                count += 1
                save()
            require(count > 0, 'each initial/final stage requires at least one explicit query')
        queries('initial', initial)
        # Restart the exact second home, preserving its indexed bodies and state.
        b.stop()
        b = launch('b-restart', root/'home-b', [peer_endpoint])
        require(state_matches(b.ready, initial), 'node B restart did not restore its authoritative persisted tip/root/money')
        authoritative(b, initial)
        record['checks'].append(dict(check='restart-persistence', status=b.ready))
        save()
        # An ingestion acknowledgement plus unchanged roots is inconclusive.
        # Require the runtime's exact deterministic-invalid/causal-root ledger.
        submit(a, corpus['invalid'])
        deadline = time.monotonic()+args.timeout
        invalid = None
        while time.monotonic() < deadline:
            invalid = a.request('blockstatus', wait_timeout=max(0.001,deadline-time.monotonic()), block_id=corpus['invalid']['block_id'])
            if invalid.get('deterministic_invalid') is True:
                break
            time.sleep(0.05)
        require(invalid and invalid.get('known_header') is True and invalid.get('deterministic_invalid') is True and invalid.get('invalid_root') == corpus['invalid']['invalid_root'], 'invalid body lacks exact deterministic rejection evidence')
        require(invalid.get('is_active_tip') is False and invalid.get('ever_connected') is False, 'invalid fixture was active/connected')
        authoritative(a, initial)
        authoritative(b, initial)
        record['checks'].append(dict(check='invalid-body-no-state-drift', blockstatus=invalid))
        save()
        deadline=time.monotonic()+args.timeout
        baseline=None
        while time.monotonic()<deadline:
            baseline=b.request('status',wait_timeout=max(0.001,deadline-time.monotonic()))
            if baseline.get('peer_active',0)>0:break
            time.sleep(0.05)
        require(baseline and baseline.get('peer_active',0)>0,'restarted node failed to reactivate its native peer')
        latest = initial
        for block in corpus['blocks'][corpus['initial_height']:]:
            submit(a, block)
            authoritative(a, block)
            received = authoritative(b, block)
            latest = block
            record['checks'].append(dict(check='newer-block-propagated', status=received))
            save()
        final = authoritative(b, latest)
        require(final['peer_active']>0,'newer propagation lost its active native peer')
        full = final['download_full_requests']-baseline['download_full_requests']
        compact = final['download_compact_requests']-baseline['download_compact_requests']
        fallback = final['download_fallbacks']-baseline['download_fallbacks']
        compact_retained=final['download_compact_retained']-baseline['download_compact_retained']
        full_retained=final['download_full_retained']-baseline['download_full_retained']
        require(min(full,compact,fallback,compact_retained,full_retained) >= 0, 'download counters regressed')
        record['checks'].append(dict(check='propagation-transport', full_requests=full,compact_requests=compact,fallbacks=fallback,compact_retained=compact_retained,full_retained=full_retained,
            compact_evidence='retained-and-authoritative-tip-accepted' if compact_retained else 'attempted' if compact else 'not-demonstrated', note='retention alone never establishes acceptance; authoritative expected tip/root/money checked separately'))
        queries('final', latest)
        if relay:
            require(relay.stats['chunks']>0 and relay.stats['bytes']>0,'slow-response relay forwarded no actual peer traffic')
            record['checks'].append(dict(check='delayed-real-peer-response',delay_seconds=args.relay_delay,chunks=relay.stats['chunks'],bytes=relay.stats['bytes']))
        record['passed'] = True
        record['final'] = {field:final[field] for field in (*STATE_FIELDS,*IDENTITY_FIELDS)}
        save()
    except Exception as error:
        record['failure'] = dict(kind=type(error).__name__, error=str(error))
        raise
    finally:
        cleanup_errors=[]
        for node in reversed(nodes):
            try:node.stop()
            except Exception as error:cleanup_errors.append(dict(node=node.label,error=str(error)))
        if relay:
            try:relay.stop()
            except Exception as error:cleanup_errors.append(dict(relay=True,error=str(error)))
            record['relay']=relay.stats
        record['cleanup_errors']=cleanup_errors
        if cleanup_errors:
            record['passed']=False
            record['failure']=dict(kind='CleanupError',error=str(cleanup_errors))
        record['cleanup'] = [dict(label=node.label, pid=node.process.pid, exit=node.process.poll()) for node in nodes]
        save()
        require(not cleanup_errors,'bounded child/relay cleanup failed: '+str(cleanup_errors))
    print('Two isolated native node processes passed:',root)


if __name__ == '__main__':
    main()
