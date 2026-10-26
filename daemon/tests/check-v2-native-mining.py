#!/usr/bin/env python3
"""Native bounded mining -> actual produced bytes -> independent full validation."""
import argparse
from dataclasses import replace
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time


def load_local():
    spec=importlib.util.spec_from_file_location('lotus_v2_local_node_test',Path(__file__).with_name('check-v2-local-nodes.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--daemon',type=Path,required=True)
    p.add_argument('--daemon-source',required=True)
    p.add_argument('--expected-daemon-sha256',required=True)
    p.add_argument('--build-command',required=True)
    p.add_argument('--manifest',type=Path,required=True)
    p.add_argument('--reference-package',type=Path,required=True)
    p.add_argument('--reference-source',required=True)
    p.add_argument('--compiler',type=Path,required=True,help='built compiler package directory')
    p.add_argument('--compiler-source',required=True)
    p.add_argument('--node',default='node')
    p.add_argument('--network-magic',required=True)
    p.add_argument('--receive-limit',type=int,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--timeout',type=float,default=30)
    p.add_argument('--relay-delay',type=float,default=0.05)
    args=p.parse_args(argv)
    local=load_local();require=local.require
    for pin in (args.daemon_source,args.reference_source,args.compiler_source):
        require(re.fullmatch(r'[0-9a-f]{40}',pin) is not None,'full native/reference/compiler source commits required')
    require(re.fullmatch(r'[0-9a-f]{64}',args.expected_daemon_sha256) is not None,'approved binary SHA256 required')
    require(re.fullmatch(r'[0-9a-f]{8}',args.network_magic) is not None,'explicit development magic required')
    require(1<=args.timeout<=120 and 0<args.relay_delay<=0.5,'bounded timeout/delayed real-peer regression required')
    daemon=args.daemon.resolve();manifest_path=args.manifest.resolve()
    require(local.digest(daemon)==args.expected_daemon_sha256,'binary differs from approved build')
    manifest=json.loads(manifest_path.read_text())
    require(manifest['block_read_limit']<=args.receive_limit<=16*1024*1024,'receive limit must cover explicit manifest cap')
    require(2<=manifest['coinbase_maturity']<=16,'pilot requires actual maturity waiting within 2..16 blocks')
    require(manifest.get('schema')==1 and not manifest['field_sizes'],'pilot supports schema1 without supplied field hints')
    root=args.output.resolve();root.mkdir()
    (root/'manifest.json').write_bytes(manifest_path.read_bytes())
    sys.path.insert(0,str(args.reference_package.resolve()))
    from coincurve import PrivateKey
    from lotus_v2_reference.block import Parent,MonetaryState,empty_utxo_root,state_root,connect_complete_block
    from lotus_v2_reference.block_wire import decode_block_wire
    from lotus_v2_reference.block_seal import block_id
    from lotus_v2_reference.block_cost import BlockCostProfile
    from lotus_v2_reference.header_context import HeaderChainProfile
    from lotus_v2_reference.encoding import Output,Profile as OutputProfile,encode_output
    from lotus_v2_reference.signing import TxProfile,Transaction,Input,Witness,encode_transaction,identity_digests,signing_message
    from lotus_v2_reference.monetary import Profile as MonetaryProfile
    from lotus_v2_reference.vm import ASSIGNED,VMProfile
    h=manifest['header'];chain=bytes.fromhex(h['chain_id'])
    tx_profile=TxProfile(*manifest['transaction_limits']);money=MonetaryState.from_bytes(bytes.fromhex(manifest['initial_monetary']))
    monetary_profile=MonetaryProfile(*manifest['monetary']);cost_profile=BlockCostProfile(*manifest['outer_costs'])
    vm_limits=manifest['vm_limits'];schedule=manifest['opcode_costs']
    vm_profile=VMProfile(*vm_limits[:7],int(manifest['invocation_limits'][0]),manifest['invocation_limits'][2],
        {op:(lambda operands,results,c=schedule[op]:c[0]+c[1]*sum(operands)+c[2]*sum(results)) for op in ASSIGNED})
    hp=HeaderChainProfile(chain,h['version'],h['time'],h['bits'],int.from_bytes(bytes.fromhex(h['pow_limit']),'little'),h['half_life'],h['spacing'])
    genesis_block=decode_block_wire(bytes.fromhex(manifest['genesis']),tx_profile,chain)
    genesis=genesis_block.header
    require(all(output.flags&2 and output.value==0 for tx in genesis_block.transactions for output in tx.outputs),'pilot requires zero-valued pruned genesis outputs')
    require(manifest['dust_limit']==monetary_profile.dust_limit,'ordinary/monetary dust-limit mismatch unsupported')
    require(state_root(chain,0,empty_utxo_root(),money)==genesis.state_root,'empty genesis state assumption unsupported')
    coins={};history=[genesis];parent=Parent(chain,0,genesis.time,genesis.state_root,money,genesis)
    # Public fixture scalar, not a wallet key. Message derives from actual
    # native-mined funding bytes and independently validated resolved coins.
    fixture_key=PrivateKey.from_int(3);owner=fixture_key.public_key.format(compressed=True)[1:].hex()
    compiler=args.compiler.resolve()
    source=compiler/'examples/gallery/payment.lotus'
    js="import {readFileSync} from 'node:fs';const {compileContract}=await import(process.argv[1]);const source=readFileSync(process.argv[2],'utf8');console.log(JSON.stringify({source,artifact:compileContract(source,{contract:'Payment',bindings:{Payment:{owner:process.argv[3]}}})}));"
    compiled=subprocess.run([args.node,'--input-type=module','-e',js,(compiler/'dist/generic.js').as_uri(),str(source),owner],capture_output=True,text=True,timeout=30)
    require(compiled.returncode==0,compiled.stderr)
    artifact=json.loads(compiled.stdout);(root/'payment-artifact.json').write_text(json.dumps(artifact,indent=2)+'\n')
    policy=bytes.fromhex(artifact['artifact']['policy']['root']);script=bytes.fromhex(artifact['artifact']['methods'][0]['scriptHex'])
    output_profile=OutputProfile(16,16,812,8192)
    destination=encode_output(Output(0,0,None,(policy,),((0,),)),output_profile).hex()
    records=dict(schema='lotus-v2/native-mining-check/1',daemon_source=args.daemon_source,daemon_sha256=local.digest(daemon),
        build_command=args.build_command,reference_source=args.reference_source,compiler_source=args.compiler_source,
        reference_package=str(args.reference_package.resolve()),compiler=str(compiler),compiler_module_sha256=local.digest(compiler/'dist/generic.js'),
        manifest_sha256=local.digest(manifest_path),harness_sha256=local.digest(Path(__file__)),signer_scope='public fixture scalar3 using independent reference FULL signing; no wallet workflow',processes=[],checks=[])
    nodes=[];relay=None
    def save():(root/'evidence.json').write_text(json.dumps(records,indent=2)+'\n')
    def launch(label,home,connect):
        network=root/(label+'.network.json');network.write_text(json.dumps(dict(schema=1,magic=args.network_magic,listen=dict(address='127.0.0.1',port=0),connect=connect,receive_limit=args.receive_limit,local_policy='bounded-local-v1'),indent=2)+'\n')
        node=local.Node(label,daemon,root/'manifest.json',home,network,root,args.timeout);nodes.append(node);node.await_ready()
        records['processes'].append(dict(label=label,pid=node.process.pid,command=node.command,ready=node.ready));save();return node
    def snapshot(node):
        deadline=time.monotonic()+args.timeout
        while time.monotonic()<deadline:
            value=node.request('status',wait_timeout=max(.001,deadline-time.monotonic()))
            if value.get('tip_known') is True and all(value.get(key) is False for key in ('pending_journal','pending_receipt','pending_propagation','execution_paused','reopen_required')):return value
            time.sleep(.05)
        raise AssertionError('native owner did not reach quiescent authoritative state')
    def projection(value):return {key:value[key] for key in (*local.STATE_FIELDS,*local.IDENTITY_FIELDS,'invalid_roots','fetch_epoch')}
    def request_base(status):return dict(expected_parent=status['tip'],time=h['time']+(status['height']+1)*h['spacing'],max_claim='100000',coinbase_output=destination,coinbase_data=None,transactions=[],start_nonce='0',max_attempts=256)
    def negative(node,name,payload,result='invalid_request'):
        before=snapshot(node);answer=node.request('mineblock',**payload);after=snapshot(node)
        records['checks'].append(dict(check=name,response=answer,before=projection(before),after=projection(after)));save()
        require(answer.get('ok') is False and answer.get('result')==result,name+' unexpected error category: '+str(answer))
        require(projection(before)==projection(after),name+' changed authoritative chain/invalidity/fetch fences')
        return answer
    def duplicate_negative(node,payload):
        before=projection(snapshot(node));node.sequence+=1;identity=node.label+'-duplicate-'+str(node.sequence)
        raw=json.dumps(dict(id=identity,command='mineblock',**payload))[:-1]+',"max_claim":"100000"}\n'
        with (root/(node.label+'.requests.jsonl')).open('a') as output:output.write(raw)
        pending=memoryview(raw.encode());deadline=time.monotonic()+args.timeout
        while pending:
            require(time.monotonic()<deadline,'duplicate-field command write timeout')
            try:sent=os.write(node.process.stdin.fileno(),pending)
            except BlockingIOError:time.sleep(.01);continue
            require(sent>0,'duplicate-field command pipe closed');pending=pending[sent:]
        answer=node.wait(lambda response:response.get('id')==identity,max(.001,deadline-time.monotonic()))
        after=projection(snapshot(node))
        records['checks'].append(dict(check='duplicate-field',response=answer,before=before,after=after));save()
        require(answer.get('ok') is False and answer.get('result')=='invalid_request' and before==after,'duplicate fields mutated state or were accepted')

    def fetch(node,identity):
        # Small fixtures must exercise offsets spanning header/transaction bytes.
        chunk_bytes=97
        offset=0;body=bytearray();total=None;chunks=0
        while total is None or offset<total:
            answer=node.request('readblock',block_id=identity,offset=offset,length=chunk_bytes)
            require(answer.get('ok') is True and answer['block_id']==identity and answer['offset']==offset,'readblock chunk identity mismatch')
            require(type(answer['total_bytes']) is int and 0<answer['total_bytes']<=manifest['block_read_limit'],'readblock total exceeds manifest bound')
            require(total is None or total==answer['total_bytes'],'readblock length changed')
            total=answer['total_bytes'];require(local.hex_string(answer['data']),'noncanonical readblock hex');chunk=bytes.fromhex(answer['data'])
            require(0<len(chunk)<=chunk_bytes and offset+len(chunk)<=total,'invalid readblock chunk length')
            body.extend(chunk);offset+=len(chunk);chunks+=1
            require(answer['eof']==(offset==total),'readblock EOF mismatch')
        eof=node.request('readblock',block_id=identity,offset=total,length=1)
        require(eof.get('ok') is True and eof['data']=='' and eof['eof'] is True and eof['total_bytes']==total,'readblock exact-end behavior mismatch')
        path=root/(identity+'.block');path.write_bytes(body)
        require(chunks>1,'fixture did not exercise multiple readblock offsets')
        records['checks'].append(dict(check='connected-body-multiple-chunks',block_id=identity,chunks=chunks,chunk_bytes=chunk_bytes,total_bytes=total));save()
        return bytes(body)
    def accept_found(node,answer,peer,ordinary=()):
        nonlocal parent,money,history
        require(answer.get('ok') is True and answer.get('found') is True and answer.get('result')=='pending_validation','mining did not report a pending found candidate')
        require(answer.get('accepted') is False and answer.get('pending_validation') is True and answer.get('retained_authenticated') is True,'mineblock bypassed pending normal-validation boundary')
        require(answer.get('tip')==block_id(chain,parent.header).hex() and answer.get('height')==parent.height and answer.get('state_root')==parent.state_root.hex() and answer.get('monetary_bytes')==money.to_bytes().hex(),'found response already changed authoritative state before normal validation')
        deadline=time.monotonic()+args.timeout
        while time.monotonic()<deadline:
            status=snapshot(node)
            if status['tip']==answer['block_id']:break
            result=node.request('blockstatus',block_id=answer['block_id'])
            require(not result.get('deterministic_invalid'),'native mined its own invalid block')
            time.sleep(.05)
        require(status['tip']==answer['block_id'],'found candidate did not become authoritative')
        wire=fetch(node,answer['block_id']);framed=decode_block_wire(wire,tx_profile,chain)
        require(block_id(chain,framed.header).hex()==answer['block_id'] and str(framed.header.nonce)==answer['nonce'],'produced header ID/nonce differs from found result')
        connected=connect_complete_block(wire,parent,history,hp,coins,money,monetary_profile,cost_profile,tx_profile=tx_profile,vm_profile=vm_profile,block_cap=int(manifest['invocation_limits'][1]),coinbase_maturity=manifest['coinbase_maturity'])
        expected=dict(tip=answer['block_id'],height=framed.header.height,utxo_root=connected.utxo_root.hex(),state_root=connected.state_root.hex(),monetary_bytes=connected.monetary_bytes.hex())
        require(local.state_matches(status,expected),'native mined state differs from independent produced-byte validation')
        local.wait_state(peer,expected,args.timeout)
        require(tuple(framed.transactions[1:])==ordinary,'native miner changed supplied ordinary transaction order/bytes')
        cb=framed.transactions[0];ids=identity_digests(cb,tx_profile,chain)
        require(answer['coinbase_txid']==ids.txid.hex() and answer['coinbase_index']==0 and answer['coinbase_value']==str(cb.outputs[0].value),'confirmed coinbase identity/value differs from produced bytes')
        require(0<cb.outputs[0].value<=100000 and cb.outputs[0].branches==(policy,),'mined funding policy/claim mismatch')
        records['checks'].append(dict(check='native-found-reference-and-peer-accepted',response=answer,expected=expected,invocation_cost=connected.invocation_cost,coinbase_txid=ids.txid.hex(),coinbase_value=str(cb.outputs[0].value),body_sha256=local.digest(root/(answer['block_id']+'.block'))));save()
        money=MonetaryState.from_bytes(connected.monetary_bytes);parent=Parent(chain,framed.header.height,framed.header.time,framed.header.state_root,money,framed.header);history=([framed.header]+history)[:11]
        return ids,expected
    try:
        a=launch('a',root/'home-a',[])
        initial=snapshot(a)
        require(initial['tip']==h['genesis_id'] and initial['state_root']==genesis.state_root.hex() and initial['monetary_bytes']==money.to_bytes().hex(),'native genesis differs from explicit reference profile')
        relay=local.DelayRelay(a.ready['listen'],args.relay_delay,root)
        b=launch('b',root/'home-b',[relay.endpoint]);snapshot(b)
        deadline=time.monotonic()+args.timeout
        while time.monotonic()<deadline:
            if snapshot(a)['peer_active']>0 and snapshot(b)['peer_active']>0:break
            time.sleep(.05)
        require(snapshot(a)['peer_active']>0 and snapshot(b)['peer_active']>0,'real native peers did not activate')
        base=request_base(initial)
        for name,changes in [('attempts257',dict(max_attempts=257)),('attempts-bool',dict(max_attempts=True)),('nonce-overflow',dict(start_nonce=str(1<<64))),('nonce-noncanonical',dict(start_nonce='01')),('claim-overflow',dict(max_claim=str(1<<64))),('claim-noncanonical',dict(max_claim='00')),('time-overflow',dict(time=1<<48)),('empty-coinbase-data',dict(coinbase_data='')),('coinbase-data-cap',dict(coinbase_data='00'*8193)),('uppercase-hex',dict(coinbase_output=destination.upper())),('unknown-field',dict(extra=True))]:
            negative(a,name,{**base,**changes},'capacity_refused' if name=='coinbase-data-cap' else 'invalid_request')
        duplicate_negative(a,base)
        missing=dict(base);missing.pop('max_claim');negative(a,'missing-field',missing)
        nonzero=encode_output(Output(0,1,None,(policy,),((0,),)),output_profile).hex()
        negative(a,'nonzero-destination',{**base,'coinbase_output':nonzero})
        negative(a,'output-byte-cap',{**base,'coinbase_output':'00'*813},'capacity_refused')
        negative(a,'transaction-count-cap',{**base,'transactions':['00']*65536},'capacity_refused')
        stale={**base,'expected_parent':'ff'*32};negative(a,'stale-parent',stale,'stale_parent')
        before=projection(snapshot(a));zero=a.request('mineblock',**{**base,'max_attempts':0});after=projection(snapshot(a))
        require(zero.get('ok') is True and zero.get('found') is False and zero.get('result')=='nonce_exhausted' and zero.get('next_nonce')=='0' and zero.get('accepted') is False and zero.get('pending_validation') is False and before==after,'zero attempts mutated state or misreported exhaustion')
        records['checks'].append(dict(check='zero-attempts',response=zero));save()
        edge=a.request('mineblock',**{**base,'start_nonce':str((1<<64)-1),'max_attempts':2})
        if edge.get('found'):
            require(edge['nonce']==str((1<<64)-1),'native nonce search wrapped')
            funding_ids,expected=accept_found(a,edge,b)
        else:
            require(edge.get('ok') is True and edge.get('next_nonce') is None and edge.get('found') is False and projection(snapshot(a))==before,'end-of-u64 exhaustion wrapped or mutated state')
            funding_ids,expected=accept_found(a,a.request('mineblock',**base),b)
        records['checks'].append(dict(check='nonce-end-no-wrap',response=edge));save()
        funding=coins[(funding_ids.txid,0)]
        unsigned=Transaction(0,(Input(funding.tx_id,0,0xffffffff,1,witnesses=(Witness(script,(),(b'',)),)),),(Output(0,funding.value-1000,None,(policy,),((0,),)),))
        message=signing_message(unsigned,tx_profile,chain,(funding.output,),0,0,0)
        signature=fixture_key.sign_schnorr(message,aux_randomness=bytes(32))
        signed=replace(unsigned,inputs=(replace(unsigned.inputs[0],witnesses=(replace(unsigned.inputs[0].witnesses[0],arguments=(signature,)),)),))
        wire=encode_transaction(signed,tx_profile);(root/'signed-payment.tx').write_bytes(wire)
        negative(a,'immature-funding',{**request_base(snapshot(a)),'transactions':[wire.hex()]},'invalid_transactions')
        for _ in range(manifest['coinbase_maturity']-1):accept_found(a,a.request('mineblock',**request_base(snapshot(a))),b)
        base=request_base(snapshot(a))
        negative(a,'malformed-signed-bytes',{**base,'transactions':['00']},'invalid_transactions')
        bad=bytearray(signature);bad[0]^=1
        invalid=replace(signed,inputs=(replace(signed.inputs[0],witnesses=(replace(signed.inputs[0].witnesses[0],arguments=(bytes(bad),)),)),))
        negative(a,'invalid-signature',{**base,'transactions':[encode_transaction(invalid,tx_profile).hex()]},'invalid_transactions')
        negative(a,'aggregate-byte-cap',{**base,'transactions':['00'*(manifest['block_read_limit']+1)]},'capacity_refused')
        _,expected=accept_found(a,a.request('mineblock',**{**base,'transactions':[wire.hex()]}),b,(signed,))
        require((funding.tx_id,0) not in coins,'native mined spend retained its funding coin')
        spent_id=identity_digests(signed,tx_profile,chain).txid
        for point in [(funding.tx_id,0),(spent_id,0)]:
            wanted=None if point not in coins else coins[point].encode().hex()
            responses=[]
            for node in (a,b):
                coin=node.request('coin',txid=point[0].hex(),index=point[1]);proof=node.request('proof',txid=point[0].hex(),index=point[1])
                require(local.state_matches(coin,expected) and local.state_matches(proof,expected) and coin['coin']==wanted,'confirmed coin/reference snapshot mismatch')
                responses.append(proof['proof'])
            require(responses[0]==responses[1],'native mined proof paths differ across nodes')
            records['checks'].append(dict(check='mined-coin-proof',txid=point[0].hex(),coin=wanted,proof=responses[0]));save()
        b.stop();b=launch('b-restart',root/'home-b',[relay.endpoint]);require(local.state_matches(b.ready,expected),'native mined tip failed persisted restart')
        local.wait_state(b,expected,args.timeout)
        records['passed']=True;records['final']=expected;save()
    except Exception as error:
        records['failure']=dict(kind=type(error).__name__,error=str(error));raise
    finally:
        errors=[]
        for node in reversed(nodes):
            try:node.stop()
            except Exception as error:errors.append(str(error))
        if relay:
            try:relay.stop()
            except Exception as error:errors.append(str(error))
            records['relay']=relay.stats
        records['cleanup']=[dict(label=node.label,pid=node.process.pid,exit=node.process.poll()) for node in nodes]
        records['cleanup_errors']=errors
        if errors:records['passed']=False
        save();require(not errors,'child/relay cleanup failed: '+str(errors))
    print('Native-mined blocks and public-fixture signed Payment passed:',root)


if __name__=='__main__':main()
