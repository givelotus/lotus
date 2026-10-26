#!/usr/bin/env python3
"""Check large plain/TLS bodies, chunked framing and keep-alive; no timing claims."""
import argparse
import base64
import hashlib
import http.client
import json
import shutil
import ssl
import subprocess
import time
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--runtime', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    build = json.loads(args.build.read_text())
    binary = Path(build['binary'])
    assert hashlib.file_digest(binary.open('rb'),'sha256').hexdigest() == build['binary_sha256']
    args.runtime.mkdir(parents=True, exist_ok=False)
    args.output.mkdir(parents=True, exist_ok=False)
    port = 39211
    command = [str(binary), '-regtest', '-server', '-listen=0', '-connect=0', '-dnsseed=0',
               '-discover=0', '-avalanche=0', '-rpcbind=127.0.0.1', '-rpcallowip=127.0.0.1',
               '-rpcuser=probe', '-rpcpassword=local-probe', f'-rpcport={port}',
               '-printtoconsole=0', '-datadir='+str(args.runtime.resolve())]
    headers = {'Authorization':'Basic '+base64.b64encode(b'probe:local-probe').decode(),
               'Content-Type':'application/json'}
    result = dict(status='running', source=build, command=command, cases=[],
                  script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  cleanup='Fresh generated node data removed only after clean exit; logs retained')
    log = (args.output/'process.log').open('w')
    proc = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
    try:
        for _ in range(200):
            if proc.poll() is not None:
                raise RuntimeError('Owned daemon failed during startup')
            try:
                connection = http.client.HTTPConnection('127.0.0.1',port,timeout=1)
                connection.request('POST','/',json.dumps({'method':'echo','params':['ready'],'id':1}),headers)
                response = connection.getresponse()
                ready = response.status == 200 and json.loads(response.read()).get('result') == ['ready']
                connection.close()
                if ready:
                    break
            except (OSError, http.client.HTTPException):
                pass
            time.sleep(.1)
        else:
            raise RuntimeError('Owned daemon readiness timeout')
        value = 'body π🙂 boundary ' * 2048
        payload = json.dumps([{'method':'echo','params':[value],'id':i} for i in range(4)],ensure_ascii=False).encode()
        for tls in (False, True):
            for chunked in (False, True):
                conn = (http.client.HTTPSConnection('127.0.0.1',port,timeout=15,context=ssl._create_unverified_context())
                        if tls else http.client.HTTPConnection('127.0.0.1',port,timeout=15))
                body = (payload[n:n+137] for n in range(0,len(payload),137)) if chunked else payload
                conn.request('POST','/',body,headers,encode_chunked=chunked)
                response = conn.getresponse()
                assert response.status == 200
                rows = json.loads(response.read())
                assert len(rows) == 4
                for i, row in enumerate(rows):
                    assert row['id'] == i and row['error'] is None and row['result'] == [value]
                conn.request('POST','/',json.dumps({'method':'echo','params':['after'],'id':99}),headers)
                response = conn.getresponse()
                row = json.loads(response.read())
                assert response.status == 200 and row['id'] == 99 and row['result'] == ['after'] and row['error'] is None
                conn.close()
                result['cases'].append(dict(tls=tls,chunked=chunked,request_bytes=len(payload),large_results=4,keep_alive_followup='PASS'))
        result['status'] = 'PASS'
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill();proc.wait();result['forced_kill']=True
        log.close()
        result['daemon_exit'] = proc.returncode
        if result['status'] != 'PASS':
            result['status'] = 'FAIL'
        (args.output/'RESULTS.json').write_text(json.dumps(result,indent=2)+'\n')
        if result['status'] == 'PASS' and proc.returncode == 0 and not result.get('forced_kill'):
            shutil.rmtree(args.runtime)
        else:
            raise RuntimeError('Roundtrip failed or daemon did not stop cleanly; runtime preserved')
    print(json.dumps(result,indent=2))

if __name__ == '__main__':
    main()
