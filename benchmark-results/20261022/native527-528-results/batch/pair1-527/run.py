import pathlib,json,subprocess,hashlib,time,os,signal,datetime,re,shlex
plan=json.load(open(pathlib.Path('benchmark-results/20261022/native527-528-results/batch/pair1-527/execution-plan.json')));tooling=pathlib.Path('/Users/shammah/repos/lotus-v2-optimizations/daemon/patch-audit/consolidation/20261022/benchmark-tools');scripts=tooling/'scripts'
assert plan['status']=='READY_ROOT_EXCLUSIVE_RUNTIME_LEASE'
os.environ.update(plan['environment'])
for name,digest in plan['module_hashes'].items():assert hashlib.sha256((scripts/name).read_bytes()).hexdigest()==digest
assert hashlib.file_digest(open(plan['binary'],'rb'),'sha256').hexdigest()==plan['binary_sha256']
assert subprocess.check_output(['git','-C',plan['source'],'rev-parse','HEAD'],text=True).strip()==plan['source_sha']
assert subprocess.check_output(['git','-C',plan['source'],'rev-parse','HEAD^{tree}'],text=True).strip()==plan['source_tree']
def system_memory():
 pressure=subprocess.check_output(['/usr/bin/memory_pressure','-Q'],text=True)
 free=int(re.search(r'free percentage: (\d+)%',pressure)[1])
 ram=int(subprocess.check_output(['/usr/sbin/sysctl','-n','hw.memsize'],text=True))
 level=int(subprocess.check_output(['/usr/sbin/sysctl','-n','kern.memorystatus_vm_pressure_level'],text=True))
 swap=subprocess.check_output(['/usr/sbin/sysctl','-n','vm.swapusage'],text=True)
 used=float(re.search(r'used = ([0-9.]+)M',swap)[1])*1048576
 return {'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'free_indicator_percent':free,'free_indicator_bytes':ram*free/100,'pressure_level':level,'swap_used_bytes':used}
baseline_memory=system_memory()
assert baseline_memory['free_indicator_bytes']>=6*1024**3 and baseline_memory['pressure_level']<4,baseline_memory
samplers=[]
receipts=[]
for case in plan['cases']:
 receipt={'host_memory_checks':[baseline_memory], 'case':case,'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'load_before':os.getloadavg(),'throughput_measured':not case['fixed_work_diagnostic'],'diagnostic_only':case['fixed_work_diagnostic'],'rss_samples':[]}
 output=pathlib.Path(case['argv'][case['argv'].index('--output')+1]);log=output.with_suffix('.log');started=time.monotonic()
 with log.open('w') as stream:
  process=subprocess.Popen(case['argv'],stdout=stream,stderr=subprocess.STDOUT,start_new_session=True);receipt['owned_group']=process.pid;print(case['case'],'steady-state PID',process.pid,flush=True)
  seen_progress=0
  while process.poll() is None:
   text=log.read_text(errors='replace')
   observed=[json.loads(row) for row in re.findall(r'\[completion-progress\] (\{[^\n]+\})',text)]
   latest=observed[-1] if observed else None
   peer_rows=[json.loads(row) for row in re.findall(r'\[network-progress\] (\{[^\n]+\})',text)]
   if len(peer_rows)>len(receipt.get('network_progress',[])):
    receipt['network_progress']=peer_rows;os.fsync(stream.fileno())
    with (output.parent/'LIVE-NETWORK-CHECKPOINT.json').open('w') as network_checkpoint:
     json.dump({'status':'RUNNING_NETWORK_DIAGNOSTIC','owned_group':process.pid,'latest_peer_inventory':peer_rows[-1],'receipt':receipt},network_checkpoint,indent=2);network_checkpoint.flush();os.fsync(network_checkpoint.fileno())
   for schedule in plan['sampling'].get('peer_schedule',[]):
    node,threshold=schedule['node'],schedule['depth']
    latest_local=next((row for row in peer_rows[-1]['nodes'] if row['node']==node),None) if peer_rows else None
    if latest_local and latest_local['size']>=threshold and not any(item.get('node')==node and item['threshold']==threshold for item in samplers):
     commands=subprocess.check_output(['ps','-axo','pid=,pgid=,command='],text=True).splitlines();targets=[]
     for line in commands:
      parts=line.split(None,2)
      if len(parts)!=3 or int(parts[1])!=process.pid:continue
      argv=shlex.split(parts[2])
      if argv and argv[0]==plan['binary'] and any(arg.startswith('-datadir=') and arg.endswith('/node'+str(node)) for arg in argv):targets.append(int(parts[0]))
     if len(targets)!=1:
      os.killpg(process.pid,signal.SIGTERM);process.wait(timeout=10)
      raise RuntimeError('Cannot identify exact ownedpeer for diagnostic sample')
     sample_path=output.parent/('node'+str(node)+'-local-depth-'+str(threshold)+'.sample.txt')
     job=subprocess.Popen(['/usr/bin/sample',str(targets[0]),'1','1','-file',str(sample_path)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
     samplers.append({'node':node,'threshold':threshold,'target_pid':targets[0],'path':str(sample_path),'launch_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'launch_local_inventory':latest_local,'launch_ingress_progress':latest,'process':job})
   if latest and latest['completed_transactions']>seen_progress:
    seen_progress=latest['completed_transactions'];receipt['completion_progress']=observed;os.fsync(stream.fileno())
    for threshold in plan["sampling"]["depth_thresholds"]:
     if seen_progress>=threshold and not any(item['threshold']==threshold for item in samplers):
      commands=subprocess.check_output(['ps','-axo','pid=,pgid=,command='],text=True).splitlines();targets=[]
      for line in commands:
       parts=line.split(None,2)
       if len(parts)!=3 or int(parts[1])!=process.pid:continue
       argv=shlex.split(parts[2])
       if argv and argv[0]==plan['binary'] and any(arg.startswith('-datadir=') and arg.endswith('/node0') for arg in argv):targets.append(int(parts[0]))
      if len(targets)!=1:
       os.killpg(process.pid,signal.SIGTERM);process.wait(timeout=10)
       raise RuntimeError('Cannot identify exact ownednode0 for diagnostic sampler; ownedgroupstopped')
      sample_path=output.parent/('node0-depth-'+str(threshold)+'.sample.txt')
      job=subprocess.Popen(['/usr/bin/sample',str(targets[0]),'1','1','-file',str(sample_path)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
      samplers.append({'threshold':threshold,'target_pid':targets[0],'path':str(sample_path),'launch_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'launch_progress':latest,'process':job})
    receipt['sample_windows']=[{**{k:v for k,v in row.items() if k!='process'},'returncode':row['process'].poll()} for row in samplers]
    checkpoint={'status':'RUNNING_DIAGNOSTIC_ONLY','owned_group':process.pid,'latest_progress':latest,'receipt':receipt}
    checkpoint_path=output.parent/'LIVE-CHECKPOINT.json'
    with checkpoint_path.open('w') as checkpoint_file:json.dump(checkpoint,checkpoint_file,indent=2);checkpoint_file.flush();os.fsync(checkpoint_file.fileno())

   rows=subprocess.check_output(['ps','-axo','pid=,pgid=,rss='],text=True).splitlines();rss=sum(int(x.split()[2])*1024 for x in rows if len(x.split())==3 and int(x.split()[1])==process.pid);receipt['rss_samples'].append({'elapsed':time.monotonic()-started,'bytes':rss})
   memory_stop=False
   if len(receipt['rss_samples'])==1 or time.monotonic()-started-receipt.get('last_host_check_elapsed',-10)>=2:
    mem=system_memory();receipt['host_memory_checks'].append(mem);receipt['last_host_check_elapsed']=time.monotonic()-started
    memory_stop=(mem['free_indicator_bytes']<6*1024**3 or mem['pressure_level']>=4 or mem['swap_used_bytes']-baseline_memory['swap_used_bytes']>4*1024**3)
   if memory_stop or rss>case['owned_rss_limit_bytes'] or time.monotonic()-started>case['max_seconds']:
    receipt['stopped_for']='system_memory_pressure_or_swap' if memory_stop else 'RSS' if rss>case['owned_rss_limit_bytes'] else 'timeout';os.killpg(process.pid,signal.SIGTERM)
    try:process.wait(timeout=10)
    except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait()
    break
   time.sleep(.5)
  receipt['returncode']=process.wait()
 for item in samplers:
  item['returncode']=item['process'].wait(timeout=10)
 receipt['sample_windows']=[{k:v for k,v in item.items() if k!='process'} for item in samplers]
 receipt['elapsed_seconds']=time.monotonic()-started;receipt['load_after']=os.getloadavg();receipt['log']=str(log);receipt['peak_observed_owned_rss_bytes']=max(x['bytes'] for x in receipt['rss_samples']);receipts.append(receipt)
 (pathlib.Path('benchmark-results/20261022/native527-528-results/batch/pair1-527/execution-results.json')).write_text(json.dumps({'status':'failed' if receipt['returncode'] else 'in_progress','throughput_measured':False,'fixed_work_diagnostic':True,'receipts':receipts},indent=2)+'\n')
 if receipt['returncode']:raise SystemExit(receipt['returncode'])
 data=json.load(open(output));metric=data['metrics'][case['case']]
 assert data['status']=='ok'
 assert metric['fixture_count']==case['exact_fixture_count']
 assert metric['preparation']['disk_bytes']<=case['max_final_fixture_bytes']
 assert all(data['metrics']['preparation_pilot_cleanup'].values())
 assert metric['post_measurement_mempool']['size']==metric['tx_count']+16*metric['batch_size']
 if case['fixed_work_diagnostic']:
  assert metric['seconds']>0 and 'tps' not in metric
  assert metric['tx_count']==case['exact_fixture_count']-16*metric['batch_size']
  print(case['case'],'FINITE LATENCY PASS',metric['tx_count'],metric['seconds'],'seconds; no sustainable TPS claim',flush=True)
 else:
  assert metric['seconds']>=5 and metric['tx_count']>0
  print(case['case'],'STEADY PASS',metric['tx_count'],metric['seconds'],'seconds;',metric['tps'],'tx/s',flush=True)

(pathlib.Path('benchmark-results/20261022/native527-528-results/batch/pair1-527/execution-results.json')).write_text(json.dumps({'status':'PASS','throughput_measured':False,'fixed_work_diagnostic':True,'receipts':receipts},indent=2)+'\n')
