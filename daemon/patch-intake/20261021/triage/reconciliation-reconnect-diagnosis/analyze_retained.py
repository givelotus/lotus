"""Audit retained admission times/messages, not a protocol simulation."""
import argparse,collections,datetime,hashlib,json,pathlib,re
ap=argparse.ArgumentParser();ap.add_argument('retained',type=pathlib.Path);ap.add_argument('--output',type=pathlib.Path);args=ap.parse_args();p=args.retained
parse=lambda text:datetime.datetime.fromisoformat(text.replace('Z','+00:00'))
sets=json.loads((p/'MISSING-SET-FINAL.json').read_text());allids=set(sets['snapshots'][0]['txids']);missing=set(sets['node2_missing_txids']);evidence=json.loads((p/'evidence.json').read_text());times=[];nodes=[];reconnect=None
for n in range(3):
 tx={};messages=collections.defaultdict(list);received_generic=collections.Counter();modeled_rates={};modeled_drops=collections.Counter();file=p/f'data/node{n}/regtest/debug.log'
 for line in file.read_text().splitlines():
  timestamp=parse(line.split()[0]) if line and line[0].isdigit() else None
  if timestamp is None:continue
  m=re.search(r'TransactionAddedToMempool: txid=([0-9a-f]{64})',line)
  if m and m[1] in allids and 'Enqueuing TransactionAddedToMempool' not in line:tx[m[1]]=timestamp
  if n==2 and 'Added connection peer=2' in line:reconnect=timestamp
  m=re.search(r'(sending|received:) (merklixsync|getmerklixbuck|merklixbuck|getshorttx|shorttx) \((\d+) bytes\) peer=(\d+)',line)
  if not m:continue
  direction,name,size,peer=m.groups();messages[(direction,name)].append((timestamp,int(size),int(peer)))
  if direction=='received:' and name in {'merklixsync','getmerklixbuck','merklixbuck'}:
   received_generic[peer]+=1
   start,count=modeled_rates.get(peer,(timestamp,0))
   if (timestamp-start).total_seconds()>=1:start,count=timestamp,0
   if count>=32:modeled_drops[peer]+=1
   else:count+=1
   modeled_rates[peer]=(start,count)
 times.append(tx)
 nodes.append({'node':n,'admission_log_count':len(tx),'first_admission':min(tx.values()).isoformat(),'last_admission':max(tx.values()).isoformat(),'missing_admission_count':len(missing&tx.keys()),'missing_first':min(tx[x]for x in missing&tx.keys()).isoformat() if missing&tx.keys()else None,'missing_last':max(tx[x]for x in missing&tx.keys()).isoformat() if missing&tx.keys()else None,'messages':{direction+' '+name:{'count':len(v),'last':v[-1][0].isoformat(),'last_bytes':v[-1][1]}for(direction,name),v in messages.items()},'modeled_generic_rate_drops_NOT_native_counter':dict(modeled_drops),'generic_received':dict(received_generic),'debug_log_sha256':hashlib.sha256(file.read_bytes()).hexdigest()})
for n in [0,1]:
 expired={x for x in missing if x in times[n] and(reconnect-times[n][x]).total_seconds()>=30}
 nodes[n]['missing_already_aged_30s_at_first_reconnect']=len(expired)
last=max(times[2].values());progress=[x for x in evidence['inventory_progress']if x['phase']=='reconnect-exact-10000-all-peers'];out={'tested_source':'cf50cd5ef24561806eac03c665b79fc2e7edf6c7','reconnect_first_connection':reconnect.isoformat(),'last_count_change':progress[-1],'last_receiver_admission':last.isoformat(),'last_receiver_minus_latest_source_admission_seconds':[(last-max(times[n].values())).total_seconds()for n in [0,1]],'missing':len(missing),'nodes':nodes,'limits':['Logged notification times approximate actual index callback time; no actual wire root/context/prefix capture is present','Modeled rate drops replay only three generic commands, not actual handler counters; other generic users and exact time_received may shift results','Missing-set/timestamps establish age exclusion, not attribution of every missed body to one cause','Full256-bit roots, request IDs and payloads are absent from these text logs; no exact message-level reconstruction claim']}
encoded=json.dumps(out,indent=2)+'\n'
if args.output:args.output.write_text(encoded)
print(encoded)
