#!/usr/bin/env python3
"""Common L1 workload: presigned v2 P2PKH Schnorr, fixed work counts, owned nodes."""
import argparse, base64, concurrent.futures as cf, hashlib, http.client, json, math, os, signal, subprocess, sys, tempfile, threading, time, random
from pathlib import Path
random.seed(20261018)
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'harness/legacy'))
AUTH='Basic '+base64.b64encode(b'bench:bench').decode()
class RPC:
    def __init__(self,port):self.port=port;self.local=threading.local()
    def request(self,payload):
        c=getattr(self.local,'conn',None)
        if c is None:c=http.client.HTTPConnection('127.0.0.1',self.port,timeout=180);self.local.conn=c
        c.request('POST','/',json.dumps(payload),{'Authorization':AUTH,'Content-Type':'application/json'})
        r=c.getresponse();data=json.loads(r.read())
        for item in data if isinstance(data,list) else [data]:
            if item.get('error'):raise RuntimeError(str(item['error']))
        return data
    def call(self,m,p=None):return self.request({'jsonrpc':'2.0','id':1,'method':m,'params':p or []})['result']
def wait(predicate,timeout=90):
    end=time.perf_counter()+timeout
    while time.perf_counter()<end:
        if predicate():return
        time.sleep(.002)
    raise TimeoutError('convergence predicate did not become true')
