import json,datetime as dt,hashlib
from pathlib import Path
root=Path(__file__).resolve().parent
rows={}
for label in ['before','after','production-check0']:
 p=root/label/'evidence.json'
 if not p.exists():continue
 d=json.loads(p.read_text())
 if not d['status'].startswith('PASS'):continue
 events=d['full_scope_event_proof'][2]['events_after_reconnect']
 stamp=lambda x:dt.datetime.fromisoformat(x.split()[0].replace('Z','+00:00'))
 capture=next(x for x in events if 'captured complete mempool' in x)
 coverage=next(x for x in events if 'verified remote snapshot' in x and 'bodies=10000' in x)
 admission=next(x for x in events if 'full reconciliation admission' in x)
 final=d['snapshots'][-1]
 rows[label]={'status':d['status'],'exact_all_peer_recovery_seconds':d['completed_sets'][-1]['seconds'],'capture_event':capture,'first_coverage_event':coverage,'first_admission_complete_event':admission,'capture_to_first_coverage_seconds':(stamp(coverage)-stamp(capture)).total_seconds(),'first_coverage_to_first_admission_seconds':(stamp(admission)-stamp(coverage)).total_seconds(),'metrics_by_node':[{'node':x['index'],**x['fullrecon_metrics']} for x in final['nodes']],'raw_body_proof':d['raw_body_proof'],'evidence_sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
(root/'PHASES.json').write_text(json.dumps(rows,indent=2)+'\n')
print(json.dumps({k:{n:v for n,v in x.items() if n.endswith('seconds')}for k,x in rows.items()},indent=2))
