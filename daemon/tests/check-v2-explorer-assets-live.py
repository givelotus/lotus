#!/usr/bin/env python3
"""Native-accepted testscript assets -> real explorer HTTP -> competing-fork undo.

This is an explicitly public native TRUE/MINT testscript fixture, not compiler
contract or wallet acceptance. Transaction bytes enter submittransaction and are
selected only by minepool. No index insertion or manual transaction block occurs.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

PREFIX = '/v2/explorer/v1'


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    for key in ('daemon', 'manifest', 'output'):
        p.add_argument('--'+key, type=Path, required=True)
    p.add_argument('--daemon-source', required=True)
    p.add_argument('--expected-daemon-sha256', required=True)
    p.add_argument('--timeout', type=float, default=30)
    args = p.parse_args(argv)
    repo = Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location('asset_live_nodes', Path(__file__).with_name('check-v2-local-nodes.py'))
    local = importlib.util.module_from_spec(spec); spec.loader.exec_module(local)
    require = local.require
    require(re.fullmatch('[0-9a-f]{40}', args.daemon_source), 'full daemon source required')
    require(re.fullmatch('[0-9a-f]{64}', args.expected_daemon_sha256), 'full daemon SHA256 required')
    require(1 <= args.timeout <= 60, 'timeout outside 1..60 seconds')
    daemon = args.daemon.resolve(); manifest_path = args.manifest.resolve()
    require(local.digest(daemon) == args.expected_daemon_sha256, 'binary differs from supplied SHA256')
    manifest = json.loads(manifest_path.read_text())
    require(manifest['schema'] == 2 and 2 <= manifest['coinbase_maturity'] <= 16, 'current absolute profile and bounded maturity required')
    sys.path.insert(0, str(repo/'tools/lotus-v2-reference'))
    from lotus_v2_reference.encoding import Output, Profile, encode_output
    from lotus_v2_reference.signing import Input, Witness, Transaction, TxProfile, encode_transaction, identity_digests
    from lotus_v2_reference.vm import branch_leaf_hash
    from lotus_v2_reference.block_wire import decode_block_wire
    from lotus_v2_reference.block_seal import block_id
    output_profile = Profile(16, 16, 812, 8192)
    tx_profile = TxProfile(*manifest['transaction_limits'])
    chain = bytes.fromhex(manifest['header']['chain_id'])
    true_script, mint_script = bytes.fromhex('4e'), bytes.fromhex('794e')
    root_hash, token = branch_leaf_hash(true_script), branch_leaf_hash(mint_script)
    token_hex = token.hex()
    root = args.output.resolve(); root.mkdir()  # Existing homes are never reused.
    (root/'manifest.json').write_bytes(manifest_path.read_bytes())
    record = dict(schema='lotus-v2/explorer-assets-live/1', passed=False,
        scope='native testscript mint/transfer/explicit and implicit burns; real pool mining and competing-fork canonical undo',
        compiler_contract_acceptance=False, signer='none: public native TRUE 4e / MINT 794e testscript witnesses',
        daemon_source=args.daemon_source, daemon_sha256=local.digest(daemon),
        manifest_sha256=local.digest(manifest_path), harness_sha256=local.digest(Path(__file__)),
        transport_sha256=local.digest(Path(local.__file__)),
        reference_sha256={name: local.digest(repo/'tools/lotus-v2-reference/lotus_v2_reference'/name)
            for name in ('encoding.py','signing.py','vm.py','block_wire.py','block_seal.py')},
        token_id=token_hex, processes=[], checks=[], http=[], transactions=[])
    nodes = []; deadline = time.monotonic()+300
    class Node(local.Node):
        def request(self, command, wait_timeout=None, **fields):
            started=time.monotonic_ns()
            answer=super().request(command,wait_timeout=wait_timeout,**fields)
            record.setdefault('native_requests',[]).append(dict(started_ns=started,finished_ns=time.monotonic_ns(),node=self.label,command=command,fields=fields,response=answer))
            return answer
    def save(): (root/'evidence.json').write_text(json.dumps(record, indent=2)+'\n')
    def check(name, **facts): record['checks'].append(dict(check=name, **facts)); save()
    def eventually(fn, predicate, why):
        end = min(deadline, time.monotonic()+args.timeout); value = None
        while time.monotonic() < end:
            value = fn()
            if predicate(value): return value
            time.sleep(.025)
        raise AssertionError(why+': '+str(value))
    def status(node):
        return eventually(lambda: node.request('status'), lambda s: s.get('tip_known') and s.get('mempool_ready')
            and not any(s.get(k) for k in ('pending_journal','pending_receipt','pending_propagation','execution_paused','reopen_required')),
            'native state not quiescent')
    def launch(label, home, peers=()):
        require(local.digest(daemon) == record['daemon_sha256'], 'binary changed before launch')
        path = root/(label+'.network.json')
        path.write_text(json.dumps(dict(schema=1, magic='76326173', listen=dict(address='127.0.0.1',port=0),
            connect=list(peers), receive_limit=max(1048576,manifest['block_read_limit']),
            local_policy='bounded-local-v1', chronik_bind='127.0.0.1:0'))+'\n')
        node = Node(label,daemon,root/'manifest.json',home,path,root,args.timeout)
        nodes.append(node); node.await_ready()
        port = int(node.ready['chronik_address'].split(':')[1])
        require(0 < port <= 65535 and port not in local.FORBIDDEN_PORTS, 'forbidden Chronik port')
        record['processes'].append(dict(label=label,pid=node.process.pid,command=node.command,ready=node.ready)); save()
        status(node); return node
    def http(node, route, params=None, expected=200):
        query = '' if not params else '?'+urllib.parse.urlencode(params)
        url = 'http://'+node.ready['chronik_address']+PREFIX+route+query
        end = min(deadline,time.monotonic()+args.timeout)
        while True:
            try:
                with urllib.request.urlopen(url,timeout=min(args.timeout,5)) as response:
                    code = response.status; raw = response.read(262145)
                    require(response.headers.get('Cache-Control') == 'no-store','missing no-store')
            except urllib.error.HTTPError as error:
                code=error.code; raw=error.read(262145)
            require(len(raw)<=262144,'unbounded HTTP response')
            answer=json.loads(raw)
            record['http'].append(dict(monotonic_ns=time.monotonic_ns(),node=node.label,route=route,query=params,status=code,response=answer)); save()
            if code == 503:
                require(time.monotonic()<end,'explorer remained unavailable'); time.sleep(.025); continue
            require(code==expected,'unexpected HTTP response '+str((route,code,answer)))
            require(answer['api_version']=='1','wrong explorer version')
            return answer
    def ready(node):
        native=status(node)
        value=eventually(lambda:http(node,'/status'),lambda s:s['ready'] and s['indexed_anchor']['block_id']==native['tip'], 'explorer did not catch up')
        require(value['coverage']['complete'] and value['coverage']['from_height']=='0','incomplete historical coverage')
        require(value['capabilities']['assets'] and value['capabilities']['asset_events'],'asset capability missing')
        return native
    def pages(node,route,token_snapshot,extra=None):
        items=[]; cursor=None; seen=set()
        for _ in range(64):
            params=dict(snapshot_token=token_snapshot,page_size='1',**(extra or {}))
            if cursor is not None: params['cursor']=cursor
            response=http(node,route,params); page=response['data']
            require(response['snapshot_token']==token_snapshot,'page snapshot changed')
            require(len(page['items'])<=1,'page cap ignored'); items.extend(page['items'])
            nxt=page['next_cursor']
            if page['exhausted']:
                require(nxt is None,'exhausted page has cursor'); return items
            require(isinstance(nxt,str) and nxt not in seen,'nonadvancing page cursor'); seen.add(nxt); cursor=nxt
        raise AssertionError('fixture pagination limit exceeded')
    def native_output(value, burn=False): return Output(2 if burn else 0,value,None,(root_hash,),() if burn else ((0,),))
    def token_output(value,burn=False): return Output(3 if burn else 1,value,token,(root_hash,),() if burn else ((0,),))
    destination=encode_output(native_output(0),output_profile).hex()
    def fetch(node,identity):
        offset=0; result=bytearray(); total=None
        while total is None or offset<total:
            answer=node.request('readblock',block_id=identity,offset=offset,length=32768)
            require(answer.get('ok') and answer['offset']==offset,'native body unavailable')
            total=answer['total_bytes']; part=bytes.fromhex(answer['data']);require(part and len(part)<=32768,'invalid native body chunk')
            result.extend(part);offset+=len(part);require(offset<=total<=manifest['block_read_limit'],'native body size mismatch')
        wire=bytes(result); (root/(identity+'.block')).write_bytes(wire)
        block=decode_block_wire(wire,tx_profile,chain)
        require(block_id(chain,block.header).hex()==identity,'independent native header identity mismatch')
        return block
    def mine(node, selected=None, branch=0):
        before=status(node)
        answer=node.request('minepool',expected_parent=before['tip'],time=manifest['header']['time']+(before['height']+1)*manifest['header']['spacing']+branch,
            max_claim='100000',coinbase_output=destination,coinbase_data=None,start_nonce='0',max_attempts=256)
        require(answer.get('found') and answer.get('accepted') is False and answer.get('pending_validation') is True,'mining bypassed normal validation '+str(answer))
        if selected is not None: require(answer['pool_selected']==selected,'wrong pool selection '+str(answer))
        after=eventually(lambda:status(node),lambda s:s['tip']==answer['block_id'],'native candidate not connected')
        block=fetch(node,answer['block_id']); locations={}
        for i,tx in enumerate(block.transactions):
            ids=identity_digests(tx,tx_profile,chain)
            locations[ids.txid.hex()]=dict(block_id=answer['block_id'],height=str(after['height']),tx_index=str(i),txid=ids.txid.hex(),txhash=ids.txhash.hex())
        check('native-pool-block-connected',node=node.label,response=answer,status=after,locations=locations,
              body_sha256=local.digest(root/(answer['block_id']+'.block')))
        ready(node); return answer, locations
    txs=[]
    def make(name, inputs, outputs, event):
        tx=Transaction(0,tuple(inputs),tuple(outputs)); wire=encode_transaction(tx,tx_profile); ids=identity_digests(tx,tx_profile,chain)
        value=dict(name=name,wire=wire.hex(),txid=ids.txid.hex(),txhash=ids.txhash.hex(),event=event,outputs=outputs,model=tx)
        (root/(name+'.tx')).write_bytes(wire)
        record['transactions'].append({k:v for k,v in value.items() if k not in ('outputs','model')});save();txs.append(value);return value
    def spend(txid,index): return Input(bytes.fromhex(txid),index,0xffffffff,1,witnesses=(Witness(true_script),))
    def submit(node,tx):
        answer=node.request('submittransaction',wire=tx['wire'],expected_tip=status(node)['tip'])
        require(answer.get('ok') and answer.get('result') in ('accepted','duplicate'),'native pool rejected testscript '+str(answer))
        require(answer['txid']==tx['txid'] and answer['txhash']==tx['txhash'],'reference/native transaction identities differ')
        check('native-token-pool-accepted',node=node.label,transaction_name=tx['name'],response=answer)
    def audit(node, active, locations, phase):
        ready(node); detail=http(node,'/assets/'+token_hex); snap=detail['snapshot_token']; summary=detail['data']
        require(summary['token_id']==token_hex and summary['first_seen']==locations[active[0]['txid']],'wrong first occurrence')
        count=sum(1 for tx in active for out in tx['outputs'] if out.flags&1)
        require(summary['event_count']==str(len(active)) and summary['output_count']==str(count),'wrong asset counters')
        require(summary['metadata']==dict(availability='unknown',name=None,symbol=None,decimals=None,issuer=None,mint_cap=None)
            and summary['supply']==dict(availability='unknown'),'fabricated metadata/supply')
        registry=pages(node,'/assets',snap); require(registry==[summary],'registry excludes burned token or includes native currency')
        events=pages(node,'/assets/'+token_hex+'/events',snap)
        expected=[dict(token_id=token_hex,location=locations[tx['txid']],**tx['event']) for tx in active]
        require(events==expected,'asset event arithmetic/order/location mismatch '+str((events,expected)))
        history=pages(node,'/assets/'+token_hex+'/outputs',snap,dict(view='history'))
        unspent=pages(node,'/assets/'+token_hex+'/outputs',snap,dict(view='unspent'))
        wanted=[]; spent={}
        for tx in active:
            for ordinal,inp in enumerate(tx['model'].inputs):
                if inp.flags==1: spent[(inp.prev_txid.hex(),str(inp.prev_index))]=dict(transaction=locations[tx['txid']],input_index=str(ordinal))
            for i,out in enumerate(tx['outputs']):
                if out.flags&1: wanted.append((tx,i,out))
        require(len(history)==len(wanted),'missing zero/burn/history outputs')
        for row,(tx,index,out) in zip(history,wanted):
            key=(tx['txid'],str(index)); want_spend=spent.get(key)
            require(row['txid']==key[0] and row['out_idx']==key[1] and row['creation']==locations[tx['txid']]
                and row['value']==str(out.value) and row['flags']==str(out.flags) and row['token_id']==token_hex
                and row['has_token'] and row['is_burn']==bool(out.flags&2) and row['branches']==[root_hash.hex()]
                and row['paths']==[[str(pos) for pos in path] for path in out.paths] and row['spend']==want_spend,'output differs from accepted native facts '+str(row))
            direct=http(node,'/outputs/'+key[0]+'/'+key[1],dict(snapshot_token=snap))
            require(direct['data']==row,'direct historical output differs')
        require(unspent==[row for row in history if row['spend'] is None and not row['is_burn']],'unspent view includes burn/spent or drops live output')
        # Finish the complete pinned HTTP observation before issuing native
        # control commands; compare coins only while its canonical tip persists.
        require(http(node,'/assets/'+token_hex,dict(snapshot_token=snap))['data']==summary,'pinned summary changed')
        for row in history:
            coin=node.request('coin',txid=row['txid'],index=int(row['out_idx']))
            require(coin['tip']==detail['snapshot']['tip'],'native coin observation moved beyond pinned snapshot')
            require((coin['coin'] is not None)==(row['spend'] is None and not row['is_burn']),'native coin and explorer spendability disagree')
        check('asset-explorer-parity',phase=phase,node=node.label,snapshot=detail['snapshot'],summary=summary,events=events,history=history,unspent=unspent)
    def event(i,o,b,m,implicit,has=False): return dict(spent_units=str(i),output_units=str(o),explicit_burn_units=str(b),minted_units=str(m),implicit_burn_units=str(implicit),has_mint_input=has)
    try:
        a=launch('a',root/'home-a')
        ready(a)
        # No native command or transaction is issued between these HTTP-only
        # samples. Record idle publication churn explicitly before pinned reads.
        idle=[]; probe_started=time.monotonic_ns(); probe_http_start=len(record['http'])
        for _ in range(10):
            sample=eventually(lambda:http(a,'/status'),lambda s:s['ready'],'idle status never became ready');idle.append(dict(monotonic_ns=time.monotonic_ns(),tip=sample['indexed_anchor'],epoch=sample['service_epoch'],generation=sample['generation'],ready=sample['ready']))
            time.sleep(.025)
        check('idle-http-only-authority-stability',samples=idle,http_attempts=len(record['http'])-probe_http_start,elapsed_ns=time.monotonic_ns()-probe_started,total_deadline_seconds=300)
        require(all(s['ready'] for s in idle) and len({(s['epoch'],s['generation'],s['tip']['block_id'],s['tip']['height']) for s in idle})==1,
            'idle authority publications prevent stable pinned reads; inspect idle HTTP-only trace')
        funding,_=mine(a,0)
        for _ in range(manifest['coinbase_maturity']-1): mine(a,0)
        common=status(a); a.stop(); shutil.copytree(root/'home-a',root/'fork-home'); a=launch('a-assets',root/'home-a')
        amount=int(funding['coinbase_value']); require(amount>30000,'fixture funding insufficient')
        mint=make('mint',[spend(funding['coinbase_txid'],0),Input(token,0,0xffffffff,3,witnesses=(Witness(mint_script),))],
            [native_output(amount-10000),token_output(1000),token_output(0,True)],event(0,1000,0,1000,0,True))
        submit(a,mint); _,locations=mine(a,1); active=[mint];audit(a,active,locations,'mint-zero-burn')
        transfer=make('transfer',[spend(mint['txid'],0),spend(mint['txid'],1)],
            [native_output(amount-20000),token_output(600),token_output(250,True)],event(1000,850,250,0,150))
        submit(a,transfer); _,more=mine(a,1);locations.update(more);active.append(transfer);audit(a,active,locations,'transfer-explicit-and-implicit-burn')
        burn=make('input-only-burn',[spend(transfer['txid'],0),spend(transfer['txid'],1)],
            [native_output(amount-30000)],event(600,0,0,0,600))
        submit(a,burn); _,more=mine(a,1);locations.update(more);active.append(burn);audit(a,active,locations,'input-only-total-implicit-burn')
        original=status(a); a.stop()
        b=launch('b-fork',root/'fork-home')
        while status(b)['height']<=original['height']: mine(b,0,branch=1)
        fork=status(b);a=launch('a-reorg',root/'home-a',[b.ready['listen']])
        eventually(lambda:status(a),lambda s:all(s[k]==fork[k] for k in local.STATE_FIELDS),'longer fork did not become canonical')
        ready(a); absent=http(a,'/assets/'+token_hex,expected=404)
        listing=http(a,'/assets');require(listing['data']['items']==[] and listing['data']['exhausted'],'registry survived full asset undo')
        for tx in active:
            http(a,'/transactions/by-id/'+tx['txid'],expected=404)
        detached_outputs=[]
        for tx in active:
            for index,out in enumerate(tx['outputs']):
                if not out.flags&1: continue
                missing_output=http(a,'/outputs/'+tx['txid']+'/'+str(index),dict(snapshot_token=listing['snapshot_token']),expected=404)
                native_coin=a.request('coin',txid=tx['txid'],index=index)
                require(native_coin['tip']==fork['tip'] and native_coin['coin'] is None,'detached token output retained a native coin')
                detached_outputs.append(dict(txid=tx['txid'],out_idx=str(index),http=missing_output,native=native_coin))
        require(len(detached_outputs)==4,'all former asset outpoints must be checked')
        restored=a.request('coin',txid=funding['coinbase_txid'],index=0);require(restored['coin'] is not None,'reorg did not restore real funding coin')
        detached=a.request('blockstatus',block_id=original['tip']);require(detached['ever_connected'] and not detached['is_active_tip'],'native detach evidence missing')
        check('native-competing-fork-asset-undo',common=common,old_tip=original,fork=fork,absent=absent,listing=listing,restored_funding=restored,detached=detached,detached_outputs=detached_outputs)
        # Re-submit exact accepted bytes in dependency order. A pool may retain
        # detached valid transactions; duplicate is explicitly accepted above.
        for tx in active: submit(a,tx)
        _,remine=mine(a,3); audit(a,active,remine,'original-wire-remined-after-undo')
        require(remine[mint['txid']]['block_id']!=locations[mint['txid']]['block_id'],'re-mining reused detached location')
        before_restart=record['checks'][-1]['snapshot']
        a.stop(); b.stop(); a=launch('a-remine-restart',root/'home-a')
        audit(a,active,remine,'remined-locations-persist-after-restart')
        after_restart=record['checks'][-1]['snapshot']
        require(before_restart['tip']==after_restart['tip'] and before_restart['service_epoch']!=after_restart['service_epoch'],
            'same-home restart did not preserve tip or renew service epoch')
        check('same-home-restart-preserves-remined-asset-locations',before=before_restart,after=after_restart,locations=remine)

        record['passed']=True; save()
    except Exception as error:
        record['failure']=dict(type=type(error).__name__,message=str(error));save();raise
    finally:
        for node in reversed(nodes):
            if node.process.poll() is None: node.stop()
        record['cleanup']=dict(all_stopped=all(node.process.poll() is not None for node in nodes),processes=[dict(label=node.label,pid=node.process.pid,returncode=node.process.returncode) for node in nodes])
        save()
    print('Native explorer asset lifecycle passed:',root)


if __name__=='__main__': main()
