#!/usr/bin/env python3
"""Sequential frozen-harness paired cases; refuses red or unreleased endpoints."""
import argparse,hashlib,json,os,subprocess,sys,time
from pathlib import Path
R=Path(__file__).resolve().parent;REPO=R.parents[2]
p=argparse.ArgumentParser();p.add_argument('--endpoints',type=Path,required=True);p.add_argument('--phase',choices=['ordinary','reads','batch','reconciliation'],default='ordinary');p.add_argument('--ordinary-pairs',type=int,default=4);p.add_argument('--output',type=Path,required=True);p.add_argument('--total-seconds',type=int,default=3600);a=p.parse_args()
assert 1<=a.ordinary_pairs<=4
D=json.loads(a.endpoints.read_text());assert D['green_gate'] is True and D['root_runtime_lease'] is True and D['status']=='GREEN_FROZEN_ENDPOINTS_EXCLUSIVE_RUNTIME_RELEASED'
a.output.mkdir(parents=True,exist_ok=True);assert not (a.output/'RESULTS.json').exists(),'refuse prior result overwrite'
tools=Path(D['tooling_root']);scripts=tools/'scripts';tmp=REPO/'daemon/.local-artifact-archive/benchmark-tmp';tmp.mkdir(parents=True,exist_ok=True)
sha=lambda f:hashlib.sha256(Path(f).read_bytes()).hexdigest()
for name,x in D['points'].items():
 assert sha(x['binary'])==x['binary_sha256']
 assert subprocess.check_output(['git','-C',x['source'],'rev-parse','HEAD'],text=True).strip()==x['source_sha']
 assert subprocess.check_output(['git','-C',x['source'],'rev-parse','HEAD^{tree}'],text=True).strip()==x['source_tree']
 assert sha(x['cache'])==x['cache_sha256'] and sha(x['config'])==x['config_sha256']
 cache=Path(x['cache']).read_text()
 for flag in ['USE_JEMALLOC:BOOL=OFF','BUILD_WALLET:BOOL=OFF','BUILD_CHRONIK:BOOL=OFF','CMAKE_CXX_FLAGS_RELEASE:STRING=-O3']:assert flag in cache,(name,flag)
# Snapshot endpoint/release receipts and tooling hashes before any runtime.
(a.output/'ENDPOINTS.json').write_text(json.dumps(D,indent=2)+'\n')
hashes={f.name:sha(f) for f in scripts.glob('*.py')};(a.output/'TOOL-HASHES.json').write_text(json.dumps(hashes,indent=2)+'\n')
order=[]
for rep in range(a.ordinary_pairs if a.phase=='ordinary' else 1):
 order.extend((rep,point) for point in (['527','528'] if rep%2==0 else ['528','527']))
started=time.monotonic();results=[]
for rep,point in order:
 if time.monotonic()-started>a.total_seconds:raise SystemExit('Total budget reached; remaining cases UNRUN')
 x=D['points'][point];case_root=a.output/f'pair{rep+1}-{point}';case_root.mkdir(exist_ok=False)
 if a.phase=='reconciliation':
  script=R/'aged_fullscope_gate.py'
  cfg=case_root/'config.ini';cfg.write_bytes(Path(x['config']).read_bytes())
  plan={'status':'ACTUAL_BINARY_READY_FULL_NATIVE_GATE_DRAIN','binary':x['binary'],'binary_sha256':x['binary_sha256'],'source':x['source'],'source_sha':x['source_sha'],'source_tree':x['source_tree'],'script_sha256':sha(script),'max_runtime_seconds':420,'max_owned_rss_bytes':12*2**30,'command':['/opt/homebrew/bin/python3.13',str(script),'--configfile='+str(cfg),'--tmpdir='+str(tmp/f'recon-{a.output.name}-{rep}-{point}'),'--evidence='+str(case_root/'evidence.json'),'--portseed=631','--nocleanup'],'env':{'PYTHONPATH':x['source']+'/test/functional','BITCOIND':x['binary'],'SRCDIR':x['source'],'TEST_RUNNER_PORT_MIN':'35000'}}
  driver=(R/'reconciliation-guard-template.py').read_text()
 else:
  case={'ordinary':'json_rpc_batch50_steady','reads':'single_tx_loaded_steady','batch':'signed_batch200_steady'}[a.phase];warm={'ordinary':800,'reads':16,'batch':3200}[a.phase];n=500000+warm
  argv=['/usr/local/bin/python3',str(scripts/'matched_loopback.py'),'--series','v2','--steady','--case',case,'--daemon',x['binary'],'--source',x['source'],'--output',str(case_root/(case+'.json')),'--port-base','35110','--max-fixture-transactions',str(n),'--exact-fixture-transactions',str(n),'--fixture-hash-site',str(REPO/'daemon/.local-artifact-archive/python-site'),'--minimum-predicted-supply-seconds','6.0','--maxmempool-mb','2048','--hierarchical-funding','--fixture-fee-sats','10000','--diagnostic-fixed-work','--progress-chunk-transactions','10000','--network-observe']
  plan={'status':'READY_ROOT_EXCLUSIVE_RUNTIME_LEASE','source':x['source'],'source_sha':x['source_sha'],'source_tree':x['source_tree'],'binary':x['binary'],'binary_sha256':x['binary_sha256'],'tooling_head':'canonicalcopiedff9181e1+declaredfullscope/noAVA+loadedeligibilityonly','module_hashes':hashes,'environment':{'TMPDIR':str(tmp)},'cases':[{'case':case,'argv':argv,'exact_fixture_count':n,'fixed_work_diagnostic':True,'max_seconds':1200,'owned_rss_limit_bytes':12*2**30,'max_final_fixture_bytes':n*418,'max_fixture_index_bytes':n*8}],'sampling':{'peer_schedule':[],'depth_thresholds':[]}}
  driver=(R/'ingestion-driver-template.py').read_text().replace('@@CASE_ROOT@@',str(case_root)).replace('@@TOOLING_ROOT@@',str(tools))
 (case_root/'execution-plan.json').write_text(json.dumps(plan,indent=2)+'\n');(case_root/'run.py').write_text(driver)
 print('START',a.phase,rep+1,point,flush=True)
 rc=subprocess.run([sys.executable,str(case_root/'run.py')]).returncode
 row={'phase':a.phase,'pair':rep+1,'point':point,'returncode':rc,'case_root':str(case_root)}
 if rc==0 and a.phase!='reconciliation':
  metric=json.loads((case_root/(case+'.json')).read_text())['metrics'];m=metric[case];assert m['tx_count']==500000 and m['seconds']>=5
  network=metric['network_observation'];final=network['final_inventories'];assert len(final)==3
  assert all(v['mempool']['size']==n for v in final) and len({v['sorted_txid_sha256'] for v in final})==1
  row.update(ingress_seconds=m['seconds'],observed_origin_accepted_per_second=500000/m['seconds'],allpeer_seconds=network['all_peers_observed_full_seconds'],loaded_read=m.get('loaded_read'),final_txid_digest=final[0]['sorted_txid_sha256'])
 results.append(row);(a.output/'RESULTS.json').write_text(json.dumps({'status':'FAIL_STOP' if rc else 'IN_PROGRESS','phase':a.phase,'one_observation_per_case':True,'cases':results},indent=2)+'\n')
 if rc:raise SystemExit(rc)
 print('PASS',json.dumps(row),flush=True)
(a.output/'RESULTS.json').write_text(json.dumps({'status':'PASS_FULL_DRAIN','phase':a.phase,'cases':results,'elapsed_whole_matrix_seconds':time.monotonic()-started},indent=2)+'\n')
