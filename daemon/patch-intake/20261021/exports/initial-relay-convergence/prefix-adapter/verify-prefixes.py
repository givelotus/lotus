import subprocess,json,importlib.util,hashlib,argparse
from pathlib import Path
parser=argparse.ArgumentParser();parser.add_argument('--repo',required=True);R=parser.parse_args().repo;D=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('tx',D/'transform.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
shas=subprocess.check_output(['git','-C',R,'rev-list','--reverse','3a7173fde303d5ee47dc251dcdbcadd8a90537e2^..8bf07b498fcd14f7b6ddce9f3efbe8a1cf61d317'],text=True).splitlines()
paths=list(m.PAYLOAD)+['src/net/txrelay_index.h'];rows=[]
for sha in shas:
 f={}
 for p in paths:
  x=subprocess.run(['git','-C',R,'show',sha+':'+p],capture_output=True)
  if x.returncode==0:f[p]=x.stdout
 try:g=m.transform(f);assert m.transform(g)==g
 except Exception as e:print('FAIL',sha,str(e));raise
 rows.append({'commit':sha,'changed':[p for p in f if f[p]!=g[p]],'idempotent':True})
print('PASS',len(rows));(D/'prefix-ledger.json').write_text(json.dumps(rows,indent=2)+'\n')
for p in m.PAYLOAD:
 want=subprocess.check_output(['git','-C',R,'show','61c20da2c247ff5d2e50000bcef51dd64b086099:'+p]);assert g[p]==want,p
print('ENDPOINT EXACT')
