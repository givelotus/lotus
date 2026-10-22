import subprocess,json,importlib.util,hashlib,argparse
from pathlib import Path
parser=argparse.ArgumentParser();parser.add_argument('--repo',required=True);R=parser.parse_args().repo;D=Path(__file__).resolve().parent;spec=importlib.util.spec_from_file_location('tx',D/'transform.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
start='23274d8fbf3ec0b9e268b094b50481ec553804e1';end='2cf83331db74d3d13c6945fcce9fb99f12027339';target='c2630fca5ac2af0e6ac066da3d822fc75b02a369';shas=subprocess.check_output(['git','-C',R,'rev-list','--reverse',start+'^..'+end],text=True).splitlines();paths=[p for p in m.PAYLOAD if p!='new_tests'];rows=[]
for sha in shas:
 f={}
 for p in paths:
  r=subprocess.run(['git','-C',R,'show',sha+':'+p],capture_output=True)
  if r.returncode==0:f[p]=r.stdout
 try:g=m.transform(f);assert m.transform(g)==g
 except Exception as e:print('FAIL',sha,str(e));raise
 rows.append({'commit':sha,'changed':[p for p in g if p not in f or f[p]!=g[p]],'idempotent':True})
print('PREFIX PASS',len(rows));proof=[]
for p in paths:
 want=subprocess.check_output(['git','-C',R,'show',target+':'+p]);assert g[p]==want,p
 proof.append({'path':p,'sha256':hashlib.sha256(g[p]).hexdigest(),'native_endpoint_exact':True})
(D/'prefix-ledger.json').write_text(json.dumps(rows,indent=2)+'\n');(D/'endpoint-proof.json').write_text(json.dumps({'base':end,'target':target,'shared_insertion_parent':start,'prefix_count':len(rows),'paths':proof},indent=2)+'\n');print('EXACT ENDPOINT')
