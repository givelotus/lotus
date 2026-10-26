import pathlib,json,subprocess,time,os,signal,datetime,re
p=pathlib.Path(__file__).resolve().parent;d=json.loads((p/'execution-plan.json').read_text());t=time.monotonic();result={'status':'RUNNING','started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'owned_rss_samples':[]}
# Readiness/pins must be completed before any test process starts.
import hashlib
assert d['status'] == 'ACTUAL_BINARY_READY_FULL_NATIVE_GATE_DRAIN'
assert hashlib.sha256(pathlib.Path(d['binary']).read_bytes()).hexdigest() == d['binary_sha256']
assert hashlib.sha256(pathlib.Path(d['command'][1]).read_bytes()).hexdigest() == d['script_sha256']
assert subprocess.check_output(['git','-C',d['source'],'rev-parse','HEAD'],text=True).strip() == d['source_sha']
assert subprocess.check_output(['git','-C',d['source'],'rev-parse','HEAD^{tree}'],text=True).strip() == d['source_tree']
assert not subprocess.check_output(['git','-C',d['source'],'status','--porcelain'],text=True).strip()
def hostmemory():
 pressure=subprocess.check_output(['/usr/bin/memory_pressure','-Q'],text=True)
 free=int(re.search(r'free percentage: (\d+)%',pressure)[1])
 ram=int(subprocess.check_output(['/usr/sbin/sysctl','-n','hw.memsize'],text=True))
 level=int(subprocess.check_output(['/usr/sbin/sysctl','-n','kern.memorystatus_vm_pressure_level'],text=True))
 swap=subprocess.check_output(['/usr/sbin/sysctl','-n','vm.swapusage'],text=True)
 used=float(re.search(r'used = ([0-9.]+)M',swap)[1])*1048576
 return {'free_indicator_bytes':ram*free/100,'pressure_level':level,'swap_used_bytes':used}
initial=hostmemory();assert initial['free_indicator_bytes']>=6*2**30 and initial['pressure_level']<4
result['host_memory_checks']=[initial];last_host=-10
with(p/'gate.log').open('wb')as f:
 job=subprocess.Popen(d['command'],env=dict(os.environ,**d['env']),stdout=f,stderr=subprocess.STDOUT,start_new_session=True);result['owned_process_group']=job.pid;print('aged full-scope correctness PID',job.pid,flush=True);(p/'LIVE.json').write_text(json.dumps(result,indent=2)+'\n')
 while job.poll() is None:
  rows=subprocess.check_output(['ps','-axo','pid=,pgid=,rss='],text=True).splitlines();rss=sum(int(x.split()[2])*1024 for x in rows if len(x.split())==3 and int(x.split()[1])==job.pid);result['owned_rss_samples'].append({'seconds':time.monotonic()-t,'bytes':rss})
  hoststop=False
  if time.monotonic()-t-last_host>=2:
   mem=hostmemory();result['host_memory_checks'].append(mem);last_host=time.monotonic()-t
   hoststop=mem['free_indicator_bytes']<6*2**30 or mem['pressure_level']>=4 or mem['swap_used_bytes']-initial['swap_used_bytes']>4*2**30
  if hoststop or rss>d['max_owned_rss_bytes'] or time.monotonic()-t>d['max_runtime_seconds']:
   result['stopped_for']='host_memory'if hoststop else 'owned_RSS'if rss>d['max_owned_rss_bytes']else'whole_case_timeout';os.killpg(job.pid,signal.SIGTERM)
   try:job.wait(timeout=10)
   except subprocess.TimeoutExpired:os.killpg(job.pid,signal.SIGKILL);job.wait()
   break
  time.sleep(.5)
 result.update(exit_code=job.wait(),seconds=time.monotonic()-t,finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat());result['status']='PASS'if result['exit_code']==0 else'FAIL';result['peak_owned_rss_bytes']=max(x['bytes']for x in result['owned_rss_samples']);(p/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k!='owned_rss_samples'}));raise SystemExit(result['exit_code'])
