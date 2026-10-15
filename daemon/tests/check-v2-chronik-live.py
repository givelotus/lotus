#!/usr/bin/env python3
"""Actual native HTTP acceptance during the private-relay wallet lifecycle.

Uses the native wallet harness unchanged. No mocked HTTP, synthetic DB insertion,
manual payment mining, or production directory/port is used.
"""
import importlib.util
import json
from pathlib import Path
import sys
import time
import urllib.error
import urllib.request


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SnapshotChanged(Exception):
    pass


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    # Keep exactly the private-relay CLI and its validation/fresh-directory rules.
    if '--output' not in argv:
        raise SystemExit('--output is required (see check-v2-private-relay.py --help)')
    output = Path(argv[argv.index('--output')+1]).resolve()
    require = lambda ok, why: None if ok else (_ for _ in ()).throw(AssertionError(why))
    require(not output.exists(), 'output must be a fresh directory')
    private = load('private_relay_chronik_driver', Path(__file__).with_name('check-v2-private-relay.py'))
    local = private.local_module()
    original_node = local.Node
    evidence = dict(schema='lotus-v2/chronik-live-check/1', passed=False,
                    harness_sha256=local.digest(Path(__file__)),
                    driver_sha256=local.digest(Path(private.__file__)),
                    scope='native confirmed HTTP, compiler Payment wallets, relay, restart, reorg and re-mining',
                    checks=[], requests=[])
    known_coinbases = {}
    submitted = {}
    observed = {}
    cursors = {}
    def save():
        if output.exists():
            (output/'chronik-evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
    def record(name, **fields):
        evidence['checks'].append(dict(check=name,**fields)); save()
    class Node(original_node):
        def __init__(self, label, daemon, manifest, home, network, destination, timeout):
            config=json.loads(network.read_text())
            config['chronik_bind']='127.0.0.1:0'
            network.write_text(json.dumps(config)+'\n')
            self.auditing=False
            self.audited=set()
            self.http_address=None
            super().__init__(label,daemon,manifest,home,network,destination,timeout)
        def raw(self, command, **fields):
            return super().request(command,**fields)
        def await_ready(self):
            super().await_ready()
            address=self.ready.get('chronik_address')
            require(isinstance(address,str) and address.startswith('127.0.0.1:'),'native Chronik numeric loopback address required')
            port=int(address.split(':')[1])
            require(0<port<=65535 and port not in local.FORBIDDEN_PORTS,'forbidden Chronik port')
            self.http_address='http://'+address
            record('listener',node=self.label,address=address,pid=self.process.pid)
            self.audit(force=True)
        def http(self, path, body=None, expected=200):
            end=time.monotonic()+self.timeout
            while True:
                request=urllib.request.Request(self.http_address+path,
                    data=None if body is None else json.dumps(body).encode(),
                    headers={'Content-Type':'application/json'}, method='GET' if body is None else 'POST')
                try:
                    with urllib.request.urlopen(request,timeout=min(2,max(.01,end-time.monotonic()))) as response:
                        code=response.status; raw=response.read(262145)
                except urllib.error.HTTPError as error:
                    code=error.code; raw=error.read(262145)
                require(len(raw)<=262144,'HTTP response exceeds API capacity')
                value=json.loads(raw)
                evidence['requests'].append(dict(node=self.label,path=path,request=body,status=code,response=value))
                if code==503:
                    require(time.monotonic()<end,'Chronik remained unavailable beyond deadline')
                    time.sleep(.025);continue
                if code==409 and expected==200 and value.get('error')=='stale_cursor':raise SnapshotChanged()
                if code!=expected and self.auditing and hasattr(self,'audit_tip') and self.raw('status').get('tip')!=self.audit_tip:raise SnapshotChanged()
                require(code==expected,'unexpected HTTP status '+str((code,expected,path,value)))
                return value
        def pages(self, route, query):
            results=[]; cursor=None; seen=set(); snapshot=None
            for _ in range(256):
                page=self.http(route,dict(query,page_size=1,cursor=cursor))
                if page['snapshot']['tip']!=self.audit_tip:raise SnapshotChanged()
                require(page['version']==2 and page['confirmed_only'] is True,'confirmed API identity')
                if snapshot is not None and snapshot!=page['snapshot']:raise SnapshotChanged()
                snapshot=page['snapshot']
                require(len(page['outputs'])<=1,'page_size ignored')
                for item in page['outputs']:
                    row=item['record']; key=(row['txid'],row['out_idx'])
                    require(key not in seen,'pagination duplicated an outpoint')
                    seen.add(key); results.append(item)
                cursor=page['cursor']
                if cursor is None:return results,snapshot
                require(isinstance(cursor,str) and len(cursor)==348,'cursor transport shape')
            raise AssertionError('pagination exceeded bounded local corpus')
        def audit(self, force=False):
            if self.auditing or self.http_address is None:return
            self.auditing=True
            end=time.monotonic()+self.timeout
            try:
                while True:
                    try:return self.audit_once(force)
                    except SnapshotChanged:
                        require(time.monotonic()<end,'HTTP snapshots kept changing beyond audit deadline')
            finally:self.auditing=False
        def audit_once(self, force=False):
            try:
                end=time.monotonic()+self.timeout
                while True:
                    native=self.raw('status')
                    current=self.http('/v2/status')
                    if current['ready'] and current['snapshot']['tip']==native.get('tip'):break
                    require(time.monotonic()<end,'HTTP/native authoritative tip did not converge')
                    time.sleep(.025)
                snapshot=current['snapshot']; tip=snapshot['tip']; self.audit_tip=tip
                require(current['version']==2 and current['confirmed_only'] and current['pool_indexed'] is False,'HTTP status scope mismatch')
                require(snapshot['chain_id']==native['chain_id'] and snapshot['profile_id']==native['profile_digest'] and snapshot['height']==str(native['height']),'HTTP/native profile or height mismatch')
                roots=sorted({json.loads(path.read_text())['policy']['root'] for path in output.glob('payment-artifact-*.json')})
                key=(tip,tuple(roots))
                if not roots or (key in self.audited and not force):return
                query=dict(any_branch=roots)
                history,_=self.pages('/v2/branches/outputs',query)
                utxos,_=self.pages('/v2/branches/utxos',query)
                hist={ (v['record']['txid'],v['record']['out_idx']):v for v in history }
                unspent={ (v['record']['txid'],v['record']['out_idx']):v for v in utxos }
                require(len(hist)==len(history) and len(unspent)==len(utxos),'duplicate matching output')
                require(set(unspent)=={k for k,v in hist.items() if v['record']['spend'] is None},'UTXO set differs from unspent history')
                for point,item in hist.items():
                    row=item['record']
                    require(isinstance(row['value'],str) and row['value'].isdigit() and str(int(row['value']))==row['value'] and 0<=int(row['value'])<2**64,'uint64 value must be canonical decimal string')
                    require(isinstance(row['creation']['height'],str),'creation height must be string')
                    require(row['branches'] and set(row['branches'])<=set(roots),'unexpected Payment policy roots')
                    require(item['matching_positions']==[0],'single Payment root must match position zero exactly')
                    native_coin=self.raw('coin',txid=point[0],index=point[1])
                    if native_coin.get('tip')!=tip:raise SnapshotChanged()
                    require((native_coin['coin'] is not None)==(point in unspent),'HTTP/native UTXO presence differs')
                    if point in unspent:
                        direct=self.http('/v2/utxos/'+point[0]+'/'+str(point[1]))
                        if direct['snapshot']!=snapshot:raise SnapshotChanged()
                        require(direct['record']==row,'direct UTXO lookup differs from branch query')
                    else:
                        self.http('/v2/utxos/'+point[0]+'/'+str(point[1]),expected=404)
                    if point[0] in known_coinbases:
                        cb=known_coinbases[point[0]]
                        require(point[1]==0 and row['value']==cb['coinbase_value'] and row['creation']['block_id']==cb['block_id'],'coinbase history does not match native mining result')
                    observed.setdefault(point,[]).append(dict(node=self.label,tip=tip,present=point in unspent,spend=row['spend']))
                # OR union and same-output AND: each Payment has exactly one
                # branch, so A(position0) AND B(anywhere) must never match.
                if len(roots)==2:
                    singles=[]
                    for root in roots:
                        matches,_=self.pages('/v2/branches/utxos',dict(any_branch=[root]))
                        singles.append({(i['record']['txid'],i['record']['out_idx']) for i in matches})
                        positional,_=self.pages('/v2/branches/utxos',dict(positions=[dict(position=0,roots=[root])]))
                        require(singles[-1]=={(i['record']['txid'],i['record']['out_idx']) for i in positional},'position-zero root set mismatch')
                    require(set(unspent)==singles[0]|singles[1] and not singles[0]&singles[1],'OR branch union/dedup mismatch')
                    mixed,_=self.pages('/v2/branches/utxos',dict(any_branch=[roots[0]],positions=[dict(position=0,roots=[roots[1]])]))
                    require(not mixed,'AND matched roots on different outputs')
                    missing,_=self.pages('/v2/branches/utxos',dict(positions=[dict(position=1,roots=roots)]))
                    require(not missing,'single-root Payment matched nonexistent position one')
                # Persist a real history continuation and reject it after a tip
                # transition. A restart at the same tip retains its validity.
                page=self.http('/v2/branches/outputs',dict(query,page_size=1))
                old=cursors.get(str(self.command[3]))
                if old and old['roots']==roots:
                    if old['tip']!=tip:
                        self.http('/v2/branches/outputs',dict(query,page_size=1,cursor=old['cursor']),expected=409)
                        record('stale-cursor-rejected',node=self.label,old_tip=old['tip'],tip=tip)
                    elif old['label']!=self.label:
                        self.http('/v2/branches/outputs',dict(query,page_size=1,cursor=old['cursor']))
                        record('restart-cursor-persisted',node=self.label,tip=tip)
                if page['cursor']:cursors[str(self.command[3])]=dict(tip=tip,roots=roots,cursor=page['cursor'],label=self.label)
                final=self.http('/v2/status')
                if not final['ready'] or final['snapshot']!=snapshot:raise SnapshotChanged()
                self.audited.add(key)
                record('native-http-snapshot',node=self.label,snapshot=snapshot,history=history,utxos=utxos)
            finally:pass
        def request(self, command, wait_timeout=None, **fields):
            response=super().request(command,wait_timeout=wait_timeout,**fields)
            if command=='minepool' and response.get('found'):
                known_coinbases[response['coinbase_txid']]=response
            if command=='submittransaction' and response.get('ok'):
                submitted[response['txid']]=dict(wire=fields['wire'],txhash=response['txhash'])
            if command=='status' and response.get('tip_known') and response.get('mempool_ready'):
                self.audit()
            if command=='stop':save()
            return response
        def stop(self):
            try:
                if self.process.poll() is None:self.audit(force=True)
            finally:
                super().stop()
    local.Node=Node
    private.local_module=lambda:local
    try:
        private.main(argv)
        driver=json.loads((output/'evidence.json').read_text())
        require(driver['passed'],'native wallet driver did not pass')
        snapshots=[c for c in evidence['checks'] if c['check']=='native-http-snapshot']
        require(any(c['check']=='restart-cursor-persisted' for c in evidence['checks']),'no persisted index/cursor restart demonstrated')
        require(any(c['check']=='stale-cursor-rejected' for c in evidence['checks']),'no stale cursor rejection demonstrated')
        # Require actual detach/remine and spend-history restoration for the
        # payment selected by the independent native wallet driver.
        detached=[c for c in driver['checks'] if c['check']=='detached-payment' and c['response']['state']=='pending']
        require(len(detached)==1,'driver did not demonstrate valid detached pending payment')
        payment=detached[0]['response']['txid']
        presence=[]
        for snap in snapshots:
            history={(x['record']['txid'],x['record']['out_idx']) for x in snap['history']}
            presence.append((int(snap['snapshot']['height']), (payment,0) in history))
        require(any(h==5 and present for h,present in presence) and any(h==7 and not present for h,present in presence) and any(h==8 and present for h,present in presence),'HTTP history did not remove then restore re-mined payment')
        require(any(any(v['spend'] is not None for v in entries) and any(v['spend'] is None for v in entries) for entries in observed.values()),'confirmed spent history never reverted to unspent')
        expected_payments={}
        for check in driver['checks']:
            if check['check']=='wallet-pay':
                pay=check['response']; recipient=check['request']['recipient']
                funding=[cb for txid,cb in known_coinbases.items() if txid in pay['wire']]
                require(len(funding)==1,'signed payment must resolve exactly one native funding outpoint')
                expected_payments[pay['txid']]=dict(txhash=pay['txhash'],recipient=recipient,change=int(funding[0]['coinbase_value'])-int(recipient['value'])-int(check['request']['fee']))
        for snap in snapshots:
            for item in snap['history']:
                row=item['record']; wanted=expected_payments.get(row['txid'])
                if wanted:
                    require(row['creation']['txhash']==wanted['txhash'],'HTTP payment TxHash differs from native wallet')
                    if row['out_idx']==0:
                        require(row['value']==wanted['recipient']['value'] and row['branches']==wanted['recipient']['branches'] and row['paths']==wanted['recipient']['paths'],'HTTP recipient Payment output differs from native wallet request')
                    else:
                        require(row['out_idx']==1 and row['value']==str(wanted['change']),'HTTP sender change amount differs from funding minus amount and fee')
        record('wallet-payment-output-values',payments=expected_payments)
        evidence['native_evidence_sha256']=local.digest(output/'evidence.json')
        evidence['passed']=True;save()
    except Exception as error:
        evidence['failure']=dict(kind=type(error).__name__,error=str(error));save();raise
    print('Native Chronik HTTP lifecycle passed:',output)


if __name__=='__main__':main()
