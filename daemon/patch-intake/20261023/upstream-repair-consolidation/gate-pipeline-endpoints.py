#!/usr/bin/env python3
"""Gate exact shared/native endpoints; keep prior owner-prefix failure visible."""
from pathlib import Path
import subprocess,sys,json,hashlib,time
ROOT=Path(__file__).resolve().parents[4];OUT=Path(__file__).resolve().parent
S=[('shared',378,'b14362f31c6c46fd10a1eb5a9d2c29362f6fa315'),('native',531,'b466fdd221427e9d60a01f6b36db6b7943ff579d')]
for name,point,commit in S:
 data=ROOT/'benchmark-results/20261023'/('pipeline-final-'+name+'-gate')
 assert not data.exists()
 cmd=[sys.executable,str(ROOT/'daemon/bench/commit-regressions/run.py'),'--build-only','--points',str(point),'--plan',str(OUT/'FROZEN-STACK.json'),'--override-ref',str(point)+'='+commit,'--variant','pipeline-final-'+name,'--data',str(data)]
 print('BUILD',name,commit,flush=True);subprocess.run(cmd,check=True)
 runtime=data/'full-unit-runtime';runtime.mkdir();binary=ROOT/'daemon/.local-artifact-archive/grok-progression-build/src/test/test_bitcoin';start=time.monotonic();binary_hash=hashlib.file_digest(binary.open('rb'),'sha256').hexdigest()
 print('FULL UNIT',name,flush=True)
 with (data/'all-units.log').open('w') as f:code=subprocess.run([str(binary),'--log_level=test_suite','--report_level=short'],cwd=runtime,stdout=f,stderr=subprocess.STDOUT).returncode
 receipt=dict(source=commit,test_binary_sha256=binary_hash,exit=code,seconds=time.monotonic()-start,scope='all '+name+' native C++ unit cases; owner268 failure preserved separately, not waived')
 (data/'ALL-UNIT-RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n');print('FULL RESULT',name,code,flush=True)
 if code:raise SystemExit(code)