def stats(values):
    a=sorted(values)
    return {f'p{q}_ms':a[min(len(a)-1,math.ceil(q/100*len(a))-1)]*1000 for q in [50,95,99]}
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--daemon',required=True);ap.add_argument('--source',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--port-base',type=int,default=35210);ap.add_argument('--latency-only',action='store_true');args=ap.parse_args()
    if not 1024 <= args.port_base <= 65530:raise ValueError('Invalid benchmark port range')
    os.environ['SRCDIR']=str(args.source.resolve())
    from test_framework.address import ADDRESS_ECREG_P2SH_OP_TRUE, SCRIPTSIG_OP_TRUE
    from test_framework.hash import hash160
    from test_framework.key import ECKey
    from test_framework.messages import CTransaction,COutPoint,CTxIn,CTxOut,ToHex
    from test_framework.script import CScript,OP_DUP,OP_HASH160,OP_EQUALVERIFY,OP_CHECKSIG
    from test_framework.signature_hash import SignatureHashForkId,SIGHASH_ALL,SIGHASH_FORKID
    from test_framework.txtools import pad_tx
    out={'schema_version':1,'workload':'legacy-v2-p2pkh-schnorr64','workload_seed':20261018,'metrics':{},'status':'running'}
    def save():
        tmp=args.output.with_suffix('.tmp');tmp.write_text(json.dumps(out,indent=2));tmp.replace(args.output)
    save();procs=[];logs=[]
    with tempfile.TemporaryDirectory(prefix='step-bench-') as d:
        try:
            clients=[RPC(args.port_base+1+i*2) for i in range(3)]
            for i in range(3):
                nd=Path(d)/str(i);nd.mkdir();err=open(nd/'stderr.log','w');logs.append(err)
                argv=[args.daemon,'-regtest',f'-datadir={nd}',f'-port={args.port_base+i*2}',f'-bind=127.0.0.1:{args.port_base+i*2}',f'-rpcport={args.port_base+1+i*2}','-rpcuser=bench','-rpcpassword=bench','-server=1','-listenonion=0','-discover=0','-dnsseed=0','-natpmp=0','-rpcthreads=16','-rpcworkqueue=2048','-par=8','-maxmempool=1024','-checkmempool=0','-whitelist=127.0.0.1']
                procs.append(subprocess.Popen(argv,stdout=subprocess.DEVNULL,stderr=err))
            def ready():
                for i,c in enumerate(clients):
                    if procs[i].poll() is not None:raise RuntimeError((Path(d)/str(i)/'stderr.log').read_text())
                    try:c.call('getblockchaininfo')
                    except (OSError, http.client.HTTPException, RuntimeError):
                        old=getattr(c.local,'conn',None)
                        if old:old.close()
                        c.local.conn=None
                        return False
                return True
            wait(ready,45);c=clients[0]
            for i,j in [(0,1),(0,2),(1,2)]:clients[i].call('addnode',[f'127.0.0.1:{args.port_base+j*2}','onetry'])
            wait(lambda:all(len(x.call('getpeerinfo'))>=2 for x in clients))
            def sync():
                tip=c.call('getbestblockhash');wait(lambda:all(x.call('getbestblockhash')==tip for x in clients))
            def mine():c.call('generatetoaddress',[1,ADDRESS_ECREG_P2SH_OP_TRUE]);sync()
            hashes=c.call('generatetoaddress',[120,ADDRESS_ECREG_P2SH_OP_TRUE]);sync()
            key=ECKey();key.set((42).to_bytes(32,'big'),True);pub=key.get_pubkey().get_bytes()
            spk=CScript([OP_DUP,OP_HASH160,hash160(pub),OP_EQUALVERIFY,OP_CHECKSIG])
            # Independent output pools. Signing/funding excluded from timers.
            pools=[]
            for pool_index,h in enumerate(hashes[:4]):
                count=801 if pool_index==3 else 500
                cb=c.call('getblock',[h,2])['tx'][0];value=int(round(cb['vout'][0]['value']*100));unit=(value-100000)//count
                tx=CTransaction();tx.nVersion=2;tx.vin=[CTxIn(COutPoint(int(cb['txid'],16),0),SCRIPTSIG_OP_TRUE,0xfffffffe)];tx.vout=[CTxOut(unit,spk) for _ in range(count)]
                txid=c.call('sendrawtransaction',[ToHex(tx)])
                pool=[]
                for idx in range(count):
                    t=CTransaction();t.nVersion=2;t.vin=[CTxIn(COutPoint(int(txid,16),idx),b'',0xfffffffe)];t.vout=[CTxOut(unit-1000,spk)];pad_tx(t)
                    sig=key.sign_schnorr(SignatureHashForkId(spk,t,0,65,unit))+b'\x41';t.vin[0].scriptSig=CScript([sig,pub]);pool.append(ToHex(t))
                pools.append(pool)
            out['transaction_fixture_sha256']=hashlib.sha256(''.join(h for pool in pools for h in pool).encode()).hexdigest()
            out['workload_definition']={'track':'legacy-fixed-latency-v2' if args.latency_only else 'legacy-v2-p2pkh-schnorr64-v1','pool_counts':[len(pool) for pool in pools],'transaction_sizes':[sorted({len(h)//2 for h in pool}) for pool in pools],'ingestion_workers':8,'reader_workers':12,'json_rpc_batch':50}
            out['workload_id']=hashlib.sha256(json.dumps(out['workload_definition'],sort_keys=True).encode()).hexdigest();save()
            mine()
            def ingest(pool,batch=False):
                chunks=[pool[i:i+50] for i in range(0,len(pool),50)] if batch else [[x] for x in pool]
                def submit(chunk):
                    if batch:return c.request([{'jsonrpc':'2.0','id':j,'method':'sendrawtransaction','params':[h]} for j,h in enumerate(chunk)])
                    return c.call('sendrawtransaction',[chunk[0]])
                start=time.perf_counter()
                with cf.ThreadPoolExecutor(max_workers=8) as ex:list(ex.map(submit,chunks))
                elapsed=time.perf_counter()-start
                return dict(count=len(pool),workers=8,seconds=elapsed,tps=len(pool)/elapsed)
            def readload(writer=None):
                stop=threading.Event();start_barrier=threading.Barrier(13)
                def reader(_):
                    times=[];start_barrier.wait()
                    while not stop.is_set():
                        st=time.perf_counter();c.call('getmempoolinfo');c.call('getblockchaininfo');times.append(time.perf_counter()-st)
                    return times
                with cf.ThreadPoolExecutor(max_workers=12) as ex:
                    futures=[ex.submit(reader,i) for i in range(12)];start_barrier.wait();st=time.perf_counter()
                    if writer:writer()
                    remaining=3-(time.perf_counter()-st)
                    if remaining>0 and writer is None:time.sleep(remaining)
                    stop.set();times=sum([f.result() for f in futures],[])
                sec=time.perf_counter()-st
                return dict(pairs=len(times),rpc_calls=len(times)*2,seconds=sec,rpc_per_second=len(times)*2/sec,latency_unit='two sequential RPCs per reader',**stats(times))
            m=out['metrics']
            if not args.latency_only:m['read_unloaded']=readload();save()
            if not args.latency_only:
                m['single_tx']=ingest(pools[0]);mine();m['json_rpc_batch50']=ingest(pools[1],True);mine();save()
            st=time.perf_counter();relay_ingest=ingest(pools[2]);wait(lambda:all(x.call('getmempoolinfo')['size']==500 for x in clients));sec=time.perf_counter()-st
            if not args.latency_only:m['relay_ingest']=relay_ingest
            m['relay500']={'seconds':sec,'transaction_count':500,'measurement':'fixed-work propagation latency','poll_interval_ms':2,'all_converged':True};save()
            for name,params in [('gbt_standard',[{'rules':['segwit']}]),('gbt_compact',[{'mode':'compact_template'}])]:
                samples=[]
                try:
                    gbt_started=time.perf_counter()
                    while len(samples)<31 or time.perf_counter()-gbt_started<5:
                        st=time.perf_counter();response=c.call('getblocktemplate',params);samples.append(time.perf_counter()-st)
                    # Unsupported compact requests can silently return standard templates.
                    if name=='gbt_compact' and 'transactions' in response:
                        m[name]={'status':'unavailable','reason':'standard template returned'}
                    else:m[name]={'samples':len(samples),'sampling_seconds':time.perf_counter()-gbt_started,**stats(samples)}
                except RuntimeError as ex:m[name]={'status':'unavailable','reason':str(ex)}
            st=time.perf_counter();c.call('generatetoaddress',[1,ADDRESS_ECREG_P2SH_OP_TRUE]);node0=time.perf_counter()-st;sync();sec=time.perf_counter()-st
            m['block500']={'mine_connect_node0_ms':node0*1000,'three_node_ms':sec*1000,'tx_count':500}
            if args.latency_only:ingest(pools[3])
            else:m['read_loaded']=readload(lambda:ingest(pools[3]));save()
            st=time.perf_counter();c.call('generatetoaddress',[1,ADDRESS_ECREG_P2SH_OP_TRUE]);node0=time.perf_counter()-st;sync();sec=time.perf_counter()-st
            m['block801']={'mine_connect_node0_ms':node0*1000,'three_node_ms':sec*1000,'tx_count':801};save()
            # Available independently of the larger historical suite.
            try:out['batch_rpc_available']=c.call('help',['submitrawtxbatch']).splitlines()[0].startswith('submitrawtxbatch ')
            except RuntimeError:out['batch_rpc_available']=False
            out['status']='ok';save()
        except Exception as ex:
            out['status']='failed';out['error']=repr(ex)
            out['node_logs']={str(i):'\n'.join(f.read_text(errors='replace')[-6000:] for f in [(Path(d)/str(i)/'stderr.log'),(Path(d)/str(i)/'regtest/debug.log')] if f.exists()) for i in range(len(procs))}
            save();raise
        finally:
            for p in procs:
                if p.poll() is None:p.terminate()
            for p in procs:
                try:p.wait(timeout=15)
                except subprocess.TimeoutExpired:p.kill();p.wait()
            for f in logs:f.close()
            time.sleep(1)
if __name__=='__main__':main()
