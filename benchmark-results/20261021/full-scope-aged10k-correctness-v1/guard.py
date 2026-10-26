import pathlib,json,subprocess,time,os,signal,datetime
p=pathlib.Path(__file__).resolve().parent;d=json.loads((p/'execution-plan.json').read_text());t=time.monotonic();result={'status':'RUNNING','started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'owned_rss_samples':[]}
# Readiness/pins must be completed before any test process starts.
import hashlib
assert d['status'] == 'ACTUAL_BINARY_READY_FULL_NATIVE_GATE_DRAIN'
assert hashlib.sha256(pathlib.Path(d['binary']).read_bytes()).hexdigest() == d['binary_sha256']
assert hashlib.sha256(pathlib.Path(d['command'][1]).read_bytes()).hexdigest() == d['script_sha256']
assert subprocess.check_output(['git','-C',d['source'],'rev-parse','HEAD'],text=True).strip() == d['source_sha']
assert subprocess.check_output(['git','-C',d['source'],'rev-parse','HEAD^{tree}'],text=True).strip() == d['source_tree']
assert not subprocess.check_output(['git','-C',d['source'],'status','--porcelain'],text=True).strip()
with(p/'gate.log').open('wb')as f:
 job=subprocess.Popen(d['command'],env=dict(os.environ,**d['env']),stdout=f,stderr=subprocess.STDOUT,start_new_session=True);result['owned_process_group']=job.pid;print('aged full-scope correctness PID',job.pid,flush=True);(p/'LIVE.json').write_text(json.dumps(result,indent=2)+'\n')
 while job.poll() is None:
  rows=subprocess.check_output(['ps','-axo','pid=,pgid=,rss='],text=True).splitlines();rss=sum(int(x.split()[2])*1024 for x in rows if len(x.split())==3 and int(x.split()[1])==job.pid);result['owned_rss_samples'].append({'seconds':time.monotonic()-t,'bytes':rss})
  if rss>d['max_owned_rss_bytes'] or time.monotonic()-t>d['max_runtime_seconds']:
   result['stopped_for']='owned_RSS'if rss>d['max_owned_rss_bytes']else'whole_case_timeout';os.killpg(job.pid,signal.SIGTERM)
   try:job.wait(timeout=10)
   except subprocess.TimeoutExpired:os.killpg(job.pid,signal.SIGKILL);job.wait()
   break
  time.sleep(.5)
 result.update(exit_code=job.wait(),seconds=time.monotonic()-t,finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat());result['status']='PASS'if result['exit_code']==0 else'FAIL';result['peak_owned_rss_bytes']=max(x['bytes']for x in result['owned_rss_samples']);(p/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k!='owned_rss_samples'}));raise SystemExit(result['exit_code'])
