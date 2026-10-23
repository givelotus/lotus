import datetime as dt,re,json,statistics,hashlib
from pathlib import Path
root=Path(__file__).resolve().parent
result={}
for point in ['527','528']:
 p=Path(f'daemon/.local-artifact-archive/benchmark-tmp/recon-reconciliation-0-{point}/node2/regtest/debug.log');lines=p.read_text().splitlines()
 events=[x for x in lines if any(k in x for k in ['captured complete mempool','verified remote snapshot','full reconciliation admission'])]
 cov=next(x for x in lines if 'verified remote snapshot peer=' in x and 'bodies=10000' in x)
 end=dt.datetime.fromisoformat(cov.split()[0].replace('Z','+00:00'));start=end-dt.timedelta(seconds=60)
 rows={}
 for peer in [2,3]:
  sent=[];responses=[]
  for line in lines:
   if not line or not re.match(r'\d{4}-',line):continue
   t=dt.datetime.fromisoformat(line.split()[0].replace('Z','+00:00'))
   if not start<=t<=end or f'peer={peer}' not in line:continue
   if 'sending getmerklixbuck ' in line:sent.append(t)
   if 'received: merklixbuck ' in line:responses.append(t)
  gaps=[(b-a).total_seconds() for a,b in zip(sent,sent[1:])]
  rows[str(peer)]={'requests_before_first_coverage':len(sent),'responses':len(responses),'first_request':str(sent[0]) if sent else None,'last_request':str(sent[-1]) if sent else None,'request_gap_seconds_median':statistics.median(gaps) if gaps else None,'request_gap_seconds_min':min(gaps)if gaps else None,'request_gap_seconds_max':max(gaps)if gaps else None}
 result[point]={'raw_log':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'events':events,'last60seconds_request_cadence_node2':rows,'caveat':'60-second window preceding first10000-body coverage; peer3 can complete later. Counts/gaps are protocol observations, not CPU time.'}
(root/'retained-timeline.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({p:v['last60seconds_request_cadence_node2'] for p,v in result.items()},indent=2))
