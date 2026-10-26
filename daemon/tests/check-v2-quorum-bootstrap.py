#!/usr/bin/env python3
"""Prepare real native 2024-block development stake; no quorum acceptance claim."""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time


def public_key(scalar):
    """Public fixture scalars 1..9; deterministic curve multiplication only."""
    field=2**256-2**32-977
    g=(0x79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798,
       0x483ada7726a3c4655da4fbfc0e1108a8fd17b448a68554199c47d08ffb10d4b8)
    def add(a,b):
        if a is None:return b
        if b is None:return a
        if a[0]==b[0] and (a[1]+b[1])%field==0:return None
        slope=((3*a[0]*a[0])*pow(2*a[1],-1,field) if a==b else (b[1]-a[1])*pow(b[0]-a[0],-1,field))%field
        x=(slope*slope-a[0]-b[0])%field
        return x,(slope*(a[0]-x)-a[1])%field
    result=None
    while scalar:
        if scalar&1:result=add(result,g)
        g=add(g,g);scalar>>=1
    return result[0].to_bytes(32,'big').hex()


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('daemon','compiler','manifest','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    for name in ('daemon-source','compiler-source','generator-source'):
        parser.add_argument('--'+name,required=True)
    parser.add_argument('--report',type=Path,help='defaults to manifest sibling report.json')
    parser.add_argument('--node',default='node')
    parser.add_argument('--timeout',type=float,default=30)
    parser.add_argument('--deadline-seconds',type=float,default=1800)
    parser.add_argument('--max-nonce-batches',type=int,default=4096)
    args=parser.parse_args(argv)
    spec=importlib.util.spec_from_file_location('local_bootstrap',Path(__file__).with_name('check-v2-local-nodes.py'))
    local=importlib.util.module_from_spec(spec);spec.loader.exec_module(local)
    require=local.require
    for pin in (args.daemon_source,args.compiler_source,args.generator_source):require(local.hex_string(pin,20),'full exact source commits required')
    require(1<=args.timeout<=60 and 60<=args.deadline_seconds<=14400 and 1<=args.max_nonce_batches<=4096,'explicit bounded deadlines/batches required')
    manifest_path=args.manifest.resolve(); manifest=json.loads(manifest_path.read_text())
    report_path=(args.report or manifest_path.with_name('report.json')).resolve()
    report=json.loads(report_path.read_text())
    require(manifest['schema']==2 and report['name']=='lotus-v2-quorum-development-20261015-v1','explicit generated quorum development candidate required')
    require(local.digest(manifest_path)==report['manifest_sha256'],'candidate manifest/report digest mismatch')
    require(report['mature_tip']==2024 and report['funding_blocks']==9 and report['stake_confirmations']==2016,'unexpected candidate stake schedule')
    require(manifest['header']['chain_id']==report['chain_id'] and manifest['header']['genesis_id']==report['genesis_id'],'candidate report identity mismatch')
    root=args.output.resolve();root.mkdir()
    (root/'manifest.json').write_bytes(manifest_path.read_bytes())
    (root/'candidate-report.json').write_bytes(report_path.read_bytes())
    (root/'blocks').mkdir()
    repo=Path(__file__).resolve().parents[2]
    sys.path.insert(0,str(repo/'tools/lotus-v2-reference'))
    from lotus_v2_reference.block import Coin,utxo_root,state_root,MonetaryState
    from lotus_v2_reference.block_wire import decode_block_wire,complete_transaction_root
    from lotus_v2_reference.block_seal import block_id
    from lotus_v2_reference.header_context import HeaderChainProfile,parent_median_time,validate_child_header
    from lotus_v2_reference.signing import TxProfile,identity_digests
    from lotus_v2_reference.encoding import Output,Profile,encode_output
    h=manifest['header'];chain=bytes.fromhex(h['chain_id'])
    txp=TxProfile(*manifest['transaction_limits'])
    hp=HeaderChainProfile(chain,h['version'],h['time'],h['bits'],int.from_bytes(bytes.fromhex(h['pow_limit']),'little'),h['half_life'],h['spacing'])
    history=[decode_block_wire(bytes.fromhex(manifest['genesis']),txp,chain).header]
    coins={}; funding=[]; node=None; end=time.monotonic()+args.deadline_seconds
    evidence=dict(schema='lotus-v2/quorum-bootstrap-check/1',passed=False,
        scope='native accepted development stake preparation only; no peer proof/quorum/poll/finality claim',
        fixture_keys='PUBLIC TEST ONLY: BIP340 x-only public keys of known scalars 1 through 9; never use for real funds',
        daemon_source=args.daemon_source,compiler_source=args.compiler_source,generator_source=args.generator_source,
        daemon_sha256=local.digest(args.daemon.resolve()),compiler_sha256=local.digest(args.compiler.resolve()/'dist/generic.js'),
        manifest_sha256=local.digest(manifest_path),report_sha256=local.digest(report_path),harness_sha256=local.digest(Path(__file__)),
        funding=funding,milestones=[],accepted_blocks=0)
    def save():(root/'evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
    def deadline():require(time.monotonic()<end,'bootstrap overall deadline expired')
    def status():
        until=min(end,time.monotonic()+args.timeout)
        while time.monotonic()<until:
            value=node.request('status',wait_timeout=max(.001,min(args.timeout,until-time.monotonic())))
            if value.get('tip_known') and value.get('mempool_ready') and not any(value.get(k) for k in ('pending_journal','pending_receipt','pending_propagation','execution_paused','reopen_required')):return value
            time.sleep(.01)
        raise AssertionError('native state did not quiesce')
    templates=[]
    for scalar in range(1,10):
        key=public_key(scalar);compiler=args.compiler.resolve()
        js="import{readFileSync}from'node:fs';const{compileContract}=await import(process.argv[1]);console.log(JSON.stringify(compileContract(readFileSync(process.argv[2],'utf8'),{contract:'Payment',bindings:{Payment:{owner:process.argv[3]}}})));"
        result=subprocess.run([args.node,'--input-type=module','-e',js,(compiler/'dist/generic.js').as_uri(),str(compiler/'examples/gallery/payment.lotus'),key],capture_output=True,text=True,timeout=args.timeout)
        require(result.returncode==0,result.stderr)
        artifact=json.loads(result.stdout);script=artifact['methods'][0]['scriptHex'];policy=artifact['policy']['root']
        require(script=='20'+key+'bc4e','compiler Payment must match native stake ownership script')
        (root/('payment-'+str(scalar)+'.json')).write_text(json.dumps(artifact,indent=2)+'\n')
        template=encode_output(Output(0,0,None,(bytes.fromhex(policy),),((0,),)),Profile(16,16,812,8192)).hex()
        templates.append(dict(public_fixture_scalar=scalar,public_key=key,script=script,policy_root=policy,coinbase_output=template))
    def milestone(current):
        expected_root=utxo_root(coins).hex()
        require(current['utxo_root']==expected_root,'native UTXO root differs from all actual produced coinbase outputs')
        expected_state=state_root(chain,current['height'],bytes.fromhex(expected_root),MonetaryState.from_bytes(bytes.fromhex(current['monetary_bytes']))).hex()
        require(current['state_root']==expected_state,'native state commitment inconsistent with actual coins/monetary bytes')
        results=[]
        for entry in funding:
            lookup=node.request('coin',txid=entry['txid'],index=0)
            proof=node.request('proof',txid=entry['txid'],index=0)
            expected=coins[(bytes.fromhex(entry['txid']),0)].encode().hex()
            require(lookup['coin']==expected and proof['proof']['presence']==1 and proof['proof']['coin']==expected,'native stake coin/proof differs from produced funding bytes')
            require(all(lookup[k]==current[k] and proof[k]==current[k] for k in local.STATE_FIELDS),'stake coin/proof snapshot drift')
            confirmations=current['height']-entry['creation_height']+1
            results.append(dict(txid=entry['txid'],confirmations=confirmations,stake_mature=confirmations>=2016,coin=lookup['coin'],proof=proof['proof']))
        require(results[-1]['confirmations']==(2015 if current['height']==2023 else 2016),'youngest funding maturity boundary differs')
        evidence['milestones'].append(dict(status=current,coins=results,independent_utxo_root=expected_root));save()
    try:
        network=root/'node.network.json'
        network.write_text(json.dumps(dict(schema=1,magic='76327139',listen=dict(address='127.0.0.1',port=0),connect=[],receive_limit=max(1048576,manifest['block_read_limit']),local_policy='bounded-local-v1'))+'\n')
        node=local.Node('bootstrap',args.daemon.resolve(),root/'manifest.json',root/'node-home',network,root,args.timeout)
        node.await_ready(); evidence['process']=dict(pid=node.process.pid,command=node.command,ready=node.ready);save()
        current=status()
        require(current['height']==0 and current['tip']==h['genesis_id'] and current['profile_digest']==report['profile_digest'],'native initial candidate profile differs')
        with (root/'accepted-blocks.jsonl').open('x') as ledger:
            for height in range(1,2025):
                deadline();parent=history[0];mtp=parent_median_time(hp,parent,history);timestamp=mtp+1
                require(timestamp<=int(time.time())+manifest['future_window'],'compressed schedule exceeds actual native future-time bound')
                selected=templates[height-1] if height<=9 else templates[0]
                nonce='0';answer=None
                for _ in range(args.max_nonce_batches):
                    deadline()
                    answer=node.request('minepool',expected_parent=current['tip'],time=timestamp,max_claim=str(2**64-1) if height<=9 else '100000',coinbase_output=selected['coinbase_output'],coinbase_data=None,start_nonce=nonce,max_attempts=256)
                    require(answer.get('ok') and answer.get('pool_selected')==0,'bootstrap mining must use empty native pool')
                    if answer.get('found'):break
                    require(answer.get('result')=='nonce_exhausted' and answer.get('next_nonce') is not None,'nonce batch failed '+str(answer))
                    nonce=answer['next_nonce']
                require(answer.get('found') and answer.get('accepted') is False and answer.get('pending_validation') is True,'mined candidate must enter native validation')
                until=min(end,time.monotonic()+args.timeout)
                while True:
                    current=status()
                    if current['tip']==answer['block_id']:break
                    require(time.monotonic()<until,'native candidate did not connect')
                require(current['height']==height,'accepted native height differs')
                body=node.request('readblock',block_id=current['tip'],offset=0,length=8192)
                require(body.get('ok') and body['eof'] and body['total_bytes']<=8192,'bootstrap body must fit bounded read')
                wire=bytes.fromhex(body['data']);framed=decode_block_wire(wire,txp,chain)
                require(len(framed.transactions)==1,'unexpected ordinary transaction in native funding chain')
                txroot=complete_transaction_root(framed.transactions,txp,chain)
                validate_child_header(hp,parent,history,framed.header,expected_tx_root=txroot,expected_state_root=framed.header.state_root,expected_size=len(wire))
                require(block_id(chain,framed.header).hex()==current['tip'] and framed.header.time==timestamp,'native-produced header identity/time mismatch')
                cb=framed.transactions[0];ids=identity_digests(cb,txp,chain)
                require(ids.txid.hex()==answer['coinbase_txid'] and len(cb.outputs)==1 and str(cb.outputs[0].value)==answer['coinbase_value'] and cb.outputs[0].branches==(bytes.fromhex(selected['policy_root']),),'native coinbase result differs from actual produced bytes')
                coin=Coin(ids.txid,0,cb.outputs[0].value,bytes.fromhex(selected['policy_root']),height,mtp,True,cb.outputs[0]);coins[coin.key()]=coin
                if height<=9:
                    require(coin.value>=report['stake_dust'],'native funded proof below stake dust')
                    funding.append(dict(selected,txid=ids.txid.hex(),txhash=ids.txhash.hex(),index=0,value=str(coin.value),creation_height=height,creation_parent_mtp=mtp,block_id=current['tip'],coin=coin.encode().hex()))
                path=root/'blocks'/(str(height)+'.block');path.write_bytes(wire)
                row=dict(height=height,time=timestamp,bits=framed.header.bits,nonce=str(framed.header.nonce),status=current,mining=answer,body_sha256=local.digest(path))
                ledger.write(json.dumps(row,separators=(',',':'))+'\n');ledger.flush()
                history=([framed.header]+history)[:11];evidence['accepted_blocks']=height
                if height in (9,2023,2024):
                    if height>=2023:milestone(current)
                    save()
                if height%100==0:print('Native accepted height',height,flush=True)
        values=[int(x['value']) for x in funding]
        require(len(values)==9 and sum(values)-max(values)>=report['quorum'],'native actual minimum-any-eight stake below quorum')
        evidence['minimum_any_eight']=str(sum(values)-max(values));evidence['final']=current
        evidence['accepted_ledger_sha256']=local.digest(root/'accepted-blocks.jsonl')
        evidence['passed']=True;save()
    except Exception as error:
        evidence['failure']=dict(kind=type(error).__name__,error=str(error));save();raise
    finally:
        if node:
            try:
                node.stop()
                require(node.process.poll()==0,'native bootstrap child did not exit cleanly')
            except Exception as error:
                evidence['passed']=False
                evidence['cleanup_error']=str(error)
                raise
            finally:
                evidence['cleanup']=dict(pid=node.process.pid,exit=node.process.poll());save()
    print('Native stake preparation passed (no quorum claim):',root)


if __name__=='__main__':main()
