#!/usr/bin/env python3
"""Bounded cheap-RPC transport probe. Independent persistent clients, no mempool work."""
import argparse, base64, hashlib, http.client, json, multiprocessing as mp
import os, pathlib, subprocess, time, traceback

AUTH = 'Basic ' + base64.b64encode(b'probe:local-probe').decode()

def request(conn, payload, count):
    conn.request('POST', '/', payload, {'Authorization': AUTH, 'Content-Type': 'application/json'})
    response = conn.getresponse()
    raw = response.read()
    assert response.status == 200, (response.status, raw)
    values = json.loads(raw)
    if count == 1:
        values = [values]
    assert len(values) == count
    for item in values:
        assert item['error'] is None and item['result'] == ['transport-probe'], item
    return len(raw)

def client(port, batch, ready, start, end, out):
    try:
        conn = http.client.HTTPConnection('127.0.0.1', port, timeout=30)
        conn.connect()
        conn.sock.setsockopt(__import__('socket').IPPROTO_TCP, __import__('socket').TCP_NODELAY, 1)
        one = {'jsonrpc':'1.0', 'id':1, 'method':'echo', 'params':['transport-probe']}
        payload = json.dumps(one if batch == 1 else [dict(one, id=i) for i in range(batch)], separators=(',', ':')).encode()
        for _ in range(10): request(conn, payload, batch)
        ready.put(True)
        start.wait()
        t0, c0 = time.perf_counter(), time.process_time()
        calls = responses = read_bytes = 0
        while time.perf_counter() < end.value:
            read_bytes += request(conn, payload, batch)
            calls += batch
            responses += 1
        out.put({'calls':calls, 'http_responses':responses, 'bytes':read_bytes,
                 'seconds':time.perf_counter()-t0, 'client_cpu_seconds':time.process_time()-c0})
        conn.close()
    except BaseException:
        ready.put(False)
        out.put({'error':traceback.format_exc()})


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--binary', required=True)
    p.add_argument('--output', type=pathlib.Path, required=True)
    p.add_argument('--port', type=int, required=True)
    p.add_argument('--duration', type=float, default=5)
    p.add_argument('--sample', action='store_true')
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    datadir = args.output / 'data'
    datadir.mkdir()
    command = [args.binary, '-regtest', '-server', '-listen=0', '-discover=0', '-dnsseed=0',
               '-connect=0', '-rpcuser=probe', '-rpcpassword=local-probe',
               '-rpcport='+str(args.port), '-rpcbind=127.0.0.1', '-rpcallowip=127.0.0.1',
               '-rpcthreads=16', '-rpcworkqueue=128', '-par=8', '-checkmempool=0',
               '-datadir='+str(datadir.resolve()), '-printtoconsole=0']
    log = (args.output/'process.log').open('w')
    proc = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
    results = {'binary':str(pathlib.Path(args.binary).resolve()),
               'binary_sha256':hashlib.sha256(pathlib.Path(args.binary).read_bytes()).hexdigest(),
               'command':command, 'method':'echo', 'workers':8, 'duration':args.duration,
               'utc_start':time.time(), 'load_start':os.getloadavg(), 'cases':[]}
    try:
        for _ in range(300):
            if proc.poll() is not None: raise RuntimeError('Daemon exited during initialization')
            try:
                conn = http.client.HTTPConnection('127.0.0.1', args.port, timeout=1)
                request(conn, json.dumps({'method':'echo','params':['transport-probe'],'id':1}), 1)
                conn.close()
                break
            except Exception: time.sleep(.1)
        else: raise RuntimeError('Readiness timeout')
        ctx = mp.get_context('spawn')
        for batch in [1,50]:
            ready, out = ctx.Queue(), ctx.Queue()
            start, end = ctx.Event(), ctx.Value('d', 0)
            workers = [ctx.Process(target=client, args=(args.port,batch,ready,start,end,out)) for _ in range(8)]
            for worker in workers: worker.start()
            assert all(ready.get(timeout=30) for _ in workers)
            end.value = time.perf_counter()+args.duration
            case_start = time.perf_counter()
            start.set()
            sample = None
            if args.sample:
                sample = subprocess.Popen(['/usr/bin/sample',str(proc.pid),'1','1','-file',str(args.output/f'array{batch}.sample.txt')], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            rows = [out.get(timeout=60) for _ in workers]
            elapsed = time.perf_counter()-case_start
            for worker in workers:
                worker.join(timeout=5)
                assert worker.exitcode == 0
            if sample: assert sample.wait(timeout=10) == 0
            assert not any('error' in row for row in rows), rows
            results['cases'].append({'array_size':batch, 'workers':rows,
                'wall_seconds':elapsed, 'calls':sum(row['calls'] for row in rows),
                'calls_per_second':sum(row['calls'] for row in rows)/elapsed})
            (args.output/'results.json').write_text(json.dumps(results,indent=2))
        results['status'] = 'PASS'
    finally:
        proc.terminate()
        try: proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            proc.kill(); proc.wait(); results['forced_kill'] = True
        log.close()
        results.update(daemon_exit=proc.returncode, load_end=os.getloadavg(), utc_end=time.time())
        (args.output/'results.json').write_text(json.dumps(results,indent=2))
    print(json.dumps({k:v for k,v in results.items() if k!='command'},indent=2))

if __name__ == '__main__': main()
