import subprocess,json,time
from pathlib import Path
R=Path(__file__).resolve().parent
receipts=[]
for point in ['before','after']:
 print('START',point,flush=True)
 result=subprocess.run(['python3',str(R/point/'run.py')])
 receipts.append({'point':point,'returncode':result.returncode})
 (R/'PAIR-EXECUTION.json').write_text(json.dumps({'status':'FAIL_STOP' if result.returncode else 'RUNNING','cases':receipts},indent=2)+'\n')
 if result.returncode:raise SystemExit(result.returncode)
(R/'PAIR-EXECUTION.json').write_text(json.dumps({'status':'PASS','cases':receipts},indent=2)+'\n')
print('BOTH FULL CASES PASS',flush=True)
