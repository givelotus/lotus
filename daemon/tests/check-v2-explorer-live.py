#!/usr/bin/env python3
"""Actual native explorer API and DOM acceptance over the unchanged wallet driver.

No payment frames are manually inserted into blocks. The existing controller
prepares/signs/pays via its private FD relay; native minepool, peer validation,
persisted restart and competing-chain reorg supply every indexed observation.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

PREFIX = '/v2/explorer/v1'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Changed(Exception):
    def __init__(self, reason='observation changed', context=None):
        super().__init__(reason);self.context=context


# Runs the actual built app and its live fetch adapter against the real proxy.
# Happy DOM is a DOM execution gate, explicitly not a manual browser check.
DOM_SCRIPT = r"""
import {readFile} from 'node:fs/promises';
import {pathToFileURL} from 'node:url';
const packagePath=process.argv[1],base=process.argv[2],plan=JSON.parse(process.argv[3]);
const {Window}=await import(pathToFileURL(packagePath+'/node_modules/happy-dom/lib/index.js'));
const win=new Window({url:base+'/?api='+encodeURIComponent(base)});
win.document.write(await readFile(packagePath+'/index.html','utf8'));
for(const k of ['window','document','location','sessionStorage'])globalThis[k]=k==='window'?win:win[k];
const fetchReal=globalThis.fetch;const requests=[];
globalThis.fetch=async(...args)=>{requests.push(String(args[0]));return fetchReal(...args);};
await import(pathToFileURL(packagePath+'/dist/app.js'));
async function ready(){const end=Date.now()+15000;while(Date.now()<end){const n=win.document.querySelector('#notice').textContent;if(n.startsWith('Observation loaded.'))return;if(n.startsWith('Invalid or unavailable')||n.startsWith('Absent')||n.startsWith('Index unavailable'))throw new Error(n);await new Promise(r=>setTimeout(r,20));}throw new Error('DOM screen deadline');}
await ready();const screens=[];
async function screen(route,expected){win.document.querySelector('#notice').textContent='';win.location.hash=route;win.dispatchEvent(new win.HashChangeEvent('hashchange'));await ready();const content=win.document.querySelector('#results').textContent;if(expected&&!content.includes(expected))throw new Error('Expected native fact missing from DOM: '+expected);screens.push({route,text:content});}
await screen('/blocks',plan.block_id);await screen('/blocks/'+plan.block_id,plan.txid);
await screen('/transactions/by-id/'+plan.txid,plan.txhash);
const witness=[...win.document.querySelectorAll('#results button')].find(b=>b.textContent.startsWith('Witnesses:'));
async function contains(text){const end=Date.now()+15000;while(Date.now()<end){if(win.document.querySelector('#results').textContent.includes(text))return;const n=win.document.querySelector('#notice').textContent;if(n.includes('unavailable')||n.includes('Snapshot changed'))throw new Error(n);await new Promise(r=>setTimeout(r,20));}throw new Error('DOM detail deadline: '+text);}
if(witness){witness.click();await contains('Public witnesses');}
const wire=[...win.document.querySelectorAll('#results button')].find(b=>b.textContent==='Inspect exact transaction wire');wire.click();await contains(plan.wire_prefix);
await screen('/transactions/by-hash/'+plan.txhash,plan.txid);await screen('/outputs/'+plan.txid+'/0',plan.output_value);await screen('/assets');
async function search(kind,value,expected,missing=false){win.document.querySelector('#notice').textContent='';win.document.querySelector('#kind').value=kind;win.document.querySelector('#query').value=value;win.document.querySelector('#search').dispatchEvent(new win.Event('submit',{cancelable:true}));if(missing){const end=Date.now()+15000;while(Date.now()<end&&!win.document.querySelector('#notice').textContent.startsWith('Absent'))await new Promise(r=>setTimeout(r,20));if(!win.document.querySelector('#notice').textContent.startsWith('Absent'))throw new Error('Unknown asset search must show covered-history absence');}else{await ready();if(expected&&!win.document.querySelector('#results').textContent.includes(expected))throw new Error('Typed search missing native fact '+kind);}screens.push({search_kind:kind,value,text:win.document.querySelector('#results').textContent,notice:win.document.querySelector('#notice').textContent});}
await search('height',plan.height,plan.block_id);await search('block',plan.block_id,plan.block_id);await search('txid',plan.txid,plan.txhash);await search('txhash',plan.txhash,plan.txid);await search('outpoint',plan.txid+':0',plan.output_value);
await search('asset',plan.assets[0]??'00'.repeat(32),plan.assets[0],plan.assets.length===0);
if(plan.root)await search('branch',plan.root,plan.root);
for(const id of plan.assets)await screen('/assets/'+id,id);
if(plan.root){win.document.querySelector('#notice').textContent='';win.document.querySelector('#roots').value=plan.root;win.document.querySelector('#positions').value=JSON.stringify([{position:'0',roots:[plan.root]}]);win.document.querySelector('#branches').dispatchEvent(new win.Event('submit',{cancelable:true}));await ready();if(!win.document.querySelector('#results').textContent.includes(plan.root))throw new Error('Actual branch root missing from DOM');screens.push({route:'POST /branches/outputs',text:win.document.querySelector('#results').textContent});}
if(!win.document.querySelector('#anchor').textContent.includes(plan.tip))throw new Error('DOM anchor differs from authenticated native tip');
console.log(JSON.stringify({scope:'actual frontend DOM/live fetch, not manual browser evidence',screens,requests}));
await win.happyDOM.abort();
"""


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('reference-package', 'frontend-package'):
        parser.add_argument('--'+name, type=Path, required=True)
    for name in ('reference-source', 'frontend-source', 'expected-daemon-sha256', 'expected-wallet-sha256', 'expected-manifest-sha256'):
        parser.add_argument('--'+name, required=True)
    parser.add_argument('--require-assets', action='store_true', help='Fail explicitly: asset accounting/lifecycle requires the separate asset harness')
    own, driver_args = parser.parse_known_args(argv)
    driver = load('explorer_wallet_discovery_driver', Path(__file__).with_name('check-v2-wallet-discovery-live.py'))
    local = driver.local_module()
    require = local.require
    require('--output' in driver_args, 'fresh --output required by unchanged wallet driver')
    output = Path(driver_args[driver_args.index('--output')+1]).resolve()
    require(not output.exists(), 'existing output must never be reused/reset')
    require('--daemon' in driver_args, 'exact daemon path required')
    daemon = Path(driver_args[driver_args.index('--daemon')+1]).resolve()
    require(local.hex_string(own.expected_daemon_sha256, 32), 'exact binary SHA256 required')
    require(local.digest(daemon) == own.expected_daemon_sha256, 'native binary hash mismatch')
    for pin in (own.reference_source, own.frontend_source):
        require(local.hex_string(pin, 20), 'full immutable source pin required')
    frontend = own.frontend_package.resolve()
    for path in ('dist/app.js', 'dist/client.js', 'server.mjs', 'node_modules/happy-dom/lib/index.js'):
        require((frontend/path).is_file(), 'built frontend/dev dependency missing: '+path)
    require(subprocess.check_output(['git','rev-parse','HEAD'],cwd=frontend,text=True).strip() == own.frontend_source, 'frontend checkout does not match pin')
    reference = own.reference_package.resolve()
    sys.path.insert(0, str(reference))
    from lotus_v2_reference.block_wire import decode_block_wire
    from lotus_v2_reference.block_seal import block_id
    from lotus_v2_reference.signing import TxProfile, encode_transaction, identity_digests
    from lotus_v2_reference.encoding import encode_compact_size
    manifest_path = Path(driver_args[driver_args.index('--manifest')+1]).resolve()
    require(local.digest(manifest_path)==own.expected_manifest_sha256,'manifest hash differs from supplied fixture pin')
    wallet_path=Path(driver_args[driver_args.index('--wallet-client')+1]).resolve()
    require(local.digest(wallet_path)==own.expected_wallet_sha256,'wallet binary hash mismatch')
    require(subprocess.check_output(['git','rev-parse','HEAD'],cwd=reference,text=True).strip()==own.reference_source,'reference checkout differs from pin')
    manifest = json.loads(manifest_path.read_text())
    profile = TxProfile(*manifest['transaction_limits'])
    chain = bytes.fromhex(manifest['header']['chain_id'])
    node_exe = driver_args[driver_args.index('--node')+1] if '--node' in driver_args else 'node'
    evidence = dict(schema='lotus-v2/explorer-live-check/1', passed=False,
        scope='real native wallet/controller, confirmed HTTP, private proxy and actual frontend DOM; no manual browser/public deployment claim',
        harness_sha256=local.digest(Path(__file__)), driver_sha256=local.digest(Path(driver.__file__)),
        daemon_sha256=local.digest(daemon), reference_source=own.reference_source, frontend_source=own.frontend_source,
        frontend_sha256={p:local.digest(frontend/p) for p in ('dist/app.js','dist/client.js','server.mjs','package-lock.json')},
        reference_sha256={str(p.relative_to(reference)):local.digest(p) for p in sorted(reference.glob('lotus_v2_reference/*.py'))},
        wallet_sha256=local.digest(wallet_path),manifest_sha256=local.digest(manifest_path),checks=[], requests=[], asset_fixture='not_yet_observed')
    original = local.Node
    previous = {}
    snapshots = []
    payments = {}
    proxies = []
    lifecycle_failed = False
    def save():
        if output.exists(): (output/'explorer-evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
    def record(name, **fields):
        evidence['checks'].append(dict(check=name, **fields)); save()
    class Node(original):
        def __init__(self, label, daemon_path, manifest_file, home, network, destination, timeout):
            require(local.digest(daemon_path)==own.expected_daemon_sha256, 'daemon changed before launch')
            config=json.loads(network.read_text());config['chronik_bind']='127.0.0.1:0';network.write_text(json.dumps(config)+'\n')
            self.home=str(home.resolve());self.failed=False;self.auditing=False;self.audited=set();self.base=None;self.proxy=None
            super().__init__(label,daemon_path,manifest_file,home,network,destination,timeout)
        def raw(self, command, **fields): return super().request(command, **fields)
        def await_ready(self):
            super().await_ready();address=self.ready.get('chronik_address');require(isinstance(address,str) and address.startswith('127.0.0.1:'),'numeric loopback Chronik required')
            port=int(address.rsplit(':',1)[1]);require(0<port<=65535 and port not in local.FORBIDDEN_PORTS,'forbidden Chronik port')
            self.base='http://'+address
            proxy=subprocess.Popen([node_exe,str(frontend/'server.mjs'),'--port','0','--api',self.base],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            self.proxy=proxy;proxies.append(proxy);lines=queue.Queue()
            def collect():
                for line in proxy.stdout: lines.put(line)
            threading.Thread(target=collect,daemon=True).start()
            line=lines.get(timeout=self.timeout);prefix='Private explorer: ';require(line.startswith(prefix),'proxy did not announce private address')
            self.proxy_base=line[len(prefix):].strip().split('/?')[0].rstrip('/')
            parsed=urllib.parse.urlparse(self.proxy_base);require(parsed.hostname=='127.0.0.1' and parsed.port not in local.FORBIDDEN_PORTS,'proxy must be private ephemeral loopback')
            record('listeners',node=self.label,home=self.home,native=self.base,proxy=self.proxy_base,proxy_pid=proxy.pid)
            self.audit(force=True)
        def http(self, route, token=None, body=None, expected=200, proxy=False, idle_probe=False, budget=None):
            url=(self.proxy_base if proxy else self.base)+PREFIX+route
            if token: url += ('&' if '?' in url else '?')+urllib.parse.urlencode({'snapshot_token':token})
            deadline=time.monotonic()+(self.timeout if budget is None else budget)
            while True:
                request=urllib.request.Request(url,data=None if body is None else json.dumps(body).encode(),headers={'Content-Type':'application/json'},method='GET' if body is None else 'POST')
                try:
                    with urllib.request.urlopen(request,timeout=min(2,max(.01,deadline-time.monotonic()))) as response:
                        code=response.status;raw=response.read(262145);cache=response.headers.get('Cache-Control')
                except urllib.error.HTTPError as error:
                    code=error.code;raw=error.read(262145);cache=error.headers.get('Cache-Control')
                require(len(raw)<=262144,'HTTP encoded response cap exceeded');value=json.loads(raw)
                require(cache=='no-store','HTTP must not cache mutable observations')
                evidence['requests'].append(dict(monotonic=time.monotonic(),node=self.label,route=route,token=token,body=body,proxy=proxy,status=code,response=value))
                require(len(evidence['requests'])<=20000,'acceptance request budget exceeded')
                if code==503:
                    require(time.monotonic()<deadline,'explorer stayed unavailable');time.sleep(.025);continue
                if code==409 and expected!=409:
                    current=value.get('snapshot') or {}
                    if idle_probe:raise AssertionError('idle probe token invalidated without native control commands: '+str(current))
                    raise Changed('HTTP pinned request changed',dict(route=route,status=code,error=value))
                if code!=expected and self.auditing and not idle_probe and self.raw('status').get('tip')!=getattr(self,'audit_tip',None):raise Changed()
                require(code==expected,'unexpected HTTP result '+str((route,code,value)))
                require(value.get('api_version')=='1','wrong explorer API version')
                return value
        def pinned(self, route, envelope, body=None):
            value=self.http(route,envelope['snapshot_token'],body)
            if value['snapshot']!=envelope['snapshot'] or value['snapshot_token']!=envelope['snapshot_token']:raise Changed()
            return value['data']
        def pages(self, route, envelope, body=None):
            items=[];cursor=None;seen=set()
            for _ in range(256):
                if body is None:
                    url=route+('&' if '?' in route else '?')+urllib.parse.urlencode(dict(page_size='1',**({} if cursor is None else dict(cursor=cursor))))
                    data=self.pinned(url,envelope)
                else: data=self.pinned(route,envelope,dict(body,page_size='1',**({} if cursor is None else dict(cursor=cursor))))
                require(len(data['items'])<=1,'page size ignored');items.extend(data['items']);cursor=data['next_cursor']
                require(data['exhausted']==(cursor is None),'invalid exhaustion')
                if cursor is None:return items
                require(cursor not in seen,'nonadvancing page continuation');seen.add(cursor)
            raise AssertionError('local corpus exceeded page budget')
        def body_bytes(self, identity):
            if identity==self.ready['genesis_id']:return bytes.fromhex(manifest['genesis'])
            result=bytearray();total=None
            while total is None or len(result)<total:
                value=self.raw('readblock',block_id=identity,offset=len(result),length=97)
                require(value.get('ok') is True and value['block_id']==identity and value['offset']==len(result),'native block read identity/range')
                require(type(value['total_bytes']) is int and value['total_bytes']<=manifest['block_read_limit'],'native body bound')
                require(total is None or total==value['total_bytes'],'native body total changed');total=value['total_bytes'];chunk=bytes.fromhex(value['data']);require(0<len(chunk)<=97,'native chunk did not advance');result.extend(chunk)
            require(len(result)==total,'native body length mismatch');path=output/(identity+'.native.block')
            if path.exists():require(path.read_bytes()==result,'retained native body changed')
            else:path.write_bytes(result)
            return bytes(result)
        def wire(self, txid, envelope):
            raw=bytearray();offset='0';total=None
            for _ in range(2048):
                data=self.pinned('/transactions/by-id/'+txid+'/wire?offset='+offset+'&length=97',envelope)
                require(data['txid']==txid and data['offset']==offset,'wire identity/offset');require(total is None or total==data['total_bytes'],'wire total changed');total=data['total_bytes'];chunk=bytes.fromhex(data['bytes_hex']);require(len(chunk)<=97,'wire chunk cap ignored');raw.extend(chunk)
                next_offset=data['next_offset']
                if next_offset is None:require(len(raw)==int(total),'wire final length');return bytes(raw)
                require(next_offset==str(len(raw)) and int(next_offset)>int(offset),'wire did not advance');offset=next_offset
            raise AssertionError('transaction wire exceeded local bound')
        def context(self):
            return dict(native=self.raw('status'),http=self.http('/status'))
        @staticmethod
        def stamp(context):
            n=context['native'];h=context['http']
            return dict(native={k:n.get(k) for k in (*local.STATE_FIELDS,'fetch_epoch','pending_journal','pending_receipt','pending_propagation','execution_paused','reopen_required','mempool_ready')},http={k:h.get(k) for k in ('service_epoch','generation','binding','indexed_anchor','authoritative_anchor')})
        def idle_probe(self):
            # Initial A has no peers and no commands run inside this interval.
            started=time.monotonic();end=started+6;first_request=len(evidence['requests']);baseline=None;rounds=0;busy=0
            while rounds<20 or time.monotonic()-started<2:
                require(time.monotonic()<end,'idle HTTP-only probe did not complete bounded ready observations')
                status=self.http('/status',idle_probe=True,budget=min(2,end-time.monotonic()))
                if not status['ready']:
                    busy+=1;time.sleep(.01);continue
                stamp={k:status[k] for k in ('service_epoch','generation','binding','indexed_anchor','authoritative_anchor')}
                if baseline is None:
                    envelope=self.http('/blocks?page_size=1',idle_probe=True,budget=min(2,end-time.monotonic()));baseline=stamp
                require(stamp==baseline,'idle durable authority stamp changed')
                page=self.http('/blocks?page_size=1',envelope['snapshot_token'],idle_probe=True,budget=min(2,end-time.monotonic()))
                require(page==envelope,'idle pinned data changed');rounds+=1;time.sleep(.1)
            record('http-only-idle-authority-probe',node=self.label,seconds=time.monotonic()-started,rounds=rounds,not_ready_observations=busy,baseline=baseline,request_range=[first_request,len(evidence['requests'])])
        def audit(self, force=False):
            nonlocal lifecycle_failed
            if self.auditing or self.base is None:return
            self.auditing=True;started=time.monotonic();deadline=started+self.timeout;attempt=0
            try:
                while True:
                    attempt+=1;self.audit_context=None
                    try:return self.audit_once(force)
                    except (Changed,AssertionError) as error:
                        before=self.audit_context
                        if before is None:raise
                        after=self.context()
                        # Same tip may acquire a new header/body/policy context.
                        # Native coin reads and multi-screen DOM use the latest
                        # state: retry only when their observation fence changed.
                        changed=self.stamp(before)!=self.stamp(after)
                        if not changed:raise
                        record('whole-observation-restart',node=self.label,attempt=attempt,max_attempts=4,elapsed=time.monotonic()-started,deadline_seconds=self.timeout,error=str(error),error_context=getattr(error,'context',None),old_snapshot=getattr(self,'audit_envelope',None),before=before,after=after)
                        require(attempt<4 and time.monotonic()<deadline,'whole observation kept changing beyond bounded retries')
            except Exception:
                lifecycle_failed=True
                self.failed=True
                raise
            finally:self.auditing=False
        def audit_once(self, force):
            require(all(local.digest(reference/p)==digest for p,digest in evidence['reference_sha256'].items()),'reference source changed during acceptance')
            require(all(local.digest(frontend/p)==digest for p,digest in evidence['frontend_sha256'].items()),'frontend changed during acceptance')
            deadline=time.monotonic()+self.timeout
            while True:
                native=self.raw('status');status=self.http('/status')
                if status['ready'] and status['indexed_anchor']['block_id']==native.get('tip') and native.get('mempool_ready') is True and not any(native.get(k) for k in ('pending_journal','pending_receipt','pending_propagation','execution_paused','reopen_required')):break
                require(time.monotonic()<deadline,'explorer/native did not converge');time.sleep(.025)
            self.audit_tip=native['tip'];self.audit_context=dict(native=native,http=status);identity=(native['tip'],status['service_epoch'],status['generation'])
            if identity in self.audited and not force:return
            if self.label=='a' and not getattr(self,'idle_probed',False):
                self.idle_probe();self.idle_probed=True
            for k in ('accepted_pool','detached_history','finality'):require(status['capabilities'][k] is False,'unsupported feature claim')
            require(status['binding']==dict(chain_id=native['chain_id'],genesis=native['genesis_id'],profile_id=native['profile_digest']),'native chain/profile differs')
            envelope=self.http('/blocks?page_size=1');self.audit_envelope=envelope;snapshot=envelope['snapshot'];token=envelope['snapshot_token']
            if snapshot['tip']!=native['tip']:raise Changed()
            blocks=self.pages('/blocks',envelope);require([int(b['height']) for b in blocks]==list(range(native['height'],-1,-1)),'canonical block paging incomplete/order wrong')
            old=previous.get(self.home)
            if old and (old['token']!=token):
                changed=self.http('/blocks',old['token'],expected=409);require(changed['error']['code']=='stale_snapshot','old token not rejected')
                reason='restart' if old['tip']==snapshot['tip'] and old['epoch']!=snapshot['service_epoch'] else 'publication'
                record('stale-token-rejected',node=self.label,reason=reason,old=old['snapshot'],new=snapshot)
                if old['cursor']:
                    changed=self.http('/blocks?page_size=1&'+urllib.parse.urlencode(dict(cursor=old['cursor'])),expected=409);require(changed['error']['code']=='stale_cursor','old block cursor not rejected');record('stale-cursor-rejected',node=self.label,reason=reason)
            rows={};spends={};expected_assets=set();plan=None
            for summary in reversed(blocks):
                bid=summary['block_id'];detail=self.pinned('/blocks/'+bid,envelope);height=self.pinned('/blocks/by-height/'+summary['height'],envelope);require(detail==height,'block height/ID resolution differs')
                raw=self.body_bytes(bid);decoded=decode_block_wire(raw,profile,chain);require(block_id(chain,decoded.header).hex()==bid,'native BlockID/wire-order parity')
                require(detail['header_wire']==raw[:134].hex(),'exact134-byte native header mismatch');require(detail['tx_count']==str(len(decoded.transactions)),'native tx count mismatch')
                for key in ('prev_id','bits','time','nonce','version','size','height','tx_root','state_root'):
                    value=getattr(decoded.header,key);wanted=value.hex() if isinstance(value,bytes) else str(value);require(detail['header'][key]==wanted,'native header field mismatch '+key)
                summaries=self.pages('/blocks/'+bid+'/transactions',envelope);require(len(summaries)==len(decoded.transactions),'native tx order page count')
                for index,(transaction,tx_summary) in enumerate(zip(decoded.transactions,summaries)):
                    ids=identity_digests(transaction,profile,chain);txid,txhash=ids.txid.hex(),ids.txhash.hex();wire=encode_transaction(transaction,profile)
                    require(tx_summary['txid']==txid and tx_summary['txhash']==txhash and tx_summary['location']==dict(block_id=bid,height=summary['height'],tx_index=str(index)),'native ordered identities differ')
                    tx=self.pinned('/transactions/by-id/'+txid,envelope);require(tx==self.pinned('/transactions/by-hash/'+txhash,envelope),'TxID/TxHash resolution differs');require(tx['lock']==str(transaction.lock),'native lock differs');require(self.wire(txid,envelope)==wire,'exact native transaction wire mismatch')
                    if txid in payments:require(payments[txid]['wire']==wire.hex() and payments[txid]['txhash']==txhash,'controller signed payment bytes changed')
                    inputs=self.pages('/transactions/by-id/'+txid+'/inputs',envelope);outputs=self.pages('/transactions/by-id/'+txid+'/outputs',envelope);require(len(inputs)==len(transaction.inputs) and len(outputs)==len(transaction.outputs),'native input/output completeness')
                    for ordinal,(fact,inp) in enumerate(zip(inputs,transaction.inputs)):
                        wanted=dict(input_index=str(ordinal),flags=str(inp.flags),prev_txid=inp.prev_txid.hex(),prev_index=str(inp.prev_index),sequence=str(inp.sequence),path_index=str(inp.path_index) if inp.flags==1 else None,witness_count=str(len(inp.witnesses)))
                        require(all(fact[k]==v for k,v in wanted.items()),'native input selectors differ');cb=fact['coinbase_data'];require(cb['present']==(inp.coinbase_data is not None),'coinbase data presence differs')
                        def referenced(ref):
                            offset,length=int(ref['offset']),int(ref['length']);require(offset+length<=len(wire),'descriptor escapes native frame');return wire[offset:offset+length]
                        if inp.coinbase_data is not None:require(referenced(cb['wire_ref'])==inp.coinbase_data,'coinbase payload bytes differ')
                        if inp.flags==1:
                            spends[(inp.prev_txid.hex(),str(inp.prev_index))]=dict(transaction=dict(block_id=bid,height=summary['height'],tx_index=str(index),txid=txid,txhash=txhash),input_index=str(ordinal))
                            prior=rows[(inp.prev_txid.hex(),str(inp.prev_index))];resolved=fact['resolved_coin'];require(resolved['availability']=='complete','spend missing frozen creation');require(resolved['output']=={k:v for k,v in prior.items() if k!='spend'},'frozen native prior output differs')
                        witnesses=self.pages('/transactions/by-id/'+txid+'/witnesses?input_index='+str(ordinal),envelope);require(len(witnesses)==len(inp.witnesses),'native witnesses truncated')
                        for witness,native_witness in zip(witnesses,inp.witnesses):
                            require(referenced(witness['script'])==native_witness.script,'script bytes differ')
                            siblings=witness['siblings'];arguments=witness['arguments'];require(int(siblings['count'])==len(native_witness.siblings) and int(arguments['count'])==len(native_witness.arguments),'native witness counts differ')
                            require(referenced(siblings['table_ref'])==encode_compact_size(len(native_witness.siblings))+b''.join(native_witness.siblings),'proof table framing differs')
                            require(referenced(arguments['table_ref'])==encode_compact_size(len(native_witness.arguments))+b''.join(encode_compact_size(len(a))+a for a in native_witness.arguments),'argument table framing differs')
                    for ordinal,(row,native_output) in enumerate(zip(outputs,transaction.outputs)):
                        wanted=dict(txid=txid,out_idx=str(ordinal),flags=str(native_output.flags),value=str(native_output.value),has_token=native_output.token_id is not None,is_burn=bool(native_output.flags&2),branches=[b.hex() for b in native_output.branches],paths=[list(map(str,p)) for p in native_output.paths])
                        require(all(row[k]==v for k,v in wanted.items()),'native output facts differ');require(row['creation']==dict(block_id=bid,height=summary['height'],tx_index=str(index),txid=txid,txhash=txhash),'native output creation differs');require(row==self.pinned('/outputs/'+txid+'/'+str(ordinal),envelope),'historical outpoint differs');rows[(txid,str(ordinal))]=row
                        if native_output.token_id is not None:require(row['token_id']==native_output.token_id.hex(),'native token identity differs');expected_assets.add(row['token_id'])
                    if index>0 or plan is None:plan=dict(block_id=bid,height=summary['height'],txid=txid,txhash=txhash,wire_prefix=wire[:24].hex(),output_value=str(transaction.outputs[0].value),tip=snapshot['tip'],assets=[])
            for point,row in rows.items():
                require(row['spend']==spends.get(point),'spend history differs from decoded native inputs')
                coin=self.raw('coin',txid=point[0],index=int(point[1]));require((coin['coin'] is not None)==(point not in spends and not row['is_burn']),'native UTXO presence differs from historical spend/burn')
            roots=sorted({json.loads(p.read_text())['policy']['root'] for p in output.glob('payment-artifact-*.json')})
            history=self.pages('/branches/outputs',envelope,dict(any_branch=roots,include_burn=True)) if roots else [];unspent=self.pages('/branches/utxos',envelope,dict(any_branch=roots)) if roots else []
            wanted={k:v for k,v in rows.items() if set(v['branches'])&set(roots)};observed={(i['record']['txid'],i['record']['out_idx']):i['record'] for i in history};require(observed==wanted,'branch history differs from native decoded outputs')
            require({(i['record']['txid'],i['record']['out_idx']) for i in unspent}=={k for k,v in wanted.items() if v['spend'] is None and not v['is_burn']},'branch UTXOs differ from native history')
            for root in roots:
                positional=self.pages('/branches/outputs',envelope,dict(positions=[dict(position='0',roots=[root])],include_burn=True));require({(i['record']['txid'],i['record']['out_idx']) for i in positional}=={k for k,v in wanted.items() if v['branches'][0]==root},'positional predicate differs')
            assets=self.pages('/assets',envelope);require([a['token_id'] for a in assets]==sorted(expected_assets),'asset registry differs from native token occurrences')
            for asset in assets:
                aid=asset['token_id'];require(self.pinned('/assets/'+aid,envelope)==asset,'asset detail differs');self.pages('/assets/'+aid+'/events',envelope);self.pages('/assets/'+aid+'/outputs?view=history',envelope);self.pages('/assets/'+aid+'/outputs?view=unspent',envelope)
            if assets:evidence['asset_fixture']='native_accepted_token_observed_only_not_accounting_validated'
            # Every native pending transaction remains absent from confirmed-only explorer.
            for txid,payment in payments.items():
                native_tx=self.raw('transactionstatus',txid=txid,txhash=payment['txhash'],wire=payment['wire'])
                if native_tx.get('state') in ('pending','conflicted'):
                    missing=self.http('/transactions/by-id/'+txid,token,expected=404);require(missing['error']['code']=='not_in_covered_chain','miss asserted pending/rejected');record('pending-distinct-from-confirmed',node=self.label,txid=txid,native_state=native_tx['state'],snapshot=snapshot)
            final=self.http('/status');
            if not final['ready'] or final['service_epoch']!=snapshot['service_epoch'] or final['generation']!=snapshot['generation']:raise Changed()
            proxy=self.http('/blocks?page_size=1',token,proxy=True);require(proxy==envelope,'private proxy changed exact envelope')
            if plan and (self.label.startswith('a') or self.label=='c-fork'):
                plan['root']=next((root for root in roots if any(root in i['record']['branches'] for i in history)),None);plan['assets']=sorted(expected_assets)
                answer=subprocess.run([node_exe,'--input-type=module','-e',DOM_SCRIPT,str(frontend),self.proxy_base,json.dumps(plan)],capture_output=True,text=True,timeout=min(60,self.timeout*2))
                require(answer.returncode==0,'actual frontend DOM failed '+answer.stderr);record('actual-frontend-dom',node=self.label,observation=snapshot,result=json.loads(answer.stdout))
            previous[self.home]=dict(token=token,cursor=envelope['data']['next_cursor'],tip=snapshot['tip'],epoch=snapshot['service_epoch'],snapshot=snapshot)
            snapshots.append(dict(node=self.label,home=self.home,snapshot=snapshot,txids=sorted({k[0] for k in rows}),history=history))
            record('native-explorer-snapshot',**snapshots[-1]);self.audited.add(identity)
        def request(self, command, wait_timeout=None, **fields):
            result=super().request(command,wait_timeout=wait_timeout,**fields)
            if command=='transactionstatus' and result.get('txid'):
                payments[result['txid']]=dict(wire=fields['wire'],txhash=fields['txhash'])
                if self.base and not self.auditing:self.audit()
            if command=='status' and result.get('tip_known') and result.get('mempool_ready') and not self.auditing:self.audit()
            return result
        def stop(self):
            nonlocal lifecycle_failed
            if sys.exc_info()[0] is not None:lifecycle_failed=True
            try:
                if self.process.poll() is None and self.base and not self.failed and not lifecycle_failed:self.audit(force=True)
            finally:
                super().stop()
                if self.proxy and self.proxy.poll() is None:
                    self.proxy.terminate()
                    try:self.proxy.wait(timeout=3)
                    except subprocess.TimeoutExpired:self.proxy.kill();self.proxy.wait(timeout=3)
    local.Node=Node;driver.local_module=lambda:local
    try:
        driver.main(driver_args)
        native=json.loads((output/'evidence.json').read_text());require(native['passed'],'native wallet lifecycle failed')
        checks=evidence['checks'];require(any(c['check']=='stale-token-rejected' and c['reason']=='restart' for c in checks),'no same-tip epoch restart invalidation')
        require(any(c['check']=='stale-cursor-rejected' for c in checks),'no stale cursor rejection')
        require(any(c['check']=='actual-frontend-dom' for c in checks),'actual frontend DOM not exercised')
        require(any(c['check']=='pending-distinct-from-confirmed' for c in checks),'pending not independently distinguished')
        detached=[c for c in native['checks'] if c['check']=='detached-payment' and c['response']['state']=='pending'];require(len(detached)==1,'native detach/remine witness missing');txid=detached[0]['response']['txid']
        homes={s['home'] for s in snapshots};transition=None
        for home in homes:
            phase=0;found=[]
            for s in snapshots:
                if s['home']!=home:continue
                present=txid in s['txids']
                if (phase==0 and present) or (phase==1 and not present) or (phase==2 and present):phase+=1;found.append(s['snapshot'])
                if phase==3:transition=dict(home=home,txid=txid,snapshots=found);break
            if transition:break
        require(transition is not None,'same-home confirmed/detached/remined explorer membership missing');record('confirmed-detached-remined-membership',**transition)
        require(not own.require_assets,'asset accounting/lifecycle is a separate acceptance harness; this wallet gate does not establish it')
        evidence['native_evidence_sha256']=local.digest(output/'evidence.json');evidence['passed']=True;save()
    except Exception as error:
        evidence['failure']=dict(kind=type(error).__name__,error=str(error));save();raise
    finally:
        for proxy in proxies:
            if proxy.poll() is None:proxy.terminate()
            try:proxy.wait(timeout=3)
            except subprocess.TimeoutExpired:proxy.kill();proxy.wait(timeout=3)
        evidence['proxy_cleanup']=[dict(pid=p.pid,exit=p.poll()) for p in proxies];save()
    print('Actual native explorer/DOM lifecycle passed:',output)


if __name__=='__main__': main()
