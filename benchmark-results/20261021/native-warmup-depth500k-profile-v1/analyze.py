import collections,csv,hashlib,json,re
from pathlib import Path
R=Path(__file__).resolve().parent
APP=re.compile(r'MemPoolAccept::|CheckInputScripts|CScriptCheck::|PreparedVmTransaction::|ToV2Transaction|ToV2Input|FeeHysteresisController::|PublishMempool|CaptureMempool|PopulateMempool|RadixTree<|RCUPtr<|GetScopedTransactions|RelayReconSet|ComputeScopedMerklixRoot|TransactionSubtreeA|NormalizeCtorTxList|VerifyBip340|SignatureCache::|ScriptInterpreter::|PrecomputeMempoolAdmission|BroadcastTransaction|RelayTransaction|Processor::transactionAdded|Machine::|RpcAdmissionDispatcher::|AdmitBroadcastLocked|ResolveRelayShortIds|RemoveUnbroadcastTx|ProcessGetData|SocketSendData|PreparedNative|PrepareStoredChecked|SignatureHash|WarmNativeAdmissionSignatures')
def label(s):return s.split('  (in ',1)[0].replace('(anonymous namespace)::','')
def state(s):
 if re.search(r'__psynch_mutexwait|__ulock_wait',s):return 'mutex_wait'
 if re.search(r'__psynch_cvwait|__psynch_rw_|semaphore_wait',s):return 'condition_wait'
 if re.search(r'\b(?:__)?(?:read|kevent|kevent64|poll|select|mach_msg2_trap|workq_kernreturn|nanosleep)\b',s):return 'io_or_idle_wait'
 if '<deduplicated_symbol>' in s or '???' in s:return 'unresolved'
 return 'active_candidate'
results={};rows=[]
for depth in [50000,250000,450000]:
 path=R/f'node0-depth-{depth}.sample.txt';graph=path.read_text().split('Call graph:',1)[1].split('Total number in stack',1)[0]
 threads=[];current=None
 for line in graph.splitlines():
  t=re.match(r'^    (\d+) Thread_(\d+)(.*)$',line)
  if t:current={'ticks':int(t[1]),'id':t[2],'name':t[3].strip(),'frames':[]};threads.append(current)
  elif current:
   f=re.match(r'^([ +!:|]+)(\d+) (.*)$',line)
   if f:current['frames'].append({'depth':len(f[1]),'count':int(f[2]),'symbol':f[3]})
 leaves=collections.Counter();active=collections.Counter();waits=collections.Counter();totals=collections.Counter();threadstates={};active_by_thread={};callers=collections.defaultdict(collections.Counter)
 for t in threads:
  stack=[];n=0;states=collections.Counter();threadapps=collections.Counter()
  for i,f in enumerate(t['frames']):
   while stack and stack[-1]['depth']>=f['depth']:stack.pop()
   if i+1==len(t['frames']) or t['frames'][i+1]['depth']<=f['depth']:
    c=f['count'];n+=c;s=state(f['symbol']);totals[s]+=c;states[s]+=c
    apps=list(dict.fromkeys(label(a['symbol']) for a in stack+[f] if APP.search(a['symbol'])))
    if s=='active_candidate':
     leaves[label(f['symbol'])]+=c
     for a in apps:active[a]+=c;threadapps[a]+=c
     callers[label(f['symbol'])][apps[-1] if apps else '(other/background)']+=c
    elif s!='unresolved':waits[(s,apps[-1] if apps else '(other/background)')]+=c
   stack.append(f)
  assert n==t['ticks'],(depth,t['id'],n,t['ticks'])
  threadstates[t['id']+' '+t['name']]=dict(states)
  active_by_thread[t['id']+' '+t['name']]=threadapps.most_common(100)
 results[str(depth)]={'trace_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'exclusive_state_counts':dict(totals),'threads':threadstates,'active_application_ancestors_by_thread_NONADDITIVE':active_by_thread,'active_leaves':[{'symbol':s,'count':c,'nearest_application_callers':callers[s].most_common(3)} for s,c in leaves.most_common(30)],'active_application_ancestors_nonadditive':active.most_common(100),'wait_callers':[{'kind':s,'caller':a,'count':c} for (s,a),c in waits.most_common(15)]}
 for s,c in leaves.most_common(20):rows.append({'depth':depth,'kind':'exclusive_active_leaf','count':c,'symbol':s})
 for s,c in active.most_common(20):rows.append({'depth':depth,'kind':'active_application_ancestor_NONADDITIVE','count':c,'symbol':s})
metric=json.loads((R/'json_rpc_batch50_steady.json').read_text())['metrics']['json_rpc_batch50_steady'];receipt=json.loads((R/'execution-results.json').read_text())['receipts'][0]
progress=metric['completion_progress'];prevn=0;prevt=0;chunks=[]
for p in progress:
 n=p['completed_transactions'];t=p['elapsed_seconds'];a=metric['started_monotonic']+prevt;b=metric['started_monotonic']+t
 overlaps=[w['threshold'] for w in receipt['sample_windows'] if w['launch_monotonic']<b and w['exit_observed_monotonic']>a]
 chunks.append({'from':prevn,'to':n,'seconds':t-prevt,'completed_per_second':(n-prevn)/(t-prevt),'sample_overlap_depths':str(overlaps)})
 prevn=n;prevt=t
results['method']={'definition':'Exclusive active-candidate leaves exclude recognized waits and unresolved symbols; each thread leaf count exactly equals its root count. Active application ancestors aggregate only active leaf descendants, deduplicated per path; rows NONADDITIVE. Thread samples are NOT CPU utilization or workload percentages.','script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
(R/'hotspot-analysis.json').write_text(json.dumps(results,indent=2)+'\n')
for name,data in [('hotspots.csv',rows),('completion-chunks.csv',chunks)]:
 with (R/name).open('w') as f:w=csv.DictWriter(f,fieldnames=list(data[0]),lineterminator="\n");w.writeheader();w.writerows(data)
text='# Native523 depth profiles\n\nOne sampled fixed-work run, not a maximum sustainable TPS measurement. Counts are sampled leaf observations, not CPU percentages. Known wait/idle leaves and unresolved symbols are excluded from active candidates. Active ancestor counts are NONADDITIVE.\n'
for d in ['50000','250000','450000']:
 v=results[d];text+=f'\n## Depth {d}\n\nState counts: {v["exclusive_state_counts"]}\n\n| Active leaf | Count |\n|---|---:|\n'
 for row in v['active_leaves'][:20]:text+=f'| `{row["symbol"]}` | {row["count"]} |\n'
 text+='\nActive application ancestors (nonadditive):\n\n'
 for s,c in v['active_application_ancestors_nonadditive'][:12]:text+=f'- {c}: `{s}`\n'
 text+='\nWait callers (wall-thread waits, not CPU cost; background may be idle):\n\n'
 for row in v['wait_callers'][:6]:text+=f'- {row["count"]} {row["kind"]}: `{row["caller"]}`\n'
(R/'HOTSPOTS.md').write_text(text)
for d in ['50000','250000','450000']:
 print(d,results[d]['exclusive_state_counts']);print('ACTIVE ANCESTORS',[(s[:130],c) for s,c in results[d]['active_application_ancestors_nonadditive'][:12]])
